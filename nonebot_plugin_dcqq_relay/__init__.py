import asyncio
from typing import Union

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
from nonebot.plugin import PluginMetadata
from nonebot.rule import Rule, StartswithRule
from nonebot.typing import T_State

require("nonebot_plugin_orm")
require("nonebot_plugin_localstore")

from .config import Config, LinkWithoutWebhook, LinkWithWebhook, plugin_config
from .dc_to_qq import create_dc_to_qq, delete_dc_to_qq
from .qq_to_dc import create_qq_to_dc, delete_qq_to_dc
from .utils import check_messages, check_to_me, get_webhook

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
without_webhook_links: list[LinkWithoutWebhook] = plugin_config.dcqq_relay_channel_links
with_webhook_links: list[LinkWithWebhook] = []
discord_proxy = plugin_config.discord_proxy
unmatch_beginning = plugin_config.dcqq_relay_unmatch_beginning

just_delete = []


class NotStartswithRule(StartswithRule):
    async def __call__(self, event: Event, state: T_State) -> bool:
        return not await super().__call__(event, state)


matcher = on(
    rule=(
        Rule(NotStartswithRule(tuple(unmatch_beginning)))
        & check_messages
        & (check_to_me if plugin_config.dcqq_relay_only_to_me else None)
    ),
    priority=2,
)


@driver.on_bot_connect
async def get_dc_bot(bot: dc_Bot):
    global dc_bot
    dc_bot = bot


@driver.on_bot_connect
async def get_qq_bot(bot: qq_Bot):
    global qq_bot
    qq_bot = bot


@driver.on_bot_connect
async def get_webhooks(bot: dc_Bot):
    logger.info("prepare webhooks: start")
    global with_webhook_links
    task = [get_webhook(bot, link) for link in without_webhook_links]
    links = await asyncio.gather(*task)
    with_webhook_links.extend(
        link for link in links if isinstance(link, LinkWithWebhook)
    )
    logger.info("prepare webhooks: done")
    if failed := [link for link in links if isinstance(link, int)]:
        logger.error(
            f"{len(failed)} channels failed to get or create webhook: {failed}"
        )


@matcher.handle()
async def message_relay(
    bot: Union[qq_Bot, dc_Bot],
    event: Union[
        GroupMessageEvent,
        GuildMessageCreateEvent,
        GroupRecallNoticeEvent,
        GuildMessageDeleteEvent,
    ],
):
    logger.debug("message relay: start")
    for try_times in range(3):
        try:
            if isinstance(bot, qq_Bot) and isinstance(event, GroupMessageEvent):
                await create_qq_to_dc(bot, event, dc_bot, with_webhook_links)
            elif isinstance(bot, dc_Bot) and isinstance(event, GuildMessageCreateEvent):
                await create_dc_to_qq(bot, event, qq_bot, with_webhook_links)
            elif isinstance(bot, qq_Bot) and isinstance(event, GroupRecallNoticeEvent):
                await delete_qq_to_dc(event, dc_bot, with_webhook_links, just_delete)
            elif isinstance(bot, dc_Bot) and isinstance(event, GuildMessageDeleteEvent):
                await delete_dc_to_qq(event, qq_bot, just_delete)
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
