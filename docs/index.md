# anytomd

<div class="rx-hero" markdown>
<p>The Python binding of <a href="https://github.com/developer0hye/anytomd-rs"><strong>anytomd-rs</strong></a> — the pure-Rust engine that turns DOCX, PPTX, XLSX, HTML, CSV, notebooks, images and code into clean Markdown, designed for LLM consumption.</p>
</div>

```bash
pip install anytomd        # or: uv add anytomd
```

```python
from anytomd import convert_file

result = convert_file("report.docx")
print(result.markdown)
```

```markdown
# Quarterly Report

## Summary

Revenue grew by **18 percent** and costs fell by *4 percent*.

![Sales chart](chart.png)

| Region | Sales |
|---|---|
| EMEA | 1200 |
```

<div class="rx-grid" markdown>
<div markdown>
### The engine, unchanged
Every conversion runs inside anytomd-rs itself. The binding adds no parsing logic of its own — output matches the Rust crate and its CLI byte for byte.
</div>
<div markdown>
### No Python dependencies
One compiled extension module per platform. No runtime packages, no subprocess, no system libraries.
</div>
<div markdown>
### Releases the GIL
Conversions run with the GIL released: threads convert in parallel, the interpreter stays responsive.
</div>
<div markdown>
### Native asyncio
`await convert_file_async(...)` runs the conversion off the event loop and describes every image of a document concurrently.
</div>
<div markdown>
### LLM alt text
Plug any callable — your OpenAI, Anthropic or local model — or the built-in Gemini describers, to replace image placeholders with real descriptions.
</div>
<div markdown>
### Typed end to end
Inline type stubs, `py.typed`, a typed exception tree and typed warnings. Your type checker sees the whole surface.
</div>
</div>

## What it converts

DOCX, PPTX, XLSX, XLS, HTML, CSV, Jupyter notebooks, JSON, XML, images (PNG, JPEG, GIF, WebP, BMP, TIFF, SVG, HEIC, AVIF), source code and plain text. PDF is refused on purpose: current LLMs read PDF natively. Full matrix → [Formats](guide/formats.md).

## Where to go next

- [Installation](installation.md) — wheels, platforms, building from source.
- [Quickstart](quickstart.md) — the five calls you will actually use.
- [Reference](reference/conversion.md) — every function, option, class and exception, one by one.
- [Upstream and versioning](upstream.md) — how this binding tracks anytomd-rs.

!!! info "Relationship to anytomd-rs"
    anytomd-rs is written and maintained by [developer0hye](https://github.com/developer0hye). This package is a binding of it for Python; conversion quality, format coverage and performance belong to the upstream project, and so do its [benchmarks](https://github.com/developer0hye/anytomd-rs). Bugs in the Markdown output are upstream issues; bugs in the Python surface belong [here](https://github.com/damvolkov/anytomd/issues).
