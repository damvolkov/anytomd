"""convert: every format, both input shapes, every option, the result and the error contract."""

import errno
import os
import sys

import pytest

import anytomd as ad

ENGINE_FORMATS = [
    ("notes.txt", "Plain memo body."),
    ("table.csv", "| Alice | 30 |"),
    ("page.html", "[link](https://example.com)"),
    ("data.xml", "```xml"),
    ("payload.json", "```json"),
    ("kernel.ipynb", "```python"),
    ("script.py", "```python"),
    ("settings.yaml", "port: 8080"),
    ("essay.md", "*emphasis*"),
    ("report.docx", "# Quarterly Report"),
    ("deck.pptx", "## Slide 1"),
    ("book.xlsx", "## Sales"),
]


class _PathLike:
    def __init__(self, target: str) -> None:
        self._target = target

    def __fspath__(self) -> str:
        return self._target


##### FORMATS #####


@pytest.mark.parametrize(("fixture", "marker"), ENGINE_FORMATS, ids=[f for f, _ in ENGINE_FORMATS])
async def test_convert_path_formats(path_of, fixture, marker) -> None:
    assert marker in ad.convert(path_of(fixture)).markdown


@pytest.mark.parametrize(("fixture", "marker"), ENGINE_FORMATS, ids=[f for f, _ in ENGINE_FORMATS])
async def test_convert_bytes_formats(raw, fixture, marker) -> None:
    assert marker in ad.convert(raw(fixture), format=fixture.rsplit(".", 1)[1]).markdown


@pytest.mark.parametrize(
    "fixture",
    [
        "shot.png",
        "snap.jpg",
        "anim.gif",
        "still.webp",
        "pixel.bmp",
        "raster.tiff",
        "scene.heic",
        "cover.avif",
        "vector.svg",
    ],
    ids=["png", "jpg", "gif", "webp", "bmp", "tiff", "heic", "avif", "svg"],
)
async def test_convert_image_without_ocr_is_the_engine_reference(path_of, fixture) -> None:
    assert ad.convert(path_of(fixture), ocr=False).markdown.startswith("![](image")


##### INPUTS #####


@pytest.mark.parametrize("shape", [str, os.fspath, _PathLike], ids=["str", "fspath", "pathlike"])
async def test_convert_path_shapes(path_of, shape) -> None:
    assert ad.convert(shape(str(path_of("notes.txt")))).markdown == "Plain memo body.\nSecond line.\n"


async def test_convert_bytearray(raw) -> None:
    assert "| Alice | 30 |" in ad.convert(bytearray(raw("table.csv")), format="csv").markdown


@pytest.mark.parametrize("spelling", ["csv", ".csv", "CSV", ".CSV"], ids=["plain", "dot", "upper", "dot-upper"])
async def test_convert_format_is_normalized(raw, spelling) -> None:
    assert "| Alice | 30 |" in ad.convert(raw("table.csv"), format=spelling).markdown


async def test_convert_format_overrides_the_extension(path_of, tmp_path) -> None:
    disguised = tmp_path / "table.txt"
    disguised.write_bytes(path_of("table.csv").read_bytes())
    assert "| Alice | 30 |" in ad.convert(disguised, format="csv").markdown


async def test_convert_detects_office_type_by_content(path_of, tmp_path) -> None:
    opaque = tmp_path / "export.dat"
    opaque.write_bytes(path_of("book.xlsx").read_bytes())
    assert "## Sales" in ad.convert(opaque).markdown


@pytest.mark.skipif(sys.platform != "linux", reason="only Linux file systems accept undecodable names")
async def test_convert_undecodable_path(tmp_path) -> None:
    target = tmp_path / os.fsdecode(b"memo-\xff.txt")
    target.write_bytes(b"undecodable name")
    assert ad.convert(target).markdown == "undecodable name"


##### RESULT #####


async def test_convert_document_fields(path_of) -> None:
    document = ad.convert(path_of("report.docx"), images=True)
    assert document.title == "Quarterly Report"
    assert "**" not in document.text
    assert "Quarterly Report" in document.text
    assert [name for name, _ in document.images] == ["chart.png"]
    assert document.images[0][1].startswith(b"\x89PNG")
    assert document.warnings == ()
    assert document.pages is None


async def test_convert_document_is_frozen(path_of) -> None:
    document = ad.convert(path_of("notes.txt"))
    with pytest.raises(AttributeError):
        document.markdown = "overwrite"  # ty: ignore[invalid-assignment]


async def test_convert_text_is_extracted_not_stripped(raw) -> None:
    assert ad.convert(raw("table.csv"), format="csv").text == "Name\tAge\nAlice\t30\nBob\t25\n"


async def test_convert_title_from_html_head(path_of) -> None:
    assert ad.convert(path_of("page.html")).title == "Docs Page"


async def test_convert_title_none_without_heading(path_of) -> None:
    assert ad.convert(path_of("notes.txt")).title is None


async def test_convert_empty_text() -> None:
    assert ad.convert(b"", format="txt").markdown == ""


##### OPTIONS #####


async def test_convert_images_off_by_default(path_of) -> None:
    assert ad.convert(path_of("report.docx")).images == ()


async def test_convert_comments(path_of) -> None:
    plain, commented = ad.convert(path_of("report.docx")), ad.convert(path_of("report.docx"), comments=True)
    assert "# Comments" not in plain.markdown
    assert "Verify against ledger." in commented.markdown


async def test_convert_max_image_bytes_drops_extraction(path_of) -> None:
    assert ad.convert(path_of("report.docx"), images=True, max_image_bytes=0).images == ()


##### WARNINGS #####


@pytest.mark.parametrize(
    ("payload", "code", "fragment"),
    [
        (b"Caf\xe9 con leche", "unsupported_feature", "windows-1252"),
        ("Bom text".encode("utf-16"), "unsupported_feature", "UTF-16"),
        (b"\xff\xfe\x00", "malformed_segment", "replacement"),
    ],
    ids=["windows-1252", "utf-16", "truncated"],
)
async def test_convert_warnings(payload, code, fragment) -> None:
    warning = ad.convert(payload, format="txt").warnings[0]
    assert warning.code == code
    assert fragment in warning.message
    assert warning.location is None


async def test_convert_warning_location(path_of) -> None:
    warning = ad.convert(path_of("shot.png"), images=True, ocr=False, max_image_bytes=0).warnings[0]
    assert (warning.code, warning.location) == ("resource_limit_reached", "image.png")


async def test_convert_lenient_parsers_survive_damage(raw) -> None:
    assert ad.convert(raw("riddled.docx"), format="docx").markdown == ""
    assert "Revenue grew" in ad.convert(raw("latin.docx"), format="docx").markdown


##### ERRORS #####


@pytest.mark.parametrize(
    ("fixture", "format", "match"),
    [
        ("shredded.docx", "docx", "failed to read ZIP archive: "),
        ("hollow.docx", "docx", "missing word/document.xml"),
        ("slime.xlsx", "xlsx", "failed to read spreadsheet"),
        ("manglednb.ipynb", "ipynb", "invalid JSON"),
        ("mangledjson.json", "json", "malformed document"),
    ],
    ids=["zip", "hollow", "spreadsheet", "notebook", "json"],
)
async def test_convert_broken_documents(raw, fixture, format, match) -> None:
    with pytest.raises(ad.MalformedDocumentError, match=match):
        ad.convert(raw(fixture), format=format)


async def test_convert_strict_promotes_warnings() -> None:
    with pytest.raises(ad.MalformedDocumentError, match="strict mode"):
        ad.convert(b"Caf\xe9", format="txt", strict=True)


@pytest.mark.parametrize("format", ["nope", "bin", "exe"], ids=["nope", "bin", "exe"])
async def test_convert_unknown_format(raw, format) -> None:
    with pytest.raises(ad.UnknownFormatError, match="unsupported format"):
        ad.convert(raw("notes.txt"), format=format)


async def test_convert_bytes_need_a_format() -> None:
    with pytest.raises(ad.UnknownFormatError, match="bytes need a format"):
        ad.convert(b"anything")


async def test_convert_plain_zip_is_unknown(path_of) -> None:
    with pytest.raises(ad.UnknownFormatError, match="zip"):
        ad.convert(path_of("alien.zip"))


async def test_convert_unknown_extension(path_of) -> None:
    with pytest.raises(ad.UnknownFormatError):
        ad.convert(path_of("mystery.unknown"))


@pytest.mark.parametrize(("source", "format"), [("table.csv", "csv"), ("report.docx", None)], ids=["bytes", "path"])
async def test_convert_input_too_large(raw, path_of, source, format) -> None:
    given = raw(source) if format else path_of(source)
    with pytest.raises(ad.InputTooLargeError) as caught:
        ad.convert(given, format=format, max_input_bytes=4)
    assert caught.value.size > caught.value.limit == 4


async def test_convert_zip_bomb_guard(raw) -> None:
    with pytest.raises(ad.InputTooLargeError) as caught:
        ad.convert(raw("report.docx"), format="docx", max_zip_bytes=100)
    assert caught.value.limit == 100


async def test_convert_missing_file(tmp_path) -> None:
    target = tmp_path / "absent.docx"
    with pytest.raises(FileNotFoundError) as caught:
        ad.convert(target)
    assert caught.value.errno == errno.ENOENT


@pytest.mark.skipif(sys.platform == "win32", reason="Windows reports directories as PermissionError")
async def test_convert_directory(tmp_path) -> None:
    with pytest.raises(IsADirectoryError):
        ad.convert(tmp_path)


async def test_convert_every_failure_is_a_conversion_error(raw) -> None:
    with pytest.raises(ad.ConversionError):
        ad.convert(raw("shredded.docx"), format="docx")
