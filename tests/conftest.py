import nonebot
from nonebot.adapters.discord import Adapter as DCAdapter
from nonebot.adapters.onebot import V11Adapter
from nonebug import NONEBOT_INIT_KWARGS
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
    driver.register_adapter(V11Adapter)

    # 加载插件
    nonebot.load_plugin("nonebot_plugin_dcqq_relay")
