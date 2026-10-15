# Errors and warnings

Conversion is **best-effort**. A broken table, an undecodable byte or a failed image description does not sink the document: the element is skipped or repaired, the rest converts, and a **warning** says what happened. Only problems that make the whole document unusable raise.

```python
from anytomd import ConvertError, convert_file

try:
    result = convert_file("upload.docx")
except FileNotFoundError:
    ...                                # filesystem: plain OSError subclasses
except ConvertError as error:
    ...                                # the document itself: see the tree below
else:
    for warning in result.warnings:
        print(warning.code, warning.message, warning.location)
```

## Warnings

Each `ConversionWarning` carries a `code`, a `message` and, when known, a `location`.

| `code` | Meaning | Example |
|---|---|---|
| `skipped_element` | An element was left out or left as-is | An image describer failed |
| `unsupported_feature` | Something was handled by a fallback | Text decoded as Windows-1252 or UTF-16 |
| `resource_limit_reached` | A limit dropped part of the output | An image over `max_total_image_bytes` |
| `malformed_segment` | Damaged data was repaired | Invalid bytes replaced with U+FFFD |

```python
from anytomd import convert_bytes

result = convert_bytes(b"Caf\xe9 con leche", "txt")
result.markdown      # 'Café con leche'
result.warnings      # [ConversionWarning(code="unsupported_feature", message="decoded from windows-1252 encoding (fallback)", location=None)]
```

## Strict mode

`strict=True` turns any warning into a `MalformedDocumentError`. Use it when partial output is worse than none:

```python
convert_bytes(b"Caf\xe9", "txt", strict=True)
# MalformedDocumentError: malformed document: strict mode: encountered warning [UnsupportedFeature] decoded from windows-1252 encoding (fallback)
```

## Exceptions

```text
Exception
├── ConvertError
│   ├── UnsupportedFormatError     no converter for this format
│   ├── FormatNotSupportedError    recognized, refused on purpose (PDF)
│   ├── InputTooLargeError         .size, .limit
│   ├── MalformedDocumentError     structure broken, or a warning under strict=True
│   ├── ImageDescriptionError      a Gemini describer could not be built, or a direct call failed
│   ├── ZipError                   Office container unreadable
│   ├── XmlError                   XML unparseable
│   ├── SpreadsheetError           workbook unreadable
│   └── Utf8Error                  invalid UTF-8
├── OSError                        FileNotFoundError, PermissionError, IsADirectoryError… with errno and filename
├── TypeError                      a describer that is not callable
└── RuntimeError                   an internal engine panic, reported instead of crashing the interpreter
```

Catch `ConvertError` for "this document could not be converted". Each class, with the exact messages → [Exceptions](../reference/exceptions.md).

## Limits protect you from hostile input

Three ceilings guard memory: the input size, the decompressed size of Office archives (ZIP bombs), and the total size of extracted images. Lower them for untrusted uploads:

```python
from anytomd import InputTooLargeError, convert_bytes

try:
    result = convert_bytes(
        upload,
        "docx",
        max_input_bytes=20 * 1024**2,             # 20 MiB file
        max_uncompressed_zip_bytes=200 * 1024**2, # 200 MiB unpacked
    )
except InputTooLargeError as error:
    print(error.size, error.limit)
```

→ [Options](../reference/options.md)
