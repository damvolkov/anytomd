"""Optional third-party capabilities: resolved at first use, never at import time."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from types import ModuleType


class Capability:
    """An optional dependency owned by one extra, imported on demand; its absence names the extra."""

    __slots__ = ("extra", "module")

    def __init__(self, module: str, extra: str) -> None:
        self.module = module
        self.extra = extra

    def resolve(self) -> ModuleType:
        """The module behind the capability, or an ImportError pointing at its extra."""
        try:
            return importlib.import_module(self.module)
        except ImportError as error:
            msg = f"{self.module} is an optional capability: install 'anytomd[{self.extra}]'"
            raise ImportError(msg) from error


LITEPARSE_OCR: Final = Capability("liteparse", "ocr")
LITEPARSE_PDF: Final = Capability("liteparse", "pdf")
OPENAI_VLM: Final = Capability("openai", "vlm")
