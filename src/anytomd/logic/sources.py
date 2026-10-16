"""What the caller handed in: a path or bytes, and the format it turns out to be."""

import asyncio
import os
from pathlib import Path
from typing import Final, Self

from anytomd.backends.native import NativeBackend
from anytomd.infra.errors import UnknownFormatError

type Source = str | os.PathLike[str] | bytes | bytearray

HEADER: Final = 8192


class InputSource:
    """A path or bytes with its normalized format; bytes are loaded only when a route needs them."""

    __slots__ = ("data", "format", "path")

    ##### PRIVATE #####

    @staticmethod
    def _build_format(format: str | None) -> str | None:
        return format.lower().removeprefix(".") if format else None

    @staticmethod
    def _build_required(format: str | None) -> str:
        return format or InputSource._build_missing()

    @staticmethod
    def _build_missing() -> str:
        msg = "bytes need a format, e.g. format='docx'"
        raise UnknownFormatError(msg)

    ############################################################

    ##### PUBLIC #####

    def __init__(self, path: str | None, data: bytes | None, format: str) -> None:
        self.path = path
        self.data = data
        self.format = format

    @classmethod
    def build(cls, source: Source, format: str | None) -> Self:
        """Resolve the source; a path without a format is sniffed from its name and first bytes."""
        given = cls._build_format(format)
        match source:
            case bytes() | bytearray():
                return cls(None, bytes(source), cls._build_required(given))
            case _ if given:
                ### An explicit format overrides detection, and only the bytes route honours it.
                path = os.fspath(source)
                return cls(path, Path(path).read_bytes(), given)
            case _:
                path = os.fspath(source)
                with Path(path).open("rb") as handle:
                    header = handle.read(HEADER)
                return cls(path, None, NativeBackend().detect(path, header) or "")

    @classmethod
    async def abuild(cls, source: Source, format: str | None) -> Self:
        """`build`, with the file read off the event loop."""
        return await asyncio.to_thread(cls.build, source, format)

    def load(self) -> bytes:
        """The content, read from disk when the source is a path."""
        return self.data if self.data is not None else Path(self.path or "").read_bytes()

    async def aload(self) -> bytes:
        """`load`, off the event loop."""
        return self.data if self.data is not None else await asyncio.to_thread(Path(self.path or "").read_bytes)

    def size(self) -> int:
        """Bytes in the source, without reading a file."""
        return len(self.data) if self.data is not None else Path(self.path or "").stat().st_size
