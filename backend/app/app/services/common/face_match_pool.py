"""
Process pool for face matching operations.

OpenCV DNN and InsightFace ONNX runtime are NOT thread-safe.
Using a ProcessPoolExecutor ensures each face match runs in an isolated
process, preventing segfaults from concurrent access.
"""

import sys
import atexit
import asyncio
import logging
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from threading import Lock
from typing import Callable, Any

logger = logging.getLogger(__name__)

# Use 'spawn' on macOS to avoid fork-related segfaults with C extensions
if sys.platform == "darwin":
    try:
        multiprocessing.set_start_method("spawn", force=True)
    except RuntimeError:
        pass  # Already set

_face_pool: ProcessPoolExecutor | None = None
_pool_lock = Lock()
_shutting_down = False


def _get_face_pool() -> ProcessPoolExecutor:
    """Lazy-initialize the face match process pool (thread-safe)."""
    global _face_pool
    if _face_pool is None:
        with _pool_lock:
            if _face_pool is None and not _shutting_down:
                from app.config import settings
                max_workers = settings.face_match_max_workers
                _face_pool = ProcessPoolExecutor(max_workers=max_workers)
                logger.info(f"Face match process pool initialized with {max_workers} workers")
    if _face_pool is None:
        raise RuntimeError("Face match pool is shut down")
    return _face_pool


def shutdown_face_pool(wait: bool = True):
    """
    Gracefully shutdown the face match process pool.
    
    Call this from FastAPI's shutdown event or when cleaning up.
    """
    global _face_pool, _shutting_down
    _shutting_down = True
    with _pool_lock:
        if _face_pool is not None:
            logger.info("Shutting down face match process pool...")
            try:
                _face_pool.shutdown(wait=wait, cancel_futures=True)
            except Exception as e:
                logger.warning(f"Error during face match pool shutdown: {e}")
            _face_pool = None
            logger.info("Face match process pool shut down")


# Register cleanup on interpreter exit
atexit.register(lambda: shutdown_face_pool(wait=False))


async def run_in_face_pool(func: Callable, *args: Any) -> Any:
    """
    Run a function in the face match process pool.
    
    Args:
        func: The function to run (must be picklable)
        *args: Arguments to pass to the function
    
    Returns:
        The result of the function call
    """
    loop = asyncio.get_running_loop()
    pool = _get_face_pool()
    return await loop.run_in_executor(pool, func, *args)
