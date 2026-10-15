# Options

Keyword-only, identical on the four [conversion functions](conversion.md). Defaults are anytomd-rs's own.

| Option | Type | Default | Effect |
|---|---|---|---|
| [`extract_images`](#extract_images) | `bool` | `False` | Return embedded images in `result.images` |
| [`extract_comments`](#extract_comments) | `bool` | `False` | Append DOCX/PPTX comments as a `# Comments` section |
| [`strict`](#strict) | `bool` | `False` | Raise on the first warning instead of collecting it |
| [`max_input_bytes`](#max_input_bytes) | `int` | 8 GiB | Largest accepted input |
| [`max_total_image_bytes`](#max_total_image_bytes) | `int` | 4 GiB | Budget for image bytes held in memory |
| [`max_uncompressed_zip_bytes`](#max_uncompressed_zip_bytes) | `int` | 16 GiB | ZIP-bomb guard for Office documents |
| [`image_describer`](#image_describer) | callable | `None` | Sync alt-text generator |
| [`async_image_describer`](#async_image_describer) | async callable | `None` | Async alt-text generator, concurrent |

---

## `extract_images`

```python
result = convert_file("report.docx", extract_images=True)
result.images   # [('chart.png', b'\x89PNG\r\n\x1a\n...')]

for name, data in result.images:
    Path("out", name).write_bytes(data)
```

`(filename, bytes)` pairs. The Markdown references the same filenames: `![Sales chart](chart.png)`.

## `extract_comments`

```python
result = convert_file("report.docx", extract_comments=True)
print(result.markdown[result.markdown.index("# Comments"):])
```

```markdown
# Comments

## 1
- **author**: Reviewer (2026-01-01T00:00:00Z)
- **comment**: Verify against ledger.
- **source**: Commented figure
```

Added to `markdown` and `plain_text`. No effect on formats other than DOCX and PPTX.

## `strict`

```python
convert_bytes(b"Caf\xe9", "txt")                # ok, one 'unsupported_feature' warning
convert_bytes(b"Caf\xe9", "txt", strict=True)   # MalformedDocumentError
```

Any [warning](results.md#conversionwarning) — a fallback decoding, a skipped element, a failed image description — becomes a `MalformedDocumentError`.

## `max_input_bytes`

```python
convert_bytes(b"abcdef", "txt", max_input_bytes=4)
# InputTooLargeError: input too large: 6 bytes exceeds limit of 4 bytes   (.size == 6, .limit == 4)
```

Checked before parsing starts.

## `max_total_image_bytes`

```python
result = convert_file("shot.png", extract_images=True, max_total_image_bytes=0)
result.images     # []
result.warnings   # [ConversionWarning(code="resource_limit_reached", message="image size (79 bytes) exceeds limit (0)", location="image.png")]
```

Caps the image bytes collected for `extract_images` and for describers. Images past the budget are neither returned nor described.

## `max_uncompressed_zip_bytes`

```python
convert_bytes(zip_bomb, "docx", max_uncompressed_zip_bytes=100 * 1024**2)
# InputTooLargeError: ... (.size > .limit)
```

Limits how much an Office archive (DOCX, PPTX, XLSX) may expand while being read. Keep it low for untrusted uploads.

## `image_describer`

Sync functions only. Any callable `(image: bytes, mime_type: str, prompt: str) -> str`, or a [`GeminiDescriber`](describers.md#geminidescriber).

```python
convert_file("shot.png", image_describer=lambda image, mime, prompt: "A red square").markdown
# '![A red square](image.png)\n'
```

Not callable → `TypeError`. A failing call → `skipped_element` warning. → [Image descriptions](../guide/images.md)

## `async_image_describer`

Async functions only. Any `async def (image: bytes, mime_type: str, prompt: str) -> str`, or an [`AsyncGeminiDescriber`](describers.md#asyncgeminidescriber). All images of a document are described concurrently.

```python
async def describe(image: bytes, mime_type: str, prompt: str) -> str:
    return await client.describe(image, mime_type)

result = await convert_file_async("deck.pptx", async_image_describer=describe)
```
