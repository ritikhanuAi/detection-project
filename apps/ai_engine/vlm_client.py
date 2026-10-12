"""VLM client orchestrator with provider factory, fallback handling, and telemetry."""
import base64
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from apps.core.exceptions import VLMUnavailable
from apps.core.imaging import downscale_to_width, bgr_to_jpeg_bytes, bytes_to_bgr
from .parsers import extract_json
from .providers.base import BaseVLMProvider, VLMResponse
from .providers.gemini import GeminiProvider
from .providers.mock import MockProvider
from .providers.ollama import OllamaProvider

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class VLMResult:
    """Standardized result envelope returned by the VLM engine."""
    data: Dict[str, Any]
    raw_text: str
    provider: str
    model: str
    latency_ms: int
    degraded: bool = False
    attempts: int = 1
    warnings: List[str] = field(default_factory=list)


class VLMClient:
    """
    Factory orchestrator for vision-language models.
    Supports primary provider execution, model fallback (e.g. Qwen -> Moondream),
    optional mock degradation, and tolerant JSON recovery.
    """

    def __init__(self):
        self.reload_config()

    def reload_config(self) -> None:
        """Reloads active provider and fallback settings from environment variables."""
        self.provider_name = os.getenv("AI_PROVIDER", "ollama").lower()
        self.max_width = int(os.getenv("VLM_MAX_IMAGE_WIDTH", "768"))
        self.primary_model = os.getenv("VLM_MODEL", "qwen2.5vl:3b")
        self.fallback_model = os.getenv("VLM_FALLBACK_MODEL", "moondream:latest")
        self.allow_mock_fallback = os.getenv("AI_FALLBACK_TO_MOCK", "False").lower() in ("true", "1", "yes")

        # Provider instances
        self.providers: Dict[str, BaseVLMProvider] = {
            "ollama": OllamaProvider(model=self.primary_model),
            "gemini": GeminiProvider(),
            "mock": MockProvider(),
        }

    def _prepare_image_b64(self, image_bytes: bytes) -> str:
        """Safely resizes image bytes to max_width and returns base64 JPEG string."""
        bgr = bytes_to_bgr(image_bytes)
        if bgr is not None:
            resized = downscale_to_width(bgr, max_width=self.max_width)
            jpeg_bytes = bgr_to_jpeg_bytes(resized, max_width=self.max_width, quality=85)
            return base64.b64encode(jpeg_bytes).decode("utf-8")
        # Fallback to direct encoding if decoding fails
        return base64.b64encode(image_bytes).decode("utf-8")

    def query_detailed(self, image_bytes: bytes, prompt: str) -> VLMResult:
        """
        Executes multimodal inference and returns a comprehensive VLMResult envelope.
        Follows a strict failover sequence:
        1. Configured Primary Provider.
        2. Secondary Model (if on Ollama, tries VLM_FALLBACK_MODEL).
        3. Mock Provider (only if AI_FALLBACK_TO_MOCK=True).
        4. Raises VLMUnavailable if all fail.
        """
        img_b64 = self._prepare_image_b64(image_bytes)
        images = [img_b64]
        warnings: List[str] = []
        attempts = 0

        # 1. Primary execution
        primary_provider = self.providers.get(self.provider_name) or self.providers["ollama"]
        attempts += 1
        try:
            resp = primary_provider.generate(prompt, images)
            data = extract_json(resp.raw_text)
            if data:
                return VLMResult(
                    data=data,
                    raw_text=resp.raw_text,
                    provider=resp.provider,
                    model=resp.model,
                    latency_ms=resp.latency_ms,
                    degraded=False,
                    attempts=attempts,
                )
            warnings.append(f"Primary provider {self.provider_name} returned unparseable text: {resp.raw_text[:100]}")
        except Exception as e:
            msg = f"Primary provider '{self.provider_name}' failed: {e}"
            logger.warning(msg)
            warnings.append(msg)

        # 2. Secondary fallback (Ollama secondary model if primary was Ollama)
        if self.provider_name == "ollama" and self.fallback_model != self.primary_model:
            attempts += 1
            try:
                logger.info(f"Attempting secondary fallback model: {self.fallback_model}")
                fallback_provider = OllamaProvider(model=self.fallback_model)
                resp = fallback_provider.generate(prompt, images)
                data = extract_json(resp.raw_text)
                if data:
                    warnings.append(f"Recovered using secondary fallback model {self.fallback_model}")
                    return VLMResult(
                        data=data,
                        raw_text=resp.raw_text,
                        provider="ollama",
                        model=self.fallback_model,
                        latency_ms=resp.latency_ms,
                        degraded=True,
                        attempts=attempts,
                        warnings=warnings,
                    )
            except Exception as e:
                msg = f"Fallback model '{self.fallback_model}' failed: {e}"
                logger.warning(msg)
                warnings.append(msg)

        # 3. Mock fallback if explicitly allowed
        if self.allow_mock_fallback:
            attempts += 1
            logger.warning("All live VLM providers failed; activating MockProvider fallback.")
            mock_resp = self.providers["mock"].generate(prompt, images)
            data = extract_json(mock_resp.raw_text)
            warnings.append("Gracefully degraded to deterministic offline MockProvider.")
            return VLMResult(
                data=data,
                raw_text=mock_resp.raw_text,
                provider="mock",
                model="mock-heuristic-v1",
                latency_ms=mock_resp.latency_ms,
                degraded=True,
                attempts=attempts,
                warnings=warnings,
            )

        # 4. Critical failure: Raise exception rather than returning silent defaults
        error_summary = " | ".join(warnings) or "All VLM providers failed."
        raise VLMUnavailable(
            f"VLM inference unavailable: {error_summary}",
            details={"attempts": attempts, "warnings": warnings, "provider": self.provider_name},
        )

    def query(self, image_bytes: bytes, prompt: str) -> Dict[str, Any]:
        """
        Backward-compatible dictionary endpoint for existing pipeline callers.
        Returns the parsed data dictionary or raises VLMUnavailable on critical failure.
        """
        result = self.query_detailed(image_bytes, prompt)
        return result.data


# Global singleton instance
ai_client = VLMClient()
