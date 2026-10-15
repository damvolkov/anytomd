"""Integration: the capability stack end to end — real liteparse OCR, real vision fallback.

The vision provider defaults to an OpenAI-compatible endpoint and honours
ANYTOMD_VLM_BASE_URL / ANYTOMD_VLM_MODEL / ANYTOMD_VLM_API_KEY (or ALIBABA_TOKEN_PLAN_KEY).
Skipped without a key; the real-engine OCR and PDF tests need no network and live in the unit suite.
"""

import os
from types import SimpleNamespace

import pytest

import anytomd

pytestmark = [pytest.mark.integration, pytest.mark.timeout(180)]

VLM_BASE_URL: str = os.environ.get(
    "ANYTOMD_VLM_BASE_URL", "https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1"
)
VLM_MODEL: str = os.environ.get("ANYTOMD_VLM_MODEL", "qwen3.8-flash")
VLM_API_KEY: str = os.environ.get("ANYTOMD_VLM_API_KEY", os.environ.get("ALIBABA_TOKEN_PLAN_KEY", ""))


def _alts(markdown: str) -> list[str]:
    return [line.split("![", 1)[1].split("](", 1)[0] for line in markdown.splitlines() if "![" in line]


@pytest.fixture(scope="module")
def vlm():
    if not VLM_API_KEY:
        pytest.skip("no vision provider key configured")
    return SimpleNamespace(base_url=VLM_BASE_URL, model=VLM_MODEL, api_key=VLM_API_KEY)


def test_composite_falls_back_to_vision_when_ocr_finds_no_text(vlm, gallery_docx):
    describer = anytomd.ImageDescriber(model=vlm.model, api_base=vlm.base_url, api_key=vlm.api_key)
    try:
        result = anytomd.convert_bytes(gallery_docx, "docx", image_describer=describer)
    finally:
        describer.close()
    alts = _alts(result.markdown)
    assert result.warnings == []
    assert len(alts) == 3
    assert all(len(alt) > 10 for alt in alts)


async def test_async_composite_falls_back_to_vision_under_its_gate(vlm, gallery_docx):
    describer = anytomd.AsyncImageDescriber(
        model=vlm.model, api_base=vlm.base_url, api_key=vlm.api_key, max_concurrency=1
    )
    try:
        result = await anytomd.convert_bytes_async(gallery_docx, "docx", async_image_describer=describer)
    finally:
        await describer.aclose()
    alts = _alts(result.markdown)
    assert result.warnings == []
    assert len(alts) == 3
    assert all(len(alt) > 10 for alt in alts)
