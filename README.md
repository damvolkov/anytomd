# anytomd

[![PyPI](https://img.shields.io/pypi/v/anytomd.svg)](https://pypi.org/project/anytomd/)
[![Python](https://img.shields.io/pypi/pyversions/anytomd.svg)](https://pypi.org/project/anytomd/)
[![Docs](https://img.shields.io/badge/docs-damvolkov.github.io%2Fanytomd-8f3b1b)](https://damvolkov.github.io/anytomd/)
[![Upstream](https://img.shields.io/crates/v/anytomd.svg?label=anytomd-rs)](https://crates.io/crates/anytomd)

**Python binding of [anytomd-rs](https://github.com/developer0hye/anytomd-rs)** — the pure-Rust engine by
[developer0hye](https://github.com/developer0hye) that converts DOCX, PPTX, XLSX, HTML, CSV, notebooks, images and code
into clean Markdown, designed for LLM consumption.

Same engine, same output, now one `pip install` away: no Python dependencies, the GIL released during conversion,
native asyncio, typed end to end.

```bash
pip install anytomd        # or: uv add anytomd
```

```python
from anytomd import convert_file

result = convert_file("report.docx")
print(result.markdown)     # headings, tables, lists, links, images
print(result.plain_text)   # the same content, no Markdown syntax
print(result.title)        # 'Quarterly Report'
```

## Formats

| Format | Extensions |
|---|---|
| Word, PowerPoint, Excel | `.docx` `.pptx` `.xlsx` `.xls` |
| Web and data | `.html` `.htm` `.csv` `.json` `.xml` `.ipynb` |
| Images | `.png` `.jpg` `.gif` `.webp` `.bmp` `.tiff` `.svg` `.heic` `.avif` |
| Code and text | `.py` `.rs` `.js` `.ts` `.go` … · `.txt` `.md` `.yaml` `.toml` … |

Detected from magic bytes and extension. PDF is refused by the engine on purpose: current LLMs read it natively —
the optional [`pdf` extra](#optional-capabilities) parses it locally when you would rather not send it.
Details per format → [Formats](https://damvolkov.github.io/anytomd/guide/formats/).

## API

| Call | Does |
|---|---|
| `convert_file(path, **options)` | Convert a file; format autodetected |
| `convert_bytes(data, format, **options)` | Convert in-memory bytes; `format` is an extension (`"docx"`, `".csv"`) |
| `await convert_file_async(path, **options)` | Awaitable, off the event loop; images described concurrently |
| `await convert_bytes_async(data, format, **options)` | Awaitable variant over bytes |
| `detect_format(path, data)` | The format the engine would pick, or `None` |
| `detect_zip_format(data)` | `"docx"`, `"pptx"`, `"xlsx"` behind a ZIP, or `None` |

Options, keyword-only on every conversion: `extract_images`, `extract_comments`, `strict`, `max_input_bytes`,
`max_total_image_bytes`, `max_uncompressed_zip_bytes`, and `image_describer` / `async_image_describer`.
One by one → [Reference](https://damvolkov.github.io/anytomd/reference/conversion/).

## LLM image descriptions

Any callable `(image: bytes, mime_type: str, prompt: str) -> str` writes the alt text — your OpenAI, Anthropic or local
model — or use the built-in Gemini describers:

```python
from anytomd import GeminiDescriber, convert_file

result = convert_file("deck.pptx", image_describer=GeminiDescriber())   # GEMINI_API_KEY
# ![A bar chart of quarterly revenue by region](image1.png)
```

The async variants take an `async def` and describe every image of a document concurrently. A failing describer never
aborts the conversion: it becomes a warning. → [Image descriptions](https://damvolkov.github.io/anytomd/guide/images/)

## Optional capabilities

The wheel keeps zero Python dependencies. Four extras add a capability — the name says what it brings, not the library
behind it:

| Extra | Adds | Backed by |
|---|---|---|
| `[ocr]` | `LiteParseDescriber`: local OCR alt text — offline, no key, free | [liteparse](https://github.com/run-llama/liteparse), Rust in-process |
| `[vlm]` | `OpenAIDescriber`: vision answers through any OpenAI-compatible endpoint — OpenAI, Anthropic, Gemini, local servers | `openai` SDK |
| `[pdf]` | `PdfConverter`: PDF to Markdown, OCR on by default | liteparse again (the wheel deduplicates) |
| `[full]` | all three, plus the composite below | |

`GeminiDescriber` needs no extra: it is compiled into every wheel.

`ImageDescriber` composes them with one rule — empty means no letters: OCR answers images that carry text; only when it
reads nothing does the vision model describe the image; when everything is silent, the alt text stays empty exactly as
without a describer.

```bash
uv add "anytomd[full]"
```

```python
from anytomd import ImageDescriber, convert_file

describer = ImageDescriber(
    model="claude-sonnet-5-5",
    api_base="https://api.anthropic.com/v1/",       # Anthropic's OpenAI-compatible endpoint
    api_key="sk-ant-...",
)
result = convert_file("deck.pptx", image_describer=describer)
describer.close()
```

## Errors

Best-effort by default: recoverable problems land in `result.warnings`; `strict=True` raises instead. Unrecoverable ones
raise a subclass of `ConvertError`; unreadable paths raise `FileNotFoundError` and friends.
→ [Errors and warnings](https://damvolkov.github.io/anytomd/guide/errors/)

## Upstream

All conversion logic, format coverage and performance belong to
[anytomd-rs](https://github.com/developer0hye/anytomd-rs) — see its README for benchmarks, the CLI and the WASM build.
`anytomd.__version__` reports the engine release compiled into your wheel. Markdown output issues go
[upstream](https://github.com/developer0hye/anytomd-rs/issues); Python API issues go
[here](https://github.com/damvolkov/anytomd/issues). → [Upstream and versioning](https://damvolkov.github.io/anytomd/upstream/)

## Self-maintenance

The binding follows its dependencies on its own; a human only reviews and merges.

| Trigger | Job | Does |
|---|---|---|
| New anytomd-rs, PyO3, tokio, tooling release | Renovate | Opens a PR (`renovate/*`) |
| That PR | `sync.yml` | Sets the package version to the engine's, logs the engine in `CHANGELOG.md`, regenerates `THIRD_PARTY_LICENSES.md` |
| Every push and PR | `ci.yml` | prek hooks, tests on Linux/macOS/Windows × Python 3.12/3.14, Rust coverage ≥ 90 %, docs; on `renovate/*` also the engine's public API diff and release notes |
| CI red, or engine API grew | `ai-fix.yml` | A Qwen Code agent repairs or extends the binding under [`QWEN.md`](QWEN.md); allowlisted commits only, three attempts at most |
| First day of the month | `health.yml` | Flags archived, vanished, stale or dormant dependencies in one issue |
| `v*` tag | `release.yml` | Wheels for five platforms, sdist, build provenance, PyPI via trusted publishing |

Package version = engine version; binding-only fixes ship as `.postN`. Exactly which files each piece may edit, and with
which tool → [What it touches](https://damvolkov.github.io/anytomd/maintenance/#what-it-touches)

## Development

```bash
uv sync && uv run prek install   # hooks: ruff, ty, tach, rustfmt, clippy, licenses, zizmor, docs, gitleaks
make check                       # build + ruff + ty + tach + tests
make cov                         # Rust coverage driven by the Python suite (gate 90 %)
```

→ [Development](https://damvolkov.github.io/anytomd/development/)

## License

Apache-2.0, like [anytomd-rs](https://github.com/developer0hye/anytomd-rs). Wheels statically link anytomd-rs and its
dependencies; their licenses ship in [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md), inside every wheel too.
