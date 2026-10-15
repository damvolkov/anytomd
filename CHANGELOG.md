# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

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
