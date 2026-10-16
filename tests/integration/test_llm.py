"""Integration: a real OpenAI-compatible vision model behind the fallback and describe.

Configured through ANYTOMD_VISION_MODEL / ANYTOMD_VISION_BASE_URL / ANYTOMD_VISION_API_KEY; skipped without a model.
"""

from dataclasses import replace

import pytest

import anytomd as ad

pytestmark = [pytest.mark.integration, pytest.mark.timeout(180)]


def _alts(markdown: str) -> list[str]:
    return [line.split("![", 1)[1].split("](", 1)[0] for line in markdown.splitlines() if "![" in line]


async def test_llm_convert_image_falls_back_to_description(path_of, vision_spec) -> None:
    document = ad.convert(path_of("shot.png"), vision=vision_spec)
    assert document.markdown.startswith("Image description: ")
    assert len(document.markdown) > len("Image description: ") + 3


async def test_llm_convert_text_image_stays_ocr(path_of, vision_spec) -> None:
    assert ad.convert(path_of("real_photo.png"), vision=vision_spec).markdown == "This is just\nan example."


async def test_llm_convert_embedded_images(gallery_docx, vision_spec) -> None:
    document = ad.convert(gallery_docx, format="docx", vision=vision_spec)
    assert document.warnings == ()
    assert all(alt.startswith("Image description: ") for alt in _alts(document.markdown))


async def test_llm_aconvert_embedded_images_bounded(gallery_docx, vision_spec) -> None:
    document = await ad.aconvert(gallery_docx, format="docx", vision=replace(vision_spec, concurrency=1))
    assert document.warnings == ()
    assert len(_alts(document.markdown)) == 3


async def test_llm_describe_text_image_is_a_description(path_of, vision_spec) -> None:
    document = ad.describe(path_of("real_photo.png"), vision=vision_spec)
    assert document.markdown.startswith("Image description: ")
    assert document.markdown != "Image description: This is just an example."


async def test_llm_adescribe(path_of, vision_spec) -> None:
    assert (await ad.adescribe(path_of("shot.png"), vision=vision_spec)).markdown.startswith("Image description: ")
