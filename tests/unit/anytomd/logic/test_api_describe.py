"""describe / adescribe: vision only, images only, the same markdown convert writes on fallback."""

import pytest

import anytomd as ad


async def test_describe_labels_the_description(path_of, fake_vision) -> None:
    document = ad.describe(path_of("shot.png"))
    assert document.markdown == document.text == "Image description: A red square"


async def test_describe_matches_the_convert_fallback(path_of, fake_vision) -> None:
    assert ad.describe(path_of("shot.png")) == ad.convert(path_of("shot.png"))


async def test_describe_text_image_is_described_not_transcribed(path_of, fake_vision) -> None:
    assert ad.describe(path_of("real_photo.png")).markdown == "Image description: A red square"
    assert fake_vision.calls


async def test_describe_bytes(raw, fake_vision) -> None:
    assert ad.describe(raw("snap.jpg"), format="jpg").markdown.startswith("Image description:")
    assert fake_vision.calls[0][1] == "image/jpeg"


async def test_adescribe(path_of, fake_vision) -> None:
    assert (await ad.adescribe(path_of("shot.png"))).markdown == "Image description: A red square"


@pytest.mark.parametrize("fixture", ["report.docx", "notes.txt"], ids=["docx", "txt"])
async def test_describe_refuses_non_images(path_of, fake_vision, fixture) -> None:
    with pytest.raises(ad.UnknownFormatError, match="images only"):
        ad.describe(path_of(fixture))


async def test_describe_provider_failure_raises(path_of, fake_vision) -> None:
    fake_vision.error = ad.DescriptionError("vision model 'v' failed: 429")
    with pytest.raises(ad.DescriptionError, match="429"):
        ad.describe(path_of("shot.png"))


async def test_describe_without_a_model(path_of, monkeypatch) -> None:
    monkeypatch.delenv("ANYTOMD_VISION_MODEL", raising=False)
    with pytest.raises(ad.DescriptionError, match="ANYTOMD_VISION_MODEL"):
        ad.describe(path_of("shot.png"))


async def test_adescribe_without_a_model(path_of, monkeypatch) -> None:
    monkeypatch.delenv("ANYTOMD_VISION_MODEL", raising=False)
    with pytest.raises(ad.DescriptionError):
        await ad.adescribe(path_of("shot.png"))


async def test_describe_without_the_extra(path_of, missing_extra) -> None:
    missing_extra("openai")
    with pytest.raises(ad.MissingExtraError, match=r"anytomd\[vlm\]"):
        ad.describe(path_of("shot.png"))
