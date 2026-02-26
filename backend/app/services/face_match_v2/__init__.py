"""
Face Match V2 - InsightFace-based face verification.

Uses MobileFaceNet (buffalo_sc) for improved accuracy on ID verification tasks.
"""

from .processor import (
    process_face_match_v2,
    get_latest_result,
    update_review_status,
    DEFAULT_SIMILARITY_THRESHOLD,
)

__all__ = [
    "process_face_match_v2",
    "get_latest_result",
    "update_review_status",
    "DEFAULT_SIMILARITY_THRESHOLD",
]
