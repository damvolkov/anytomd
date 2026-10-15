"""Stress: volume, parallel threads, native coroutines and fuzzed payloads."""

import asyncio
import io
import threading
import time
import zipfile

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

import anytomd

pytestmark = pytest.mark.stress


def big_csv(rows: int = 200_000) -> bytes:
    return ("Name,Value\n" + "\n".join(f"user{index},{index}" for index in range(rows))).encode()


def huge_docx(uncompressed_bytes: int = 20 * 1024 * 1024) -> bytes:
    """DOCX whose document.xml decompresses to `uncompressed_bytes` from a tiny archive."""
    body = "x" * uncompressed_bytes
    document = f'<?xml version="1.0"?><w:document><w:body><w:t>{body}</w:t></w:body></w:document>'
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml", '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>'
        )
        archive.writestr("_rels/.rels", "<Relationships/>")
        archive.writestr("word/document.xml", document)
    return buffer.getvalue()


def test_threads_convert_concurrently_with_identical_results(tmp_path):
    target = tmp_path / "stress.csv"
    target.write_bytes(big_csv())
    baseline = anytomd.convert_file(target)
    results: list[anytomd.ConversionResult] = []
    run_in_threads(8, lambda: anytomd.convert_file(target), results)
    assert len(results) == 8
    assert all(result.markdown == baseline.markdown for result in results)


def test_conversion_releases_the_gil_for_other_threads():
    ### A pure-Python heartbeat only ticks during a long native call if that call has released the GIL.
    payload = big_csv(1_000_000)
    stop = threading.Event()
    ticks: list[int] = []

    def heartbeat():
        while not stop.is_set():
            ticks.append(1)
            time.sleep(0.001)

    thread = threading.Thread(target=heartbeat)
    thread.start()
    try:
        before = len(ticks)
        anytomd.convert_bytes(payload, "csv")
        during = len(ticks) - before
    finally:
        stop.set()
        thread.join()
    assert during > 10


def run_in_threads(count: int, work, sink: list) -> None:
    barrier = threading.Barrier(count)

    def runner():
        barrier.wait()
        sink.append(work())

    threads = [threading.Thread(target=runner) for _ in range(count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()


def test_convert_huge_html():
    payload = "<html><body>" + "".join(f"<p>paragraph {index}</p>" for index in range(200_000)) + "</body></html>"
    start = time.perf_counter()
    result = anytomd.convert_bytes(payload.encode(), "html")
    assert "paragraph 199999" in result.markdown
    assert time.perf_counter() - start < 20


def test_zip_bomb_guard_rejects_uncompressed_volume():
    payload = huge_docx()
    assert len(payload) < 1024 * 1024
    with pytest.raises(anytomd.InputTooLargeError) as caught:
        anytomd.convert_bytes(payload, "docx", max_uncompressed_zip_bytes=1024 * 1024)
    assert caught.value.size > caught.value.limit


def test_many_async_conversions_share_the_loop(gallery_docx):
    async def describer(image, mime_type, prompt):
        await asyncio.sleep(0.05)
        return "alt"

    async def run_all():
        return await asyncio.gather(
            *(
                anytomd.convert_bytes_async(gallery_docx, "docx", extract_images=True, async_image_describer=describer)
                for _ in range(16)
            )
        )

    start = time.perf_counter()
    results = asyncio.run(run_all())
    elapsed = time.perf_counter() - start
    assert all(r.markdown.count("alt") == 3 for r in results)
    assert elapsed < 3


@pytest.mark.parametrize("format", ["txt", "csv", "html", "json", "xml", "md"])
@settings(max_examples=120, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(payload=st.binary(max_size=4096))
def test_fuzz_never_crashes_the_engine(payload, format):
    try:
        result = anytomd.convert_bytes(payload, format)
    except (anytomd.ConvertError, OSError):
        return
    assert isinstance(result.markdown, str)
    assert isinstance(result.plain_text, str)
