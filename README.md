# anytomd

[![PyPI](https://img.shields.io/pypi/v/anytomd.svg)](https://pypi.org/project/anytomd/)
[![Python](https://img.shields.io/pypi/pyversions/anytomd.svg)](https://pypi.org/project/anytomd/)
[![Docs](https://img.shields.io/badge/docs-damvolkov.github.io%2Fanytomd-8f3b1b)](https://damvolkov.github.io/anytomd/)
[![CI](https://github.com/damvolkov/anytomd/actions/workflows/ci.yml/badge.svg)](https://github.com/damvolkov/anytomd/actions/workflows/ci.yml)
[![Upstream](https://img.shields.io/crates/v/anytomd.svg?label=anytomd-rs)](https://crates.io/crates/anytomd)

**Python binding of [anytomd-rs](https://github.com/developer0hye/anytomd-rs)** — the pure-Rust engine by
[developer0hye](https://github.com/developer0hye) that turns DOCX, PPTX, XLSX, HTML, CSV, notebooks, images and code
into clean Markdown for LLMs. No Python dependencies, GIL released, native asyncio, fully typed.

📖 **Documentation: <https://damvolkov.github.io/anytomd/>**

```bash
pip install anytomd            # or: uv add anytomd
pip install "anytomd[full]"    # + PDF, text in images (OCR), image descriptions (vision LLM)
```

```python
import anytomd as ad

document = ad.convert("report.docx")
document.markdown              # headings, tables, lists, links, images

await ad.aconvert("scan.pdf")  # every call has its async twin
ad.detect("export.dat")        # 'xlsx'
ad.describe("cat.png")         # 'Image description: A tabby cat asleep on a chair.'
```

**Text recovery** — one fixed 103-word passage written into every supported format and converted back: the share of
the passage each format gives whole ([method](https://damvolkov.github.io/anytomd/formats/#text-recovery)).

![Text recovered per format](https://raw.githubusercontent.com/damvolkov/anytomd/main/docs/assets/fidelity-mini.svg)

| | |
|---|---|
| [Formats](https://damvolkov.github.io/anytomd/formats/) | What converts, with and without each extra |
| [API](https://damvolkov.github.io/anytomd/api/) | `convert`, `detect`, `describe`, their async twins, `Document`, `VisionSpec` |
| [Errors](https://damvolkov.github.io/anytomd/errors/) | What can fail, and how to catch it |
| [Self-maintenance](https://damvolkov.github.io/anytomd/maintenance/) | How the binding follows anytomd-rs on its own |

Conversion quality, format coverage and performance belong to
[anytomd-rs](https://github.com/developer0hye/anytomd-rs): Markdown output issues go
[upstream](https://github.com/developer0hye/anytomd-rs/issues), Python API issues [here](https://github.com/damvolkov/anytomd/issues).

Apache-2.0, like anytomd-rs. Wheels statically link the engine and its dependencies; their licenses ship in
[`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md).
