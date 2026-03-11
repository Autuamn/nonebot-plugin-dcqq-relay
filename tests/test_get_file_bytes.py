from tests.conftest import create_bot

from nonebug import App
import pytest
from pytest_httpserver import HTTPServer


@pytest.mark.asyncio
async def test_ssl_error(app: App, httpserver: HTTPServer) -> None:
    httpserver.expect_request("/test").respond_with_data("{}")
    url = httpserver.url_for("/test").replace("http://", "https://")

    from nonebot_plugin_dcqq_relay.utils import get_file_bytes

    async with app.test_api() as ctx:
        bot, _ = create_bot(ctx)
        assert await get_file_bytes(bot, url) == b"{}"
