<p align="center">
  <a href="https://github.com/edamlabs/anytomd/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/edamlabs/anytomd/ci.yml?label=test" alt="CI"></a>
  <a href="https://pypi.org/project/anytomd/"><img src="https://img.shields.io/pypi/v/anytomd?color=166b7e" alt="PyPI"></a>
  <a href="https://pypi.org/project/anytomd/"><img src="https://img.shields.io/pypi/pyversions/anytomd" alt="Python"></a>
  <a href="LICENSE"><img src="https://img.shields.io/pypi/l/anytomd?color=166b7e" alt="License"></a>
</p>

Python binding of anytomd-rs: DOCX, PPTX, XLSX, HTML, CSV, images and more to clean Markdown for LLMs.

An **EDamLabs binding**: a Python binding of a third-party engine that keeps its upstream's syntax and follows its releases ([EDamLabs families](https://github.com/edamlabs/esteward#identity)).

## Install

```bash
pip install anytomd            # or: uv add anytomd
pip install "anytomd[full]"    # + PDF, text in images (OCR), image descriptions (vision LLM)
```

## Usage

```python
import anytomd as ad

document = ad.convert("report.docx")
document.markdown              # headings, tables, lists, links, images

await ad.aconvert("scan.pdf")  # every call has its async twin
ad.detect("export.dat")        # 'xlsx'
ad.describe("cat.png")         # 'Image description: A tabby cat asleep on a chair.'
```

**Text recovery** — one fixed 103-word passage written into every supported format and converted back: the share of the passage each format gives whole ([method](https://edamlabs.github.io/anytomd/formats/#text-recovery)).

![Text recovered per format](https://raw.githubusercontent.com/edamlabs/anytomd/main/docs/assets/fidelity-mini.svg)

| | |
| --- | --- |
| [Formats](https://edamlabs.github.io/anytomd/formats/) | What converts, with and without each extra |
| [API](https://edamlabs.github.io/anytomd/api/) | `convert`, `detect`, `describe`, their async twins, `Document`, `VisionSpec` |
| [Errors](https://edamlabs.github.io/anytomd/errors/) | What can fail, and how to catch it |
| [Self-maintenance](https://edamlabs.github.io/anytomd/maintenance/) | How the binding follows anytomd-rs on its own |

Conversion quality, format coverage and performance belong to [anytomd-rs](https://github.com/developer0hye/anytomd-rs): Markdown output issues go [upstream](https://github.com/developer0hye/anytomd-rs/issues), Python API issues [here](https://github.com/edamlabs/anytomd/issues).

Apache-2.0, like anytomd-rs. Wheels statically link the engine and its dependencies; their licenses ship in [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md).
