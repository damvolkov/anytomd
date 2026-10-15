# Quickstart

Five calls cover almost every use.

## 1. Convert a file

```python
from anytomd import convert_file

result = convert_file("report.docx")
result.markdown     # '# Quarterly Report\n\n## Summary\n\n...'
result.title        # 'Quarterly Report'
```

The format is detected from the file's magic bytes and extension. `path` accepts `str`, `pathlib.Path` or any `os.PathLike`.

## 2. Convert bytes

When the document lives in memory — an upload, an S3 object, an email attachment — pass the bytes and name the format:

```python
from anytomd import convert_bytes

result = convert_bytes(b"Name,Age\nAlice,30\nBob,25\n", "csv")
print(result.markdown)
```

```markdown
| Name | Age |
|---|---|
| Alice | 30 |
| Bob | 25 |
```

`format` is an extension, with or without the dot, any case: `"docx"`, `".DOCX"`, `"py"`.

## 3. Read plain text too

Every conversion returns Markdown **and** plain text, extracted straight from the source rather than by stripping Markdown:

```python
result = convert_bytes(b"Name,Age\nAlice,30\n", "csv")
result.plain_text   # 'Name\tAge\nAlice\t30\n'
```

## 4. Await it

```python
import asyncio
from anytomd import convert_file_async

async def main() -> None:
    results = await asyncio.gather(
        convert_file_async("report.docx"),
        convert_file_async("deck.pptx"),
        convert_file_async("book.xlsx"),
    )
    for result in results:
        print(result.title)

asyncio.run(main())
```

## 5. Describe images with an LLM

Any callable `(image: bytes, mime_type: str, prompt: str) -> str` becomes the alt-text generator:

```python
from anytomd import convert_file

def describe(image: bytes, mime_type: str, prompt: str) -> str:
    return my_vision_model(image, mime_type, prompt)   # your client here

result = convert_file("deck.pptx", image_describer=describe)
# e.g. ![A bar chart of quarterly revenue by region](image1.png)
```

Failures never abort the conversion: they become warnings. More → [Image descriptions](guide/images.md).

## 6. Optional: OCR, vision and PDF

```bash
pip install "anytomd[full]"
```

```python
from anytomd import ImageDescriber, PdfConverter, convert_file

describer = ImageDescriber(model="gpt-4.1-mini", api_key="sk-...")   # OCR first, vision only for images without text
result = convert_file("deck.pptx", image_describer=describer)
describer.close()

document = PdfConverter().convert_file("report.pdf")                 # the format the engine refuses, read locally
document.markdown
```

Each extra adds one capability: `[ocr]`, `[vlm]`, `[pdf]`, or `[full]` for all. → [Extras](installation.md#extras-what-each-one-adds) · [Image descriptions](guide/images.md#optional-the-capability-composites) · [PDF](reference/pdf.md)

## Handle what went wrong

```python
from anytomd import ConvertError, convert_file

try:
    result = convert_file("upload.bin")
except ConvertError as error:      # every conversion failure
    print(type(error).__name__, error)
else:
    for warning in result.warnings:   # recoverable problems
        print(warning.code, warning.message)
```

More → [Errors and warnings](guide/errors.md).
