"""
Post-processing for risk analysis.

Validates and enriches LLM response.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional


def extract_all_sources_from_summary(summary: Dict) -> List[str]:
    """Recursively extract all source citations from the summary."""
    sources = []

    def extract_recursive(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key in ["source", "sources", "supporting_evidence", "disclosure_source"]:
                    if isinstance(value, str) and value:
                        sources.append(value)
                    elif isinstance(value, list):
                        sources.extend([v for v in value if isinstance(v, str) and v])
                    elif isinstance(value, dict):
                        sources.extend(
                            [v for v in value.values() if isinstance(v, str) and v]
                        )
                else:
                    extract_recursive(value)
        elif isinstance(obj, list):
            for item in obj:
                extract_recursive(item)

    extract_recursive(summary)
    return sources


def validate_sources(
    summary: Dict, mer_data: Optional[Dict], pathology_data: Optional[Dict]
) -> List[str]:
    """Validate that cited sources actually exist in the input data."""
    warnings = []
    cited_sources = extract_all_sources_from_summary(summary)

    # Build set of valid pathology test names
    valid_pathology = set()
    if pathology_data:
        for test in pathology_data.get("tests", []):
            if test.get("standard_name"):
                valid_pathology.add(test["standard_name"])
            if test.get("original_name"):
                valid_pathology.add(test["original_name"])

    for source in cited_sources:
        if not source:
            continue

        # Check pathology sources
        if source.startswith("pathology."):
            test_name = source.replace("pathology.", "")
            if test_name not in valid_pathology:
                warnings.append(f"Unknown pathology test cited: {source}")

        # Check MER sources (basic validation)
        elif source.startswith("mer.") and mer_data:
            parts = source.split(".")
            if len(parts) >= 2:
                page_ref = parts[1]  # e.g., "page1"
                page_key = page_ref.replace("page", "page_")  # "page_1"
                if page_key not in mer_data and page_ref not in mer_data:
                    warnings.append(f"Invalid MER page reference: {source}")

        # Derived sources are always valid
        elif source.startswith("derived."):
            pass

    return warnings


def post_process_response(
    llm_response: Dict,
    mer_data: Optional[Dict],
    pathology_data: Optional[Dict],
    model_name: str,
) -> Dict:
    """
    Light-touch post-processing.
    - Validate sources
    - Add metadata
    - DO NOT override clinical judgment
    """
    # Validate sources
    source_warnings = validate_sources(llm_response, mer_data, pathology_data)

    # Add metadata
    llm_response["_metadata"] = {
        "generated_at": datetime.utcnow().isoformat(),
        "source_validation_warnings": source_warnings if source_warnings else None,
        "model": model_name,
    }

    return llm_response


def extract_risk_profile(llm_response: Dict) -> Dict[str, Any]:
    """Extract the risk profile from LLM response for quick access."""
    return llm_response.get("risk_profile", {})
