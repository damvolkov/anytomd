"""Every failure anytomd raises, rooted in `ConversionError`; the native engine raises into this tree."""


class ConversionError(Exception):
    """A document could not be converted."""


class UnknownFormatError(ConversionError):
    """No converter recognizes the format, or the call does not accept it."""


class MissingExtraError(ConversionError):
    """The format or capability needs an extra that is not installed."""


class InputTooLargeError(ConversionError):
    """The input, or an archive once decompressed, exceeds its limit."""

    def __init__(self, message: str, size: int, limit: int) -> None:
        super().__init__(message)
        self.size = size
        self.limit = limit


class MalformedDocumentError(ConversionError):
    """The document is broken beyond recovery, or a warning occurred under `strict=True`."""


class DescriptionError(ConversionError):
    """`describe` has no vision model configured, or the provider failed."""
