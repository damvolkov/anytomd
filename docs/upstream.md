# Upstream and versioning

## anytomd-rs

[anytomd-rs](https://github.com/developer0hye/anytomd-rs) is a pure-Rust library, CLI and WebAssembly package by [developer0hye](https://github.com/developer0hye) that converts documents into Markdown for LLMs — no Python runtime, no C bindings, no subprocesses.

This package compiles it into a Python extension with [PyO3](https://pyo3.rs) and [maturin](https://www.maturin.rs), and adds:

| From anytomd-rs | Added here |
|---|---|
| Every converter and the Markdown it produces | The Python API: `convert`, `detect`, `describe` and their async twins |
| Format detection | Errors, warnings and `Document` as Python types |
| Limits, warnings, strict mode | GIL release, asyncio, cancellation |
| Performance and [benchmarks](https://github.com/developer0hye/anytomd-rs) | The extras: PDF and OCR (liteparse), vision (OpenAI-compatible) |

Wrong Markdown from a supported format → [anytomd-rs issues](https://github.com/developer0hye/anytomd-rs/issues). Anything else → [ours](https://github.com/edamlabs/anytomd/issues).

## Versions

```python
import anytomd as ad

ad.__version__      # '1.4.0' — this package, its own semver
ad.ENGINE_VERSION   # '1.3.1' — the anytomd-rs release compiled in
```

The engine is pinned to an exact release. Every new release is picked up automatically and recorded in the [changelog](changelog.md) → [Self-maintenance](maintenance.md).

## Other ways to use anytomd

| Runtime | Install |
|---|---|
| Rust | `cargo add anytomd` |
| CLI | `cargo install anytomd` |
| JavaScript / WASM | `npm install anytomd` |
| Python | `pip install anytomd` |

## Licenses

Apache-2.0, like anytomd-rs. Wheels statically link the engine and its dependencies, under permissive licenses and MPL-2.0. All license texts are in [`THIRD_PARTY_LICENSES.md`](https://github.com/edamlabs/anytomd/blob/main/THIRD_PARTY_LICENSES.md), shipped inside every wheel and regenerated with `make licenses`.
