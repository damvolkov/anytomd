# Formats

| Format | Extensions | What survives |
|---|---|---|
| DOCX | `.docx` | Headings, tables (merged and layout tables included), lists, bold/italic, hyperlinks, images, text boxes, comments |
| PPTX | `.pptx` | Slides, tables (merged cells included), speaker notes, images, group shapes, comments |
| XLSX | `.xlsx` | Every sheet as a table, dates and times, images |
| XLS | `.xls` | Legacy Excel, every sheet as a table |
| HTML | `.html`, `.htm` | Headings, tables (`colspan`/`rowspan`), lists, links, blockquotes, code blocks; `<title>` becomes `result.title` |
| CSV | `.csv` | One Markdown table |
| Jupyter | `.ipynb` | Markdown cells verbatim, code cells fenced with their language |
| JSON | `.json` | Pretty-printed in a fenced block |
| XML | `.xml` | Pretty-printed in a fenced block |
| Images | `.png`, `.jpg`, `.gif`, `.webp`, `.bmp`, `.tiff`, `.svg`, `.heic`, `.avif` | A Markdown image; alt text from an [image describer](images.md) |
| Code | `.py`, `.rs`, `.js`, `.ts`, `.c`, `.cpp`, `.go`, `.java`, `.rb`, `.swift`, `.sh`, … | A fenced block with the language tag |
| Plain text | `.txt`, `.md`, `.rst`, `.log`, `.toml`, `.yaml`, `.ini`, … | Passed through; UTF-8, UTF-16 (BOM) and Windows-1252 detected |

The matrix is anytomd-rs's; this binding exposes it unchanged. The authoritative, always-current list lives in the [upstream README](https://github.com/developer0hye/anytomd-rs#supported-formats).

## PDF is refused on purpose

```python
from anytomd import convert_bytes

convert_bytes(pdf_bytes, "pdf")
# FormatNotSupportedError: pdf: PDF is intentionally unsupported — Gemini, ChatGPT, and Claude handle PDF natively
```

Send PDFs to the model directly. Catch `FormatNotSupportedError` to route them.

Or keep them local: the optional [`pdf` extra](../installation.md#extras-what-each-one-adds) adds [`PdfConverter`](../reference/pdf.md), a separate entry point over the same liteparse engine — text layers read directly, scanned pages OCR'd unless you turn that off.

## How the format is chosen

`convert_file` reads the file and decides in this order:

1. **Magic bytes.** A ZIP signature means an Office document: the archive's internal layout then tells DOCX, PPTX and XLSX apart. A PDF signature means PDF.
2. **Extension.** Everything else is chosen by the file extension.
3. **JSON sniffing.** An unknown extension whose content starts with `{` or `[` is treated as JSON.

So a renamed spreadsheet still converts:

```python
from anytomd import convert_file

convert_file("export.dat").markdown   # '## Sales\n| Name | Amount |\n...' — XLSX found by content
```

A plain ZIP that is not an Office document raises `UnsupportedFormatError: unsupported format: zip`.

`convert_bytes` skips detection: you name the format. To reproduce the decision yourself, use [`detect_format`](../reference/detection.md#detect_format) and [`detect_zip_format`](../reference/detection.md#detect_zip_format).

## Tables

Every table — plain, merged or used for page layout — becomes one pipe table with the table's true column count:

- a horizontally spanned cell keeps its text in the first column and leaves the others empty;
- a vertically merged continuation cell is blank;
- a full-width row stays a normal row.

A table that contains a **nested table** cannot fit in Markdown cells, so it is linearized: each cell's text and the nested table become standalone blocks.

## Plain text

`result.plain_text` is extracted directly from the source, not produced by stripping Markdown. Characters such as `**kwargs` or `# comment` in the source come through untouched. Table cells are tab-separated:

```python
from anytomd import convert_bytes

convert_bytes(b"Name,Age\nAlice,30\n", "csv").plain_text   # 'Name\tAge\nAlice\t30\n'
```

## Comments

DOCX and PPTX comments are opt-in with `extract_comments=True`. They are appended as a `# Comments` section to both outputs:

```markdown
# Comments

## 1
- **author**: Reviewer (2026-01-01T00:00:00Z)
- **comment**: Verify against ledger.
- **source**: Commented figure
```

For DOCX the source is the commented text; for PPTX, the slide label. Replies are flattened and marked `(reply)`. Other formats ignore the flag.
