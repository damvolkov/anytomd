"""Type stubs for the native anytomd binding."""

import os
from collections.abc import Awaitable, Callable
from typing import Literal

type WarningCode = Literal["skipped_element", "unsupported_feature", "resource_limit_reached", "malformed_segment"]
type DescribeCallable = Callable[[bytes, str, str], str]
type AsyncDescribeCallable = Callable[[bytes, str, str], Awaitable[str]]
type DescriberArg = DescribeCallable | GeminiDescriber
type AsyncDescriberArg = AsyncDescribeCallable | AsyncGeminiDescriber

class ConvertError(Exception): ...
class UnsupportedFormatError(ConvertError): ...
class FormatNotSupportedError(ConvertError): ...

class InputTooLargeError(ConvertError):
    size: int
    limit: int

class MalformedDocumentError(ConvertError): ...
class ImageDescriptionError(ConvertError): ...
class ZipError(ConvertError): ...
class XmlError(ConvertError): ...
class SpreadsheetError(ConvertError): ...
class Utf8Error(ConvertError): ...

class ConversionWarning:
    code: WarningCode
    message: str
    location: str | None

class ConversionResult:
    markdown: str
    plain_text: str
    title: str | None
    images: list[tuple[str, bytes]]
    warnings: list[ConversionWarning]

class GeminiDescriber:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None: ...
    def __call__(self, image: bytes | bytearray, mime_type: str, prompt: str) -> str: ...

class AsyncGeminiDescriber:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None: ...

def convert_file(
    path: str | os.PathLike[str],
    *,
    extract_images: bool = False,
    extract_comments: bool = False,
    strict: bool = False,
    max_input_bytes: int = 8589934592,
    max_total_image_bytes: int = 4294967296,
    max_uncompressed_zip_bytes: int = 17179869184,
    image_describer: DescriberArg | None = None,
) -> ConversionResult: ...
def convert_bytes(
    data: bytes | bytearray,
    format: str,
    *,
    extract_images: bool = False,
    extract_comments: bool = False,
    strict: bool = False,
    max_input_bytes: int = 8589934592,
    max_total_image_bytes: int = 4294967296,
    max_uncompressed_zip_bytes: int = 17179869184,
    image_describer: DescriberArg | None = None,
) -> ConversionResult: ...
async def convert_file_async(
    path: str | os.PathLike[str],
    *,
    extract_images: bool = False,
    extract_comments: bool = False,
    strict: bool = False,
    max_input_bytes: int = 8589934592,
    max_total_image_bytes: int = 4294967296,
    max_uncompressed_zip_bytes: int = 17179869184,
    async_image_describer: AsyncDescriberArg | None = None,
) -> ConversionResult: ...
async def convert_bytes_async(
    data: bytes | bytearray,
    format: str,
    *,
    extract_images: bool = False,
    extract_comments: bool = False,
    strict: bool = False,
    max_input_bytes: int = 8589934592,
    max_total_image_bytes: int = 4294967296,
    max_uncompressed_zip_bytes: int = 17179869184,
    async_image_describer: AsyncDescriberArg | None = None,
) -> ConversionResult: ...
def detect_format(path: str | os.PathLike[str], data: bytes | bytearray) -> str | None: ...
def detect_zip_format(data: bytes | bytearray) -> str | None: ...

__version__: str
