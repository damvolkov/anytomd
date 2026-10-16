"""Optional backends, loaded by name only when their extra is installed."""

import importlib
import logging
from types import MappingProxyType, ModuleType
from typing import Final, NoReturn

from anytomd.backends.base import Describer, Reader, Recognizer
from anytomd.infra.errors import DescriptionError, MissingExtraError
from anytomd.infra.specs import VisionSpec

logger = logging.getLogger(__name__)

### Each third-party library the extras install, and the extra that installs it.
EXTRAS: Final = MappingProxyType({"liteparse": "ocr", "openai": "vlm", "pydantic_settings": "vlm"})


class BackendRegistry:
    """Resolves the optional backends: None when their extra is absent, never an import error at `import anytomd`."""

    __slots__ = ()

    ##### PRIVATE #####

    @staticmethod
    def _common_module(path: str) -> ModuleType | None:
        ### The one deferred import, by design: optional backends import their third-party library at module level, so
        ### they are loaded here, by name, only once their extra is installed — `import anytomd` must never need them.
        try:
            return importlib.import_module(path)
        except ModuleNotFoundError as error:
            match error.name:
                case str() as name if name in EXTRAS:
                    logger.debug("optional backend %s unavailable: install anytomd[%s]", path, EXTRAS[name])
                    return None
            raise

    def _describer_spec(self, vision: VisionSpec | None) -> VisionSpec | None:
        settings = self._common_module("anytomd.config.vision")
        return vision or (settings.VisionSettings().spec() if settings else None)

    ############################################################

    ##### PUBLIC #####

    def recognizer(self, *, ocr: bool) -> Recognizer | None:
        """Local OCR, when wanted and installed."""
        module = self._common_module("anytomd.backends.liteparse") if ocr else None
        return module.LiteparseBackend() if module else None

    def reader(self, *, ocr: bool) -> Reader:
        """The PDF reader; raises when the `pdf` extra is missing."""
        module = self._common_module("anytomd.backends.liteparse")
        return module.LiteparseBackend(ocr=ocr) if module else self.missing("PDF", "pdf")

    def describer(self, vision: VisionSpec | None) -> Describer | None:
        """The vision model from `vision` or `ANYTOMD_VISION_*`, when the `vlm` extra is installed and a model is set."""
        module = self._common_module("anytomd.backends.openai")
        spec = self._describer_spec(vision) if module else None
        logger.debug("vision fallback %s", f"on with {spec.model!r}" if spec else "off: no vision model configured")
        return module.OpenaiBackend(spec) if module and spec else None

    def require(self, vision: VisionSpec | None) -> Describer:
        """The vision model, or the exact reason there is none."""
        module = self._common_module("anytomd.backends.openai")
        spec = self._describer_spec(vision) if module else self.missing("describe", "vlm")
        return module.OpenaiBackend(spec) if module and spec else self.unconfigured()

    @staticmethod
    def missing(what: str, extra: str) -> NoReturn:
        """Raise the error that names the extra to install."""
        msg = f"{what} needs the '{extra}' extra: pip install 'anytomd[{extra}]'"
        raise MissingExtraError(msg)

    @staticmethod
    def unconfigured() -> NoReturn:
        """Raise the error that says how to configure a vision model."""
        msg = "no vision model: set ANYTOMD_VISION_MODEL or pass vision=VisionSpec(model=...)"
        raise DescriptionError(msg)
