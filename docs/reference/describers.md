# Describers

An image describer turns image bytes into alt text. Three kinds plug into the [conversion functions](conversion.md):

| Kind | Keyword | Concurrency |
|---|---|---|
| Your callable `(bytes, str, str) -> str` | `image_describer` | One image at a time |
| Your `async def (bytes, str, str) -> str` | `async_image_describer` | All images of a document at once, on your event loop |
| [`GeminiDescriber`](#geminidescriber) | `image_describer` | One image at a time, native HTTP |
| [`AsyncGeminiDescriber`](#asyncgeminidescriber) | `async_image_describer` | All images at once, native HTTP |

The type aliases used in the stubs:

```python
type ImageDescriber = Callable[[bytes, str, str], str]
type AsyncImageDescriber = Callable[[bytes, str, str], Awaitable[str]]
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
