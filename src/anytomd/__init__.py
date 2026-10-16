"""anytomd: any document to clean Markdown, on the anytomd-rs engine.

Declared `__init__` exception (tax-py-naming): the distribution's public surface is the package itself,
`import anytomd as ad; ad.convert(...)`, so this module re-exports `logic.api` and the infra contracts. Nothing else.
"""

from importlib.metadata import version

from anytomd._native import ENGINE_VERSION
from anytomd.infra.documents import Document
from anytomd.infra.errors import (
    ConversionError,
    DescriptionError,
    InputTooLargeError,
    MalformedDocumentError,
    MissingExtraError,
    UnknownFormatError,
)
from anytomd.infra.specs import VisionSpec
from anytomd.infra.warnings import DocumentWarning
from anytomd.logic.api import aconvert, adescribe, adetect, convert, describe, detect

__version__ = version("anytomd")

__all__ = [
    "ENGINE_VERSION",
    "ConversionError",
    "DescriptionError",
    "Document",
    "DocumentWarning",
    "InputTooLargeError",
    "MalformedDocumentError",
    "MissingExtraError",
    "UnknownFormatError",
    "VisionSpec",
    "__version__",
    "aconvert",
    "adescribe",
    "adetect",
    "convert",
    "describe",
    "detect",
]
