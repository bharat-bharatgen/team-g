"""
Page 2 Questions extraction prompt - extracts Q3k through Q9.
Used when split processing is enabled for better accuracy.
"""

from app.services.llm.config import LLMCallConfig

CONFIG = LLMCallConfig(
    model="qwen3.5-27b",
    temperature=0.0,
    response_format="json_object",
    top_p=1,
    top_k=1,
    seed=133,
    min_pixels=8192*32*32,
    max_pixels=16382*32*32,
)

SYSTEM_PROMPT = """
<role>
You are a document extraction system for SBI Life Insurance MER forms.
Extract ONLY Questions 3k through 9 from this cropped image of Page 2.
</role>

<form_layout>
This section contains medical questions. Each question has:
- Question text on the LEFT
- Y/N answer option (circled or ticked) on the RIGHT
- Details/comments field on the FAR RIGHT

Questions in order:
k) Kidney disorder, renal stones, renal failure, Dialysis.              Y / N  [details]
l) Chronic ulceration on skin or inside any organ.                      Y / N  [details]
m) Are you on blood thinners, Oral steroids,                            Y / N  [details]
   Immunosuppressant or any special therapy.
n) Insomnia, depression, stress-related problems, anxiety               Y / N  [details]
   state, nervous breakdown, epilepsy, fits, blackouts or
   any other mental disorder.
o) Any other serious or chronic illness not mentioned above?            Y / N  [details]
p) Do you have any permanent disability, which could                    Y / N  [details]
   affect your ability to walk or work.
4) Have you undergone any radiological/cardiological/                   Y / N  [details]
   pathological/medical/USG/CT Scan/MRI, CT angiography,
   Angiogram, endoscopy, biopsy, FNAC or any other test?
5) Have you undergone or advised hospitalization/operation/              Y / N  [details]
   surgery/organ transplant?
   if YES:
   a) month & year of hospitalization / operation                              [details]
   b) nature & cause of hospitalization / operation                            [details]
   c) location, size and condition of the scar                                 [details]
   d) degree of impairment, if any                                             [details]
6) Do you have any physical deformity/congenital disease?               Y / N  [details]
   If YES:
   a) Cause of deformity                                                       [details]
   b) The part affected with cause thereof                                     [details]
   c) Do you use any physical aid?                                             [details]
7) Is your vision and hearing normal?                                   Y / N  [details]
8) Did you ever meet with an accident or suffer any injury?             Y / N  [details]
   If YES:
   a) Date of Injury / Surgery                                                 [details]
   b) Nature of Injury / Surgery                                               [details]
   c) Degree of Impairment                                                     [details]
   d) Did you suffer from any head injury?                                     [details]
   e) Duration of unconsciousness (if any)                                     [details]
9) Have you or your spouse received treatment for sexually              Y / N  [details]
   transmitted disease, AIDS/HIV?
</form_layout>

<output_schema>
{
  "questions": {
    "3k) Kidney disorder, renal stones, renal failure, Dialysis?": {"answer": "<Yes | No | null>", "details": "<string | null>", "confidence": <float 0-1>},
    "3l) Chronic ulceration on skin or inside any organ?": {"answer": "<Yes | No | null>", "details": "<string | null>", "confidence": <float 0-1>},
    "3m) Are you on blood thinners, Oral steroids, Immunosuppressant or any special therapy?": {"answer": "<Yes | No | null>", "details": "<string | null>", "confidence": <float 0-1>},
    "3n) Insomnia, depression, stress-related problems, anxiety state, nervous breakdown, epilepsy, fits, blackouts or any other mental disorder?": {"answer": "<Yes | No | null>", "details": "<string | null>", "confidence": <float 0-1>},
    "3o) Any other serious or chronic illness not mentioned above?": {"answer": "<Yes | No | null>", "details": "<string | null>", "confidence": <float 0-1>},
    "3p) Do you have any permanent disability, which could affect your ability to walk or work?": {"answer": "<Yes | No | null>", "details": "<string | null>", "confidence": <float 0-1>},
    "4) Have you undergone any radiological/cardiological/pathological/medical test?": {"answer": "<Yes | No | null>", "details": "<string | null>", "confidence": <float 0-1>},
    "5) Have you undergone or advised hospitalization/operation/surgery?": {
      "answer": "<Yes | No | null>",
      "details": "<string | null>",
      "confidence": <float 0-1>,
      "sub_questions": {
        "a) month & year of hospitalization/operation": {"value": "<string | null>", "confidence": <float 0-1>},
        "b) nature & cause of hospitalization/operation": {"value": "<string | null>", "confidence": <float 0-1>},
        "c) location, size and condition of the scar": {"value": "<string | null>", "confidence": <float 0-1>},
        "d) degree of impairment, if any": {"value": "<string | null>", "confidence": <float 0-1>}
      }
    },
    "6) Do you have any physical deformity/congenital disease?": {
      "answer": "<Yes | No | null>",
      "details": "<string | null>",
      "confidence": <float 0-1>,
      "sub_questions": {
        "a) Cause of deformity": {"value": "<string | null>", "confidence": <float 0-1>},
        "b) The part affected with cause thereof": {"value": "<string | null>", "confidence": <float 0-1>},
        "c) Do you use any physical aid?": {"value": "<string | null>", "confidence": <float 0-1>}
      }
    },
    "7) Is your vision and hearing normal?": {"answer": "<Yes | No | null>", "details": "<string | null>", "confidence": <float 0-1>},
    "8) Did you ever meet with an accident or suffer any injury?": {
      "answer": "<Yes | No | null>",
      "details": "<string | null>",
      "confidence": <float 0-1>,
      "sub_questions": {
        "a) Date of Injury/Surgery": {"value": "<string | null>", "confidence": <float 0-1>},
        "b) Nature of Injury/Surgery": {"value": "<string | null>", "confidence": <float 0-1>},
        "c) Degree of Impairment": {"value": "<string | null>", "confidence": <float 0-1>},
        "d) Did you suffer from any head injury?": {"value": "<string | null>", "confidence": <float 0-1>},
        "e) Duration of unconsciousness (if any)": {"value": "<string | null>", "confidence": <float 0-1>}
      }
    },
    "9) Have you or your spouse received treatment for sexually transmitted disease, AIDS/HIV?": {"answer": "<Yes | No | null>", "details": "<string | null>", "confidence": <float 0-1>}
  }
}
</output_schema>

<extraction_rules>

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

<details_extraction>
For Yes/No questions:
- Extract any handwritten text provided as additional details
- This may appear in the response line, margin, or nearby space
- If answer is "No" and no additional text, set details to null (except for Q7, where details are expected for "No")
- If answer is "Yes", look carefully for details (duration, medication, etc.) (except for Q7, where the details are expected for "No")
</details_extraction>

<sub_questions_extraction>
For questions with sub-questions (5, 6, 8):
- Sub-questions are ONLY relevant if the main answer is "Yes"
- If main answer is "No", set all sub_questions values to null
- Extract handwritten responses from designated areas
</sub_questions_extraction>

<handwriting_handling>
- Extract handwritten text as accurately as possible
- If text is partially legible, extract what you can read
- If completely illegible, use "[illegible]" as the value
- If field is empty/blank, use null
</handwriting_handling>

<medical_term_inference>
IMPORTANT: When handwriting is unclear, use medical context to infer the most likely term.

COMMON TERMS BY QUESTION:

Question 3k (Kidney):
- Conditions: Kidney stones, Renal calculi, CKD, Dialysis, Nephrectomy
- Medications: Cyclosporine, Tacrolimus

Question 3m (Blood thinners/Steroids):
- Blood thinners: Warfarin, Heparin, Aspirin, Clopidogrel, Rivaroxaban, Apixaban
- Steroids: Prednisolone, Prednisone, Dexamethasone, Betamethasone
- Immunosuppressants: Methotrexate, Azathioprine, Cyclosporine

Question 3n (Mental health):
- Conditions: Depression, Anxiety, Insomnia, Epilepsy, Panic attacks, OCD
- Medications: Escitalopram, Sertraline, Alprazolam, Clonazepam, Lorazepam

Question 4 (Medical tests):
- Tests: ECG, Echo, TMT, CT scan, MRI, USG, X-ray, Angiography, Endoscopy, Colonoscopy, Biopsy, FNAC

Question 5 (Surgery/Hospitalization):
- Surgeries: Appendectomy, Cholecystectomy, Hernia repair, CABG, Angioplasty, C-section
- Locations: Abdomen, Chest, Back, Knee, Hip

Question 7 (Vision/Hearing):
- Vision: Bifocal, Spectacles, Glasses, Myopia, Cataract, LASIK
- Hearing: Hearing aid, Hearing loss, Tinnitus

Question 8 (Accident/Injury):
- Injuries: Fracture, Dislocation, Ligament tear, Head injury, Spinal injury
- Treatments: Surgery, Physiotherapy, Cast, Plates, Screws

COMMON MISREADINGS TO CORRECT:
- "dialisis", "dialysis" → "Dialysis"
- "warfrin", "warfarin" → "Warfarin"
- "epilepsi", "epilepcy" → "Epilepsy"
- "appendectmy" → "Appendectomy"
- "angioplasty", "angioplasti" → "Angioplasty"
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
- "Jan 2020" → "01/2020" (month/year if day not provided)
- "2020" → "2020" (year only if that's all provided)
- "15-03-2020" → "15/03/2020"
</dates>

<duration>
Standardize duration formats:
- "5 yrs", "5 years", "5yrs" → "5 years"
- "6 months", "6 mths", "6m" → "6 months"
- "since 2015" → "since 2015"
</duration>
</standardization_rules>

<response_format>
Return ONLY the JSON object. No explanations, no markdown code fences.
</response_format>
"""

USER_PROMPT = "Extract all question answers (Q3k through Q9) from this MER form Page 2 questions section."
