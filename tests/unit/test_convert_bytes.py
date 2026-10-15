"""convert_bytes: every supported format, every error contract."""

import pytest

import anytomd

TEXT_CASES = [
    ("notes.txt", "txt", "Plain memo body."),
    ("table.csv", "csv", "| Alice | 30 |"),
    ("page.html", "html", "[link](https://example.com)"),
    ("data.xml", "xml", "```xml"),
    ("payload.json", "json", "```json"),
    ("kernel.ipynb", "ipynb", "```python"),
    ("script.py", "py", "```python"),
    ("settings.yaml", "yaml", "port: 8080"),
    ("essay.md", "md", "*emphasis*"),
]

MEDIA_CASES = [
    ("shot.png", "png", "](image.png)"),
    ("snap.jpg", "jpg", "](image.jpg)"),
    ("anim.gif", "gif", "](image.gif)"),
    ("still.webp", "webp", "](image.webp)"),
    ("pixel.bmp", "bmp", "](image)"),
    ("raster.tiff", "tiff", "](image)"),
    ("scene.heic", "heic", "](image)"),
    ("cover.avif", "avif", "](image)"),
    ("vector.svg", "svg", "](image)"),
]

OFFICE_CASES = [
    ("report.docx", "docx", "# Quarterly Report"),
    ("deck.pptx", "pptx", "## Slide 1"),
    ("book.xlsx", "xlsx", "## Sales"),
]


@pytest.mark.parametrize(("fixture", "format", "marker"), TEXT_CASES + MEDIA_CASES + OFFICE_CASES)
def test_convert_bytes_formats(raw, fixture, format, marker):
    result = anytomd.convert_bytes(raw(fixture), format)
    assert marker in result.markdown


def test_convert_bytes_plain_text_is_unformatted(raw):
    result = anytomd.convert_bytes(raw("table.csv"), "csv")
    assert result.plain_text == "Name\tAge\nAlice\t30\nBob\t25\n"


def test_convert_bytes_title_from_html_head(raw):
    result = anytomd.convert_bytes(raw("page.html"), "html")
    assert result.title == "Docs Page"


def test_convert_bytes_format_is_normalized(raw):
    dotted = anytomd.convert_bytes(raw("table.csv"), ".CSV")
    assert "| Alice | 30 |" in dotted.markdown


def test_convert_bytes_empty_text_yields_empty_markdown():
    result = anytomd.convert_bytes(b"", "txt")
    assert result.markdown == ""


@pytest.mark.parametrize("format", ["nope", "bin", "", "exe"])
def test_convert_bytes_unsupported_format(raw, format):
    with pytest.raises(anytomd.UnsupportedFormatError, match="unsupported format"):
        anytomd.convert_bytes(raw("notes.txt"), format)


def test_convert_bytes_pdf_is_refused():
    with pytest.raises(anytomd.FormatNotSupportedError, match="PDF is intentionally unsupported"):
        anytomd.convert_bytes(b"%PDF-1.4 anything", "pdf")


def test_convert_bytes_rejects_input_over_limit(raw):
    with pytest.raises(anytomd.InputTooLargeError) as caught:
        anytomd.convert_bytes(raw("table.csv"), "csv", max_input_bytes=4)
    assert caught.value.size > 4
    assert caught.value.limit == 4
