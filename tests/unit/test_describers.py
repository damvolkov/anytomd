"""Optional-capability describers: OCR emptiness, OpenAI-compatible wire, and the composite fallback."""

import asyncio
import sys

import liteparse
import pytest

import anytomd
from anytomd import (
    AsyncImageDescriber,
    AsyncLiteParseDescriber,
    AsyncOpenAIDescriber,
    ImageDescriber,
    LiteParseDescriber,
    OpenAIDescriber,
)
from anytomd._capabilities import Capability


def _parse_result(text="", pages=1, page_errors=()):
    parsed_pages = [
        type("Page", (), {"page_num": number, "text": text, "markdown": ""})() for number in range(1, pages + 1)
    ]
    return type("Result", (), {"pages": parsed_pages, "num_pages": pages, "page_errors": list(page_errors)})()


class FakeParser:
    def __init__(self, result=None, error: Exception | None = None):
        self.result = result if result is not None else _parse_result()
        self.error = error
        self.received = None

    def parse(self, data):
        self.received = data
        return self._answer()

    async def aparse(self, data):
        self.received = data
        return self._answer()

    def _answer(self):
        match self.error:
            case Exception() as error:
                raise error
        return self.result


class FakeCompletions:
    def __init__(self, content="A cat asleep on a chair", error=None):
        self.content = content
        self.error = error
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        match self.error:
            case Exception() as error:
                raise error
        return type(
            "Completion",
            (),
            {"choices": [type("Choice", (), {"message": type("Message", (), {"content": self.content})()})]},
        )()


class FakeAsyncCompletions(FakeCompletions):
    async def create(self, **kwargs):
        return FakeCompletions.create(self, **kwargs)


def _fake_client(completions, events=None, async_close=False):
    sink = events if events is not None else []

    def close():
        sink.append("close")

    async def aclose():
        sink.append("aclose")

    return type(
        "Client",
        (),
        {
            "chat": type("Chat", (), {"completions": completions})(),
            "close": staticmethod(aclose if async_close else close),
        },
    )()


def test_liteparse_describer_strips_first_page_text():
    parser = FakeParser(_parse_result(text="  Hello there  \n"))
    assert LiteParseDescriber(parser=parser)(b"bytes", "image/png", "prompt") == "Hello there"


def test_liteparse_describer_normalizes_bytearray_to_bytes():
    parser = FakeParser(_parse_result(text="x"))
    LiteParseDescriber(parser=parser)(bytearray(b"raw"), "image/png", "prompt")
    assert isinstance(parser.received, bytes)


def test_liteparse_describer_miss_on_broken_image_returns_empty():
    parser = FakeParser(error=liteparse.ParseError("no format"))
    assert LiteParseDescriber(parser=parser)(b"junk", "image/png", "prompt") == ""


def test_liteparse_describer_programming_errors_are_not_swallowed():
    parser = FakeParser(error=TypeError("bug"))
    with pytest.raises(TypeError, match="bug"):
        LiteParseDescriber(parser=parser)(b"bytes", "image/png", "prompt")


def test_liteparse_describer_collapses_multiline_text_to_one_alt_line():
    parser = FakeParser(_parse_result(text="Title\n\nBody   line\n"))
    assert LiteParseDescriber(parser=parser)(b"bytes", "image/png", "prompt") == "Title Body line"


def test_liteparse_describer_real_engine_reads_text_in_a_photo(raw):
    assert LiteParseDescriber()(raw("real_photo.png"), "image/png", "prompt") == "This is just an example."


@pytest.mark.parametrize("fixture", ["vector.svg", "scene.heic", "shot.png"])
def test_liteparse_describer_real_engine_misses_are_empty(raw, fixture):
    assert LiteParseDescriber()(raw(fixture), "image/png", "prompt") == ""


def test_liteparse_describer_real_engine_end_to_end_alt_text(path_of):
    result = anytomd.convert_file(path_of("real_photo.png"), image_describer=LiteParseDescriber())
    assert result.markdown == "![This is just an example.](image.png)\n"
    assert result.warnings == []


def test_liteparse_describer_miss_on_pageless_result_returns_empty():
    parser = FakeParser(_parse_result(pages=0))
    assert LiteParseDescriber(parser=parser)(b"bytes", "image/png", "prompt") == ""


def test_liteparse_describer_real_engine_reads_letterless_image():
    assert (
        LiteParseDescriber()(
            bytes.fromhex(
                "89504e470d0a1a0a0000000d4948445200000020000000200802000000fc18ed"
                "a30000002a4944415478da63b823274753c4306ac1a805a3168c5a306ac1a805"
                "a3168c5a306ac1a805a3160c150b009236603df43ffd0b0000000049454e44ae"
                "426082"
            ),
            "image/png",
            "prompt",
        )
        == ""
    )


async def test_async_liteparse_describer_returns_stripped_text():
    describer = AsyncLiteParseDescriber(parser=FakeParser(_parse_result(text=" text \n")))
    assert await describer(b"bytes", "image/png", "prompt") == "text"


async def test_async_liteparse_describer_miss_returns_empty():
    describer = AsyncLiteParseDescriber(parser=FakeParser(error=liteparse.ParseError("boom")))
    assert await describer(b"bytes", "image/png", "prompt") == ""


async def test_async_liteparse_describer_real_engine_end_to_end(raw, single_image_docx):
    result = await anytomd.convert_bytes_async(
        single_image_docx, "docx", async_image_describer=AsyncLiteParseDescriber()
    )
    assert result.warnings == []
    assert "![](image1.png)" in result.markdown


def test_async_liteparse_describer_real_engine_construction():
    assert isinstance(AsyncLiteParseDescriber(), AsyncLiteParseDescriber)


async def test_async_liteparse_describer_gate_bounds_ocr_fanout():
    state = {"live": 0, "peak": 0}

    class GateParser:
        async def aparse(self, data):
            state["live"] += 1
            state["peak"] = max(state["peak"], state["live"])
            await asyncio.sleep(0.01)
            state["live"] -= 1
            return _parse_result()

    describer = AsyncLiteParseDescriber(max_concurrency=2, parser=GateParser())
    await asyncio.gather(*(describer(b"x", "image/png", "p") for _ in range(8)))
    assert state["peak"] == 2


def test_openai_describer_sends_prompt_and_data_uri():
    completions = FakeCompletions()
    describer = OpenAIDescriber(model="vision-1", api_key="k", client=_fake_client(completions))
    assert describer(b"raw", "image/png", "Describe this.") == "A cat asleep on a chair"
    sent = completions.calls[0]
    assert sent["model"] == "vision-1"
    assert sent["messages"][0]["content"][0]["text"] == "Describe this."
    assert sent["messages"][0]["content"][1]["image_url"]["url"] == "data:image/png;base64," + "cmF3"


def test_openai_describer_prompt_override_wins_over_engine_prompt():
    completions = FakeCompletions()
    describer = OpenAIDescriber(model="v", prompt="My prompt", client=_fake_client(completions))
    describer(b"raw", "image/png", "Engine prompt")
    assert completions.calls[0]["messages"][0]["content"][0]["text"] == "My prompt"


def test_openai_describer_collapses_multiline_answer():
    describer = OpenAIDescriber(model="v", client=_fake_client(FakeCompletions(content="A cat\n\non a chair ")))
    assert describer(b"raw", "image/png", "p") == "A cat on a chair"


def test_openai_describer_silent_answer_is_empty():
    describer = OpenAIDescriber(model="v", client=_fake_client(FakeCompletions(content=None)))
    assert describer(b"raw", "image/png", "p") == ""


def test_openai_describer_provider_failure_propagates_for_the_engine_warning():
    describer = OpenAIDescriber(model="v", client=_fake_client(FakeCompletions(error=RuntimeError("429"))))
    with pytest.raises(RuntimeError, match="429"):
        describer(b"raw", "image/png", "p")


def test_openai_describer_default_client_resolves_the_extra():
    assert isinstance(OpenAIDescriber(model="v", api_key="k"), OpenAIDescriber)


async def test_async_openai_describer_returns_stripped_answer():
    describer = AsyncOpenAIDescriber(model="v", client=_fake_client(FakeAsyncCompletions()))
    assert await describer(b"raw", "image/png", "p") == "A cat asleep on a chair"


def test_async_openai_describer_default_client_resolves_the_extra():
    assert isinstance(AsyncOpenAIDescriber(model="v", api_key="k"), AsyncOpenAIDescriber)


def test_composite_vision_answers_only_when_ocr_finds_nothing():
    completions = FakeCompletions()
    composite = ImageDescriber(
        model="v",
        vlm_client=_fake_client(completions),
        ocr_parser=FakeParser(_parse_result(text="")),
    )
    assert composite(b"raw", "image/png", "p") == "A cat asleep on a chair"
    assert len(completions.calls) == 1


def test_composite_skips_vision_when_ocr_reads_text():
    completions = FakeCompletions()
    composite = ImageDescriber(
        model="v",
        vlm_client=_fake_client(completions),
        ocr_parser=FakeParser(_parse_result(text="Invoice 2026")),
    )
    assert composite(b"raw", "image/png", "p") == "Invoice 2026"
    assert completions.calls == []


def test_composite_stays_empty_when_every_layer_is_silent():
    composite = ImageDescriber(
        model="v",
        vlm_client=_fake_client(FakeCompletions(content="  ")),
        ocr_parser=FakeParser(_parse_result(text="")),
    )
    assert composite(b"raw", "image/png", "p") == ""


def test_composite_real_ocr_answers_and_vision_stays_unasked(path_of):
    completions = FakeCompletions()
    composite = ImageDescriber(model="v", vlm_client=_fake_client(completions))
    result = anytomd.convert_file(path_of("real_photo.png"), image_describer=composite)
    assert result.markdown == "![This is just an example.](image.png)\n"
    assert completions.calls == []


def test_composite_provider_failure_lands_as_engine_warning(single_image_docx):
    composite = ImageDescriber(
        model="v",
        vlm_client=_fake_client(FakeCompletions(error=RuntimeError("429"))),
        ocr_parser=FakeParser(_parse_result(text="")),
    )
    result = anytomd.convert_bytes(single_image_docx, "docx", image_describer=composite)
    assert [w.code for w in result.warnings] == ["skipped_element"]
    assert "429" in result.warnings[0].message


def test_composite_ocr_only_needs_no_vision(path_of):
    result = anytomd.convert_file(path_of("real_photo.png"), image_describer=ImageDescriber())
    assert "This is just an example." in result.markdown


def test_composite_without_any_capability_is_rejected():
    with pytest.raises(ValueError, match="nothing to describe"):
        ImageDescriber(ocr=False)


def test_composite_missing_extra_names_the_install(monkeypatch):
    monkeypatch.setitem(sys.modules, "liteparse", None)
    with pytest.raises(ImportError, match=r"anytomd\[ocr\]"):
        ImageDescriber()


def test_openai_describer_close_releases_the_client():
    events = []
    describer = OpenAIDescriber(model="v", client=_fake_client(FakeCompletions(), events))
    describer.close()
    assert events == ["close"]


async def test_async_openai_describer_aclose_releases_the_client():
    events = []
    describer = AsyncOpenAIDescriber(model="v", client=_fake_client(FakeAsyncCompletions(), events, async_close=True))
    await describer.aclose()
    assert events == ["aclose"]


def test_composite_close_releases_every_layer_that_owns_sockets():
    events = []
    composite = ImageDescriber(
        model="v",
        vlm_client=_fake_client(FakeCompletions(), events),
        ocr_parser=FakeParser(_parse_result(text="")),
    )
    composite.close()
    assert events == ["close"]


def test_composite_close_is_quiet_with_ocr_only():
    ImageDescriber(ocr_parser=FakeParser()).close()


async def test_async_composite_aclose_releases_the_vision_layer():
    events = []
    composite = AsyncImageDescriber(
        model="v",
        vlm_client=_fake_client(FakeAsyncCompletions(), events, async_close=True),
        ocr_parser=FakeParser(_parse_result(text="")),
    )
    await composite.aclose()
    assert events == ["aclose"]


async def test_async_composite_aclose_is_quiet_with_ocr_only():
    await AsyncImageDescriber(ocr_parser=FakeParser()).aclose()


async def test_async_composite_falls_back_to_vision_on_blank_ocr():
    completions = FakeAsyncCompletions()
    composite = AsyncImageDescriber(
        model="v",
        vlm_client=_fake_client(completions),
        ocr_parser=FakeParser(_parse_result(text="")),
    )
    assert await composite(b"raw", "image/png", "p") == "A cat asleep on a chair"


async def test_async_composite_keeps_ocr_text_off_the_wire():
    composite = AsyncImageDescriber(
        ocr_parser=FakeParser(_parse_result(text="Figure 3")),
    )
    assert await composite(b"raw", "image/png", "p") == "Figure 3"


async def test_async_composite_single_gate_bounds_every_layer():
    state = {"live": 0, "peak": 0}

    class GateParser:
        async def aparse(self, data):
            state["live"] += 1
            state["peak"] = max(state["peak"], state["live"])
            await asyncio.sleep(0.01)
            state["live"] -= 1
            return _parse_result(text="")

    composite = AsyncImageDescriber(
        model="v",
        max_concurrency=2,
        ocr_parser=GateParser(),
        vlm_client=_fake_client(FakeAsyncCompletions()),
    )
    await asyncio.gather(*(composite(b"x", "image/png", "p") for _ in range(8)))
    assert state["peak"] == 2


def test_async_composite_without_any_capability_is_rejected():
    with pytest.raises(ValueError, match="nothing to describe"):
        AsyncImageDescriber(ocr=False)


async def test_async_composite_ocr_off_answers_with_vision_only():
    completions = FakeAsyncCompletions()
    composite = AsyncImageDescriber(model="v", ocr=False, vlm_client=_fake_client(completions))
    assert await composite(b"raw", "image/png", "p") == "A cat asleep on a chair"


def test_capability_hint_points_at_its_extra():
    with pytest.raises(ImportError, match=r"install 'anytomd\[vlm\]'"):
        Capability("nonexistent_provider", "vlm").resolve()
