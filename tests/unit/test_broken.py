"""Every failure mode the crate reports, through the typed exception tree."""

import pytest

import anytomd


def test_shredded_docx_raises_zip_error(raw):
    with pytest.raises(anytomd.ZipError) as caught:
        anytomd.convert_bytes(raw("shredded.docx"), "docx")
    message = str(caught.value)
    assert message.count("failed to read ZIP archive") == 1
    assert message != "failed to read ZIP archive"


def test_hollow_docx_raises_malformed_document(raw):
    with pytest.raises(anytomd.MalformedDocumentError, match=r"missing word/document.xml"):
        anytomd.convert_bytes(raw("hollow.docx"), "docx")


def test_slime_xlsx_raises_spreadsheet_error(raw):
    with pytest.raises(anytomd.SpreadsheetError):
        anytomd.convert_bytes(raw("slime.xlsx"), "xlsx")


def test_mangled_ipynb_raises_malformed_document(raw):
    with pytest.raises(anytomd.MalformedDocumentError, match="invalid JSON"):
        anytomd.convert_bytes(raw("manglednb.ipynb"), "ipynb")


def test_mangled_json_raises_malformed_document(raw):
    with pytest.raises(anytomd.MalformedDocumentError):
        anytomd.convert_bytes(raw("mangledjson.json"), "json")


def test_empty_bytes_reaches_the_unsupported_path(raw):
    with pytest.raises(anytomd.UnsupportedFormatError):
        anytomd.convert_bytes(raw("empty.bin"), "bin")


def test_lenient_parsers_survive_riddled_documents(raw):
    ### quick-xml streams leniently: truncation or invalid bytes degrade, they do not abort.
    result = anytomd.convert_bytes(raw("riddled.docx"), "docx")
    assert result.markdown == ""
    latin = anytomd.convert_bytes(raw("latin.docx"), "docx")
    assert "Revenue grew" in latin.markdown


@pytest.mark.parametrize(
    "name",
    [
        "ConvertError",
        "UnsupportedFormatError",
        "FormatNotSupportedError",
        "InputTooLargeError",
        "MalformedDocumentError",
        "ImageDescriptionError",
        "ZipError",
        "XmlError",
        "SpreadsheetError",
        "Utf8Error",
    ],
)
def test_exception_tree_is_complete_and_catchable(name):
    cls = getattr(anytomd, name)
    assert issubclass(cls, anytomd.ConvertError)
    assert issubclass(anytomd.ConvertError, Exception)


def test_unreachable_parse_errors_stay_catchable(raw):
    ### XmlError and Utf8Error come from tight parser paths the lenient converters rarely hit;
    ### they stay exported so broad `except ConvertError` handlers cover them by construction.
    for name in ("XmlError", "Utf8Error"):
        assert isinstance(getattr(anytomd, name), type)
