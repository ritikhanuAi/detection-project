"""Mock deterministic VLM provider for testing and offline degradation fallback."""
import json
import logging
from typing import Any, Dict, List
from .base import BaseVLMProvider, VLMResponse

logger = logging.getLogger(__name__)


class MockProvider(BaseVLMProvider):
    """
    Returns realistic, deterministic JSON responses without making network requests.
    Supports both Stage 1 (Road Profiling) and Stage 2 (Defect Validation).
    """

    def __init__(self, latency_ms: int = 15):
        self.latency_ms = latency_ms

    def generate(self, prompt: str, images_b64: List[str], **kwargs: Any) -> VLMResponse:
        p_lower = prompt.lower()

        if any(k in p_lower for k in ("stage1", "stage 1", "road_type", "profil", "road")):
            payload = {
                "road_type": "Urban",
                "pavement_type": "Asphalt",
                "carriageway_type": "Undivided",
                "lanes": 2,
                "estimated_width_m": 7.0,
                "explanation": "Deterministic mock analysis: Two-lane undivided urban asphalt road with standard curbs.",
            }
        elif any(k in p_lower for k in ("stage2", "stage 2", "proposed defect", "look-alike", "defect", "validator")):
            payload = {
                "status": "Correct",
                "confidence": 0.92,
                "reason": "Deterministic mock analysis: Visible surface depression with distinct edge depression typical of pavement distress.",
            }
        else:
            payload = {
                "status": "success",
                "mock": True,
                "message": "Generic mock provider response",
            }

        return VLMResponse(
            raw_text=json.dumps(payload),
            provider="mock",
            model="mock-heuristic-v1",
            latency_ms=self.latency_ms,
            status_code=200,
            meta={"synthetic": True},
        )

    def health(self) -> Dict[str, Any]:
        return {
            "provider": "mock",
            "status": "healthy",
            "model": "mock-heuristic-v1",
            "offline": True,
        }
