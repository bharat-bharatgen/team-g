"""
Risk analysis processor.

Main orchestration for risk analysis pipeline:
1. Load MER and pathology results
2. Pre-process data
3. Call LLM for analysis
4. Post-process and store result
"""

import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from bson import ObjectId

from app.dependencies import get_database
from app.models.risk_result import RiskResultModel
from app.services.llm import client as llm_client
from app.services.llm.context import current_case_id, current_task, current_call_count
from app.services.risk.pre_processor import prepare_llm_input
from app.services.risk.post_processor import post_process_response
from app.services.risk.prompts.analysis import (
    CONFIG,
    SYSTEM_PROMPT,
    build_user_prompt,
)

logger = logging.getLogger(__name__)


async def _get_latest_mer_result(case_id: str) -> Tuple[Optional[Dict], Optional[int]]:
    """
    Get the latest MER result for a case.

    Returns:
        (mer_pages_data, version) or (None, None) if not found
    """
    db = await get_database()
    result = await db.mer_results.find_one(
        {"case_id": case_id},
        sort=[("version", -1)],
    )
    if result:
        raw_pages = result.get("pages", {})
        mer_data = {f"page_{k}": v for k, v in raw_pages.items()}
        return mer_data, result.get("version")
    return None, None


async def _get_latest_pathology_result(
    case_id: str,
) -> Tuple[Optional[Dict], Optional[int]]:
    """
    Get the latest pathology result for a case.

    Returns:
        (pathology_standardized_data, version) or (None, None) if not found
    """
    db = await get_database()
    result = await db.pathology_results.find_one(
        {"case_id": case_id},
        sort=[("version", -1)],
    )
    if result:
        # Convert standardized tests to the format expected by pre-processor
        standardized = result.get("standardized", {})

        # Detect format: v2 has "tests" array, v1 has param names as keys
        if "tests" in standardized:
            # v2 format: filter matched tests
            raw_tests = standardized.get("tests", [])
            tests = [
                {
                    "standard_name": t.get("standard_name"),
                    "value": t.get("value"),
                    "unit": t.get("unit"),
                    "reference_range": t.get("range"),
                    "flag": t.get("flag"),
                    "source_page": t.get("source_page"),  # Include page number
                }
                for t in raw_tests
                if isinstance(t, dict) and t.get("status") == "matched"
            ]
        else:
            # v1 format: param names as keys
            tests = []
            for param_name, param_data in standardized.items():
                if param_name in ("unmatched_tests", "Remark"):
                    continue
                if isinstance(param_data, dict):
                    tests.append(
                        {
                            "standard_name": param_name,
                            "value": param_data.get("value"),
                            "unit": param_data.get("unit"),
                            "reference_range": param_data.get("reference_range"),
                            "flag": param_data.get("flag"),
                        }
                    )

        pathology_data = {
            "tests": tests,
            "patient_info": result.get("patient_info", {}),
            "lab_info": result.get("lab_info", {}),
        }
        return pathology_data, result.get("version")
    return None, None


async def _get_next_version(case_id: str) -> int:
    """Get the next version number for risk results."""
    db = await get_database()
    latest = await db.risk_results.find_one(
        {"case_id": case_id},
        sort=[("version", -1)],
        projection={"version": 1},
    )
    return (latest.get("version", 0) + 1) if latest else 1


async def _store_risk_result(result: RiskResultModel) -> str:
    """Store risk result in MongoDB."""
    db = await get_database()
    doc = result.model_dump()
    insert_result = await db.risk_results.insert_one(doc)
    return str(insert_result.inserted_id)


async def process_risk(case_id: str) -> Dict[str, Any]:
    """
    Main risk analysis pipeline.

    Args:
        case_id: The case ID to analyze

    Returns:
        Dict with status and result info
    """
    current_case_id.set(case_id)
    current_task.set("risk")
    call_counter = [0]
    current_call_count.set(call_counter)

    logger.info(f"Starting risk analysis for case {case_id}")

    # Step 1: Load latest MER and pathology results
    mer_data, mer_version = await _get_latest_mer_result(case_id)
    pathology_data, pathology_version = await _get_latest_pathology_result(case_id)

    if not mer_data and not pathology_data:
        raise ValueError(
            "Cannot run risk analysis: no MER or pathology results available"
        )

    logger.info(
        f"Loaded data - MER v{mer_version}, Pathology v{pathology_version}"
    )

    # Step 2: Pre-process data and generate references
    llm_input, references = prepare_llm_input(mer_data, pathology_data)
    logger.info(
        f"Pre-processing complete - "
        f"critical_flags: {len(llm_input['pre_computed']['critical_flags'])}, "
        f"contradictions: {len(llm_input['pre_computed']['direct_contradictions'])}, "
        f"references: {len(references)}"
    )

    # Step 3: Call LLM for analysis
    user_prompt = build_user_prompt(llm_input)
    logger.info(f"Calling LLM for risk analysis (model: {CONFIG.model})")

    t_llm = time.monotonic()
    llm_response_text = await llm_client.call(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        config=CONFIG,
    )
    llm_wall = time.monotonic() - t_llm

    logger.info(
        "LLM_PIPELINE,case_id=%s,task=risk,total_calls=%s,llm_wall_s=%.2f,calls_per_sec=%.2f",
        case_id, call_counter[0], llm_wall, call_counter[0] / llm_wall if llm_wall > 0 else 0,
    )

    # Parse JSON response
    try:
        llm_response = json.loads(llm_response_text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        logger.error(f"Raw response: {llm_response_text[:500]}")
        raise ValueError(f"LLM returned invalid JSON: {e}")

    # Step 4: Post-process
    llm_response = post_process_response(
        llm_response, mer_data, pathology_data, CONFIG.model
    )
    logger.info("Post-processing complete")

    # Step 5: Store result
    next_version = await _get_next_version(case_id)
    source_freshness = (mer_version or 0) + (pathology_version or 0)

    risk_result = RiskResultModel(
        case_id=case_id,
        version=next_version,
        mer_version=mer_version,
        pathology_version=pathology_version,
        source_freshness=source_freshness,
        patient_info=llm_input["patient_info"],
        critical_flags=llm_input["pre_computed"]["critical_flags"],
        contradictions=llm_input["pre_computed"]["direct_contradictions"],
        llm_response=llm_response,
        references=references,
        created_at=datetime.utcnow(),
    )

    doc_id = await _store_risk_result(risk_result)
    logger.info(f"Risk result stored: version={next_version}, id={doc_id}")

    return {
        "version": next_version,
        "mer_version": mer_version,
        "pathology_version": pathology_version,
        "source_freshness": source_freshness,
        "risk_level": llm_response.get("risk_level"),
        "summary": llm_response.get("summary"),
        "integrity_concerns": llm_response.get("integrity_concerns", []),
        "clinical_discoveries": llm_response.get("clinical_discoveries", []),
    }
