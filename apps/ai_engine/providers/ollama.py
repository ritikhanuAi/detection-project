"""Ollama local VLM provider implementation."""
import os
import time
import logging
import requests
from typing import Any, Dict, List, Optional

from apps.core.exceptions import VLMUnavailable
from .base import BaseVLMProvider, VLMResponse

logger = logging.getLogger(__name__)


class OllamaProvider(BaseVLMProvider):
    """Integrates with a local or containerized Ollama instance."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        temperature: float = 0.1,
    ):
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        self.model = model or os.getenv("VLM_MODEL", "qwen2.5vl:3b")
        self.timeout = int(timeout_seconds or os.getenv("VLM_TIMEOUT_SECONDS", "60"))
        self.temperature = float(os.getenv("VLM_TEMPERATURE", str(temperature)))

    def generate(self, prompt: str, images_b64: List[str], **kwargs: Any) -> VLMResponse:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt + "\nReturn strictly valid JSON only.",
            "images": images_b64,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": self.temperature,
                "num_predict": 512,
            },
        }

        start = time.perf_counter()
        try:
            resp = requests.post(url, json=payload, timeout=self.timeout)
            latency_ms = int((time.perf_counter() - start) * 1000)

            if resp.status_code != 200:
                msg = f"Ollama HTTP {resp.status_code} ({self.model}): {resp.text[:200]}"
                logger.warning(msg)
                raise VLMUnavailable(msg, details={"status_code": resp.status_code, "model": self.model})

            data = resp.json()
            raw_text = data.get("response", "")
            return VLMResponse(
                raw_text=raw_text,
                provider="ollama",
                model=self.model,
                latency_ms=latency_ms,
                status_code=resp.status_code,
                meta={"eval_count": data.get("eval_count"), "done": data.get("done")},
            )
        except requests.RequestException as e:
            latency_ms = int((time.perf_counter() - start) * 1000)
            msg = f"Failed to connect to Ollama at {self.base_url} ({self.model}): {e}"
            logger.warning(msg)
            raise VLMUnavailable(msg, details={"base_url": self.base_url, "model": self.model, "error": str(e)})

    def health(self) -> Dict[str, Any]:
        url = f"{self.base_url}/api/tags"
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                models = [m.get("name") for m in resp.json().get("models", [])]
                return {
                    "provider": "ollama",
                    "status": "healthy",
                    "base_url": self.base_url,
                    "target_model": self.model,
                    "model_available": any(self.model in name for name in models),
                    "installed_models": models,
                }
            return {"provider": "ollama", "status": "unhealthy", "code": resp.status_code}
        except Exception as e:
            return {"provider": "ollama", "status": "unreachable", "error": str(e)}
