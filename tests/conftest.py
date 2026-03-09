import nonebot
from nonebot.adapters.discord import (
    Adapter as DCAdapter,
    Bot as DCBot,
)
from nonebot.adapters.onebot.v11 import (
    Adapter as QQAdapter,
    Bot as QQBot,
)
from nonebug import NONEBOT_INIT_KWARGS
from nonebug.mixin.call_api import ApiContext
import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.stash[NONEBOT_INIT_KWARGS] = {
        "driver": "nonebot.drivers.aiohttp",
        "log_level": "TRACE",
        "alembic_startup_check": False,
        "dcqq_relay_channel_links": [
            {
                "dc_guild_id": int("6" * 18),
                "dc_channel_id": int("2" * 18),
                "qq_group_id": 10001,
            },
            {
                "dc_guild_id": int("6" * 18),
                "dc_channel_id": int("8" * 18),
                "qq_group_id": 10002,
            },
            {
                "dc_guild_id": int("6" * 18),
                "dc_channel_id": int("9" * 18),
                "qq_group_id": 10002,
                "webhook_id": 1000000000000000001,
                "webhook_token": "xxxxxxxxxx",
            },
            {
                "dc_guild_id": int("6" * 18),
                "dc_channel_id": int("7" * 18),
                "qq_group_id": 10002,
            },
        ],
        "localstore_data_dir": "./data",
    }


@pytest.fixture(scope="session", autouse=True)
async def after_nonebot_init(after_nonebot_init: None):
    # 加载适配器
    driver = nonebot.get_driver()
    driver.register_adapter(DCAdapter)
    driver.register_adapter(QQAdapter)

    # 加载插件
    nonebot.load_plugin("nonebot_plugin_dcqq_relay")


def create_bot(ctx: ApiContext) -> tuple[QQBot, DCBot]:
    dc_adapter = nonebot.get_adapter(DCAdapter)
    qq_adapter = nonebot.get_adapter(QQAdapter)
    qq_bot = ctx.create_bot(
        base=QQBot,
        adapter=qq_adapter,
    )
    dc_bot: DCBot = ctx.create_bot(
        base=DCBot,
        adapter=dc_adapter,
        bot_info=None,
        self_id="12345",
        auto_connect=False,
    )
    return qq_bot, dc_bot
