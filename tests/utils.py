from tests.data import (
    create_webhook_result,
    get_channel_webhooks_result,
)

import nonebot
from nonebot.adapters.discord import (
    Adapter as DCAdapter,
    Bot as DCBot,
)
from nonebot.adapters.onebot.v11 import (
    Adapter as QQAdapter,
    Bot as QQBot,
)
from nonebug.mixin.process import ApiContext


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


def prepare_webhooks_calls(ctx: ApiContext) -> None:
    ctx.should_call_api(
        "get_channel_webhooks",
        {"channel_id": int("2" * 18)},
        get_channel_webhooks_result(12345),
    )
    ctx.should_call_api(
        "get_channel_webhooks",
        {"channel_id": int("8" * 18)},
        get_channel_webhooks_result(66666),
    )
    ctx.should_call_api(
        "create_webhook",
        {"channel_id": int("8" * 18), "name": "8" * 18},
        create_webhook_result(12345),
    )
    ctx.should_call_api(
        "get_channel_webhooks",
        {"channel_id": int("7" * 18)},
        exception=Exception(),
    )
    ctx.should_call_api(
        "create_webhook",
        {"channel_id": int("7" * 18), "name": "7" * 18},
        exception=Exception(),
    )
