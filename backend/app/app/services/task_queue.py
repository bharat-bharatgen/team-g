"""
MongoDB-backed task queue.

API endpoints enqueue tasks; the worker process polls and executes them.
Uses find_one_and_update for atomic task claiming (no double-picks).
"""

import logging
from datetime import datetime
from typing import Optional

from bson import ObjectId
from pymongo import ReturnDocument

from app.dependencies import get_database

logger = logging.getLogger(__name__)

COLLECTION = "tasks"


async def enqueue_task(case_id: str, task_type: str, priority: int = 0) -> str:
    """Insert a pending task. Returns the inserted task ID."""
    db = await get_database()
    doc = {
        "case_id": case_id,
        "task_type": task_type,
        "status": "pending",
        "priority": priority,
        "created_at": datetime.utcnow(),
        "started_at": None,
        "completed_at": None,
        "error": None,
    }
    result = await db[COLLECTION].insert_one(doc)
    task_id = str(result.inserted_id)
    logger.info(f"Enqueued {task_type} task {task_id} for case {case_id}")
    return task_id


async def claim_next_task() -> Optional[dict]:
    """Atomically claim the oldest pending task (higher priority first)."""
    db = await get_database()
    task = await db[COLLECTION].find_one_and_update(
        {"status": "pending"},
        {"$set": {"status": "processing", "started_at": datetime.utcnow()}},
        sort=[("priority", -1), ("created_at", 1)],
        return_document=ReturnDocument.AFTER,
    )
    return task


async def complete_task(task_id: str):
    """Mark task as completed."""
    db = await get_database()
    await db[COLLECTION].update_one(
        {"_id": ObjectId(task_id)},
        {"$set": {"status": "completed", "completed_at": datetime.utcnow()}},
    )


async def fail_task(task_id: str, error: str):
    """Mark task as failed with an error message."""
    db = await get_database()
    await db[COLLECTION].update_one(
        {"_id": ObjectId(task_id)},
        {"$set": {"status": "failed", "completed_at": datetime.utcnow(), "error": error}},
    )


async def ensure_indexes():
    """Create indexes for efficient polling and cleanup."""
    db = await get_database()
    col = db[COLLECTION]
    await col.create_index([("status", 1), ("priority", -1), ("created_at", 1)])
    await col.create_index("completed_at", expireAfterSeconds=7 * 24 * 3600)
