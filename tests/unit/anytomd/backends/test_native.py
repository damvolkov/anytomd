"""NativeBackend and the compiled module: detection families, the hook bridge, engine panics and OS errors."""

import pytest

from anytomd import _native
from anytomd.backends.native import NativeBackend


@pytest.mark.parametrize(
    ("name", "data", "expected"),
    [("a.py", b"x", "py"), ("a.PNG", b"x", "png"), ("a.log", b"x", "log"), ("a.csv", b"x", "csv"), ("", b"x", None)],
    ids=["code", "image", "txt", "plain", "nothing"],
)
async def test_native_detect_resolves_families(name, data, expected) -> None:
    assert NativeBackend().detect(name, data) == expected


async def test_native_engine_version() -> None:
    assert _native.ENGINE_VERSION.count(".") == 2


async def test_native_hook_must_be_callable(raw) -> None:
    with pytest.raises(TypeError, match="callable"):
        _native.convert_bytes(raw("report.docx"), "docx", image_describer="nope")  # ty: ignore[invalid-argument-type]


async def test_native_async_hook_must_be_callable(raw) -> None:
    with pytest.raises(TypeError, match="callable"):
        await _native.convert_bytes_async(raw("report.docx"), "docx", async_image_describer=42)  # ty: ignore[invalid-argument-type]


async def test_native_non_coroutine_async_hook_degrades(single_image_docx) -> None:
    result = await _native.convert_bytes_async(single_image_docx, "docx", async_image_describer=lambda *a: "sync")  # ty: ignore[invalid-argument-type]
    assert [w.code for w in result.warnings] == ["skipped_element"]


async def test_native_non_string_hook_degrades(single_image_docx) -> None:
    result = _native.convert_bytes(single_image_docx, "docx", image_describer=lambda *a: 42)  # ty: ignore[invalid-argument-type]
    assert [w.code for w in result.warnings] == ["skipped_element"]


async def test_native_result_repr(raw) -> None:
    result = _native.convert_bytes("héllo".encode(), "txt")
    assert "markdown=5 chars" in repr(result)
    assert "unsupported_feature" in repr(_native.convert_bytes(b"Caf\xe9", "txt").warnings[0])
    assert result.markdown is result.markdown
