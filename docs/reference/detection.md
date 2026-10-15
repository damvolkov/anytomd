# Detection

The engine's own format detection, exposed so you can route documents before converting them.

## `detect_format`

The format `convert_file` would pick for a file named `path` whose content starts with `data`.

```python
from anytomd import detect_format

detect_format("report.docx", docx_bytes)   # 'zip'   — Office documents: ask detect_zip_format next
detect_format("main.rs", b"fn main() {}")  # 'code'
detect_format("table.csv", b"a,b\n1,2\n")  # 'csv'
detect_format("export", b'{"a": 1}')       # 'json'  — sniffed from content
detect_format("notes.unknown", b"hello")   # None
```

```python
detect_format(path: str | os.PathLike[str], data: bytes | bytearray) -> str | None
```

| Parameter | Type | Meaning |
|---|---|---|
| `path` | `str \| os.PathLike[str]` | File name; only its extension is used — the file is never opened |
| `data` | `bytes \| bytearray` | Leading bytes of the content; the first few are enough for the magic check |

Returns the format, `"zip"` for any ZIP container, `"code"` for source files, or `None`. Order of decision → [Formats](../guide/formats.md#how-the-format-is-chosen).

---

## `detect_zip_format`

The Office type behind a ZIP container, from its internal layout.

```python
from anytomd import detect_zip_format

detect_zip_format(docx_bytes)   # 'docx'
detect_zip_format(pptx_bytes)   # 'pptx'
detect_zip_format(xlsx_bytes)   # 'xlsx'
detect_zip_format(plain_zip)    # None
```

```python
detect_zip_format(data: bytes | bytearray) -> str | None
```

| Parameter | Type | Meaning |
|---|---|---|
| `data` | `bytes \| bytearray` | The **whole** archive — the central directory sits at its end |

## Routing bytes of unknown type

```python
from anytomd import convert_bytes, detect_format, detect_zip_format

def convert_upload(filename: str, data: bytes):
    match detect_format(filename, data):
        case "zip":
            kind = detect_zip_format(data)
        case "code":
            kind = filename.rsplit(".", 1)[-1]
        case other:
            kind = other
    return convert_bytes(data, kind or "unknown")
```

`convert_bytes` raises `UnsupportedFormatError` for `"unknown"`, as `convert_file` would.
