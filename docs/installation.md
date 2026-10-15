# Installation

```bash
pip install anytomd
```

```bash
uv add anytomd
```

The package has **no runtime dependencies**. It ships a single compiled extension module built against the stable ABI (`abi3`), so one wheel per platform serves every CPython from 3.12 on.

## Requirements

| | |
|---|---|
| Python | CPython ≥ 3.12 |
| Runtime dependencies | none |
| Build from source | Rust toolchain (stable) + [maturin](https://www.maturin.rs/) |

## Wheels

Pre-built wheels are published for the platforms released through CI. Where no wheel matches, `pip` falls back to the source distribution and compiles the extension locally — that needs a Rust toolchain:

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
pip install anytomd
```

Check what you got:

```python
import anytomd

print(anytomd.__version__)   # 1.3.1 — the anytomd-rs version embedded in this build
```

## From the repository

```bash
git clone https://github.com/damvolkov/anytomd
cd anytomd
uv sync              # builds the extension in place (debug)
make build-release   # optimized build into the venv
```

## Optional: Gemini

The built-in [`GeminiDescriber`](reference/describers.md#geminidescriber) and [`AsyncGeminiDescriber`](reference/describers.md#asyncgeminidescriber) are compiled in. They need a Google AI Studio key, passed explicitly or read from `GEMINI_API_KEY`. Nothing else to install.
