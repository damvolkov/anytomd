# anytomd

<div class="rx-hero" markdown>
<p>Any document to clean Markdown, for LLMs. The Python binding of <a href="https://github.com/developer0hye/anytomd-rs"><strong>anytomd-rs</strong></a>, a pure-Rust engine by developer0hye.</p>
</div>

```bash
pip install anytomd
```

```python
import anytomd as ad

document = ad.convert("report.docx")
print(document.markdown)
```

```markdown
# Quarterly Report

## Summary

Revenue grew by **18 percent** and costs fell by *4 percent*.

| Region | Sales |
|---|---|
| EMEA | 1200 |
```

Three verbs, each with its async twin:

| Sync | Async | Does |
|---|---|---|
| `ad.convert(source)` | `await ad.aconvert(source)` | Document → Markdown |
| `ad.detect(source)` | `await ad.adetect(source)` | Which format is this? |
| `ad.describe(image)` | `await ad.adescribe(image)` | Image → description, with a vision model |

## Extras

The base package has no Python dependencies. Extras add a capability, and once installed they work on their own:

| Extra | Adds |
|---|---|
| `anytomd[pdf]` | PDF conversion |
| `anytomd[ocr]` | The text inside images |
| `anytomd[vlm]` | Image descriptions from any OpenAI-compatible vision model, and `describe` |
| `anytomd[full]` | All of them |

```bash
pip install "anytomd[full]"
```

Format by format → [Formats](formats.md) · every call → [API](api.md) · what can fail → [Errors](errors.md)

!!! info "anytomd-rs"
    Conversion quality, format coverage and performance belong to [anytomd-rs](https://github.com/developer0hye/anytomd-rs). Wrong Markdown is an [upstream issue](https://github.com/developer0hye/anytomd-rs/issues); anything about the Python API is [ours](https://github.com/edamlabs/anytomd/issues).
