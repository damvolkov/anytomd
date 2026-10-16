# Formats

`convert` picks the format from the file's first bytes and its extension. For bytes, you name it: `format="docx"`.

## Documents

| Format | Extensions | Out |
|---|---|---|
| Word | `.docx` | Headings, paragraphs, bold/italic, lists, tables, links, images, comments |
| PowerPoint | `.pptx` | One `## Slide N` per slide, tables, speaker notes, images, comments |
| Excel | `.xlsx` `.xls` | One `## Sheet` per sheet, as a table |
| PDF | `.pdf` | Every page, in reading order. **Not native — needs `anytomd[pdf]`** |

## Web and data

| Format | Extensions | Out |
|---|---|---|
| HTML | `.html` `.htm` | Headings, tables, lists, links, code blocks; `<title>` becomes `document.title` |
| CSV | `.csv` | One table |
| Jupyter | `.ipynb` | Markdown cells as-is, code cells fenced |
| JSON | `.json` | Pretty-printed, fenced |
| XML | `.xml` | Pretty-printed, fenced |

## Text and code

| Format | Extensions | Out |
|---|---|---|
| Text | `.txt` `.md` `.rst` `.log` `.yaml` `.toml` `.ini` … | As-is; UTF-8, UTF-16 and Windows-1252 detected |
| Code | `.py` `.rs` `.js` `.ts` `.go` `.java` `.c` … | Fenced, with its language |

## Images

`.png` `.jpg` `.gif` `.webp` `.bmp` `.tiff` `.svg` `.heic` `.avif`, alone or inside a DOCX, PPTX or XLSX.

| Installed | An image with text | An image without text |
|---|---|---|
| nothing | `![](image.png)` | `![](image.png)` |
| `[ocr]` | its text | `""` |
| `[ocr]` + `[vlm]` | its text | `Image description: A red square on white.` |
| `[vlm]` only | `Image description: …` | `Image description: …` |

OCR always goes first: it is local, free and exact. The vision model is asked only when OCR finds no letters, and its answer is always labeled `Image description:`, so you can tell it from text that was really in the image.

```python
import anytomd as ad

ad.convert("invoice.png").markdown   # e.g. 'Invoice 2026\nAmount due: 1.240,00 EUR'
ad.convert("cat.png").markdown       # e.g. 'Image description: A tabby cat asleep on a wooden chair.'
```

Inside documents, the same rule fills each image's alt text, on one line:

```markdown
![Invoice 2026 Amount due: 1.240,00 EUR](image1.png)
![Image description: A tabby cat asleep on a wooden chair.](image2.png)
```

When neither finds anything, the author's own alt text stays: `![Sales chart](chart.png)`.

Vision needs a model → [VisionSpec](api.md#visionspec). Turn OCR off with `ocr=False`.

## PDF

The engine leaves PDF out on purpose: LLMs read it natively. To convert it here:

```bash
pip install "anytomd[pdf]"
```

```python
document = ad.convert("report.pdf")
document.markdown   # every page, joined
document.pages      # 12
```

Text layers are read directly; scanned pages go through OCR (`ocr=False` skips it). Without the extra:

```python
ad.convert("report.pdf")
# MissingExtraError: PDF needs the 'pdf' extra: pip install 'anytomd[pdf]'
```

## Not supported

Plain ZIP archives, EPUB, binaries → `UnknownFormatError`.
