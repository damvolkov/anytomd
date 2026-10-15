"""Session fixtures shared across the suite."""

import base64
import io
import json
import os
import re
import urllib.error
import urllib.request
import zipfile
from types import SimpleNamespace
from typing import Final

import pytest

REL_NS: Final = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_NS: Final = "http://schemas.openxmlformats.org/package/2006/content-types"
DOC_NS: Final = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
REL_OFFICE: Final = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

LLM_BASE_URL: Final = os.environ.get(
    "ANYTOMD_LLM_BASE_URL", "https://token-plan.ap-southeast-1.maas.aliyuncs.com/apps/anthropic/v1"
)
LLM_MODEL: Final = os.environ.get("ANYTOMD_LLM_MODEL", "qwen3.8-flash")
LLM_API_KEY: Final = os.environ.get("ANYTOMD_LLM_API_KEY", os.environ.get("ALIBABA_TOKEN_PLAN_KEY", ""))
LLM_AVAILABLE: Final = bool(LLM_API_KEY)


def docx_with_images(count: int, descr: str = "") -> bytes:
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
            archive.writestr(f"word/media/image{index + 1}.png", _PNG)
    return buffer.getvalue()


_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000020000000200802000000fc18ed"
    "a30000002a4944415478da63b823274753c4306ac1a805a3168c5a306ac1a805"
    "a3168c5a306ac1a805a3160c150b009236603df43ffd0b0000000049454e44ae"
    "426082"
)


def llm_describe(image: bytes, mime_type: str, prompt: str) -> str:
    """Description from the configured OpenAI-compatible provider (stdlib HTTP only)."""
    encoded = _base64(image)
    if "/anthropic" in LLM_BASE_URL:
        body = {
            "model": LLM_MODEL,
            "max_tokens": 128,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": mime_type, "data": encoded}},
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        }
        request = urllib.request.Request(
            f"{LLM_BASE_URL}/messages",
            data=_json_bytes(body),
            headers={
                "x-api-key": LLM_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
        )
        payload = _post(request)
        text = "".join(block.get("text", "") for block in payload["content"] if block.get("type") == "text")
    else:
        body = {
            "model": LLM_MODEL,
            "max_tokens": 128,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{encoded}"}},
                    ],
                }
            ],
        }
        request = urllib.request.Request(
            f"{LLM_BASE_URL}/chat/completions",
            data=_json_bytes(body),
            headers={"Authorization": f"Bearer {LLM_API_KEY}", "content-type": "application/json"},
        )
        payload = _post(request)
        text = payload["choices"][0]["message"]["content"]
    return str(text).strip()


def _base64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def _json_bytes(body: dict) -> bytes:
    return json.dumps(body).encode()


def _post(request: urllib.request.Request) -> dict:
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", "replace")[:300]
        error.close()
        msg = f"provider HTTP {error.code}: {body}"
        raise RuntimeError(msg) from error


@pytest.fixture(scope="session")
def gallery_docx() -> bytes:
    """DOCX with three describable images."""
    return docx_with_images(3)


@pytest.fixture(scope="session")
def single_image_docx() -> bytes:
    """DOCX with one describable image."""
    return docx_with_images(1)


@pytest.fixture(scope="session")
def llm():
    """Configured OpenAI-compatible provider, or skip when no key is present."""
    if not LLM_AVAILABLE:
        pytest.skip("no LLM provider key configured")
    return SimpleNamespace(describe=llm_describe, model=LLM_MODEL, base_url=LLM_BASE_URL)


@pytest.fixture(scope="session")
def path_of(resources):
    """Resolver returning the Path of a uniquely named fixture by filename."""

    def _resolve(filename: str):
        found = list(resources.walk(re.compile(r"\A" + re.escape(filename) + r"\Z")))
        assert len(found) == 1, f"{filename!r} is not unique in the resource tree"
        return found[0]

    return _resolve


@pytest.fixture(scope="session")
def raw(path_of):
    """Reader returning the bytes of a uniquely named fixture by filename."""

    def _read(filename: str) -> bytes:
        return path_of(filename).read_bytes()

    return _read
