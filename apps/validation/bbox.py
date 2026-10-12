"""Universal Bounding Box Normalizer supporting common vision formats, auto-repair, and clamping."""
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

from apps.core.exceptions import BBoxError


class BBoxFormat(str, Enum):
    XYXY = "xyxy"
    XYWH = "xywh"
    CXCYWH = "cxcywh"
    NORMALIZED_XYXY = "normalized_xyxy"
    NORMALIZED_XYWH = "normalized_xywh"


@dataclass(slots=True)
class NormalizedBBox:
    xmin: float
    ymin: float
    xmax: float
    ymax: float
    width: float
    height: float
    format_detected: str

    def to_dict(self) -> Dict[str, float]:
        return {
            "xmin": self.xmin,
            "ymin": self.ymin,
            "xmax": self.xmax,
            "ymax": self.ymax,
            "width": self.width,
            "height": self.height,
        }

    def to_xyxy_int(self) -> Tuple[int, int, int, int]:
        return (int(round(self.xmin)), int(round(self.ymin)), int(round(self.xmax)), int(round(self.ymax)))

    def to_xywh(self) -> List[float]:
        return [self.xmin, self.ymin, self.width, self.height]


def _extract_box_values(raw_box: Any) -> Tuple[float, float, float, float]:
    """Extracts 4 numerical values from diverse formats (list, dict)."""
    if isinstance(raw_box, (list, tuple)):
        if len(raw_box) < 4:
            raise BBoxError(f"Bounding box list has fewer than 4 elements: {raw_box}")
        return float(raw_box[0]), float(raw_box[1]), float(raw_box[2]), float(raw_box[3])

    if isinstance(raw_box, dict):
        # Format 1: xmin, ymin, xmax, ymax
        if all(k in raw_box for k in ("xmin", "ymin", "xmax", "ymax")):
            return float(raw_box["xmin"]), float(raw_box["ymin"]), float(raw_box["xmax"]), float(raw_box["ymax"])
        # Format 2: x1, y1, x2, y2
        if all(k in raw_box for k in ("x1", "y1", "x2", "y2")):
            return float(raw_box["x1"]), float(raw_box["y1"]), float(raw_box["x2"]), float(raw_box["y2"])
        # Format 3: x, y, width, height / x, y, w, h
        x = raw_box.get("x", raw_box.get("left"))
        y = raw_box.get("y", raw_box.get("top"))
        w = raw_box.get("width", raw_box.get("w"))
        h = raw_box.get("height", raw_box.get("h"))
        if None not in (x, y, w, h):
            return float(x), float(y), float(x) + float(w), float(y) + float(h)
        # Format 4: inner bbox key
        if "bbox" in raw_box and isinstance(raw_box["bbox"], (list, tuple, dict)):
            return _extract_box_values(raw_box["bbox"])

    raise BBoxError(f"Cannot extract 4 bounding box coordinates from: {raw_box}")


def normalize_bounding_box(
    raw_box: Any,
    img_width: int,
    img_height: int,
    expected_format: Optional[Union[str, BBoxFormat]] = None,
) -> Dict[str, float]:
    """
    Universal normalizer that converts any bounding box into absolute [xmin, ymin, xmax, ymax]
    and guarantees valid coordinates:
    - Auto-detects relative normalized [0, 1] vs absolute pixel values.
    - Swaps inverted coordinates (x2 < x1 or y2 < y1).
    - Clamps strictly to [0, img_width] and [0, img_height].
    - Enforces a minimum 1-pixel area to avoid zero-division errors during cropping.
    """
    if img_width <= 0 or img_height <= 0:
        raise ValueError(f"Invalid image dimensions: {img_width}x{img_height}")

    if isinstance(expected_format, Enum):
        fmt = expected_format.value.lower()
    elif expected_format:
        fmt = str(expected_format).lower()
        if "." in fmt:
            fmt = fmt.split(".")[-1]
    else:
        fmt = None

    c1, c2, c3, c4 = _extract_box_values(raw_box)

    # Auto-detect normalized coordinates: all values between 0.0 and 1.05
    is_normalized = all(0.0 <= val <= 1.05 for val in (c1, c2, c3, c4))

    if is_normalized:
        c1 *= img_width
        c2 *= img_height
        c3 *= img_width
        c4 *= img_height

    # Detect coordinate representation if not specified
    if fmt == BBoxFormat.XYWH.value:
        xmin, ymin, xmax, ymax = c1, c2, c1 + c3, c2 + c4
        detected_fmt = BBoxFormat.XYWH.value
    elif fmt == BBoxFormat.CXCYWH.value:
        xmin, ymin, xmax, ymax = c1 - (c3 / 2), c2 - (c4 / 2), c1 + (c3 / 2), c2 + (c4 / 2)
        detected_fmt = BBoxFormat.CXCYWH.value
    elif fmt == BBoxFormat.XYXY.value:
        xmin, ymin, xmax, ymax = c1, c2, c3, c4
        detected_fmt = BBoxFormat.XYXY.value
    else:
        # Heuristic detection between XYWH and XYXY:
        # If c3 < c1 or c4 < c2 (and positive), c3/c4 represent width/height!
        # Also if c1 + c3 <= img_width and c3 < (img_width * 0.7), it is likely XYWH
        if c3 < c1 or c4 < c2:
            xmin, ymin, xmax, ymax = c1, c2, c1 + c3, c2 + c4
            detected_fmt = BBoxFormat.XYWH.value
        else:
            xmin, ymin, xmax, ymax = c1, c2, c3, c4
            detected_fmt = BBoxFormat.XYXY.value

    # Auto-repair inverted corners
    if xmax < xmin:
        xmin, xmax = xmax, xmin
    if ymax < ymin:
        ymin, ymax = ymax, ymin

    # Clamp to image boundaries
    xmin = max(0.0, min(float(img_width), xmin))
    ymin = max(0.0, min(float(img_height), ymin))
    xmax = max(0.0, min(float(img_width), xmax))
    ymax = max(0.0, min(float(img_height), ymax))

    # Enforce minimum 1-pixel area
    if (xmax - xmin) < 1.0:
        if xmax + 1.0 <= img_width:
            xmax = xmin + 1.0
        elif xmin - 1.0 >= 0:
            xmin = xmax - 1.0

    if (ymax - ymin) < 1.0:
        if ymax + 1.0 <= img_height:
            ymax = ymin + 1.0
        elif ymin - 1.0 >= 0:
            ymin = ymax - 1.0

    width = round(xmax - xmin, 2)
    height = round(ymax - ymin, 2)

    return {
        "xmin": round(xmin, 2),
        "ymin": round(ymin, 2),
        "xmax": round(xmax, 2),
        "ymax": round(ymax, 2),
        "width": width,
        "height": height,
    }
