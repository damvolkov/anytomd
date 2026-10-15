"""Integration: real image description through the configured OpenAI-compatible provider.

The provider defaults to an Alibaba token-plan endpoint (Anthropic-compatible
messages API) and honours ANYTOMD_LLM_BASE_URL / ANYTOMD_LLM_API_KEY / ANYTOMD_LLM_MODEL
for any other OpenAI-compatible gateway. Skipped without a key.
"""

import asyncio

import pytest

import anytomd

pytestmark = [pytest.mark.integration, pytest.mark.timeout(180)]


def _alts(markdown: str) -> list[str]:
    return [line.split("![", 1)[1].split("](", 1)[0] for line in markdown.splitlines() if "![" in line]


def test_sync_describer_uses_provider(llm, gallery_docx):
    result = anytomd.convert_bytes(gallery_docx, "docx", extract_images=True, image_describer=llm.describe)
    alts = _alts(result.markdown)
    assert result.warnings == []
    assert len(alts) == 3
    assert all(alt not in ("image1.png", "image2.png", "image3.png") for alt in alts)


def test_async_describer_uses_provider(llm, gallery_docx):
    ### Provider burst limits answer 429 to simultaneous calls; concurrency itself is covered by the unit suite.
    gate = asyncio.Semaphore(1)

    async def describer(image: bytes, mime_type: str, prompt: str) -> str:
        async with gate:
            return await asyncio.to_thread(llm.describe, image, mime_type, prompt)

    result = asyncio.run(
        anytomd.convert_bytes_async(gallery_docx, "docx", extract_images=True, async_image_describer=describer)
    )
    alts = _alts(result.markdown)
    assert result.warnings == []
    assert len(alts) == 3
    assert all(alt not in ("image1.png", "image2.png", "image3.png") for alt in alts)


def test_gemini_describer_call_reports_provider_rejection():
    describer = anytomd.GeminiDescriber("invalid-key")
    with pytest.raises(anytomd.ImageDescriptionError, match="Gemini"):
        describer(b"\x89PNG\r\n\x1a\n", "image/png", "Describe this image.")


def test_descriptions_carry_visual_content(llm, single_image_docx):
    result = anytomd.convert_bytes(single_image_docx, "docx", extract_images=True, image_describer=llm.describe)
    lowered = result.markdown.lower()
    assert any(word in lowered for word in ("red", "square", "color", "solid", "image", "green", "blue"))
