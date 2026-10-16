"""Where a format is converted."""

from enum import StrEnum, auto


class Route(StrEnum):
    NATIVE = auto()
    IMAGE = auto()
    PDF = auto()
