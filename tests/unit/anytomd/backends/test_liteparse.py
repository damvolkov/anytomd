"""LiteparseBackend: real OCR and PDF reading, misses as empty text, refusals as MalformedDocumentError."""

import pytest

from anytomd.backends.liteparse import LiteparseBackend
from anytomd.infra.errors import MalformedDocumentError
from tests.conftest import text_pdf


@pytest.fixture(scope="module")
def backend() -> LiteparseBackend:
    return LiteparseBackend(ocr=False)


async def test_liteparse_recognize_text(backend, raw) -> None:
    assert backend.recognize(raw("real_photo.png")) == "This is just\nan example."


@pytest.mark.parametrize("fixture", ["shot.png", "vector.svg", "scene.heic"], ids=["letterless", "svg", "heic"])
async def test_liteparse_recognize_miss(backend, raw, fixture) -> None:
    assert backend.recognize(raw(fixture)) == ""


async def test_liteparse_arecognize(backend, raw) -> None:
    assert await backend.arecognize(raw("real_photo.png")) == "This is just\nan example."


async def test_liteparse_arecognize_miss(backend, raw) -> None:
    assert await backend.arecognize(raw("scene.heic")) == ""


async def test_liteparse_read(backend) -> None:
    document = backend.read(text_pdf("Hello"))
    assert ("Hello" in document.markdown, document.pages, document.warnings) == (True, 1, ())


async def test_liteparse_read_path(backend, tmp_path) -> None:
    target = tmp_path / "doc.pdf"
    target.write_bytes(text_pdf("Path read"))
    assert "Path read" in backend.read(str(target)).markdown


async def test_liteparse_aread(backend) -> None:
    assert "Async read" in (await backend.aread(text_pdf("Async read"))).markdown


async def test_liteparse_read_refusal(backend) -> None:
    with pytest.raises(MalformedDocumentError, match="invalid PDF"):
        backend.read(b"%PDF-1.4 garbage")


async def test_liteparse_aread_refusal(backend) -> None:
    with pytest.raises(MalformedDocumentError):
        await backend.aread(b"%PDF-1.4 garbage")


async def test_liteparse_page_errors_become_warnings() -> None:
    page_error = type("PageError", (), {"page_num": 3, "message": "corrupt xref"})()
    result = type("Result", (), {"pages": [], "num_pages": 3, "page_errors": [page_error]})()
    warning = LiteparseBackend._common_document(result).warnings[0]
    assert (warning.code, warning.message, warning.location) == ("skipped_element", "page 3: corrupt xref", "page 3")
