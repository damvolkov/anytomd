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
pip install "anytomd[full]"    # + local OCR, OpenAI-compatible vision, PDF
```

```python
from anytomd import convert_file

result = convert_file("report.docx")
print(result.markdown)     # headings, tables, lists, links, images
print(result.title)        # 'Quarterly Report'
```

| | |
|---|---|
| [Quickstart](https://damvolkov.github.io/anytomd/quickstart/) | The five calls you will actually use |
| [Formats](https://damvolkov.github.io/anytomd/guide/formats/) | What converts, how the format is chosen, PDF |
| [Image descriptions](https://damvolkov.github.io/anytomd/guide/images/) | LLM and OCR alt text: callables, Gemini, `ImageDescriber` |
| [Async](https://damvolkov.github.io/anytomd/guide/async/) | `await convert_file_async(...)`, concurrency, cancellation |
| [Errors and warnings](https://damvolkov.github.io/anytomd/guide/errors/) | Best-effort conversion, strict mode, limits |
| [Reference](https://damvolkov.github.io/anytomd/reference/conversion/) | Every function, option, class and exception |
| [Self-maintenance](https://damvolkov.github.io/anytomd/maintenance/) | How the binding follows anytomd-rs on its own |

Conversion quality, format coverage and performance belong to
[anytomd-rs](https://github.com/developer0hye/anytomd-rs): Markdown output issues go
[upstream](https://github.com/developer0hye/anytomd-rs/issues), Python API issues [here](https://github.com/damvolkov/anytomd/issues).

Apache-2.0, like anytomd-rs. Wheels statically link the engine and its dependencies; their licenses ship in
[`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md).
