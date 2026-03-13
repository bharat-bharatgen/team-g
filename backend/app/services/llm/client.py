import asyncio
import base64
import io
import logging
import os
import time
from typing import Optional
import httpx
from PIL import Image
from app.config import settings
from app.services.llm.config import LLMCallConfig
from app.services.llm.context import current_case_id, current_task, current_call_count

logger = logging.getLogger(__name__)

# Retries for transient server/network failures
MAX_RETRIES = 5
RETRY_BASE_DELAY = 1.0
RETRY_MAX_DELAY = 30.0

# Per-model semaphores to cap concurrent requests and prevent GPU overload.
# When multiple worker tasks run in parallel, total in-flight calls can spike;
# the semaphore ensures the inference server gets a steady, manageable load.
_MODEL_SEMAPHORES: dict[str, asyncio.Semaphore] = {}
_DEFAULT_MODEL_CONCURRENCY = int(os.environ.get("LLM_DEFAULT_CONCURRENCY", "8"))
_MODEL_CONCURRENCY_OVERRIDES: dict[str, int] = {
    "qwen3.5-27b": int(os.environ.get("LLM_CONCURRENCY_QWEN35_27B", "8")),
    "gpt-oss-120b": int(os.environ.get("LLM_CONCURRENCY_GPT_OSS_120B", "4")),
}


def _get_model_semaphore(model: str) -> asyncio.Semaphore:
    """Return (or create) the semaphore for a given model."""
    if model not in _MODEL_SEMAPHORES:
        limit = _MODEL_CONCURRENCY_OVERRIDES.get(model, _DEFAULT_MODEL_CONCURRENCY)
        _MODEL_SEMAPHORES[model] = asyncio.Semaphore(limit)
        logger.info("Created LLM semaphore for model=%s limit=%s", model, limit)
    return _MODEL_SEMAPHORES[model]

# Keep raw image bytes under 7 MB so the base64 result (~33 % overhead)
# stays well within typical provider data-URI limits (e.g. 10 MB).
_IMG_MAX_BYTES = 7 * 1024 * 1024


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


def _compress_image(img_bytes: bytes) -> tuple[bytes, str]:
    """Compress an image so the raw bytes stay under _IMG_MAX_BYTES.

    Returns (compressed_bytes, mime_type).
    Strategy: convert to JPEG, progressively lower quality, then resize if needed.
    """
    if len(img_bytes) <= _IMG_MAX_BYTES:
        return img_bytes, _detect_mime_type(img_bytes)

    img = Image.open(io.BytesIO(img_bytes))
    if img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGB")

    for quality in (85, 70, 55, 40):
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        if buf.tell() <= _IMG_MAX_BYTES:
            logger.debug("Compressed image: %d -> %d bytes (quality=%d)",
                         len(img_bytes), buf.tell(), quality)
            return buf.getvalue(), "image/jpeg"

    scale = 0.75
    while scale > 0.1:
        new_size = (int(img.width * scale), int(img.height * scale))
        resized = img.resize(new_size, Image.LANCZOS)
        buf = io.BytesIO()
        resized.save(buf, format="JPEG", quality=60, optimize=True)
        if buf.tell() <= _IMG_MAX_BYTES:
            logger.debug("Compressed+resized image: %d -> %d bytes (scale=%.2f)",
                         len(img_bytes), buf.tell(), scale)
            return buf.getvalue(), "image/jpeg"
        scale -= 0.1

    buf = io.BytesIO()
    img.resize((int(img.width * 0.1), int(img.height * 0.1)), Image.LANCZOS)\
       .save(buf, format="JPEG", quality=40, optimize=True)
    return buf.getvalue(), "image/jpeg"


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
    if not base_url.endswith("/chat/completions"):
        base_url = f"{base_url}/chat/completions"
    api_key = config.api_key or settings.llm_api_key
    model = config.model

    is_openrouter = False
    if settings.use_openrouter and model == "qwen3.5-27b":
        base_url = settings.openrouter_base_url
        api_key = settings.openrouter_api_key
        model = settings.openrouter_model
        is_openrouter = True
        logger.debug("OpenRouter override: %s -> %s", config.model, model)

    # Build user message content
    user_content = [{"type": "text", "text": user_prompt}]

    if images:
        for img_bytes in images:
            img_bytes, mime_type = _compress_image(img_bytes)
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
        "model": model,
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

    case_id = current_case_id.get()
    task = current_task.get()
    counter = current_call_count.get()
    sem = _get_model_semaphore(config.model)

    num_images = len(images) if images else 0
    t_wait = time.monotonic()

    async with sem:
        sem_wait = time.monotonic() - t_wait
        if sem_wait > 1.0:
            logger.info(
                "LLM_SEM_WAIT,case_id=%s,task=%s,model=%s,wait_s=%.2f",
                case_id, task, model, sem_wait,
            )
        t0 = time.monotonic()
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
                    content = data["choices"][0]["message"]["content"]
                    if counter is not None:
                        counter[0] += 1
                    logger.info(
                        "LLM_CALL,case_id=%s,task=%s,model=%s,latency_s=%.2f,attempts=%s,images=%s,status=success",
                        case_id, task, model, time.monotonic() - t0, attempt + 1, num_images,
                    )
                    return content
                except (httpx.RemoteProtocolError, httpx.ConnectError, httpx.TimeoutException) as e:
                    if attempt < MAX_RETRIES - 1:
                        delay = min(RETRY_BASE_DELAY * (2 ** attempt), RETRY_MAX_DELAY)
                        logger.warning(
                            "LLM_RETRY,case_id=%s,task=%s,model=%s,attempt=%s/%s,elapsed_s=%.2f,timeout_s=%s,images=%s,error=%s,retry_in=%.1fs",
                            case_id, task, model, attempt + 1, MAX_RETRIES,
                            time.monotonic() - t0, config.timeout, num_images,
                            type(e).__name__, delay,
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            "LLM_CALL,case_id=%s,task=%s,model=%s,latency_s=%.2f,attempts=%s,timeout_s=%s,images=%s,status=error,error=%s",
                            case_id, task, model, time.monotonic() - t0, attempt + 1,
                            config.timeout, num_images, e,
                        )
                        raise
                except httpx.HTTPStatusError as e:
                    status = e.response.status_code
                    body = e.response.text[:500]
                    if (status >= 500 or status == 429) and attempt < MAX_RETRIES - 1:
                        delay = min(RETRY_BASE_DELAY * (2 ** attempt), RETRY_MAX_DELAY)
                        logger.warning(
                            "LLM_RETRY,case_id=%s,task=%s,model=%s,attempt=%s/%s,elapsed_s=%.2f,images=%s,error=HTTP %s,retry_in=%.1fs,body=%s",
                            case_id, task, model, attempt + 1, MAX_RETRIES,
                            time.monotonic() - t0, num_images, status, delay, body,
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            "LLM_CALL,case_id=%s,task=%s,model=%s,latency_s=%.2f,attempts=%s,images=%s,status=error,error=HTTP %s,body=%s",
                            case_id, task, model, time.monotonic() - t0, attempt + 1,
                            num_images, status, body,
                        )
                        raise
