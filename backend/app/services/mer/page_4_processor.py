"""
Page 4 Split Processor - Processes MER Page 4 by splitting into 3 sections.

Sections:
1. Physical Measurements + Blood Pressure (top ~30%)
2. Systemic Examination - Y/N questions (middle ~45%)
3. Certificate - Doctor details (bottom ~25%)

This improves extraction accuracy by:
1. Using Tesseract OCR with multiple anchor texts to detect section boundaries
2. Cropping image into 3 focused sections
3. Making 3 parallel LLM calls with specialized prompts
4. Merging results into the expected output format
5. Falling back to full page if no anchors found
"""

import io
import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Optional, Tuple, List

import pytesseract
from PIL import Image

from app.services.llm import client as llm_client
from app.services.llm.context import current_operation
from app.services.mer.prompts import page_4_physical, page_4_systemic, page_4_certificate

logger = logging.getLogger("mer_page4_processor")

# ─── Configuration ───────────────────────────────────────────────────────────

# Set to False to use the original single-call method
USE_SPLIT_PROCESSING = False

# Set to True to save cropped images locally for debugging
DEBUG_SAVE_CROPS = False
DEBUG_CROPS_DIR = "/tmp/mer_page4_crops"

# Fixed layout percentages (fallback if anchor detection fails)
# Section 1 (Physical + BP): 0% - 30%
# Section 2 (Systemic): 28% - 75%
# Section 3 (Certificate): 73% - 100%
SECTION_1_END_PERCENT = 0.30
SECTION_2_START_PERCENT = 0.28
SECTION_2_END_PERCENT = 0.75
SECTION_3_START_PERCENT = 0.73

# Safety margin for cropping
SAFETY_MARGIN_PERCENT = 0.02  # 2% padding

# Multiple anchor texts for each section boundary (for robustness)
SECTION_2_ANCHORS = [
    "Systemic Examination",
    "B. Systemic",
    "B.",  # Just "B." alone as fallback
    "evidence of abnormality",
]

SECTION_3_ANCHORS = [
    "CERTIFICATE",
    "Certificate",
    "I hereby certify",
    "Name of Doctor",
]


# ─── Debug Helpers ───────────────────────────────────────────────────────────

def _save_debug_image(image_bytes: bytes, name: str) -> Optional[str]:
    """Save cropped image to disk for debugging."""
    if not DEBUG_SAVE_CROPS:
        return None
    
    try:
        os.makedirs(DEBUG_CROPS_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"page4_{name}_{timestamp}.png"
        filepath = os.path.join(DEBUG_CROPS_DIR, filename)
        
        with open(filepath, "wb") as f:
            f.write(image_bytes)
        
        logger.info(f"Debug: Saved {name} crop to {filepath}")
        return filepath
        
    except Exception as e:
        logger.warning(f"Failed to save debug image: {e}")
        return None


# ─── Multi-Anchor Section Boundary Detection ─────────────────────────────────

def _find_anchor_position(ocr_data: dict, anchors: List[str]) -> Optional[int]:
    """
    Find the Y position of any matching anchor text.
    Tries each anchor in order, returns first match.
    
    Args:
        ocr_data: Tesseract OCR data with bounding boxes
        anchors: List of anchor texts to search for (in priority order)
        
    Returns:
        Y coordinate of the first matching anchor, or None if not found
    """
    text_list = ocr_data['text']
    
    for anchor in anchors:
        anchor_upper = anchor.upper()
        anchor_words = anchor_upper.split()
        
        for i, text in enumerate(text_list):
            text_upper = str(text).upper().strip()
            
            # Single word anchor
            if len(anchor_words) == 1:
                if anchor_upper in text_upper or text_upper == anchor_upper:
                    return ocr_data['top'][i]
            
            # Multi-word anchor - check if first word matches and subsequent words follow
            elif text_upper == anchor_words[0]:
                # Check if remaining words follow
                match = True
                for j, word in enumerate(anchor_words[1:], start=1):
                    if i + j < len(text_list):
                        next_text = str(text_list[i + j]).upper().strip()
                        if next_text != word:
                            match = False
                            break
                    else:
                        match = False
                        break
                
                if match:
                    return ocr_data['top'][i]
    
    return None


def _detect_section_boundaries(image_bytes: bytes) -> Tuple[Optional[int], Optional[int], int]:
    """
    Use Tesseract OCR to find section boundaries using multiple anchor texts.
    
    Returns:
        Tuple of (section_2_start_y, section_3_start_y, image_height)
        Any position may be None if anchor not found.
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))
        img_height = image.height
        
        # Get text with bounding boxes
        ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        
        # Find section 2 start (Systemic Examination)
        section_2_y = _find_anchor_position(ocr_data, SECTION_2_ANCHORS)
        if section_2_y:
            logger.info(f"Found Section 2 anchor at Y={section_2_y}")
        
        # Find section 3 start (Certificate)
        section_3_y = _find_anchor_position(ocr_data, SECTION_3_ANCHORS)
        if section_3_y:
            logger.info(f"Found Section 3 anchor at Y={section_3_y}")
        
        return section_2_y, section_3_y, img_height
        
    except Exception as e:
        logger.warning(f"Section boundary detection failed: {e}")
        image = Image.open(io.BytesIO(image_bytes))
        return None, None, image.height


def _get_section_boundaries(image_bytes: bytes) -> Tuple[int, int, int, int, int, bool]:
    """
    Get Y coordinates for all 3 sections with fallback to fixed percentages.
    
    Returns:
        Tuple of (section_1_end, section_2_start, section_2_end, section_3_start, img_height, anchors_found)
    """
    section_2_y, section_3_y, img_height = _detect_section_boundaries(image_bytes)
    
    safety = int(img_height * SAFETY_MARGIN_PERCENT)
    anchors_found = section_2_y is not None or section_3_y is not None
    
    # Section 1 end / Section 2 start
    if section_2_y is not None:
        section_1_end = section_2_y - safety
        section_2_start = section_2_y - safety
    else:
        section_1_end = int(img_height * SECTION_1_END_PERCENT)
        section_2_start = int(img_height * SECTION_2_START_PERCENT)
        logger.info("Using fixed percentage for Section 1/2 boundary")
    
    # Section 2 end / Section 3 start
    if section_3_y is not None:
        section_2_end = section_3_y - safety
        section_3_start = section_3_y - safety
    else:
        section_2_end = int(img_height * SECTION_2_END_PERCENT)
        section_3_start = int(img_height * SECTION_3_START_PERCENT)
        logger.info("Using fixed percentage for Section 2/3 boundary")
    
    return section_1_end, section_2_start, section_2_end, section_3_start, img_height, anchors_found


# ─── Image Cropping ──────────────────────────────────────────────────────────

def _crop_section(image_bytes: bytes, y_start: int, y_end: int) -> bytes:
    """Crop image to a specific vertical section."""
    image = Image.open(io.BytesIO(image_bytes))
    
    # Clamp values to image bounds
    y_start = max(0, y_start)
    y_end = min(image.height, y_end)
    
    cropped = image.crop((0, y_start, image.width, y_end))
    
    buf = io.BytesIO()
    cropped.save(buf, format='PNG')
    return buf.getvalue()


def crop_physical_section(image_bytes: bytes) -> bytes:
    """Crop image to show only the physical measurements + BP section."""
    section_1_end, _, _, _, img_height, _ = _get_section_boundaries(image_bytes)
    margin = int(img_height * SAFETY_MARGIN_PERCENT)
    return _crop_section(image_bytes, 0, section_1_end + margin)


def crop_systemic_section(image_bytes: bytes) -> bytes:
    """Crop image to show only the systemic examination section."""
    _, section_2_start, section_2_end, _, img_height, _ = _get_section_boundaries(image_bytes)
    margin = int(img_height * SAFETY_MARGIN_PERCENT)
    return _crop_section(image_bytes, section_2_start, section_2_end + margin)


def crop_certificate_section(image_bytes: bytes) -> bytes:
    """Crop image to show only the certificate section."""
    _, _, _, section_3_start, img_height, _ = _get_section_boundaries(image_bytes)
    margin = int(img_height * SAFETY_MARGIN_PERCENT)
    return _crop_section(image_bytes, section_3_start, img_height)


# ─── LLM Extraction ──────────────────────────────────────────────────────────

async def _extract_physical(image_bytes: bytes) -> dict:
    """Extract physical measurements and BP from cropped section."""
    current_operation.set("physical")
    cropped = crop_physical_section(image_bytes)
    _save_debug_image(cropped, "physical")

    response = await llm_client.call(
        system_prompt=page_4_physical.SYSTEM_PROMPT,
        user_prompt=page_4_physical.USER_PROMPT,
        config=page_4_physical.CONFIG,
        images=[cropped],
    )
    
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        logger.warning("Failed to parse physical extraction response as JSON")
        return {"physical_measurement": {}, "blood_pressure": {}, "raw_response": response}


async def _extract_systemic(image_bytes: bytes) -> dict:
    """Extract systemic examination Y/N questions from cropped section."""
    current_operation.set("systemic")
    cropped = crop_systemic_section(image_bytes)
    _save_debug_image(cropped, "systemic")

    response = await llm_client.call(
        system_prompt=page_4_systemic.SYSTEM_PROMPT,
        user_prompt=page_4_systemic.USER_PROMPT,
        config=page_4_systemic.CONFIG,
        images=[cropped],
    )
    
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        logger.warning("Failed to parse systemic extraction response as JSON")
        return {"systemic_examination": {}, "raw_response": response}


async def _extract_certificate(image_bytes: bytes) -> dict:
    """Extract certificate/doctor details from cropped section."""
    current_operation.set("certificate")
    cropped = crop_certificate_section(image_bytes)
    _save_debug_image(cropped, "certificate")

    response = await llm_client.call(
        system_prompt=page_4_certificate.SYSTEM_PROMPT,
        user_prompt=page_4_certificate.USER_PROMPT,
        config=page_4_certificate.CONFIG,
        images=[cropped],
    )
    
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        logger.warning("Failed to parse certificate extraction response as JSON")
        return {"certificate": {}, "raw_response": response}


# ─── Full Page Fallback ──────────────────────────────────────────────────────

async def _extract_full_page(image_bytes: bytes) -> dict:
    """
    Fallback: Extract from full page using original prompt.
    Used when no anchors are found to ensure no data is lost.
    """
    from app.services.mer.prompts import page_4 as page_4_original

    current_operation.set("full")
    logger.info("Fallback: Processing Page 4 with full page (no anchors found)")
    _save_debug_image(image_bytes, "fullpage_fallback")

    response = await llm_client.call(
        system_prompt=page_4_original.SYSTEM_PROMPT,
        user_prompt=page_4_original.USER_PROMPT,
        config=page_4_original.CONFIG,
        images=[image_bytes],
    )
    
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return {"raw_response": response}


# ─── Main Processing Function ────────────────────────────────────────────────

async def extract_page_4_split(image_bytes: bytes) -> dict:
    """
    Extract Page 4 data using split processing (3 sections).
    Falls back to full page if anchors are missing, partial, or nonsensical.
    """
    section_2_y, section_3_y, img_height = _detect_section_boundaries(image_bytes)

    if section_2_y is None and section_3_y is None:
        logger.warning("No section anchors found - using full page fallback")
        return await _extract_full_page(image_bytes)

    if section_2_y is None or section_3_y is None:
        logger.warning(
            "Partial anchors (sec2=%s, sec3=%s) - using full page fallback",
            section_2_y, section_3_y,
        )
        return await _extract_full_page(image_bytes)

    if section_2_y >= section_3_y:
        logger.warning(
            "Anchors out of order (sec2=%s >= sec3=%s) - using full page fallback",
            section_2_y, section_3_y,
        )
        return await _extract_full_page(image_bytes)
    
    logger.info("Processing Page 4 with split method (physical + systemic + certificate)")
    _save_debug_image(image_bytes, "original")
    
    # Run all 3 extractions in parallel
    physical_result, systemic_result, certificate_result = await asyncio.gather(
        _extract_physical(image_bytes),
        _extract_systemic(image_bytes),
        _extract_certificate(image_bytes),
    )
    
    # Merge results
    combined = {
        "page_number": 4,
        "physical_measurement": physical_result.get("physical_measurement", {}),
        "blood_pressure": physical_result.get("blood_pressure", {}),
        "systemic_examination": systemic_result.get("systemic_examination", {}),
        "certificate": certificate_result.get("certificate", {}),
    }
    
    # Preserve any raw responses for debugging
    if "raw_response" in physical_result:
        combined["_physical_raw"] = physical_result["raw_response"]
    if "raw_response" in systemic_result:
        combined["_systemic_raw"] = systemic_result["raw_response"]
    if "raw_response" in certificate_result:
        combined["_certificate_raw"] = certificate_result["raw_response"]
    
    return combined


async def extract_page_4(image_bytes: bytes, use_split: Optional[bool] = None) -> dict:
    """
    Extract Page 4 data, optionally using split processing.
    
    Args:
        image_bytes: The full page image bytes
        use_split: Override the USE_SPLIT_PROCESSING config.
                   If None, uses the module-level config.
                   
    Returns:
        Extracted data dict
    """
    should_split = use_split if use_split is not None else USE_SPLIT_PROCESSING
    
    if should_split:
        return await extract_page_4_split(image_bytes)
    else:
        # Use original single-call method
        from app.services.mer.prompts import page_4 as page_4_original

        current_operation.set("full")
        logger.info("Processing Page 4 with original single-call method")

        response = await llm_client.call(
            system_prompt=page_4_original.SYSTEM_PROMPT,
            user_prompt=page_4_original.USER_PROMPT,
            config=page_4_original.CONFIG,
            images=[image_bytes],
        )
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {"raw_response": response}
