"""An image described by the vision model, as `convert` writes it when it falls back."""

import logging

from anytomd.backends.registry import BackendRegistry
from anytomd.infra.documents import Document
from anytomd.infra.errors import UnknownFormatError
from anytomd.infra.formats import DESCRIPTION_LABEL, IMAGE_MIMES
from anytomd.infra.specs import VisionSpec
from anytomd.logic.sources import InputSource

logger = logging.getLogger(__name__)


class Description:
    """Vision only: no OCR, so an image full of text is described, not transcribed."""

    __slots__ = ("_registry", "_vision")

    ##### PRIVATE #####

    @staticmethod
    def _common_mime(source: InputSource) -> str:
        return IMAGE_MIMES.get(source.format) or Description._common_refuse(source.format)

    @staticmethod
    def _common_refuse(format: str) -> str:
        msg = f"describe accepts images only, got {format!r}"
        raise UnknownFormatError(msg)

    @staticmethod
    def _common_document(description: str) -> Document:
        markdown = f"{DESCRIPTION_LABEL}{description}"
        return Document(markdown=markdown, text=markdown)

    ############################################################

    ##### PUBLIC #####

    def __init__(self, vision: VisionSpec | None) -> None:
        self._vision = vision
        self._registry = BackendRegistry()

    def run(self, source: InputSource) -> Document:
        """The labeled description of one image."""
        mime = self._common_mime(source)
        logger.debug("describing %s (%s) with the vision model", source.path or "bytes", mime)
        with self._registry.require(self._vision) as describer:
            return self._common_document(describer.describe(source.load(), mime))

    async def arun(self, source: InputSource) -> Document:
        """`run`, off the event loop."""
        mime = self._common_mime(source)
        logger.debug("describing %s (%s) with the vision model", source.path or "bytes", mime)
        async with self._registry.require(self._vision) as describer:
            return self._common_document(await describer.adescribe(await source.aload(), mime))
