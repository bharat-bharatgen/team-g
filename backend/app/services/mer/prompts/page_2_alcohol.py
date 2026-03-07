"""
Page 2 Alcohol section extraction prompt - extracts Q10a Y/N + alcohol table.
Used when split processing is enabled for better accuracy.
"""

from app.services.llm.config import LLMCallConfig

CONFIG = LLMCallConfig(
    base_url="https://apps.bharatgen.dev/inference/v1/chat/completions",
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
Extract ONLY Question 10 (Habits - Alcohol) from this cropped image of Page 2.
</role>

<form_layout>
This section contains:

10) Habits
    a) Do you consume alcohol?                                    Y / N  [details]

    ┌─────────────────┬────────────────────┬──────────────────────────────────────┐
    │ Type of Alcohol │    Quantity / day  │      For no. of months / years       │
    ├─────────────────┼────────────────────┼──────────────────────────────────────┤
    │ Beer            │ [________________] │ [________________] │ [______________]│
    │ Wine            │ [________________] │ [________________] │ [______________]│
    │ Spirit          │ [________________] │ [________________] │ [______________]│
    └─────────────────┴────────────────────┴──────────────────────────────────────┘

KEY LOCATIONS:
- Y/N for "Do you consume alcohol?" is on the RIGHT of the question text
- The table has 3 rows (Beer, Wine, Spirit) and columns for Quantity and Duration
</form_layout>

<output_schema>
{
  "alcohol": {
    "10a) Do you consume alcohol?": {
      "answer": "<Yes | No | null>",
      "confidence": <float 0-1>,
      "alcohol_table": {
        "Beer": {"quantity_per_day": "<string | null>", "duration": "<string | null>", "confidence": <float 0-1>},
        "Wine": {"quantity_per_day": "<string | null>", "duration": "<string | null>", "confidence": <float 0-1>},
        "Spirit": {"quantity_per_day": "<string | null>", "duration": "<string | null>", "confidence": <float 0-1>}
      }
    }
  }
}
</output_schema>

<extraction_rules>

<yes_no_detection>
Look for these indicators on the "Do you consume alcohol?" line:
- Circled "Y" or "N"
- Tick mark (✓) next to Y or N
- Handwritten "Yes" or "No"

Normalize to: "Yes", "No", or null (if unclear)
</yes_no_detection>

<alcohol_table_extraction>
CRITICAL: Only extract what is actually written in the table cells. Do NOT invent or guess values.

- If the answer to "Do you consume alcohol?" is "No", the table should be empty.
  Set all table fields to null.
- Some people write "N", "No", "Nil", or "-" inside the table cells. This means
  they don't consume that type. Set those fields to null.
- If a table row is completely empty/blank, set both quantity_per_day and duration to null.
- Only extract actual handwritten values like "2 bottles", "60 ml", "1 peg", "5 years", etc.

Common quantity formats: bottles, ml, pegs, glasses, cans, pints
Common duration formats: "5 years", "10 months", "since 2015", "occasionally"
</alcohol_table_extraction>

<!!!SPECIAL_CARE!!!>
Some people fill alcohol table with N or No sometimes. This means they don't consume alcohol.
In such cases, set all table fields to null or No.
If you see any text in alcohol table, analyze it properly and extract the information.
Don't generate the content of the alcohol table. Only extract the information as it is.
</!!!SPECIAL_CARE!!!>

<handwriting_handling>
- Extract handwritten text as accurately as possible
- If text is partially legible, extract what you can read
- If completely illegible, use "[illegible]" as the value
- If field is empty/blank, use null
</handwriting_handling>

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
<duration>
Standardize duration formats:
- "5 yrs", "5 years", "5yrs" → "5 years"
- "6 months", "6 mths", "6m" → "6 months"
- "since 2015" → "since 2015"
</duration>

<quantities>
Keep original units but standardize spelling:
- "2 btls", "2 bottles" → "2 bottles"
- "60 ml", "60ml" → "60 ml"
- "1 peg", "1peg" → "1 peg"
</quantities>
</standardization_rules>

<response_format>
Return ONLY the JSON object. No explanations, no markdown code fences.
</response_format>
"""

USER_PROMPT = "Extract the alcohol consumption question (Q10a) and alcohol table from this MER form Page 2 image."
