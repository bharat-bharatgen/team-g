"""
Pathology range utilities.

Functions for formatting, parsing, and comparing reference ranges.
"""

import re
from typing import Any, List, Optional, Tuple, Union


def format_range(range_value: Any, gender: str = "male") -> Optional[str]:
    """
    Convert a range value to display string.

    Args:
        range_value: Can be:
            - List: [4.0, 6.0] → "4.0-6.0"
            - List one-sided: [None, 40] → "< 40", [30, None] → "> 30"
            - Dict (gender-specific): {"male": [13, 18], "female": [11, 17]}
            - String: "Non-Reactive" → "Non-Reactive"
            - Empty list [] → None
        gender: "male" or "female" for gender-specific ranges

    Returns:
        Formatted string or None if no range.
    """
    if range_value is None:
        return None

    # Handle gender-specific dict
    if isinstance(range_value, dict):
        if gender in range_value:
            return format_range(range_value[gender], gender)
        # Fallback to male if gender not found
        if "male" in range_value:
            return format_range(range_value["male"], gender)
        return None

    # Handle list ranges
    if isinstance(range_value, list):
        if len(range_value) == 0:
            return None
        if len(range_value) == 2:
            low, high = range_value
            if low is None and high is not None:
                return f"< {high}"
            if low is not None and high is None:
                return f"> {low}"
            if low is not None and high is not None:
                return f"{low}-{high}"
        return None

    # Handle string/qualitative ranges
    if isinstance(range_value, str):
        return range_value if range_value.strip() else None

    return None


def parse_range(range_str: Optional[str]) -> Tuple[Optional[float], Optional[float]]:
    """
    Parse a range string into (low, high) bounds.

    Args:
        range_str: String like "4.0-6.0", "< 40", "> 30", "0-200"

    Returns:
        (low, high) tuple. None for unbounded side.
    """
    if not range_str or not isinstance(range_str, str):
        return (None, None)

    range_str = range_str.strip()

    # Handle "< X" or "<X"
    match = re.match(r'^[<≤]\s*(\d+\.?\d*)$', range_str)
    if match:
        return (None, float(match.group(1)))

    # Handle "> X" or ">X"
    match = re.match(r'^[>≥]\s*(\d+\.?\d*)$', range_str)
    if match:
        return (float(match.group(1)), None)

    # Handle "X-Y" or "X - Y"
    match = re.match(r'^(\d+\.?\d*)\s*[-–]\s*(\d+\.?\d*)$', range_str)
    if match:
        return (float(match.group(1)), float(match.group(2)))

    return (None, None)


def parse_value(value: Optional[str]) -> Optional[float]:
    """
    Parse a value string to float.

    Args:
        value: String like "13.5", "178000", etc.

    Returns:
        Float value or None if not parseable.
    """
    if not value or not isinstance(value, str):
        return None

    value = value.strip()

    # Try direct float conversion
    try:
        return float(value)
    except ValueError:
        pass

    # Remove common suffixes and try again
    cleaned = re.sub(r'[%\s]+$', '', value)
    try:
        return float(cleaned)
    except ValueError:
        pass

    return None


def is_qualitative_match(value: Optional[str], expected: Optional[str]) -> Optional[bool]:
    """
    Check if a qualitative value matches expected.

    Handles variations like:
    - "Negative", "Non-Reactive", "No", "Nil" → matches "No"/"Non-Reactive"/"Negative"
    - "Positive", "Reactive", "Yes" → does NOT match "No"/"Non-Reactive"/"Negative"

    Args:
        value: The test value
        expected: The expected/normal value

    Returns:
        True if matches (normal), False if doesn't match (abnormal), None if can't determine.
    """
    if not value or not expected:
        return None

    value_lower = value.lower().strip()
    expected_lower = expected.lower().strip()

    # Define normal/negative indicators
    negative_indicators = {"negative", "non-reactive", "non reactive", "no", "nil", "absent", "not detected"}
    positive_indicators = {"positive", "reactive", "yes", "present", "detected"}

    # Check if expected is a "negative/normal" type
    expected_is_negative = any(ind in expected_lower for ind in negative_indicators)

    if expected_is_negative:
        # Value should also be negative to be "normal"
        if any(ind in value_lower for ind in negative_indicators):
            return True  # Normal
        if any(ind in value_lower for ind in positive_indicators):
            return False  # Abnormal
        return None  # Can't determine

    # Check if expected is a "positive" type (rare but possible)
    expected_is_positive = any(ind in expected_lower for ind in positive_indicators)

    if expected_is_positive:
        if any(ind in value_lower for ind in positive_indicators):
            return True
        if any(ind in value_lower for ind in negative_indicators):
            return False
        return None

    # Direct string comparison as fallback
    if value_lower == expected_lower:
        return True

    return None


def is_in_range(
    value: Optional[str],
    range_str: Optional[str],
) -> Optional[bool]:
    """
    Check if a value is within a reference range.

    Args:
        value: The test value (string)
        range_str: The reference range (string like "4.0-6.0", "< 40", "Non-Reactive")

    Returns:
        True if in range (normal), False if out of range (abnormal), None if can't determine.
    """
    if not value or not range_str:
        return None

    # Try numeric comparison first
    parsed_value = parse_value(value)
    low, high = parse_range(range_str)

    if parsed_value is not None and (low is not None or high is not None):
        # Numeric comparison
        if low is not None and parsed_value < low:
            return False
        if high is not None and parsed_value > high:
            return False
        return True

    # Fall back to qualitative comparison
    return is_qualitative_match(value, range_str)


def compute_range_status(
    value: Optional[str],
    report_range: Optional[str],
    config_range: Optional[str],
) -> Optional[str]:
    """
    Compute the range status by checking against both report and config ranges.

    Args:
        value: The test value
        report_range: Reference range extracted from report
        config_range: Reference range from config (NEW_PARAMS)

    Returns:
        "normal" - in range for all available ranges
        "abnormal" - out of range for at least one range
        None - no ranges available to compare
    """
    if not value:
        return None

    results = []

    # Check against report range
    if report_range:
        result = is_in_range(value, report_range)
        if result is not None:
            results.append(result)

    # Check against config range
    if config_range:
        result = is_in_range(value, config_range)
        if result is not None:
            results.append(result)

    if not results:
        return None  # No ranges to compare against

    # If ANY range check returns False (out of range), status is abnormal
    if False in results:
        return "abnormal"

    return "normal"
