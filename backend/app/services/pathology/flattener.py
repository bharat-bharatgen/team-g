"""
Pathology flattener — converts standardized JSON to a flat list of PathologyField
for Excel export/import.

Expects v2 format: {"tests": [{standard_name, original_name, status, ...}, ...]}

Also computes range_status by comparing against both report range and config range.
"""

import uuid
from typing import Any, Dict, List, Optional

from app.models.pathology_result import PathologyField, FieldSource
from app.services.pathology.config import get_config_range
from app.services.pathology.range_utils import format_range, compute_range_status


def _get_config_range_str(
    standard_name: Optional[str],
    sample_type: Optional[str],
) -> Optional[str]:
    """
    Get formatted config range string for a parameter.

    Args:
        standard_name: The standardized parameter name
        sample_type: The sample type (blood, urine, etc.)

    Returns:
        Formatted range string or None.
    """
    if not standard_name:
        return None

    config_info = get_config_range(standard_name, sample_type)
    if not config_info:
        return None

    raw_range = config_info.get("range")
    return format_range(raw_range, gender="male")


def flatten_standardized(standardized: Dict[str, Any]) -> List[PathologyField]:
    """
    Flatten the standardized JSON into a list of PathologyField.

    Expects v2 format: {"tests": [...]}
    Preserves the order from LLM output (page order).
    Computes range_status for each field.

    Args:
        standardized: The LLM step-2 output.

    Returns:
        List of PathologyField in LLM output order.
    """
    return _flatten_v2(standardized)


def _flatten_v2(standardized: Dict[str, Any]) -> List[PathologyField]:
    """
    Flatten v2 format: {"tests": [...]}

    Preserves LLM output order. No placeholders for missing standard params.
    """
    fields: List[PathologyField] = []
    tests = standardized.get("tests", [])

    for test in tests:
        if not isinstance(test, dict):
            continue

        std_name = test.get("standard_name")
        is_matched = test.get("status") == "matched" and std_name
        sample_type = test.get("sample_type")
        value = test.get("value")
        report_range = test.get("range")
        source_page = test.get("source_page")  # Page number from LLM

        # Get config range for matched params
        config_range = _get_config_range_str(std_name, sample_type) if is_matched else None

        # Compute range status
        range_status = compute_range_status(value, report_range, config_range)

        fields.append(PathologyField(
            id=str(uuid.uuid4()),
            key=std_name if is_matched else test.get("original_name", "Unknown"),
            value=value,
            unit=test.get("unit"),
            reference_range=report_range,
            config_range=config_range,
            range_status=range_status,
            flag=test.get("flag"),
            method=test.get("method"),
            reference_name=test.get("original_name"),
            sample_type=sample_type,
            page_number=source_page,  # Pass through page number
            section_path=[],
            is_standard=bool(is_matched),
            source=FieldSource.LLM,
        ))

    return fields


