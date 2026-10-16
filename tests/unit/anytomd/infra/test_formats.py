"""Formats: every image extension maps to an image MIME type."""

from anytomd.infra.formats import DESCRIPTION_LABEL, IMAGE_MIMES, PDF


async def test_formats_images_are_image_mimes() -> None:
    assert all(mime.startswith("image/") for mime in IMAGE_MIMES.values())
    assert PDF not in IMAGE_MIMES
    assert DESCRIPTION_LABEL == "Image description: "
