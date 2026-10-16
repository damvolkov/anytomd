"""aconvert: the same contract as convert, off the event loop, images resolved concurrently."""

import asyncio

import pytest

import anytomd as ad
from tests.conftest import text_pdf


async def test_aconvert_matches_convert(path_of) -> None:
    sync = ad.convert(path_of("report.docx"), comments=True)
    assert await ad.aconvert(path_of("report.docx"), comments=True) == sync


async def test_aconvert_bytes(raw) -> None:
    assert "| Alice | 30 |" in (await ad.aconvert(raw("table.csv"), format="csv")).markdown


async def test_aconvert_pdf() -> None:
    assert "Async PDF" in (await ad.aconvert(text_pdf("Async PDF"), format="pdf", ocr=False)).markdown


async def test_aconvert_pdf_without_the_extra(missing_extra) -> None:
    missing_extra("liteparse")
    with pytest.raises(ad.MissingExtraError, match="pdf"):
        await ad.aconvert(text_pdf("x"), format="pdf")


async def test_aconvert_image_ocr(path_of) -> None:
    assert (await ad.aconvert(path_of("real_photo.png"))).markdown == "This is just\nan example."


async def test_aconvert_image_falls_back_to_vision(path_of, fake_vision) -> None:
    assert (await ad.aconvert(path_of("shot.png"))).markdown == "Image description: A red square"
    assert fake_vision.closed == ["async"]


async def test_aconvert_image_vision_failure_is_a_warning(path_of, fake_vision) -> None:
    fake_vision.error = ad.DescriptionError("vision model 'v' failed: 429")
    document = await ad.aconvert(path_of("shot.png"))
    assert (document.markdown, [w.code for w in document.warnings]) == ("", ["skipped_element"])


async def test_aconvert_image_without_any_capability(path_of, missing_extra) -> None:
    missing_extra("liteparse")
    assert (await ad.aconvert(path_of("shot.png"))).markdown.startswith("![](image")


async def test_aconvert_embedded_images_described_concurrently(gallery_docx, fake_vision) -> None:
    document = await ad.aconvert(gallery_docx, format="docx")
    assert document.markdown.count("Image description: A red square") == 3
    assert fake_vision.peak > 1


async def test_aconvert_concurrency_is_bounded(gallery_docx, fake_vision) -> None:
    fake_vision.concurrency = 1
    await ad.aconvert(gallery_docx, format="docx")
    assert fake_vision.peak == 1


async def test_aconvert_embedded_keeps_the_author_alt(path_of) -> None:
    document = await ad.aconvert(path_of("report.docx"))
    assert "![Sales chart](chart.png)" in document.markdown
    assert document.warnings == ()


async def test_aconvert_leaves_the_loop_free(gallery_docx, fake_vision) -> None:
    ticks = 0
    stop = asyncio.Event()

    async def heartbeat() -> None:
        nonlocal ticks
        while not stop.is_set():
            ticks += 1
            await asyncio.sleep(0.001)

    async with asyncio.TaskGroup() as group:
        group.create_task(heartbeat())
        await ad.aconvert(gallery_docx, format="docx")
        stop.set()
    assert ticks > 1


async def test_aconvert_cancellation_reaches_the_vision_calls(single_image_docx, fake_vision) -> None:
    started, cancelled = asyncio.Event(), asyncio.Event()

    async def slow(image: bytes, mime_type: str) -> str:
        started.set()
        try:
            await asyncio.sleep(30)
        except asyncio.CancelledError:
            cancelled.set()
            raise
        return "never"

    fake_vision.adescribe = slow
    task = asyncio.create_task(ad.aconvert(single_image_docx, format="docx"))
    await asyncio.wait_for(started.wait(), 5)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    await asyncio.wait_for(cancelled.wait(), 5)


async def test_aconvert_gather_of_documents(gallery_docx) -> None:
    documents = await asyncio.gather(*(ad.aconvert(gallery_docx, format="docx", ocr=False) for _ in range(8)))
    assert all(document.title == "Image Gallery" for document in documents)


async def test_aconvert_errors_match_convert(raw) -> None:
    with pytest.raises(ad.InputTooLargeError):
        await ad.aconvert(raw("table.csv"), format="csv", max_input_bytes=4)
    with pytest.raises(ad.UnknownFormatError):
        await ad.aconvert(b"x", format="exe")


async def test_aconvert_missing_file(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        await ad.aconvert(tmp_path / "absent.txt")
