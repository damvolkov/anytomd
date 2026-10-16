# API

```python
import anytomd as ad
```

Every call has an async twin with the same arguments, prefixed `a`: `convert` → `aconvert`, `detect` → `adetect`, `describe` → `adescribe`.

---

## `convert`

```python
document = ad.convert("report.docx")
document.markdown   # '# Quarterly Report\n\n## Summary\n\nRevenue grew by **18 percent** ...'
document.title      # 'Quarterly Report'

ad.convert(b"Name,Age\nAlice,30\n", format="csv").markdown
# '| Name | Age |\n|---|---|\n| Alice | 30 |\n'
```

Returns a [`Document`](#document).

| Argument | Type | Default | |
|---|---|---|---|
| `source` | `str \| PathLike \| bytes \| bytearray` | — | A path, or the content itself |
| `format` | `str \| None` | `None` | Needed for bytes (`"docx"`, `".CSV"`…); for a path, overrides detection |
| `images` | `bool` | `False` | Return embedded images in `document.images` |
| `comments` | `bool` | `False` | Append DOCX/PPTX comments as a `# Comments` section |
| `strict` | `bool` | `False` | Raise on the first warning instead of collecting it |
| `ocr` | `bool` | `True` | Read the text inside images, when `[ocr]` is installed |
| `vision` | `VisionSpec \| None` | `None` | Vision model for descriptions; `None` reads `ANYTOMD_VISION_*` |
| `max_input_bytes` | `int` | 8 GiB | Largest input accepted |
| `max_image_bytes` | `int` | 4 GiB | Budget for image bytes held in memory |
| `max_zip_bytes` | `int` | 16 GiB | Limit for Office archives once decompressed (ZIP bombs) |

Raises → [Errors](errors.md).

## `aconvert`

```python
import asyncio

documents = await asyncio.gather(
    ad.aconvert("report.docx"),
    ad.aconvert("deck.pptx"),
    ad.aconvert("scan.pdf"),
)
```

Same arguments and result as `convert`. Conversion runs off the event loop; the images of one document are read and described concurrently, at most `VisionSpec.concurrency` at once. Cancelling the task cancels the conversion.

---

## `detect`

```python
ad.detect("report.docx")            # 'docx'
ad.detect("export.dat")             # 'xlsx'  — by content
ad.detect(data, name="table.csv")   # 'csv'
ad.detect("mystery.bin")            # None
```

Returns the format as `str`, or `None`. Office files are recognized by content; the result is valid as `convert(..., format=)`.

| Argument | Type | Default | |
|---|---|---|---|
| `source` | `str \| PathLike \| bytes \| bytearray` | — | A path or the content |
| `name` | `str \| None` | `None` | A filename hint for bytes |

## `adetect`

`await ad.adetect("report.docx")` — same, off the event loop.

---

## `describe`

```python
ad.describe("cat.png").markdown
# e.g. 'Image description: A tabby cat asleep on a wooden chair.'
```

Asks the vision model only, with no OCR. For an image without text, the result equals what `convert` returns. For an image full of text, you get a description of it, not a transcription. Needs `anytomd[vlm]` and a model.

Returns a [`Document`](#document) whose `markdown` and `text` are the labeled description.

| Argument | Type | Default | |
|---|---|---|---|
| `source` | `str \| PathLike \| bytes \| bytearray` | — | An image |
| `format` | `str \| None` | `None` | Needed for bytes (`"png"`) |
| `vision` | `VisionSpec \| None` | `None` | `None` reads `ANYTOMD_VISION_*` |

| Raises | When |
|---|---|
| `UnknownFormatError` | The source is not an image |
| `MissingExtraError` | `anytomd[vlm]` is not installed |
| `DescriptionError` | No model is configured, or the provider failed |

## `adescribe`

`await ad.adescribe("cat.png")` — same, off the event loop.

---

## `Document`

What `convert` and `describe` return. Frozen.

```python
document = ad.convert("report.docx", images=True)
document.markdown   # str
document.text       # same content, no Markdown syntax
document.title      # 'Quarterly Report' | None
document.images     # (('chart.png', b'\x89PNG...'),)
document.warnings   # (DocumentWarning(...), ...)
document.pages      # PDF page count | None
```

## `DocumentWarning`

Something recoverable went wrong; the rest converted.

```python
ad.convert(b"Caf\xe9", format="txt").warnings[0]
# DocumentWarning(code='unsupported_feature', message='decoded from windows-1252 encoding (fallback)', location=None)
```

| `code` | |
|---|---|
| `skipped_element` | Something was left out — e.g. a vision call failed |
| `unsupported_feature` | A fallback was used — e.g. a text encoding |
| `resource_limit_reached` | A limit dropped part of the output |
| `malformed_segment` | Damaged data was repaired |

## `VisionSpec`

The vision model behind descriptions. Any OpenAI-compatible endpoint works: `base_url` picks the provider.

```python
vision = ad.VisionSpec(
    model="claude-sonnet-5-5",
    base_url="https://api.anthropic.com/v1/",
    api_key="sk-ant-...",
)
ad.convert("deck.pptx", vision=vision)
```

| Field | Default | |
|---|---|---|
| `model` | — | Model name at the endpoint |
| `base_url` | `None` | `None` is OpenAI |
| `api_key` | `None` | `None` lets the SDK read `OPENAI_API_KEY` |
| `prompt` | `"Describe this image concisely for use as alt text."` | |
| `max_tokens` | `256` | |
| `concurrency` | `4` | Images described at once by `aconvert` |

Or configure it once from the environment, and every call picks it up:

```bash
export ANYTOMD_VISION_MODEL=gpt-4.1-mini
export ANYTOMD_VISION_API_KEY=sk-...
export ANYTOMD_VISION_BASE_URL=...        # optional
```

No model configured: the vision fallback stays off, and `describe` raises `DescriptionError`.

---

## Versions

```python
ad.__version__      # '1.4.0' — this package
ad.ENGINE_VERSION   # '1.3.1' — anytomd-rs inside it
```

## Logging

anytomd logs its decisions under the `anytomd` logger at `DEBUG`: the route taken, OCR finding text or not, the vision fallback switching on or off. It is silent by default.

```python
import logging

logging.basicConfig(level=logging.DEBUG)
ad.convert("cat.png")
# DEBUG:anytomd.logic.conversion:converting cat.png as 'png' through the image route
# DEBUG:anytomd.backends.registry:vision fallback on with 'gpt-4.1-mini'
# DEBUG:anytomd.logic.fallback:standalone image: ocr found nothing
```
