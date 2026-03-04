"""
ID card preprocessing utilities for face_match_v2.

Includes:
- Perspective correction (homography-based)
- Image enhancement (gamma, CLAHE)
- Aspect-ratio preserving resize
"""

import cv2
import numpy as np
from typing import Optional, Tuple


def resize_with_aspect(image: np.ndarray, max_dim: int = 800) -> np.ndarray:
    """
    Resize image maintaining aspect ratio.
    
    Args:
        image: BGR image
        max_dim: Maximum dimension (width or height)
    
    Returns:
        Resized image
    """
    h, w = image.shape[:2]
    if max(h, w) <= max_dim:
        return image
    
    if w > h:
        new_w = max_dim
        new_h = int(h * max_dim / w)
    else:
        new_h = max_dim
        new_w = int(w * max_dim / h)
    
    return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)


def order_points(pts: np.ndarray) -> np.ndarray:
    """
    Order points in: top-left, top-right, bottom-right, bottom-left order.
    
    Args:
        pts: Array of 4 points
    
    Returns:
        Ordered points array
    """
    rect = np.zeros((4, 2), dtype=np.float32)
    
    # Sum of coordinates: top-left has smallest, bottom-right has largest
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    
    # Difference: top-right has smallest, bottom-left has largest
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    
    return rect


def four_point_transform(image: np.ndarray, pts: np.ndarray) -> np.ndarray:
    """
    Apply perspective transform using 4 corner points.
    
    Args:
        image: Input image
        pts: 4 corner points (ordered)
    
    Returns:
        Warped (perspective-corrected) image
    """
    rect = order_points(pts)
    (tl, tr, br, bl) = rect
    
    # Compute width of new image
    width_a = np.linalg.norm(br - bl)
    width_b = np.linalg.norm(tr - tl)
    max_width = max(int(width_a), int(width_b))
    
    # Compute height of new image
    height_a = np.linalg.norm(tr - br)
    height_b = np.linalg.norm(tl - bl)
    max_height = max(int(height_a), int(height_b))
    
    # Destination points
    dst = np.array([
        [0, 0],
        [max_width - 1, 0],
        [max_width - 1, max_height - 1],
        [0, max_height - 1]
    ], dtype=np.float32)
    
    # Perspective transform
    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, M, (max_width, max_height))
    
    return warped


def detect_document_corners(image: np.ndarray) -> Optional[np.ndarray]:
    """
    Detect document corners using edge detection and contour finding.
    
    Args:
        image: BGR image
    
    Returns:
        4 corner points if found, None otherwise
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    
    # Dilate to connect edge segments
    kernel = np.ones((3, 3), np.uint8)
    edges = cv2.dilate(edges, kernel, iterations=1)
    
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return None
    
    # Find largest contour
    largest_contour = max(contours, key=cv2.contourArea)
    
    # Check if contour is large enough (at least 10% of image area)
    img_area = image.shape[0] * image.shape[1]
    contour_area = cv2.contourArea(largest_contour)
    if contour_area < 0.1 * img_area:
        return None
    
    # Approximate to polygon
    peri = cv2.arcLength(largest_contour, True)
    approx = cv2.approxPolyDP(largest_contour, 0.02 * peri, True)
    
    # Must be quadrilateral
    if len(approx) == 4:
        return approx.reshape(4, 2).astype(np.float32)
    
    return None


def perspective_correct(image: np.ndarray) -> np.ndarray:
    """
    Attempt perspective correction on document image.
    
    Falls back to original if corners cannot be detected.
    
    Args:
        image: BGR image
    
    Returns:
        Perspective-corrected image (or original if correction fails)
    """
    corners = detect_document_corners(image)
    if corners is not None:
        try:
            return four_point_transform(image, corners)
        except Exception:
            pass
    return image


def apply_gamma_correction(image: np.ndarray, gamma: float = 1.2) -> np.ndarray:
    """
    Apply gamma correction for brightness adjustment.
    
    Args:
        image: BGR image
        gamma: Gamma value (>1 brightens, <1 darkens)
    
    Returns:
        Gamma-corrected image
    """
    inv_gamma = 1.0 / gamma
    table = np.array([
        ((i / 255.0) ** inv_gamma) * 255
        for i in range(256)
    ]).astype(np.uint8)
    
    return cv2.LUT(image, table)


def apply_clahe(image: np.ndarray, clip_limit: float = 2.0, tile_size: int = 8) -> np.ndarray:
    """
    Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) on L channel.
    
    Args:
        image: BGR image
        clip_limit: Contrast limiting threshold
        tile_size: Size of grid for histogram equalization
    
    Returns:
        Enhanced image
    """
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_size, tile_size))
    l_enhanced = clahe.apply(l)
    
    enhanced_lab = cv2.merge([l_enhanced, a, b])
    return cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)


def preprocess_id_card(
    image: np.ndarray,
    max_dim: int = 800,
    apply_perspective: bool = True,
    gamma: float = 1.2,
    clahe_clip: float = 2.0,
) -> np.ndarray:
    """
    Full preprocessing pipeline for ID card images.
    
    Steps:
    1. Resize maintaining aspect ratio
    2. Perspective correction (optional)
    3. Gamma correction
    4. CLAHE enhancement
    
    Args:
        image: BGR image
        max_dim: Maximum dimension after resize
        apply_perspective: Whether to attempt perspective correction
        gamma: Gamma correction value
        clahe_clip: CLAHE clip limit
    
    Returns:
        Preprocessed image
    """
    # 1. Resize maintaining aspect ratio
    img = resize_with_aspect(image, max_dim)
    
    # 2. Perspective correction (optional, may fail silently)
    if apply_perspective:
        img = perspective_correct(img)
    
    # 3. Gamma correction
    img = apply_gamma_correction(img, gamma)
    
    # 4. CLAHE enhancement
    img = apply_clahe(img, clip_limit=clahe_clip)
    
    return img


def rotate_image(image: np.ndarray, k90: int) -> np.ndarray:
    """
    Rotate image by k * 90 degrees clockwise.
    
    Args:
        image: BGR image
        k90: Number of 90-degree rotations
    
    Returns:
        Rotated image
    """
    k90 = k90 % 4
    if k90 == 0:
        return image
    if k90 == 1:
        return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    if k90 == 2:
        return cv2.rotate(image, cv2.ROTATE_180)
    return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
