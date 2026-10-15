"""PDF as an optional capability: the format anytomd-rs refuses by design, read through liteparse."""

from __future__ import annotations

from typing import TYPE_CHECKING

from anytomd._capabilities import LITEPARSE_PDF
from anytomd.documents import PdfDocument
from anytomd.errors import PdfError

if TYPE_CHECKING:
    import os

    from liteparse import LiteParse, ParseResult


class PdfConverter:
    """One liteparse engine per converter: OCR on by default, configurable off. Needs 'anytomd[pdf]'."""

    __slots__ = ("_miss", "_parser")

    ##### PRIVATE #####

    def _common_document(self, result: ParseResult) -> PdfDocument:
        return PdfDocument(
            markdown="\n\n".join(page.markdown for page in result.pages),
            pages=result.num_pages,
            warnings=tuple(f"page {error.page_num}: {error.message}" for error in result.page_errors),
        )

    def _common_refusal(self, error: Exception) -> PdfError:
        return PdfError(f"liteparse could not read the document: {error}")

    def _common_read(self, data: bytes | str) -> PdfDocument:
        try:
            return self._common_document(self._parser.parse(data))
        except self._miss as error:
            raise self._common_refusal(error) from error

    async def _common_aread(self, data: bytes | str) -> PdfDocument:
        try:
            return self._common_document(await self._parser.aparse(data))
        except self._miss as error:
            raise self._common_refusal(error) from error

    ############################################################

    ##### PUBLIC #####

    def __init__(
        self,
        *,
        ocr: bool = True,
        language: str = "eng",
        workers: int | None = None,
        parser: LiteParse | None = None,
    ) -> None:
        module = LITEPARSE_PDF.resolve()
        self._miss: type[Exception] = module.ParseError
        self._parser = (
            parser
            if parser is not None
            else module.LiteParse(
                ocr_enabled=ocr, ocr_language=language, num_workers=workers, output_format="markdown", quiet=True
            )
        )

    def convert_file(self, path: str | os.PathLike[str]) -> PdfDocument:
        """A PDF file read to Markdown."""
        return self._common_read(str(path))

    def convert_bytes(self, data: bytes | bytearray) -> PdfDocument:
        """PDF bytes read to Markdown."""
        return self._common_read(bytes(data))

    async def convert_file_async(self, path: str | os.PathLike[str]) -> PdfDocument:
        """A PDF file read off the event loop."""
        return await self._common_aread(str(path))

    async def convert_bytes_async(self, data: bytes | bytearray) -> PdfDocument:
        """PDF bytes read off the event loop."""
        return await self._common_aread(bytes(data))
