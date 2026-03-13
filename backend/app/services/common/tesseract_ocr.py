import io
import sys
import atexit
import asyncio
import logging
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from threading import Lock
from PIL import Image
import pytesseract
import fitz  # PyMuPDF
import warnings
from app.services.llm.context import current_case_id

Image.MAX_IMAGE_PIXELS = None
warnings.simplefilter('ignore', Image.DecompressionBombWarning)

logger = logging.getLogger(__name__)

# LiteLLM/vision models reject images above 178_956_970 pixels.
# Cap rendered pages to stay safely under that limit.
_MAX_PIXELS = 170_000_000

# Lock for PyMuPDF (fitz) - NOT thread-safe on macOS
_fitz_lock = Lock()

# ─── Safe Process Pool with Cleanup ───────────────────────────────────────────

# Use 'spawn' on macOS to avoid fork-related segfaults with C extensions
if sys.platform == "darwin":
    try:
        multiprocessing.set_start_method("spawn", force=True)
    except RuntimeError:
        pass  # Already set

_ocr_pool: ProcessPoolExecutor | None = None
_pool_lock = Lock()
_shutting_down = False


def _is_pool_broken(pool: ProcessPoolExecutor | None) -> bool:
    """Check if a ProcessPoolExecutor is broken (child process crashed)."""
    return pool is not None and getattr(pool, "_broken", False)


def _get_ocr_pool() -> ProcessPoolExecutor:
    """Lazy-initialize the OCR process pool (thread-safe).

    If the pool exists but is broken (a child process crashed), it is
    replaced with a fresh one so that subsequent OCR calls can succeed.
    """
    global _ocr_pool
    if _ocr_pool is None or _is_pool_broken(_ocr_pool):
        with _pool_lock:
            if _shutting_down:
                raise RuntimeError("OCR pool is shut down")
            if _ocr_pool is None or _is_pool_broken(_ocr_pool):
                if _ocr_pool is not None:
                    logger.warning("OCR process pool is broken — recreating")
                    try:
                        _ocr_pool.shutdown(wait=False)
                    except Exception:
                        pass
                from app.config import settings
                max_workers = settings.ocr_max_workers
                _ocr_pool = ProcessPoolExecutor(max_workers=max_workers)
                logger.info(f"OCR process pool initialized with {max_workers} workers")
    return _ocr_pool


def shutdown_ocr_pool(wait: bool = True):
    """
    Gracefully shutdown the OCR process pool.
    
    Call this from FastAPI's shutdown event or when cleaning up.
    """
    global _ocr_pool, _shutting_down
    _shutting_down = True
    with _pool_lock:
        if _ocr_pool is not None:
            logger.info("Shutting down OCR process pool...")
            try:
                _ocr_pool.shutdown(wait=wait, cancel_futures=True)
            except Exception as e:
                logger.warning(f"Error during OCR pool shutdown: {e}")
            _ocr_pool = None
            logger.info("OCR process pool shut down")


# Register cleanup on interpreter exit
atexit.register(lambda: shutdown_ocr_pool(wait=False))


def _ocr_single_image(image_bytes: bytes) -> str:
    """Run Tesseract OCR on a single image (CPU-bound, runs in process pool)."""
    image = Image.open(io.BytesIO(image_bytes))
    return pytesseract.image_to_string(image)


def pdf_to_page_images(pdf_bytes: bytes) -> list[dict]:
    """
    Convert each page of a PDF to a PNG image.
    Returns list of {"page_number": int, "image_bytes": bytes} (no OCR yet).

    Uses a lock because PyMuPDF (fitz) is NOT thread-safe on macOS.
    Large pages are rendered at a reduced DPI so the pixel count stays
    under _MAX_PIXELS (the LiteLLM vision-model limit).
    """
    with _fitz_lock:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        case_id = current_case_id.get()
        logger.info(
            "PDF_RENDER,case_id=%s,total_pages=%d,pdf_size_kb=%.1f",
            case_id, len(doc), len(pdf_bytes) / 1024,
        )
        pages = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            # Try 300 DPI first; downscale if the image would be too large
            dpi = 300
            rect = page.rect  # dimensions in points (1 pt = 1/72 in)
            width_px = rect.width * dpi / 72
            height_px = rect.height * dpi / 72
            total_px = width_px * height_px
            if total_px > _MAX_PIXELS:
                scale = (_MAX_PIXELS / total_px) ** 0.5
                dpi = int(dpi * scale)
                logger.info(
                    "PDF_RENDER_DOWNSCALE,case_id=%s,page=%d,original_px=%.0fM,dpi=%d",
                    case_id, page_num + 1, total_px / 1e6, dpi,
                )
            pix = page.get_pixmap(dpi=dpi)
            img_bytes = pix.tobytes("png")
            logger.info(
                "PDF_PAGE,case_id=%s,page=%d,dpi=%d,size_kb=%.1f",
                case_id, page_num + 1, dpi, len(img_bytes) / 1024,
            )
            pages.append({
                "page_number": page_num + 1,
                "image_bytes": img_bytes,
            })
        doc.close()
        return pages


# ─── Image normalization ─────────────────────────────────────────────────────

# Magic byte signatures
_PDF_SIG = b"%PDF"
_PNG_SIG = b"\x89PNG"
_JPEG_SIG = b"\xff\xd8\xff"


def normalize_to_image(file_bytes: bytes) -> bytes:
    """
    Normalize file bytes to a PNG/JPEG image.
    
    - PDF: converts first page to PNG
    - PNG/JPEG: passes through unchanged
    - Other formats: raises ValueError
    
    Args:
        file_bytes: Raw file bytes
        
    Returns:
        Image bytes (PNG or JPEG)
        
    Raises:
        ValueError: If file format is not supported (PNG, JPEG, or PDF)
    """
    if file_bytes.startswith(_PDF_SIG):
        pages = pdf_to_page_images(file_bytes)
        if not pages:
            raise ValueError("PDF has no pages")
        return pages[0]["image_bytes"]
    
    if file_bytes.startswith(_PNG_SIG) or file_bytes.startswith(_JPEG_SIG):
        return file_bytes
    
    raise ValueError("Unsupported file format; expected PNG, JPEG, or PDF")


async def ocr_image_async(image_bytes: bytes) -> str:
    """Run Tesseract OCR on a single image asynchronously via process pool."""
    loop = asyncio.get_running_loop()
    pool = _get_ocr_pool()
    return await loop.run_in_executor(pool, _ocr_single_image, image_bytes)


async def extract_from_file(file_bytes: bytes, content_type: str) -> list[dict]:
    """
    Extract OCR text from a file (PDF or image).

    Pages are OCR'd sequentially to avoid flooding the process pool with
    large images and causing OOM kills in child processes.

    Returns:
        List of dicts: [{"page_number": 1, "text": "...", "image_bytes": b"..."}, ...]
    """
    if content_type == "application/pdf":
        page_images = pdf_to_page_images(file_bytes)
        for page_info in page_images:
            page_info["text"] = await ocr_image_async(page_info["image_bytes"])
        return page_images
    else:
        text = await ocr_image_async(file_bytes)
        return [{"page_number": 1, "text": text, "image_bytes": file_bytes}]
