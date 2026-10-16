"""OpenaiBackend: the chat/completions wire, one-line answers, failures as DescriptionError, scoped clients."""

import openai
import pytest

from anytomd.backends.openai import OpenaiBackend
from anytomd.infra.errors import DescriptionError
from anytomd.infra.specs import VisionSpec

SPEC = VisionSpec(model="vision-1", prompt="Describe.", max_tokens=64, concurrency=3)


class FakeCompletions:
    def __init__(self, content: str | None = "A cat\n\non a chair ", error: Exception | None = None) -> None:
        self.content = content
        self.error = error
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        match self.error:
            case Exception() as error:
                raise error
        message = type("Message", (), {"content": self.content})()
        return type("Completion", (), {"choices": [type("Choice", (), {"message": message})()]})()


class FakeAsyncCompletions(FakeCompletions):
    async def create(self, **kwargs):
        return FakeCompletions.create(self, **kwargs)


def fake_client(completions: FakeCompletions, events: list[str]):
    return type(
        "Client",
        (),
        {
            "chat": type("Chat", (), {"completions": completions})(),
            "close": staticmethod(lambda: events.append("close")),
        },
    )()


@pytest.fixture
def events() -> list[str]:
    return []


async def test_openai_describe_sends_prompt_and_data_uri(events) -> None:
    completions = FakeCompletions()
    backend = OpenaiBackend(SPEC, client=fake_client(completions, events), aclient=fake_client(completions, events))
    assert backend.describe(b"raw", "image/png") == "A cat on a chair"
    sent = completions.calls[0]
    assert (sent["model"], sent["max_tokens"]) == ("vision-1", 64)
    assert sent["messages"][0]["content"][0]["text"] == "Describe."
    assert sent["messages"][0]["content"][1]["image_url"]["url"] == "data:image/png;base64,cmF3"


async def test_openai_describe_silent_answer_is_empty(events) -> None:
    completions = FakeCompletions(content=None)
    backend = OpenaiBackend(SPEC, client=fake_client(completions, events), aclient=fake_client(completions, events))
    assert backend.describe(b"raw", "image/png") == ""


async def test_openai_describe_failure_is_a_description_error(events) -> None:
    completions = FakeCompletions(error=openai.APIConnectionError(request=None))  # ty: ignore[invalid-argument-type]
    backend = OpenaiBackend(SPEC, client=fake_client(completions, events), aclient=fake_client(completions, events))
    with pytest.raises(DescriptionError, match="vision-1"):
        backend.describe(b"raw", "image/png")


async def test_openai_adescribe(events) -> None:
    completions = FakeAsyncCompletions()
    backend = OpenaiBackend(SPEC, client=fake_client(completions, events), aclient=fake_client(completions, events))
    assert await backend.adescribe(b"raw", "image/jpeg") == "A cat on a chair"


async def test_openai_adescribe_failure(events) -> None:
    completions = FakeAsyncCompletions(error=openai.APIConnectionError(request=None))  # ty: ignore[invalid-argument-type]
    backend = OpenaiBackend(SPEC, client=fake_client(completions, events), aclient=fake_client(completions, events))
    with pytest.raises(DescriptionError):
        await backend.adescribe(b"raw", "image/png")


async def test_openai_scopes_close_their_clients() -> None:
    backend = OpenaiBackend(SPEC, client=openai.OpenAI(api_key="k"), aclient=openai.AsyncOpenAI(api_key="k"))
    with backend as entered:
        assert entered is backend
    async with backend as aentered:
        assert aentered is backend
    assert backend.concurrency == 3


async def test_openai_builds_real_clients_from_the_spec() -> None:
    async with OpenaiBackend(VisionSpec(model="m", base_url="http://localhost:1/v1", api_key="k")) as backend:
        assert backend.concurrency == 4
    backend._client.close()
