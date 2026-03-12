import os
from typing import Optional
from pydantic import BaseModel

_DEFAULT_TIMEOUT = int(os.environ.get("LLM_TIMEOUT", "480"))


class LLMCallConfig(BaseModel):
    model: str = "gpt-4o"
    base_url: Optional[str] = None      # override per-call (different provider)
    api_key: Optional[str] = None       # override per-call
    temperature: float = 0.0
    response_format: str = "json_object"  # "text" or "json_object"
    timeout: int = _DEFAULT_TIMEOUT
    top_p: Optional[float] = 1       # nucleus sampling
    top_k: Optional[int] = 1         # top-k sampling
    seed: Optional[int] = 133        # for reproducibility
