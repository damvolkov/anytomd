"""VisionSettings: ANYTOMD_VISION_* to a VisionSpec, None without a model."""

from anytomd.config.vision import VisionSettings
from anytomd.infra.specs import VisionSpec


async def test_vision_without_model_is_none(monkeypatch) -> None:
    monkeypatch.delenv("ANYTOMD_VISION_MODEL", raising=False)
    assert VisionSettings().spec() is None


async def test_vision_spec_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("ANYTOMD_VISION_MODEL", "qwen")
    monkeypatch.setenv("ANYTOMD_VISION_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("ANYTOMD_VISION_MAX_TOKENS", "32")
    assert VisionSettings().spec() == VisionSpec(model="qwen", base_url="https://example.test/v1", max_tokens=32)
