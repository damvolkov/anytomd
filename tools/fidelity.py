"""Text recovery by format: one known passage, generated into every format anytomd converts, scored after conversion.

`make fidelity` re-measures, compares against the committed baseline and refreshes the chart.
"""

import argparse
import difflib
import json
import re
import sys
import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Final

from liteparse import LiteParse
from tools.gen_samples import (
    A_NS,
    DOC_NS,
    PPTX_NS,
    XLS_NS,
    XML_DECL,
    docx_with,
    pdf_with,
    pptx_with,
    xlsx_with,
)

import anytomd

ROOT: Final = Path(__file__).resolve().parent.parent
BASELINE: Final = ROOT / "docs" / "fidelity.json"
CHART: Final = ROOT / "docs" / "assets" / "fidelity.svg"
MINI: Final = ROOT / "docs" / "assets" / "fidelity-mini.svg"
TOLERANCE: Final = 0.02

CORPUS: Final = (
    "The quarterly review opened with the revenue story and closed with the hiring plan for next spring.",
    "Six teams shipped forty small features while the platform group rebuilt the ingestion pipeline twice.",
    "Costs fell because the old search cluster went quiet and the new one answered faster with fewer machines.",
    "The board asked for clearer charts, so every report now begins with one honest number and one plain sentence.",
    "Training ended the week the first customer dashboard went live, and support tickets dropped by a third.",
    "Nobody predicted the winter storm, yet the backup site carried the traffic without a single lost message.",
)

TOKENS: Final = tuple(word.lower() for word in re.findall(r"[A-Za-z]+", " ".join(CORPUS)))


##### BUILDERS #####


def _document() -> bytes:
    paragraphs = "".join(f'<w:p><w:r><w:t xml:space="preserve">{line}</w:t></w:r></w:p>' for line in CORPUS)
    return docx_with(f'{XML_DECL}<w:document xmlns:w="{DOC_NS}"><w:body>{paragraphs}</w:body></w:document>')


def _presentation() -> bytes:
    lines = "".join(f"<a:p><a:r><a:t>{line}</a:t></a:r></a:p>" for line in CORPUS)
    slide = f"""{XML_DECL}
<p:sld xmlns:p="{PPTX_NS}" xmlns:a="{A_NS}">
  <p:cSld><p:spTree>
    <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
    <p:grpSpPr/>
    <p:sp>
      <p:nvSpPr><p:cNvPr id="2" name="Body"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
      <p:txBody><a:bodyPr/><a:lstStyle/>{lines}</p:txBody>
    </p:sp>
  </p:spTree></p:cSld>
</p:sld>"""
    return pptx_with(slide)


def _workbook() -> bytes:
    rows = "".join(
        f'<row r="{index}"><c r="A{index}" t="inlineStr"><is><t>{line}</t></is></c></row>'
        for index, line in enumerate(CORPUS, start=1)
    )
    return xlsx_with(f'{XML_DECL}<worksheet xmlns="{XLS_NS}"><sheetData>{rows}</sheetData></worksheet>')


def _portable() -> bytes:
    return pdf_with(list(CORPUS))


def _webpage() -> bytes:
    blocks = "".join(f"<p>{line}</p>" for line in CORPUS)
    return f"<html><head><title>Review</title></head><body>{blocks}</body></html>".encode()


def _spreadsheet() -> bytes:
    return "".join(f'"{line}"\n' for line in CORPUS).encode()


def _payload() -> bytes:
    return json.dumps({"lines": list(CORPUS)}).encode()


def _markup() -> bytes:
    lines = "".join(f"<line>{line}</line>" for line in CORPUS)
    return f'<?xml version="1.0"?><passage>{lines}</passage>'.encode()


def _notebook() -> bytes:
    source = [f"{line}\n" for line in CORPUS]
    cells = [{"cell_type": "markdown", "metadata": {}, "source": source}]
    return json.dumps({"cells": cells, "metadata": {}, "nbformat": 4, "nbformat_minor": 5}).encode()


def _plain() -> bytes:
    return "".join(f"{line}\n" for line in CORPUS).encode()


def _settings() -> bytes:
    return ("passage: |\n  " + "\n  ".join(CORPUS)).encode()


def _manifest() -> bytes:
    return ('text = """\n' + "".join(f"{line}\n" for line in CORPUS) + '"""\n').encode()


def _catalog() -> bytes:
    entries = "".join(f"line{index} = {line}\n" for index, line in enumerate(CORPUS))
    return f"[passage]\n{entries}".encode()


def _source() -> bytes:
    return ('"""Review notes."""\n\n' + "".join(f"# {line}\n" for line in CORPUS)).encode()


def _vector() -> bytes:
    spans = "".join(f'<text x="20" y="{40 + 34 * index}">{line}</text>' for index, line in enumerate(CORPUS))
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="900" height="260">{spans}</svg>'
    return f'<?xml version="1.0" encoding="UTF-8" standalone="no"?>{svg}'.encode()


def _pixels() -> bytes:
    """The passage as raster: pdfium renders the PDF fixture, so the OCR rows need no image library."""
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "passage.pdf"
        page.write_bytes(pdf_with(list(CORPUS)))
        return LiteParse().screenshot(page)[0].image_bytes


##### MATRIX #####

Row = tuple[str, str, Callable[[], bytes], str, bool]

ROWS: Final[tuple[Row, ...]] = (
    ("Word", "Office", _document, "docx", True),
    ("PowerPoint", "Office", _presentation, "pptx", True),
    ("Excel", "Office", _workbook, "xlsx", True),
    ("PDF", "PDF", _portable, "pdf", True),
    ("HTML", "Web and data", _webpage, "html", True),
    ("CSV", "Web and data", _spreadsheet, "csv", True),
    ("JSON", "Web and data", _payload, "json", True),
    ("XML", "Web and data", _markup, "xml", True),
    ("Jupyter", "Web and data", _notebook, "ipynb", True),
    ("Text", "Text", _plain, "txt", True),
    ("Markdown", "Text", _plain, "md", True),
    ("reStructuredText", "Text", _plain, "rst", True),
    ("Log", "Text", _plain, "log", True),
    ("YAML", "Text", _settings, "yaml", True),
    ("TOML", "Text", _manifest, "toml", True),
    ("INI", "Text", _catalog, "ini", True),
    ("Code", "Code", _source, "py", True),
    ("Image + OCR", "Image with OCR", _pixels, "png", True),
    ("Image, no OCR", "Image without OCR", _pixels, "png", False),
    ("SVG text", "Image without OCR", _vector, "svg", True),
)


##### SCORING #####


def recovery(output: str) -> float:
    """The share of the known words the conversion gave back, counting order-preserving matches."""
    found = tuple(word.lower() for word in re.findall(r"[A-Za-z]+", output))
    blocks = difflib.SequenceMatcher(None, TOKENS, found, autojunk=False).get_matching_blocks()
    return sum(block.size for block in blocks) / len(TOKENS)


def measure() -> dict[str, float | None]:
    """Recovery per format; None when the document refuses to convert."""
    scores: dict[str, float | None] = {}
    for label, _, build, format, ocr in ROWS:
        try:
            scores[label] = recovery(anytomd.convert(build(), format=format, ocr=ocr).text)
        except anytomd.ConversionError:
            scores[label] = None
    return scores


def compare(scores: dict[str, float | None], baseline: dict[str, float | None]) -> tuple[str, ...]:
    """Regression lines against the committed baseline; a format absent from either side is noise, not failure."""
    return tuple(
        f"{name}: {before:.0%} -> {now:.0%}"
        for name, now in scores.items()
        if now is not None and name in baseline and (before := baseline[name]) is not None and now < before - TOLERANCE
    )


##### OUTPUT #####


def chart(items: Mapping[str, float | None], *, step: int, left: int, width: int, note: str) -> str:
    """One horizontal bar per entry: recovered share of the passage, in percent."""
    height = step * len(items) + 60
    head = '<text x="14" y="26" font-family="sans-serif" font-size="14" font-weight="bold" fill="#333">Text recovered (%)</text>'
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{left + width + 80}" height="{height}" role="img">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        head,
    ]
    for index, (name, score) in enumerate(items.items()):
        y, ratio = 44 + index * step, score or 0.0
        tone = "#c9cbd1" if score is None else "#8f3b1b"
        value = "n/a" if score is None else f"{score:.0%}"
        parts.append(
            f'<text x="{left - 10}" y="{y + step // 2 - 4}" text-anchor="end" font-family="sans-serif" '
            f'font-size="12.5" fill="#333">{name}</text>',
        )
        parts.append(f'<rect x="{left}" y="{y}" width="{width}" height="{step - 14}" rx="3" fill="#ece5df"/>')
        parts.append(
            f'<rect x="{left}" y="{y}" width="{width * ratio:.0f}" height="{step - 14}" rx="3" fill="{tone}"/>'
        )
        parts.append(
            f'<text x="{left + width * ratio + 8:.0f}" y="{y + step // 2 - 4}" font-family="sans-serif" '
            f'font-size="12" fill="#555">{value}</text>',
        )
    footer = (
        f'<text x="{left}" y="{height - 12}" font-family="sans-serif" font-size="11" fill="#777">'
        f"{len(TOKENS)}-word passage · anytomd[full] · {note}</text>"
    )
    parts += [footer, "</svg>"]
    return "\n".join(parts) + "\n"


def families(scores: Mapping[str, float | None]) -> dict[str, float | None]:
    """Worst recovery per family, for the compact chart: a group is only as good as its weakest format."""
    grouped: dict[str, float | None] = {}
    for label, family, _, _, _ in ROWS:
        score = scores[label]
        previous = grouped.get(family)
        grouped[family] = score if previous is None or (score is not None and score < previous) else previous
    return grouped


def report(scores: dict[str, float | None]) -> None:
    sys.stdout.write(
        "".join(f"{name:<20} {'n/a' if score is None else f'{score:.1%}'}\n" for name, score in scores.items())
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure text recovery per format.")
    parser.add_argument("--update", action="store_true", help="rewrite the baseline and the charts")
    arguments = parser.parse_args()

    scores = measure()
    baseline = json.loads(BASELINE.read_text()) if BASELINE.exists() else {}
    regressions = compare(scores, baseline)
    report(scores)
    if arguments.update:
        BASELINE.write_text(json.dumps(scores, indent=2) + "\n")
        CHART.parent.mkdir(parents=True, exist_ok=True)
        CHART.write_text(chart(scores, step=40, left=200, width=540, note="one corpus per format"))
        MINI.write_text(chart(families(scores), step=34, left=170, width=420, note="worst format per family"))
        sys.stdout.write(
            f"updated {BASELINE.relative_to(ROOT)}, {CHART.relative_to(ROOT)} and {MINI.relative_to(ROOT)}\n"
        )
    sys.stdout.write("".join(f"REGRESSION  {line}\n" for line in regressions))
    return 1 if regressions else 0


if __name__ == "__main__":
    raise SystemExit(main())
