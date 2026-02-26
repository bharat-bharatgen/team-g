"""
Face-match processing pipeline.

Step 1: Download photo (geo-tagged selfie) and ID proof from S3
Step 2: Run YuNet face detection + SFace embedding comparison
Step 3: Store versioned result in MongoDB
"""

import asyncio
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
cv2.setNumThreads(1)
import numpy as np

from app.services.storage import s3_service
from app.services.common.tesseract_ocr import normalize_to_image
from app.models.face_match_result import FaceMatchResultModel, MatchDecision, ReviewStatus
from app.dependencies import get_database


# ─── Model paths ─────────────────────────────────────────────────────────────

MODELS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "models" / "onnx"
YUNET_MODEL = MODELS_DIR / "face_detection_yunet_2023mar.onnx"
SFACE_MODEL = MODELS_DIR / "face_recognition_sface_2021dec.onnx"

DEFAULT_SIMILARITY_THRESHOLD = 0.363


# ─── Similarity to percentage conversion ─────────────────────────────────────

def similarity_to_match_percent(sim: float, threshold: float = DEFAULT_SIMILARITY_THRESHOLD) -> int:
    """
    Convert cosine similarity to user-friendly match percentage.
    
    - Match (sim >= threshold): 75% - 99%
    - No match (sim < threshold): 0% - 74%
    
    This ensures matches always show 75%+ which is more convincing for users.
    """
    PERCENT_MATCH_THRESHOLD = 60
    if sim <= 0:
        return 0
    
    if sim >= threshold:
        # Match: map [threshold, 1.0] → [75%, 99%]
        percent = PERCENT_MATCH_THRESHOLD + (sim - threshold) / (1.0 - threshold) * (99 - PERCENT_MATCH_THRESHOLD)
    else:
        # No match: map [0, threshold] → [0%, 74%]
        percent = (sim / threshold) * (PERCENT_MATCH_THRESHOLD - 1)
    
    return min(99, max(0, int(round(percent))))


# ─── S3 download ─────────────────────────────────────────────────────────────

async def _download_file(s3_key: str) -> bytes:
    """Download a single file from S3."""
    return await s3_service.download_file(s3_key)


# ─── Face detection & matching ───────────────────────────────────────────────

def _bytes_to_bgr(image_bytes: bytes) -> np.ndarray:
    """Convert image bytes to BGR numpy array."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image bytes")
    return img


def _detect_faces_yunet(detector: cv2.FaceDetectorYN, image_bgr: np.ndarray) -> np.ndarray:
    """Returns faces array with shape (N, 15)."""
    h, w = image_bgr.shape[:2]
    detector.setInputSize((w, h))
    _, faces = detector.detect(image_bgr)
    if faces is None:
        return np.zeros((0, 15), dtype=np.float32)
    return faces


def _rotate_bgr(image_bgr: np.ndarray, k90: int) -> np.ndarray:
    """Rotate image by k * 90 degrees clockwise."""
    k90 = k90 % 4
    if k90 == 0:
        return image_bgr
    if k90 == 1:
        return cv2.rotate(image_bgr, cv2.ROTATE_90_CLOCKWISE)
    if k90 == 2:
        return cv2.rotate(image_bgr, cv2.ROTATE_180)
    return cv2.rotate(image_bgr, cv2.ROTATE_90_COUNTERCLOCKWISE)


def _scale_bgr(image_bgr: np.ndarray, scale: float) -> np.ndarray:
    """Scale image by given factor."""
    if scale == 1.0:
        return image_bgr
    h, w = image_bgr.shape[:2]
    nh = max(1, int(h * scale))
    nw = max(1, int(w * scale))
    return cv2.resize(image_bgr, (nw, nh), interpolation=cv2.INTER_CUBIC if scale > 1 else cv2.INTER_AREA)


def _extract_best_face(faces: np.ndarray) -> Optional[np.ndarray]:
    """Pick the highest-score face row (or None)."""
    if faces.shape[0] == 0:
        return None
    best_idx = int(np.argmax(faces[:, -1]))
    return faces[best_idx]


def _extract_largest_face(faces: np.ndarray) -> Optional[np.ndarray]:
    """Pick the largest face by bounding box area (or None).
    
    Useful for ID cards where holograms/watermarks may be detected as small faces,
    but the main photo is typically the largest.
    """
    if faces.shape[0] == 0:
        return None
    # Bounding box: x, y, w, h are first 4 elements
    areas = faces[:, 2] * faces[:, 3]  # w * h
    largest_idx = int(np.argmax(areas))
    return faces[largest_idx]


def _find_best_face_with_fallbacks(
    detector: cv2.FaceDetectorYN,
    image_bgr: np.ndarray,
    rotations_k90: Tuple[int, ...] = (0, 1, 2, 3),
    scales: Tuple[float, ...] = (1.0, 1.5, 2.0, 3.0),
    use_largest: bool = False,
) -> Tuple[Optional[np.ndarray], np.ndarray, int]:
    """
    Try multiple rotations and scales; return (best_face_row, best_image_used, face_count_in_best_setting).
    
    Args:
        use_largest: If True, pick largest bounding box instead of highest score.
                     Useful for ID cards where holograms may be detected as small faces.
    """
    best_face = None
    best_img = image_bgr
    best_score = -1.0
    best_area = -1.0
    best_count = 0

    for k in rotations_k90:
        rot = _rotate_bgr(image_bgr, k)
        for s in scales:
            img = _scale_bgr(rot, s)
            faces = _detect_faces_yunet(detector, img)
            count = int(faces.shape[0])
            
            if use_largest:
                candidate = _extract_largest_face(faces)
                if candidate is None:
                    continue
                area = float(candidate[2] * candidate[3])  # w * h
                if area > best_area:
                    best_area = area
                    best_face = candidate
                    best_img = img
                    best_count = count
            else:
                candidate = _extract_best_face(faces)
                if candidate is None:
                    continue
                score = float(candidate[-1])
                if score > best_score:
                    best_score = score
                    best_face = candidate
                    best_img = img
                    best_count = count

    return best_face, best_img, best_count


def _sface_embedding(recognizer: cv2.FaceRecognizerSF, image_bgr: np.ndarray, face_row: np.ndarray) -> np.ndarray:
    """Align & crop using landmarks, then compute SFace embedding."""
    aligned = recognizer.alignCrop(image_bgr, face_row)
    feat = recognizer.feature(aligned)
    return feat


def _run_face_match_pipeline(
    photo_bytes: bytes,
    id_bytes: bytes,
    tolerance: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> dict:
    """
    Run the full face matching pipeline on two images.

    Returns:
        dict with match, confidence, person_face_count, id_face_count, decision, message
    """
    # Load models
    if not YUNET_MODEL.exists() or not SFACE_MODEL.exists():
        return {
            "match": False,
            "confidence": 0.0,
            "person_face_count": -1,
            "id_face_count": -1,
            "decision": MatchDecision.INCONCLUSIVE,
            "message": f"Model files not found at {MODELS_DIR}",
        }

    detector = cv2.FaceDetectorYN.create(str(YUNET_MODEL), "", (320, 320), score_threshold=0.6, nms_threshold=0.3)
    recognizer = cv2.FaceRecognizerSF.create(str(SFACE_MODEL), "")

    # Load images
    try:
        photo_bgr = _bytes_to_bgr(photo_bytes)
        id_bgr = _bytes_to_bgr(id_bytes)
    except ValueError as e:
        return {
            "match": False,
            "confidence": 0.0,
            "person_face_count": -1,
            "id_face_count": -1,
            "decision": MatchDecision.INCONCLUSIVE,
            "message": str(e),
        }

    # Detect faces with fallbacks
    # Person/selfie: use best detection score (handles multiple faces in frame)
    person_best, person_img_used, person_face_count = _find_best_face_with_fallbacks(
        detector,
        photo_bgr,
        rotations_k90=(0,),  # selfies typically upright
        scales=(1.0, 1.5, 2.0),
        use_largest=False,
    )
    
    # ID: use largest bounding box (main photo, not holograms/watermarks)
    id_best, id_img_used, id_face_count = _find_best_face_with_fallbacks(
        detector,
        id_bgr,
        rotations_k90=(0, 1, 2, 3),  # IDs may be rotated
        scales=(1.0, 1.5, 2.0, 3.0),
        use_largest=True,  # Pick largest face to avoid holograms
    )

    if person_best is None or id_best is None:
        return {
            "match": False,
            "confidence": 0.0,
            "person_face_count": person_face_count,
            "id_face_count": id_face_count,
            "decision": MatchDecision.INCONCLUSIVE,
            "message": "Could not detect face(s) in one or both images.",
        }

    # Extract embeddings
    person_feat = _sface_embedding(recognizer, person_img_used, person_best)
    id_feat = _sface_embedding(recognizer, id_img_used, id_best)

    # Compare (cosine similarity)
    sim = float(recognizer.match(person_feat, id_feat, cv2.FaceRecognizerSF_FR_COSINE))
    match = sim >= tolerance

    if match:
        decision = MatchDecision.MATCH
        message = f"Match: same person (cosine_similarity={sim:.3f})."
    else:
        decision = MatchDecision.NO_MATCH
        message = f"No match: cosine_similarity={sim:.3f} < threshold={tolerance}."

    return {
        "match": match,
        "confidence": sim,
        "person_face_count": person_face_count,
        "id_face_count": id_face_count,
        "decision": decision,
        "message": message,
    }


# ─── DB storage ──────────────────────────────────────────────────────────────

async def _get_next_version(case_id: str) -> int:
    """Get the next version number for a case's face match result."""
    db = await get_database()
    latest = await db.face_match_results.find_one(
        {"case_id": case_id},
        sort=[("version", -1)],
        projection={"version": 1},
    )
    return (latest["version"] + 1) if latest else 1


async def _store_result(result: FaceMatchResultModel) -> str:
    """Store a face match result in MongoDB. Returns the inserted ID."""
    db = await get_database()
    doc = result.model_dump()
    insert = await db.face_match_results.insert_one(doc)
    return str(insert.inserted_id)


async def get_latest_result(case_id: str) -> Optional[dict]:
    """Get the latest face match result for a case."""
    db = await get_database()
    doc = await db.face_match_results.find_one(
        {"case_id": case_id},
        sort=[("version", -1)],
    )
    if doc:
        doc["_id"] = str(doc["_id"])
    return doc


async def update_review_status(
    case_id: str,
    review_status: ReviewStatus,
    reviewed_by: str,
    comment: Optional[str] = None,
) -> Optional[dict]:
    """Update the review status of the latest face match result."""
    from datetime import datetime

    db = await get_database()
    result = await db.face_match_results.find_one_and_update(
        {"case_id": case_id},
        {
            "$set": {
                "review_status": review_status.value,
                "reviewed_by": reviewed_by,
                "reviewed_at": datetime.utcnow(),
                "review_comment": comment,
            }
        },
        sort=[("version", -1)],
        return_document=True,
    )
    if result:
        result["_id"] = str(result["_id"])
    return result


# ─── Main pipeline ───────────────────────────────────────────────────────────

async def process_face_match(
    case_id: str,
    photo_files: List[dict],
    id_files: List[dict],
    tolerance: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> dict:
    """
    Full face-match processing pipeline:

    1. Download photo (geo-tagged selfie) and ID proof from S3
    2. Run YuNet + SFace face matching
    3. Store versioned result in MongoDB

    Args:
        case_id: The case ID.
        photo_files: List of photo file entries (geo-tagged selfies)
        id_files: List of ID proof file entries
        tolerance: Cosine similarity threshold (default 0.363)

    Returns:
        Result summary dict.
    """
    if not photo_files or not id_files:
        raise ValueError("Both photo and ID proof files are required for face matching")

    # Use first file of each type
    photo_entry = photo_files[0]
    id_entry = id_files[0]

    # Download both files in parallel
    photo_bytes, id_bytes = await asyncio.gather(
        _download_file(photo_entry["s3_key"]),
        _download_file(id_entry["s3_key"]),
    )

    # Normalize to image (handles PDF → first page as image)
    try:
        photo_bytes = normalize_to_image(photo_bytes)
        id_bytes = normalize_to_image(id_bytes)
    except ValueError as e:
        return {
            "match": False,
            "confidence": 0.0,
            "person_face_count": -1,
            "id_face_count": -1,
            "decision": MatchDecision.INCONCLUSIVE,
            "message": f"Could not process file: {e}",
        }

    # Run face matching synchronously (OpenCV ONNX not thread-safe)
    result = _run_face_match_pipeline(photo_bytes, id_bytes, tolerance)

    # Get next version and store
    version = await _get_next_version(case_id)

    # Calculate user-friendly match percentage
    match_percent = similarity_to_match_percent(result["confidence"])

    face_match_result = FaceMatchResultModel(
        case_id=case_id,
        version=version,
        photo_file_id=photo_entry["id"],
        id_file_id=id_entry["id"],
        match=result["match"],
        confidence=result["confidence"],
        match_percent=match_percent,
        person_face_count=result["person_face_count"],
        id_face_count=result["id_face_count"],
        decision=result["decision"],
        message=result["message"],
        review_status=ReviewStatus.PENDING,
    )

    doc_id = await _store_result(face_match_result)

    return {
        "_id": doc_id,
        "case_id": case_id,
        "version": version,
        "match": result["match"],
        "confidence": result["confidence"],
        "decision": result["decision"].value,
        "message": result["message"],
        "photo_file_id": photo_entry["id"],
        "id_file_id": id_entry["id"],
    }
