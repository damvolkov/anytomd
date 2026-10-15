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

print(anytomd.__version__)   # e.g. '1.3.1' — the anytomd-rs version embedded in this build
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

## Extras: what each one adds

The base package has no Python dependencies; every extra adds one capability and names it, not the library that implements it:

| Extra | Capability it adds | Library it installs |
|---|---|---|
| `[ocr]` | [`LiteParseDescriber`](reference/describers.md#liteparsedescriber): local OCR — readable text as alt text, offline, no key, no cost | `liteparse` (Rust, in-process, bundled Tesseract) |
| `[vlm]` | [`OpenAIDescriber`](reference/describers.md#openaidescriber): vision answers from any OpenAI-compatible endpoint — OpenAI, Anthropic, Gemini, Vertex, local servers | `openai` (SDK only — the wire is the provider choice) |
| `[pdf]` | [`PdfConverter`](reference/pdf.md): PDF to Markdown, OCR on by default — the format the engine refuses by design | `liteparse` (same wheel as `[ocr]`) |
| `[full]` | All of the above plus [`ImageDescriber`](reference/describers.md#imagedescriber): OCR first, a vision model only for images that carry no text | — |

```bash
uv add "anytomd[full]"      # or pip install "anytomd[full]"
uv add "anytomd[pdf]"       # just local PDF
```

!!! note "Why OpenAI-compatible instead of a provider SDK per vendor"

    Anthropic, Google and Azure all publish official OpenAI-compatible endpoints with image support, so `api_base` + `model` is the provider switch. Anything the OpenAI wire cannot reach, the plain [describer callback](guide/images.md) can: bring your own client.
