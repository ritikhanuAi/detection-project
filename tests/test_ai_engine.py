"""Unit tests for Phase 1: Core imaging, tolerant parsers, and VLM provider engine."""
import numpy as np
import pytest
from apps.core.imaging import downscale_to_width, laplacian_variance, encode_jpeg_base64
from apps.core.exceptions import VLMUnavailable
from apps.ai_engine.parsers import extract_json, coerce_enum, coerce_float, coerce_int
from apps.ai_engine.providers.mock import MockProvider
from apps.ai_engine.vlm_client import VLMClient


def test_downscale_to_width():
    # 1080p image (1920x1080)
    img = np.zeros((1080, 1920, 3), dtype=np.uint8)
    downscaled = downscale_to_width(img, max_width=768)
    assert downscaled.shape[1] == 768
    assert downscaled.shape[0] == int(1080 * (768 / 1920))

    # Image narrower than max_width stays unchanged
    small = np.zeros((200, 300, 3), dtype=np.uint8)
    assert downscale_to_width(small, max_width=768).shape == (200, 300, 3)


def test_laplacian_variance():
    # Uniform black image -> 0 variance
    black = np.zeros((100, 100, 3), dtype=np.uint8)
    assert laplacian_variance(black) == 0.0

    # High frequency noise/checkered -> high variance
    checkered = np.zeros((100, 100), dtype=np.uint8)
    checkered[::2, ::2] = 255
    assert laplacian_variance(checkered) > 100.0


def test_extract_json_markdown():
    text = '```json\n{"road_type": "Urban", "lanes": 2}\n```'
    data = extract_json(text)
    assert data == {"road_type": "Urban", "lanes": 2}


def test_extract_json_loose_text():
    text = 'Here is the analysis:\n{"road_type": "Highway", "pavement_type": "Asphalt"}\nHope this helps!'
    data = extract_json(text)
    assert data == {"road_type": "Highway", "pavement_type": "Asphalt"}


def test_coercers():
    assert coerce_enum("highway", ["Highway", "Urban", "Rural"]) == "Highway"
    assert coerce_enum("mostly concrete", ["Asphalt", "Concrete"]) == "Concrete"
    assert coerce_enum("gravel", ["Asphalt", "Concrete"], default="Unknown") == "Unknown"

    assert coerce_float("7.5m", default=0.0) == 7.5
    assert coerce_float("approx 12.3 meters") == 12.3
    assert coerce_float("invalid", default=3.5) == 3.5

    assert coerce_int("3 lanes", default=1) == 3
    assert coerce_int(4.2) == 4


def test_mock_provider():
    provider = MockProvider()
    resp = provider.generate("Stage 1 Road Profiling prompt", [])
    assert resp.status_code == 200
    data = extract_json(resp.raw_text)
    assert data["road_type"] == "Urban"
    assert data["lanes"] == 2


def test_vlm_client_mock_mode(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "mock")
    client = VLMClient()
    dummy_bytes = np.zeros((50, 50, 3), dtype=np.uint8).tobytes()

    result = client.query_detailed(dummy_bytes, "road profile test")
    assert result.provider == "mock"
    assert result.data["road_type"] == "Urban"
    assert result.degraded is False


def test_vlm_client_raises_when_unreachable(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:59999")  # Unreachable port
    monkeypatch.setenv("VLM_FALLBACK_MODEL", "qwen2.5vl:3b")
    monkeypatch.setenv("AI_FALLBACK_TO_MOCK", "False")

    client = VLMClient()
    dummy_bytes = np.zeros((50, 50, 3), dtype=np.uint8).tobytes()

    with pytest.raises(VLMUnavailable):
        client.query_detailed(dummy_bytes, "test prompt")
