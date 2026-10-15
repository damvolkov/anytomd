"""ConversionOptions: every knob reaches the Rust engine."""

import pytest

import anytomd


def test_extract_images_off_by_default(raw):
    assert anytomd.convert_bytes(raw("report.docx"), "docx").images == []


def test_extract_images_on_returns_archive_payload(raw):
    result = anytomd.convert_bytes(raw("report.docx"), "docx", extract_images=True)
    assert [name for name, _ in result.images] == ["chart.png"]


def test_extract_comments_off_by_default(raw):
    assert "# Comments" not in anytomd.convert_bytes(raw("report.docx"), "docx").markdown


def test_extract_comments_appends_section(raw):
    result = anytomd.convert_bytes(raw("report.docx"), "docx", extract_comments=True)
    assert "# Comments" in result.markdown
    assert "Verify against ledger." in result.markdown
    assert "Reviewer" in result.markdown


def test_strict_false_keeps_recoverable_problems_as_warnings():
    result = anytomd.convert_bytes(b"Caf\xe9", "txt")
    assert len(result.warnings) == 1


def test_strict_true_promotes_warnings_to_errors():
    with pytest.raises(anytomd.MalformedDocumentError, match="strict mode"):
        anytomd.convert_bytes(b"Caf\xe9", "txt", strict=True)


def test_strict_applies_to_file_conversion(path_of):
    with pytest.raises(anytomd.MalformedDocumentError):
        anytomd.convert_file(path_of("latin.txt"), strict=True)


def test_max_total_image_bytes_drops_extraction(raw):
    result = anytomd.convert_bytes(raw("report.docx"), "docx", extract_images=True, max_total_image_bytes=0)
    assert result.images == []


def test_max_uncompressed_zip_bytes_guard_trips_as_input_too_large(raw):
    with pytest.raises(anytomd.InputTooLargeError) as caught:
        anytomd.convert_bytes(raw("report.docx"), "docx", max_uncompressed_zip_bytes=100)
    assert caught.value.limit == 100


def test_all_options_together_produce_valid_result(raw):
    result = anytomd.convert_bytes(
        raw("report.docx"),
        "docx",
        extract_images=True,
        extract_comments=True,
        strict=False,
        max_input_bytes=2**20,
        max_total_image_bytes=2**20,
        max_uncompressed_zip_bytes=2**20,
    )
    assert "# Quarterly Report" in result.markdown
    assert result.images
