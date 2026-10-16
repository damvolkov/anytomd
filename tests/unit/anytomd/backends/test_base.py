"""The ports: every backend satisfies its protocol (checked statically by ty, exercised here)."""

from typing import TYPE_CHECKING

from anytomd.backends.liteparse import LiteparseBackend
from anytomd.backends.openai import OpenaiBackend
from anytomd.infra.specs import VisionSpec
from tests.conftest import text_pdf

if TYPE_CHECKING:
    from anytomd.backends.base import Describer, Reader, Recognizer


async def test_base_liteparse_is_recognizer_and_reader(raw) -> None:
    recognizer: Recognizer = LiteparseBackend()
    reader: Reader = LiteparseBackend(ocr=False)
    assert recognizer.recognize(raw("shot.png")) == ""
    assert reader.read(text_pdf("Port")).pages == 1


async def test_base_openai_is_describer() -> None:
    with OpenaiBackend(VisionSpec(model="m", api_key="k")) as backend:
        describer: Describer = backend
        assert describer.concurrency == 4
    await backend._aclient.close()
