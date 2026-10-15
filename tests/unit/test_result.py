"""ConversionResult and ConversionWarning: shape, typing and repr."""

import pytest

import anytomd


@pytest.fixture(scope="module")
def docx_result(raw) -> anytomd.ConversionResult:
    return anytomd.convert_bytes(raw("report.docx"), "docx", extract_images=True, extract_comments=True)


def test_result_markdown_is_str(docx_result):
    assert isinstance(docx_result.markdown, str)


def test_result_plain_text_has_no_markers(docx_result):
    assert "**" not in docx_result.plain_text
    assert "Quarterly Report" in docx_result.plain_text


def test_result_title_is_first_heading(docx_result):
    assert docx_result.title == "Quarterly Report"


def test_result_title_is_none_without_heading(raw):
    assert anytomd.convert_bytes(raw("notes.txt"), "txt").title is None


def test_result_images_are_named_bytes(docx_result):
    name, data = docx_result.images[0]
    assert name == "chart.png"
    assert data[:8] == b"\x89PNG\r\n\x1a\n"


def test_result_images_empty_without_extraction(raw):
    assert anytomd.convert_bytes(raw("report.docx"), "docx").images == []


def test_result_warnings_are_typed_objects(docx_result):
    assert docx_result.warnings == []
    latin = anytomd.convert_bytes(b"Caf\xe9 con leche", "txt")
    warning = latin.warnings[0]
    assert warning.code == "unsupported_feature"
    assert "windows-1252" in warning.message
    assert warning.location is None


def test_warning_repr_shows_fields(docx_result):
    latin = anytomd.convert_bytes(b"Caf\xe9 con leche", "txt")
    assert "unsupported_feature" in repr(latin.warnings[0])


def test_result_repr_shows_summary(docx_result):
    text = repr(docx_result)
    assert text.startswith("ConversionResult(markdown=")
    assert "images=1" in text


def test_result_is_frozen(docx_result):
    with pytest.raises(AttributeError):
        docx_result.markdown = "overwrite"


def test_images_are_fresh_copies(docx_result):
    first = docx_result.images[0][1]
    second = docx_result.images[0][1]
    assert first == second
