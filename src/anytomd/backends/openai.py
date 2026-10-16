"""OpenAI-compatible vision: any `chat/completions` endpoint that accepts images. Imported only with the `vlm` extra."""

import base64
import logging
from types import TracebackType
from typing import Self

import openai
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam

from anytomd.infra.errors import DescriptionError
from anytomd.infra.specs import VisionSpec

logger = logging.getLogger(__name__)


class OpenaiBackend:
    """Describes images through one provider; a sync and an async client, each scoped by its `with`."""

    __slots__ = ("_aclient", "_client", "_spec")

    ##### PRIVATE #####

    def _common_messages(self, image: bytes, mime_type: str) -> list[ChatCompletionMessageParam]:
        data_url = f"data:{mime_type};base64,{base64.b64encode(image).decode()}"
        return [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": self._spec.prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ]

    @staticmethod
    def _common_answer(completion: ChatCompletion) -> str:
        return " ".join((completion.choices[0].message.content or "").split())

    def _common_failure(self, error: openai.OpenAIError) -> DescriptionError:
        return DescriptionError(f"vision model {self._spec.model!r} failed: {error}")

    ############################################################

    ##### PUBLIC #####

    def __init__(
        self,
        spec: VisionSpec,
        *,
        client: openai.OpenAI | None = None,
        aclient: openai.AsyncOpenAI | None = None,
    ) -> None:
        self._spec = spec
        self._client = client or openai.OpenAI(base_url=spec.base_url, api_key=spec.api_key)
        self._aclient = aclient or openai.AsyncOpenAI(base_url=spec.base_url, api_key=spec.api_key)

    @property
    def concurrency(self) -> int:
        """How many images may be described at once."""
        return self._spec.concurrency

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: type[BaseException] | BaseException | TracebackType | None) -> None:
        self._client.close()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: type[BaseException] | BaseException | TracebackType | None) -> None:
        await self._aclient.close()

    def describe(self, image: bytes, mime_type: str) -> str:
        """The model's description of one image, on one line."""
        try:
            completion = self._client.chat.completions.create(
                model=self._spec.model,
                max_tokens=self._spec.max_tokens,
                messages=self._common_messages(image, mime_type),
            )
        except openai.OpenAIError as error:
            raise self._common_failure(error) from error
        return self._common_answer(completion)

    async def adescribe(self, image: bytes, mime_type: str) -> str:
        """`describe`, off the event loop."""
        try:
            completion = await self._aclient.chat.completions.create(
                model=self._spec.model,
                max_tokens=self._spec.max_tokens,
                messages=self._common_messages(image, mime_type),
            )
        except openai.OpenAIError as error:
            raise self._common_failure(error) from error
        return self._common_answer(completion)
