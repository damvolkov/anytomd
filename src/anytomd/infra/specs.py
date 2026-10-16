"""Explicit configuration values: what the caller asks a conversion for."""

from dataclasses import dataclass
from typing import Final

DEFAULT_MAX_INPUT_BYTES: Final = 8 * 1024**3
DEFAULT_MAX_IMAGE_BYTES: Final = 4 * 1024**3
DEFAULT_MAX_ZIP_BYTES: Final = 16 * 1024**3


@dataclass(frozen=True, slots=True)
class VisionSpec:
    """An OpenAI-compatible vision model: OpenAI, Anthropic, Gemini, local servers — `base_url` picks the provider."""

    model: str
    base_url: str | None = None
    api_key: str | None = None
    prompt: str = "Describe this image concisely for use as alt text."
    max_tokens: int = 256
    concurrency: int = 4


@dataclass(frozen=True, slots=True)
class ConversionSpec:
    """Every option of one conversion, as given to `convert` / `aconvert`."""

    images: bool = False
    comments: bool = False
    strict: bool = False
    ocr: bool = True
    vision: VisionSpec | None = None
    max_input_bytes: int = DEFAULT_MAX_INPUT_BYTES
    max_image_bytes: int = DEFAULT_MAX_IMAGE_BYTES
    max_zip_bytes: int = DEFAULT_MAX_ZIP_BYTES
