"""Errors of the optional capabilities, rooted in the engine's own `ConvertError`."""

from anytomd._native import ConvertError


class PdfError(ConvertError):
    """liteparse refused the PDF: bytes it cannot read, a password it lacks, a structure beyond recovery."""
