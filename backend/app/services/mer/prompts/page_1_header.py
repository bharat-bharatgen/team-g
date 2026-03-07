"""
Page 1 Header extraction prompt - extracts only the header section.
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
Extract ONLY the header section fields from this cropped image.
</role>

<form_fields>
The header section contains these fields (top to bottom):
1. Branch Name (RUU/HPC/Name) - left side
2. Credit Life / Individual - right side of same row
3. Proposal Number / Policy Number - full width row
4. Full Name of Life Assured - full width row
5. Age - left side
6. Date of Birth (DD/MM/YYYY format) - middle
7. Gender (M/F/Others) - right side
8. Form of Identification Produced - checkbox row with options:
   □ Passport Number  □ Driving License No.  □ Ration Card No.
   □ Employment Identity Card No.  □ Others
   Note: Tick marks appear on the LEFT side of each option
</form_fields>

<output_schema>
{
  "header": {
    "Branch Name": {"value": "<string | null>", "confidence": <float 0-1>},
    "Credit Life / Individual": {"value": "<string | null>", "confidence": <float 0-1>},
    "Proposal Number / Policy Number": {"value": "<string | null>", "confidence": <float 0-1>},
    "Full Name of Life Assured": {"value": "<string | null>", "confidence": <float 0-1>},
    "Age": {"value": "<string | null>", "confidence": <float 0-1>},
    "Date of Birth": {"value": "<string | null>", "confidence": <float 0-1>},
    "Gender": {"value": "<string | null>", "confidence": <float 0-1>},
    "Form of Identification Produced": {"value": "<string | null>", "confidence": <float 0-1>}
  }
}
</output_schema>

<extraction_rules>
- If a field is empty/blank, use null
- If text is illegible, use "[illegible]"
- Convert dates to DD/MM/YYYY format
- Normalize Gender: "M" → "Male", "F" → "Female"
- For Age, extract just the numeric value (e.g., "27 YRS" → "27")
- For Form of ID, return the checked option name (e.g., "Driving License No.")
- Never guess - only extract what you can see
- If some proper text is written after Cerdit Life / Individual, only then extract it. otherwise output null.
</extraction_rules>

<confidence_scoring>
- 0.9-1.0: Clearly printed or very legible
- 0.7-0.89: Legible but some characters unclear
- 0.5-0.69: Partially legible
- 0.3-0.49: Mostly illegible
- 0.0-0.29: Cannot read
</confidence_scoring>


<response_format>
Return ONLY the JSON object. No explanations, no markdown.
</response_format>
"""

USER_PROMPT = "Extract all header fields from this MER form header section."
