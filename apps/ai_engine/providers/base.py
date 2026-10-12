"""Abstract contract and data models for VLM providers."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(slots=True)
class VLMResponse:
    """Raw response wrapper from an underlying VLM service."""
    raw_text: str
    provider: str
    model: str
    latency_ms: int
    status_code: int = 200
    meta: Dict[str, Any] = field(default_factory=dict)


class BaseVLMProvider(ABC):
    """Abstract interface that all vision-language providers must implement."""

    @abstractmethod
    def generate(self, prompt: str, images_b64: List[str], **kwargs: Any) -> VLMResponse:
        """
        Executes a multimodal query against the VLM with prompt and base64 images.
        Raises an exception if the provider is completely unreachable or times out.
        """
        pass

    @abstractmethod
    def health(self) -> Dict[str, Any]:
        """Checks connectivity and returns status information for the provider."""
        pass
