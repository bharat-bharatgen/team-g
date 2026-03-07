"""
Test Verification Configuration.

Maps insurance test categories to individual test names.
These test names should match the standardized parameter names in pathology config.
"""

# Category → List of tests mapping
# Test names must match the standard_name values produced by the v2 extract prompt
CATEGORY_TESTS = {
    "HbA1c": ["HbA1c"],
    
    "ECG": ["ECG"],
    
    "TMT": ["TMT"],
    
    "Category A": [
        "Total Cholesterol",
        "LDL",
        "HDL",
        "Triglycerides",
        "ESR",
        "Platelets",
        "Hb%",
        "RBC",
        "MCV",
        "WBC",
    ],
    
    "Category B": [
        "Serum Uric Acid",
        "BUN",
        "Serum Creatinine",
        "HBsAg",
        "Serum Albumin",
        "Serum Protein",
        "Total Bilirubin",
        "Direct Bilirubin",
        "Indirect Bilirubin",
        "Alka Phosphates",
        "SGPT",
        "SGOT",
        "GGTP",
    ],
    
    "Category C": [
        "RBS",
        # Urine tests - these map to pathology urine section
        "Pus Cells",
        "Urine Sugar",
        "Albumin/Proteins",
    ],
    
    "CAT D": ["HIV"],
    
    # Special tests
    "PSA": ["PSA"],
    "USG": ["USG"],
    "Echo": ["2D Echo"],
    "CXR": ["CXR"],
    "Microalbumin": ["Microalbumin"],
    "Fundoscopy": ["Fundus"],
    "T3": ["T3"],
    "T4": ["T4"],
    "TSH": ["TSH"],
    "Nicotine": ["Nicotine"],
    "PFT": ["PFT"],
}

# Aliases for parsing Ins Test Remark
# Maps variations to canonical category names
CATEGORY_ALIASES = {
    # Category A variations
    "category a": "Category A",
    "cat a": "Category A",
    "a": "Category A",
    
    # Category B variations
    "category b": "Category B",
    "cat b": "Category B",
    "b": "Category B",
    
    # Category C variations
    "category c": "Category C",
    "cat c": "Category C",
    "c": "Category C",
    
    # Category D variations
    "category d": "CAT D",
    "cat d": "CAT D",
    "d": "CAT D",
    
    # HbA1c variations
    "hba1c": "HbA1c",
    "hb a1c": "HbA1c",
    "hba 1c": "HbA1c",
    "glycated hemoglobin": "HbA1c",
    
    # ECG variations
    "ecg": "ECG",
    "electrocardiogram": "ECG",
    
    # TMT variations
    "tmt": "TMT",
    "treadmill": "TMT",
    "treadmill test": "TMT",
    "tread mill": "TMT",
    "tread mill test": "TMT",
    "exercise stress test": "TMT",
    
    # Special tests
    "psa": "PSA",
    "usg": "USG",
    "ultrasound": "USG",
    "echo": "Echo",
    "2d echo": "Echo",
    "echocardiogram": "Echo",
    "cxr": "CXR",
    "chest x-ray": "CXR",
    "x-ray chest": "CXR",
    "microalbumin": "Microalbumin",
    "fundoscopy": "Fundoscopy",
    "fundus": "Fundoscopy",
    "t3": "T3",
    "t4": "T4",
    "tsh": "TSH",
    "thyroid": "TSH",  # Usually refers to TSH
    "nicotine": "Nicotine",
    "cotinine": "Nicotine",
    "pft": "PFT",
    "spirometry": "PFT",
}

# Keywords to identify Page 5 (Requirements page)
PAGE_5_IDENTIFIERS = [
    "Ins Test Remark",
    "HI Test Remark",
    "Life to be Assured",
    "FRS Details",
    "Confidence",
    "Similarity",
    "Propsoal No",
    "Proposal No",
]


def normalize_category(raw_category: str) -> str | None:
    """
    Normalize a raw category string to canonical form.
    
    Args:
        raw_category: Raw category string from Ins Test Remark
        
    Returns:
        Canonical category name or None if not recognized
    """
    import re
    
    normalized = raw_category.strip().lower()
    
    # Direct match in aliases
    if normalized in CATEGORY_ALIASES:
        return CATEGORY_ALIASES[normalized]
    
    # Direct match in CATEGORY_TESTS (case-insensitive)
    for canonical in CATEGORY_TESTS:
        if canonical.lower() == normalized:
            return canonical
    
    # Strip parenthetical content and try again
    # e.g., "TREAD MILL TEST (TMT)" → "tread mill test"
    stripped = re.sub(r'\s*\([^)]*\)\s*', '', normalized).strip()
    if stripped and stripped != normalized:
        if stripped in CATEGORY_ALIASES:
            return CATEGORY_ALIASES[stripped]
        for canonical in CATEGORY_TESTS:
            if canonical.lower() == stripped:
                return canonical
    
    # Check if parenthetical content itself is a match
    # e.g., "(TMT)" → "tmt"
    paren_match = re.search(r'\(([^)]+)\)', normalized)
    if paren_match:
        paren_content = paren_match.group(1).strip().lower()
        if paren_content in CATEGORY_ALIASES:
            return CATEGORY_ALIASES[paren_content]
        for canonical in CATEGORY_TESTS:
            if canonical.lower() == paren_content:
                return canonical
    
    return None


def expand_categories(categories: list[str]) -> list[str]:
    """
    Expand a list of categories to individual test names.
    
    Args:
        categories: List of category names (e.g., ["Category A", "HbA1c"])
        
    Returns:
        List of individual test names
    """
    tests = []
    seen = set()
    
    for category in categories:
        canonical = normalize_category(category)
        if canonical and canonical in CATEGORY_TESTS:
            for test in CATEGORY_TESTS[canonical]:
                if test not in seen:
                    tests.append(test)
                    seen.add(test)
    
    return tests
