# Errors

Conversion is best-effort. A broken table or an undecodable byte doesn't stop the document: the problem lands in `document.warnings` and the rest converts. Only a document that can't be converted at all raises.

```python
import anytomd as ad

try:
    document = ad.convert(upload, format="docx", max_input_bytes=20 * 1024**2)
except ad.MissingExtraError as error:
    print(error)                    # PDF needs the 'pdf' extra: pip install 'anytomd[pdf]'
except ad.InputTooLargeError as error:
    print(error.size, error.limit)
except ad.ConversionError as error:
    print("cannot convert:", error)
else:
    for warning in document.warnings:
        print(warning.code, warning.message)
```

## The tree

```text
ConversionError
├── UnknownFormatError       nothing converts this format, or describe got a non-image
├── MissingExtraError        the format needs an extra: PDF → [pdf], describe → [vlm]
├── InputTooLargeError       over max_input_bytes or max_zip_bytes      .size  .limit
├── MalformedDocumentError   the document is broken, or a warning under strict=True
└── DescriptionError         describe: no vision model configured, or the provider failed
```

| Error | Example message |
|---|---|
| `UnknownFormatError` | `unsupported format: exe` · `bytes need a format, e.g. format='docx'` |
| `MissingExtraError` | `PDF needs the 'pdf' extra: pip install 'anytomd[pdf]'` |
| `InputTooLargeError` | `input too large: 6 bytes exceeds limit of 4 bytes` |
| `MalformedDocumentError` | `failed to read ZIP archive: invalid Zip archive: Could not find EOCD` |
| `DescriptionError` | `no vision model: set ANYTOMD_VISION_MODEL or pass vision=VisionSpec(model=...)` |

A path that can't be read raises the usual `FileNotFoundError`, `PermissionError` or `IsADirectoryError`.

## Strict mode

```python
ad.convert(b"Caf\xe9", format="txt")                # converts, one warning
ad.convert(b"Caf\xe9", format="txt", strict=True)   # MalformedDocumentError
```

## Vision inside `convert`

A failing vision call never fails a conversion: the image keeps its OCR text or its original alt, and a `skipped_element` warning says why. Only `describe`, which you call for the description itself, raises `DescriptionError`.
