"""
Lab address extraction prompt — LLM Text.

Extracts lab/diagnostic center name and address from pathology report OCR text.
"""

from app.services.llm.config import LLMCallConfig

CONFIG = LLMCallConfig(
#    model="Qwen/Qwen3-14B",
    model="gpt-oss-120b",
    temperature=0.0,
    response_format="json_object",
    top_p=1,
    top_k=1,
    seed=133,
)

SYSTEM_PROMPT = """You are an address extractor for Indian pathology/diagnostic lab reports.

<task>
Extract the lab/diagnostic center name and address from the provided pathology report text.
The lab details are typically found in the letterhead, header, or footer of the report.
</task>

<output>
Return a JSON object:
{
  "lab_name": "<lab or diagnostic center name, or null>",
  "address": "<full address string, or null>",
  "pincode": "<6-digit pincode if found, else null>"
}

If no lab address is found, return:
{"lab_name": null, "address": null, "pincode": null}
</output>

<notes>
- Look for lab/diagnostic center details in header or footer sections
- The address may include: street, area, city, state, pincode
- The pincode is a 6-digit number (Indian postal code)
- Common lab names: SRL, Metropolis, Dr. Lal PathLabs, Thyrocare, etc.
- Ignore patient address — we want the LAB's address
</notes>
"""


def build_user_prompt(ocr_text: str) -> str:
    """Build the user prompt with OCR text."""
    return f"""Extract the lab/diagnostic center address from this pathology report text.
Return only the JSON object.

--- OCR TEXT ---
{ocr_text}
"""
