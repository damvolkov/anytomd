"""ImageFallback: OCR first, vision only on blanks, the author's alt kept, strict mode respected."""

import pytest

from anytomd.infra.errors import DescriptionError
from anytomd.logic.fallback import KEEP_ALT, ImageFallback, KeepAltError
from tests.conftest import FakeVision


class FakeOcr:
    def __init__(self, text: str) -> None:
        self.text = text

    def recognize(self, image: bytes) -> str:
        return self.text

    async def arecognize(self, image: bytes) -> str:
        return self.text


def fallback(ocr: str | None, vision: FakeVision | None, *, strict: bool = False) -> ImageFallback:
    return ImageFallback(FakeOcr(ocr) if ocr is not None else None, vision, strict=strict, concurrency=2)


async def test_fallback_hook_ocr_text_on_one_line() -> None:
    assert fallback("Title\n\nBody  text", FakeVision()).hook(b"x", "image/png", "p") == "Title Body text"


async def test_fallback_hook_vision_on_blank_ocr() -> None:
    assert fallback("", FakeVision()).hook(b"x", "image/png", "p") == "Image description: A red square"


async def test_fallback_hook_keeps_alt_when_silent() -> None:
    with pytest.raises(KeepAltError, match=KEEP_ALT):
        fallback("", None).hook(b"x", "image/png", "p")


async def test_fallback_hook_strict_empties_instead() -> None:
    assert fallback("", None, strict=True).hook(b"x", "image/png", "p") == ""


async def test_fallback_ahook_vision_on_blank_ocr() -> None:
    assert await fallback("", FakeVision()).ahook(b"x", "image/png", "p") == "Image description: A red square"


async def test_fallback_ahook_ocr_skips_vision() -> None:
    vision = FakeVision()
    assert await fallback("Text", vision).ahook(b"x", "image/png", "p") == "Text"
    assert vision.calls == []


async def test_fallback_resolve_keeps_newlines() -> None:
    assert fallback("Line one\nLine two", None).resolve(b"x", "image/png") == ("Line one\nLine two", ())


async def test_fallback_resolve_empty_without_vision() -> None:
    assert fallback("", None).resolve(b"x", "image/png") == ("", ())


async def test_fallback_resolve_empty_vision_answer_stays_empty() -> None:
    assert fallback("", FakeVision(answer="")).resolve(b"x", "image/png") == ("", ())


async def test_fallback_aresolve_vision_failure_is_a_warning() -> None:
    markdown, warnings = await fallback("", FakeVision(error=DescriptionError("down"))).aresolve(b"x", "image/png")
    assert (markdown, warnings[0].code, warnings[0].message) == ("", "skipped_element", "down")


async def test_fallback_active() -> None:
    assert fallback("", None).active
    assert fallback(None, FakeVision()).active
    assert not fallback(None, None).active
