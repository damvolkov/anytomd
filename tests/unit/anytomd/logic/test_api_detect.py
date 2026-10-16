"""detect / adetect: the concrete format a source turns out to be."""

import pytest

import anytomd as ad

CASES = [
    ("report.docx", "docx"),
    ("deck.pptx", "pptx"),
    ("book.xlsx", "xlsx"),
    ("table.csv", "csv"),
    ("script.py", "py"),
    ("notes.txt", "txt"),
    ("essay.md", "md"),
    ("snap.jpg", "jpg"),
    ("real_dummy.pdf", "pdf"),
    ("alien.zip", None),
    ("mystery.unknown", None),
]


@pytest.mark.parametrize(("fixture", "expected"), CASES, ids=[f for f, _ in CASES])
async def test_detect_path(path_of, fixture, expected) -> None:
    assert ad.detect(path_of(fixture)) == expected


@pytest.mark.parametrize(("fixture", "expected"), CASES, ids=[f for f, _ in CASES])
async def test_adetect_path(path_of, fixture, expected) -> None:
    assert await ad.adetect(path_of(fixture)) == expected


async def test_detect_bytes_by_content(raw) -> None:
    assert ad.detect(raw("report.docx")) == "docx"


async def test_detect_bytes_with_a_name(raw) -> None:
    assert ad.detect(raw("table.csv"), name="table.csv") == "csv"


async def test_detect_bytes_json_sniffed() -> None:
    assert ad.detect(b'{"a": 1}') == "json"


async def test_detect_feeds_convert(raw) -> None:
    data = raw("deck.pptx")
    assert "## Slide 1" in ad.convert(data, format=ad.detect(data)).markdown
