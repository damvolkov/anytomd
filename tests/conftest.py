"""Session fixtures shared across the suite."""

import asyncio
import contextlib
import io
import itertools
import sys
import zipfile
from pathlib import Path
from typing import Final

import pytest

from anytomd.backends.registry import BackendRegistry
from anytomd.config.vision import VisionSettings
from anytomd.infra.specs import VisionSpec

RESOURCES: Final = Path(__file__).parent / "resources"

REL_NS: Final = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_NS: Final = "http://schemas.openxmlformats.org/package/2006/content-types"
DOC_NS: Final = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
REL_OFFICE: Final = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def docx_with_images(count: int, descr: str = "", image: bytes | None = None) -> bytes:
    """DOCX archive with `count` embedded images awaiting description."""
    drawings = "\n".join(
        f"""<w:p><w:r><w:drawing><wp:inline><wp:docPr descr="{descr}"/>
      <a:graphic><a:graphicData><pic:pic><pic:blipFill>
        <a:blip r:embed="rId{index + 2}"/>
      </pic:blipFill></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>"""
        for index in range(count)
    )
    body = f"""<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="{DOC_NS}" xmlns:r="{REL_OFFICE}"
    xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
    xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
    xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">
  <w:body>
    <w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Image Gallery</w:t></w:r></w:p>
    {drawings}
  </w:body>
</w:document>"""
    rels = "".join(
        f'<Relationship Id="rId{index + 2}" Type="{REL_OFFICE}/image" Target="media/image{index + 1}.png"/>'
        for index in range(count)
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            f"""<?xml version="1.0"?><Types xmlns="{CT_NS}">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Default Extension="png" ContentType="image/png"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>""",
        )
        archive.writestr(
            "_rels/.rels",
            f"""<?xml version="1.0"?><Relationships xmlns="{REL_NS}">
<Relationship Id="rId1" Type="{REL_OFFICE}/officeDocument" Target="word/document.xml"/></Relationships>""",
        )
        archive.writestr(
            "word/_rels/document.xml.rels",
            f"""<?xml version="1.0"?><Relationships xmlns="{REL_NS}">{rels}</Relationships>""",
        )
        archive.writestr("word/document.xml", body)
        archive.writestr("word/media/placeholder.png", b"\x89PNG\r\n\x1a\n" + bytes(60))
        for index in range(count):
            archive.writestr(f"word/media/image{index + 1}.png", image or _PNG)
    return buffer.getvalue()


_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000020000000200802000000fc18ed"
    "a30000002a4944415478da63b823274753c4306ac1a805a3168c5a306ac1a805"
    "a3168c5a306ac1a805a3160c150b009236603df43ffd0b0000000049454e44ae"
    "426082"
)


def text_pdf(text: str) -> bytes:
    """One-page PDF carrying `text` in its text layer, with a valid xref table."""
    stream = f"BT /F1 24 Tf 72 700 Td ({text}) Tj ET".encode()
    bodies = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    header = b"%PDF-1.4\n"
    objects = [f"{number} 0 obj\n".encode() + body + b"\nendobj\n" for number, body in enumerate(bodies, start=1)]
    offsets = list(itertools.accumulate((len(obj) for obj in objects[:-1]), initial=len(header)))
    xref = len(header) + sum(map(len, objects))
    table = f"xref\n0 {len(bodies) + 1}\n0000000000 65535 f \n".encode() + b"".join(
        f"{offset:010d} 00000 n \n".encode() for offset in offsets
    )
    trailer = f"trailer\n<< /Size {len(bodies) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return header + b"".join(objects) + table + trailer


@pytest.fixture(scope="session")
def gallery_docx() -> bytes:
    """DOCX with three describable images."""
    return docx_with_images(3)


@pytest.fixture(scope="session")
def single_image_docx() -> bytes:
    """DOCX with one describable image."""
    return docx_with_images(1)


class FakeVision:
    """A vision backend that answers from a script and records every image it was shown."""

    def __init__(self, answer: str = "A red square", error: Exception | None = None, concurrency: int = 4) -> None:
        self.answer = answer
        self.error = error
        self.concurrency = concurrency
        self.calls: list[tuple[bytes, str]] = []
        self.live = 0
        self.peak = 0
        self.closed: list[str] = []
        self.rendezvous = 0
        self.met = asyncio.Event()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.closed.append("sync")

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        self.closed.append("async")

    def describe(self, image: bytes, mime_type: str) -> str:
        self.calls.append((image, mime_type))
        match self.error:
            case Exception() as error:
                raise error
        return self.answer

    async def adescribe(self, image: bytes, mime_type: str) -> str:
        ### With `rendezvous` set, each call waits (at most 2 s) until that many are in flight: overlap proven, not timed.
        self.live += 1
        self.peak = max(self.peak, self.live)
        _ = self.live >= self.rendezvous and self.met.set()
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(self.met.wait(), 2)
        self.live -= 1
        return self.describe(image, mime_type)


@pytest.fixture
def fake_vision(monkeypatch) -> FakeVision:
    """The vision fallback wired to a scripted backend, OCR left as installed."""
    vision = FakeVision()
    monkeypatch.setattr(BackendRegistry, "describer", lambda self, spec: vision)
    monkeypatch.setattr(BackendRegistry, "require", lambda self, spec: vision)
    return vision


@pytest.fixture
def missing_extra(monkeypatch):
    """Uninstaller: makes a third-party library of an extra unimportable for one test."""

    def _remove(library: str) -> None:
        monkeypatch.setitem(sys.modules, library, None)
        _ = [
            monkeypatch.delitem(sys.modules, module, raising=False)
            for module in ("anytomd.backends.liteparse", "anytomd.backends.openai", "anytomd.config.vision")
        ]

    return _remove


@pytest.fixture(scope="session")
def vision_spec() -> VisionSpec:
    """The real vision model from ANYTOMD_VISION_*, or skip."""
    spec = VisionSettings().spec()
    return spec or pytest.skip("no vision model configured (ANYTOMD_VISION_MODEL)")


@pytest.fixture(scope="session")
def resources() -> Path:
    """Root of the fixture tree."""
    return RESOURCES


@pytest.fixture(scope="session")
def path_of(resources: Path):
    """Resolver returning the Path of a uniquely named fixture by filename."""

    def _resolve(filename: str) -> Path:
        found = list(resources.rglob(filename))
        assert len(found) == 1, f"{filename!r} is not unique in the resource tree"
        return found[0]

    return _resolve


@pytest.fixture(scope="session")
def raw(path_of):
    """Reader returning the bytes of a uniquely named fixture by filename."""

    def _read(filename: str) -> bytes:
        return path_of(filename).read_bytes()

    return _read
