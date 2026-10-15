# Exceptions

Every failure of the document itself derives from `ConvertError`. Filesystem failures stay standard `OSError` subclasses.

```python
from anytomd import ConvertError, InputTooLargeError, convert_file

try:
    convert_file("upload.docx", max_input_bytes=10 * 1024**2)
except InputTooLargeError as error:
    print(f"{error.size} > {error.limit}")
except ConvertError as error:
    print(f"cannot convert: {error}")
```

| Exception | Raised when | Example message |
|---|---|---|
| `ConvertError` | Base class; never raised directly | — |
| `UnsupportedFormatError` | No converter for the format | `unsupported format: exe` |
| `FormatNotSupportedError` | Recognized, refused on purpose | `pdf: PDF is intentionally unsupported — Gemini, ChatGPT, and Claude handle PDF natively` |
| `InputTooLargeError` | Input over `max_input_bytes`, or archive over `max_uncompressed_zip_bytes` | `input too large: 6 bytes exceeds limit of 4 bytes` |
| `MalformedDocumentError` | Structure broken beyond recovery, or any warning under `strict=True` | `malformed document: missing word/document.xml` |
| `ImageDescriptionError` | `GeminiDescriber` / `AsyncGeminiDescriber` without a key, or a direct `GeminiDescriber(...)` call failed | `image description failed: …` |
| `ZipError` | Office container unreadable | `failed to read ZIP archive: invalid Zip archive: …` |
| `XmlError` | XML unparseable | `failed to parse XML: …` |
| `SpreadsheetError` | Workbook unreadable | `failed to read spreadsheet: …` |
| `Utf8Error` | Content that must be UTF-8 is not | `invalid UTF-8 content: …` |
| `PdfError` | [`PdfConverter`](pdf.md) (`anytomd[pdf]`) could not read the PDF | `liteparse could not read the document: PDF error: invalid PDF format` |

## `InputTooLargeError`

The only exception with extra attributes:

| Attribute | Type | Meaning |
|---|---|---|
| `size` | `int` | Bytes found |
| `limit` | `int` | Bytes allowed |

## Outside the tree

| Exception | When |
|---|---|
| `FileNotFoundError`, `PermissionError`, `IsADirectoryError`, … | `convert_file` cannot read `path`; `errno`, `strerror` and `filename` are set |
| `TypeError` | A describer is not callable, or an argument has the wrong type |
| `RuntimeError` | The engine panicked — a bug upstream; reported instead of crashing the interpreter |

Describer failures *during* a conversion are not exceptions: they become `skipped_element` [warnings](results.md#conversionwarning), or a `MalformedDocumentError` under `strict=True`.
