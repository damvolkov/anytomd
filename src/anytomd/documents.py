"""Documents produced by the optional capabilities."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PdfDocument:
    """A PDF read to Markdown: every page joined in reading order, with its count and page-level warnings."""

    markdown: str
    pages: int
    warnings: tuple[str, ...] = ()
