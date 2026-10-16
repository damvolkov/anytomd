"""InputSource: path or bytes, the format normalized or sniffed, bytes loaded on demand."""

import pytest

from anytomd.infra.errors import UnknownFormatError
from anytomd.logic.sources import InputSource


async def test_sources_bytes_need_a_format() -> None:
    with pytest.raises(UnknownFormatError, match="bytes need a format"):
        InputSource.build(b"x", None)


async def test_sources_format_normalized() -> None:
    assert InputSource.build(bytearray(b"x"), ".CSV").format == "csv"


async def test_sources_path_sniffed_without_loading(path_of) -> None:
    source = InputSource.build(path_of("report.docx"), None)
    assert (source.format, source.data) == ("docx", None)


async def test_sources_path_with_a_format_is_loaded(path_of) -> None:
    source = InputSource.build(path_of("table.csv"), "csv")
    assert source.data == path_of("table.csv").read_bytes()


async def test_sources_load_and_size(path_of) -> None:
    source = InputSource.build(path_of("notes.txt"), None)
    assert source.load() == path_of("notes.txt").read_bytes()
    assert source.size() == path_of("notes.txt").stat().st_size
    assert await source.aload() == source.load()


async def test_sources_abuild(path_of) -> None:
    assert (await InputSource.abuild(path_of("deck.pptx"), "pptx")).format == "pptx"
