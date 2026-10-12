"""Tolerant JSON extraction and schema coercion helpers for VLM responses."""
import json
import re
from typing import Any, Dict, List, Optional, Sequence


def extract_json(text: str) -> Dict[str, Any]:
    """
    Extracts a JSON object from text that may be surrounded by markdown code blocks,
    explanations, or leading/trailing whitespace.
    """
    if not text or not isinstance(text, str):
        return {}

    cleaned = text.strip()

    # 1. Check for markdown code fences ```json ... ```
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL | re.IGNORECASE)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # 2. Find outermost curly braces { ... }
    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        candidate = cleaned[first_brace : last_brace + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            # Try cleaning trailing commas: e.g. ", }" -> " }"
            candidate_cleaned = re.sub(r",\s*([\}\]])", r"\1", candidate)
            try:
                return json.loads(candidate_cleaned)
            except json.JSONDecodeError:
                pass

    # 3. Direct parse attempt
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    return {}


def coerce_enum(
    value: Any,
    choices: Sequence[str],
    default: Optional[str] = None,
) -> Optional[str]:
    """
    Case-insensitive matching of a string or enum representation against an allowed list of choices.
    """
    if value is None:
        return default

    val_str = str(value).strip().lower()
    for choice in choices:
        if val_str == choice.lower():
            return choice
        # Also check if choice is inside val_str (e.g. "mostly asphalt" -> "asphalt")
        if choice.lower() in val_str:
            return choice

    return default


def coerce_float(
    value: Any,
    default: Optional[float] = None,
    minimum: Optional[float] = None,
    maximum: Optional[float] = None,
) -> Optional[float]:
    """
    Extracts and clamps a float value from numeric or string input (e.g. '7.5m' -> 7.5).
    """
    if value is None:
        return default

    parsed_val: Optional[float] = None
    if isinstance(value, (int, float)):
        parsed_val = float(value)
    elif isinstance(value, str):
        # Extract first decimal number pattern
        match = re.search(r"[-+]?\d*\.?\d+", value.strip())
        if match:
            try:
                parsed_val = float(match.group(0))
            except ValueError:
                pass

    if parsed_val is None:
        return default

    if minimum is not None:
        parsed_val = max(minimum, parsed_val)
    if maximum is not None:
        parsed_val = min(maximum, parsed_val)

    return parsed_val


def coerce_int(
    value: Any,
    default: Optional[int] = None,
    minimum: Optional[int] = None,
    maximum: Optional[int] = None,
) -> Optional[int]:
    """
    Extracts and clamps an integer from numeric or string input (e.g. '2 lanes' -> 2).
    """
    flt = coerce_float(value, default=None if default is None else float(default))
    if flt is None:
        return default

    int_val = int(round(flt))
    if minimum is not None:
        int_val = max(minimum, int_val)
    if maximum is not None:
        int_val = min(maximum, int_val)

    return int_val
