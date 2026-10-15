# Upstream and versioning

## anytomd-rs

[anytomd-rs](https://github.com/developer0hye/anytomd-rs) is a pure-Rust library, CLI and WebAssembly package by [developer0hye](https://github.com/developer0hye) that converts documents into Markdown for LLM consumption — a native alternative to Microsoft's [MarkItDown](https://github.com/microsoft/markitdown) with no Python runtime, C bindings or subprocesses.

This package compiles that crate into a Python extension module with [PyO3](https://pyo3.rs) and [maturin](https://www.maturin.rs). It contributes only the Python surface:

| Belongs to anytomd-rs | Belongs to this binding |
|---|---|
| Every converter and the Markdown it produces | Python signatures, stubs and docstrings |
| Format detection | Mapping Rust errors to the Python exception tree |
| Limits, warnings, strict mode | GIL release, the asyncio bridge, cancellation |
| Gemini describers | Accepting Python callables as describers |
| Performance and [benchmarks](https://github.com/developer0hye/anytomd-rs) | Wheels for Python platforms |

Report wrong or missing Markdown [upstream](https://github.com/developer0hye/anytomd-rs/issues); report anything about the Python API [here](https://github.com/damvolkov/anytomd/issues).

## Which engine am I running?

```python
import anytomd

anytomd.__version__   # '1.3.1' — the anytomd-rs release compiled into this build
```

The binding pins an exact crate version. The package version is the engine version it embeds — anytomd-rs `1.3.1` ships as `anytomd 1.3.1` — and binding-only fixes over the same engine add a post-release: `1.3.1.post1`. New engine releases are picked up automatically → [Self-maintenance](maintenance.md).

## Other ways to use anytomd

| Runtime | Install |
|---|---|
| Rust | `cargo add anytomd` |
| CLI | `cargo install anytomd` |
| JavaScript / WASM | `npm install anytomd` |
| Python | `pip install anytomd` |

## Licenses

The binding is Apache-2.0, the same license as anytomd-rs. Its wheels statically link anytomd-rs and about two hundred crates under permissive licenses (Apache-2.0, MIT, ISC, Unicode-3.0, BSD-3-Clause, Zlib, CDLA-Permissive-2.0) and MPL-2.0; every license text is listed in [`THIRD_PARTY_LICENSES.md`](https://github.com/damvolkov/anytomd/blob/main/THIRD_PARTY_LICENSES.md), which ships inside each wheel and the sdist. It is regenerated with `make licenses`.
