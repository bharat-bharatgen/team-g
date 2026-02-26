"""
Page 1 Split Processor - Processes MER Page 1 by splitting into header and questions sections.

This improves extraction accuracy by:
1. Using Tesseract OCR with multiple anchor texts to detect section boundaries
2. Cropping image into header and questions sections
3. Making two parallel LLM calls with focused prompts
4. Merging results into the expected output format
5. Falling back to full page if no anchors found
"""

import io
import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Optional, Tuple

import pytesseract
from PIL import Image

from app.services.llm import client as llm_client
from app.services.mer.prompts import page_1_header, page_1_questions

logger = logging.getLogger("mer_page1_processor")

# ─── Configuration ───────────────────────────────────────────────────────────

# Set to False to use the original single-call method
USE_SPLIT_PROCESSING = True

# Set to True to save cropped images locally for debugging
DEBUG_SAVE_CROPS = False
DEBUG_CROPS_DIR = "/tmp/mer_page1_crops"

# Fixed layout percentages (fallback if anchor detection fails)
# These are approximate positions based on the standard MER form layout
HEADER_END_PERCENT = 0.22  # Header ends at ~22% from top
SAFETY_MARGIN_PERCENT = 0.03  # 3% padding for safety

# Multiple anchor texts for section boundary detection (for robustness)
SECTION_ANCHORS = [
    "PART I",
    "PART-I",
    "PART 1",
    "Questions to be put",
    "Medical Examiner",
]


# ─── Debug Helpers ───────────────────────────────────────────────────────────

def _save_debug_image(image_bytes: bytes, name: str) -> Optional[str]:
    """
    Save cropped image to disk for debugging.
    
    Args:
        image_bytes: The image bytes to save
        name: Identifier for the image (e.g., "header", "questions")
        
    Returns:
        Path to saved file, or None if debug is disabled
    """
    if not DEBUG_SAVE_CROPS:
        return None
    
    try:
        # Ensure directory exists
        os.makedirs(DEBUG_CROPS_DIR, exist_ok=True)
        
        # Generate timestamped filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"page1_{name}_{timestamp}.png"
        filepath = os.path.join(DEBUG_CROPS_DIR, filename)
        
        # Save image
        with open(filepath, "wb") as f:
            f.write(image_bytes)
        
        logger.info(f"Debug: Saved {name} crop to {filepath}")
        return filepath
        
    except Exception as e:
        logger.warning(f"Failed to save debug image: {e}")
        return None


# ─── Multi-Anchor Section Boundary Detection ─────────────────────────────────

def _find_anchor_position(ocr_data: dict, anchors: list) -> Optional[int]:
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
            
            # Single word anchor or partial match
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
            
            # Also check for "PART" followed by "I" or "1" pattern
            if text_upper == 'PART' and i + 1 < len(text_list):
                next_text = str(text_list[i + 1]).upper().strip()
                if next_text in ('I', '1', '-I', '-1'):
                    return ocr_data['top'][i]
    
    return None


def _detect_section_boundary(image_bytes: bytes) -> Tuple[Optional[int], int]:
    """
    Use Tesseract OCR to find section boundary using multiple anchor texts.
    
    Returns:
        Tuple of (section_y, image_height) - section_y is None if not found.
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))
        img_height = image.height
        
        # Get text with bounding boxes
        ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        
        # Find section boundary using multiple anchors
        section_y = _find_anchor_position(ocr_data, SECTION_ANCHORS)
        
        if section_y:
            logger.info(f"Found section anchor at Y={section_y}")
        
        return section_y, img_height
        
    except Exception as e:
        logger.warning(f"Section boundary detection failed: {e}")
        image = Image.open(io.BytesIO(image_bytes))
        return None, image.height


def _get_section_boundaries(image_bytes: bytes) -> Tuple[int, int, int, bool]:
    """
    Get the Y coordinates for header and questions sections.
    
    Returns:
        Tuple of (header_end_y, questions_start_y, image_height, anchor_found)
    """
    section_y, img_height = _detect_section_boundary(image_bytes)
    
    anchor_found = section_y is not None
    safety_pixels = int(img_height * SAFETY_MARGIN_PERCENT)
    
    if anchor_found:
        logger.info(f"Detected section boundary at Y={section_y} (image height={img_height})")
        header_end = section_y - safety_pixels
        questions_start = section_y - safety_pixels
    else:
        # Fallback to fixed percentages (but caller should use full page instead)
        logger.info(f"No anchor found, using fixed percentages (image height={img_height})")
        header_end = int(img_height * HEADER_END_PERCENT)
        questions_start = int(img_height * (HEADER_END_PERCENT - SAFETY_MARGIN_PERCENT))
    
    return header_end, questions_start, img_height, anchor_found


# ─── Image Cropping ──────────────────────────────────────────────────────────

def _crop_section(image_bytes: bytes, y_start: int, y_end: int) -> bytes:
    """
    Crop the image to a specific vertical section.
    
    Args:
        image_bytes: Original image bytes
        y_start: Top Y coordinate
        y_end: Bottom Y coordinate
        
    Returns:
        Cropped image as PNG bytes
    """
    image = Image.open(io.BytesIO(image_bytes))
    
    # Clamp values to image bounds
    y_start = max(0, y_start)
    y_end = min(image.height, y_end)
    
    # Crop: (left, upper, right, lower)
    cropped = image.crop((0, y_start, image.width, y_end))
    
    buf = io.BytesIO()
    cropped.save(buf, format='PNG')
    return buf.getvalue()


def crop_header_section(image_bytes: bytes) -> bytes:
    """Crop image to show only the header section (top portion)."""
    header_end, _, img_height, _ = _get_section_boundaries(image_bytes)
    
    # Add some margin at the bottom to avoid cutting off content
    margin = int(img_height * SAFETY_MARGIN_PERCENT)
    return _crop_section(image_bytes, 0, header_end + margin)


def crop_questions_section(image_bytes: bytes) -> bytes:
    """Crop image to show only the questions section (PART I onwards)."""
    _, questions_start, img_height, _ = _get_section_boundaries(image_bytes)
    
    # Include from questions start to near bottom (leave out stamp area)
    bottom_margin = int(img_height * 0.05)  # Leave 5% at bottom for stamps
    return _crop_section(image_bytes, questions_start, img_height - bottom_margin)


# ─── LLM Extraction ──────────────────────────────────────────────────────────

async def _extract_header(image_bytes: bytes) -> dict:
    """Extract header fields from cropped header image."""
    cropped = crop_header_section(image_bytes)
    
    # Save debug image if enabled
    _save_debug_image(cropped, "header")
    
    response = await llm_client.call(
        system_prompt=page_1_header.SYSTEM_PROMPT,
        user_prompt=page_1_header.USER_PROMPT,
        config=page_1_header.CONFIG,
        images=[cropped],
    )
    
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        logger.warning("Failed to parse header extraction response as JSON")
        return {"header": {}, "raw_response": response}


async def _extract_questions(image_bytes: bytes) -> dict:
    """Extract question answers from cropped questions image."""
    cropped = crop_questions_section(image_bytes)
    
    # Save debug image if enabled
    _save_debug_image(cropped, "questions")
    
    response = await llm_client.call(
        system_prompt=page_1_questions.SYSTEM_PROMPT,
        user_prompt=page_1_questions.USER_PROMPT,
        config=page_1_questions.CONFIG,
        images=[cropped],
    )
    
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        logger.warning("Failed to parse questions extraction response as JSON")
        return {"questions": {}, "raw_response": response}


# ─── Full Page Fallback ──────────────────────────────────────────────────────

async def _extract_full_page(image_bytes: bytes) -> dict:
    """
    Fallback: Extract from full page using original prompt.
    Used when no anchors are found to ensure no data is lost.
    """
    from app.services.mer.prompts import page_1 as page_1_original
    
    logger.info("Fallback: Processing Page 1 with full page (no anchors found)")
    _save_debug_image(image_bytes, "fullpage_fallback")
    
    response = await llm_client.call(
        system_prompt=page_1_original.SYSTEM_PROMPT,
        user_prompt=page_1_original.USER_PROMPT,
        config=page_1_original.CONFIG,
        images=[image_bytes],
    )
    
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return {"raw_response": response}


# ─── Main Processing Function ────────────────────────────────────────────────

async def extract_page_1_split(image_bytes: bytes) -> dict:
    """
    Extract Page 1 data using split processing (header + questions separately).
    Falls back to full page if no anchors are found.
    
    Args:
        image_bytes: The full page image bytes
        
    Returns:
        Combined dict with both "header" and "questions" keys
    """
    # Check if we can find any anchors
    section_y, img_height = _detect_section_boundary(image_bytes)
    
    # If no anchor found, use full page to avoid losing data
    if section_y is None:
        logger.warning("No section anchor found - using full page fallback")
        return await _extract_full_page(image_bytes)
    
    logger.info("Processing Page 1 with split method (header + questions)")
    
    # Save original image if debug enabled
    _save_debug_image(image_bytes, "original")
    
    # Run both extractions in parallel
    header_result, questions_result = await asyncio.gather(
        _extract_header(image_bytes),
        _extract_questions(image_bytes),
    )
    
    # Merge results
    combined = {
        "header": header_result.get("header", {}),
        "questions": questions_result.get("questions", {}),
    }
    
    # Preserve any raw responses for debugging
    if "raw_response" in header_result:
        combined["_header_raw"] = header_result["raw_response"]
    if "raw_response" in questions_result:
        combined["_questions_raw"] = questions_result["raw_response"]
    
    return combined


async def extract_page_1(image_bytes: bytes, use_split: Optional[bool] = None) -> dict:
    """
    Extract Page 1 data, optionally using split processing.
    
    Args:
        image_bytes: The full page image bytes
        use_split: Override the USE_SPLIT_PROCESSING config. 
                   If None, uses the module-level config.
                   
    Returns:
        Extracted data dict with "header" and "questions" keys
    """
    should_split = use_split if use_split is not None else USE_SPLIT_PROCESSING
    
    if should_split:
        return await extract_page_1_split(image_bytes)
    else:
        # Fall back to original method - import here to avoid circular imports
        from app.services.mer.prompts import page_1 as page_1_original
        
        logger.info("Processing Page 1 with original single-call method")
        
        response = await llm_client.call(
            system_prompt=page_1_original.SYSTEM_PROMPT,
            user_prompt=page_1_original.USER_PROMPT,
            config=page_1_original.CONFIG,
            images=[image_bytes],
        )
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {"raw_response": response}
