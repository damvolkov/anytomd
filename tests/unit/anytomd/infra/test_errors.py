"""The error tree: one root, one meaning per class."""

import pytest

import anytomd as ad

CHILDREN = [
    ad.UnknownFormatError,
    ad.MissingExtraError,
    ad.InputTooLargeError,
    ad.MalformedDocumentError,
    ad.DescriptionError,
]


@pytest.mark.parametrize("error", CHILDREN, ids=[e.__name__ for e in CHILDREN])
async def test_errors_root(error) -> None:
    assert issubclass(error, ad.ConversionError)


async def test_errors_input_too_large_attributes() -> None:
    error = ad.InputTooLargeError("too big", 10, 4)
    assert (str(error), error.size, error.limit) == ("too big", 10, 4)
