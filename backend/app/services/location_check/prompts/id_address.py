"""
ID card address extraction prompt — LLM Vision.

Extracts address from Indian ID cards (Aadhaar, PAN, Voter ID, etc).
"""

from app.services.llm.config import LLMCallConfig

CONFIG = LLMCallConfig(
    model="qwen3.5-27b",
    temperature=0.0,
    response_format="json_object",
    top_p=1,
    top_k=1,
    seed=133,
)

SYSTEM_PROMPT = """You are an address extractor for Indian ID cards.

<task>
Extract the full address from this ID document image.
Supported documents: Aadhaar Card, PAN Card, Voter ID, Driving License, Passport.
</task>

<output>
Return a JSON object:
{
  "address": "<full address string or null>",
  "pincode": "<6-digit pincode if found, else null>",
  "id_type": "<detected ID type: aadhaar/pan/voter_id/driving_license/passport/unknown>"
}

If no address is found, return:
{"address": null, "pincode": null, "id_type": "<detected type or unknown>"}
</output>

<notes>
- Extract the complete address as a single string
- Preserve the original formatting (commas, line breaks as spaces)
- The pincode is a 6-digit number, usually at the end of the address
- For Aadhaar, address is typically on the back side
</notes>
"""


def build_user_prompt() -> str:
    """Build the user prompt for ID address extraction."""
    return "Extract the address from this ID card image. Return only the JSON object."
