"""
Page 3 Family History table extraction prompt.
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
Extract ONLY the Family History table (Question 12) from this cropped image.
</role>

<table_layout>
12) Family History of Life Assured

┌─────────────┬──────────┬───────────┬─────────────────────┬───────────────┐
│ Relationship│ Alive/   │ Present   │ If alive give       │ If not alive  │
│             │ Not Alive│ Age/Age   │ present state of    │ specify cause │
│             │          │ at Death  │ health              │ of death      │
├─────────────┼──────────┼───────────┼─────────────────────┼───────────────┤
│ Father      │ [______] │ [_______] │ [_________________] │ [___________] │
│ Mother      │ [______] │ [_______] │ [_________________] │ [___________] │
│ Brother(s)  │ [______] │ [_______] │ [_________________] │ [___________] │
│ Sister(s)   │ [______] │ [_______] │ [_________________] │ [___________] │
└─────────────┴──────────┴───────────┴─────────────────────┴───────────────┘

Each row has 4 data columns:
1. Alive/Not Alive status
2. Age (if alive) or Age at Death (if not alive)
3. Health status (if alive)
4. Cause of death (if not alive)
</table_layout>

<output_schema>
{
  "family_history": {
    "Father": {
      "alive_status": "<Alive | Not Alive | null>",
      "age_or_age_at_death": {"value": "<string | null>", "confidence": <float 0-1>},
      "health_status_or_cause_of_death": {"value": "<string | null>", "confidence": <float 0-1>}
    },
    "Mother": {
      "alive_status": "<Alive | Not Alive | null>",
      "age_or_age_at_death": {"value": "<string | null>", "confidence": <float 0-1>},
      "health_status_or_cause_of_death": {"value": "<string | null>", "confidence": <float 0-1>}
    },
    "Brother(s)": {
      "alive_status": "<Alive | Not Alive | null>",
      "age_or_age_at_death": {"value": "<string | null>", "confidence": <float 0-1>},
      "health_status_or_cause_of_death": {"value": "<string | null>", "confidence": <float 0-1>}
    },
    "Sister(s)": {
      "alive_status": "<Alive | Not Alive | null>",
      "age_or_age_at_death": {"value": "<string | null>", "confidence": <float 0-1>},
      "health_status_or_cause_of_death": {"value": "<string | null>", "confidence": <float 0-1>}
    }
  }
}
</output_schema>

<extraction_rules>

<alive_status>
Look for these indicators in the "Alive/Not Alive" column:
- "Alive", "A", "Living", "Yes", "Y" → "Alive"
- "Not Alive", "N/Alive", "Dead", "Deceased", "D", "No", "N" → "Not Alive"
- Empty or illegible → null
</alive_status>

<age_extraction>
- Extract numeric age value
- Common formats: "70 Yrs", "70yrs", "70 Y", "70 years", "70"
- For multiple siblings: may show comma-separated ages "57, 51 Yrs"
- Standardize to just the number(s)
</age_extraction>

<health_or_death>
If ALIVE - extract health status:
- Common: "Normal", "Good", "Healthy", "Fine", "OK"
- Conditions: "DM" (Diabetes), "HTN" (Hypertension), "Heart disease", "Asthma"

If NOT ALIVE - extract cause of death:
- Common: "Heart attack", "MI", "Cancer", "Stroke", "Old age", "Natural causes"
- "Accident", "Kidney failure", "Liver disease"
</health_or_death>

<common_misreadings>
- "N.Alive", "N. Alive", "N/Alive" → "Not Alive"
- "A live", "A.live" → "Alive"
- "Nornal", "Nrmal" → "Normal"
- "Helthy", "Healty" → "Healthy"
- "Deceaed", "Decesed" → "Deceased"
- "Hart attack", "Hear attack" → "Heart attack"
</common_misreadings>

</extraction_rules>

<row_alignment>
CRITICAL: Each row must be read carefully:
- Father row: First data row after header
- Mother row: Second data row
- Brother(s) row: Third data row
- Sister(s) row: Fourth data row

Don't mix up data between rows!
</row_alignment>

<confidence_scoring>
- 0.9-1.0: Clearly printed/legible
- 0.7-0.89: Legible but some characters unclear
- 0.5-0.69: Partially legible
- Below 0.5: Mostly illegible
</confidence_scoring>

<response_format>
Return ONLY the JSON object. No explanations, no markdown.
</response_format>
"""

USER_PROMPT = "Extract the Family History table (Question 12) from this MER form section."
