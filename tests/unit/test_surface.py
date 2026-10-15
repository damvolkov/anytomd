"""Package surface: exports, version, callable signatures."""

import inspect

import pytest

import anytomd

OPTIONAL_KWARGS = [
    "extract_images",
    "extract_comments",
    "strict",
    "max_input_bytes",
    "max_total_image_bytes",
    "max_uncompressed_zip_bytes",
]


def test_public_surface_is_complete():
    assert set(anytomd.__all__) <= set(dir(anytomd))
    for name in anytomd.__all__:
        assert hasattr(anytomd, name)


def test_version_is_exposed():
    parts = anytomd._native.__version__.split(".")
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)


@pytest.mark.parametrize("function", [anytomd.convert_file, anytomd.convert_file_async])
def test_file_entrypoints_expose_every_option(function):
    signature = inspect.signature(function)
    assert "path" in signature.parameters
    for option in OPTIONAL_KWARGS[:5]:
        assert option in signature.parameters


def test_bytes_entrypoints_expose_format_and_describer():
    sync = inspect.signature(anytomd.convert_bytes)
    assert {"data", "format", "image_describer"} <= set(sync.parameters)
    async_ = inspect.signature(anytomd.convert_bytes_async)
    assert {"data", "format", "async_image_describer"} <= set(async_.parameters)


def test_detect_helpers_signatures():
    assert set(inspect.signature(anytomd.detect_format).parameters) == {"path", "data"}
    assert set(inspect.signature(anytomd.detect_zip_format).parameters) == {"data"}


async def test_async_entrypoints_return_awaitables():
    coroutine = anytomd.convert_bytes_async(b"hello", "txt")
    assert hasattr(coroutine, "__await__")
    result = await coroutine
    assert result.markdown == "hello"
