"""
API endpoints for Test Verification (Recommended Tests Verification).

Verifies that required tests from insurance requirements (Page 5) are present in pathology results.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from bson import ObjectId

from app.core.security import get_current_user
from app.dependencies import get_database
from app.services.test_verification.processor import (
    get_latest_result,
    complete_verification,
)
from app.api.v1.schemas.test_verification import (
    TestVerificationResultResponse,
    TestVerificationProcessResponse,
    RequiredTestResponse,
)

router = APIRouter()


# ─── Helpers ─────────────────────────────────────────────────────────────────

async def _get_case_or_404(case_id: str, user_id: str):
    """Fetch a case and verify ownership."""
    db = await get_database()
    case = await db.cases.find_one({"_id": ObjectId(case_id), "user_id": user_id})
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return case


# ─── POST /cases/{case_id}/test-verification/process ─────────────────────────

@router.post("/{case_id}/test-verification/process", response_model=TestVerificationProcessResponse)
async def trigger_test_verification(case_id: str, user: dict = Depends(get_current_user)):
    """
    Run test verification for a case.
    
    This checks if Page 5 (requirements page) exists in the MER documents,
    extracts the required tests, and compares against pathology results.
    
    Prerequisites:
    - MER must be processed first (to detect Page 5 in unmatched pages)
    - Pathology should be processed (to verify tests against)
    """
    await _get_case_or_404(case_id, user["id"])
    
    try:
        result = await complete_verification(case_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Test verification failed: {str(e)}",
        )
    
    # Handle error case
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"],
        )
    
    # Handle Page 5 detected but needs re-processing
    if result.get("page_5_detected"):
        return TestVerificationProcessResponse(
            id="",
            case_id=case_id,
            version=0,
            status="page_5_detected",
            total_required=0,
            total_found=0,
            total_missing=0,
            missing_tests=[],
            message=result.get("message", "Page 5 detected. Re-process MER for full verification."),
        )
    
    # Normal result
    status_msg = {
        "complete": "All required tests are present.",
        "missing_tests": f"{result['total_missing']} required test(s) are missing.",
        "requirements_page_not_found": "Requirements page (Page 5) not found in MER documents.",
        "extraction_failed": "Failed to extract requirements from Page 5.",
    }.get(result["status"], result["status"])
    
    return TestVerificationProcessResponse(
        id=result.get("_id", ""),
        case_id=case_id,
        version=result.get("version", 0),
        status=result["status"],
        total_required=result.get("total_required", 0),
        total_found=result.get("total_found", 0),
        total_missing=result.get("total_missing", 0),
        missing_tests=result.get("missing_tests", []),
        message=status_msg,
    )


# ─── GET /cases/{case_id}/test-verification/result ───────────────────────────

@router.get("/{case_id}/test-verification/result", response_model=TestVerificationResultResponse)
async def get_test_verification_result(
    case_id: str,
    user: dict = Depends(get_current_user),
):
    """
    Get the latest test verification result for a case.
    
    Returns the full verification result including:
    - Page 5 extraction results
    - List of required tests and their verification status
    - Summary of missing tests
    """
    await _get_case_or_404(case_id, user["id"])
    
    doc = await get_latest_result(case_id)
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No test verification result found. Run verification first.",
        )
    
    return TestVerificationResultResponse(
        id=doc["_id"],
        case_id=doc["case_id"],
        version=doc["version"],
        page_found=doc["page_found"],
        proposal_number=doc.get("proposal_number"),
        life_assured_name=doc.get("life_assured_name"),
        ins_test_remark=doc.get("ins_test_remark"),
        hi_test_remark=doc.get("hi_test_remark"),
        extraction_confidence=doc.get("extraction_confidence", 0.0),
        raw_requirements=doc.get("raw_requirements", []),
        required_tests=[
            RequiredTestResponse(**t) for t in doc.get("required_tests", [])
        ],
        total_required=doc.get("total_required", 0),
        total_found=doc.get("total_found", 0),
        total_missing=doc.get("total_missing", 0),
        missing_tests=doc.get("missing_tests", []),
        status=doc["status"],
        mer_result_version=doc.get("mer_result_version"),
        pathology_result_version=doc.get("pathology_result_version"),
        created_at=doc["created_at"],
    )
