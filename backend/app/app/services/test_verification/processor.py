"""
Test Verification Processor.

Verifies that required tests (from insurance requirements page) are present in pathology results.
"""

import json
import asyncio
import logging
import time
from typing import Any, Dict, List, Optional
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)

from app.services.llm import client as llm_client
from app.services.llm.context import current_case_id, current_task, current_call_count
from app.services.test_verification.config import (
    PAGE_5_IDENTIFIERS,
    normalize_category,
    expand_categories,
    CATEGORY_TESTS,
)
from app.services.test_verification.prompts import extract as extract_prompt
from app.models.test_verification_result import (
    TestVerificationResultModel,
    RequiredTest,
)
from app.dependencies import get_database
from bson import ObjectId
from datetime import datetime


# Thresholds for page classification
FUZZY_THRESHOLD = 80
CONFIDENCE_THRESHOLD = 0.5  # Lower threshold since Page 5 has fewer keywords


def score_page_for_requirements(ocr_text: str) -> float:
    """
    Score how well OCR text matches Page 5 (requirements page) identifiers.
    
    Returns a score between 0.0 and 1.0
    """
    matched = 0
    text_lower = ocr_text.lower()
    
    for keyword in PAGE_5_IDENTIFIERS:
        if fuzz.partial_ratio(keyword.lower(), text_lower) >= FUZZY_THRESHOLD:
            matched += 1
    
    return matched / len(PAGE_5_IDENTIFIERS)


def find_requirements_page(pages: List[dict]) -> Optional[dict]:
    """
    Find the requirements page (Page 5) from a list of OCR'd pages.
    
    Args:
        pages: List of dicts with "page_number", "text", "image_bytes"
        
    Returns:
        The page dict if found, None otherwise
    """
    best_page = None
    best_score = 0.0
    
    for page in pages:
        score = score_page_for_requirements(page["text"])
        if score > best_score and score >= CONFIDENCE_THRESHOLD:
            best_score = score
            best_page = page
    
    return best_page


async def extract_requirements(image_bytes: bytes) -> dict:
    """
    Extract insurance requirements from Page 5 image using LLM.
    
    Returns:
        Extracted data dict with ins_test_remark, parsed_requirements, etc.
    """
    llm_response = await llm_client.call(
        system_prompt=extract_prompt.SYSTEM_PROMPT,
        user_prompt=extract_prompt.USER_PROMPT,
        config=extract_prompt.CONFIG,
        images=[image_bytes],
    )
    
    try:
        return json.loads(llm_response)
    except json.JSONDecodeError:
        return {"raw_response": llm_response, "error": "Failed to parse LLM response"}


def get_pathology_test_names(pathology_result: dict) -> set:
    """
    Extract all test names present in pathology result.
    
    Args:
        pathology_result: PathologyResultModel as dict
        
    Returns:
        Set of test names (standardized names)
    """
    test_names = set()
    
    # Get from fields (flattened)
    for field in pathology_result.get("fields", []):
        if field.get("key"):
            test_names.add(field["key"])
    
    # Also check standardized section
    standardized = pathology_result.get("standardized", {})
    for key in standardized:
        if key not in ("Remark", "unmatched_tests"):
            test_names.add(key)
    
    return test_names


def verify_tests(
    required_categories: List[str],
    pathology_tests: set,
    mer_exists: bool,
) -> tuple[List[RequiredTest], List[str]]:
    """
    Verify which required tests are present.
    
    Args:
        required_categories: List of category names from ins_test_remark
        pathology_tests: Set of test names from pathology result
        mer_exists: Whether MER result exists
        
    Returns:
        Tuple of (list of RequiredTest, list of missing test names)
    """
    required_tests = []
    missing = []
    
    for category in required_categories:
        canonical = normalize_category(category)
        
        # Handle MER requirement
        if category.upper() == "MER" or canonical == "MER":
            req = RequiredTest(
                category="MER",
                test_name="MER Form",
                found=mer_exists,
            )
            required_tests.append(req)
            if not mer_exists:
                missing.append("MER Form")
            continue
        
        # Skip if category not recognized
        if not canonical or canonical not in CATEGORY_TESTS:
            continue
        
        # Expand category to individual tests
        for test_name in CATEGORY_TESTS[canonical]:
            found = test_name in pathology_tests
            req = RequiredTest(
                category=category,
                test_name=test_name,
                found=found,
            )
            required_tests.append(req)
            if not found:
                missing.append(test_name)
    
    return required_tests, missing


# ─── DB operations ──────────────────────────────────────────────────────────

async def _update_pipeline_status(case_id: str, status: str):
    """Update the test_verification pipeline status for a case."""
    db = await get_database()
    await db.cases.update_one(
        {"_id": ObjectId(case_id)},
        {"$set": {
            "pipeline_status.test_verification": status,
            "updated_at": datetime.utcnow(),
        }},
    )


async def _get_next_version(case_id: str) -> int:
    """Get the next version number for a case's test verification result."""
    db = await get_database()
    latest = await db.test_verification_results.find_one(
        {"case_id": case_id},
        sort=[("version", -1)],
        projection={"version": 1},
    )
    return (latest["version"] + 1) if latest else 1


async def _store_result(result: TestVerificationResultModel) -> str:
    """Store a test verification result in MongoDB. Returns the inserted ID."""
    db = await get_database()
    doc = result.model_dump()
    insert = await db.test_verification_results.insert_one(doc)
    return str(insert.inserted_id)


async def get_latest_result(case_id: str) -> Optional[dict]:
    """Get the latest test verification result for a case."""
    db = await get_database()
    doc = await db.test_verification_results.find_one(
        {"case_id": case_id},
        sort=[("version", -1)],
    )
    if doc:
        doc["_id"] = str(doc["_id"])
    return doc


async def get_mer_result(case_id: str) -> Optional[dict]:
    """Get the latest MER result for a case."""
    db = await get_database()
    doc = await db.mer_results.find_one(
        {"case_id": case_id},
        sort=[("version", -1)],
    )
    return doc


async def get_pathology_result(case_id: str) -> Optional[dict]:
    """Get the latest pathology result for a case."""
    db = await get_database()
    doc = await db.pathology_results.find_one(
        {"case_id": case_id},
        sort=[("version", -1)],
    )
    return doc


# ─── Main pipeline ──────────────────────────────────────────────────────────

async def extract_requirements_for_case(
    case_id: str,
    mer_pages: List[dict],
) -> dict:
    """
    Phase 1: Extract requirements from Page 5 during MER processing.

    Finds Page 5, runs LLM extraction, and stores the result with
    status="pending_verification". The actual comparison against
    pathology results happens later in ``complete_verification``.

    Args:
        case_id: The case ID
        mer_pages: List of OCR'd pages from MER processing

    Returns:
        Stored result dict (status will be "pending_verification",
        "requirements_page_not_found", or "extraction_failed")
    """
    current_case_id.set(case_id)
    current_task.set("test_verification")
    call_counter = [0]
    current_call_count.set(call_counter)

    await _update_pipeline_status(case_id, "processing")

    try:
        requirements_page = find_requirements_page(mer_pages)
        version = await _get_next_version(case_id)

        if not requirements_page:
            result = TestVerificationResultModel(
                case_id=case_id,
                version=version,
                page_found=False,
                status="requirements_page_not_found",
            )
            doc_id = await _store_result(result)
            await _update_pipeline_status(case_id, "extracted")
            return {"_id": doc_id, **result.model_dump()}

        t_llm = time.monotonic()
        extracted = await extract_requirements(requirements_page["image_bytes"])
        llm_wall = time.monotonic() - t_llm
        logger.info(
            "LLM_PIPELINE,case_id=%s,task=test_verification,total_calls=%s,llm_wall_s=%.2f,calls_per_sec=%.2f",
            case_id, call_counter[0], llm_wall, call_counter[0] / llm_wall if llm_wall > 0 else 0,
        )

        if "error" in extracted:
            result = TestVerificationResultModel(
                case_id=case_id,
                version=version,
                page_found=True,
                status="extraction_failed",
            )
            doc_id = await _store_result(result)
            await _update_pipeline_status(case_id, "failed")
            return {
                "_id": doc_id,
                **result.model_dump(),
                "extraction_error": extracted.get("error"),
            }

        raw_requirements = extracted.get("parsed_requirements", [])

        result = TestVerificationResultModel(
            case_id=case_id,
            version=version,
            page_found=True,
            proposal_number=extracted.get("proposal_number"),
            life_assured_name=extracted.get("life_assured_name"),
            ins_test_remark=extracted.get("ins_test_remark"),
            hi_test_remark=extracted.get("hi_test_remark"),
            extraction_confidence=extracted.get("confidence", 0.0),
            raw_requirements=raw_requirements,
            status="pending_verification",
        )
        doc_id = await _store_result(result)
        # Stay in "processing" — verification will finish later
        await _update_pipeline_status(case_id, "pending_verification")
        return {"_id": doc_id, **result.model_dump()}

    except Exception as e:
        await _update_pipeline_status(case_id, "failed")
        raise


async def complete_verification(case_id: str) -> dict:
    """
    Phase 2: Compare extracted requirements against pathology results.

    Called by the orchestrator once both MER and pathology have completed.
    Reads the previously stored extraction result and runs the comparison.

    Args:
        case_id: The case ID

    Returns:
        Updated verification result dict
    """
    current_case_id.set(case_id)
    current_task.set("test_verification")

    await _update_pipeline_status(case_id, "processing")

    try:
        # Get the stored extraction result
        prev = await get_latest_result(case_id)

        if not prev:
            # No extraction was stored (MER had no unmatched pages)
            await _update_pipeline_status(case_id, "extracted")
            return {"case_id": case_id, "status": "no_extraction_found"}

        # If extraction already failed or page wasn't found, nothing to do
        if prev.get("status") in ("requirements_page_not_found", "extraction_failed"):
            await _update_pipeline_status(case_id, "extracted")
            return prev

        # If already verified (not pending), skip
        if prev.get("status") not in ("pending_verification",):
            await _update_pipeline_status(case_id, "extracted")
            return prev

        raw_requirements = prev.get("raw_requirements", [])

        # Get pathology result (should exist now)
        pathology_result = await get_pathology_result(case_id)
        pathology_tests = get_pathology_test_names(pathology_result) if pathology_result else set()

        # Get MER result
        mer_result = await get_mer_result(case_id)
        mer_exists = mer_result is not None

        # Run comparison
        required_tests, missing_tests = verify_tests(
            raw_requirements,
            pathology_tests,
            mer_exists,
        )

        total_required = len(required_tests)
        total_found = sum(1 for t in required_tests if t.found)
        total_missing = total_required - total_found
        status = "complete" if total_missing == 0 else "missing_tests"

        version = await _get_next_version(case_id)

        result = TestVerificationResultModel(
            case_id=case_id,
            version=version,
            page_found=prev.get("page_found", True),
            proposal_number=prev.get("proposal_number"),
            life_assured_name=prev.get("life_assured_name"),
            ins_test_remark=prev.get("ins_test_remark"),
            hi_test_remark=prev.get("hi_test_remark"),
            extraction_confidence=prev.get("extraction_confidence", 0.0),
            raw_requirements=raw_requirements,
            required_tests=required_tests,
            total_required=total_required,
            total_found=total_found,
            total_missing=total_missing,
            missing_tests=missing_tests,
            status=status,
            mer_result_version=mer_result.get("version") if mer_result else None,
            pathology_result_version=pathology_result.get("version") if pathology_result else None,
        )

        doc_id = await _store_result(result)
        await _update_pipeline_status(case_id, "extracted")

        return {"_id": doc_id, **result.model_dump()}

    except Exception as e:
        await _update_pipeline_status(case_id, "failed")
        raise


async def run_verification_standalone(case_id: str) -> dict:
    """
    Run test verification as a standalone operation.
    
    Fetches MER result to get classification info and re-runs Page 5 detection
    if unmatched pages exist. For cases where MER was already processed.
    
    Args:
        case_id: The case ID
        
    Returns:
        Test verification result dict
    """
    current_case_id.set(case_id)
    current_task.set("test_verification")

    # Update pipeline status to processing
    await _update_pipeline_status(case_id, "processing")
    
    try:
        # Get MER result to check for unmatched pages
        mer_result = await get_mer_result(case_id)
        
        if not mer_result:
            await _update_pipeline_status(case_id, "not_started")
            return {
                "error": "MER result not found. Process MER first.",
                "case_id": case_id,
            }
        
        # Check if there are unmatched pages that might be Page 5
        classification = mer_result.get("classification", {})
        unmatched_pages = classification.get("unmatched_pages", [])
        
        if not unmatched_pages:
            # No unmatched pages - Page 5 likely not present
            version = await _get_next_version(case_id)
            result = TestVerificationResultModel(
                case_id=case_id,
                version=version,
                page_found=False,
                status="requirements_page_not_found",
                mer_result_version=mer_result.get("version"),
            )
            doc_id = await _store_result(result)
            await _update_pipeline_status(case_id, "extracted")
            return {
                "_id": doc_id,
                **result.model_dump(),
            }
        
        # Re-score unmatched pages for Page 5
        # Note: This requires the OCR text which is stored in unmatched_pages
        best_page = None
        best_score = 0.0
        
        for page in unmatched_pages:
            ocr_text = page.get("ocr_text", "")
            score = score_page_for_requirements(ocr_text)
            if score > best_score and score >= CONFIDENCE_THRESHOLD:
                best_score = score
                best_page = page
        
        if not best_page:
            version = await _get_next_version(case_id)
            result = TestVerificationResultModel(
                case_id=case_id,
                version=version,
                page_found=False,
                status="requirements_page_not_found",
                mer_result_version=mer_result.get("version"),
            )
            doc_id = await _store_result(result)
            await _update_pipeline_status(case_id, "extracted")
            return {
                "_id": doc_id,
                **result.model_dump(),
            }
        
        # Found a candidate - but we need image bytes which aren't stored
        # Return info that Page 5 was detected but needs re-processing
        await _update_pipeline_status(case_id, "not_started")
        return {
            "case_id": case_id,
            "page_5_detected": True,
            "page_number": best_page.get("page_number"),
            "confidence": best_score,
            "message": "Page 5 detected in unmatched pages. Re-process MER to run full verification.",
        }
    except Exception as e:
        await _update_pipeline_status(case_id, "failed")
        raise
