"""convert_file: path shapes, autodetection, I/O failures."""

import os

import pytest

import anytomd


class _PathLike:
    """Minimal object implementing only the fspath protocol."""

    def __init__(self, target: str) -> None:
        self._target = target

    def __fspath__(self) -> str:
        return self._target


def test_convert_file_by_str_path(path_of):
    result = anytomd.convert_file(str(path_of("report.docx")))
    assert "# Quarterly Report" in result.markdown


def test_convert_file_by_pathlib_path(path_of):
    result = anytomd.convert_file(path_of("table.csv"))
    assert "| Alice | 30 |" in result.markdown


def test_convert_file_by_pathlike_object(path_of):
    result = anytomd.convert_file(_PathLike(os.fspath(path_of("notes.txt"))))
    assert result.markdown == "Plain memo body.\nSecond line.\n"


def test_convert_file_autodetects_zip_format_by_content(path_of, tmp_path):
    opaque = tmp_path / "opaque.dat"
    opaque.write_bytes(path_of("book.xlsx").read_bytes())
    result = anytomd.convert_file(opaque)
    assert "## Sales" in result.markdown


def test_convert_file_rejects_missing_path(tmp_path):
    with pytest.raises(OSError, match="No such file"):
        anytomd.convert_file(tmp_path / "absent.docx")


def test_convert_file_rejects_directory(tmp_path):
    with pytest.raises(OSError, match="Is a directory"):
        anytomd.convert_file(tmp_path)


def test_convert_file_rejects_oversized_input(path_of):
    with pytest.raises(anytomd.InputTooLargeError) as caught:
        anytomd.convert_file(path_of("report.docx"), max_input_bytes=100)
    assert caught.value.size > caught.value.limit == 100


def test_convert_file_rejects_plain_zip(path_of):
    with pytest.raises(anytomd.UnsupportedFormatError, match="zip"):
        anytomd.convert_file(path_of("alien.zip"))


def test_convert_file_rejects_unknown_extension(path_of):
    with pytest.raises(anytomd.UnsupportedFormatError, match="unknown"):
        anytomd.convert_file(path_of("mystery.unknown"))
