"""
Test Verification Result Model.

Stores the result of comparing required tests (from Page 5) against actual pathology results.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RequiredTest(BaseModel):
    """A single required test from insurance requirements."""
    category: str              # Original category (e.g., "Category A", "HbA1c")
    test_name: str            # Individual test name (e.g., "Total Cholesterol")
    found: bool = False       # Whether test was found in pathology
    pathology_value: Optional[str] = None  # Value from pathology (if found)


class TestVerificationResultModel(BaseModel):
    """Result of test verification."""
    case_id: str
    version: int = 1
    
    # Page 5 extraction results
    page_found: bool = False
    proposal_number: Optional[str] = None
    life_assured_name: Optional[str] = None
    ins_test_remark: Optional[str] = None
    hi_test_remark: Optional[str] = None
    extraction_confidence: float = 0.0
    
    # Parsed requirements
    raw_requirements: List[str] = Field(default_factory=list)  # As parsed from ins_test_remark
    
    # Verification results
    required_tests: List[RequiredTest] = Field(default_factory=list)
    
    # Summary
    total_required: int = 0
    total_found: int = 0
    total_missing: int = 0
    missing_tests: List[str] = Field(default_factory=list)  # Test names that are missing
    status: str = "unknown"  # "complete" | "missing_tests" | "requirements_page_not_found"
    
    # Metadata
    mer_result_version: Optional[int] = None
    pathology_result_version: Optional[int] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
