import json
import asyncio
import importlib
import logging
import time
from typing import Any, Dict, List, Optional

from app.services.storage import s3_service
from app.services.common.tesseract_ocr import extract_from_file
from app.services.mer.page_classifier import classify_pages
from app.services.llm import client as llm_client
from app.services.llm.context import current_case_id, current_task, current_call_count
from app.services.mer.flattener import flatten_all_pages
from app.models.mer_result import MERResultModel
from app.dependencies import get_database

logger = logging.getLogger("mer_processor")


# ─── Prompt module registry ─────────────────────────────────────────────────
PROMPT_MODULES = {
    1: "app.services.mer.prompts.page_1",
    2: "app.services.mer.prompts.page_2",
    3: "app.services.mer.prompts.page_3",
    4: "app.services.mer.prompts.page_4",
}

_module_cache: Dict[int, Any] = {}


def _get_prompt_module(page_num: int):
    """Import & cache the prompt module for a given MER page number."""
    if page_num in _module_cache:
        return _module_cache[page_num]
    module_path = PROMPT_MODULES.get(page_num)
    if not module_path:
        return None
    mod = importlib.import_module(module_path)
    _module_cache[page_num] = mod
    return mod


# ─── S3 download (parallel) ─────────────────────────────────────────────────

async def _download_file(s3_key: str) -> bytes:
    """Download a single file from S3."""
    return await s3_service.download_file(s3_key)


async def _download_all(file_entries: List[dict]) -> List[dict]:
    """Download all files from S3 in parallel.

    Returns list of {"file_bytes": bytes, "content_type": str} in same order.
    """
    tasks = [_download_file(e["s3_key"]) for e in file_entries]
    results = await asyncio.gather(*tasks)
    return [
        {"file_bytes": fb, "content_type": e["content_type"]}
        for fb, e in zip(results, file_entries)
    ]


# ─── OCR (already parallel inside extract_from_file) ────────────────────────

async def _ocr_all(downloaded: List[dict]) -> List[dict]:
    """Run OCR on all downloaded files in parallel.

    Each file may produce multiple pages (PDFs).
    Returns flat list of page dicts with global page_number re-indexing.
    """
    tasks = [extract_from_file(d["file_bytes"], d["content_type"]) for d in downloaded]
    all_file_pages = await asyncio.gather(*tasks)

    # Flatten and re-index pages globally
    all_pages = []
    page_counter = 1
    for file_pages in all_file_pages:
        for page in file_pages:
            page["page_number"] = page_counter
            all_pages.append(page)
            page_counter += 1

    return all_pages


# ─── LLM extraction (parallel) ──────────────────────────────────────────────

async def _llm_extract_page(mer_page_num: int, match_info: dict) -> Optional[dict]:
    """Run LLM extraction for a single matched MER page."""
    page = match_info["page"]

    # Special handling for Page 1 - use split processor for better accuracy
    if mer_page_num == 1:
        from app.services.mer.page_1_processor import extract_page_1
        parsed = await extract_page_1(page["image_bytes"])
        return {
            "mer_page_num": mer_page_num,
            "extracted_data": parsed,
            "confidence": match_info["confidence"],
            "source_page": page["page_number"],
        }

    # Special handling for Page 2 - use split processor for alcohol table accuracy
    if mer_page_num == 2:
        from app.services.mer.page_2_processor import extract_page_2
        parsed = await extract_page_2(page["image_bytes"])
        return {
            "mer_page_num": mer_page_num,
            "extracted_data": parsed,
            "confidence": match_info["confidence"],
            "source_page": page["page_number"],
        }

    # Special handling for Page 3 - use split processor for Y/N questions accuracy
    if mer_page_num == 3:
        from app.services.mer.page_3_processor import extract_page_3
        parsed = await extract_page_3(page["image_bytes"])
        return {
            "mer_page_num": mer_page_num,
            "extracted_data": parsed,
            "confidence": match_info["confidence"],
            "source_page": page["page_number"],
        }

    # Special handling for Page 4 - use split processor for Y/N questions accuracy
    if mer_page_num == 4:
        from app.services.mer.page_4_processor import extract_page_4
        parsed = await extract_page_4(page["image_bytes"])
        return {
            "mer_page_num": mer_page_num,
            "extracted_data": parsed,
            "confidence": match_info["confidence"],
            "source_page": page["page_number"],
        }

    # Standard processing for other pages
    prompt_module = _get_prompt_module(mer_page_num)
    if not prompt_module:
        return None

    llm_response = await llm_client.call(
        system_prompt=prompt_module.SYSTEM_PROMPT,
        user_prompt=prompt_module.USER_PROMPT,
        config=prompt_module.CONFIG,
        images=[page["image_bytes"]],
    )

    try:
        parsed = json.loads(llm_response)
    except json.JSONDecodeError:
        parsed = {"raw_response": llm_response}

    return {
        "mer_page_num": mer_page_num,
        "extracted_data": parsed,
        "confidence": match_info["confidence"],
        "source_page": page["page_number"],
    }


async def _llm_extract_all(classification: dict) -> Dict[int, dict]:
    """Run LLM extraction for all matched pages in parallel."""
    tasks = []
    for mer_page_num, match_info in classification["mapping"].items():
        tasks.append(_llm_extract_page(mer_page_num, match_info))

    results = await asyncio.gather(*tasks)

    extracted = {}
    for r in results:
        if r is not None:
            extracted[r["mer_page_num"]] = {
                "extracted_data": r["extracted_data"],
                "confidence": r["confidence"],
                "source_page": r["source_page"],
            }
    return extracted


# ─── DB storage ──────────────────────────────────────────────────────────────

async def _get_next_version(case_id: str) -> int:
    """Get the next version number for a case's MER result."""
    db = await get_database()
    latest = await db.mer_results.find_one(
        {"case_id": case_id},
        sort=[("version", -1)],
        projection={"version": 1},
    )
    return (latest["version"] + 1) if latest else 1


async def _store_result(result: MERResultModel) -> str:
    """Store a MER result snapshot in MongoDB. Returns the inserted ID."""
    db = await get_database()
    doc = result.model_dump()
    insert = await db.mer_results.insert_one(doc)
    return str(insert.inserted_id)


async def get_latest_result(case_id: str) -> Optional[dict]:
    """Get the latest MER result for a case."""
    db = await get_database()
    doc = await db.mer_results.find_one(
        {"case_id": case_id},
        sort=[("version", -1)],
    )
    if doc:
        doc["_id"] = str(doc["_id"])
    return doc


async def get_result_by_version(case_id: str, version: int) -> Optional[dict]:
    """Get a specific version of MER result for a case."""
    db = await get_database()
    doc = await db.mer_results.find_one(
        {"case_id": case_id, "version": version},
    )
    if doc:
        doc["_id"] = str(doc["_id"])
    return doc


async def list_result_versions(case_id: str) -> List[dict]:
    """List all result versions for a case (metadata only)."""
    db = await get_database()
    cursor = db.mer_results.find(
        {"case_id": case_id},
        projection={"version": 1, "source": 1, "created_at": 1, "_id": 1},
    ).sort("version", -1)

    versions = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        versions.append(doc)
    return versions


# ─── Main pipeline ───────────────────────────────────────────────────────────

async def process_mer(case_id: str, file_entries: List[dict]) -> dict:
    """
    Full MER processing pipeline with maximum parallelism:

    1. Download all files from S3              (parallel)
    2. Run Tesseract OCR on all pages          (parallel across pages & files)
    3. Classify pages (fuzzy keyword matching)  (CPU, fast)
    4. Run LLM-based OCR per matched page      (parallel)
    5. Flatten extracted data into MERFields
    6. Store versioned snapshot in MongoDB
    7. Run test verification if Page 5 is detected (async)

    Args:
        case_id: The case ID.
        file_entries: List of file entry dicts from CaseModel.documents["mer"]

    Returns:
        Complete result dict including DB id and version.
    """
    current_case_id.set(case_id)
    current_task.set("mer")
    call_counter = [0]
    current_call_count.set(call_counter)

    # ── Step 1: Download all files in parallel
    downloaded = await _download_all(file_entries)

    # ── Step 2: OCR all files in parallel (each file's pages also parallelized)
    all_pages = await _ocr_all(downloaded)

    # ── Step 3: Classify pages (CPU-bound, offloaded to thread)
    classification = await classify_pages(all_pages)

    # ── Step 4: LLM extraction in parallel
    t_llm = time.monotonic()
    extracted = await _llm_extract_all(classification)
    llm_wall = time.monotonic() - t_llm

    total_calls = call_counter[0]
    cps = total_calls / llm_wall if llm_wall > 0 else 0
    logger.info(
        "LLM_PIPELINE,case_id=%s,task=mer,matched_pages=%s,total_calls=%s,"
        "llm_wall_s=%.2f,calls_per_sec=%.2f",
        case_id, len(classification["mapping"]), total_calls, llm_wall, cps,
    )

    # ── Step 5: Build pages dict and flatten
    pages = {}
    for mer_page_num, data in extracted.items():
        pages[str(mer_page_num)] = data["extracted_data"]

    fields = flatten_all_pages(pages)

    # ── Step 6: Create and store versioned snapshot
    version = await _get_next_version(case_id)

    result = MERResultModel(
        case_id=case_id,
        version=version,
        source="llm",
        classification={
            "mapping_summary": {
                str(k): {
                    "source_page": v["source_page"],
                    "confidence": v["confidence"],
                }
                for k, v in extracted.items()
            },
            "unmatched_pages": [
                {"page_number": p["page_number"], "ocr_text": p["text"][:200]}
                for p in classification["unmatched_pages"]
            ],
            "missing_pages": classification["missing_pages"],
            "needs_review": classification["needs_review"],
        },
        pages=pages,
        fields=fields,
    )

    doc_id = await _store_result(result)

    # ── Step 7: Extract requirements from Page 5 (if unmatched pages exist)
    # Actual verification against pathology happens later via orchestrator
    test_extraction_result = None
    if classification["unmatched_pages"]:
        try:
            from app.services.test_verification.processor import extract_requirements_for_case
            test_extraction_result = await extract_requirements_for_case(case_id, all_pages)
            logger.info(f"Test requirements extracted for case {case_id}: {test_extraction_result.get('status')}")
        except Exception as e:
            logger.warning(f"Test requirements extraction failed for case {case_id}: {e}")

    return {
        "_id": doc_id,
        "case_id": case_id,
        "version": version,
        "source": "llm",
        "extracted": extracted,
        "fields_count": len(fields),
        "classification": result.classification,
        "test_verification": test_extraction_result,
    }
