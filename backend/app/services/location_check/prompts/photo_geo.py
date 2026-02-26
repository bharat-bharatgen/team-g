"""
Photo geo-location extraction prompt — LLM Vision.

Extracts GPS coordinates and/or address from geo-tagged photo overlays (GPS Map Camera apps).
Coordinates preferred, address as fallback.
"""

from app.services.llm.config import LLMCallConfig

CONFIG = LLMCallConfig(
#    base_url="http://10.67.18.3:8004/v1/chat/completions",
#    model="Qwen/Qwen3-VL-8B-Instruct",
    base_url="https://apps.bharatgen.dev/inference/v1/chat/completions",
    model="qwen3-vl-32b",
    temperature=0.0,
    response_format="json_object",
    top_p=1,
    top_k=1,
    seed=133,
)

SYSTEM_PROMPT = """You are a location extractor for geo-tagged photos.

<task>
Extract location information from the photo overlay. Look for:
1. GPS coordinates (latitude/longitude) - PREFERRED
2. Address text - FALLBACK if no coordinates

GPS overlay apps may show coordinates, address, or both.
</task>

<coordinate_formats>
Common coordinate formats:
- "Lat 28.6139° Long 77.2090°"
- "28°36'50.0"N 77°12'32.4"E"
- "28.6139, 77.2090"
- "N 28.6139 E 77.2090"
</coordinate_formats>

<output>
Return a JSON object with ALL fields:
{
  "lat": <float or null>,
  "lon": <float or null>,
  "address": "<address string if shown, else null>",
  "pincode": "<6-digit pincode if visible, else null>",
  "raw_text": "<full overlay text as seen>"
}

Examples:
- Coords found: {"lat": 28.6139, "lon": 77.2090, "address": null, "pincode": null, "raw_text": "Lat 28.6139° Long 77.2090°"}
- Address found: {"lat": null, "lon": null, "address": "Connaught Place, New Delhi", "pincode": "110001", "raw_text": "Connaught Place, New Delhi 110001"}
- Both found: {"lat": 28.6139, "lon": 77.2090, "address": "Connaught Place, New Delhi", "pincode": "110001", "raw_text": "..."}
- Nothing found: {"lat": null, "lon": null, "address": null, "pincode": null, "raw_text": null}
</output>

<validation>
For Indian coordinates:
- Latitude should be between 8 and 37
- Longitude should be between 68 and 97
If values are outside this range, they may be swapped or invalid.
</validation>
"""


def build_user_prompt() -> str:
    """Build the user prompt for photo geo extraction."""
    return "Extract location information (coordinates and/or address) from this photo. Return only the JSON object."
