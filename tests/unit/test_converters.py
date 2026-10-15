"""PdfConverter: pages joined, page errors kept, engine refusals wrapped, real liteparse end to end."""

import liteparse
import pytest

from anytomd import ConvertError, PdfConverter, PdfDocument, PdfError
from tests.conftest import text_pdf


def _page(number, markdown):
    return type("Page", (), {"page_num": number, "markdown": markdown, "text": ""})()


def _result(pages=(), errors=()):
    return type("Result", (), {"pages": list(pages), "num_pages": len(pages), "page_errors": list(errors)})()


def _error(number, message):
    return type("PageError", (), {"page_num": number, "message": message})()


class FakeParser:
    def __init__(self, result=None, error: Exception | None = None):
        self.result = result if result is not None else _result([_page(1, "# Hello")])
        self.error = error
        self.received = None

    def parse(self, data):
        self.received = data
        return self._answer()

    async def aparse(self, data):
        self.received = data
        return self._answer()

    def _answer(self):
        match self.error:
            case Exception() as error:
                raise error
        return self.result


def test_convert_bytes_joins_pages_in_reading_order():
    parser = FakeParser(_result([_page(1, "# Title"), _page(2, "Body text")]))
    document = PdfConverter(parser=parser).convert_bytes(b"%PDF-1.4")
    assert document == PdfDocument(markdown="# Title\n\nBody text", pages=2, warnings=())


def test_convert_bytes_keeps_page_errors_as_warnings():
    parser = FakeParser(_result([_page(1, "Fine")], [_error(3, "corrupt xref")]))
    assert PdfConverter(parser=parser).convert_bytes(b"%PDF-1.4").warnings == ("page 3: corrupt xref",)


def test_convert_bytes_normalizes_bytearray_to_bytes():
    parser = FakeParser()
    PdfConverter(parser=parser).convert_bytes(bytearray(b"%PDF"))
    assert isinstance(parser.received, bytes)


def test_convert_file_hands_the_path_to_the_parser(tmp_path):
    parser = FakeParser()
    PdfConverter(parser=parser).convert_file(tmp_path / "doc.pdf")
    assert parser.received == str(tmp_path / "doc.pdf")


def test_convert_bytes_engine_refusal_raises_pdf_error_with_the_reason():
    converter = PdfConverter(parser=FakeParser(error=liteparse.ParseError("not a pdf")))
    with pytest.raises(PdfError, match="could not read the document: not a pdf"):
        converter.convert_bytes(b"junk")


def test_convert_bytes_programming_errors_are_not_disguised():
    converter = PdfConverter(parser=FakeParser(error=TypeError("bug")))
    with pytest.raises(TypeError, match="bug"):
        converter.convert_bytes(b"%PDF")


def test_pdf_error_is_a_convert_error():
    assert issubclass(PdfError, ConvertError)


def test_pdf_document_is_frozen():
    document = PdfDocument(markdown="x", pages=1)
    with pytest.raises(AttributeError):
        document.pages = 2  # ty: ignore[invalid-assignment]


async def test_convert_bytes_async_joins_pages_off_the_loop():
    parser = FakeParser(_result([_page(1, "A"), _page(2, "B")]))
    assert (await PdfConverter(parser=parser).convert_bytes_async(b"%PDF-1.4")).markdown == "A\n\nB"


async def test_convert_bytes_async_engine_refusal_raises_pdf_error():
    converter = PdfConverter(parser=FakeParser(error=liteparse.ParseError("boom")))
    with pytest.raises(PdfError, match="boom"):
        await converter.convert_bytes_async(b"junk")


async def test_convert_file_async_reads_paths_off_the_loop():
    parser = FakeParser()
    await PdfConverter(parser=parser).convert_file_async("doc.pdf")
    assert parser.received == "doc.pdf"


def test_convert_bytes_real_engine_reads_the_text_layer():
    document = PdfConverter(ocr=False).convert_bytes(text_pdf("Hello Anytomd"))
    assert document.pages == 1
    assert document.warnings == ()
    assert "Hello Anytomd" in document.markdown


def test_convert_file_real_engine_reads_a_path(tmp_path):
    target = tmp_path / "memo.pdf"
    target.write_bytes(text_pdf("From disk"))
    assert "From disk" in PdfConverter(ocr=False).convert_file(target).markdown


async def test_convert_bytes_async_real_engine_matches_sync():
    data = text_pdf("Async PDF")
    converter = PdfConverter(ocr=False)
    assert (await converter.convert_bytes_async(data)).markdown == converter.convert_bytes(data).markdown


def test_convert_bytes_real_engine_refuses_garbage():
    with pytest.raises(PdfError, match="invalid PDF"):
        PdfConverter(ocr=False).convert_bytes(b"%PDF-1.4 garbage")


def test_convert_bytes_real_engine_with_ocr_on_keeps_the_text_layer():
    assert "Scanned or not" in PdfConverter().convert_bytes(text_pdf("Scanned or not")).markdown
