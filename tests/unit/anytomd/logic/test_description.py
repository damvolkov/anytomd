"""Description: images only, labeled exactly as the convert fallback."""

import pytest

from anytomd.infra.errors import UnknownFormatError
from anytomd.logic.description import Description
from anytomd.logic.sources import InputSource


async def test_description_refuses_non_images() -> None:
    with pytest.raises(UnknownFormatError, match="'docx'"):
        Description(None).run(InputSource(None, b"x", "docx"))


async def test_description_labels(fake_vision) -> None:
    assert Description(None).run(InputSource(None, b"x", "webp")).markdown == "Image description: A red square"
    assert fake_vision.calls[0][1] == "image/webp"
