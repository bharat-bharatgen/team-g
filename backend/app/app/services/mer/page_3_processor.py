"""
Page 3 Split Processor - Processes MER Page 3 by splitting into 3 sections.

Sections:
1. Questions (top ~35%) - Y/N questions 10b, 10c, 11a-d
2. Family History (middle ~40%) - Table with Father, Mother, Brother(s), Sister(s)
3. Declaration (bottom ~25%) - Signature, Date, Place

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
from app.services.mer.prompts import page_3_questions, page_3_family, page_3_declaration

logger = logging.getLogger("mer_page3_processor")

# ─── Configuration ───────────────────────────────────────────────────────────

# Set to False to use the original single-call method
USE_SPLIT_PROCESSING = False

# Set to True to save cropped images locally for debugging
DEBUG_SAVE_CROPS = False
DEBUG_CROPS_DIR = "/tmp/mer_page3_crops"

# Fixed layout percentages (fallback if anchor detection fails)
# Section 1 (Questions): 0% - 35%
# Section 2 (Family History): 33% - 75%
# Section 3 (Declaration): 73% - 100%
SECTION_1_END_PERCENT = 0.35
SECTION_2_START_PERCENT = 0.33
SECTION_2_END_PERCENT = 0.75
SECTION_3_START_PERCENT = 0.73

# Safety margin for cropping
SAFETY_MARGIN_PERCENT = 0.02  # 2% padding

# Multiple anchor texts for each section boundary (for robustness)
SECTION_2_ANCHORS = [
    "Family History",
    "12)",
    "12.",
    "Relationship",
    "Father",
]

SECTION_3_ANCHORS = [
    "Declaration",
    "Signature of Life",
    "Signature of life assured",
    "Date:",
    "Place:",
]


# ─── Debug Helpers ───────────────────────────────────────────────────────────

def _save_debug_image(image_bytes: bytes, name: str) -> Optional[str]:
    """Save cropped image to disk for debugging."""
    if not DEBUG_SAVE_CROPS:
        return None
    
    try:
        os.makedirs(DEBUG_CROPS_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"page3_{name}_{timestamp}.png"
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
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))
        img_height = image.height
        
        # Get text with bounding boxes
        ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        
        # Find section 2 start (Family History)
        section_2_y = _find_anchor_position(ocr_data, SECTION_2_ANCHORS)
        if section_2_y:
            logger.info(f"Found Section 2 (Family History) anchor at Y={section_2_y}")
        
        # Find section 3 start (Declaration)
        section_3_y = _find_anchor_position(ocr_data, SECTION_3_ANCHORS)
        if section_3_y:
            logger.info(f"Found Section 3 (Declaration) anchor at Y={section_3_y}")
        
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


def crop_questions_section(image_bytes: bytes) -> bytes:
    """Crop image to show only the questions section (10b, 10c, 11a-d)."""
    section_1_end, _, _, _, img_height, _ = _get_section_boundaries(image_bytes)
    margin = int(img_height * SAFETY_MARGIN_PERCENT)
    return _crop_section(image_bytes, 0, section_1_end + margin)


def crop_family_section(image_bytes: bytes) -> bytes:
    """Crop image to show only the family history table."""
    _, section_2_start, section_2_end, _, img_height, _ = _get_section_boundaries(image_bytes)
    margin = int(img_height * SAFETY_MARGIN_PERCENT)
    return _crop_section(image_bytes, section_2_start, section_2_end + margin)


def crop_declaration_section(image_bytes: bytes) -> bytes:
    """Crop image to show only the declaration section."""
    _, _, _, section_3_start, img_height, _ = _get_section_boundaries(image_bytes)
    margin = int(img_height * SAFETY_MARGIN_PERCENT)
    return _crop_section(image_bytes, section_3_start, img_height)


# ─── LLM Extraction ──────────────────────────────────────────────────────────

async def _extract_questions(image_bytes: bytes) -> dict:
    """Extract Y/N questions (10b, 10c, 11a-d) from cropped section."""
    cropped = crop_questions_section(image_bytes)
    _save_debug_image(cropped, "questions")
    
    response = await llm_client.call(
        system_prompt=page_3_questions.SYSTEM_PROMPT,
        user_prompt=page_3_questions.USER_PROMPT,
        config=page_3_questions.CONFIG,
        images=[cropped],
    )
    
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        logger.warning("Failed to parse questions extraction response as JSON")
        return {"questions": {}, "raw_response": response}


async def _extract_family(image_bytes: bytes) -> dict:
    """Extract family history table from cropped section."""
    cropped = crop_family_section(image_bytes)
    _save_debug_image(cropped, "family")
    
    response = await llm_client.call(
        system_prompt=page_3_family.SYSTEM_PROMPT,
        user_prompt=page_3_family.USER_PROMPT,
        config=page_3_family.CONFIG,
        images=[cropped],
    )
    
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        logger.warning("Failed to parse family extraction response as JSON")
        return {"family_history": {}, "raw_response": response}


async def _extract_declaration(image_bytes: bytes) -> dict:
    """Extract declaration section from cropped section."""
    cropped = crop_declaration_section(image_bytes)
    _save_debug_image(cropped, "declaration")
    
    response = await llm_client.call(
        system_prompt=page_3_declaration.SYSTEM_PROMPT,
        user_prompt=page_3_declaration.USER_PROMPT,
        config=page_3_declaration.CONFIG,
        images=[cropped],
    )
    
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        logger.warning("Failed to parse declaration extraction response as JSON")
        return {"declaration": {}, "raw_response": response}


# ─── Full Page Fallback ──────────────────────────────────────────────────────

async def _extract_full_page(image_bytes: bytes) -> dict:
    """
    Fallback: Extract from full page using original prompt.
    Used when no anchors are found to ensure no data is lost.
    """
    from app.services.mer.prompts import page_3 as page_3_original
    
    logger.info("Fallback: Processing Page 3 with full page (no anchors found)")
    _save_debug_image(image_bytes, "fullpage_fallback")
    
    response = await llm_client.call(
        system_prompt=page_3_original.SYSTEM_PROMPT,
        user_prompt=page_3_original.USER_PROMPT,
        config=page_3_original.CONFIG,
        images=[image_bytes],
    )
    
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return {"raw_response": response}


# ─── Main Processing Function ────────────────────────────────────────────────

async def extract_page_3_split(image_bytes: bytes) -> dict:
    """
    Extract Page 3 data using split processing (3 sections).
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
    
    logger.info("Processing Page 3 with split method (questions + family + declaration)")
    _save_debug_image(image_bytes, "original")
    
    # Run all 3 extractions in parallel
    questions_result, family_result, declaration_result = await asyncio.gather(
        _extract_questions(image_bytes),
        _extract_family(image_bytes),
        _extract_declaration(image_bytes),
    )
    
    # Merge results - need to restructure family_history into questions.12
    questions_data = questions_result.get("questions", {})
    family_data = family_result.get("family_history", {})
    
    # Add family history under "12) Family History" in questions
    questions_data["12) Family History"] = family_data
    
    combined = {
        "page_number": 3,
        "questions": questions_data,
        "declaration": declaration_result.get("declaration", {}),
    }
    
    # Preserve any raw responses for debugging
    if "raw_response" in questions_result:
        combined["_questions_raw"] = questions_result["raw_response"]
    if "raw_response" in family_result:
        combined["_family_raw"] = family_result["raw_response"]
    if "raw_response" in declaration_result:
        combined["_declaration_raw"] = declaration_result["raw_response"]
    
    return combined


async def extract_page_3(image_bytes: bytes, use_split: Optional[bool] = None) -> dict:
    """
    Extract Page 3 data, optionally using split processing.
    
    Args:
        image_bytes: The full page image bytes
        use_split: Override the USE_SPLIT_PROCESSING config.
                   If None, uses the module-level config.
    """
    should_split = use_split if use_split is not None else USE_SPLIT_PROCESSING
    
    if should_split:
        return await extract_page_3_split(image_bytes)
    else:
        # Use original single-call method
        from app.services.mer.prompts import page_3 as page_3_original
        
        logger.info("Processing Page 3 with original single-call method")
        
        response = await llm_client.call(
            system_prompt=page_3_original.SYSTEM_PROMPT,
            user_prompt=page_3_original.USER_PROMPT,
            config=page_3_original.CONFIG,
            images=[image_bytes],
        )
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {"raw_response": response}
