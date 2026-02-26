"""
Pathology processing pipeline.

Step 1: Download files → convert PDF to images
Step 2: LLM vision OCR per page (parallel) → raw text per page
Step 3: LLM extraction per page (parallel) → tests array per page
Step 4: Merge extracted data (attach source_page to each test)
Step 5: Flatten to PathologyField list
Step 6: Store versioned snapshot in MongoDB
"""

import json
import asyncio
from typing import Any, Dict, List, Optional

from app.services.storage import s3_service
from app.services.common.tesseract_ocr import pdf_to_page_images
from app.services.llm import client as llm_client
from app.services.pathology.prompts import ocr as ocr_prompt
from app.services.pathology.prompts import extract as extract_prompt
from app.services.pathology.flattener import flatten_standardized
from app.models.pathology_result import PathologyResultModel
from app.dependencies import get_database


# ─── S3 download (parallel) ─────────────────────────────────────────────────

async def _download_file(s3_key: str) -> bytes:
    """Download a single file from S3."""
    return await s3_service.download_file(s3_key)


async def _download_all(file_entries: List[dict]) -> List[dict]:
    """Download all files from S3 in parallel."""
    tasks = [_download_file(e["s3_key"]) for e in file_entries]
    results = await asyncio.gather(*tasks)
    return [
        {"file_bytes": fb, "content_type": e["content_type"]}
        for fb, e in zip(results, file_entries)
    ]


# ─── File → page images ─────────────────────────────────────────────────────

def _files_to_page_images(downloaded: List[dict]) -> List[dict]:
    """
    Convert all downloaded files to a flat list of page images.
    PDFs are split into pages; single images become 1-page entries.

    Returns:
        [{"page_number": int, "image_bytes": bytes}, ...]
    """
    all_pages = []
    page_counter = 1

    for d in downloaded:
        if d["content_type"] == "application/pdf":
            pages = pdf_to_page_images(d["file_bytes"])
            for p in pages:
                p["page_number"] = page_counter
                all_pages.append(p)
                page_counter += 1
        else:
            all_pages.append({
                "page_number": page_counter,
                "image_bytes": d["file_bytes"],
            })
            page_counter += 1

    return all_pages


# ─── Step 2: LLM Vision OCR per page (parallel) ─────────────────────────────

async def _ocr_page(page: dict) -> dict:
    """Run LLM vision OCR on a single page image. Returns raw text."""
    page_num = page["page_number"]
    user_prompt = ocr_prompt.build_user_prompt(page_num)

    llm_response = await llm_client.call(
        system_prompt=ocr_prompt.SYSTEM_PROMPT,
        user_prompt=user_prompt,
        config=ocr_prompt.CONFIG,
        images=[page["image_bytes"]],
    )

    return {"page_number": page_num, "text": llm_response}


async def _ocr_all_pages(pages: List[dict]) -> Dict[str, str]:
    """Run LLM vision OCR on all pages in parallel. Returns {page_num_str: text}."""
    tasks = [_ocr_page(p) for p in pages]
    results = await asyncio.gather(*tasks)

    pages_data = {}
    for r in results:
        pages_data[str(r["page_number"])] = r["text"]

    return pages_data


# ─── Step 3: LLM extraction per page (parallel) ─────────────────────────────

async def _extract_page(page_num: int, text: str) -> Dict[str, Any]:
    """
    Run LLM extraction on a single page's OCR text.

    Args:
        page_num: The page number
        text: The OCR text for this page

    Returns:
        {"page_number": int, "result": parsed_json}
    """
    if not text or not text.strip():
        return {"page_number": page_num, "result": {"tests": []}}

    user_prompt = extract_prompt.build_user_prompt(text)

    llm_response = await llm_client.call(
        system_prompt=extract_prompt.SYSTEM_PROMPT,
        user_prompt=user_prompt,
        config=extract_prompt.CONFIG,
        images=None,
    )

    try:
        parsed = json.loads(llm_response)
    except json.JSONDecodeError:
        parsed = {"tests": [], "raw_response": llm_response}

    return {"page_number": page_num, "result": parsed}


async def _extract_all_pages(pages_data: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    Run LLM extraction on all pages in parallel.

    Args:
        pages_data: {page_num_str: ocr_text}

    Returns:
        List of {"page_number": int, "result": parsed_json}
    """
    tasks = [
        _extract_page(int(page_num_str), text)
        for page_num_str, text in pages_data.items()
    ]
    results = await asyncio.gather(*tasks)
    return list(results)


def _merge_extracted_data(page_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Merge extracted data from all pages and attach source_page to each test.

    Args:
        page_results: List of {"page_number": int, "result": {"tests": [...]}}

    Returns:
        Combined {"tests": [...]} with source_page attached to each test
    """
    # Sort by page number to maintain order
    sorted_results = sorted(page_results, key=lambda x: x["page_number"])

    all_tests = []
    for page_result in sorted_results:
        page_num = page_result["page_number"]
        result = page_result.get("result", {})
        tests = result.get("tests", [])

        for test in tests:
            # Attach source_page to each test
            test["source_page"] = page_num
            all_tests.append(test)

    return {"tests": all_tests}


# ─── DB storage ──────────────────────────────────────────────────────────────

async def _get_next_version(case_id: str) -> int:
    """Get the next version number for a case's pathology result."""
    db = await get_database()
    latest = await db.pathology_results.find_one(
        {"case_id": case_id},
        sort=[("version", -1)],
        projection={"version": 1},
    )
    return (latest["version"] + 1) if latest else 1


async def _store_result(result: PathologyResultModel) -> str:
    """Store a pathology result snapshot in MongoDB. Returns the inserted ID."""
    db = await get_database()
    doc = result.model_dump()
    insert = await db.pathology_results.insert_one(doc)
    return str(insert.inserted_id)


async def get_latest_result(case_id: str) -> Optional[dict]:
    """Get the latest pathology result for a case."""
    db = await get_database()
    doc = await db.pathology_results.find_one(
        {"case_id": case_id},
        sort=[("version", -1)],
    )
    if doc:
        doc["_id"] = str(doc["_id"])
    return doc


async def get_result_by_version(case_id: str, version: int) -> Optional[dict]:
    """Get a specific version of pathology result for a case."""
    db = await get_database()
    doc = await db.pathology_results.find_one(
        {"case_id": case_id, "version": version},
    )
    if doc:
        doc["_id"] = str(doc["_id"])
    return doc


async def list_result_versions(case_id: str) -> List[dict]:
    """List all result versions for a case (metadata only)."""
    db = await get_database()
    cursor = db.pathology_results.find(
        {"case_id": case_id},
        projection={"version": 1, "source": 1, "created_at": 1, "_id": 1},
    ).sort("version", -1)

    versions = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        versions.append(doc)
    return versions


# ─── Main pipeline ───────────────────────────────────────────────────────────

async def process_pathology(case_id: str, file_entries: List[dict]) -> dict:
    """
    Full pathology processing pipeline:

    1. Download all files from S3              (parallel)
    2. Convert to page images
    3. LLM vision OCR per page                 (parallel)
    4. LLM extraction per page                 (parallel)
    5. Merge extracted data (attach source_page)
    6. Flatten to PathologyFields
    7. Store versioned snapshot in MongoDB

    Args:
        case_id: The case ID.
        file_entries: List of file entry dicts from CaseModel.documents["pathology"]

    Returns:
        Result summary dict.
    """
    # ── Step 1: Download all files in parallel
    downloaded = await _download_all(file_entries)

    # ── Step 2: Convert to page images (synchronous - PyMuPDF not thread-safe)
    page_images = _files_to_page_images(downloaded)

    # ── Step 3: LLM vision OCR per page (parallel)
    pages_data = await _ocr_all_pages(page_images)

    # ── Step 4: LLM extraction per page (parallel)
    page_results = await _extract_all_pages(pages_data)

    # ── Step 5: Merge extracted data (attach source_page to each test)
    standardized = _merge_extracted_data(page_results)

    # ── Step 6: Flatten
    fields = flatten_standardized(standardized)

    # ── Step 7: Store
    version = await _get_next_version(case_id)

    result = PathologyResultModel(
        case_id=case_id,
        version=version,
        source="llm",
        pages=pages_data,
        patient_info={},
        lab_info={},
        report_info={},
        standardized=standardized,
        fields=fields,
    )

    doc_id = await _store_result(result)

    # Count how many standard params have values
    filled_count = sum(
        1 for f in fields
        if f.is_standard and f.value is not None
    )
    unmatched_count = sum(1 for f in fields if not f.is_standard)

    return {
        "_id": doc_id,
        "case_id": case_id,
        "version": version,
        "source": "llm",
        "total_pages": len(pages_data),
        "filled_params": filled_count,
        "unmatched_tests": unmatched_count,
        "fields_count": len(fields),
    }
