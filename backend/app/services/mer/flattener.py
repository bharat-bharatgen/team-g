import uuid
from typing import Any, Dict, List
from app.models.mer_result import MERField, FieldSource


def _make_field(page: int, section: str, key: str, data: Any) -> List[MERField]:
    """
    Convert a single extracted item into one or more MERField entries.

    Handles three shapes:
    1. {"value": "...", "confidence": 0.9}                         → simple value
    2. {"answer": "Yes", "details": "...", "confidence": 0.8}     → Y/N question
    3. Nested dict with sub_questions or special structures        → recurse
    """
    fields = []

    if not isinstance(data, dict):
        return fields

    # Shape 1: simple value field - use answer column for consistency
    if "value" in data and "answer" not in data:
        val = data.get("value")
        
        # Special handling for signature fields: show Present/Absent, no confidence
        if "signature" in key.lower():
            fields.append(MERField(
                id=str(uuid.uuid4()),
                page=page,
                section=section,
                key=key,
                answer="Present" if val is not None else "Absent",
                confidence=None,
                source=FieldSource.LLM,
            ))
            return fields
        
        # Normal value field
        fields.append(MERField(
            id=str(uuid.uuid4()),
            page=page,
            section=section,
            key=key,
            answer=val,
            confidence=None if val is None else data.get("confidence", 0.0),
            source=FieldSource.LLM,
        ))
        return fields

    # Shape 2: Y/N question field
    if "answer" in data:
        ans = data.get("answer")
        fields.append(MERField(
            id=str(uuid.uuid4()),
            page=page,
            section=section,
            key=key,
            answer=ans,
            details=data.get("details"),
            confidence=None if ans is None else data.get("confidence", 0.0),
            source=FieldSource.LLM,
        ))
        # Handle sub_questions if present
        if "sub_questions" in data and isinstance(data["sub_questions"], dict):
            for sub_key, sub_data in data["sub_questions"].items():
                fields.extend(_make_field(page, section, f"{key} > {sub_key}", sub_data))
        # Handle alcohol_table if present
        if "alcohol_table" in data and isinstance(data["alcohol_table"], dict):
            for drink, drink_data in data["alcohol_table"].items():
                if isinstance(drink_data, dict):
                    qty = drink_data.get("quantity_per_day")
                    dur = drink_data.get("duration")
                    composite = f"Qty: {qty}, Duration: {dur}" if qty or dur else None
                    conf = drink_data.get("confidence", 0.0)
                    fields.append(MERField(
                        id=str(uuid.uuid4()),
                        page=page,
                        section=section,
                        key=f"{key} > {drink}",
                        answer=composite,
                        confidence=None if composite is None else conf,
                        source=FieldSource.LLM,
                    ))
        return fields

    # Shape 3: nested dict (e.g. family history, tobacco, weight_changed)
    # Recurse into all keys that look like field containers
    for sub_key, sub_data in data.items():
        if isinstance(sub_data, dict):
            fields.extend(_make_field(page, section, f"{key} > {sub_key}" if key else sub_key, sub_data))
        elif isinstance(sub_data, str) and sub_key == "applicable":
            # 11) For Females > applicable: always leave empty (not shown)
            fields.append(MERField(
                id=str(uuid.uuid4()),
                page=page,
                section=section,
                key=f"{key} > applicable",
                answer=None,
                confidence=None,
                source=FieldSource.LLM,
            ))
        elif isinstance(sub_data, str) and sub_key == "alive_status":
            # Family history: Alive/Not Alive so it shows in frontend
            fields.append(MERField(
                id=str(uuid.uuid4()),
                page=page,
                section=section,
                key=f"{key} > alive_status",
                answer=sub_data,
                confidence=None,
                source=FieldSource.LLM,
            ))

    return fields


def flatten_page(page_num: int, page_data: dict) -> List[MERField]:
    """
    Flatten a single page's LLM JSON output into a list of MERFields.

    Args:
        page_num: MER page number (1-4)
        page_data: The parsed LLM JSON for this page

    Returns:
        List of MERField
    """
    fields = []

    for section_name, section_data in page_data.items():
        # Skip non-dict entries like "page_number"
        if not isinstance(section_data, dict):
            continue

        for key, data in section_data.items():
            fields.extend(_make_field(page_num, section_name, key, data))

    return fields


def flatten_all_pages(pages: Dict[str, dict]) -> List[MERField]:
    """
    Flatten all pages' LLM JSON into a single list of MERFields.

    Args:
        pages: {page_num_str: page_llm_json, ...}

    Returns:
        List of MERField in page order (1, 2, 3, 4)
    """
    all_fields = []
    # Sort by page number to ensure consistent ordering
    sorted_pages = sorted(pages.items(), key=lambda x: int(x[0]))
    for page_num_str, page_data in sorted_pages:
        page_num = int(page_num_str)
        all_fields.extend(flatten_page(page_num, page_data))

    return all_fields
