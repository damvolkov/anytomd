"""Format vocabulary shared by routing and the backends."""

from types import MappingProxyType
from typing import Final

PDF: Final = "pdf"
DESCRIPTION_LABEL: Final = "Image description: "

IMAGE_MIMES: Final = MappingProxyType(
    {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "gif": "image/gif",
        "webp": "image/webp",
        "bmp": "image/bmp",
        "tiff": "image/tiff",
        "tif": "image/tiff",
        "svg": "image/svg+xml",
        "heic": "image/heic",
        "heif": "image/heif",
        "avif": "image/avif",
    }
)
