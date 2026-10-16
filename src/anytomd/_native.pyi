"""Type stubs for the native anytomd binding."""

import os
from collections.abc import Awaitable, Callable
from typing import Literal

type WarningCode = Literal["skipped_element", "unsupported_feature", "resource_limit_reached", "malformed_segment"]
type DescribeCallable = Callable[[bytes, str, str], str]
type AsyncDescribeCallable = Callable[[bytes, str, str], Awaitable[str]]

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

def convert_file(
    path: str | os.PathLike[str],
    *,
    extract_images: bool = False,
    extract_comments: bool = False,
    strict: bool = False,
    max_input_bytes: int = 8589934592,
    max_total_image_bytes: int = 4294967296,
    max_uncompressed_zip_bytes: int = 17179869184,
    image_describer: DescribeCallable | None = None,
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
    image_describer: DescribeCallable | None = None,
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
    async_image_describer: AsyncDescribeCallable | None = None,
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
    async_image_describer: AsyncDescribeCallable | None = None,
) -> ConversionResult: ...
def detect_format(path: str | os.PathLike[str], data: bytes | bytearray) -> str | None: ...
def detect_zip_format(data: bytes | bytearray) -> str | None: ...

ENGINE_VERSION: str
