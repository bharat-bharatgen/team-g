"""
Page 2 Split Processor - Processes MER Page 2 by splitting into 2 sections.

Sections:
1. Questions (top ~80%) - Y/N questions 3k-3p, 4-9
2. Alcohol (bottom ~25%) - Question 10a Y/N + alcohol table (Beer/Wine/Spirit)

This improves extraction accuracy by:
1. Using Tesseract OCR with multiple anchor texts to detect section boundaries
2. Cropping image into 2 focused sections with overlap
3. Making 2 parallel LLM calls with specialized prompts
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
from app.services.mer.prompts import page_2_questions, page_2_alcohol

logger = logging.getLogger("mer_page2_processor")

# ─── Configuration ───────────────────────────────────────────────────────────

USE_SPLIT_PROCESSING = False

DEBUG_SAVE_CROPS = False
DEBUG_CROPS_DIR = "/tmp/mer_page2_crops"

# Fixed layout percentages (fallback if anchor detection fails)
# Section 1 (Questions): 0% - 82%
# Section 2 (Alcohol):   78% - 100%
# ~4% overlap around the boundary
SECTION_1_END_PERCENT = 0.82
SECTION_2_START_PERCENT = 0.78

SAFETY_MARGIN_PERCENT = 0.02  # 2% padding

# Anchor texts to detect the alcohol section boundary
ALCOHOL_SECTION_ANCHORS = [
    "Habits",
    "10)",
    "10.",
    "consume alcohol",
    "Type of Alcohol",
    "Quantity",
    "Beer",
]


# ─── Debug Helpers ───────────────────────────────────────────────────────────

def _save_debug_image(image_bytes: bytes, name: str) -> Optional[str]:
    """Save cropped image to disk for debugging."""
    if not DEBUG_SAVE_CROPS:
        return None

    try:
        os.makedirs(DEBUG_CROPS_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"page2_{name}_{timestamp}.png"
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

            if len(anchor_words) == 1:
                if anchor_upper in text_upper or text_upper == anchor_upper:
                    return ocr_data['top'][i]
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


def _detect_section_boundary(image_bytes: bytes) -> Tuple[Optional[int], int]:
    """
    Use Tesseract OCR to find the alcohol section boundary.

    Returns:
        Tuple of (alcohol_section_start_y, image_height)
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))
        img_height = image.height

        ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

        alcohol_y = _find_anchor_position(ocr_data, ALCOHOL_SECTION_ANCHORS)
        if alcohol_y:
            logger.info(f"Found Alcohol section anchor at Y={alcohol_y}")

        return alcohol_y, img_height

    except Exception as e:
        logger.warning(f"Section boundary detection failed: {e}")
        image = Image.open(io.BytesIO(image_bytes))
        return None, image.height


def _get_section_boundaries(image_bytes: bytes) -> Tuple[int, int, int, bool]:
    """
    Get Y coordinates for both sections with fallback to fixed percentages.

    Returns:
        Tuple of (questions_end_y, alcohol_start_y, img_height, anchor_found)
    """
    alcohol_y, img_height = _detect_section_boundary(image_bytes)

    safety = int(img_height * SAFETY_MARGIN_PERCENT)
    anchor_found = alcohol_y is not None

    if alcohol_y is not None:
        questions_end_y = alcohol_y + safety
        alcohol_start_y = alcohol_y - safety
    else:
        questions_end_y = int(img_height * SECTION_1_END_PERCENT)
        alcohol_start_y = int(img_height * SECTION_2_START_PERCENT)
        logger.info("Using fixed percentage for Questions/Alcohol boundary")

    return questions_end_y, alcohol_start_y, img_height, anchor_found


# ─── Image Cropping ──────────────────────────────────────────────────────────

def _crop_section(image_bytes: bytes, y_start: int, y_end: int) -> bytes:
    """Crop image to a specific vertical section."""
    image = Image.open(io.BytesIO(image_bytes))

    y_start = max(0, y_start)
    y_end = min(image.height, y_end)

    cropped = image.crop((0, y_start, image.width, y_end))

    buf = io.BytesIO()
    cropped.save(buf, format='PNG')
    return buf.getvalue()


def crop_questions_section(image_bytes: bytes) -> bytes:
    """Crop image to show only the questions section (Q3k through Q9)."""
    questions_end_y, _, img_height, _ = _get_section_boundaries(image_bytes)
    return _crop_section(image_bytes, 0, questions_end_y)


def crop_alcohol_section(image_bytes: bytes) -> bytes:
    """Crop image to show only the alcohol section (Q10a + table)."""
    _, alcohol_start_y, img_height, _ = _get_section_boundaries(image_bytes)
    return _crop_section(image_bytes, alcohol_start_y, img_height)


# ─── LLM Extraction ──────────────────────────────────────────────────────────

async def _extract_questions(image_bytes: bytes) -> dict:
    """Extract Y/N questions (3k through 9) from cropped section."""
    current_operation.set("questions")
    cropped = crop_questions_section(image_bytes)
    _save_debug_image(cropped, "questions")

    response = await llm_client.call(
        system_prompt=page_2_questions.SYSTEM_PROMPT,
        user_prompt=page_2_questions.USER_PROMPT,
        config=page_2_questions.CONFIG,
        images=[cropped],
    )

    try:
        return json.loads(response)
    except json.JSONDecodeError:
        logger.warning("Failed to parse questions extraction response as JSON")
        return {"questions": {}, "raw_response": response}


async def _extract_alcohol(image_bytes: bytes) -> dict:
    """Extract alcohol question + table from cropped section."""
    current_operation.set("alcohol")
    cropped = crop_alcohol_section(image_bytes)
    _save_debug_image(cropped, "alcohol")

    response = await llm_client.call(
        system_prompt=page_2_alcohol.SYSTEM_PROMPT,
        user_prompt=page_2_alcohol.USER_PROMPT,
        config=page_2_alcohol.CONFIG,
        images=[cropped],
    )

    try:
        return json.loads(response)
    except json.JSONDecodeError:
        logger.warning("Failed to parse alcohol extraction response as JSON")
        return {"alcohol": {}, "raw_response": response}


# ─── Full Page Fallback ──────────────────────────────────────────────────────

async def _extract_full_page(image_bytes: bytes) -> dict:
    """
    Fallback: Extract from full page using original prompt.
    Used when no anchors are found to ensure no data is lost.
    """
    from app.services.mer.prompts import page_2 as page_2_original

    current_operation.set("full")
    logger.info("Fallback: Processing Page 2 with full page (no anchors found)")
    _save_debug_image(image_bytes, "fullpage_fallback")

    response = await llm_client.call(
        system_prompt=page_2_original.SYSTEM_PROMPT,
        user_prompt=page_2_original.USER_PROMPT,
        config=page_2_original.CONFIG,
        images=[image_bytes],
    )

    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return {"raw_response": response}


# ─── Main Processing Function ────────────────────────────────────────────────

async def extract_page_2_split(image_bytes: bytes) -> dict:
    """
    Extract Page 2 data using split processing (2 sections).
    Falls back to full page if anchor is missing or at a nonsensical position.
    """
    alcohol_y, img_height = _detect_section_boundary(image_bytes)

    if alcohol_y is None:
        logger.warning("No section anchors found - using full page fallback")
        return await _extract_full_page(image_bytes)

    min_y = int(img_height * 0.40)
    max_y = int(img_height * 0.95)
    if alcohol_y < min_y or alcohol_y > max_y:
        logger.warning(
            "Anchor at Y=%s outside reasonable range (%s-%s) - using full page fallback",
            alcohol_y, min_y, max_y,
        )
        return await _extract_full_page(image_bytes)

    logger.info("Processing Page 2 with split method (questions + alcohol)")
    _save_debug_image(image_bytes, "original")

    questions_result, alcohol_result = await asyncio.gather(
        _extract_questions(image_bytes),
        _extract_alcohol(image_bytes),
    )

    questions_data = questions_result.get("questions", {})
    alcohol_data = alcohol_result.get("alcohol", {})

    # Merge alcohol Q10a into questions dict
    for key, value in alcohol_data.items():
        questions_data[key] = value

    combined = {
        "page_number": 2,
        "questions": questions_data,
    }

    if "raw_response" in questions_result:
        combined["_questions_raw"] = questions_result["raw_response"]
    if "raw_response" in alcohol_result:
        combined["_alcohol_raw"] = alcohol_result["raw_response"]

    return combined


async def extract_page_2(image_bytes: bytes, use_split: Optional[bool] = None) -> dict:
    """
    Extract Page 2 data, optionally using split processing.

    Args:
        image_bytes: The full page image bytes
        use_split: Override the USE_SPLIT_PROCESSING config.
                   If None, uses the module-level config.
    """
    should_split = use_split if use_split is not None else USE_SPLIT_PROCESSING

    if should_split:
        return await extract_page_2_split(image_bytes)
    else:
        from app.services.mer.prompts import page_2 as page_2_original

        current_operation.set("full")
        logger.info("Processing Page 2 with original single-call method")

        response = await llm_client.call(
            system_prompt=page_2_original.SYSTEM_PROMPT,
            user_prompt=page_2_original.USER_PROMPT,
            config=page_2_original.CONFIG,
            images=[image_bytes],
        )

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {"raw_response": response}
