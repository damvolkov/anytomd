# Results

## `ConversionResult`

What every conversion returns. Immutable; every field is built once, so repeated access is free.

```python
from anytomd import convert_file

result = convert_file("report.docx", extract_images=True)
result
# ConversionResult(markdown=185 chars, title='Quarterly Report', images=1, warnings=0)
```

| Attribute | Type | Content |
|---|---|---|
| `markdown` | `str` | The converted Markdown |
| `plain_text` | `str` | Same content without Markdown syntax, extracted directly from the source |
| `title` | `str \| None` | First heading, or the HTML `<title>`; `None` if the document has neither |
| `images` | `list[tuple[str, bytes]]` | `(filename, bytes)` per embedded image; empty unless `extract_images=True` |
| `warnings` | `list[ConversionWarning]` | Recoverable problems |

```python
result.markdown     # '# Quarterly Report\n\n## Summary\n\n...'
result.plain_text   # 'Quarterly Report\n\nSummary\n\n...'
result.title        # 'Quarterly Report'
result.images       # [('chart.png', b'\x89PNG...')]
result.warnings     # []
```

Instances are created by the conversion functions only; the class cannot be instantiated from Python.

---

## `ConversionWarning`

One recoverable problem.

```python
from anytomd import convert_bytes

warning = convert_bytes(b"Caf\xe9 con leche", "txt").warnings[0]
warning.code       # 'unsupported_feature'
warning.message    # 'decoded from windows-1252 encoding (fallback)'
warning.location   # None
```

| Attribute | Type | Content |
|---|---|---|
| `code` | `Literal["skipped_element", "unsupported_feature", "resource_limit_reached", "malformed_segment"]` | Category — branch on this |
| `message` | `str` | Human-readable explanation; wording may change |
| `location` | `str \| None` | Where it happened — an image file name, a sheet, a slide — when known |

Branch on `code`, log `message`. The four codes → [Errors and warnings](../guide/errors.md#warnings).
