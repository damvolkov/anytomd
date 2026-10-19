# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

### Changed

- Workflows named by the house rule (one lowercase word, acronyms uppercase): `ai-fix` is now `maintenance`
  (its commits are tagged `[maintenance]`), `Release` is now `release`.
- Renovate never bumps `requires-python`; the unused, abandoned `pytest-xdist` is dropped from the test tools.

## [1.4.0] - 2026-10-16

A new, smaller API. **Breaking**: every name below replaces the old one; there are no aliases. Same engine,
anytomd-rs 1.3.1.

### Changed

- Three verbs, each with an `a`-prefixed async twin: `convert` / `aconvert` (path or bytes, replacing the four
  `convert_file*` / `convert_bytes*`), `detect` / `adetect` (replacing `detect_format` + `detect_zip_format`; office
  types and engine families resolve to the concrete format), `describe` / `adescribe`.
- PDF is just another format: `convert("report.pdf")` works with `anytomd[pdf]` and raises `MissingExtraError` without
  it. `PdfConverter` and `PdfDocument` are gone.
- Images follow one rule when the extras are installed: OCR text first (`[ocr]`); for an image without letters, a
  description labeled `Image description:` (`[vlm]`); otherwise `""`, or the author's own alt text inside documents.
- `describe` asks the vision model only (no OCR) and returns what `convert` returns on fallback.
- Vision is configured with `VisionSpec(model, base_url, api_key, …)` or `ANYTOMD_VISION_*`; any OpenAI-compatible
  endpoint. The describer classes and user callables are gone, and so are the compiled Gemini describers
  (Gemini is reachable through its OpenAI-compatible endpoint); the wheel drops reqwest and rustls.
- `Document` (frozen) replaces `ConversionResult`; `plain_text` is now `text`; `pages` carries the PDF page count.
  `DocumentWarning` replaces `ConversionWarning`.
- Options: `images`, `comments`, `max_image_bytes`, `max_zip_bytes` replace `extract_images`, `extract_comments`,
  `max_total_image_bytes`, `max_uncompressed_zip_bytes`; `ocr` and `vision` are new.
- Errors: `ConversionError` root with `UnknownFormatError`, `MissingExtraError`, `InputTooLargeError`,
  `MalformedDocumentError` and `DescriptionError`. ZIP, XML, spreadsheet and UTF-8 failures are
  `MalformedDocumentError`.
- `__version__` is the package version, an independent semver; `ENGINE_VERSION` is the anytomd-rs release inside.
- `anytomd[vlm]` also installs `pydantic-settings`.
- Package layout follows the library triad: `infra/` (contracts), `backends/` (native, liteparse, openai, registry),
  `logic/` (api and use cases).

### Added

- Debug logging under the `anytomd` logger: route, OCR result, vision fallback on/off and failures.

## [1.3.1.post3] - 2026-10-15

Documentation only; same code as 1.3.1.post2.

### Changed

- README reduced to the essentials and a map of the documentation site, which carries the full usage.
- Quickstart and home page cover the optional OCR, vision and PDF capabilities and self-maintenance.

## [1.3.1.post2] - 2026-10-15

Optional capabilities over the same engine (anytomd-rs 1.3.1). The base wheel keeps zero Python dependencies.

### Added

- Extras named by capability, not vendor: `anytomd[ocr]` (local OCR, liteparse with bundled Tesseract),
  `anytomd[vlm]` (vision through any OpenAI-compatible endpoint, `openai` SDK), `anytomd[pdf]` (PDF to Markdown,
  liteparse) and `anytomd[full]`. A missing extra raises `ImportError` naming the one to install.
- `LiteParseDescriber` / `AsyncLiteParseDescriber`: OCR describers; `""` means the image holds no letters, and formats
  OCR cannot read (SVG, HEIC) miss the same way.
- `OpenAIDescriber` / `AsyncOpenAIDescriber`: vision describers over `chat/completions` with a data-URI image;
  `close()` / `await aclose()` release the sockets.
- `ImageDescriber` / `AsyncImageDescriber`: OCR first, the vision model only for images OCR reads as blank, empty alt
  text when every layer is silent; the async composite bounds the per-image fan-out with one gate (`max_concurrency`).
- `PdfConverter`, `PdfDocument` and `PdfError` (a `ConvertError`): a separate entry point for PDFs; the engine still
  raises `FormatNotSupportedError` for them, so routing stays explicit.
- The monthly dependency health check also covers optional dependencies.

### Changed

- The stub-only callback aliases are now `DescribeCallable` / `AsyncDescribeCallable`; `ImageDescriber` and
  `AsyncImageDescriber` are the composite classes.

### Fixed

- Alt text from the new describers is collapsed to one line: a blank line inside `![...]` split the image into two
  paragraphs.

## [1.3.1.post1] - 2026-10-15

Binding fixes over the same engine (anytomd-rs 1.3.1). No change to Markdown output.

### Fixed

- Engine panics no longer abort the interpreter: release builds unwind, and a panic surfaces as `RuntimeError`
  from sync and async conversions alike.
- `ZipError`, `XmlError`, `SpreadsheetError` and `Utf8Error` carry the underlying cause instead of a duplicated prefix.
- Unreadable paths raise the matching `OSError` subclass (`FileNotFoundError`, `IsADirectoryError`, …) with `errno`
  and `filename` set; non-UTF-8 file names are accepted.
- `async_image_describer` works without `extract_images=True`, matching the sync describer; `result.images` stays empty
  unless extraction was asked for.
- A describer that is not callable raises `TypeError` up front instead of degrading every image to a warning.
- Cancelling an awaiting task aborts the conversion and cancels in-flight `async def` describers.
- `anytomd.__version__` is exported.
- `ConversionResult` repr counts characters, not bytes.

### Changed

- Supports CPython 3.12 and later (abi3 wheels from `cp312`), down from 3.14.
- Licensed Apache-2.0, like anytomd-rs. Wheels and sdist ship `THIRD_PARTY_LICENSES.md` with the license of every
  statically linked crate.
- Versioning: the package version is the embedded engine version; binding-only releases add `.postN`.
- `ConversionResult` fields are built once: repeated access no longer copies strings and image bytes.
- `bytes` inputs are read without a copy; `bytearray` is accepted wherever bytes are.
- The async runtime sizes its worker pool to the machine instead of a fixed four threads.
- Every function, class, property and exception carries a docstring.

### Added

- Documentation site (MkDocs Material), README oriented to anytomd-rs.
- CI (lint, types, Rust gates, tests on Linux, macOS and Windows × Python 3.12/3.14, docs, Pages) and a tag-driven
  release building wheels for Linux x86_64/aarch64, macOS arm64/x86_64 and Windows x86_64.
- Rust line coverage of the binding driven by the Python suite (`cargo llvm-cov`, gate 90 %).
- prek hooks (`prek.toml`) shared by local commits and CI: Python, Rust, licenses, workflows, docs, secrets;
  coverage gates on pre-push.
- Build provenance attestations for released wheels and sdist.
- Self-maintenance: Renovate, version and license sync, upstream API diff, a Qwen agent that repairs or extends the
  binding on dependency updates, and a monthly dependency health check.

## [1.3.1] - 2026-10-15

Initial release: thin PyO3 binding of anytomd-rs 1.3.1.

### Added

- `convert_file` / `convert_bytes`: full sync surface — every `ConversionOptions` field, image
  description via Python callables or the built-in `GeminiDescriber`, GIL released during conversion.
- `convert_file_async` / `convert_bytes_async`: native coroutines awaited from asyncio; concurrent
  image description through `AsyncGeminiDescriber` or `async def` Python describers bridged to the
  running loop; conversions spawn onto an internal tokio runtime.
- `detect_format` / `detect_zip_format`.
- `ConversionResult` (`markdown`, `plain_text`, `title`, `images`, `warnings`) and
  `ConversionWarning` (`code`, `message`, `location`).
- Typed error tree rooted at `ConvertError` covering every `ConvertError` variant.
- Type stubs (`py.typed`), abi3 wheels (CPython ≥ 3.14), sdist.
