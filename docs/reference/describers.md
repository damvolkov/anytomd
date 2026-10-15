# Describers

An image describer turns image bytes into alt text. These kinds plug into the [conversion functions](conversion.md):

| Kind | Keyword | Needs | Concurrency |
|---|---|---|---|
| Your callable `(bytes, str, str) -> str` | `image_describer` | — | One image at a time |
| Your `async def (bytes, str, str) -> str` | `async_image_describer` | — | All images of a document at once, on your event loop |
| [`GeminiDescriber`](#geminidescriber) | `image_describer` | compiled in | One image at a time, native HTTP |
| [`AsyncGeminiDescriber`](#asyncgeminidescriber) | `async_image_describer` | compiled in | All images at once, native HTTP |
| [`LiteParseDescriber`](#liteparsedescriber) | `image_describer` | `anytomd[ocr]` | One image at a time, local Tesseract |
| [`AsyncLiteParseDescriber`](#asyncliteparsedescriber) | `async_image_describer` | `anytomd[ocr]` | Bounded worker pool |
| [`OpenAIDescriber`](#openaidescriber) | `image_describer` | `anytomd[vlm]` | One image at a time, OpenAI-compatible HTTP |
| [`AsyncOpenAIDescriber`](#asyncopenaidescriber) | `async_image_describer` | `anytomd[vlm]` | All images at once |
| [`ImageDescriber`](#imagedescriber) | `image_describer` | `anytomd[ocr]` / `[vlm]` | OCR first, vision only on blanks |
| [`AsyncImageDescriber`](#asyncimagedescriber) | `async_image_describer` | `anytomd[ocr]` / `[vlm]` | One shared gate over both layers |

The callback shapes as typed in the stubs — type-checking names only; `anytomd.ImageDescriber` is the composite class below:

```python
type DescribeCallable = Callable[[bytes, str, str], str]
type AsyncDescribeCallable = Callable[[bytes, str, str], Awaitable[str]]
```

---

## `GeminiDescriber`

Google Gemini, blocking HTTP, implemented in Rust.

```python
from anytomd import GeminiDescriber, convert_file

describer = GeminiDescriber()                                   # key from GEMINI_API_KEY
result = convert_file("deck.pptx", image_describer=describer)
```

```python
GeminiDescriber(api_key: str | None = None, model: str | None = None)
```

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `api_key` | `str \| None` | `None` | Google AI Studio key; `None` reads `GEMINI_API_KEY` |
| `model` | `str \| None` | `None` | Model name; `None` uses `gemini-3-flash-preview` |

| Raises | When |
|---|---|
| `ImageDescriptionError` | No `api_key` and `GEMINI_API_KEY` unset |

### Calling it directly

A `GeminiDescriber` is itself a describer function — useful to test a key or describe a lone image:

```python
with open("chart.png", "rb") as handle:
    describer(handle.read(), "image/png", "Describe this chart in one sentence.")
# e.g. 'A bar chart comparing quarterly revenue across three regions.'
```

```python
describer(image: bytes | bytearray, mime_type: str, prompt: str) -> str
```

Runs with the GIL released. Failures raise `ImageDescriptionError` here; inside a conversion they become `skipped_element` warnings.

---

## `AsyncGeminiDescriber`

Google Gemini, async HTTP, implemented in Rust. Pass it to the async conversions; every image of a document is described concurrently without touching your event loop.

```python
from anytomd import AsyncGeminiDescriber, convert_file_async

describer = AsyncGeminiDescriber(model="gemini-2.5-flash-lite")
result = await convert_file_async("deck.pptx", async_image_describer=describer)
```

```python
AsyncGeminiDescriber(api_key: str | None = None, model: str | None = None)
```

Parameters and errors as [`GeminiDescriber`](#geminidescriber). Not callable from Python: it exists to be handed to `convert_file_async` / `convert_bytes_async`.

---

## `LiteParseDescriber`

Local OCR: [liteparse](https://github.com/run-llama/liteparse) — Rust, in-process, Tesseract bundled — reads whatever letters the image holds. Needs `anytomd[ocr]`; no key, no network, no cost.

```python
from anytomd import LiteParseDescriber, convert_file

describer = LiteParseDescriber()
result = convert_file("scan.docx", image_describer=describer)
# ![Invoice 2026 — Amount due 1.240,00 EUR](image1.png)
```

```python
LiteParseDescriber(language: str = "eng", parser: LiteParse | None = None)
```

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `language` | `str` | `"eng"` | Tesseract language code |
| `parser` | `LiteParse \| None` | `None` | Injected engine; one parser is worth reusing across conversions |

Returns the image's text on one line (whitespace collapsed, so a blank line can never split the Markdown image), or `""`. The empty string is a promise, not noise: measured on noise, gradients, solid fills, dense line art and real photographs, the OCR layer yields zero text items — `""` means "this image carries no letters". Formats OCR cannot rasterize (SVG, HEIC) also answer `""`: a miss is data, never a fault.

---

## `AsyncLiteParseDescriber`

The same contract as an `async def`, running each parse off the event loop through a bounded worker pool. Pass it to the async conversions.

```python
AsyncLiteParseDescriber(language: str = "eng", max_concurrency: int = 4, parser: LiteParse | None = None)
```

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `max_concurrency` | `int` | `4` | Simultaneous Tesseract workers |

---

## `OpenAIDescriber`

Vision through the OpenAI-compatible wire — OpenAI, Anthropic, Gemini, Vertex and any local server that speaks `chat/completions` are one `api_base` apart. Needs `anytomd[vlm]`.

```python
from anytomd import OpenAIDescriber, convert_file

describer = OpenAIDescriber(
    model="claude-sonnet-5-5",
    api_base="https://api.anthropic.com/v1/",
    api_key=os.environ["ANTHROPIC_API_KEY"],
)
result = convert_file("gallery.docx", image_describer=describer)
# ![A tabby cat asleep on a wooden chair](image1.png)
```

```python
OpenAIDescriber(model: str, api_base: str | None = None, api_key: str | None = None,
                prompt: str | None = None, max_tokens: int = 128, client: OpenAI | None = None)
```

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `model` | `str` | — | Model name at the chosen endpoint |
| `api_base` | `str \| None` | `None` | Endpoint base URL; `None` is OpenAI's own |
| `api_key` | `str \| None` | `None` | Key; `None` falls back to the SDK's environment variable |
| `prompt` | `str \| None` | `None` | Replaces the engine's alt-text instruction when set |
| `max_tokens` | `int` | `128` | Answer budget |
| `client` | `OpenAI \| None` | `None` | Injected client; the one to reuse for many documents |

| Raises | When |
|---|---|
| `ImportError` | `client` not injected and `openai` not installed: `pip install anytomd[vlm]` |
| The SDK's `APIError` and friends | Provider refused or failed — inside a conversion the engine turns it into a `skipped_element` warning |

`close()` releases the client's sockets.

---

## `AsyncOpenAIDescriber`

Async twin of [`OpenAIDescriber`](#openaidescriber), same parameters with `client: AsyncOpenAI | None`, answers off the loop. `await aclose()` releases the sockets.

---

## `ImageDescriber`

The composite of the two capabilities, in one describer: **local OCR answers images that carry text; the vision model is asked only when OCR comes back empty; when everything is silent the alt text stays empty** — exactly as without a describer, nothing invented. Needs `anytomd[ocr]` while `ocr=True` and `anytomd[vlm]` when `model` is given.

```python
from anytomd import ImageDescriber, convert_file

describer = ImageDescriber(model="gpt-4.1-mini", api_key="sk-...")
result = convert_file("mixed.docx", image_describer=describer)
# ![Invoice 2026 — Amount due 1.240,00 EUR](image1.png)   ← read by OCR, free
# ![A tabby cat asleep on a wooden chair](image2.png)      ← no letters: described by the model
describer.close()
```

```python
ImageDescriber(model: str | None = None, api_base: str | None = None, api_key: str | None = None,
               prompt: str | None = None, max_tokens: int = 128, ocr: bool = True,
               language: str = "eng", ocr_parser: LiteParse | None = None, vlm_client: OpenAI | None = None)
```

Parameters are those of [`LiteParseDescriber`](#liteparsedescriber) and [`OpenAIDescriber`](#openaidescriber) at once — their injected engines are `ocr_parser` and `vlm_client`; `model=None` makes the composite OCR-only, `ocr=False` vision-only. Answers are collapsed to one line.

| Raises | When |
|---|---|
| `ValueError` | Both layers off: no `model` and `ocr=False` |
| `ImportError` | A requested layer's extra is not installed |

---

## `AsyncImageDescriber`

Same composite for the async conversions, same parameters plus `max_concurrency: int = 4`, with `vlm_client: AsyncOpenAI | None`. The engine describes every image of a document at once; one shared gate bounds both layers together, so neither the Tesseract pool nor the provider is ever hit by an unbounded burst. `await aclose()` releases the vision layer.
