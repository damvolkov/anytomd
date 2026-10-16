"""Stress: volume, parallel threads, native coroutines and fuzzed payloads."""

import asyncio
import io
import threading
import time
import zipfile

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

import anytomd as ad

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


async def test_stress_threads_identical_results(tmp_path) -> None:
    target = tmp_path / "stress.csv"
    target.write_bytes(big_csv())
    baseline = ad.convert(target)
    results: list[ad.Document] = []
    run_in_threads(8, lambda: ad.convert(target), results)
    assert len(results) == 8
    assert all(result.markdown == baseline.markdown for result in results)


async def test_stress_gil_released() -> None:
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
        ad.convert(payload, format="csv")
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


async def test_stress_huge_html() -> None:
    payload = "<html><body>" + "".join(f"<p>paragraph {index}</p>" for index in range(200_000)) + "</body></html>"
    start = time.perf_counter()
    result = ad.convert(payload.encode(), format="html")
    assert "paragraph 199999" in result.markdown
    assert time.perf_counter() - start < 20


async def test_stress_zip_bomb() -> None:
    payload = huge_docx()
    assert len(payload) < 1024 * 1024
    with pytest.raises(ad.InputTooLargeError) as caught:
        ad.convert(payload, format="docx", max_zip_bytes=1024 * 1024)
    assert caught.value.size > caught.value.limit


async def test_stress_many_aconversions_share_the_loop(gallery_docx, fake_vision) -> None:
    start = time.perf_counter()
    documents = await asyncio.gather(*(ad.aconvert(gallery_docx, format="docx") for _ in range(16)))
    elapsed = time.perf_counter() - start
    assert all(document.markdown.count("Image description:") == 3 for document in documents)
    assert elapsed < 10


FUZZ_FORMATS = ["txt", "csv", "html", "json", "xml", "md"]


@pytest.mark.parametrize("format", FUZZ_FORMATS, ids=FUZZ_FORMATS)
@settings(max_examples=120, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(payload=st.binary(max_size=4096))
def test_stress_fuzz_never_crashes(payload, format) -> None:
    ### hypothesis drives its own loop of examples, so this one test stays synchronous.
    try:
        document = ad.convert(payload, format=format)
    except ad.ConversionError:
        return
    assert isinstance(document.markdown, str)
    assert isinstance(document.text, str)
