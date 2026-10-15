"""Real-world documents fetched from public sources: conversion sanity per family."""

import pytest

import anytomd

REAL_FILES = [
    "real_paragraphs.docx",
    "real_comments.docx",
    "real_deck.pptx",
    "real_book.xlsx",
    "real_photo.png",
    "real_anim.gif",
    "real_logo.svg",
    "real_site.html",
]


@pytest.fixture(scope="module")
def real_available(resources):
    if not list(resources.walk("real_paragraphs.docx")):
        pytest.skip("real samples not downloaded — run `make samples-real`")
    return True


@pytest.mark.parametrize("fixture", REAL_FILES)
def test_real_documents_convert(real_available, path_of, fixture):
    result = anytomd.convert_file(path_of(fixture))
    assert isinstance(result.markdown, str)


def test_real_docx_keeps_paragraph_text(real_available, path_of):
    assert "paragraph" in anytomd.convert_file(path_of("real_paragraphs.docx")).markdown.lower()


def test_real_xlsx_renders_grid(real_available, path_of):
    assert "|" in anytomd.convert_file(path_of("real_book.xlsx")).markdown


def test_real_images_render_markdown_images(real_available, path_of):
    for fixture in ("real_photo.png", "real_anim.gif", "real_logo.svg"):
        assert "![" in anytomd.convert_file(path_of(fixture)).markdown


def test_real_html_keeps_body_text(real_available, path_of):
    assert "domain" in anytomd.convert_file(path_of("real_site.html")).markdown.lower()


def test_real_comments_docx_extracts_or_warns(real_available, path_of):
    result = anytomd.convert_file(path_of("real_comments.docx"), extract_comments=True)
    assert "omments" in result.markdown or result.warnings == []


def test_real_pdf_is_refused_with_reason(real_available, path_of):
    with pytest.raises(anytomd.FormatNotSupportedError, match="PDF"):
        anytomd.convert_file(path_of("real_dummy.pdf"))


def test_real_epub_is_unsupported(real_available, path_of):
    with pytest.raises(anytomd.ConvertError):
        anytomd.convert_file(path_of("real_chapter.epub"))


async def test_real_documents_async_match_sync(real_available, raw):
    data = raw("real_paragraphs.docx")
    sync = anytomd.convert_bytes(data, "docx")
    async_result = await anytomd.convert_bytes_async(data, "docx")
    assert async_result.markdown == sync.markdown
