import asyncio

from nonebot import get_driver, logger, on, require
from nonebot.adapters import Event
from nonebot.adapters.discord import (
    Bot as dc_Bot,
    GuildMessageCreateEvent,
    GuildMessageDeleteEvent,
)
from nonebot.adapters.onebot.v11 import (
    Bot as qq_Bot,
    GroupMessageEvent,
    GroupRecallNoticeEvent,
)
from nonebot.params import Depends
from nonebot.plugin import PluginMetadata
from nonebot.rule import Rule, StartswithRule
from nonebot.typing import T_State

require("nonebot_plugin_orm")
require("nonebot_plugin_localstore")

from .config import (
    Config,
    LinkWithWebhook,
    only_to_me,
    unmatch_beginning,
)
from .dc_to_qq import create_dc_to_qq, delete_dc_to_qq
from .qq_to_dc import create_qq_to_dc, delete_qq_to_dc
from .utils import check_messages, check_to_me, get_link, get_webhooks

__plugin_meta__ = PluginMetadata(
    name="QQ群-Discord 互通",
    description="在QQ群与 Discord 之间同步消息的 nonebot2 插件",
    usage="",
    type="application",
    homepage="https://github.com/Autuamn/nonebot-plugin-dcqq-relay",
    config=Config,
    supported_adapters={"~onebot.v11", "~discord"},
)


driver = get_driver()
with_webhook_links: list[LinkWithWebhook] = []
just_delete = []


class NotStartswithRule(StartswithRule):
    async def __call__(self, event: Event, state: T_State) -> bool:
        return not await super().__call__(event, state)


matcher = on(
    rule=(
        Rule(NotStartswithRule(tuple(unmatch_beginning)))
        & check_messages
        & (check_to_me if only_to_me else None)
    ),
    priority=2,
)


@driver.on_bot_connect
async def prepare_webhooks(bot: dc_Bot):
    logger.info("prepare webhooks: start")
    failed = await get_webhooks(bot)
    logger.info("prepare webhooks: done")
    if failed:
        logger.error(
            f"{len(failed)} channels failed to get or create webhook: {failed}"
        )


@matcher.handle()
async def message_relay(
    bot: qq_Bot | dc_Bot,
    event: (
        GroupMessageEvent
        | GuildMessageCreateEvent
        | GroupRecallNoticeEvent
        | GuildMessageDeleteEvent
    ),
    link: LinkWithWebhook | None = Depends(get_link),
):
    if link is None:
        logger.warning("fail to get channel link")
        matcher.finish()
        return
    logger.debug("message relay: start")
    for try_times in range(3):
        try:
            if isinstance(bot, qq_Bot) and isinstance(event, GroupMessageEvent):
                await create_qq_to_dc(bot, event, link)
            elif isinstance(bot, dc_Bot) and isinstance(event, GuildMessageCreateEvent):
                await create_dc_to_qq(bot, event, link)
            elif isinstance(bot, qq_Bot) and isinstance(event, GroupRecallNoticeEvent):
                await delete_qq_to_dc(event, link, just_delete)
            elif isinstance(bot, dc_Bot) and isinstance(event, GuildMessageDeleteEvent):
                await delete_dc_to_qq(event, link, just_delete)
            else:
                logger.error(
                    "bot type and event type not match: "
                    + f"bot - {bot.type}, event - {type(event)}"
                )
            logger.debug("message relay: done")
            break
        except NameError as e:
            logger.warning(f"message relay error: {e}, retry {try_times + 1}")
            if try_times == 3:
                raise e
            await asyncio.sleep(5)
    else:
        logger.error("message relay: failed")
