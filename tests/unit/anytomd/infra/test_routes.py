"""Routes: three destinations."""

from anytomd.infra.routes import Route


async def test_routes_members() -> None:
    assert [route.value for route in Route] == ["native", "image", "pdf"]
