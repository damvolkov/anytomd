# anytomd

Any document to clean Markdown — a thin, typed Python binding of [anytomd-rs](https://github.com/developer0hye/anytomd-rs),
the pure-Rust document intelligence engine. PyO3 extension module, abi3, zero Python runtime dependencies.

```bash
uv add anytomd          # or: pip install anytomd
```

```python
from anytomd import convert_file

report = convert_file("document.docx")
print(report.markdown)      # headings, tables, lists, links, embedded images
print(report.plain_text)    # same content, no markers
print(report.title)         # first heading, if any
```

## API

| | |
|---|---|
| `convert_file(path, **options)` | Convert a document by path; format autodetected from magic bytes and extension. |
| `convert_bytes(data, format, **options)` | Convert raw bytes with an explicit format (`"csv"`, `"docx"`, …). |
| `await convert_file_async(path, **options)` | Async variant; concurrent image description. |
| `await convert_bytes_async(data, format, **options)` | Async variant over bytes. |
| `detect_format(path, data)` | Format string the engine would choose, or `None`. |
| `detect_zip_format(data)` | Concrete OOXML type behind ZIP magic (`"docx"`, `"pptx"`, `"xlsx"`, or `None`). |

### Options (keyword-only, on all four conversions)

`extract_images`, `extract_comments`, `strict`, `max_input_bytes`, `max_total_image_bytes`,
`max_uncompressed_zip_bytes`, and `image_describer` / `async_image_describer` on the sync/async
variants respectively. The engine's own defaults apply unless overridden.

> The engine collects image bytes only when `extract_images=True` or a describer is attached.
> For the async describers pass `extract_images=True` — the gate lives in the Rust crate.

### Result

`ConversionResult` exposes `markdown: str`, `plain_text: str`, `title: str | None`,
`images: list[tuple[str, bytes]]` and `warnings: list[ConversionWarning]`;
each warning carries `code` (`"skipped_element" | "unsupported_feature" | "resource_limit_reached" | "malformed_segment"`),
`message` and `location`.

### Image description

Any callable `f(image_bytes, mime_type, prompt) -> str` (sync) or an `async def` of the same shape
(async) plugs into `image_describer` / `async_image_describer`. Failures degrade to `skipped_element`
warnings — never abort — unless `strict=True`. Descriptions run off the GIL; the async bridge resolves
all images concurrently through the running asyncio loop.

Built-in providers ship with the crate: `GeminiDescriber` and `AsyncGeminiDescriber` (API key argument
or `GEMINI_API_KEY`), and work with any OpenAI-compatible gateway through your own callable.

### Errors

`ConvertError` is the base; `UnsupportedFormatError`, `FormatNotSupportedError`, `InputTooLargeError`
(with `.size` and `.limit`), `MalformedDocumentError`, `ImageDescriptionError`, `ZipError`, `XmlError`,
`SpreadsheetError` and `Utf8Error` refine it. Filesystem failures raise `OSError`.

## Formats

DOCX, PPTX, XLSX/XLS, HTML, CSV, Jupyter notebooks, JSON, XML, images (PNG, JPEG, GIF, WebP, BMP,
TIFF, SVG, HEIC, AVIF), source code (90+ languages) and plain text. PDF is intentionally refused —
LLMs read it natively.

## Development

```bash
make build         # maturin develop (debug)
make test          # unit suite + 100% coverage gate
make stress        # threads, loops, volume, hypothesis fuzz
make integration   # real LLM describer (defaults to Alibaba token-plan, see tests/conftest.py)
make suite         # everything, one coverage gate
make samples       # regenerate synthetic fixtures
make samples-real  # download real-world fixtures
make dist          # release wheels + sdist
```

## License

MIT for the binding. Wheels embed [anytomd-rs](https://github.com/developer0hye/anytomd-rs) under Apache-2.0.
