"""
Lab address extraction from pathology result.

Extracts lab address from raw OCR pages using LLM.
"""

import json
import logging
from typing import Optional, Tuple

from app.services.llm import client as llm_client
from app.services.llm.context import current_operation
from app.services.location_check.prompts import lab_address as lab_prompt

logger = logging.getLogger(__name__)


async def get_lab_address(case_id: str) -> Tuple[Optional[str], Optional[str], Optional[int]]:
    """
    Get lab address from pathology result by extracting from OCR pages.

    Process:
    1. Get latest pathology result
    2. Merge OCR text from all pages
    3. Call LLM to extract lab name/address from OCR text
    4. Return full address (for display) and pincode (for geocoding)

    Returns:
        (address, pincode, pathology_version) - address/pincode are None if not found
    """
    from app.services.pathology.processor import get_latest_result

    result = await get_latest_result(case_id)
    if not result:
        logger.warning(f"[lab_address] No pathology result found for case {case_id}")
        return None, None, None

    version = result.get("version")
    pages = result.get("pages", {})

    if not pages:
        logger.warning(f"[lab_address] Pathology result has no pages for case {case_id}")
        return None, None, version

    logger.info(f"[lab_address] Found {len(pages)} pages in pathology result for case {case_id}")

    # Merge OCR text from all pages
    all_text = _merge_pages_text(pages)
    if not all_text.strip():
        logger.warning(f"[lab_address] Merged OCR text is empty for case {case_id}")
        return None, None, version

    logger.info(f"[lab_address] Merged OCR text length: {len(all_text)} chars")

    # Extract lab address using LLM
    address, pincode = await _extract_lab_address_from_ocr(all_text)
    
    if address:
        logger.info("[lab_address] Extracted lab address (has_pincode=%s)", bool(pincode))
    else:
        logger.warning(f"[lab_address] No address extracted from OCR for case {case_id}")
    
    return address, pincode, version


def _merge_pages_text(pages: dict) -> str:
    """Merge OCR text from all pages into a single string."""
    parts = []
    # Sort by page number
    for page_num in sorted(pages.keys(), key=lambda x: int(x)):
        text = pages.get(page_num, "")
        if text and text.strip():
            parts.append(f"--- Page {page_num} ---\n{text}")
    return "\n\n".join(parts)


async def _extract_lab_address_from_ocr(ocr_text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Call LLM to extract lab address from OCR text.

    Returns:
        (full_address, pincode) - full_address for display, pincode for geocoding
    """
    try:
        current_operation.set("lab_address")
        logger.info("[lab_address] Calling LLM to extract lab address...")

        llm_response = await llm_client.call(
            system_prompt=lab_prompt.SYSTEM_PROMPT,
            user_prompt=lab_prompt.build_user_prompt(ocr_text),
            config=lab_prompt.CONFIG,
            images=None,
        )

        logger.info("[lab_address] LLM response received (len=%d)", len(llm_response) if llm_response else 0)

        parsed = json.loads(llm_response)
        lab_name = parsed.get("lab_name")
        address = parsed.get("address")
        pincode = parsed.get("pincode")

        logger.info("[lab_address] Parsed: has_lab_name=%s, has_address=%s, has_pincode=%s", bool(lab_name), bool(address), bool(pincode))

        # Build full address string for display
        parts = []
        if lab_name:
            parts.append(lab_name)
        if address:
            parts.append(address)

        full_address = ", ".join(parts) if parts else None
        
        return full_address, pincode

    except json.JSONDecodeError as e:
        logger.error("[lab_address] JSON parse error: %s", e)
        return None, None
    except Exception as e:
        logger.error(f"[lab_address] Failed to extract lab address: {e}")
        return None, None
