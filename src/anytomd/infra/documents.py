"""The value every conversion returns."""

from dataclasses import dataclass

from anytomd.infra.warnings import DocumentWarning


@dataclass(frozen=True, slots=True)
class Document:
    """A converted document: Markdown, the same content as plain text, and what the conversion found."""

    markdown: str
    text: str
    title: str | None = None
    images: tuple[tuple[str, bytes], ...] = ()
    warnings: tuple[DocumentWarning, ...] = ()
    pages: int | None = None
