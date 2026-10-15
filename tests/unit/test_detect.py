"""Format detection helpers."""

import pytest

import anytomd


def test_detect_format_prefers_zip_magic_over_extension(raw):
    ### ZIP magic wins: the concrete OOXML type is resolved afterwards by detect_zip_format.
    assert anytomd.detect_format("quarterly.docx", raw("report.docx")) == "zip"


def test_detect_format_returns_none_for_unknown_combos(raw):
    assert anytomd.detect_format("notes.unknown", raw("notes.txt")) is None


def test_detect_format_sniffs_zip_magic(raw):
    assert anytomd.detect_format("mystery.bin", raw("report.docx")) == "zip"


def test_detect_format_uses_extension_when_content_is_ambiguous(raw):
    assert anytomd.detect_format("quarterly.csv", raw("table.csv")) == "csv"


def test_detect_format_code_family(raw):
    assert anytomd.detect_format("script.py", raw("script.py")) == "code"


def test_detect_format_accepts_pathlike_objects(path_of):
    assert anytomd.detect_format(path_of("deck.pptx"), path_of("deck.pptx").read_bytes()) == "zip"


@pytest.mark.parametrize(
    ("fixture", "expected"),
    [("report.docx", "docx"), ("deck.pptx", "pptx"), ("book.xlsx", "xlsx"), ("alien.zip", None)],
)
def test_detect_zip_format(raw, fixture, expected):
    assert anytomd.detect_zip_format(raw(fixture)) == expected
