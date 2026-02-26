"""
API schemas for Test Verification endpoints.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class RequiredTestResponse(BaseModel):
    """A single required test with verification status."""
    category: str
    test_name: str
    found: bool
    pathology_value: Optional[str] = None


class TestVerificationResultResponse(BaseModel):
    """Full test verification result."""
    id: str
    case_id: str
    version: int
    
    # Page 5 extraction
    page_found: bool
    proposal_number: Optional[str] = None
    life_assured_name: Optional[str] = None
    ins_test_remark: Optional[str] = None
    hi_test_remark: Optional[str] = None
    extraction_confidence: float = 0.0
    
    # Parsed requirements
    raw_requirements: List[str] = []
    
    # Verification results
    required_tests: List[RequiredTestResponse] = []
    
    # Summary
    total_required: int = 0
    total_found: int = 0
    total_missing: int = 0
    missing_tests: List[str] = []
    status: str
    
    # Metadata
    mer_result_version: Optional[int] = None
    pathology_result_version: Optional[int] = None
    created_at: datetime


class TestVerificationProcessResponse(BaseModel):
    """Response for test verification processing."""
    id: str
    case_id: str
    version: int
    status: str
    total_required: int
    total_found: int
    total_missing: int
    missing_tests: List[str]
    message: str
