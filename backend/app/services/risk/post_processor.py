"""
Post-processing for risk analysis.

Validates and enriches LLM response.
Supports both old format (red_flags/contradictions) and new format
(integrity_concerns/clinical_discoveries) for backward compatibility.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional


def _extract_all_refs(llm_response: Dict) -> List[str]:
    """Extract all ref IDs cited in the LLM response (both old and new format)."""
    refs: List[str] = []

    def _collect(obj: Any):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key in ("ref", "mer_ref", "path_ref") and isinstance(value, str):
                    refs.append(value)
                elif key == "refs" and isinstance(value, list):
                    refs.extend(v for v in value if isinstance(v, str))
                else:
                    _collect(value)
        elif isinstance(obj, list):
            for item in obj:
                _collect(item)

    _collect(llm_response)
    return refs


def validate_refs(
    llm_response: Dict,
    mer_data: Optional[Dict],
    pathology_data: Optional[Dict],
) -> List[str]:
    """Validate that cited ref IDs correspond to real input data."""
    warnings: List[str] = []
    cited_refs = _extract_all_refs(llm_response)

    valid_path_names: set[str] = set()
    if pathology_data:
        for test in pathology_data.get("tests", []):
            if test.get("standard_name"):
                valid_path_names.add(test["standard_name"])

    for ref in cited_refs:
        if not ref:
            continue
        if ref.startswith("PATH:"):
            param = ref.split(":", 1)[1]
            if param not in valid_path_names:
                warnings.append(f"Unknown pathology ref: {ref}")
        elif ref.startswith("MER:") and mer_data:
            parts = ref.split(":")
            if len(parts) >= 2:
                page_key = f"page_{parts[1].replace('P', '')}"
                if page_key not in mer_data:
                    warnings.append(f"Invalid MER page ref: {ref}")

    return warnings


def _derive_risk_level(risk_score: int) -> str:
    """Derive risk_level from risk_score using fixed ranges."""
    if risk_score <= 3:
        return "Low"
    elif risk_score <= 6:
        return "Intermediate"
    else:
        return "High"


def post_process_response(
    llm_response: Dict,
    mer_data: Optional[Dict],
    pathology_data: Optional[Dict],
    model_name: str,
) -> Dict:
    """
    Light-touch post-processing.
    - Derive risk_level from risk_score (never trust LLM for this)
    - Validate ref citations
    - Add metadata
    - DO NOT override clinical judgment
    """
    ref_warnings = validate_refs(llm_response, mer_data, pathology_data)

    is_new_format = "integrity_concerns" in llm_response

    raw_score = llm_response.get("risk_score")
    if isinstance(raw_score, (int, float)):
        score = max(1, min(10, int(raw_score)))
    else:
        score = 1
    llm_response["risk_score"] = score
    llm_response["risk_level"] = _derive_risk_level(score)

    llm_response["_metadata"] = {
        "generated_at": datetime.utcnow().isoformat(),
        "format": "v2" if is_new_format else "v1",
        "ref_validation_warnings": ref_warnings if ref_warnings else None,
        "model": model_name,
    }

    return llm_response


def extract_risk_profile(llm_response: Dict) -> Dict[str, Any]:
    """Extract the risk profile from LLM response for quick access."""
    return llm_response.get("risk_profile", {})
