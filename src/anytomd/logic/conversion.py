"""One conversion: route the source to the engine, the image rule or the PDF reader."""

import dataclasses
import logging
from contextlib import nullcontext

from anytomd.backends.base import Describer
from anytomd.backends.native import NativeBackend
from anytomd.backends.registry import BackendRegistry
from anytomd.infra.documents import Document
from anytomd.infra.errors import InputTooLargeError
from anytomd.infra.formats import IMAGE_MIMES, PDF
from anytomd.infra.routes import Route
from anytomd.infra.specs import ConversionSpec
from anytomd.logic.fallback import KEEP_ALT, ImageFallback
from anytomd.logic.sources import InputSource

logger = logging.getLogger(__name__)

DEFAULT_CONCURRENCY = 4


class Conversion:
    """Applies one `ConversionSpec` to one source."""

    __slots__ = ("_native", "_registry", "_spec")

    ##### PRIVATE #####

    def _common_route(self, source: InputSource) -> Route:
        route = Route.PDF if source.format == PDF else Route.IMAGE if source.format in IMAGE_MIMES else Route.NATIVE
        logger.debug("converting %s as %r through the %s route", source.path or "bytes", source.format, route)
        return route

    def _common_fallback(self, describer: Describer | None) -> ImageFallback:
        return ImageFallback(
            self._registry.recognizer(ocr=self._spec.ocr),
            describer,
            strict=self._spec.strict,
            concurrency=describer.concurrency if describer else DEFAULT_CONCURRENCY,
        )

    def _common_bounded(self, source: InputSource) -> InputSource:
        size, limit = source.size(), self._spec.max_input_bytes
        msg = f"input too large: {size} bytes exceeds limit of {limit} bytes"
        return source if size <= limit else self._common_raise(InputTooLargeError(msg, size, limit))

    @staticmethod
    def _common_raise(error: Exception) -> InputSource:
        raise error

    @staticmethod
    def _common_clean(document: Document) -> Document:
        return dataclasses.replace(document, warnings=tuple(w for w in document.warnings if KEEP_ALT not in w.message))

    @staticmethod
    def _common_image(markdown: str, warnings: tuple) -> Document:
        return Document(markdown=markdown, text=markdown, warnings=warnings)

    def _run_native(self, source: InputSource, fallback: ImageFallback) -> Document:
        hook = fallback.hook if fallback.active else None
        document = self._native.convert(source.data or source.path or b"", source.format, self._spec, hook)
        return self._common_clean(document)

    def _run_image(self, source: InputSource, fallback: ImageFallback) -> Document:
        data = self._common_bounded(source).load()
        return (
            self._common_image(*fallback.resolve(data, IMAGE_MIMES[source.format]))
            if fallback.active
            else self._run_native(source, fallback)
        )

    def _run_pdf(self, source: InputSource) -> Document:
        reader = self._registry.reader(ocr=self._spec.ocr)
        logger.debug("reading PDF with liteparse (ocr=%s)", self._spec.ocr)
        return reader.read(self._common_bounded(source).data or source.path or b"")

    async def _arun_native(self, source: InputSource, fallback: ImageFallback) -> Document:
        hook = fallback.ahook if fallback.active else None
        document = await self._native.aconvert(source.data or source.path or b"", source.format, self._spec, hook)
        return self._common_clean(document)

    async def _arun_image(self, source: InputSource, fallback: ImageFallback) -> Document:
        data = await self._common_bounded(source).aload()
        return (
            self._common_image(*await fallback.aresolve(data, IMAGE_MIMES[source.format]))
            if fallback.active
            else await self._arun_native(source, fallback)
        )

    async def _arun_pdf(self, source: InputSource) -> Document:
        reader = self._registry.reader(ocr=self._spec.ocr)
        logger.debug("reading PDF with liteparse (ocr=%s)", self._spec.ocr)
        return await reader.aread(self._common_bounded(source).data or source.path or b"")

    ############################################################

    ##### PUBLIC #####

    def __init__(self, spec: ConversionSpec) -> None:
        self._spec = spec
        self._native = NativeBackend()
        self._registry = BackendRegistry()

    def run(self, source: InputSource) -> Document:
        """The document, converted by whichever route its format takes."""
        route = self._common_route(source)
        describer = self._registry.describer(self._spec.vision) if route is not Route.PDF else None
        with describer or nullcontext():
            match route:
                case Route.PDF:
                    return self._run_pdf(source)
                case Route.IMAGE:
                    return self._run_image(source, self._common_fallback(describer))
                case _:
                    return self._run_native(source, self._common_fallback(describer))

    async def arun(self, source: InputSource) -> Document:
        """`run`, off the event loop; a document's images are resolved concurrently."""
        route = self._common_route(source)
        describer = self._registry.describer(self._spec.vision) if route is not Route.PDF else None
        async with describer or nullcontext():
            match route:
                case Route.PDF:
                    return await self._arun_pdf(source)
                case Route.IMAGE:
                    return await self._arun_image(source, self._common_fallback(describer))
                case _:
                    return await self._arun_native(source, self._common_fallback(describer))
