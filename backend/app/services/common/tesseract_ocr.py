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

Image.MAX_IMAGE_PIXELS = None
warnings.simplefilter('ignore', Image.DecompressionBombWarning)

logger = logging.getLogger(__name__)

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


def _get_ocr_pool() -> ProcessPoolExecutor:
    """Lazy-initialize the OCR process pool (thread-safe)."""
    global _ocr_pool
    if _ocr_pool is None:
        with _pool_lock:
            if _ocr_pool is None and not _shutting_down:
                from app.config import settings
                max_workers = settings.ocr_max_workers
                _ocr_pool = ProcessPoolExecutor(max_workers=max_workers)
                logger.info(f"OCR process pool initialized with {max_workers} workers")
    if _ocr_pool is None:
        raise RuntimeError("OCR pool is shut down")
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
    """
    with _fitz_lock:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            pix = page.get_pixmap(dpi=300)
            img_bytes = pix.tobytes("png")
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
    Extract OCR text from a file (PDF or image), with parallel OCR across pages.

    Returns:
        List of dicts: [{"page_number": 1, "text": "...", "image_bytes": b"..."}, ...]
    """
    if content_type == "application/pdf":
        page_images = pdf_to_page_images(file_bytes)
        ocr_tasks = [ocr_image_async(p["image_bytes"]) for p in page_images]
        ocr_texts = await asyncio.gather(*ocr_tasks)
        for page_info, text in zip(page_images, ocr_texts):
            page_info["text"] = text
        return page_images
    else:
        text = await ocr_image_async(file_bytes)
        return [{"page_number": 1, "text": text, "image_bytes": file_bytes}]
