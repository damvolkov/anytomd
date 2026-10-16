"""BackendRegistry: optional backends resolve when installed, vanish cleanly when not, configure from env."""

import pytest

from anytomd.backends.registry import BackendRegistry
from anytomd.infra.errors import DescriptionError, MissingExtraError
from anytomd.infra.specs import VisionSpec


@pytest.fixture
def registry() -> BackendRegistry:
    return BackendRegistry()


async def test_registry_recognizer_installed(registry) -> None:
    assert registry.recognizer(ocr=True) is not None


async def test_registry_recognizer_off(registry) -> None:
    assert registry.recognizer(ocr=False) is None


async def test_registry_recognizer_missing(registry, missing_extra) -> None:
    missing_extra("liteparse")
    assert registry.recognizer(ocr=True) is None


async def test_registry_reader_missing(registry, missing_extra) -> None:
    missing_extra("liteparse")
    with pytest.raises(MissingExtraError, match=r"PDF needs the 'pdf' extra"):
        registry.reader(ocr=True)


async def test_registry_describer_from_spec(registry) -> None:
    assert registry.describer(VisionSpec(model="m", api_key="k")).concurrency == 4


async def test_registry_describer_from_environment(registry, monkeypatch) -> None:
    monkeypatch.setenv("ANYTOMD_VISION_MODEL", "env-model")
    monkeypatch.setenv("ANYTOMD_VISION_API_KEY", "k")
    monkeypatch.setenv("ANYTOMD_VISION_CONCURRENCY", "2")
    assert registry.describer(None).concurrency == 2


async def test_registry_describer_unconfigured(registry, monkeypatch) -> None:
    monkeypatch.delenv("ANYTOMD_VISION_MODEL", raising=False)
    assert registry.describer(None) is None


async def test_registry_describer_missing(registry, missing_extra) -> None:
    missing_extra("openai")
    assert registry.describer(VisionSpec(model="m")) is None


async def test_registry_require_unconfigured(registry, monkeypatch) -> None:
    monkeypatch.delenv("ANYTOMD_VISION_MODEL", raising=False)
    with pytest.raises(DescriptionError, match="ANYTOMD_VISION_MODEL"):
        registry.require(None)


async def test_registry_require_missing(registry, missing_extra) -> None:
    missing_extra("openai")
    with pytest.raises(MissingExtraError, match="vlm"):
        registry.require(None)


async def test_registry_settings_missing_falls_back_to_the_spec(registry, missing_extra) -> None:
    missing_extra("pydantic_settings")
    assert registry.describer(None) is None


async def test_registry_unrelated_import_errors_propagate(registry, monkeypatch) -> None:
    def broken(path: str):
        msg = "No module named 'typo'"
        raise ModuleNotFoundError(msg, name="typo")

    monkeypatch.setattr("importlib.import_module", broken)
    with pytest.raises(ModuleNotFoundError, match="typo"):
        registry.recognizer(ocr=True)
