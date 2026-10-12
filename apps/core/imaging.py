"""CPU-safe imaging utilities for preprocessing, sharpness scoring, and conversions."""
import base64
import io
import os
from typing import Optional, Tuple
import cv2
import numpy as np
from PIL import Image


def downscale_to_width(image: np.ndarray, max_width: int = 768) -> np.ndarray:
    """
    Guarantees an image does not exceed max_width (default 768px).
    Preserves aspect ratio to prevent excessive memory and CPU cycle usage during VLM inference.
    """
    if image is None:
        raise ValueError("Cannot downscale None image")

    h, w = image.shape[:2]
    if w <= max_width:
        return image

    scale = max_width / float(w)
    new_w = max_width
    new_h = max(1, int(h * scale))
    return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)


def laplacian_variance(image: np.ndarray) -> float:
    """
    Calculates Laplacian variance for sharpness/blur scoring.
    Higher values indicate sharper edges; lower values indicate motion blur or out-of-focus frames.
    """
    if image is None:
        return 0.0

    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def imread_unicode(path: str) -> Optional[np.ndarray]:
    """
    Safely reads an image from disk, properly handling unicode/non-ASCII characters and special paths.
    Returns BGR numpy array or None if reading fails.
    """
    if not os.path.exists(path):
        return None

    try:
        data = np.fromfile(path, dtype=np.uint8)
        return cv2.imdecode(data, cv2.IMREAD_COLOR)
    except Exception:
        return None


def imwrite_unicode(path: str, image: np.ndarray, quality: int = 88) -> bool:
    """
    Safely writes an image to disk, handling unicode and creating parent directories if needed.
    """
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        ext = os.path.splitext(path)[1].lower() or ".jpg"
        if ext in (".jpg", ".jpeg"):
            params = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        elif ext == ".png":
            params = [int(cv2.IMWRITE_PNG_COMPRESSION), 6]
        else:
            params = []

        success, encoded = cv2.imencode(ext, image, params)
        if not success:
            return False
        with open(path, "wb") as f:
            encoded.tofile(f)
        return True
    except Exception:
        return False


def bgr_to_jpeg_bytes(image: np.ndarray, max_width: int = 768, quality: int = 85) -> bytes:
    """Converts a BGR image to JPEG bytes, optionally downscaling if width exceeds max_width."""
    if image is None:
        return b""
    img = downscale_to_width(image, max_width=max_width)
    success, encoded = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not success:
        return b""
    return encoded.tobytes()


def bgr_to_png_bytes(image: np.ndarray) -> bytes:
    """Converts a BGR image to PNG bytes."""
    if image is None:
        return b""
    success, encoded = cv2.imencode(".png", image)
    if not success:
        return b""
    return encoded.tobytes()


def encode_jpeg_base64(image: np.ndarray, max_width: int = 768, quality: int = 85) -> str:
    """Encodes a BGR numpy array to a base64 JPEG string."""
    jpeg_bytes = bgr_to_jpeg_bytes(image, max_width=max_width, quality=quality)
    return base64.b64encode(jpeg_bytes).decode("utf-8")


def bytes_to_bgr(image_bytes: bytes) -> Optional[np.ndarray]:
    """Decodes image bytes (JPEG, PNG, etc.) to BGR numpy array."""
    if not image_bytes:
        return None
    try:
        arr = np.frombuffer(image_bytes, dtype=np.uint8)
        return cv2.imdecode(arr, cv2.IMREAD_COLOR)
    except Exception:
        return None
