"""Optional-capability image describers: local OCR, OpenAI-compatible vision, and their composite.

Empty is a signal here, not noise: the OCR layer answers `""` only when the image holds no
readable text, and the composite fires the vision model exactly there.
"""

from __future__ import annotations

import asyncio
import base64
from typing import TYPE_CHECKING, Final

from anytomd._capabilities import LITEPARSE_OCR, OPENAI_VLM

if TYPE_CHECKING:
    from liteparse import LiteParse, ParseResult
    from openai import AsyncOpenAI, OpenAI
    from openai.types.chat import ChatCompletion, ChatCompletionMessageParam

VLM_MAX_TOKENS: Final = 128
NOTHING_TO_DESCRIBE: Final = "nothing to describe with: pass a vision 'model' or keep 'ocr' on"


class _OcrDescriber:
    """Shared OCR rules: one liteparse engine, its ParseError as the miss, first page's raw text as the answer."""

    __slots__ = ("_miss", "_parser")

    def __init__(self, language: str, parser: LiteParse | None) -> None:
        module = LITEPARSE_OCR.resolve()
        self._miss: type[Exception] = module.ParseError
        self._parser = (
            parser
            if parser is not None
            else module.LiteParse(ocr_enabled=True, ocr_language=language, output_format="json", quiet=True)
        )

    @staticmethod
    def _text(result: ParseResult) -> str:
        ### Alt text is one line: a blank line inside `![...]` would split the image into two paragraphs.
        return " ".join(result.pages[0].text.split()) if result.pages else ""


class _ChatDescriber:
    """Shared request shape of the OpenAI-compatible describers: prompt and image as data URI over chat."""

    __slots__ = ("_max_tokens", "_model", "_prompt")

    def __init__(self, model: str, prompt: str | None, max_tokens: int) -> None:
        self._model = model
        self._prompt = prompt
        self._max_tokens = max_tokens

    def _messages(self, image: bytes, mime_type: str, prompt: str) -> list[ChatCompletionMessageParam]:
        data_url = f"data:{mime_type};base64,{base64.b64encode(image).decode()}"
        return [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": self._prompt or prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ]

    @staticmethod
    def _answer(completion: ChatCompletion) -> str:
        return " ".join((completion.choices[0].message.content or "").split())


class LiteParseDescriber(_OcrDescriber):
    """Local OCR through liteparse, in-process: readable text out, `""` when the image holds none. Needs 'anytomd[ocr]'."""

    __slots__ = ()

    ##### PRIVATE #####

    def _read(self, image: bytes) -> str:
        try:
            return self._text(self._parser.parse(image))
        except self._miss:
            ### An unreadable or unsupported image is an OCR miss, which is data; any other error is a bug and propagates.
            return ""

    ############################################################

    ##### PUBLIC #####

    def __init__(self, *, language: str = "eng", parser: LiteParse | None = None) -> None:
        super().__init__(language, parser)

    def __call__(self, image: bytes | bytearray, _mime_type: str, _prompt: str) -> str:
        """The image's readable text, or `""`: the composite's exact cue to fall back."""
        return self._read(bytes(image))


class AsyncLiteParseDescriber(_OcrDescriber):
    """OCR off the event loop with bounded workers — what the async fan-out needs. Needs 'anytomd[ocr]'."""

    __slots__ = ("_gate",)

    ##### PRIVATE #####

    async def _read(self, image: bytes) -> str:
        try:
            async with self._gate:
                return self._text(await self._parser.aparse(image))
        except self._miss:
            return ""

    ############################################################

    ##### PUBLIC #####

    def __init__(self, *, language: str = "eng", max_concurrency: int = 4, parser: LiteParse | None = None) -> None:
        super().__init__(language, parser)
        self._gate = asyncio.Semaphore(max_concurrency)

    async def __call__(self, image: bytes | bytearray, _mime_type: str, _prompt: str) -> str:
        """The image's readable text, or `""`, without blocking the loop."""
        return await self._read(bytes(image))


class OpenAIDescriber(_ChatDescriber):
    """Vision answer through any OpenAI-compatible chat endpoint — OpenAI, Anthropic, Gemini and local servers among them. Needs 'anytomd[vlm]'."""

    __slots__ = ("_client",)

    ##### PUBLIC #####

    def __init__(
        self,
        *,
        model: str,
        api_base: str | None = None,
        api_key: str | None = None,
        prompt: str | None = None,
        max_tokens: int = VLM_MAX_TOKENS,
        client: OpenAI | None = None,
    ) -> None:
        super().__init__(model, prompt, max_tokens)
        self._client = client if client is not None else OPENAI_VLM.resolve().OpenAI(base_url=api_base, api_key=api_key)

    def __call__(self, image: bytes | bytearray, mime_type: str, prompt: str) -> str:
        """The model's answer, stripped; a provider failure raises and the engine records it as a warning."""
        completion = self._client.chat.completions.create(
            model=self._model,
            max_tokens=self._max_tokens,
            messages=self._messages(bytes(image), mime_type, prompt),
        )
        return self._answer(completion)

    def close(self) -> None:
        """Release the provider's sockets."""
        self._client.close()


class AsyncOpenAIDescriber(_ChatDescriber):
    """Async twin of `OpenAIDescriber`, safe under the engine's concurrent descriptions. Needs 'anytomd[vlm]'."""

    __slots__ = ("_client",)

    ##### PUBLIC #####

    def __init__(
        self,
        *,
        model: str,
        api_base: str | None = None,
        api_key: str | None = None,
        prompt: str | None = None,
        max_tokens: int = VLM_MAX_TOKENS,
        client: AsyncOpenAI | None = None,
    ) -> None:
        super().__init__(model, prompt, max_tokens)
        self._client = (
            client if client is not None else OPENAI_VLM.resolve().AsyncOpenAI(base_url=api_base, api_key=api_key)
        )

    async def __call__(self, image: bytes | bytearray, mime_type: str, prompt: str) -> str:
        """The model's answer, stripped, off the loop."""
        completion = await self._client.chat.completions.create(
            model=self._model,
            max_tokens=self._max_tokens,
            messages=self._messages(bytes(image), mime_type, prompt),
        )
        return self._answer(completion)

    async def aclose(self) -> None:
        """Release the provider's sockets, off the loop."""
        await self._client.close()


class ImageDescriber:
    """The capability composite: OCR answers images that hold text, the vision model only the rest.

    A layer that finds nothing hands the image to the next; when every layer is silent the alt
    text stays empty, exactly as without a describer. Needs 'anytomd[ocr]' while `ocr` is on and
    'anytomd[vlm]' when a `model` is given; provider failures raise, so the engine warns instead
    of failing the document.
    """

    __slots__ = ("_layers", "_vlm")

    ##### PUBLIC #####

    def __init__(
        self,
        *,
        model: str | None = None,
        api_base: str | None = None,
        api_key: str | None = None,
        prompt: str | None = None,
        max_tokens: int = VLM_MAX_TOKENS,
        ocr: bool = True,
        language: str = "eng",
        ocr_parser: LiteParse | None = None,
        vlm_client: OpenAI | None = None,
    ) -> None:
        ocr_layer = LiteParseDescriber(language=language, parser=ocr_parser) if ocr else None
        self._vlm = (
            OpenAIDescriber(
                model=model, api_base=api_base, api_key=api_key, prompt=prompt, max_tokens=max_tokens, client=vlm_client
            )
            if model is not None
            else None
        )
        self._layers = tuple(layer for layer in (ocr_layer, self._vlm) if layer is not None)
        match self._layers:
            case ():
                raise ValueError(NOTHING_TO_DESCRIBE)

    def __call__(self, image: bytes | bytearray, mime_type: str, prompt: str) -> str:
        """The first layer with something to say; `""` when the image tells every layer nothing."""
        return next((text for layer in self._layers if (text := layer(image, mime_type, prompt))), "")

    def close(self) -> None:
        """Release the vision layer's sockets if it exists; the OCR layer owns none."""
        match self._vlm:
            case OpenAIDescriber() as vlm:
                vlm.close()


class AsyncImageDescriber:
    """Async composite: every image OCR'd under the gate, only the blank ones sent to the model.

    Same fallback rule and failure semantics as `ImageDescriber`; `max_concurrency` bounds the
    engine's per-image fan-out — tesseract workers and provider sockets alike stay under one gate.
    """

    __slots__ = ("_gate", "_layers", "_vlm")

    ##### PRIVATE #####

    async def _call_layer(
        self,
        layer: AsyncLiteParseDescriber | AsyncOpenAIDescriber,
        image: bytes | bytearray,
        mime_type: str,
        prompt: str,
    ) -> str:
        async with self._gate:
            return await layer(image, mime_type, prompt)

    ############################################################

    ##### PUBLIC #####

    def __init__(
        self,
        *,
        model: str | None = None,
        api_base: str | None = None,
        api_key: str | None = None,
        prompt: str | None = None,
        max_tokens: int = VLM_MAX_TOKENS,
        ocr: bool = True,
        language: str = "eng",
        max_concurrency: int = 4,
        ocr_parser: LiteParse | None = None,
        vlm_client: AsyncOpenAI | None = None,
    ) -> None:
        self._gate = asyncio.Semaphore(max_concurrency)
        ocr_layer = AsyncLiteParseDescriber(language=language, parser=ocr_parser) if ocr else None
        self._vlm = (
            AsyncOpenAIDescriber(
                model=model, api_base=api_base, api_key=api_key, prompt=prompt, max_tokens=max_tokens, client=vlm_client
            )
            if model is not None
            else None
        )
        self._layers = tuple(layer for layer in (ocr_layer, self._vlm) if layer is not None)
        match self._layers:
            case ():
                raise ValueError(NOTHING_TO_DESCRIBE)

    async def __call__(self, image: bytes | bytearray, mime_type: str, prompt: str) -> str:
        """OCR first; only the images it reads as blank reach the vision model, under one shared gate."""
        first, *rest = self._layers
        text = await self._call_layer(first, image, mime_type, prompt)
        return text or (await self._call_layer(rest[0], image, mime_type, prompt) if rest else "")

    async def aclose(self) -> None:
        """Release the vision layer's sockets if it exists; the OCR layer owns none."""
        match self._vlm:
            case AsyncOpenAIDescriber() as vlm:
                await vlm.aclose()
