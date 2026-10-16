"""The package surface: `import anytomd as ad` exposes the verbs, their a-twins, the types and the versions."""

import importlib.metadata
import inspect

import pytest

import anytomd as ad

VERBS = ["convert", "detect", "describe"]


@pytest.mark.parametrize("verb", VERBS, ids=VERBS)
async def test_package_every_verb_has_its_async_twin(verb) -> None:
    sync, async_ = getattr(ad, verb), getattr(ad, f"a{verb}")
    assert not inspect.iscoroutinefunction(sync)
    assert inspect.iscoroutinefunction(async_)
    assert inspect.signature(sync).parameters.keys() == inspect.signature(async_).parameters.keys()


async def test_package_all_is_exported() -> None:
    assert all(hasattr(ad, name) for name in ad.__all__)


async def test_package_versions() -> None:
    assert ad.__version__ == importlib.metadata.version("anytomd")
    assert ad.ENGINE_VERSION.count(".") == 2
