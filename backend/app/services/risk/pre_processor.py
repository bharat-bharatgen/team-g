"""
Pre-processing for risk analysis.

Extracts and prepares data from MER and pathology results for LLM analysis.
Adds reference IDs to each data item for citation linking.
"""

import re
from typing import Any, Dict, List, Optional, Tuple


def parse_numeric(value: Any) -> Optional[float]:
    """Safely parse a numeric value, stripping unit suffixes like 'cm', 'kg'."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.replace(",", "").strip()
        match = re.match(r'^-?[\d.]+', cleaned)
        if match:
            try:
                return float(match.group())
            except ValueError:
                return None
    return None


def extract_patient_info(mer_data: Dict) -> Dict:
    """Extract basic patient demographics from MER data."""
    page1 = mer_data.get("page_1", {})
    header = page1.get("header", {})

    return {
        "name": header.get("Full Name of Life Assured", {}).get("value"),
        "age": parse_numeric(header.get("Age", {}).get("value")),
        "gender": header.get("Gender", {}).get("value"),
        "dob": header.get("Date of Birth", {}).get("value"),
        "proposal_number": header.get("Proposal Number / Policy Number", {}).get("value"),
    }


# ─── Reference Generation ────────────────────────────────────────────────────

def add_pathology_refs(pathology_data: Dict) -> Tuple[Dict, Dict]:
    """
    Add reference IDs to pathology tests.
    
    Returns:
        (pathology_data_with_refs, references_lookup)
    """
    if not pathology_data:
        return None, {}
    
    references = {}
    tests_with_refs = []
    
    for test in pathology_data.get("tests", []):
        std_name = test.get("standard_name")
        if not std_name:
            continue
            
        # Create ref ID: PATH:<standard_name>
        ref_id = f"PATH:{std_name}"
        
        # Add ref to test
        test_with_ref = {**test, "ref": ref_id}
        tests_with_refs.append(test_with_ref)
        
        # Build reference lookup (include page number for PDF navigation)
        references[ref_id] = {
            "source": "pathology",
            "param": std_name,
            "value": test.get("value"),
            "unit": test.get("unit"),
            "page": test.get("source_page"),  # Page number for PDF navigation
        }
    
    return {
        **pathology_data,
        "tests": tests_with_refs,
    }, references


def add_mer_refs(mer_data: Dict) -> Tuple[Dict, Dict]:
    """
    Add reference IDs to MER fields.
    
    Returns:
        (mer_data_with_refs, references_lookup)
    """
    if not mer_data:
        return None, {}
    
    references = {}
    mer_with_refs = {}
    
    for page_key in ["page_1", "page_2", "page_3", "page_4"]:
        page = mer_data.get(page_key)
        if not page:
            continue
            
        # Extract page number (1, 2, 3, 4)
        page_num = page_key.split("_")[1]
        page_with_refs = {}
        
        for section_key, section_data in page.items():
            if not isinstance(section_data, dict):
                page_with_refs[section_key] = section_data
                continue
                
            section_with_refs = {}
            
            for field_key, field_data in section_data.items():
                if not isinstance(field_data, dict):
                    section_with_refs[field_key] = field_data
                    continue
                
                # Create short ref ID
                # MER:P1:header:name or MER:P1:Q3a
                if section_key == "questions":
                    ref_id = f"MER:P{page_num}:Q{field_key}"
                else:
                    # Shorten field key for header/physical_measurement
                    short_field = field_key[:20].replace(" ", "_")
                    ref_id = f"MER:P{page_num}:{section_key}:{short_field}"
                
                # Add ref to field
                field_with_ref = {**field_data, "ref": ref_id}
                section_with_refs[field_key] = field_with_ref
                
                # Build reference lookup
                references[ref_id] = {
                    "source": "mer",
                    "page": int(page_num),
                    "section": section_key,
                    "field": field_key,
                    "value": field_data.get("value") or field_data.get("answer"),
                }
            
            page_with_refs[section_key] = section_with_refs
        
        mer_with_refs[page_key] = page_with_refs
    
    return mer_with_refs, references


def calculate_bmi(mer_data: Dict) -> Dict:
    """Calculate BMI from physical measurements in MER Page 4."""
    page4 = mer_data.get("page_4", {})
    physical = page4.get("physical_measurement", {})

    height_cm = parse_numeric(physical.get("height_cm", {}).get("value"))
    weight_kg = parse_numeric(physical.get("weight_kg", {}).get("value"))

    if height_cm and weight_kg and height_cm > 0:
        height_m = height_cm / 100
        bmi = round(weight_kg / (height_m**2), 1)

        # Categorize
        if bmi < 18.5:
            category = "underweight"
        elif bmi < 25:
            category = "normal"
        elif bmi < 30:
            category = "overweight"
        else:
            category = "obese"

        return {
            "value": bmi,
            "category": category,
            "height_cm": height_cm,
            "weight_kg": weight_kg,
            "source": "derived.bmi",
        }

    return {"value": None, "category": None, "source": "derived.bmi"}


# Critical thresholds - ONLY flag truly dangerous values
CRITICAL_THRESHOLDS = {
    "FBS": {"critical_high": 400, "unit": "mg/dL"},
    "RBS": {"critical_high": 500, "unit": "mg/dL"},
    "HbA1c": {"critical_high": 12, "unit": "%"},
    "Serum Creatinine": {"critical_high": 5, "unit": "mg/dL"},
    "Total Bilirubin": {"critical_high": 10, "unit": "mg/dL"},
    "SGPT": {"critical_high": 500, "unit": "U/L"},
    "SGOT": {"critical_high": 500, "unit": "U/L"},
    "Hb%": {"critical_low": 7, "unit": "g/dL"},
    "Platelets": {"critical_low": 50000, "unit": "cells/µL"},
}


def flag_critical_values(pathology_data: Dict) -> List[Dict]:
    """
    Flag ONLY critical/life-threatening values.
    Leave borderline/elevated values for LLM to interpret.
    """
    critical_flags = []
    tests = pathology_data.get("tests", [])

    for test in tests:
        std_name = test.get("standard_name")
        if std_name not in CRITICAL_THRESHOLDS:
            continue

        value = parse_numeric(test.get("value"))
        if value is None:
            continue

        threshold = CRITICAL_THRESHOLDS[std_name]

        # Check critical high
        if "critical_high" in threshold and value >= threshold["critical_high"]:
            critical_flags.append(
                {
                    "test": std_name,
                    "value": test.get("value"),
                    "unit": test.get("unit"),
                    "threshold": f">= {threshold['critical_high']}",
                    "severity": "critical",
                    "source": f"pathology.{std_name}",
                }
            )

        # Check critical low
        if "critical_low" in threshold and value <= threshold["critical_low"]:
            critical_flags.append(
                {
                    "test": std_name,
                    "value": test.get("value"),
                    "unit": test.get("unit"),
                    "threshold": f"<= {threshold['critical_low']}",
                    "severity": "critical",
                    "source": f"pathology.{std_name}",
                }
            )

    return critical_flags


def detect_direct_contradictions(mer_data: Dict, pathology_data: Dict) -> List[Dict]:
    """
    Detect ONLY obvious, clear-cut contradictions.
    Leave subtle inconsistencies for LLM to identify.
    """
    contradictions = []

    # Helper to get MER question answer
    def get_mer_answer(question_key: str) -> Optional[str]:
        for page_key in ["page_1", "page_2", "page_3"]:
            page = mer_data.get(page_key, {})
            questions = page.get("questions", {})
            for q_name, q_data in questions.items():
                if question_key.lower() in q_name.lower():
                    return q_data.get("answer")
        return None

    # Helper to get pathology value
    def get_path_value(test_name: str) -> Optional[float]:
        for test in pathology_data.get("tests", []):
            if test.get("standard_name") == test_name:
                return parse_numeric(test.get("value"))
        return None

    # Rule 1: Denied diabetes but HbA1c >= 8% (clearly diabetic with poor control)
    diabetes_answer = get_mer_answer("diabetes")
    hba1c = get_path_value("HbA1c")
    if diabetes_answer == "No" and hba1c and hba1c >= 8.0:
        contradictions.append(
            {
                "type": "direct_contradiction",
                "description": f"Patient denied diabetes but HbA1c is {hba1c}% (clearly diabetic range)",
                "severity": "high",
                "sources": {
                    "disclosure": "mer.page1.questions.3a",
                    "finding": "pathology.HbA1c",
                },
            }
        )

    # Rule 2: Denied diabetes but FBS >= 200
    fbs = get_path_value("FBS")
    if diabetes_answer == "No" and fbs and fbs >= 200:
        contradictions.append(
            {
                "type": "direct_contradiction",
                "description": f"Patient denied diabetes but FBS is {fbs} mg/dL (clearly diabetic)",
                "severity": "high",
                "sources": {
                    "disclosure": "mer.page1.questions.3a",
                    "finding": "pathology.FBS",
                },
            }
        )

    # Rule 3: Denied kidney disease but creatinine >= 3
    kidney_answer = get_mer_answer("kidney")
    creatinine = get_path_value("Serum Creatinine")
    if kidney_answer == "No" and creatinine and creatinine >= 3.0:
        contradictions.append(
            {
                "type": "direct_contradiction",
                "description": f"Patient denied kidney disease but creatinine is {creatinine} mg/dL (significant renal impairment)",
                "severity": "high",
                "sources": {
                    "disclosure": "mer.page2.questions.3k",
                    "finding": "pathology.Serum Creatinine",
                },
            }
        )

    return contradictions


def prepare_llm_input(
    mer_data: Optional[Dict], pathology_data: Optional[Dict]
) -> Tuple[Dict, Dict]:
    """
    Prepare the input package for the LLM.
    Minimal pre-processing - let LLM do the heavy lifting.
    Adds reference IDs to each field for citation linking.

    Args:
        mer_data: MER pages data (can be None if not uploaded)
        pathology_data: Pathology standardized data (can be None if not uploaded)

    Returns:
        Tuple of (llm_input, references_lookup)
        - llm_input: Dict with patient_info, mer_data, pathology_data, and pre_computed flags
        - references_lookup: Dict mapping ref IDs to source info
    """
    patient_info = {}
    bmi_info = {"value": None, "category": None}
    critical_flags = []
    direct_contradictions = []
    all_references = {}

    # Add refs to MER data
    mer_with_refs = None
    if mer_data:
        mer_with_refs, mer_refs = add_mer_refs(mer_data)
        all_references.update(mer_refs)
        patient_info = extract_patient_info(mer_data)
        bmi_info = calculate_bmi(mer_data)

    # Add refs to pathology data
    path_with_refs = None
    if pathology_data:
        path_with_refs, path_refs = add_pathology_refs(pathology_data)
        all_references.update(path_refs)
        critical_flags = flag_critical_values(pathology_data)

    # Detect contradictions if both are available
    if mer_data and pathology_data:
        direct_contradictions = detect_direct_contradictions(mer_data, pathology_data)

    llm_input = {
        "patient_info": {**patient_info, "bmi": bmi_info},
        "mer_data": mer_with_refs,
        "pathology_data": path_with_refs,
        "pre_computed": {
            "critical_flags": critical_flags,
            "direct_contradictions": direct_contradictions,
        },
    }

    return llm_input, all_references
