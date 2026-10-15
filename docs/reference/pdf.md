# PDF

The engine [refuses PDFs by design](../guide/formats.md#pdf-is-refused-on-purpose); this optional capability reads them locally instead. Needs `anytomd[pdf]` — [liteparse](https://github.com/run-llama/liteparse), Rust, in-process, bundled Tesseract. No key, no network.

```python
from anytomd import PdfConverter

document = PdfConverter().convert_file("report.pdf")
document.markdown   # every page, reading-order Markdown, joined with blank lines
document.pages      # 12
document.warnings   # ('page 7: ...',) when a page was skipped
```

---

## `PdfConverter`

```python
PdfConverter(ocr: bool = True, language: str = "eng", workers: int | None = None, parser: LiteParse | None = None)
```

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `ocr` | `bool` | `True` | OCR scanned pages. Documents with a text layer keep reading it; turn this off for pure speed |
| `language` | `str` | `"eng"` | Tesseract language code |
| `workers` | `int \| None` | `None` | Concurrent page workers; `None` is liteparse's default |
| `parser` | `LiteParse \| None` | `None` | Injected engine; one converter is worth reusing across documents |

| Method | Does |
|---|---|
| `convert_file(path)` | Read a PDF path |
| `convert_bytes(data)` | Read PDF bytes |
| `await convert_file_async(path)` | Read off the event loop |
| `await convert_bytes_async(data)` | Bytes off the event loop |

| Raises | When |
|---|---|
| `ImportError` | `parser` not injected and `liteparse` not installed: `pip install anytomd[pdf]` |
| [`PdfError`](#pdferror) | The document could not be read |

A converter is stateless after construction; build it once, convert anywhere.

---

## `PdfDocument`

The frozen result: `markdown: str`, `pages: int`, `warnings: tuple[str, ...]`. Page-level failures that liteparse skips are listed here, never silently dropped.

---

## `PdfError`

Subclass of [`ConvertError`](exceptions.md), so `except ConvertError` covers PDFs too. Carries liteparse's reason: corrupt bytes, a password-protected document, an unreadable structure. Only liteparse's own `ParseError` is wrapped; any other exception is a bug and propagates unchanged. Document-level failure is fatal by choice — partial silence is not.

!!! note "Route, don't branch"

    `convert_file` still raises `FormatNotSupportedError` for PDFs: catching it and reaching for `PdfConverter` keeps the engine's routing contract intact — the capability is a destination, never a detour hidden inside core.
