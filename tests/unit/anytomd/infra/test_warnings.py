"""DocumentWarning: a frozen value, location optional."""

from anytomd.infra.warnings import DocumentWarning


async def test_warnings_location_optional() -> None:
    assert DocumentWarning("skipped_element", "gone").location is None
