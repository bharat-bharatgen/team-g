"""
Face-match V2 processing pipeline using InsightFace.

Step 1: Download photo (geo-tagged selfie) and ID proof from S3
Step 2: Preprocess ID card (perspective correction, enhancement)
Step 3: Run InsightFace (buffalo_sc / MobileFaceNet) face detection + embedding
Step 4: Calculate cosine similarity
Step 5: Store versioned result in MongoDB

Key improvements over V1:
- Better ID card preprocessing (perspective correction, CLAHE)
- MobileFaceNet embeddings (512-D, higher accuracy on LFW)
- Rotation fallback for ID cards
- Largest face selection for ID cards (handles holograms/watermarks)
"""

import asyncio
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
cv2.setNumThreads(1)
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from app.services.storage import s3_service
from app.services.common.tesseract_ocr import normalize_to_image
from app.models.face_match_result import FaceMatchResultModel, MatchDecision, ReviewStatus
from app.dependencies import get_database

from .preprocessing import preprocess_id_card, rotate_image


# ─── Model paths ─────────────────────────────────────────────────────────────

MODELS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "models" / "onnx"
BUFFALO_SC_DIR = MODELS_DIR / "buffalo_sc"

# InsightFace similarity threshold (different scale from SFace)
# InsightFace cosine similarity typically ranges 0.2-0.8 for same person
DEFAULT_SIMILARITY_THRESHOLD = 0.4

ALGORITHM_VERSION = "v2"


# ─── Lazy model loading ──────────────────────────────────────────────────────

_face_analyzer = None


def _get_face_analyzer():
    """Lazy-load InsightFace analyzer with buffalo_sc model."""
    global _face_analyzer
    
    if _face_analyzer is not None:
        return _face_analyzer
    
    from insightface.app import FaceAnalysis
    
    # Check if model exists locally
    if BUFFALO_SC_DIR.exists():
        # Use local model
        _face_analyzer = FaceAnalysis(
            name='buffalo_sc',
            root=str(MODELS_DIR),
            providers=['CPUExecutionProvider']
        )
    else:
        # Download model (will cache to ~/.insightface/models/)
        _face_analyzer = FaceAnalysis(
            name='buffalo_sc',
            providers=['CPUExecutionProvider']
        )
    
    _face_analyzer.prepare(ctx_id=-1, det_size=(640, 640))
    return _face_analyzer


# ─── Similarity to percentage conversion ─────────────────────────────────────

def similarity_to_match_percent(sim: float, threshold: float = DEFAULT_SIMILARITY_THRESHOLD) -> int:
    """
    Convert cosine similarity to user-friendly match percentage.
    
    - Match (sim >= threshold): 75% - 99%
    - No match (sim < threshold): 0% - 74%
    
    This ensures matches always show 75%+ which is more convincing for users.
    """
    if sim <= 0:
        return 0
    
    if sim >= threshold:
        # Match: map [threshold, 1.0] → [75%, 99%]
        percent = 75 + (sim - threshold) / (1.0 - threshold) * 24
    else:
        # No match: map [0, threshold] → [0%, 74%]
        percent = (sim / threshold) * 74
    
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


def _extract_faces(image_bgr: np.ndarray):
    """
    Extract faces using InsightFace.
    
    Returns:
        List of face objects with .embedding and .bbox attributes
    """
    analyzer = _get_face_analyzer()
    return analyzer.get(image_bgr)


def _get_largest_face(faces) -> Optional[object]:
    """
    Get the largest face by bounding box area.
    
    Useful for ID cards where holograms/watermarks may be detected as small faces.
    """
    if not faces:
        return None
    
    # bbox format: [x1, y1, x2, y2]
    def face_area(face):
        bbox = face.bbox
        return (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
    
    return max(faces, key=face_area)


def _get_best_face(faces) -> Optional[object]:
    """
    Get the face with highest detection score.
    """
    if not faces:
        return None
    
    return max(faces, key=lambda f: f.det_score)


def _find_best_face_with_rotations(
    image_bgr: np.ndarray,
    rotations_k90: Tuple[int, ...] = (0, 1, 2, 3),
    use_largest: bool = False,
    preprocess_as_id: bool = False,
) -> Tuple[Optional[np.ndarray], int]:
    """
    Try multiple rotations to find a face; return (embedding, face_count).
    
    Args:
        image_bgr: Input image
        rotations_k90: Rotations to try (in 90-degree increments)
        use_largest: If True, pick largest face; else pick highest score
        preprocess_as_id: If True, apply ID card preprocessing
    
    Returns:
        (face_embedding, face_count_in_best_rotation)
    """
    best_embedding = None
    best_area = -1.0
    best_score = -1.0
    best_count = 0
    
    for k in rotations_k90:
        img = rotate_image(image_bgr, k)
        
        # Apply ID preprocessing if requested
        if preprocess_as_id:
            img = preprocess_id_card(img)
        
        faces = _extract_faces(img)
        count = len(faces)
        
        if count == 0:
            continue
        
        if use_largest:
            candidate = _get_largest_face(faces)
            if candidate is None:
                continue
            bbox = candidate.bbox
            area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
            if area > best_area:
                best_area = area
                best_embedding = candidate.embedding
                best_count = count
        else:
            candidate = _get_best_face(faces)
            if candidate is None:
                continue
            score = candidate.det_score
            if score > best_score:
                best_score = score
                best_embedding = candidate.embedding
                best_count = count
    
    return best_embedding, best_count


def _calculate_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
    """Calculate cosine similarity between two face embeddings."""
    sim = cosine_similarity(
        embedding1.reshape(1, -1),
        embedding2.reshape(1, -1)
    )[0][0]
    return float(sim)


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

    # Extract face from selfie (no rotation, no ID preprocessing)
    # Picks face with highest detection score (handles multiple faces in frame)
    person_embedding, person_face_count = _find_best_face_with_rotations(
        photo_bgr,
        rotations_k90=(0,),  # selfies typically upright
        use_largest=False,
        preprocess_as_id=False,
    )
    
    # Extract face from ID card (try rotations, use largest face, apply preprocessing)
    id_embedding, id_face_count = _find_best_face_with_rotations(
        id_bgr,
        rotations_k90=(0, 1, 2, 3),  # IDs may be rotated
        use_largest=True,  # Pick largest face to avoid holograms
        preprocess_as_id=True,
    )

    if person_embedding is None or id_embedding is None:
        return {
            "match": False,
            "confidence": 0.0,
            "person_face_count": person_face_count,
            "id_face_count": id_face_count,
            "decision": MatchDecision.INCONCLUSIVE,
            "message": "Could not detect face(s) in one or both images.",
        }

    # Calculate cosine similarity
    sim = _calculate_similarity(person_embedding, id_embedding)
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
    """Get the next version number for a case's face match result (v2 algorithm)."""
    db = await get_database()
    latest = await db.face_match_results.find_one(
        {"case_id": case_id, "algorithm_version": ALGORITHM_VERSION},
        sort=[("version", -1)],
        projection={"version": 1},
    )
    return (latest["version"] + 1) if latest else 1


async def _store_result(result: FaceMatchResultModel) -> str:
    """Store a face match result in MongoDB. Returns the inserted ID."""
    db = await get_database()
    doc = result.model_dump()
    doc["algorithm_version"] = ALGORITHM_VERSION
    insert = await db.face_match_results.insert_one(doc)
    return str(insert.inserted_id)


async def get_latest_result(case_id: str) -> Optional[dict]:
    """Get the latest face match v2 result for a case."""
    db = await get_database()
    doc = await db.face_match_results.find_one(
        {"case_id": case_id, "algorithm_version": ALGORITHM_VERSION},
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
    """Update the review status of the latest face match v2 result."""
    from datetime import datetime

    db = await get_database()
    result = await db.face_match_results.find_one_and_update(
        {"case_id": case_id, "algorithm_version": ALGORITHM_VERSION},
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

async def process_face_match_v2(
    case_id: str,
    photo_files: List[dict],
    id_files: List[dict],
    tolerance: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> dict:
    """
    Full face-match V2 processing pipeline:

    1. Download photo (geo-tagged selfie) and ID proof from S3
    2. Preprocess ID card (perspective correction, gamma, CLAHE)
    3. Run InsightFace (buffalo_sc) face matching
    4. Store versioned result in MongoDB

    Args:
        case_id: The case ID.
        photo_files: List of photo file entries (geo-tagged selfies)
        id_files: List of ID proof file entries
        tolerance: Cosine similarity threshold (default 0.55)

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

    # Run face matching synchronously (ONNX runtime not thread-safe)
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
        "algorithm_version": ALGORITHM_VERSION,
        "match": result["match"],
        "confidence": result["confidence"],
        "match_percent": match_percent,
        "decision": result["decision"].value,
        "message": result["message"],
        "photo_file_id": photo_entry["id"],
        "id_file_id": id_entry["id"],
    }
