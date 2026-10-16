"""Ports of the optional backends: each act has a sync and an async (`a`-prefixed) form."""

from types import TracebackType
from typing import Protocol, Self

from anytomd.infra.documents import Document


class Recognizer(Protocol):
    """Reads the letters an image holds; `""` when it holds none."""

    def recognize(self, image: bytes) -> str: ...

    async def arecognize(self, image: bytes) -> str: ...


class Describer(Protocol):
    """Describes an image in words with a vision model; scoped by `with` / `async with`, which own its clients."""

    @property
    def concurrency(self) -> int: ...

    def __enter__(self) -> Self: ...

    def __exit__(self, *_: type[BaseException] | BaseException | TracebackType | None) -> None: ...

    async def __aenter__(self) -> Self: ...

    async def __aexit__(self, *_: type[BaseException] | BaseException | TracebackType | None) -> None: ...

    def describe(self, image: bytes, mime_type: str) -> str: ...

    async def adescribe(self, image: bytes, mime_type: str) -> str: ...


class Reader(Protocol):
    """Reads a whole document the engine does not convert (PDF)."""

    def read(self, source: str | bytes) -> Document: ...

    async def aread(self, source: str | bytes) -> Document: ...
