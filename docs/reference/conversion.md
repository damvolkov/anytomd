# Conversion

Four functions, one engine. All return a [`ConversionResult`](results.md) and take the same keyword-only [options](options.md).

| Function | Input | Describer keyword |
|---|---|---|
| [`convert_file`](#convert_file) | path | `image_describer` |
| [`convert_bytes`](#convert_bytes) | bytes + format | `image_describer` |
| [`convert_file_async`](#convert_file_async) | path | `async_image_describer` |
| [`convert_bytes_async`](#convert_bytes_async) | bytes + format | `async_image_describer` |

---

## `convert_file`

Convert the document at `path`. The format is [detected](../guide/formats.md#how-the-format-is-chosen) from magic bytes and extension.

```python
from anytomd import convert_file

result = convert_file("report.docx")
result.title      # 'Quarterly Report'
result.markdown   # '# Quarterly Report\n\n## Summary\n\nRevenue grew by **18 percent** ...'
```

```python
convert_file(
    path: str | os.PathLike[str],
    *,
    extract_images: bool = False,
    extract_comments: bool = False,
    strict: bool = False,
    max_input_bytes: int = 8 * 1024**3,
    max_total_image_bytes: int = 4 * 1024**3,
    max_uncompressed_zip_bytes: int = 16 * 1024**3,
    image_describer: DescribeCallable | GeminiDescriber | None = None,
) -> ConversionResult
```

| Parameter | Type | Meaning |
|---|---|---|
| `path` | `str \| os.PathLike[str]` | File to convert. Non-UTF-8 file names are accepted. |
| `**options` | | See [Options](options.md). |

| Raises | When |
|---|---|
| `FileNotFoundError`, `PermissionError`, `IsADirectoryError`, … | The file cannot be read; `errno` and `filename` are set |
| `UnsupportedFormatError` | Unknown extension, or a ZIP that is not an Office document |
| [`ConvertError`](exceptions.md) subclasses | The document cannot be converted |

The GIL is released for the whole conversion.

---

## `convert_bytes`

Convert in-memory `data`. No detection: `format` says what it is.

```python
from anytomd import convert_bytes

result = convert_bytes(b"Name,Age\nAlice,30\n", "csv")
result.markdown   # '| Name | Age |\n|---|---|\n| Alice | 30 |\n'
```

```python
convert_bytes(
    data: bytes | bytearray,
    format: str,
    *,
    extract_images: bool = False,
    extract_comments: bool = False,
    strict: bool = False,
    max_input_bytes: int = 8 * 1024**3,
    max_total_image_bytes: int = 4 * 1024**3,
    max_uncompressed_zip_bytes: int = 16 * 1024**3,
    image_describer: DescribeCallable | GeminiDescriber | None = None,
) -> ConversionResult
```

| Parameter | Type | Meaning |
|---|---|---|
| `data` | `bytes \| bytearray` | Document content. `bytes` is read in place, without a copy. |
| `format` | `str` | Extension naming the format: `"docx"`, `".CSV"`, `"py"`… Case and leading dot are ignored. |
| `**options` | | See [Options](options.md). |

| Raises | When |
|---|---|
| `UnsupportedFormatError` | `format` names nothing the engine converts |
| `FormatNotSupportedError` | `format` is `"pdf"` |
| [`ConvertError`](exceptions.md) subclasses | The document cannot be converted |

To find `format` for unknown bytes, use [`detect_format`](detection.md#detect_format).

---

## `convert_file_async`

Awaitable `convert_file`. Parsing runs on a Rust thread pool, off the event loop; image descriptions resolve concurrently.

```python
from anytomd import convert_file_async

result = await convert_file_async("deck.pptx")
result.markdown   # '## Slide 1\n\nLaunch Plan\nShip in Q3\n'
```

```python
async def convert_file_async(
    path: str | os.PathLike[str],
    *,
    extract_images: bool = False,
    extract_comments: bool = False,
    strict: bool = False,
    max_input_bytes: int = 8 * 1024**3,
    max_total_image_bytes: int = 4 * 1024**3,
    max_uncompressed_zip_bytes: int = 16 * 1024**3,
    async_image_describer: AsyncDescribeCallable | AsyncGeminiDescriber | None = None,
) -> ConversionResult
```

Parameters and errors as [`convert_file`](#convert_file), with `async_image_describer` in place of `image_describer`. Cancelling the awaiting task cancels the conversion and its describers. → [Async](../guide/async.md)

---

## `convert_bytes_async`

Awaitable `convert_bytes`.

```python
from anytomd import convert_bytes_async

result = await convert_bytes_async(payload, "docx", async_image_describer=describe)
```

```python
async def convert_bytes_async(
    data: bytes | bytearray,
    format: str,
    *,
    extract_images: bool = False,
    extract_comments: bool = False,
    strict: bool = False,
    max_input_bytes: int = 8 * 1024**3,
    max_total_image_bytes: int = 4 * 1024**3,
    max_uncompressed_zip_bytes: int = 16 * 1024**3,
    async_image_describer: AsyncDescribeCallable | AsyncGeminiDescriber | None = None,
) -> ConversionResult
```

Parameters and errors as [`convert_bytes`](#convert_bytes), with `async_image_describer` in place of `image_describer`.
