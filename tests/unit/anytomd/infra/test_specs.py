"""Specs: the defaults convert promises."""

from anytomd.infra.specs import ConversionSpec, VisionSpec


async def test_specs_conversion_defaults() -> None:
    spec = ConversionSpec()
    assert (spec.images, spec.comments, spec.strict, spec.ocr, spec.vision) == (False, False, False, True, None)
    assert (spec.max_input_bytes, spec.max_image_bytes, spec.max_zip_bytes) == (8 * 1024**3, 4 * 1024**3, 16 * 1024**3)


async def test_specs_vision_defaults() -> None:
    spec = VisionSpec(model="m")
    assert (spec.base_url, spec.api_key, spec.max_tokens, spec.concurrency) == (None, None, 256, 4)
