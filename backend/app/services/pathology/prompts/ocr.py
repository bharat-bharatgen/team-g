"""
Pathology OCR prompt — Step 1 (Vision model).

Extracts structured data from a single pathology report page image.
Same prompt used for every page (no page classification needed).
"""

from typing import Optional
from app.services.llm.config import LLMCallConfig

CONFIG = LLMCallConfig(
#    base_url="http://10.67.18.3:8004/v1/chat/completions",
#    model="Qwen/Qwen3-VL-8B-Instruct",
    model="qwen3.5-27b",
    temperature=0.0,
    response_format="text",
    top_p=1,
    top_k=1,
    seed=133,
)

SYSTEM_PROMPT = """
<role>
You are an OCR assistant for pathology and medical reports.
</role>

<instructions>
Extract all text from the provided pathology and medical report image exactly as written.
Keep the capital, small letters, spaces as they are, do not auto-correct them.
Do not add any additional text or formatting.
Preserve the original layout, formatting, and line breaks.
</instructions>

<reference_ranges>
Most of the tests will have a reference range associated with it.
Make sure to capture the correct reference range for each test, and not take it from any nearby tests.
</reference_ranges>
"""


def build_user_prompt(page_number: Optional[int] = None) -> str:
    """Build the user prompt for a specific page."""
    return f"Extract all text from this image. Output only the extracted text, nothing else."
