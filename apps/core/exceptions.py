"""Domain and pipeline exception definitions for RoadAthena."""
from typing import Any, Dict, Optional


class ServiceError(Exception):
    """Base service exception with error code and structured details."""

    def __init__(
        self,
        message: str,
        code: str = "service_error",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": self.message,
            "code": self.code,
            "details": self.details,
        }


class PipelineError(ServiceError):
    """Raised when an unrecoverable pipeline failure occurs in Stage 1 or Stage 2."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="pipeline_error", details=details)


class VLMUnavailable(ServiceError):
    """Raised when all VLM providers/models are unreachable, timed out, or unconfigured."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="vlm_unavailable", details=details)


class BBoxError(ServiceError):
    """Raised when a bounding box format is invalid or cannot be parsed."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="bbox_error", details=details)
