# Image descriptions

Documents carry images; LLMs reading Markdown only see `![](image1.png)`. An **image describer** fills that alt text with a real description at conversion time.

```markdown
![](image1.png)                                          ← without a describer
![A bar chart of quarterly revenue by region](image1.png) ← with one
```

Describers apply to images embedded in DOCX, PPTX and XLSX, and to standalone image files.

## The contract

A describer is any callable with this shape:

```python
def describe(image: bytes, mime_type: str, prompt: str) -> str: ...
```

| Argument | Value |
|---|---|
| `image` | Raw image bytes as stored in the document |
| `mime_type` | e.g. `"image/png"`, `"image/jpeg"` |
| `prompt` | The engine's instruction: `"Describe this image concisely for use as alt text."` |

It returns the description as `str`. Use the prompt or replace it with your own.

## Sync: `image_describer`

```python
from anytomd import convert_file

def describe(image: bytes, mime_type: str, prompt: str) -> str:
    return "A red square"

convert_file("shot.png", image_describer=describe).markdown   # '![A red square](image.png)\n'
```

Images are described one after another. The conversion runs with the GIL released; the GIL is re-acquired only around each call into your function.

### Any provider, your client

The binding ships no HTTP client for third-party APIs — you bring yours. With the OpenAI SDK, for example (any OpenAI-compatible gateway, including local servers, works the same):

```python
import base64
from openai import OpenAI
from anytomd import convert_file

client = OpenAI()

def describe(image: bytes, mime_type: str, prompt: str) -> str:
    data_url = f"data:{mime_type};base64,{base64.b64encode(image).decode()}"
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        max_tokens=128,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        }],
    )
    return response.choices[0].message.content or ""

result = convert_file("deck.pptx", image_describer=describe)
```

### Built-in: Gemini

```python
from anytomd import GeminiDescriber, convert_file

describer = GeminiDescriber()                       # reads GEMINI_API_KEY
describer = GeminiDescriber("AIza...", model="gemini-2.5-flash-lite")

result = convert_file("deck.pptx", image_describer=describer)
```

The default model is `gemini-3-flash-preview`. A `GeminiDescriber` is also callable on its own: `describer(image, "image/png", "What is this?")`. → [Reference](../reference/describers.md)

## Optional: the capability composites

Install [`anytomd[full]`](../installation.md#extras-what-each-one-adds) and two new describers appear, plus the composite that joins them:

```python
from anytomd import ImageDescriber, convert_file

describer = ImageDescriber(model="gpt-4.1-mini", api_key="sk-...")
result = convert_file("scan.docx", image_describer=describer)
describer.close()
```

`ImageDescriber` answers every image in one pass:

1. **Local OCR** (`LiteParseDescriber`, Tesseract through liteparse — offline, free) reads the text-bearing images: invoices, slides, screenshots of documents.
2. **The vision model** (`OpenAIDescriber`) is asked only when OCR returns nothing: an image without letters — a cat, a diagram, a scene.
3. **All silent**: the alt text stays empty, exactly as without a describer. Nothing is invented.

The rule that makes step 2 honest was measured, not assumed: on letterless inputs — noise, gradients, solid fills, dense line art, real photographs — the OCR layer yields zero text items, no stray characters, no confabulated words. `""` therefore means "no letters here", never "OCR was untidy".

Providers speak the OpenAI wire; the model switch is `api_base` plus `model` ([official compatibility endpoints for Anthropic and Google](../installation.md#extras-what-each-one-adds)):

```python
ImageDescriber(
    model="claude-sonnet-5-5",
    api_base="https://api.anthropic.com/v1/",
    api_key=os.environ["ANTHROPIC_API_KEY"],
)
```

Every answer is collapsed to one line: a blank line inside `![...]` would split the image in two. `AsyncImageDescriber` is the same stack for `convert_*_async`, with one shared gate over the engine's per-image fan-out (`max_concurrency`, default 4) so tesseract workers and provider sockets both stay bounded. A provider failure raises into the engine and lands as a `skipped_element` warning; an OCR failure is a miss — it just falls through. `close()` / `await aclose()` release the provider's sockets when you are done with the describer.

## Async: `async_image_describer`

The async conversions take an `async def` with the same shape and **describe every image of the document concurrently** on the running event loop:

```python
import asyncio
from anytomd import convert_file_async

async def describe(image: bytes, mime_type: str, prompt: str) -> str:
    return await my_async_client.describe(image, mime_type, prompt)

async def main() -> None:
    result = await convert_file_async("deck.pptx", async_image_describer=describe)
    print(result.markdown)

asyncio.run(main())
```

A document with 20 images takes roughly the time of its slowest description, not the sum. If your provider rate-limits, bound the fan-out inside the describer:

```python
gate = asyncio.Semaphore(4)

async def describe(image: bytes, mime_type: str, prompt: str) -> str:
    async with gate:
        return await my_async_client.describe(image, mime_type, prompt)
```

The built-in `AsyncGeminiDescriber` plugs in the same way and runs its HTTP calls natively, without touching the event loop.

## Failures degrade, they do not abort

A describer that raises or returns a non-string does not fail the conversion. The image keeps its original alt text and a `skipped_element` warning records why:

```python
def broken(image: bytes, mime_type: str, prompt: str) -> str:
    raise ValueError("boom")

result = convert_file("gallery.docx", image_describer=broken)
result.warnings[0].code       # 'skipped_element'
result.warnings[0].location   # 'image1.png'
```

With `strict=True` that warning becomes a `MalformedDocumentError` instead. Passing something that is not callable fails fast with `TypeError`.

## Describers and `extract_images`

The two are independent. A describer sees every image whether or not `extract_images` is set; `result.images` is filled only when `extract_images=True`. Both draw on the same `max_total_image_bytes` budget: images beyond it are neither described nor returned.
