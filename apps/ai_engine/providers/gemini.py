"""Google Gemini REST API VLM provider implementation."""
import os
import time
import logging
import requests
from typing import Any, Dict, List, Optional

from apps.core.exceptions import VLMUnavailable
from .base import BaseVLMProvider, VLMResponse

logger = logging.getLogger(__name__)


class GeminiProvider(BaseVLMProvider):
    """Integrates with Google Gemini multimodal API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        temperature: float = 0.1,
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        self.timeout = int(timeout_seconds or os.getenv("VLM_TIMEOUT_SECONDS", "30"))
        self.temperature = float(os.getenv("VLM_TEMPERATURE", str(temperature)))

    def generate(self, prompt: str, images_b64: List[str], **kwargs: Any) -> VLMResponse:
        if not self.api_key or not self.api_key.startswith("AIzaSy"):
            raise VLMUnavailable(
                "Gemini API key is missing or invalid. Must be a valid AI Studio key starting with 'AIzaSy'.",
                details={"provider": "gemini"},
            )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        parts: List[Dict[str, Any]] = [{"text": prompt + "\nRespond strictly in raw JSON without formatting."}]

        for b64 in images_b64:
            parts.append({
                "inlineData": {
                    "mimeType": "image/jpeg",
                    "data": b64,
                }
            })

        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "temperature": self.temperature,
                "responseMimeType": "application/json",
            },
        }
        headers = {
            "Content-Type": "application/json",
            "X-goog-api-key": self.api_key,
        }

        max_attempts = 3
        start = time.perf_counter()
        last_error = ""

        for attempt in range(max_attempts):
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
                latency_ms = int((time.perf_counter() - start) * 1000)

                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if not candidates:
                        raise VLMUnavailable("Gemini returned empty candidates", details={"response": data})
                    content_parts = candidates[0].get("content", {}).get("parts", [])
                    raw_text = content_parts[0].get("text", "") if content_parts else ""
                    return VLMResponse(
                        raw_text=raw_text,
                        provider="gemini",
                        model=self.model,
                        latency_ms=latency_ms,
                        status_code=200,
                    )

                last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                if resp.status_code in (429, 503) and attempt < max_attempts - 1:
                    time.sleep(1.5 * (attempt + 1))
                    continue

                raise VLMUnavailable(
                    f"Gemini API failed with {last_error}",
                    details={"status_code": resp.status_code, "model": self.model},
                )
            except requests.RequestException as e:
                last_error = str(e)
                if attempt < max_attempts - 1:
                    time.sleep(1.0 * (attempt + 1))
                else:
                    raise VLMUnavailable(
                        f"Network failure connecting to Gemini: {e}",
                        details={"model": self.model, "error": str(e)},
                    )

        raise VLMUnavailable(f"Gemini failed after {max_attempts} attempts: {last_error}")

    def health(self) -> Dict[str, Any]:
        has_key = bool(self.api_key and self.api_key.startswith("AIzaSy"))
        return {
            "provider": "gemini",
            "status": "healthy" if has_key else "unconfigured",
            "model": self.model,
            "has_api_key": has_key,
        }
