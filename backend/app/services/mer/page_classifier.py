import asyncio
from typing import Dict, List, Tuple
from rapidfuzz import fuzz
from app.services.mer.page_config import (
    PAGE_IDENTIFIERS,
    CONFIDENCE_THRESHOLD,
    FUZZY_THRESHOLD,
)


def score_page_against_identifiers(ocr_text: str, page_num: int) -> float:
    """
    Score how well OCR text matches a specific page's identifiers using fuzzy matching.

    Returns a score between 0.0 and 1.0
    """
    keywords = PAGE_IDENTIFIERS[page_num]
    matched = 0

    for keyword in keywords:
        if fuzz.partial_ratio(keyword.lower(), ocr_text) >= FUZZY_THRESHOLD:
            matched += 1

    return matched / len(keywords)


def get_all_scores(ocr_text: str) -> Dict[int, float]:
    """Get scores for an OCR text against all page types."""
    return {
        page_num: score_page_against_identifiers(ocr_text, page_num)
        for page_num in PAGE_IDENTIFIERS
    }


def assign_pages_smart(
    all_scores: Dict[int, Dict[int, float]],
) -> Dict[int, Tuple[int, float]]:
    """
    Smart assignment of pages using greedy conflict resolution.

    Builds all (score, page_index, page_num) candidates sorted by score descending,
    then greedily assigns ensuring each input page maps to at most one MER page
    and each MER page gets at most one input page.

    Args:
        all_scores: {page_index: {mer_page_num: score}}

    Returns:
        {mer_page_num: (page_index, confidence)}
    """
    num_mer_pages = len(PAGE_IDENTIFIERS)
    assignment: Dict[int, Tuple[int, float]] = {}
    assigned_indices: set = set()

    # Build candidates list: (score, page_index, mer_page_num)
    candidates = []
    for page_index, scores in all_scores.items():
        for mer_page_num, score in scores.items():
            candidates.append((score, page_index, mer_page_num))

    # Sort by score descending (highest confidence first)
    candidates.sort(reverse=True, key=lambda x: x[0])

    # Greedy assignment
    for score, page_index, mer_page_num in candidates:
        if page_index in assigned_indices:
            continue
        if mer_page_num in assignment:
            continue

        assignment[mer_page_num] = (page_index, score)
        assigned_indices.add(page_index)

        if len(assignment) == num_mer_pages:
            break

    return assignment


def _classify_pages_sync(pages: list[dict]) -> dict:
    """
    Synchronous page classification (CPU-bound fuzzy matching).
    Called via asyncio.to_thread from the async wrapper.
    """
    # Score each page against all MER page identifiers
    all_scores: Dict[int, Dict[int, float]] = {}
    for idx, page in enumerate(pages):
        ocr_text = page["text"].lower()
        all_scores[idx] = get_all_scores(ocr_text)

    # Smart greedy assignment
    assignment = assign_pages_smart(all_scores)

    # Build result
    mapping = {}
    needs_review = []
    assigned_indices = set()

    for mer_page_num, (page_index, confidence) in assignment.items():
        mapping[mer_page_num] = {
            "page_index": page_index,
            "page": pages[page_index],
            "confidence": round(confidence, 3),
        }
        assigned_indices.add(page_index)
        if confidence < CONFIDENCE_THRESHOLD:
            needs_review.append(mer_page_num)

    unmatched_pages = [pages[i] for i in range(len(pages)) if i not in assigned_indices]
    missing_pages = [p for p in PAGE_IDENTIFIERS if p not in mapping]

    return {
        "mapping": mapping,
        "unmatched_pages": unmatched_pages,
        "missing_pages": missing_pages,
        "needs_review": needs_review,
        "all_scores": {
            idx: {p: round(s, 3) for p, s in scores.items()}
            for idx, scores in all_scores.items()
        },
    }


async def classify_pages(pages: list[dict]) -> dict:
    """
    Async wrapper for page classification.
    Offloads CPU-bound fuzzy matching to a thread.

    Args:
        pages: List of dicts with "page_number", "text", "image_bytes"

    Returns:
        {
            "mapping": {mer_page_num: {"page_index": int, "page": dict, "confidence": float}},
            "unmatched_pages": [page dicts that didn't map],
            "missing_pages": [MER page numbers with no match],
            "needs_review": [MER page numbers with low confidence],
            "all_scores": {page_index: {mer_page_num: score}}
        }
    """
    return await asyncio.to_thread(_classify_pages_sync, pages)
