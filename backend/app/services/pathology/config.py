"""
Pathology parameters configuration (NEW_PARAMS).

Used for:
- Unit/range sanity-check reference in the v2 extract prompt
- Post-extraction range comparison (config_range vs report range)

NOTE: The canonical list of standard parameter names and aliases lives in the
v2 prompt (extract.py build_system_prompt_v2). Edits to parameter names or
aliases must be made there. This file only provides numeric ranges and units.
"""

# ─── Parameters by sample type ──────────────────────────────────────────────
# Each entry: { "unit", "range", "aliases" }
# - unit: standard unit for this parameter
# - range: normal reference range (list, dict, or string)
# - aliases: common name variations (used in the unit/range reference table)

NEW_PARAMS = {
    "blood": {
        "HbA1c": {
            "unit": "%",
            "range": [4.0, 6.0],
            "aliases": ["Glycated Hemoglobin", "Glycosylated Hemoglobin", "Glycated Haemoglobin"],
        },
        "RBS": {
            "unit": "mg/dL",
            "range": [70, 140],
            "aliases": ["Random Blood Sugar", "Glucose Random"],
        },
        "PPBS": {
            "unit": "mg/dL",
            "range": [70, 140],
            "aliases": ["Post Prandial Blood Sugar", "Glucose PP"],
        },
        "Total Cholesterol": {
            "unit": "mg/dL",
            "range": [135, 280],
            "aliases": ["Serum Cholesterol", "Cholesterol Total"],
        },
        "LDL": {
            "unit": "mg/dL",
            "range": [60, 160],
            "aliases": ["LDL Cholesterol", "LDL-C"],
        },
        "HDL": {
            "unit": "mg/dL",
            "range": [35, 100],
            "aliases": ["HDL Cholesterol", "HDL-C"],
        },
        "Triglycerides": {
            "unit": "mg/dL",
            "range": [10, 200],
            "aliases": ["Serum Triglycerides", "TG"],
        },
        "ESR": {
            "unit": "mm/hr",
            "range": [None, 40],
            "aliases": ["Erythrocyte Sedimentation Rate", "E S R"],
        },
        "Platelets": {
            "unit": "cells/µL",
            "range": [150000, 400000],
            "aliases": ["Platelet Count", "Thrombocyte Count", "PLATELET COUNT"],
        },
        "Hb%": {
            "unit": "g/dL",
            "range": {
                "male": [13.0, 18.0],
                "female": [11.5, 17.0],
            },
            "aliases": ["Haemoglobin", "Hemoglobin", "Hb", "HAEMOGLOBIN"],
        },
        "RBC": {
            "unit": "cells/µL",
            "range": [4000000, 5000000],
            "aliases": ["RBC Count", "Red Blood Cell Count", "Erythrocyte Count", "TOTAL COUNT ERYTHROCYTIC"],
        },
        "WBC": {
            "unit": "cells/µL",
            "range": [None, 12000],
            "aliases": ["WBC Count", "Total Leucocyte Count", "TLC", "LEUCOCYTIC", "Total WBC Count"],
        },
        "MCV": {
            "unit": "fL",
            "range": [75, 102],
            "aliases": ["Mean Corpuscular Volume", "M C V"],
        },
        "MCH": {
            "unit": "pg",
            "range": [],
            "aliases": ["Mean Corpuscular Hemoglobin", "Mean Corpuscular Haemoglobin", "M C H"],
        },
        "MCHC": {
            "unit": "g/dL",
            "range": [],
            "aliases": ["Mean Corpuscular Hemoglobin Concentration", "Mean Corpuscular Haemoglobin Concentration", "M C H C"],
       },
        "Neutrophils": {
            "unit": "%",
            "range": [],
            "aliases": ["Neutrophil", "Neutrophil %", "Polymorphs"],
        },
        "Lymphocytes": {
            "unit": "%",
            "range": [],
            "aliases": ["Lymphocyte", "Lymphocyte %"],
        },
        "Monocytes": {
            "unit": "%",
            "range": [],
            "aliases": ["Monocyte", "Monocyte %"],
        },
        "Eosinophils": {
            "unit": "%",
            "range": [],
            "aliases": ["Eosinophil", "Eosinophil %"],
        },
        "Basophils": {
            "unit": "%",
            "range": [],
            "aliases": ["Basophil", "Basophil %"],
        },
        "Serum Uric Acid": {
            "unit": "mg/dL",
            "range": [2.5, 8.5],
            "aliases": ["Uric Acid", "URIC ACID"],
        },
        "BUN": {
            "unit": "mg/dL",
            "range": [6, 25],
            "aliases": ["Blood Urea Nitrogen", "Urea"],
        },
        "HBsAg": {
            "unit": None,
            "range": "No",
            "aliases": ["Hepatitis B Surface Antigen"],
        },
        "Serum Albumin": {
            "unit": "g/dL",
            "range": [3.5, 5.0],
            "aliases": ["Albumin"],
        },
        "Serum Protein": {
            "unit": "g/dL",
            "range": [6.0, 8.5],
            "aliases": ["Total Protein"],
        },
        "Total Bilirubin": {
            "unit": "mg/dL",
            "range": [0.0, 1.4],
            "aliases": ["Bilirubin Total"],
        },
        "Indirect Bilirubin": {
            "unit": "mg/dL",
            "range": [0.0, 1.0],
            "aliases": ["Bilirubin Indirect", "Unconjugated Bilirubin"],
        },
        "Direct Bilirubin": {
            "unit": "mg/dL",
            "range": [0.0, 0.4],
            "aliases": ["Bilirubin Direct", "Conjugated Bilirubin"],
        },
        "Alka Phosphates": {
            "unit": "U/L",
            "range": [78, 220],
            "aliases": ["Alkaline Phosphatase", "ALP"],
        },
        "SGPT": {
            "unit": "U/L",
            "range": [0, 60],
            "aliases": ["ALT", "Alanine Aminotransferase"],
        },
        "SGOT": {
            "unit": "U/L",
            "range": [0, 40],
            "aliases": ["AST", "Aspartate Aminotransferase"],
        },
        "GGTP": {
            "unit": "U/L",
            "range": [0, 37],
            "aliases": ["Gamma GT", "GGT", "Gamma Glutamyl Transferase"],
        },
        "HIV": {
            "unit": None,
            "range": "No",
            "aliases": ["HIV I & II", "HIV Antibody"],
        },
        "PSA": {
            "unit": "ng/mL",
            "range": [0, 4.0],
            "aliases": ["Prostate Specific Antigen"],
        },
        "T3": {
            "unit": "ng/dL",
            "range": [],
            "aliases": ["Triiodothyronine"],
        },
        "T4": {
            "unit": "µg/dL",
            "range": [],
            "aliases": ["Thyroxine"],
        },
        "TSH": {
            "unit": "µIU/mL",
            "range": [],
            "aliases": ["Thyroid Stimulating Hormone"],
        },
    },
    "urine": {
        "RBC": {
            "unit": "/hpf",
            "range": [None, 0],
            "aliases": [],
        },
        "Pus Cells": {
            "unit": "/hpf",
            "range": [0, 20],
            "aliases": [],
        },
        "Urine Sugar": {
            "unit": "/hpf",
            "range": [None, 0],
            "aliases": ["Sugar", "Glucose"],
        },
        "Albumin/Proteins": {
            "unit": None,
            "range": [None, 0],
            "aliases": ["Urine Protein", "Urine Albumin", "Protein", "Proteins", "Albumin", "Urine Proteins"],
        },
        "Microalbumin": {
            "unit": "mg/dL",
            "range": [],
            "aliases": ["Microalbumin"],
        },
    },
    "special": {
        "ECG": {
            "unit": None,
            "range": [],
            "aliases": ["Electrocardiogram", "Electrocardiography"],
        },
        "TMT": {
            "unit": None,
            "range": [],
            "aliases": ["Treadmill Test", "Exercise Stress Test"],
        },
        "Nicotine": {
            "unit": "ng/mL",
            "range": [],
            "aliases": ["Cotinine", "Urine Cotinine"],
        },
        "CXR": {
            "unit": None,
            "range": [],
            "aliases": ["Chest X-Ray", "X-Ray Chest"],
        },
        "PFT": {
            "unit": None,
            "range": [],
            "aliases": ["Pulmonary Function Test", "Spirometry"],
        },
        "USG": {
            "unit": None,
            "range": [],
            "aliases": ["Ultrasonography", "Ultrasound"],
        },
        "Fundus": {
            "unit": None,
            "range": [],
            "aliases": ["Fundus Photography"],
        },
    }
}

# ─── Helper: lookup range from NEW_PARAMS ────────────────────────────────────

def get_config_range(
    standard_name: str,
    sample_type: str = None,
    gender: str = "male",
) -> dict:
    """
    Look up the range and unit from NEW_PARAMS for a given parameter.

    Args:
        standard_name: The standardized parameter name (e.g., "RBC", "Hb%")
        sample_type: Optional sample type to disambiguate (e.g., "blood", "urine")
        gender: "male" or "female" for gender-specific ranges

    Returns:
        Dict with "range" (raw value from config) and "unit" keys, or empty dict if not found.
    """
    if not standard_name:
        return {}

    # Search order: exact sample_type match, then blood, then urine, then special
    search_order = []
    if sample_type:
        search_order.append(sample_type)
    # Add remaining in priority order
    for st in ["blood", "urine", "special"]:
        if st not in search_order:
            search_order.append(st)

    for st in search_order:
        if st in NEW_PARAMS and standard_name in NEW_PARAMS[st]:
            param_info = NEW_PARAMS[st][standard_name]
            return {
                "range": param_info.get("range"),
                "unit": param_info.get("unit"),
            }

    return {}


