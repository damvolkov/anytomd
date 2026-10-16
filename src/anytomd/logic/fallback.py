"""The image rule: OCR reads the letters; only an image without letters reaches the vision model."""

import asyncio
import logging
from typing import Final

from anytomd.backends.base import Describer, Recognizer
from anytomd.infra.errors import DescriptionError
from anytomd.infra.formats import DESCRIPTION_LABEL
from anytomd.infra.warnings import DocumentWarning

logger = logging.getLogger(__name__)

KEEP_ALT: Final = "anytomd: no text and no description, original alt kept"


class KeepAltError(Exception):
    """Raised into the engine so it keeps the author's alt text; its warning is filtered out afterwards."""


class ImageFallback:
    """OCR first, vision second, nothing invented: one rule for embedded and standalone images."""

    __slots__ = ("_describer", "_gate", "_recognizer", "_strict")

    ##### PRIVATE #####

    def _hook_nothing(self, location: str) -> str:
        logger.debug("%s: no text and no description; keeping the original alt text", location)
        ### Under strict mode the engine would turn the keep-alt warning into an error, so the alt is emptied instead.
        return "" if self._strict else self._hook_raise()

    @staticmethod
    def _hook_raise() -> str:
        raise KeepAltError(KEEP_ALT)

    @staticmethod
    def _common_label(description: str) -> str:
        return f"{DESCRIPTION_LABEL}{description}" if description else ""

    def _resolve_describe(self, image: bytes, mime_type: str) -> tuple[str, tuple[DocumentWarning, ...]]:
        describer = self._describer
        try:
            return self._common_label(describer.describe(image, mime_type) if describer else ""), ()
        except DescriptionError as error:
            logger.debug("vision fallback failed: %s", error)
            return "", (DocumentWarning("skipped_element", str(error), "image"),)

    async def _aresolve_describe(self, image: bytes, mime_type: str) -> tuple[str, tuple[DocumentWarning, ...]]:
        describer = self._describer
        try:
            async with self._gate:
                return self._common_label(await describer.adescribe(image, mime_type) if describer else ""), ()
        except DescriptionError as error:
            logger.debug("vision fallback failed: %s", error)
            return "", (DocumentWarning("skipped_element", str(error), "image"),)

    ############################################################

    ##### PUBLIC #####

    def __init__(
        self, recognizer: Recognizer | None, describer: Describer | None, *, strict: bool, concurrency: int
    ) -> None:
        self._recognizer = recognizer
        self._describer = describer
        self._strict = strict
        self._gate = asyncio.Semaphore(concurrency)

    @property
    def active(self) -> bool:
        """Whether any capability is present; without one the engine's own image handling stands."""
        return bool(self._recognizer or self._describer)

    def hook(self, image: bytes, mime_type: str, _prompt: str) -> str:
        """Alt text for one embedded image, on one line."""
        recognizer, describer = self._recognizer, self._describer
        text = " ".join(recognizer.recognize(image).split()) if recognizer else ""
        logger.debug("embedded image: ocr %s", "found text" if text else "found nothing")
        described = self._common_label(describer.describe(image, mime_type)) if describer and not text else ""
        return text or described or self._hook_nothing("embedded image")

    async def ahook(self, image: bytes, mime_type: str, _prompt: str) -> str:
        """`hook`, concurrent across the document's images under one gate."""
        recognizer, describer = self._recognizer, self._describer
        async with self._gate:
            text = " ".join((await recognizer.arecognize(image)).split()) if recognizer else ""
            logger.debug("embedded image: ocr %s", "found text" if text else "found nothing")
            described = (
                self._common_label(await describer.adescribe(image, mime_type)) if describer and not text else ""
            )
        return text or described or self._hook_nothing("embedded image")

    def resolve(self, image: bytes, mime_type: str) -> tuple[str, tuple[DocumentWarning, ...]]:
        """Markdown for a standalone image: its text, else its labeled description, else `""`."""
        recognizer = self._recognizer
        text = recognizer.recognize(image) if recognizer else ""
        logger.debug("standalone image: ocr %s", "found text" if text else "found nothing")
        return (text, ()) if text or not self._describer else self._resolve_describe(image, mime_type)

    async def aresolve(self, image: bytes, mime_type: str) -> tuple[str, tuple[DocumentWarning, ...]]:
        """`resolve`, off the event loop."""
        recognizer = self._recognizer
        async with self._gate:
            text = await recognizer.arecognize(image) if recognizer else ""
        logger.debug("standalone image: ocr %s", "found text" if text else "found nothing")
        return (text, ()) if text or not self._describer else await self._aresolve_describe(image, mime_type)
