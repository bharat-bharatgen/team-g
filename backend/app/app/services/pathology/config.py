"""
Pathology standardized parameters configuration.

Edit this file to add/remove/update parameters, normal ranges, or aliases.
The mapping prompt is dynamically built from this config.
"""

# ─── 50 Standardized Parameters ─────────────────────────────────────────────
# Each entry: { "unit", "range", "aliases" }
# - unit: standard unit for this parameter
# - range: normal reference range string
# - aliases: list of common name variations found in lab reports

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
        "Alka Phosphatases": {
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
        "Sugar": {
            "unit": "/hpf",
            "range": [None, 0],
            "aliases": [],
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

STANDARD_PARAMETERS = {
    # ── Haematology ──────────────────────────────────────────────────────
    "RBC": {
        "sample_type": "blood",
        "unit": "million/µL",
        "range": "4.5-5.5",
        "aliases": ["RBC Count", "Red Blood Cell Count", "Erythrocyte Count", "TOTAL COUNT ERYTHROCYTIC"],
    },
    "Hb%": {
        "unit": "g/dL",
        "range": "12.0-16.0",
        "aliases": ["Haemoglobin", "Hemoglobin", "Hb", "HAEMOGLOBIN"],
    },
    "Platelets": {
        "unit": "cells/µL",
        "range": "150000-410000",
        "aliases": ["Platelet Count", "Thrombocyte Count", "PLATELET COUNT"],
    },
    "WBC": {
        "unit": "cells/µL",
        "range": "4000-11000",
        "aliases": ["WBC Count", "Total Leucocyte Count", "TLC", "LEUCOCYTIC", "Total WBC Count"],
    },
    "MCV": {
        "unit": "fL",
        "range": "76-96",
        "aliases": ["Mean Corpuscular Volume", "M C V"],
    },
    "ESR": {
        "unit": "mm/hr",
        "range": "0-20",
        "aliases": ["Erythrocyte Sedimentation Rate", "E S R"],
    },
    "PCV": {
        "unit": "%",
        "range": "38-54",
        "aliases": ["Packed Cell Volume", "Hematocrit", "HCT", "Hct", "P C V"],
    },
    "MCH": {
        "unit": "pg",
        "range": "27-32",
        "aliases": ["Mean Corpuscular Hemoglobin", "Mean Corpuscular Haemoglobin", "M C H"],
    },
    "MCHC": {
        "unit": "g/dL",
        "range": "31-35",
        "aliases": ["Mean Corpuscular Hemoglobin Concentration", "Mean Corpuscular Haemoglobin Concentration", "M C H C"],
    },

    # ── Differential Count ───────────────────────────────────────────────
    "Neutrophils": {
        "unit": "%",
        "range": "40-75",
        "aliases": ["Neutrophil", "Neutrophil %", "Polymorphs"],
    },
    "Lymphocytes": {
        "unit": "%",
        "range": "20-45",
        "aliases": ["Lymphocyte", "Lymphocyte %"],
    },
    "Monocytes": {
        "unit": "%",
        "range": "1-6",
        "aliases": ["Monocyte", "Monocyte %"],
    },
    "Eosinophils": {
        "unit": "%",
        "range": "1-6",
        "aliases": ["Eosinophil", "Eosinophil %"],
    },
    "Basophils": {
        "unit": "%",
        "range": "0-2",
        "aliases": ["Basophil", "Basophil %"],
    },

    # ── Lipid Profile ────────────────────────────────────────────────────
    "HDL": {
        "unit": "mg/dL",
        "range": "40-60",
        "aliases": ["HDL Cholesterol", "HDL-C"],
    },
    "LDL": {
        "unit": "mg/dL",
        "range": "0-100",
        "aliases": ["LDL Cholesterol", "LDL-C"],
    },
    "Total Cholesterol": {
        "unit": "mg/dL",
        "range": "0-200",
        "aliases": ["Serum Cholesterol", "Cholesterol Total"],
    },
    "Triglycerides": {
        "unit": "mg/dL",
        "range": "0-150",
        "aliases": ["Serum Triglycerides", "TG"],
    },

    # ── Kidney Function ──────────────────────────────────────────────────
    "Serum Creatinine": {
        "unit": "mg/dL",
        "range": "0.7-1.3",
        "aliases": ["Creatinine"],
    },
    "BUN": {
        "unit": "mg/dL",
        "range": "7-20",
        "aliases": ["Blood Urea Nitrogen", "Urea"],
    },
    "Serum Uric Acid": {
        "unit": "mg/dL",
        "range": "3.5-7.2",
        "aliases": ["Uric Acid", "URIC ACID"],
    },

    # ── Liver Function ───────────────────────────────────────────────────
    "Serum Albumin": {
        "unit": "g/dL",
        "range": "3.5-5.5",
        "aliases": ["Albumin"],
    },
    "Serum Protein": {
        "unit": "g/dL",
        "range": "6.0-8.3",
        "aliases": ["Total Protein"],
    },
    "Alka Phosphates": {
        "unit": "U/L",
        "range": "44-147",
        "aliases": ["Alkaline Phosphatase", "ALP"],
    },
    "SGPT": {
        "unit": "U/L",
        "range": "7-56",
        "aliases": ["ALT", "Alanine Aminotransferase"],
    },
    "SGOT": {
        "unit": "U/L",
        "range": "10-40",
        "aliases": ["AST", "Aspartate Aminotransferase"],
    },
    "GGTP": {
        "unit": "U/L",
        "range": "9-48",
        "aliases": ["Gamma GT", "GGT", "Gamma Glutamyl Transferase"],
    },
    "Total Bilirubin": {
        "unit": "mg/dL",
        "range": "0.1-1.2",
        "aliases": ["Bilirubin Total"],
    },
    "Direct Bilirubin": {
        "unit": "mg/dL",
        "range": "0.0-0.3",
        "aliases": ["Bilirubin Direct", "Conjugated Bilirubin"],
    },
    "Indirect Bilirubin": {
        "unit": "mg/dL",
        "range": "0.1-0.9",
        "aliases": ["Bilirubin Indirect", "Unconjugated Bilirubin"],
    },

    # ── Blood Sugar ──────────────────────────────────────────────────────
    "Sugar": {
        "unit": "mg/dL",
        "range": "70-100",
        "aliases": ["Fasting Blood Sugar", "FBS", "Glucose Fasting"],
    },
    "RBS": {
        "unit": "mg/dL",
        "range": "70-140",
        "aliases": ["Random Blood Sugar", "Glucose Random"],
    },
    "PPBS": {
        "unit": "mg/dL",
        "range": "70-140",
        "aliases": ["Post Prandial Blood Sugar", "Glucose PP"],
    },
    "HbA1c": {
        "sample_type": "blood",
        "unit": "%",
        "range": [4.0, 6.0],
        "aliases": ["Glycated Hemoglobin", "Glycosylated Hemoglobin", "Glycated Haemoglobin"],
    },

    # ── Urine ────────────────────────────────────────────────────────────
    "Pus Cells": {
        "unit": "/hpf",
        "range": "0-5",
        "aliases": ["Pus Cells"],
    },
    "Albumin/Proteins": {
        "unit": None,
        "range": "Nil",
        "aliases": ["Urine Protein", "Urine Albumin", "Protein", "Proteins", "Albumin", "Urine Proteins"],
    },
    "Urine Sugar": {
        "unit": None,
        "range": "Nil",
        "aliases": ["Glucose Urine", "Sugar Urine", "Reducing Substances", "Urine Glucose", "Reducing Sugar"],
    },
    "Microalbumin": {
        "unit": "mg/L",
        "range": "< 30",
        "aliases": ["Microalbuminuria", "Urine Microalbumin"],
    },

    # ── Serology / Infectious ────────────────────────────────────────────
    "HBsAg": {
        "unit": None,
        "range": "Non-Reactive",
        "aliases": ["Hepatitis B Surface Antigen"],
    },
    "HIV": {
        "unit": None,
        "range": "Non-Reactive",
        "aliases": ["HIV I & II", "HIV Antibody"],
    },
    "HCV": {
        "unit": None,
        "range": "Non-Reactive",
        "aliases": ["Hepatitis C Antibody", "Anti HCV"],
    },

    # ── Thyroid ───────────────────────────────────────────────────────────
    "T3": {
        "unit": "ng/dL",
        "range": "80-200",
        "aliases": ["Triiodothyronine"],
    },
    "T4": {
        "unit": "µg/dL",
        "range": "5.1-14.1",
        "aliases": ["Thyroxine"],
    },
    "TSH": {
        "unit": "µIU/mL",
        "range": "0.27-4.20",
        "aliases": ["Thyroid Stimulating Hormone"],
    },

    # ── Special Investigations ───────────────────────────────────────────
    "ECG": {
        "unit": None,
        "range": "Normal",
        "aliases": ["Electrocardiogram", "Electrocardiography"],
    },
    "TMT": {
        "unit": None,
        "range": "Normal",
        "aliases": ["Treadmill Test", "Exercise Stress Test"],
    },
    "Nicotine": {
        "unit": "ng/mL",
        "range": "Negative",
        "aliases": ["Cotinine", "Urine Cotinine"],
    },
    "2D Echo": {
        "unit": None,
        "range": "Normal",
        "aliases": ["Echocardiogram", "Echo"],
    },
    "CXR": {
        "unit": None,
        "range": "Normal",
        "aliases": ["Chest X-Ray", "X-Ray Chest"],
    },
    "PFT": {
        "unit": None,
        "range": "Normal",
        "aliases": ["Pulmonary Function Test", "Spirometry"],
    },
    "USG": {
        "unit": None,
        "range": "Normal",
        "aliases": ["Ultrasonography", "Ultrasound"],
    },
    "PSA": {
        "unit": "ng/mL",
        "range": "0-4.0",
        "aliases": ["Prostate Specific Antigen"],
    },
    "Fundus": {
        "unit": None,
        "range": "Normal",
        "aliases": ["Fundoscopy", "Fundus Photography", "Retinal Examination"],
    },
}

# Remark is a standalone free-text field (not a test parameter)
REMARK_FIELD = "Remark"


# ─── Helper: build alias → standard name lookup ─────────────────────────────

def build_alias_map() -> dict:
    """Build a flat dict mapping every alias (lowercased) to its standard name."""
    alias_map = {}
    for std_name, info in STANDARD_PARAMETERS.items():
        alias_map[std_name.lower()] = std_name
        for alias in info.get("aliases", []):
            alias_map[alias.lower()] = std_name
    return alias_map


ALIAS_MAP = build_alias_map()


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


def build_new_params_lookup() -> dict:
    """
    Build a flat lookup dict from NEW_PARAMS.

    Returns:
        Dict mapping (standard_name, sample_type) -> param_info
        Also maps standard_name -> param_info for first match (blood priority)
    """
    lookup = {}

    # Priority order for default lookup
    priority = ["blood", "urine", "special"]

    for sample_type in priority:
        if sample_type not in NEW_PARAMS:
            continue
        for param_name, param_info in NEW_PARAMS[sample_type].items():
            # Key by (name, sample_type) for exact lookup
            lookup[(param_name, sample_type)] = param_info

            # Key by name only for default lookup (first match wins)
            if param_name not in lookup:
                lookup[param_name] = {**param_info, "_sample_type": sample_type}

    return lookup


NEW_PARAMS_LOOKUP = build_new_params_lookup()
