"""
Background worker that polls the MongoDB task queue and executes
pipeline processing tasks concurrently to maximize GPU utilization.

Multiple tasks run in parallel (up to MAX_CONCURRENT_TASKS) so that
non-GPU phases of one task (download, pre/post-processing) overlap
with the GPU phases of another, keeping the inference server busy.

Run with:  python -m app.worker
"""

import asyncio
import logging
import os

from app.config import settings

os.environ.setdefault("OMP_NUM_THREADS", str(settings.omp_num_threads))

from bson import ObjectId

from app.dependencies import connect_to_mongo, close_mongo_connection, get_database
from app.services.task_queue import claim_next_task, complete_task, fail_task, ensure_indexes
from app.services.orchestrator import (
    _run_mer,
    _run_pathology,
    _run_face_match,
    _run_risk,
    _run_location_check,
    _run_test_verification,
    _get_uploaded_files,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("worker")

MAX_CONCURRENT_TASKS = int(os.environ.get("WORKER_MAX_CONCURRENT", "4"))
POLL_INTERVAL_S = 0.5


async def execute_task(task: dict):
    """Dispatch a task to the appropriate pipeline runner."""
    case_id = task["case_id"]
    task_type = task["task_type"]

    db = await get_database()
    case = await db.cases.find_one({"_id": ObjectId(case_id)})
    if not case:
        raise ValueError(f"Case {case_id} not found")

    if task_type == "mer":
        mer_files = _get_uploaded_files(case, "mer")
        if not mer_files:
            raise ValueError(f"No uploaded MER files for case {case_id}")
        await _run_mer(case_id, mer_files)

    elif task_type == "pathology":
        path_files = _get_uploaded_files(case, "pathology")
        if not path_files:
            raise ValueError(f"No uploaded pathology files for case {case_id}")
        await _run_pathology(case_id, path_files)

    elif task_type == "face_match":
        photo_files = _get_uploaded_files(case, "photo")
        id_files = _get_uploaded_files(case, "id_proof")
        if not photo_files or not id_files:
            raise ValueError(f"Missing photo or ID files for case {case_id}")
        await _run_face_match(case_id, photo_files, id_files)

    elif task_type == "risk":
        await _run_risk(case_id)

    elif task_type == "location_check":
        photo_files = _get_uploaded_files(case, "photo")
        id_files = _get_uploaded_files(case, "id_proof")
        await _run_location_check(case_id, photo_files, id_files)

    elif task_type == "test_verification":
        await _run_test_verification(case_id)

    else:
        raise ValueError(f"Unknown task type: {task_type}")


async def worker_loop():
    """Poll for pending tasks and execute them concurrently.

    Up to MAX_CONCURRENT_TASKS run in parallel so that non-GPU phases
    (S3 download, Tesseract OCR, DB writes) of one task overlap with
    the GPU-bound LLM calls of another, keeping the GPU fully utilized.
    """
    logger.info(
        "Worker started — polling for tasks (max_concurrent=%s) …",
        MAX_CONCURRENT_TASKS,
    )

    sem = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
    in_flight: set[asyncio.Task] = set()

    async def _handle(task: dict):
        task_id = str(task["_id"])
        try:
            async with sem:
                await execute_task(task)
                await complete_task(task_id)
                logger.info(f"Task {task_id} completed")
        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}", exc_info=True)
            await fail_task(task_id, str(e))

    while True:
        # Clean up finished tasks
        done = {t for t in in_flight if t.done()}
        in_flight -= done
        for t in done:
            if t.exception():
                logger.error("Task wrapper raised: %s", t.exception())

        # Don't claim more work than we can run
        if len(in_flight) >= MAX_CONCURRENT_TASKS:
            await asyncio.sleep(POLL_INTERVAL_S)
            continue

        task = await claim_next_task()

        if task is None:
            await asyncio.sleep(POLL_INTERVAL_S)
            continue

        task_id = str(task["_id"])
        logger.info(
            "Claimed task %s: type=%s case=%s (in_flight=%s)",
            task_id, task["task_type"], task["case_id"], len(in_flight) + 1,
        )

        t = asyncio.create_task(_handle(task), name=f"task-{task_id}")
        in_flight.add(t)


async def recover_orphaned_tasks():
    """Reset tasks stuck in 'processing' from a previous worker crash/restart."""
    db = await get_database()
    result = await db.tasks.update_many(
        {"status": "processing"},
        {"$set": {"status": "pending", "started_at": None}},
    )
    if result.modified_count:
        logger.warning("Recovered %d orphaned task(s) stuck in 'processing'", result.modified_count)


async def main():
    await connect_to_mongo()
    await ensure_indexes()
    await recover_orphaned_tasks()
    try:
        await worker_loop()
    finally:
        await close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(main())
