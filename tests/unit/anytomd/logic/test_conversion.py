"""Conversion: each format to its route."""

import pytest

from anytomd.infra.routes import Route
from anytomd.infra.specs import ConversionSpec
from anytomd.logic.conversion import Conversion
from anytomd.logic.sources import InputSource


@pytest.mark.parametrize(
    ("format", "route"),
    [("pdf", Route.PDF), ("png", Route.IMAGE), ("jpeg", Route.IMAGE), ("docx", Route.NATIVE), ("", Route.NATIVE)],
    ids=["pdf", "png", "jpeg", "docx", "unknown"],
)
async def test_conversion_route(format, route) -> None:
    assert Conversion(ConversionSpec())._common_route(InputSource(None, b"x", format)) is route
