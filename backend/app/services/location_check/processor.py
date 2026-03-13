"""
Location check processing pipeline.

Compares geo-locations from:
1. Photo - GPS overlay extracted via LLM
2. ID Card - Address extracted via LLM → geocoded
3. Lab - Address from pathology result → geocoded

Flags if any pairwise distance exceeds threshold.
"""

import json
import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

from app.services.storage import s3_service
from app.services.common.tesseract_ocr import normalize_to_image
from app.services.llm import client as llm_client
from app.services.llm.context import current_case_id, current_task, current_call_count, current_operation
from app.services.location_check.prompts import photo_geo as photo_prompt
from app.services.location_check.prompts import id_address as id_prompt
from app.services.location_check.lab_address import get_lab_address
from app.services.location_check.geocoder import (
    geocode_address,
    reverse_geocode,
    calculate_distance_km,
)
from app.services.location_check.config import PASS_MAX_KM, REVIEW_MAX_KM
from app.models.location_check_result import (
    LocationCheckResultModel,
    LocationSource,
    DistanceResult,
    LocationDecision,
    SourceStatus,
    ReviewStatus,
)
from app.dependencies import get_database


# ─── S3 download ─────────────────────────────────────────────────────────────

async def _download_file(s3_key: str) -> bytes:
    """Download a single file from S3."""
    return await s3_service.download_file(s3_key)


# ─── Photo geo extraction (LLM) ──────────────────────────────────────────────

async def _extract_photo_geo(image_bytes: bytes) -> LocationSource:
    """
    Extract location from photo using LLM vision.
    
    Priority:
    1. GPS coordinates (lat/lon) - preferred
    2. Address/pincode - fallback, geocoded to coordinates
    """
    try:
        current_operation.set("photo_geo")
        llm_response = await llm_client.call(
            system_prompt=photo_prompt.SYSTEM_PROMPT,
            user_prompt=photo_prompt.build_user_prompt(),
            config=photo_prompt.CONFIG,
            images=[image_bytes],
        )

        parsed = json.loads(llm_response)
        lat = parsed.get("lat")
        lon = parsed.get("lon")
        address = parsed.get("address")
        pincode = parsed.get("pincode")
        raw_text = parsed.get("raw_text")

        # Priority 1: Use coordinates if available
        if lat is not None and lon is not None:
            # Reverse geocode to get human-readable address
            resolved_address = await reverse_geocode(lat, lon)
            return LocationSource(
                source_type="photo",
                status=SourceStatus.FOUND,
                raw_input=raw_text or f"{lat}, {lon}",
                address=resolved_address or f"{lat:.6f}, {lon:.6f}",
                coords=(lat, lon),
            )

        # Priority 2: Fallback to address/pincode if no coordinates
        if address or pincode:
            # Use pincode for geocoding if available (more reliable)
            geocode_query = pincode if pincode else address
            coords = await geocode_address(geocode_query)

            if coords:
                return LocationSource(
                    source_type="photo",
                    status=SourceStatus.FOUND,
                    raw_input=raw_text or address,
                    address=address or pincode,
                    coords=coords,
                )
            else:
                return LocationSource(
                    source_type="photo",
                    status=SourceStatus.GEOCODE_FAILED,
                    raw_input=raw_text or address,
                    address=address,
                    message=f"Geocoding failed for: {geocode_query}",
                )

        # Nothing found
        return LocationSource(
            source_type="photo",
            status=SourceStatus.NOT_FOUND,
            message="No coordinates or address found in photo overlay",
        )

    except Exception as e:
        return LocationSource(
            source_type="photo",
            status=SourceStatus.NOT_FOUND,
            message=f"Failed to extract location: {str(e)}",
        )


# ─── ID card address extraction (LLM) ────────────────────────────────────────

async def _extract_id_address(image_bytes: bytes) -> LocationSource:
    """Extract address from ID card using LLM vision, then geocode."""
    try:
        current_operation.set("id_address")
        llm_response = await llm_client.call(
            system_prompt=id_prompt.SYSTEM_PROMPT,
            user_prompt=id_prompt.build_user_prompt(),
            config=id_prompt.CONFIG,
            images=[image_bytes],
        )

        parsed = json.loads(llm_response)
        address = parsed.get("address")
        pincode = parsed.get("pincode")

        if not address and not pincode:
            return LocationSource(
                source_type="id_card",
                status=SourceStatus.NOT_FOUND,
                message="No address found in ID card",
            )

        # Use pincode for geocoding if available (more reliable)
        geocode_query = pincode if pincode else address
        coords = await geocode_address(geocode_query)

        if coords:
            return LocationSource(
                source_type="id_card",
                status=SourceStatus.FOUND,
                raw_input=address,
                address=address,
                coords=coords,
            )
        else:
            return LocationSource(
                source_type="id_card",
                status=SourceStatus.GEOCODE_FAILED,
                raw_input=address,
                address=address,
                message=f"Geocoding failed for: {geocode_query}",
            )

    except Exception as e:
        return LocationSource(
            source_type="id_card",
            status=SourceStatus.NOT_FOUND,
            message=f"Failed to extract address: {str(e)}",
        )


# ─── Lab address extraction ──────────────────────────────────────────────────

async def _extract_lab_address(case_id: str) -> Tuple[LocationSource, Optional[int]]:
    """Get lab address from pathology result and geocode using full address."""
    address, pincode, path_version = await get_lab_address(case_id)

    if not address and not pincode:
        return LocationSource(
            source_type="lab",
            status=SourceStatus.NOT_FOUND,
            message="No lab address in pathology result",
        ), path_version

    # Use full address for geocoding (more accurate than pincode centroid)
    geocode_query = address if address else pincode
    coords = await geocode_address(geocode_query)

    if coords:
        return LocationSource(
            source_type="lab",
            status=SourceStatus.FOUND,
            raw_input=address or pincode,
            address=address or pincode,
            coords=coords,
        ), path_version
    else:
        return LocationSource(
            source_type="lab",
            status=SourceStatus.GEOCODE_FAILED,
            raw_input=address or pincode,
            address=address or pincode,
            message=f"Geocoding failed for: {geocode_query}",
        ), path_version


# ─── Distance calculation ────────────────────────────────────────────────────

def _calculate_distances(
    sources: List[LocationSource],
) -> List[DistanceResult]:
    """Calculate pairwise distances for sources with valid coordinates."""
    # Filter sources with valid coords
    valid_sources = [s for s in sources if s.coords is not None]

    distances = []
    for i in range(len(valid_sources)):
        for j in range(i + 1, len(valid_sources)):
            src_a = valid_sources[i]
            src_b = valid_sources[j]
            dist_km = calculate_distance_km(src_a.coords, src_b.coords)
            distances.append(DistanceResult(
                source_a=src_a.source_type,
                source_b=src_b.source_type,
                distance_km=round(dist_km, 2),
                flag=dist_km > PASS_MAX_KM,  # flag if outside pass range
            ))

    return distances


# ─── Decision logic ──────────────────────────────────────────────────────────

def _make_decision(
    sources: List[LocationSource],
    distances: List[DistanceResult],
) -> Tuple[LocationDecision, List[str], str]:
    """Determine final decision based on sources and distances.
    
    Tiered thresholds:
    - 0-15 km: pass
    - 15-30 km: needs_review
    - > 30 km: fail
    """
    valid_count = sum(1 for s in sources if s.coords is not None)
    flags = []

    # Check for missing/failed sources
    for s in sources:
        if s.status == SourceStatus.NOT_FOUND:
            flags.append(f"{s.source_type}: not detected")
        elif s.status == SourceStatus.SKIPPED:
            flags.append(f"{s.source_type}: document not uploaded")
        elif s.status == SourceStatus.GEOCODE_FAILED:
            flags.append(f"{s.source_type}: geocoding failed")

    # Categorize distances by tier
    fail_distances = [d for d in distances if d.distance_km > REVIEW_MAX_KM]
    review_distances = [d for d in distances if PASS_MAX_KM < d.distance_km <= REVIEW_MAX_KM]

    for d in fail_distances:
        flags.append(f"Distance {d.source_a} ↔ {d.source_b}: {d.distance_km} km > {REVIEW_MAX_KM} km (fail)")
    for d in review_distances:
        flags.append(f"Distance {d.source_a} ↔ {d.source_b}: {d.distance_km} km ({PASS_MAX_KM}-{REVIEW_MAX_KM} km range)")

    # Decision (tiered)
    if valid_count < 2:
        decision = LocationDecision.INSUFFICIENT
        message = f"Insufficient data: only {valid_count} location(s) available for comparison"
    elif fail_distances:
        decision = LocationDecision.FAIL
        message = f"Location mismatch: {len(fail_distances)} distance(s) exceed {REVIEW_MAX_KM} km threshold"
    elif review_distances:
        decision = LocationDecision.NEEDS_REVIEW
        message = f"Review needed: {len(review_distances)} distance(s) in {PASS_MAX_KM}-{REVIEW_MAX_KM} km range"
    else:
        decision = LocationDecision.PASS
        message = f"All {len(distances)} distance(s) within {PASS_MAX_KM} km threshold"

    return decision, flags, message


# ─── DB storage ──────────────────────────────────────────────────────────────

async def _get_next_version(case_id: str) -> int:
    """Get the next version number for a case's location check result."""
    db = await get_database()
    latest = await db.location_check_results.find_one(
        {"case_id": case_id},
        sort=[("version", -1)],
        projection={"version": 1},
    )
    return (latest["version"] + 1) if latest else 1


async def _store_result(result: LocationCheckResultModel) -> str:
    """Store a location check result in MongoDB. Returns the inserted ID."""
    db = await get_database()
    doc = result.model_dump()
    insert = await db.location_check_results.insert_one(doc)
    return str(insert.inserted_id)


async def get_latest_result(case_id: str) -> Optional[dict]:
    """Get the latest location check result for a case."""
    db = await get_database()
    doc = await db.location_check_results.find_one(
        {"case_id": case_id},
        sort=[("version", -1)],
    )
    if doc:
        doc["_id"] = str(doc["_id"])
    return doc


async def update_review_status(
    case_id: str,
    review_status: ReviewStatus,
    reviewed_by: str,
    comment: Optional[str] = None,
) -> Optional[dict]:
    """Update the review status of the latest location check result."""
    from datetime import datetime

    db = await get_database()
    result = await db.location_check_results.find_one_and_update(
        {"case_id": case_id},
        {
            "$set": {
                "review_status": review_status.value,
                "reviewed_by": reviewed_by,
                "reviewed_at": datetime.utcnow(),
                "review_comment": comment,
            }
        },
        sort=[("version", -1)],
        return_document=True,
    )
    if result:
        result["_id"] = str(result["_id"])
    return result


# ─── Main pipeline ───────────────────────────────────────────────────────────

async def process_location_check(
    case_id: str,
    photo_files: List[dict],
    id_files: List[dict],
) -> dict:
    """
    Full location check processing pipeline:

    1. Extract photo GPS coordinates (LLM vision)
    2. Extract ID card address (LLM vision) → geocode
    3. Get lab address from pathology → geocode
    4. Calculate pairwise distances
    5. Make decision
    6. Store versioned result in MongoDB

    Args:
        case_id: The case ID.
        photo_files: List of photo file entries (geo-tagged)
        id_files: List of ID proof file entries

    Returns:
        Result summary dict.
    """
    current_case_id.set(case_id)
    current_task.set("location_check")
    call_counter = [0]
    current_call_count.set(call_counter)
    t_llm = time.monotonic()

    sources = []
    photo_file_id = None
    id_file_id = None
    pathology_version = None

    # ── 1. Photo extraction
    if photo_files:
        photo_entry = photo_files[0]
        photo_file_id = photo_entry["id"]
        photo_bytes = await _download_file(photo_entry["s3_key"])
        try:
            photo_bytes = normalize_to_image(photo_bytes)
        except ValueError as e:
            sources.append(LocationSource(
                source_type="photo",
                status=SourceStatus.NOT_FOUND,
                message=str(e),
            ))
            photo_bytes = None
        if photo_bytes:
            photo_source = await _extract_photo_geo(photo_bytes)
            sources.append(photo_source)
    else:
        sources.append(LocationSource(
            source_type="photo",
            status=SourceStatus.SKIPPED,
            message="Photo not uploaded",
        ))

    # ── 2. ID card extraction
    if id_files:
        id_entry = id_files[0]
        id_file_id = id_entry["id"]
        id_bytes = await _download_file(id_entry["s3_key"])
        try:
            id_bytes = normalize_to_image(id_bytes)
        except ValueError as e:
            sources.append(LocationSource(
                source_type="id_card",
                status=SourceStatus.NOT_FOUND,
                message=str(e),
            ))
            id_bytes = None
        if id_bytes:
            id_source = await _extract_id_address(id_bytes)
            sources.append(id_source)
    else:
        sources.append(LocationSource(
            source_type="id_card",
            status=SourceStatus.SKIPPED,
            message="ID proof not uploaded",
        ))

    # ── 3. Lab address extraction
    lab_source, pathology_version = await _extract_lab_address(case_id)
    sources.append(lab_source)

    llm_wall = time.monotonic() - t_llm
    total_calls = call_counter[0]
    logger.info(
        "LLM_PIPELINE,case_id=%s,task=location_check,total_calls=%s,llm_wall_s=%.2f,calls_per_sec=%.2f",
        case_id, total_calls, llm_wall, total_calls / llm_wall if llm_wall > 0 else 0,
    )

    # ── 4. Calculate distances
    distances = _calculate_distances(sources)

    # ── 5. Make decision
    decision, flags, message = _make_decision(sources, distances)

    # ── 6. Build summary lists
    sources_detected = [s.source_type for s in sources if s.status == SourceStatus.FOUND]
    sources_not_detected = [
        s.source_type for s in sources
        if s.status in (SourceStatus.NOT_FOUND, SourceStatus.SKIPPED, SourceStatus.GEOCODE_FAILED)
    ]

    # ── 7. Store result
    version = await _get_next_version(case_id)

    result = LocationCheckResultModel(
        case_id=case_id,
        version=version,
        photo_file_id=photo_file_id,
        id_file_id=id_file_id,
        pathology_version=pathology_version,
        sources=sources,
        distances=distances,
        sources_detected=sources_detected,
        sources_not_detected=sources_not_detected,
        decision=decision,
        flags=flags,
        message=message,
        review_status=ReviewStatus.PENDING,
    )

    doc_id = await _store_result(result)

    return {
        "_id": doc_id,
        "case_id": case_id,
        "version": version,
        "decision": decision.value,
        "message": message,
        "sources_detected": sources_detected,
        "sources_not_detected": sources_not_detected,
        "distances": [d.model_dump() for d in distances],
        "flags": flags,
    }
