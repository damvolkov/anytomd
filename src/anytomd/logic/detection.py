"""The format the engine sees in a source."""

import asyncio
import os
from pathlib import Path

from anytomd.backends.native import NativeBackend
from anytomd.logic.sources import Source


class Detection:
    """Format detection: magic bytes first, then the name; ZIP resolved to DOCX, PPTX or XLSX."""

    __slots__ = ("_native",)

    ##### PUBLIC #####

    def __init__(self) -> None:
        self._native = NativeBackend()

    def run(self, source: Source, name: str | None) -> str | None:
        """The format, or None when nothing matches."""
        match source:
            case bytes() | bytearray():
                return self._native.detect(name or "", bytes(source))
            case _:
                path = os.fspath(source)
                return self._native.detect(name or path, Path(path).read_bytes())

    async def arun(self, source: Source, name: str | None) -> str | None:
        """`run`, off the event loop."""
        return await asyncio.to_thread(self.run, source, name)
