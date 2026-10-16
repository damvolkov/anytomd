"""anytomd-rs, the compiled engine: every format it supports natively."""

import os
from collections.abc import Awaitable, Callable
from pathlib import Path

from anytomd import _native
from anytomd.infra.documents import Document
from anytomd.infra.specs import ConversionSpec
from anytomd.infra.warnings import DocumentWarning

type Source = str | os.PathLike[str] | bytes
type SyncHook = Callable[[bytes, str, str], str]
type AsyncHook = Callable[[bytes, str, str], Awaitable[str]]


class NativeBackend:
    """Conversion and detection through the engine; image hooks plug OCR and vision into it."""

    __slots__ = ()

    ##### PRIVATE #####

    @staticmethod
    def _common_document(result: _native.ConversionResult) -> Document:
        return Document(
            markdown=result.markdown,
            text=result.plain_text,
            title=result.title,
            images=tuple(result.images),
            warnings=tuple(DocumentWarning(w.code, w.message, w.location) for w in result.warnings),
        )

    ############################################################

    ##### PUBLIC #####

    def convert(self, source: Source, format: str | None, spec: ConversionSpec, hook: SyncHook | None) -> Document:
        """One document through the engine."""
        match source:
            case bytes():
                result = _native.convert_bytes(
                    source,
                    format or "",
                    extract_images=spec.images,
                    extract_comments=spec.comments,
                    strict=spec.strict,
                    max_input_bytes=spec.max_input_bytes,
                    max_total_image_bytes=spec.max_image_bytes,
                    max_uncompressed_zip_bytes=spec.max_zip_bytes,
                    image_describer=hook,
                )
            case _:
                result = _native.convert_file(
                    source,
                    extract_images=spec.images,
                    extract_comments=spec.comments,
                    strict=spec.strict,
                    max_input_bytes=spec.max_input_bytes,
                    max_total_image_bytes=spec.max_image_bytes,
                    max_uncompressed_zip_bytes=spec.max_zip_bytes,
                    image_describer=hook,
                )
        return self._common_document(result)

    async def aconvert(
        self, source: Source, format: str | None, spec: ConversionSpec, hook: AsyncHook | None
    ) -> Document:
        """`convert`, off the event loop; image hooks run concurrently."""
        match source:
            case bytes():
                result = await _native.convert_bytes_async(
                    source,
                    format or "",
                    extract_images=spec.images,
                    extract_comments=spec.comments,
                    strict=spec.strict,
                    max_input_bytes=spec.max_input_bytes,
                    max_total_image_bytes=spec.max_image_bytes,
                    max_uncompressed_zip_bytes=spec.max_zip_bytes,
                    async_image_describer=hook,
                )
            case _:
                result = await _native.convert_file_async(
                    source,
                    extract_images=spec.images,
                    extract_comments=spec.comments,
                    strict=spec.strict,
                    max_input_bytes=spec.max_input_bytes,
                    max_total_image_bytes=spec.max_image_bytes,
                    max_uncompressed_zip_bytes=spec.max_zip_bytes,
                    async_image_describer=hook,
                )
        return self._common_document(result)

    def detect(self, name: str, data: bytes) -> str | None:
        """The concrete format of `data` named `name`: ZIP resolved to its Office type, families to their extension."""
        match _native.detect_format(name, data):
            case "zip":
                return _native.detect_zip_format(data)
            case "code" | "image" | "txt":
                ### The engine answers families; the extension is the concrete format it accepts back as `format=`.
                return Path(name).suffix.removeprefix(".").lower()
            case found:
                return found
