"""Document: frozen, with empty defaults."""

import dataclasses

import pytest

from anytomd.infra.documents import Document


async def test_documents_defaults() -> None:
    document = Document(markdown="# x", text="x")
    assert (document.title, document.images, document.warnings, document.pages) == (None, (), (), None)


async def test_documents_frozen() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        Document(markdown="", text="").pages = 1  # ty: ignore[invalid-assignment]
