"""
Risk analysis API endpoints.

Provides endpoints to:
- Get risk analysis result (latest or specific version)
- List all risk analysis versions
- Get quick summary of risk assessment
- Export result as Excel
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from bson import ObjectId
import io

from app.core.security import get_current_user
from app.dependencies import get_database
from app.services.risk.excel_export import generate_excel
from app.api.v1.schemas.risk import (
    RiskResultResponse,
    RiskVersionsResponse,
    RiskVersionEntry,
    RiskSummaryResponse,
    BasedOnInfo,
)

router = APIRouter()


# ─── Helpers ─────────────────────────────────────────────────────────────────


async def _get_case_or_404(case_id: str, user_id: str):
    """Fetch a case and verify ownership."""
    db = await get_database()
    case = await db.cases.find_one({"_id": ObjectId(case_id), "user_id": user_id})
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Case not found"
        )
    return case


async def _get_latest_result(case_id: str):
    """Get the latest risk result by source_freshness, then version."""
    db = await get_database()
    result = await db.risk_results.find_one(
        {"case_id": case_id},
        sort=[("source_freshness", -1), ("version", -1)],
    )
    return result


async def _get_result_by_version(case_id: str, version: int):
    """Get a specific version of risk result."""
    db = await get_database()
    result = await db.risk_results.find_one(
        {"case_id": case_id, "version": version}
    )
    return result


async def _list_result_versions(case_id: str):
    """List all risk result versions for a case."""
    db = await get_database()
    cursor = db.risk_results.find(
        {"case_id": case_id},
        projection={
            "_id": 1,
            "version": 1,
            "mer_version": 1,
            "pathology_version": 1,
            "source_freshness": 1,
            "llm_response.risk_level": 1,
            "created_at": 1,
        },
        sort=[("source_freshness", -1), ("version", -1)],
    )
    return await cursor.to_list(length=100)


def _extract_risk_summary(doc):
    """Extract risk summary fields from document. Supports both v1 and v2 formats."""
    llm_response = doc.get("llm_response", {})
    result = {
        "summary": llm_response.get("summary"),
        "risk_level": llm_response.get("risk_level"),
    }

    is_v2 = "integrity_concerns" in llm_response

    if is_v2:
        result["risk_score"] = llm_response.get("risk_score")
        result["applicant"] = llm_response.get("applicant")
        result["integrity_concerns"] = llm_response.get("integrity_concerns", [])
        result["clinical_discoveries"] = llm_response.get("clinical_discoveries", [])
    else:
        result["red_flags"] = llm_response.get("red_flags", [])
        result["contradictions"] = llm_response.get("contradictions", [])

    return result


# ─── GET /cases/{case_id}/risk/result ────────────────────────────────────────


@router.get("/{case_id}/risk/result", response_model=RiskResultResponse)
async def get_risk_result(
    case_id: str,
    version: int = Query(None, description="Specific version number. Omit for latest."),
    user: dict = Depends(get_current_user),
):
    """
    Get risk analysis result for a case.

    Returns the latest version by default (sorted by source_freshness, then version).
    Provide ?version=N to get a specific version.
    """
    await _get_case_or_404(case_id, user["id"])

    if version is not None:
        doc = await _get_result_by_version(case_id, version)
    else:
        doc = await _get_latest_result(case_id)

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No risk analysis result found. Processing may not have completed yet.",
        )

    return RiskResultResponse(
        id=str(doc["_id"]),
        case_id=doc["case_id"],
        version=doc["version"],
        based_on=BasedOnInfo(
            mer_version=doc.get("mer_version"),
            pathology_version=doc.get("pathology_version"),
            source_freshness=doc.get("source_freshness", 0),
        ),
        patient_info=doc.get("patient_info", {}),
        critical_flags=doc.get("critical_flags", []),
        contradictions=doc.get("contradictions", []),
        llm_response=doc.get("llm_response", {}),
        references=doc.get("references", {}),
        created_at=doc["created_at"],
    )


# ─── GET /cases/{case_id}/risk/versions ──────────────────────────────────────


@router.get("/{case_id}/risk/versions", response_model=RiskVersionsResponse)
async def get_risk_versions(case_id: str, user: dict = Depends(get_current_user)):
    """
    List all risk analysis versions for a case.

    Sorted by source_freshness (descending), then version (descending).
    The first entry is the "latest" result.
    """
    await _get_case_or_404(case_id, user["id"])

    versions = await _list_result_versions(case_id)

    return RiskVersionsResponse(
        case_id=case_id,
        versions=[
            RiskVersionEntry(
                id=str(v["_id"]),
                version=v["version"],
                mer_version=v.get("mer_version"),
                pathology_version=v.get("pathology_version"),
                source_freshness=v.get("source_freshness", 0),
                risk_level=v.get("llm_response", {}).get("risk_level"),
                created_at=v["created_at"],
            )
            for v in versions
        ],
    )


# ─── GET /cases/{case_id}/risk/summary ───────────────────────────────────────


@router.get("/{case_id}/risk/summary", response_model=RiskSummaryResponse)
async def get_risk_summary(
    case_id: str,
    version: int = Query(None, description="Specific version number. Omit for latest."),
    user: dict = Depends(get_current_user),
):
    """
    Get a quick summary of the risk analysis result.

    Useful for polling or dashboard views where full details aren't needed.
    """
    await _get_case_or_404(case_id, user["id"])

    if version is not None:
        doc = await _get_result_by_version(case_id, version)
    else:
        doc = await _get_latest_result(case_id)

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No risk analysis result found. Processing may not have completed yet.",
        )

    risk_summary = _extract_risk_summary(doc)

    return RiskSummaryResponse(
        case_id=doc["case_id"],
        version=doc["version"],
        based_on=BasedOnInfo(
            mer_version=doc.get("mer_version"),
            pathology_version=doc.get("pathology_version"),
            source_freshness=doc.get("source_freshness", 0),
        ),
        summary=risk_summary["summary"],
        risk_level=risk_summary["risk_level"],
        red_flags=risk_summary.get("red_flags", []),
        contradictions=risk_summary.get("contradictions", []),
        risk_score=risk_summary.get("risk_score"),
        applicant=risk_summary.get("applicant"),
        integrity_concerns=risk_summary.get("integrity_concerns", []),
        clinical_discoveries=risk_summary.get("clinical_discoveries", []),
        created_at=doc["created_at"],
    )


# ─── GET /cases/{case_id}/risk/export-excel ──────────────────────────────────


@router.get("/{case_id}/risk/export-excel")
async def export_risk_excel(
    case_id: str,
    version: int = Query(None, description="Specific version. Omit for latest."),
    user: dict = Depends(get_current_user),
):
    """
    Download risk analysis result as an Excel (.xlsx) file.

    Multi-sheet workbook with summary, findings, abnormal labs, and
    pre-computed flags/contradictions. Dynamically generated.
    """
    await _get_case_or_404(case_id, user["id"])

    if version is not None:
        doc = await _get_result_by_version(case_id, version)
    else:
        doc = await _get_latest_result(case_id)

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No risk analysis result found. Processing may not have completed yet.",
        )

    ver = doc["version"]
    excel_bytes = generate_excel(doc, case_id, ver)
    filename = f"RiskAnalysis_{case_id}_v{ver}.xlsx"

    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
