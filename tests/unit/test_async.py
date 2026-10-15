"""Async surface: coroutines, native concurrency, the Python awaitable bridge."""

import asyncio
import time

import pytest

import anytomd


async def test_convert_bytes_async_basic():
    result = await anytomd.convert_bytes_async(b"Name,Age\nAlice,30\n", "csv")
    assert "| Alice | 30 |" in result.markdown


async def test_convert_file_async_basic(path_of):
    result = await anytomd.convert_file_async(path_of("report.docx"))
    assert result.title == "Quarterly Report"


async def test_convert_bytes_async_honours_limits(raw):
    with pytest.raises(anytomd.InputTooLargeError):
        await anytomd.convert_bytes_async(raw("table.csv"), "csv", max_input_bytes=4)


async def test_convert_bytes_async_rejects_pdf():
    with pytest.raises(anytomd.FormatNotSupportedError):
        await anytomd.convert_bytes_async(b"anything", "pdf")


async def test_convert_file_async_missing_path(tmp_path):
    with pytest.raises(OSError, match="No such file"):
        await anytomd.convert_file_async(tmp_path / "absent.txt")


async def test_async_describer_replaces_placeholders(gallery_docx):
    async def describer(image: bytes, mime_type: str, prompt: str) -> str:
        await asyncio.sleep(0)
        return "async alt"

    result = await anytomd.convert_bytes_async(
        gallery_docx, "docx", extract_images=True, async_image_describer=describer
    )
    assert result.markdown.count("async alt") == 3


async def test_async_describer_runs_images_concurrently(gallery_docx):
    async def describer(image, mime_type, prompt):
        await asyncio.sleep(0.25)
        return "alt"

    start = time.monotonic()
    result = await anytomd.convert_bytes_async(
        gallery_docx, "docx", extract_images=True, async_image_describer=describer
    )
    elapsed = time.monotonic() - start
    assert result.markdown.count("alt") == 3
    assert elapsed < 0.6


async def test_async_conversion_leaves_the_loop_free(gallery_docx):
    async def describer(image, mime_type, prompt):
        await asyncio.sleep(0.2)
        return "alt"

    ticks = 0

    async def heartbeat(stop):
        nonlocal ticks
        while not stop.is_set():
            ticks += 1
            await asyncio.sleep(0.01)

    stop = asyncio.Event()
    watcher = asyncio.create_task(heartbeat(stop))
    try:
        result = await anytomd.convert_bytes_async(
            gallery_docx, "docx", extract_images=True, async_image_describer=describer
        )
    finally:
        stop.set()
        await watcher
    assert "alt" in result.markdown
    assert ticks > 1


async def test_async_describer_exception_degrades_to_warning(single_image_docx):
    async def describer(image, mime_type, prompt):
        msg = "nope"
        raise RuntimeError(msg)

    result = await anytomd.convert_bytes_async(
        single_image_docx, "docx", extract_images=True, async_image_describer=describer
    )
    assert result.warnings[0].code == "skipped_element"


async def test_async_describer_non_string_degrades_to_warning(single_image_docx):
    async def describer(image, mime_type, prompt):
        return 42

    result = await anytomd.convert_bytes_async(
        single_image_docx, "docx", extract_images=True, async_image_describer=describer
    )
    assert result.warnings[0].code == "skipped_element"


async def test_async_strict_promotes_describer_failure(single_image_docx):
    async def describer(image, mime_type, prompt):
        msg = "nope"
        raise RuntimeError(msg)

    with pytest.raises(anytomd.MalformedDocumentError):
        await anytomd.convert_bytes_async(
            single_image_docx, "docx", extract_images=True, async_image_describer=describer, strict=True
        )


async def test_async_file_describer_end_to_end(gallery_docx, tmp_path):
    target = tmp_path / "gallery.docx"
    target.write_bytes(gallery_docx)

    async def describer(image, mime_type, prompt):
        await asyncio.sleep(0.01)
        return "file alt"

    result = await anytomd.convert_file_async(target, extract_images=True, async_image_describer=describer)
    assert result.markdown.count("file alt") == 3


async def test_async_gather_of_independent_conversions(gallery_docx):
    results = await asyncio.gather(*(anytomd.convert_bytes_async(gallery_docx, "docx") for _ in range(8)))
    assert all(r.title == "Image Gallery" for r in results)
