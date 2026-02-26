import asyncio
import base64
import logging
from typing import Optional
import httpx
from app.config import settings
from app.services.llm.config import LLMCallConfig

logger = logging.getLogger(__name__)

# Retries for transient server/network failures
MAX_RETRIES = 5
RETRY_BASE_DELAY = 1.0
RETRY_MAX_DELAY = 30.0


# Magic bytes for image format detection
_SIGNATURES = {
    b"\x89PNG": "image/png",
    b"\xff\xd8\xff": "image/jpeg",
    b"GIF8": "image/gif",
    b"RIFF": "image/webp",       # RIFF....WEBP
    b"BM": "image/bmp",
    b"II": "image/tiff",
    b"MM": "image/tiff",
}


def _detect_mime_type(img_bytes: bytes) -> str:
    """Detect image MIME type from raw bytes using magic signatures."""
    for sig, mime in _SIGNATURES.items():
        if img_bytes[:len(sig)] == sig:
            return mime
    return "image/png"  # fallback


async def call(
    system_prompt: str,
    user_prompt: str,
    config: LLMCallConfig,
    images: Optional[list[bytes]] = None,
) -> str:
    """
    Call the LLM API via httpx.

    Args:
        system_prompt: System-level instruction.
        user_prompt: User-level prompt text.
        config: LLMCallConfig with model, temperature, etc.
        images: Optional list of image bytes (any format) for vision inputs.

    Returns:
        The LLM response text.
    """
    base_url = (config.base_url or settings.llm_api_base_url).rstrip("/")
    api_key = config.api_key or settings.llm_api_key

    # Build user message content
    user_content = [{"type": "text", "text": user_prompt}]

    if images:
        for img_bytes in images:
            mime_type = _detect_mime_type(img_bytes)
            b64 = base64.b64encode(img_bytes).decode("utf-8")
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:{mime_type};base64,{b64}"},
            })

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    payload = {
        "model": config.model,
        "messages": messages,
        "temperature": config.temperature,
        "top_p": config.top_p,
        "top_k": config.top_k,
        "seed": config.seed
    }

    # Response format
    if config.response_format == "json_object":
        payload["response_format"] = {"type": "json_object"}

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=config.timeout) as http_client:
        for attempt in range(MAX_RETRIES):
            try:
                response = await http_client.post(
                    base_url,
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
            except (httpx.RemoteProtocolError, httpx.ConnectError, httpx.TimeoutException) as e:
                if attempt < MAX_RETRIES - 1:
                    delay = min(RETRY_BASE_DELAY * (2 ** attempt), RETRY_MAX_DELAY)
                    logger.warning(
                        "LLM request failed (attempt %s/%s): %s; retrying in %.1fs",
                        attempt + 1, MAX_RETRIES, e, delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    raise
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                if (status >= 500 or status == 429) and attempt < MAX_RETRIES - 1:
                    delay = min(RETRY_BASE_DELAY * (2 ** attempt), RETRY_MAX_DELAY)
                    logger.warning(
                        "LLM request HTTP %s (attempt %s/%s); retrying in %.1fs",
                        status, attempt + 1, MAX_RETRIES, delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    raise
