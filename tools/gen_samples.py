"""Generate test resource fixtures: minimal valid documents for every anytomd format."""

import io
import struct
import sys
import zipfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "tests" / "resources"

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPEG_MAGIC = b"\xff\xd8\xff"
GIF_MAGIC = b"GIF89a"
WEBP_MAGIC = b"RIFF"
BMP_MAGIC = b"BM"
TIFF_MAGIC = b"II*\x00"
HEIC_MAGIC = b"\x00\x00\x00\x18ftypheic"
AVIF_MAGIC = b"\x00\x00\x00\x18ftypavif"

XML_DECL = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
DOC_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
REL_OFFICE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PPTX_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
XLS_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


def png(width: int, height: int, rgb: tuple[int, int, int]) -> bytes:
    raw = b"".join(b"\x00" + bytes(rgb) * width for _ in range(height))
    return b"".join(
        [
            PNG_MAGIC,
            _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)),
            _chunk(b"IDAT", zlib.compress(raw, 9)),
            _chunk(b"IEND", b""),
        ]
    )


def _chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def _zip(entries: dict[str, bytes | str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, payload in entries.items():
            archive.writestr(name, payload.encode("utf-8") if isinstance(payload, str) else payload)
    return buffer.getvalue()


MEDIA_PNG = png(16, 16, (220, 30, 30))

DOCX_BODY = f"""{XML_DECL}
<w:document xmlns:w="{DOC_NS}" xmlns:r="{REL_OFFICE}"
    xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
    xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
    xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">
  <w:body>
    <w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Quarterly Report</w:t></w:r></w:p>
    <w:p><w:pPr><w:pStyle w:val="Heading2"/></w:pPr><w:r><w:t>Summary</w:t></w:r></w:p>
    <w:p>
      <w:r><w:t xml:space="preserve">Revenue grew by </w:t></w:r>
      <w:r><w:rPr><w:b/></w:rPr><w:t>18 percent</w:t></w:r>
      <w:r><w:t xml:space="preserve"> and costs fell by </w:t></w:r>
      <w:r><w:rPr><w:i/></w:rPr><w:t>4 percent</w:t></w:r>
      <w:r><w:t>.</w:t></w:r>
    </w:p>
    <w:p><w:r><w:drawing><wp:inline><wp:docPr descr="Sales chart"/>
      <a:graphic><a:graphicData><pic:pic><pic:blipFill>
        <a:blip r:embed="rId2"/>
      </pic:blipFill></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>
    <w:tbl>
      <w:tr>
        <w:tc><w:p><w:r><w:t>Region</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>Sales</w:t></w:r></w:p></w:tc>
      </w:tr>
      <w:tr>
        <w:tc><w:p><w:r><w:t>EMEA</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>1200</w:t></w:r></w:p></w:tc>
      </w:tr>
    </w:tbl>
    <w:p>
      <w:commentRangeStart w:id="1"/>
      <w:r><w:t>Commented figure</w:t></w:r>
      <w:commentRangeEnd w:id="1"/>
      <w:r><w:commentReference w:id="1"/></w:r>
    </w:p>
  </w:body>
</w:document>"""

DOCX_COMMENTS = f"""{XML_DECL}
<w:comments xmlns:w="{DOC_NS}">
  <w:comment w:id="1" w:author="Reviewer" w:date="2026-01-01T00:00:00Z" w:initials="R">
    <w:p><w:r><w:t>Verify against ledger.</w:t></w:r></w:p>
  </w:comment>
</w:comments>"""

DOCX_PARTS: dict[str, bytes | str] = {
    "[Content_Types].xml": f"""{XML_DECL}
<Types xmlns="{CT_NS}">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Default Extension="png" ContentType="image/png"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/comments.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml"/>
</Types>""",
    "_rels/.rels": f"""{XML_DECL}
<Relationships xmlns="{REL_NS}">
  <Relationship Id="rId1" Type="{REL_OFFICE}/officeDocument" Target="word/document.xml"/>
</Relationships>""",
    "word/_rels/document.xml.rels": f"""{XML_DECL}
<Relationships xmlns="{REL_NS}">
  <Relationship Id="rId2" Type="{REL_OFFICE}/image" Target="media/chart.png"/>
  <Relationship Id="rId3" Type="{REL_OFFICE}/comments" Target="comments.xml"/>
</Relationships>""",
    "word/document.xml": DOCX_BODY,
    "word/comments.xml": DOCX_COMMENTS,
    "word/media/chart.png": MEDIA_PNG,
}

DOCX = _zip(DOCX_PARTS)


def docx_with(document_xml: object) -> bytes:
    """DOCX archive whose word/document.xml is replaced verbatim."""
    parts = dict(DOCX_PARTS)
    parts["word/document.xml"] = document_xml
    return _zip(parts)


def docx_with_images(count: int, descr: str = "") -> bytes:
    """DOCX archive with `count` embedded images awaiting description."""
    images = "\n".join(
        f"""<w:p><w:r><w:drawing><wp:inline><wp:docPr descr="{descr}"/>
      <a:graphic><a:graphicData><pic:pic><pic:blipFill>
        <a:blip r:embed="rId{index + 2}"/>
      </pic:blipFill></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>"""
        for index in range(count)
    )
    body = f"""{XML_DECL}
<w:document xmlns:w="{DOC_NS}" xmlns:r="{REL_OFFICE}"
    xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
    xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
    xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">
  <w:body>
    <w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Image Gallery</w:t></w:r></w:p>
    {images}
  </w:body>
</w:document>"""
    rels = "\n".join(
        f'<Relationship Id="rId{index + 2}" Type="{REL_OFFICE}/image" Target="media/image{index + 1}.png"/>'
        for index in range(count)
    )
    parts = {
        "[Content_Types].xml": DOCX_PARTS["[Content_Types].xml"],
        "_rels/.rels": DOCX_PARTS["_rels/.rels"],
        "word/_rels/document.xml.rels": f'{XML_DECL}\n<Relationships xmlns="{REL_NS}">\n{rels}\n</Relationships>',
        "word/document.xml": body,
    }
    parts.update({f"word/media/image{index + 1}.png": MEDIA_PNG for index in range(count)})
    return _zip(parts)


PPTX = _zip(
    {
        "[Content_Types].xml": f"""{XML_DECL}
<Types xmlns="{CT_NS}">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
  <Override PartName="/ppt/slides/slide1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>
</Types>""",
        "_rels/.rels": f"""{XML_DECL}
<Relationships xmlns="{REL_NS}">
  <Relationship Id="rId1" Type="{REL_OFFICE}/officeDocument" Target="ppt/presentation.xml"/>
</Relationships>""",
        "ppt/_rels/presentation.xml.rels": f"""{XML_DECL}
<Relationships xmlns="{REL_NS}">
  <Relationship Id="rId1" Type="{REL_OFFICE}/slide" Target="slides/slide1.xml"/>
</Relationships>""",
        "ppt/presentation.xml": f"""{XML_DECL}
<p:presentation xmlns:p="{PPTX_NS}" xmlns:r="{REL_OFFICE}">
  <p:sldIdLst><p:sldId id="256" r:id="rId1"/></p:sldIdLst>
</p:presentation>""",
        "ppt/slides/_rels/slide1.xml.rels": f"""{XML_DECL}
<Relationships xmlns="{REL_NS}"/>""",
        "ppt/slides/slide1.xml": f"""{XML_DECL}
<p:sld xmlns:p="{PPTX_NS}" xmlns:a="{A_NS}">
  <p:cSld><p:spTree>
    <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
    <p:grpSpPr/>
    <p:sp>
      <p:nvSpPr><p:cNvPr id="2" name="Title"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
      <p:txBody><a:bodyPr/><a:lstStyle/>
        <a:p><a:r><a:t>Launch Plan</a:t></a:r></a:p>
        <a:p><a:r><a:t>Ship in Q3</a:t></a:r></a:p>
      </p:txBody>
    </p:sp>
  </p:spTree></p:cSld>
</p:sld>""",
    }
)

XLSX = _zip(
    {
        "[Content_Types].xml": f"""{XML_DECL}
<Types xmlns="{CT_NS}">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>""",
        "_rels/.rels": f"""{XML_DECL}
<Relationships xmlns="{REL_NS}">
  <Relationship Id="rId1" Type="{REL_OFFICE}/officeDocument" Target="xl/workbook.xml"/>
</Relationships>""",
        "xl/_rels/workbook.xml.rels": f"""{XML_DECL}
<Relationships xmlns="{REL_NS}">
  <Relationship Id="rId1" Type="{REL_OFFICE}/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>""",
        "xl/workbook.xml": f"""{XML_DECL}
<workbook xmlns="{XLS_NS}" xmlns:r="{REL_OFFICE}">
  <sheets><sheet name="Sales" sheetId="1" r:id="rId1"/></sheets>
</workbook>""",
        "xl/worksheets/sheet1.xml": f"""{XML_DECL}
<worksheet xmlns="{XLS_NS}">
  <sheetData>
    <row r="1">
      <c r="A1" t="inlineStr"><is><t>Name</t></is></c>
      <c r="B1" t="inlineStr"><is><t>Amount</t></is></c>
    </row>
    <row r="2">
      <c r="A2" t="inlineStr"><is><t>Alice</t></is></c>
      <c r="B2"><v>1200</v></c>
    </row>
    <row r="3">
      <c r="A3" t="inlineStr"><is><t>Bob</t></is></c>
      <c r="B3"><v>900</v></c>
    </row>
  </sheetData>
</worksheet>""",
    }
)

ALIEN_ZIP = _zip({"readme/manifest.txt": b"not an office document"})

IPYNB = """{
 "cells": [
  {"cell_type": "markdown", "metadata": {}, "source": ["# Experiment\\n", "Notes here."]},
  {"cell_type": "code", "metadata": {}, "source": ["print('hi')\\n"], "outputs": [
    {"output_type": "stream", "name": "stdout", "text": ["hi\\n"]}], "execution_count": 1}
 ],
 "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}},
 "nbformat": 4,
 "nbformat_minor": 5
}"""

FILES: dict[str, dict[str, bytes | str]] = {
    "text": {
        "notes.txt": "Plain memo body.\nSecond line.\n",
        "latin.txt": "Café con leche\n".encode("windows-1252"),
        "utf16.txt": "Bom encoded text\n".encode("utf-16"),
        "table.csv": "Name,Age\nAlice,30\nBob,25\n",
        "page.html": "<!doctype html><html><head><title>Docs Page</title></head>"
        "<body><h1>Heading</h1><p>Paragraph with <b>bold</b> and a "
        '<a href="https://example.com">link</a>.</p><ul><li>one</li><li>two</li></ul></body></html>',
        "data.xml": "<?xml version='1.0'?><catalog><book id='1'><title>Structures</title></book></catalog>",
        "payload.json": '{"key": "value", "nested": {"list": [1, 2, 3]}}',
        "kernel.ipynb": IPYNB,
        "script.py": 'def greet(name):\n    return f"hi {name}"\n',
        "settings.yaml": "server:\n  port: 8080\n  debug: false\n",
        "essay.md": "# Markdown Doc\n\nSome *emphasis* and a [link](https://example.com).\n",
    },
    "docs": {
        "report.docx": DOCX,
        "deck.pptx": PPTX,
        "book.xlsx": XLSX,
    },
    "media": {
        "shot.png": MEDIA_PNG,
        "snap.jpg": JPEG_MAGIC + b"\xe0" + b"\x00" * 60,
        "anim.gif": GIF_MAGIC + b"\x01\x00\x01\x00\x00",
        "still.webp": WEBP_MAGIC + b"\x1a\x00\x00\x00WEBPVP8 ",
        "pixel.bmp": BMP_MAGIC + b"\x00" * 50,
        "raster.tiff": TIFF_MAGIC + b"\x00" * 50,
        "scene.heic": HEIC_MAGIC,
        "cover.avif": AVIF_MAGIC,
        "vector.svg": '<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><rect width="10" height="10"/></svg>',
    },
    "broken": {
        "alien.zip": ALIEN_ZIP,
        "shredded.docx": b"PK\x03\x04" + b"garbage not a real archive",
        "hollow.docx": _zip({"[Content_Types].xml": "<Types/>"}),
        "riddled.docx": docx_with(b'<?xml version="1.0"?><w:document><<<'),
        "latin.docx": docx_with(DOCX_BODY.replace("Quarterly Report", "Quarterly \xff\xfe").encode("utf-8")),
        "slime.xlsx": _zip({"[Content_Types].xml": "<Types/>", "xl/workbook.xml": "notxml"}),
        "manglednb.ipynb": '{"cells": [',
        "mangledjson.json": "not json at all",
        "empty.bin": b"",
        "mystery.unknown": "text but no known extension\n",
    },
}


def main() -> None:
    total = 0
    for folder, files in FILES.items():
        target = ROOT / folder
        target.mkdir(parents=True, exist_ok=True)
        for name, content in files.items():
            payload = content.encode("utf-8") if isinstance(content, str) else content
            (target / name).write_bytes(payload)
            total += 1
    sys.stdout.write(f"generated {total} fixtures in {ROOT}\n")


if __name__ == "__main__":
    main()
