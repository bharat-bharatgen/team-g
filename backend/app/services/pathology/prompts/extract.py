"""
Pathology parameter mapping prompt — Step 2 (Text-only model).

Maps OCR-extracted test data to 50 standardized parameters.
The prompt is dynamically built from pathology_config.py so that
adding/changing parameters only requires editing the config file.
"""

from app.services.llm.config import LLMCallConfig
from app.services.pathology.config import STANDARD_PARAMETERS


CONFIG = LLMCallConfig(
#    base_url="http://10.67.18.3:8002/v1/chat/completions",
#    model="Qwen/Qwen3-14B",
    base_url="https://apps.bharatgen.dev/inference/v1/chat/completions",
    #model="qwen3-14b",
    model="gpt-oss-120b",
    temperature=0.0,
    response_format="json_object",
    top_p=1,
    top_k=1,
    seed=133,
)


def _build_param_schema() -> str:
    """Build the JSON schema section showing all 50 params with null defaults."""
    lines = []
    for name in STANDARD_PARAMETERS:
        lines.append(
            f'  "{name}": {{"value": null, "unit": null, "range": null, '
            f'"reference_name": null, "flag": null, "method": null}}'
        )
    lines.append('  "Remark": null')
    lines.append('  "unmatched_tests": []')
    return "{\n" + ",\n".join(lines) + "\n}"


def _build_mapping_rules() -> str:
    """Build the alias mapping rules section from config."""
    lines = []
    for std_name, info in STANDARD_PARAMETERS.items():
        aliases = info.get("aliases", [])
        if aliases:
            alias_str = ", ".join(aliases)
            lines.append(f"- {alias_str} → {std_name}")
    return "\n".join(lines)


def _build_range_reference() -> str:
    """Build a reference table of normal ranges for the LLM."""
    lines = []
    for name, info in STANDARD_PARAMETERS.items():
        unit = info.get("unit") or ""
        rng = info.get("range") or ""
        lines.append(f"- {name}: {rng} {unit}".strip())
    return "\n".join(lines)


def build_system_prompt() -> str:
    """Dynamically build the full system prompt from pathology_config."""
    param_schema = _build_param_schema()
    mapping_rules = _build_mapping_rules()
    range_ref = _build_range_reference()

    return f"""You are a medical data extraction system. Given OCR-extracted JSON data from pathology report pages, map the test results to standardized parameter names.

<output_schema>
Return a JSON object with these standardized parameters + unmatched_tests array. Each parameter is an object with: value, unit, range, reference_name, flag, method.
Set any missing field to null.

IMPORTANT: Any test from the input that does NOT map to one of the parameters below MUST be added to "unmatched_tests" array.

{param_schema}

The "unmatched_tests" array should contain any tests NOT matching the standard parameters above.
Each unmatched test object should have:
{{
  "name": "<original test name from report>",
  "value": "<test value>",
  "unit": "<unit if present>",
  "range": "<reference range if present>",
  "flag": "<low/high/normal or null>",
  "method": "<estimation/calculation method if present>",
  "section_path": ["<section>", "<subsection>", ...]
}}
</output_schema>

<mapping_rules>
Map these common test name variations to the standardized names:
{mapping_rules}
</mapping_rules>

<normal_ranges_reference>
Standard normal ranges (for context, do NOT use these to calculate flags — only extract flags explicitly marked in the report):
{range_ref}
</normal_ranges_reference>

<field_mapping>
For standard parameters:
- value: The test result value (as string)
- unit: The measurement unit
- range: The reference range as a list of two numbers (e.g., [4.5, 5.5]). If not present, set to []. If one-sided range eg. <40, then set to [None, 40]. If one-sided range eg. >30, then set to [30, None].
- reference_name: The original test name as it appeared in the report
- flag: "low", "high", "normal", or null (ONLY if explicitly marked)
- method: The estimation/calculation method (e.g., "Cyanmethemoglobin", "Westergren Method")

For unmatched_tests:
- name: The original test name
- value, unit, range, flag, method: as above
- section_path: Array of section headers the test belongs to
</field_mapping>

<value_normalization>
CRITICAL: All numeric values must be parsable by code.

1. Remove thousand separators:
   - "1.78.000" → "178000" (Indian dot notation)
   - "6,600" → "6600" (Western comma notation)
   - "1,78,000" → "178000" (Indian comma notation)

2. Keep single decimal point for actual decimals: "13.19" → "13.19"

3. Convert lakhs/millions to base units:
   - "1.78" with "lakhs/cu.mm" → value: "178000", unit: "cells/µL"

4. Strip leading zeros: "09" → "9"

5. Separate percentage from value: "67 %" → value: "67", unit: "%"

6. Handle non-numeric values as-is: "Negative", "Positive", "Trace", "Normal"

7. Range normalization: extract only numeric range, keep consistent with value units
</value_normalization>

Return ONLY the JSON object. No explanations or markdown."""


def build_system_prompt_v2() -> str:
    return """You are a medical data extraction system. Given OCR-extracted text from a single pathology report page, extract and standardize test results.

<input_format>
You will receive OCR-extracted text from a SINGLE PAGE that may contain:
- Structured tables with headers (Test Name | Value | Unit | Range | Flag)
- Section headers like "HEMATOLOGY", "BIOCHEMISTRY", "LIVER FUNCTION TEST"
- Mixed formatting, line breaks, and potential OCR errors
- Values with various notations (Indian comma format, Western commas, decimals)
</input_format>

<output_schema>
Return a JSON object with a single "tests" array. Process each test sequentially and add to the array immediately.

{
  "tests": [
    {
      "sample_type": "<'blood'/'urine'/'serum'/'stool' or null>",
      "standard_name": "<standard param name if matched, null if unmatched>",
      "original_name": "<test name exactly as in report>",
      "value": "<normalized value>",
      "unit": "<standardized unit or null>",
      "range": "<reference range or null>",
      "flag": "<'low'/'high'/'normal' if marked, else null>",
      "method": "<method if stated, else null>",
      "status": "<'matched' or 'unmatched'>"
    }
  ]
}
</output_schema>

<workflow>
Process each test from the input ONE AT A TIME:

For EACH test found in the report:
1. Determine sample_type from context (section header, units)
2. Check if test name matches any STANDARD PARAMETER (see categories below)
3. If MATCH found:
   - Set standard_name = the matched parameter name
   - Set status = "matched"
   - Convert the values in report so that the unit matches with the standard parameter unit.
4. If NO MATCH:
   - Set standard_name = null
   - Set status = "unmatched"
5. Add the test object to the "tests" array immediately
6. Never skip any test, if not found in STANDARD PARAMETERS, add it as unmatched
7. Move to the next test

</workflow>

<standard_parameters_by_category>
Check against these 69 standard parameters organized by category:

HEMATOLOGY (14): RBC, Hb%, Platelets, WBC, MCV, ESR, PCV, MCH, MCHC, Neutrophils, Lymphocytes, Monocytes, Eosinophils, Basophils

LIPID PROFILE (5): HDL, LDL, VLDL, Total Cholesterol, Triglycerides

KIDNEY FUNCTION (4): Serum Creatinine, BUN, Serum Uric Acid, Serum Calcium

LIVER FUNCTION (11): Serum Albumin, Serum Globulin, Serum Protein, A/G Ratio, Alka Phosphates, SGPT, SGOT, GGTP, Total Bilirubin, Direct Bilirubin, Indirect Bilirubin

DIABETES (4): FBS, RBS, PPBS, HbA1c

THYROID (3): T3, T4, TSH

SEROLOGY (3): HBsAg, HIV, HCV

URINE PHYSICAL (5): Volume, Color, Appearance, Specific Gravity, Reaction

URINE CHEMICAL (7): Sugar, Pus Cells, Albumin/Proteins, Bile Salts, Bile Pigments, Ketones, Urobilinogen

URINE MICROSCOPIC (5): Urine RBC, Epithelial Cells, Casts, Crystals, Bacteria

OTHER (8): ECG, TMT, Nicotine, 2D Echo, CXR, PFT, USG, PSA
</standard_parameters_by_category>

<value_normalization>
Apply these rules IN ORDER:

STEP 1: Identify unit context and convert to base units
- If unit contains "lakh" or "lac": multiply value by 100,000, set unit to "cells/µL"
- If unit contains "million": multiply value by 1,000,000, set unit to "cells/µL"
- Convert corresponding range using same multiplier
- Examples:
  * Value "1.78 lakhs/cu.mm", Range "1.5-4.0" → value: "178000", range: "150000-400000", unit: "cells/µL"
  * Value "4.31 millions/cu.mm", Range "3.8-5.8" → value: "4310000", range: "3800000-5800000", unit: "cells/µL"

STEP 2: Remove thousand separators
- Indian comma notation: "1,78,000" → "178000", "6,50,000" → "650000"
- Western comma notation: "6,600" → "6600"
- Dot notation (rare): "1.78.000" → "178000"
- Preserve decimals: "13.19" stays "13.19", "0.5" stays "0.5"

STEP 3: Strip leading zeros
- "09" → "9", "007.5" → "7.5"

STEP 4: Normalize ranges
- Apply same conversion as values (if lakhs/millions, convert range too)
- Keep as numeric only: "150000-400000" (no units in range string)
</value_normalization>

<unit_standardization>
Apply these conversions:

VOLUME UNITS:
- cu.mm, /cmm, mm³, per cubic mm → "µL"

CELL COUNT UNITS (RBC, WBC, Platelets) - ALL use "cells/µL":
- million/µL, mill/µL, 10^6/µL, mill/cu.mm, mill/mm^3 million/mm^3 → multiply value by 1,000,000, unit = "cells/µL"
- million/cu.mm, mill/cu.mm → multiply value by 1,000,000, unit = "cells/µL"
- /cu.mm, cells/cu.mm, /cmm → "cells/µL" (no value change)
- After lakhs/millions conversion from value_normalization → already "cells/µL"

Examples:
- RBC: "4.31 million/µL" → value: "4310000", unit: "cells/µL"
- WBC: "7400 /cu.mm" → value: "7400", unit: "cells/µL"
- Platelets: "2.5 lakhs/cu.mm" → value: "250000", unit: "cells/µL"

OTHER UNITS:
- IU/L → "U/L"
- g%, gm/dl, gm/dL → "g/dL"
- Keep mg/dL and mmol/L as-is
</unit_standardization>

<range_edge_cases>
CRITICAL: Preserve inequality direction exactly as written in the report.
- "< 40", "<40", "less than 40", "Up to 40" → "< 40"
- "> 30", ">30", "greater than 30", "Above 30" → "> 30"
- "≤ 5", "<=5" → "< 5"
- "≥ 10", ">=10" → "> 10"

DO NOT convert inequalities to ranges:
- "< 40" stays "< 40" (NOT "0-40")
- "> 30" stays "> 30" (NOT "30-∞" or any other format)

Gender-specific: Extract applicable one if patient gender known, else first value
Age-specific: Extract applicable one if age known, else use general range

For a single parameter, if multiple ranges are written. Then extract the ideal/no-risk/desirable range.
<example_multiple_ranges>
< 130 desirable
130-150 border level
> 150 high

then extract the ranges as "<130", not any other
</example_multiple_ranges>
</range_edge_cases>

<qualitative_values>
Handle non-numeric results:
- Keep as-is: "Negative", "Positive", "Reactive", "Non-Reactive", "Trace", "Normal"
- Inequality values: Keep complete ("< 0.5", "> 100", "≤ 5")
- Ratios: Keep as string ("120/80", "1:16")
- Qualitative with threshold: Use qualitative only ("Negative" not "Negative (< 0.1)")
</qualitative_values>

<flag_rules>
Extract flag ONLY if explicitly marked in the report:
- Look for markers: "L", "Low", "H", "High", "N", "Normal", "*", "↑", "↓"
- If no explicit flag marker visible → set to null
- Do NOT calculate flags from value vs range
</flag_rules>

<sample_type_rules>
Determine sample type from context:

Indicators for "blood" (includes serum/plasma-derived tests):
- Section: HEMATOLOGY, COMPLETE BLOOD COUNT, CBC, HAEMATOLOGY
- Section: BIOCHEMISTRY, LIVER FUNCTION, RENAL FUNCTION, LIPID PROFILE, THYROID, SEROLOGY
- Tests: RBC, WBC, Platelets, Hemoglobin, ESR, MCV, MCH, MCHC, Differential counts
- Tests: Creatinine, Urea, Bilirubin, SGPT, SGOT, Cholesterol, Triglycerides, T3, T4, TSH, Albumin (blood context)

Indicators for "urine":
- Section: URINE, URINE ROUTINE, URINE EXAMINATION, URINE ANALYSIS
- Units: /hpf, /lpf (high/low power field)
- Tests: Pus Cells, RBCs (in urine), Epithelial cells, Crystals, Casts, Albumin (in urine context), Sugar (in urine)

Indicators for "stool":
- Section: STOOL, STOOL EXAMINATION

If unclear → set to null
</sample_type_rules>

<section_path_rules>
Build hierarchy from report headers:
- Look for: ALL CAPS text, bold markers, centered text, underlined headers
- Common patterns: "HEMATOLOGY", "Complete Blood Count", "Differential Count"

Rules:
- Test at root level (no section header) → use empty array []
- Max depth: 3 levels
- Preserve original spelling even if OCR errors present

Examples:
- Test with no section → section_path: []
- Test under "HEMATOLOGY" → section_path: ["HEMATOLOGY"]
- "Neutrophils" under "DIFFERENTIAL COUNT" in "HEMATOLOGY" → section_path: ["HEMATOLOGY", "DIFFERENTIAL COUNT"]
</section_path_rules>

<mapping_rules>
Map these test name variations to standard parameters:
- Haemoglobin, Hemoglobin, Hb → Hb%
- RBC Count, Red Blood Cell Count, Erythrocyte Count, ERYTHROCYTES → RBC
- WBC Count, Total Leucocyte Count, TLC, LEUCOCYTES → WBC
- Platelet Count, Thrombocyte Count, PLATELETS → Platelets
- Mean Corpuscular Volume → MCV
- Erythrocyte Sedimentation Rate → ESR
- Packed Cell Volume, Hematocrit, HCT, P C V → PCV
- Mean Corpuscular Hemoglobin, M C H → MCH
- Mean Corpuscular Hemoglobin Concentration, M C H C → MCHC
- Neutrophil, Neutrophil %, Polymorphs → Neutrophils
- Lymphocyte, Lymphocyte % → Lymphocytes
- Monocyte, Monocyte % → Monocytes
- Eosinophil, Eosinophil % → Eosinophils
- Basophil, Basophil % → Basophils
- HDL Cholesterol, HDL-C → HDL
- LDL Cholesterol, LDL-C → LDL
- Serum Cholesterol → Total Cholesterol
- Serum Triglycerides, TG → Triglycerides
- Creatinine → Serum Creatinine
- Blood Urea Nitrogen, Urea → BUN
- Uric Acid → Serum Uric Acid
- Albumin (serum context) → Serum Albumin
- Total Protein → Serum Protein
- Alkaline Phosphatase, ALP → Alka Phosphates
- ALT, Alanine Aminotransferase → SGPT
- AST, Aspartate Aminotransferase → SGOT
- Gamma GT, GGT → GGTP
- Fasting Blood Sugar, Fasting Sugar, Glucose Fasting → FBS
- Random Blood Sugar, Glucose Random → RBS
- Post Prandial Blood Sugar, Glucose PP → PPBS
- Glycated Hemoglobin, Glycosylated Hemoglobin → HbA1c
- Bilirubin Total → Total Bilirubin
- Bilirubin Direct, Conjugated Bilirubin → Direct Bilirubin
- Bilirubin Indirect, Unconjugated Bilirubin → Indirect Bilirubin
- Triiodothyronine → T3
- Thyroxine → T4
- Thyroid Stimulating Hormone → TSH
- Hepatitis B Surface Antigen → HBsAg
- Hepatitis C Antibody → HCV
- Prostate Specific Antigen → PSA
- Chest X-Ray, X-Ray Chest → CXR
- Echocardiogram, Echo → 2D Echo
- Electrocardiogram, Electrocardiography → ECG
- Treadmill Test, Exercise Stress Test → TMT
- Pulmonary Function Test, Spirometry → PFT
- Ultrasonography, Ultrasound → USG
- Cotinine → Nicotine
- VLDL Cholesterol, VLDL-C → VLDL
- Globulin, Total Globulin → Serum Globulin
- Albumin Globulin Ratio, Alb : Glb, A:G Ratio, A/G → A/G Ratio
- Calcium, Ca, Serum Ca → Serum Calcium

URINE MAPPINGS (sample_type will be "urine"):
- Quantity, Urine Volume → Volume
- Colour → Color
- Sp. Gr., Sp.Gr., S.G. → Specific Gravity
- pH, Urine pH → Reaction
- Urine Sugar, Sugar (urine context), Glucose (urine context) → Urine Sugar
- Albumin (urine context), Urine Protein, Protein, Proteins → Albumin/Proteins
- PusCells, Pus Cell, Leucocytes (urine), WBC (urine) → Pus Cells
- Bile Salt → Bile Salts
- Bile Pigment → Bile Pigments
- Ketone, Ketone Body, Acetone → Ketones
- R B Cs, RBCs (urine), Red Blood Cells (urine) → Urine RBC
- Epithelial, Epithelial Cell → Epithelial Cells
- Cast, Urinary Casts → Casts
- Crystal → Crystals

CRITICAL - CONTEXT-AWARE MAPPING:
When a test appears in a URINE section (identified by section headers like "URINE", "URINE ROUTINE", "URINE EXAMINATION"):
- "Protein" or "Proteins" → map to "Albumin/Proteins" (NOT to blood Serum Protein)
- "Sugar" or "Glucose" → map to "Urine Sugar" (NOT to blood RBS/FBS)
- "Albumin" → map to "Albumin/Proteins" (NOT to blood Serum Albumin)
Always check the section context before mapping ambiguous test names.
</mapping_rules>

<validation>
Before returning JSON:
1. All numeric values parsable (no commas, max one decimal point)
2. Lakhs/millions conversions have unit "cells/µL"
3. Volume units (cu.mm, /cmm) converted to "µL"
4. Ranges are numeric only (no units embedded)
5. Every test has status = "matched" or "unmatched"
6. Matched tests have standard_name set, unmatched have standard_name = null
</validation>

<example>
Input:
"HAEMATOLOGY
RBC Count: 4.31 millions/cu.mm (3.8-5.8)
Haemoglobin: 13.19 g/dl (12.0-16.0) - Cyanmethemoglobin Method
Platelet Count: 1,78,000 /cu.mm (1.5-4.0 lakhs) L
Anti-TPO Antibody: 45.2 IU/mL (<35) H"

Output:
{
  "tests": [
    {
      "sample_type": "blood",
      "standard_name": "RBC",
      "original_name": "RBC Count",
      "value": "4310000",
      "unit": "cells/µL",
      "range": "3800000-5800000",
      "flag": null,
      "method": null,
      "status": "matched"
    },
    {
      "sample_type": "blood",
      "standard_name": "Hb%",
      "original_name": "Haemoglobin",
      "value": "13.19",
      "unit": "g/dL",
      "range": "12.0-16.0",
      "flag": null,
      "method": "Cyanmethemoglobin Method",
      "status": "matched"
    },
    {
      "sample_type": "blood",
      "standard_name": "Platelets",
      "original_name": "Platelet Count",
      "value": "178000",
      "unit": "cells/µL",
      "range": "150000-400000",
      "flag": "low",
      "method": null,
      "status": "matched"
    },
    {
      "sample_type": "blood",
      "standard_name": null,
      "original_name": "Anti-TPO Antibody",
      "value": "45.2",
      "unit": "U/mL",
      "range": "< 35",
      "flag": "high",
      "method": null,
      "status": "unmatched"
    }
  ]
}
</example>

Return ONLY the JSON object. No explanations, no markdown."""


def build_user_prompt(ocr_data: str) -> str:
    """Build user prompt with the extracted OCR data."""
    return f"Extract the standardized parameters from this pathology report data:\n\n{ocr_data}"


# Cache the system prompt since it's built from static config
SYSTEM_PROMPT = build_system_prompt_v2()
