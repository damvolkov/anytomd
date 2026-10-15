"""Image describers: Python callbacks and the built-in Gemini providers."""

import threading
import time

import pytest

import anytomd


def test_sync_describer_receives_image_mime_and_prompt(single_image_docx):
    seen = []

    def describer(image: bytes, mime_type: str, prompt: str) -> str:
        seen.append((image, mime_type, prompt))
        return "a red square"

    result = anytomd.convert_bytes(single_image_docx, "docx", image_describer=describer)
    assert "![a red square]" in result.markdown
    assert len(seen) == 1
    assert seen[0][1] == "image/png"
    assert seen[0][2].startswith("Describe")


def test_describer_replacement_lands_in_plain_text_too(single_image_docx):
    result = anytomd.convert_bytes(single_image_docx, "docx", image_describer=lambda *args: "ALT")
    assert "ALT" in result.plain_text


def test_non_string_describer_return_degrades_to_warning(single_image_docx):
    def non_string(image: bytes, mime_type: str, prompt: str) -> int:
        return 42

    result = anytomd.convert_bytes(single_image_docx, "docx", image_describer=non_string)  # ty: ignore[invalid-argument-type]
    assert [w.code for w in result.warnings] == ["skipped_element"]


def test_describer_exception_degrades_to_warning(single_image_docx):
    def describer(image, mime_type, prompt):
        msg = "nope"
        raise RuntimeError(msg)

    result = anytomd.convert_bytes(single_image_docx, "docx", image_describer=describer)
    assert result.warnings[0].code == "skipped_element"


def test_strict_promotes_describer_failure(single_image_docx):
    def describer(image, mime_type, prompt):
        msg = "nope"
        raise RuntimeError(msg)

    with pytest.raises(anytomd.MalformedDocumentError):
        anytomd.convert_bytes(single_image_docx, "docx", image_describer=describer, strict=True)


def test_describer_frees_the_gil_during_long_conversion(single_image_docx):
    stop = threading.Event()
    ticks = []

    def heartbeat():
        while not stop.wait(0.001):
            ticks.append(1)

    def slow_describer(image, mime_type, prompt):
        time.sleep(0.05)
        return "slow alt"

    before = len(ticks)
    thread = threading.Thread(target=heartbeat)
    thread.start()
    try:
        result = anytomd.convert_bytes(single_image_docx, "docx", image_describer=slow_describer)
    finally:
        stop.set()
        thread.join()
    assert "slow alt" in result.markdown
    assert len(ticks) > before


def test_gemini_describer_constructs_from_explicit_key():
    describer = anytomd.GeminiDescriber("fake-key")
    assert callable(describer)


def test_gemini_describer_reads_environment(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "env-key")
    assert anytomd.GeminiDescriber() is not None


def test_gemini_describer_without_environment_raises(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(anytomd.ImageDescriptionError, match="GEMINI_API_KEY"):
        anytomd.GeminiDescriber()


def test_gemini_describer_accepts_model_override():
    assert anytomd.GeminiDescriber("fake-key", model="gemini-custom") is not None


def test_async_gemini_describer_constructs_from_explicit_key():
    assert anytomd.AsyncGeminiDescriber("fake-key") is not None


def test_async_gemini_describer_without_environment_raises(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(anytomd.ImageDescriptionError):
        anytomd.AsyncGeminiDescriber()


def test_gemini_describer_flows_through_rust_dispatch(raw):
    ### The image in report.docx already carries a descr, so the native describer is
    ### accepted and wired without ever reaching the network in this unit test.
    describer = anytomd.GeminiDescriber("fake-key")
    result = anytomd.convert_bytes(raw("report.docx"), "docx", image_describer=describer)
    assert "Sales chart" in result.markdown
