"""WarningCode: each category the crate can report."""

import pytest

import anytomd


def test_unsupported_feature_from_non_utf8_text():
    result = anytomd.convert_bytes(b"Caf\xe9 con leche", "txt")
    assert result.warnings[0].code == "unsupported_feature"


def test_unsupported_feature_from_utf16_bom():
    result = anytomd.convert_bytes("Bom text".encode("utf-16"), "txt")
    assert result.warnings[0].code == "unsupported_feature"
    assert "UTF-16" in result.warnings[0].message


def test_malformed_segment_from_truncated_multibyte():
    result = anytomd.convert_bytes(b"\xff\xfe\x00", "txt")
    assert result.warnings[0].code == "malformed_segment"
    assert "replacement" in result.warnings[0].message


def test_skipped_element_from_failing_describer(single_image_docx):
    def broken(image: bytes, mime_type: str, prompt: str) -> str:
        msg = "boom"
        raise ValueError(msg)

    result = anytomd.convert_bytes(single_image_docx, "docx", image_describer=broken)
    assert [w.code for w in result.warnings] == ["skipped_element"]
    assert "image1.png" in result.warnings[0].message


def test_resource_limit_reached_carries_location(raw):
    result = anytomd.convert_bytes(raw("shot.png"), "png", extract_images=True, max_total_image_bytes=0)
    warning = result.warnings[0]
    assert warning.code == "resource_limit_reached"
    assert warning.location == "image.png"
    assert result.images == []


def test_result_objects_are_not_python_constructible():
    with pytest.raises(TypeError):
        anytomd.ConversionWarning()
    with pytest.raises(TypeError):
        anytomd.ConversionResult()
