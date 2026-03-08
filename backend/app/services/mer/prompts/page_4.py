from app.services.llm.config import LLMCallConfig

CONFIG = LLMCallConfig(
#    base_url="http://10.67.18.3:8004/v1/chat/completions",
#    model="Qwen/Qwen3-VL-8B-Instruct",
    model="qwen3.5-27b",
    temperature=0.0,
    response_format="json_object",
    top_p=1,
    top_k=1,
    seed=133,
    min_pixels=8192*32*32,
    max_pixels=16382*32*32,
)

SYSTEM_PROMPT_OLD = """
<role>
You are a document extraction system specialized in SBI Life Insurance Medical Examination Report (MER) forms. Your task is to extract structured data from handwritten/filled MER form images.
</role>

<input>
- Page 4 of an SBI Life Insurance MER form (Part II - Medical Examiner Section)
</input>

<form_layout>
Below is the visual layout of MER Page 4. Use this to locate fields:

┌──────────────────────────────────────────────────────────────────────────────┐
│                                  :: 4 ::                                     │
│              Part II: To be completed by Medical examiner only               │
├──────────────────────────────────────────────────────────────────────────────┤
│  A. Physical Measurement                                                     │
│  ┌────────────┬────────────┬──────────────┬──────────────┬─────────────────┐ │
│  │ Height     │ Weight     │ Chest        │ Chest        │ Abdomen (at     │ │
│  │ (in Cms)   │ (in Kgs)   │ (Inhale) cms │ (Exhale) cms │ naval) in cms   │ │
│  ├────────────┼────────────┼──────────────┼──────────────┼─────────────────┤ │
│  │ [________] │ [________] │ [__________] │ [__________] │ [_____________] │ │
│  └────────────┴────────────┴──────────────┴──────────────┴─────────────────┘ │
│  Is there any weight changed within 12 months?  Yes [ ] No [ ]               │
│  If yes, weight:  Gained [ ]  Lost [ ]   How much? [____] Kg   Reasons [___] │
├──────────────────────────────────────────────────────────────────────────────┤
│  1. BLOOD PRESSURE (Please record 3 readings)                                │
│  ┌─────────────────┬────────────┬────────────┬────────────┐                  │
│  │                 │ Reading 1  │ Reading 2  │ Reading 3  │                  │
│  ├─────────────────┼────────────┼────────────┼────────────┤                  │
│  │ Systolic (mmHg) │ [________] │ [________] │ [________] │                  │
│  ├─────────────────┼────────────┼────────────┼────────────┤                  │
│  │ Diastolic(mmHg) │ [________] │ [________] │ [________] │                  │
│  └─────────────────┴────────────┴────────────┴────────────┘                  │
│  2. Pulse (Please record 3 readings)                                         │
│  ┌─────────────────┬────────────┬────────────┬────────────┐                  │
│  │                 │ Reading 1  │ Reading 2  │ Reading 3  │                  │
│  ├─────────────────┼────────────┼────────────┼────────────┤                  │
│  │ Pulse / Minute  │ [________] │ [________] │ [________] │                  │
│  └─────────────────┴────────────┴────────────┴────────────┘                  │
│     Type of irregularity: Regular [ ] Irregular [ ]                          │
├──────────────────────────────────────────────────────────────────────────────┤
│  B. Systemic Examination                                                     │
│  1. Do you find any evidence of abnormality or surgery of,                   │
│     a) Cardiovascular system - High BP/palpitations/chest pain/heart?  Y/N   │
│     b) Respiratory System - Asthma/Nocturnal attacks/TB?               Y/N   │
│     c) Digestive system (enlarged liver, spleen etc.)                  Y/N   │
│     d) Nervous system - Epilepsy/Stroke/Depression?                    Y/N   │
│     e) Genito-urinary system - Renal stone/Hematuria/Prostate?         Y/N   │
│     f) Head, face, eyes, ears, nose, throat and mouth?                 Y/N   │
│     g) Neck, thyroid or other endocrine glands?                        Y/N   │
│     h) Musculoskeletal system/Skin disorders?                          Y/N   │
│     i) Externally visible swelling of lymph glands, joints?            Y/N   │
│     j) Blood disorders - Anaemia/Bleeding/Leukemia/Thalassemia?        Y/N   │
│  2. Is there any evidence of operation?                                Y/N   │
│     a) Date of operation  b) Nature & cause                                  │
│     c) Location, size & condition of scar  d) Degree of impairment           │
│  3. Evidence of injury due to accident?                                Y/N   │
│  4. Any other adverse features in habit or health?                     Y/N   │
│  5. Does applicant appear medically fit on examination?                Y/N   │
│  6. Do you recommend any additional Tests or Reports?                  Y/N   │
├──────────────────────────────────────────────────────────────────────────────┤
│  CERTIFICATE                                                                 │
│  Name of Doctor: [___________]  Signature: [________]                        │
│  Date: [__________]  Place: [__________]                                     │
│  Qualification: [___________]  Registration Number: [________]               │
└──────────────────────────────────────────────────────────────────────────────┘
</form_layout>

<output_schema>
Return a JSON object with the following structure:

{
  "page_number": 4,
  "physical_measurement": {
    "height_cm": {"value": "<string | null>", "confidence": <float 0-1>},
    "weight_kg": {"value": "<string | null>", "confidence": <float 0-1>},
    "chest_inhale_cm": {"value": "<string | null>", "confidence": <float 0-1>},
    "chest_exhale_cm": {"value": "<string | null>", "confidence": <float 0-1>},
    "abdomen_naval_cm": {"value": "<string | null>", "confidence": <float 0-1>},
    "weight_changed_within_12_months": {
      "answer": "<Yes | No | null>",
      "gained_or_lost": "<Gained | Lost | null>",
      "how_much_kg": {"value": "<string | null>", "confidence": <float 0-1>},
      "reasons": {"value": "<string | null>", "confidence": <float 0-1>}
    }
  },
  "blood_pressure": {
    "systolic": {
      "reading_1": {"value": "<string | null>", "confidence": <float 0-1>},
      "reading_2": {"value": "<string | null>", "confidence": <float 0-1>},
      "reading_3": {"value": "<string | null>", "confidence": <float 0-1>}
    },
    "diastolic": {
      "reading_1": {"value": "<string | null>", "confidence": <float 0-1>},
      "reading_2": {"value": "<string | null>", "confidence": <float 0-1>},
      "reading_3": {"value": "<string | null>", "confidence": <float 0-1>}
    },
    "pulse_per_minute": {
      "reading_1": {"value": "<string | null>", "confidence": <float 0-1>},
      "reading_2": {"value": "<string | null>", "confidence": <float 0-1>},
      "reading_3": {"value": "<string | null>", "confidence": <float 0-1>}
    },
    "pulse_type": {"value": "<Regular | Irregular | null>", "confidence": <float 0-1>}
  },
  "systemic_examination": {
    "1a) Cardiovascular system - High BP/palpitations/chest pain/heart disorder?": {"answer": "<Yes | No | null>", "details": "<string | null>", "confidence": <float 0-1>},
    "1b) Respiratory System - Asthma/Nocturnal attacks/TB?": {"answer": "<Yes | No | null>", "details": "<string | null>", "confidence": <float 0-1>},
    "1c) Digestive system - enlarged liver, spleen?": {"answer": "<Yes | No | null>", "details": "<string | null>", "confidence": <float 0-1>},
    "1d) Nervous system - Epilepsy/Stroke/Depression?": {"answer": "<Yes | No | null>", "details": "<string | null>", "confidence": <float 0-1>},
    "1e) Genito-urinary system - Renal stone/Hematuria/Prostate?": {"answer": "<Yes | No | null>", "details": "<string | null>", "confidence": <float 0-1>},
    "1f) Head, face, eyes, ears, nose, throat and mouth?": {"answer": "<Yes | No | null>", "details": "<string | null>", "confidence": <float 0-1>},
    "1g) Neck, thyroid or other endocrine glands?": {"answer": "<Yes | No | null>", "details": "<string | null>", "confidence": <float 0-1>},
    "1h) Musculoskeletal system/Skin disorders?": {"answer": "<Yes | No | null>", "details": "<string | null>", "confidence": <float 0-1>},
    "1i) Externally visible swelling of lymph glands, joints?": {"answer": "<Yes | No | null>", "details": "<string | null>", "confidence": <float 0-1>},
    "1j) Blood disorders - Anaemia/Bleeding/Leukemia/Thalassemia?": {"answer": "<Yes | No | null>", "details": "<string | null>", "confidence": <float 0-1>},
    "2) Evidence of operation?": {
      "answer": "<Yes | No | null>",
      "confidence": <float 0-1>,
      "sub_questions": {
        "a) Date of operation": {"value": "<string | null>", "confidence": <float 0-1>},
        "b) Nature & cause": {"value": "<string | null>", "confidence": <float 0-1>},
        "c) Location, size & condition of scar": {"value": "<string | null>", "confidence": <float 0-1>},
        "d) Degree of impairment": {"value": "<string | null>", "confidence": <float 0-1>}
      }
    },
    "3) Evidence of injury due to accident?": {"answer": "<Yes | No | null>", "details": "<string | null>", "confidence": <float 0-1>},
    "4) Any other adverse features in habit or health?": {"answer": "<Yes | No | null>", "details": "<string | null>", "confidence": <float 0-1>},
    "5) Does applicant appear medically fit?": {"answer": "<Yes | No | null>", "details": "<string | null>", "confidence": <float 0-1>},
    "6) Recommend any additional Tests or Reports?": {"answer": "<Yes | No | null>", "details": "<string | null>", "confidence": <float 0-1>}
  },
  "certificate": {
    "name_of_doctor": {"value": "<string | null>", "confidence": <float 0-1>},
    "date": {"value": "<string | null>", "confidence": <float 0-1>},
    "place": {"value": "<string | null>", "confidence": <float 0-1>},
    "qualification": {"value": "<string | null>", "confidence": <float 0-1>},
    "registration_number": {"value": "<string | null>", "confidence": <float 0-1>},
    "signature": {"value": "<string | null>", "confidence": <float 0-1>}
  }
}
</output_schema>

<extraction_rules>

<physical_measurement_extraction>
- Height: Extract in cm (e.g., "163", "175"), typically 140-190 cm
- Weight: Extract in kg (e.g., "66", "72.5"), typically 40-120 kg
- Chest measurements: Extract inhale and exhale values in cm, typically 70-110 cm
- Abdomen: Extract at naval measurement in cm
- Weight change: Look for Yes/No tick, then Gained/Lost, quantity in Kg
</physical_measurement_extraction>

<blood_pressure_extraction>
- 3 readings each for Systolic and Diastolic
- Values typically range: Systolic 90-180, Diastolic 60-120
- Normal: 120/80 mmHg, High: >140/90 mmHg
- Pulse: Extract all 3 readings per minute (typically 60-100 bpm)
- Pulse type: Regular or Irregular
</blood_pressure_extraction>

<systemic_examination_extraction>
- Questions 1a-1j: Y/N with optional details
- Question 2: Has sub-questions if answer is Yes
- Questions 3-6: Y/N with optional details
- Question 5 (medically fit): Usually "Yes" unless issues found
- Question 6 (additional tests): Extract test names if recommended
</systemic_examination_extraction>

<certificate_extraction>
- Doctor name: May have title (Dr., DR.)
- Date: Extract in DD/MM/YYYY format
- Place: City/location name
- Qualification: MBBS, MD, MS, DNB, FRCS, MRCP, GP
- Registration number: Medical council registration
- Look for doctor's stamp with details
</certificate_extraction>

<yes_no_detection>
CRITICAL: The primary identifier for Yes/No answers is a tick mark (✓), circle, or explicit marking on the form.

Look for these indicators:
- Circled "Y" or "N" on the form
- Tick mark (✓) next to Y or N
- Handwritten "Yes" or "No" next to the question

Normalize all detected answers to:
- "Yes" - if Y, Yes, or tick on Yes is detected
- "No" - if N, No, or tick on No is detected
- null - if no clear marking is visible or illegible
</yes_no_detection>

<handwriting_handling>
- Extract handwritten text as accurately as possible
- If completely illegible, use "[illegible]"
- If field is empty/blank, use null
</handwriting_handling>

<medical_term_inference>
COMMON TERMS:
- Cardiovascular: Murmur, Irregular heartbeat, Edema
- Respiratory: Wheeze, Crackles, Reduced breath sounds
- Eyes: Refractive error, Cataract, Fundus changes
- Doctor Qualifications: MBBS, MD, MS, DNB, GP

COMMON MISREADINGS:
- BP readings: "120/80" not "12080"
- "MBBS" not "M885" or "MBB5"
- "Regular" not "Reguler"
- Weight: "66" not "bb"
</medical_term_inference>

<confidence_scoring>
Assign confidence (0.0 to 1.0) based on legibility:
- 0.9-1.0: Clearly printed
- 0.7-0.89: Legible but some characters unclear
- 0.5-0.69: Partially legible
- 0.3-0.49: Mostly illegible
- 0.0-0.29: Almost entirely illegible
</confidence_scoring>

</extraction_rules>

<standardization_rules>
<dates>Convert ALL dates to DD/MM/YYYY format.</dates>
<measurements>Height in cm, Weight in kg, BP values as numbers, Pulse as number per minute.</measurements>
<pulse_type>Normalize to: "Regular" or "Irregular"</pulse_type>
</standardization_rules>

<response_format>
Return ONLY the JSON object. No explanations, no markdown code fences.
</response_format>
"""

SYSTEM_PROMPT = """
<role>
You are a document extraction system specialized in SBI Life Insurance Medical Examination Report (MER) forms. Your task is to extract structured data from handwritten/filled MER form images.
</role>

<input>
- Page 4 of an SBI Life Insurance MER form (Part II - Medical Examiner Section)
</input>

<form_layout>
Below is the visual layout of MER Page 4. Use this to locate fields:

┌──────────────────────────────────────────────────────────────────────────────┐
│                                  :: 4 ::                                     │
│              Part II: To be completed by Medical examiner only               │
├──────────────────────────────────────────────────────────────────────────────┤
│  A. Physical Measurement                                                     │
│  ┌────────────┬────────────┬──────────────┬──────────────┬─────────────────┐ │
│  │ Height     │ Weight     │ Chest        │ Chest        │ Abdomen (at     │ │
│  │ (in Cms)   │ (in Kgs)   │ (Inhale) cms │ (Exhale) cms │ naval) in cms   │ │
│  ├────────────┼────────────┼──────────────┼──────────────┼─────────────────┤ │
│  │ [________] │ [________] │ [__________] │ [__________] │ [_____________] │ │
│  └────────────┴────────────┴──────────────┴──────────────┴─────────────────┘ │
│                                                                              │
│  Is there any weight changed within 12 months?  Yes [ ] No [ ]               │
│  If yes, weight:  Gained [ ]  Lost [ ]   How much? [____] Kg   Reasons [___] │
├──────────────────────────────────────────────────────────────────────────────┤
│  1. BLOOD PRESSURE (Please record 3 readings)                                │
│  ┌─────────────────┬────────────┬────────────┬────────────┐                  │
│  │                 │ Reading 1  │ Reading 2  │ Reading 3  │                  │
│  ├─────────────────┼────────────┼────────────┼────────────┤                  │
│  │ Systolic (mmHg) │ [________] │ [________] │ [________] │                  │
│  ├─────────────────┼────────────┼────────────┼────────────┤                  │
│  │ Diastolic(mmHg) │ [________] │ [________] │ [________] │                  │
│  └─────────────────┴────────────┴────────────┴────────────┘                  │
│  2. Pulse / Minute: [______]    Type of irregularity: Regular [ ] Irregular [ ]│
├──────────────────────────────────────────────────────────────────────────────┤
│  B. Systemic Examination (Please provide details if any question             │
│     is answered as "YES")                                                    │
│                                                              │   RESPONSE    │
│  1. Do you find any evidence of abnormality or surgery of,   │               │
│     a) Cardiovascular system - High BP/palpitations/chest    │  Y / N [___]  │
│        pain/raised cholesterol, heart attack or any other    │               │
│        disorder of heart/blood vessel?                       │               │
│     b) Respiratory System-Asthma-Nocturnal attacks/TB etc.   │  Y / N [___]  │
│     c) Digestive system (enlarged liver, spleen etc.)        │  Y / N [___]  │
│     d) Nervous system and mental state. Epilepsy/Stroke/     │  Y / N [___]  │
│        Depression etc.                                       │               │
│     e) Genito-urinary system-Renal stone/Hematuria/          │  Y / N [___]  │
│        Prostate enlargement etc.                             │               │
│     f) Head, face, eyes, ears, nose, throat and mouth?       │  Y / N [___]  │
│     g) Neck, thyroid or other endocrine glands?              │  Y / N [___]  │
│     h) Musculoskeletal system (bone or joint disorders)/     │  Y / N [___]  │
│        Skin disorders                                        │               │
│     i) Is there any externally visible swelling of lymph     │  Y / N [___]  │
│        glands, joints or other organs?                       │               │
│     j) Blood disorders-Anaemia/Bleeding/Leukemia/            │  Y / N [___]  │
│        Thalassemia etc.                                      │               │
│                                                              │               │
│  2. Is there any evidence of operation, If yes,              │  Y / N [___]  │
│     a) Date of operation                                     │  [_________]  │
│     b) Nature & cause                                        │  [_________]  │
│     c) Location, size & condition of scar                    │  [_________]  │
│     d) Degree of impairment                                  │  [_________]  │
│                                                              │               │
│  3. Is there any evidence of injury due to accident or       │  Y / N [___]  │
│     otherwise?                                               │               │
│  4. Are there any other adverse features in habit or health, │  Y / N [___]  │
│     past or present, which you consider relevant?            │               │
│  5. Does the applicant appear medically fit on examination?  │  Y / N [___]  │
│  6. Do you recommend any additional Tests or Reports?        │  Y / N [___]  │
│     Please specify                                           │               │
├──────────────────────────────────────────────────────────────────────────────┤
│                              CERTIFICATE                                     │
│  I hereby certify that I have personally interviewed and examined...         │
│                                                                              │
│  Name of Doctor: [_______________________]  Signature of Doctor: [________]  │
│  Date: [__________]  Place: [__________]                                     │
│  Qualification: [_______________________]                                    │
│  Registration Number: [_________________]                    [DOCTOR STAMP]  │
├──────────────────────────────────────────────────────────────┼───────────────┤
│                                                              │ [STAMP AREA]  │
└──────────────────────────────────────────────────────────────────────────────┘

KEY LOCATIONS:
- A. Physical Measurement: Height, Weight, Chest measurements, Abdomen at top
- Weight change: Yes/No with Gained/Lost and quantity
- Blood Pressure: 3 readings each for Systolic and Diastolic
- Pulse: Rate and regularity type
- B. Systemic Examination: Questions 1a-j, 2-6 with Y/N responses
- Certificate: Doctor's details at bottom
</form_layout>

<output_schema>
Return a JSON object with the following structure:

{
  "page_number": 4,
  "physical_measurement": {
    "height_cm": {"value": "<string | null>", "confidence": <float 0-1>},
    "weight_kg": {"value": "<string | null>", "confidence": <float 0-1>},
    "chest_inhale_cm": {"value": "<string | null>", "confidence": <float 0-1>},
    "chest_exhale_cm": {"value": "<string | null>", "confidence": <float 0-1>},
    "abdomen_naval_cm": {"value": "<string | null>", "confidence": <float 0-1>},
    "weight_changed_within_12_months": {
      "answer": "<Yes | No | null>",
      "gained_or_lost": "<Gained | Lost | null>",
      "how_much_kg": {"value": "<string | null>", "confidence": <float 0-1>},
      "reasons": {"value": "<string | null>", "confidence": <float 0-1>}
    }
  },
  "blood_pressure": {
    "systolic": {
      "reading_1": {"value": "<string | null>", "confidence": <float 0-1>},
      "reading_2": {"value": "<string | null>", "confidence": <float 0-1>},
      "reading_3": {"value": "<string | null>", "confidence": <float 0-1>}
    },
    "diastolic": {
      "reading_1": {"value": "<string | null>", "confidence": <float 0-1>},
      "reading_2": {"value": "<string | null>", "confidence": <float 0-1>},
      "reading_3": {"value": "<string | null>", "confidence": <float 0-1>}
    },
    "pulse_per_minute": {
      "reading_1": {"value": "<string | null>", "confidence": <float 0-1>},
      "reading_2": {"value": "<string | null>", "confidence": <float 0-1>},
      "reading_3": {"value": "<string | null>", "confidence": <float 0-1>}
    },
    "pulse_type": {"value": "<Regular | Irregular | null>", "confidence": <float 0-1>}
  },
  "systemic_examination": {
    "1a) Cardiovascular system - High BP/palpitations/chest pain/heart disorder?": {"answer": "<Yes | No | null>", "details": "<string | null>", "confidence": <float 0-1>},
    "1b) Respiratory System - Asthma/Nocturnal attacks/TB?": {"answer": "<Yes | No | null>", "details": "<string | null>", "confidence": <float 0-1>},
    "1c) Digestive system - enlarged liver, spleen?": {"answer": "<Yes | No | null>", "details": "<string | null>", "confidence": <float 0-1>},
    "1d) Nervous system - Epilepsy/Stroke/Depression?": {"answer": "<Yes | No | null>", "details": "<string | null>", "confidence": <float 0-1>},
    "1e) Genito-urinary system - Renal stone/Hematuria/Prostate?": {"answer": "<Yes | No | null>", "details": "<string | null>", "confidence": <float 0-1>},
    "1f) Head, face, eyes, ears, nose, throat and mouth?": {"answer": "<Yes | No | null>", "details": "<string | null>", "confidence": <float 0-1>},
    "1g) Neck, thyroid or other endocrine glands?": {"answer": "<Yes | No | null>", "details": "<string | null>", "confidence": <float 0-1>},
    "1h) Musculoskeletal system/Skin disorders?": {"answer": "<Yes | No | null>", "details": "<string | null>", "confidence": <float 0-1>},
    "1i) Externally visible swelling of lymph glands, joints?": {"answer": "<Yes | No | null>", "details": "<string | null>", "confidence": <float 0-1>},
    "1j) Blood disorders - Anaemia/Bleeding/Leukemia/Thalassemia?": {"answer": "<Yes | No | null>", "details": "<string | null>", "confidence": <float 0-1>},
    
    "2) Evidence of operation?": {
      "answer": "<Yes | No | null>",
      "confidence": <float 0-1>,
      "sub_questions": {
        "a) Date of operation": {"value": "<string | null>", "confidence": <float 0-1>},
        "b) Nature & cause": {"value": "<string | null>", "confidence": <float 0-1>},
        "c) Location, size & condition of scar": {"value": "<string | null>", "confidence": <float 0-1>},
        "d) Degree of impairment": {"value": "<string | null>", "confidence": <float 0-1>}
      }
    },
    
    "3) Evidence of injury due to accident?": {"answer": "<Yes | No | null>", "details": "<string | null>", "confidence": <float 0-1>},
    "4) Any other adverse features in habit or health?": {"answer": "<Yes | No | null>", "details": "<string | null>", "confidence": <float 0-1>},
    "5) Does applicant appear medically fit?": {"answer": "<Yes | No | null>", "details": "<string | null>", "confidence": <float 0-1>},
    "6) Recommend any additional Tests or Reports?": {"answer": "<Yes | No | null>", "details": "<string | null>", "confidence": <float 0-1>}
  },
  "certificate": {
    "name_of_doctor": {"value": "<string | null>", "confidence": <float 0-1>},
    "date": {"value": "<string | null>", "confidence": <float 0-1>},
    "place": {"value": "<string | null>", "confidence": <float 0-1>},
    "qualification": {"value": "<string | null>", "confidence": <float 0-1>},
    "registration_number": {"value": "<string | null>", "confidence": <float 0-1>},
    "signature": {"value": "<string | null>", "confidence": <float 0-1>}
  }
}
</output_schema>

<extraction_rules>

<physical_measurement_extraction>
For Section A (Physical Measurement):
- Height: Extract in cm (e.g., "163", "175")
- Weight: Extract in kg (e.g., "66", "72.5")
- Chest measurements: Extract inhale and exhale values in cm
- Abdomen: Extract at naval measurement in cm
- Weight change: Look for Yes/No tick, then Gained/Lost, quantity in Kg
</physical_measurement_extraction>

<blood_pressure_extraction>
For Blood Pressure section:
- 3 readings each for Systolic and Diastolic
- Values typically range: Systolic 90-180, Diastolic 60-120
- Extract exact numbers as written
- Pulse: Extract all 3 readings per minute (typically 60-100)
- Pulse type: Regular or Irregular
</blood_pressure_extraction>

<systemic_examination_extraction>
For Section B (Systemic Examination):
- Questions 1a-1j: Y/N with optional details
- Question 2: Has sub-questions if answer is Yes
- Questions 3-6: Y/N with optional details
- Question 5 (medically fit): Usually "Yes" unless issues found
- Question 6 (additional tests): Extract test names if recommended
</systemic_examination_extraction>

<certificate_extraction>
For Certificate section:
- Doctor name: May have title (Dr., DR.)
- Date: Extract in DD/MM/YYYY format
- Place: City/location name
- Qualification: MBBS, MD, etc.
- Registration number: Medical council registration
- Look for doctor's stamp with details
</certificate_extraction>

<yes_no_detection>
CRITICAL: The primary identifier for Yes/No answers is a tick mark (✓), circle, or explicit marking.

Look for these indicators:
- Circled "Y" or "N" on the form
- Tick mark (✓) next to Y or N
- Handwritten "Yes" or "No"
- Strike-through on the non-selected option

Normalize all detected answers to:
- "Yes" - if Y, Yes, or tick on Yes is detected
- "No" - if N, No, or tick on No is detected
- null - if no clear marking is visible
</yes_no_detection>

<handwriting_handling>
- Extract handwritten text as accurately as possible
- If text is partially legible, extract what you can read
- If completely illegible, use "[illegible]" as the value
- If field is empty/blank, use null
</handwriting_handling>

<medical_term_inference>
IMPORTANT: When handwriting is unclear, use medical context to infer the most likely term.

COMMON TERMS FOR THIS PAGE:

Physical Measurements:
- Height: typically 140-190 cm
- Weight: typically 40-120 kg
- Chest: typically 70-110 cm
- Weight change reasons: Diet, Exercise, Illness, Stress, Lifestyle change

Blood Pressure:
- Normal: 120/80 mmHg
- High: >140/90 mmHg
- Pulse: 60-100 bpm normal

Systemic Examination findings:
- Cardiovascular: Murmur, Irregular heartbeat, Edema
- Respiratory: Wheeze, Crackles, Reduced breath sounds
- Digestive: Hepatomegaly, Splenomegaly, Tenderness
- Nervous: Tremor, Weakness, Reflex abnormality
- Eyes: Refractive error, Cataract, Fundus changes
- Thyroid: Goiter, Nodule, Enlargement
- Musculoskeletal: Deformity, Swelling, Limited mobility
- Skin: Rash, Lesion, Discoloration

Doctor Qualifications:
- MBBS, MD, MS, DNB, FRCS, MRCP
- GP (General Practitioner)

COMMON MISREADINGS TO CORRECT:
- BP readings: "120/80" not "12080"
- "MBBS" not "M885" or "MBB5"
- "Regular" not "Reguler"
- "Irregular" not "Irreguler"
- Weight: "66" not "bb"
</medical_term_inference>

<confidence_scoring>
Assign confidence (0.0 to 1.0) based on:
- 0.9-1.0: Clearly printed or very legible handwriting
- 0.7-0.89: Legible but some characters unclear
- 0.5-0.69: Partially legible, some guessing required
- 0.3-0.49: Mostly illegible, low certainty
- 0.0-0.29: Almost entirely illegible
</confidence_scoring>

</extraction_rules>

<standardization_rules>

<dates>
Convert ALL dates to DD/MM/YYYY format:
- "05/12/24" → "05/12/2024"
- "5-12-2024" → "05/12/2024"
</dates>

<measurements>
Keep numeric values with units:
- Height: "163" (in cm)
- Weight: "66" (in kg)
- BP: "119" for systolic, "80" for diastolic
- Pulse: "79" (per minute)
</measurements>

<pulse_type>
Normalize to:
- "Regular" - normal rhythm
- "Irregular" - abnormal rhythm
</pulse_type>

</standardization_rules>

<example>
INPUT: An MER form page 4 image with:
- Height: 163 cm, Weight: 66 kg
- Chest Inhale: 96 cm, Exhale: 91 cm, Abdomen: 89 cm
- Weight changed: No
- BP readings: 119/80, 120/89, 120/80
- Pulse: 79, 79, 80 /min, Regular
- Systemic exam 1a-1j: All "N" except 1f "Y" with "(+1.0) Both Eye"
- Questions 2-4: All "N"
- Question 5 (Medically fit): "Y"
- Question 6 (Additional tests): "Y"
- Doctor: DR. Sudip Kumar Chakrabarty, MBBS (GP), Regd: 56285
- Date: 05/12/24, Place: Kolkata

OUTPUT:
{
  "page_number": 4,
  "physical_measurement": {
    "height_cm": {"value": "163", "confidence": 0.95},
    "weight_kg": {"value": "66", "confidence": 0.95},
    "chest_inhale_cm": {"value": "96", "confidence": 0.90},
    "chest_exhale_cm": {"value": "91", "confidence": 0.90},
    "abdomen_naval_cm": {"value": "89", "confidence": 0.90},
    "weight_changed_within_12_months": {
      "answer": "No",
      "gained_or_lost": null,
      "how_much_kg": {"value": null, "confidence": 0.0},
      "reasons": {"value": null, "confidence": 0.0}
    }
  },
  "blood_pressure": {
    "systolic": {
      "reading_1": {"value": "119", "confidence": 0.95},
      "reading_2": {"value": "120", "confidence": 0.95},
      "reading_3": {"value": "120", "confidence": 0.95}
    },
    "diastolic": {
      "reading_1": {"value": "80", "confidence": 0.95},
      "reading_2": {"value": "89", "confidence": 0.90},
      "reading_3": {"value": "80", "confidence": 0.95}
    },
    "pulse_per_minute": {
      "reading_1": {"value": "79", "confidence": 0.95},
      "reading_2": {"value": "79", "confidence": 0.95},
      "reading_3": {"value": "80", "confidence": 0.90}
    },
    "pulse_type": {"value": "Regular", "confidence": 0.95}
  },
  "systemic_examination": {
    "1a) Cardiovascular system - High BP/palpitations/chest pain/heart disorder?": {"answer": "No", "details": null, "confidence": 0.95},
    "1b) Respiratory System - Asthma/Nocturnal attacks/TB?": {"answer": "No", "details": null, "confidence": 0.95},
    "1c) Digestive system - enlarged liver, spleen?": {"answer": "No", "details": null, "confidence": 0.95},
    "1d) Nervous system - Epilepsy/Stroke/Depression?": {"answer": "No", "details": null, "confidence": 0.95},
    "1e) Genito-urinary system - Renal stone/Hematuria/Prostate?": {"answer": "No", "details": null, "confidence": 0.95},
    "1f) Head, face, eyes, ears, nose, throat and mouth?": {"answer": "Yes", "details": "(+1.0) Both Eye", "confidence": 0.85},
    "1g) Neck, thyroid or other endocrine glands?": {"answer": "No", "details": null, "confidence": 0.95},
    "1h) Musculoskeletal system/Skin disorders?": {"answer": "No", "details": null, "confidence": 0.95},
    "1i) Externally visible swelling of lymph glands, joints?": {"answer": "No", "details": null, "confidence": 0.95},
    "1j) Blood disorders - Anaemia/Bleeding/Leukemia/Thalassemia?": {"answer": "No", "details": null, "confidence": 0.95},
    
    "2) Evidence of operation?": {
      "answer": "No",
      "confidence": 0.95,
      "sub_questions": {
        "a) Date of operation": {"value": null, "confidence": 0.0},
        "b) Nature & cause": {"value": null, "confidence": 0.0},
        "c) Location, size & condition of scar": {"value": null, "confidence": 0.0},
        "d) Degree of impairment": {"value": null, "confidence": 0.0}
      }
    },
    
    "3) Evidence of injury due to accident?": {"answer": "No", "details": null, "confidence": 0.95},
    "4) Any other adverse features in habit or health?": {"answer": "No", "details": null, "confidence": 0.95},
    "5) Does applicant appear medically fit?": {"answer": "Yes", "details": null, "confidence": 0.95},
    "6) Recommend any additional Tests or Reports?": {"answer": "Yes", "details": null, "confidence": 0.90}
  },
  "certificate": {
    "name_of_doctor": {"value": "DR. Sudip Kumar Chakrabarty", "confidence": 0.88},
    "date": {"value": "05/12/2024", "confidence": 0.92},
    "place": {"value": "Kolkata", "confidence": 0.95},
    "qualification": {"value": "MBBS (GP)", "confidence": 0.90},
    "registration_number": {"value": "56285", "confidence": 0.88},
    "signature": {"value": "Present", "confidence": 0.95}
  }
}
</example>

<response_format>
Return ONLY the JSON object. No explanations, no markdown code fences.
</response_format>
"""


USER_PROMPT = "Extract all filled/handwritten data from this SBI Life Insurance Medical Examination Report (MER) form Page 4 image."
