# Changelog

All notable changes to this project are documented in this file.

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
