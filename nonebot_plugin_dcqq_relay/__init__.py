import asyncio
import re
from typing import Union

from nonebot import get_driver, logger, on, on_regex
from nonebot.adapters.discord import (
    Bot as dc_Bot,
    MessageCreateEvent,
    MessageDeleteEvent,
)
from nonebot.adapters.onebot.v11 import (
    Bot as qq_Bot,
    GroupMessageEvent,
    GroupRecallNoticeEvent,
)
from nonebot.plugin import PluginMetadata

from .config import Config, LinkWithoutWebhook, LinkWithWebhook, plugin_config
from .dc_to_qq import create_dc_to_qq, delete_dc_to_qq
from .qq_to_dc import create_qq_to_dc, delete_qq_to_dc
from .utils import check_messages, get_webhook


__plugin_meta__ = PluginMetadata(
    name="QQ频道-Discord 互通",
    description="在QQ频道与 Discord 之间同步消息的 nonebot2 插件",
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

unmatcher = on_regex(
    rf'\A *?[{re.escape("".join(unmatch_beginning))}].*', priority=1, block=True
)
matcher = on(rule=check_messages, priority=2, block=False)


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


@unmatcher.handle()
async def unmatcher_pass():
    pass


@matcher.handle()
async def create_message(
    bot: Union[qq_Bot, dc_Bot],
    event: Union[GroupMessageEvent, MessageCreateEvent],
):
    logger.debug("into create_message()")
    try_times = 1
    while True:
        try:
            if isinstance(bot, qq_Bot) and isinstance(event, GroupMessageEvent):
                await create_qq_to_dc(bot, event, dc_bot, with_webhook_links)
            elif isinstance(bot, dc_Bot) and isinstance(event, MessageCreateEvent):
                await create_dc_to_qq(bot, event, qq_bot, with_webhook_links)
            else:
                logger.error(
                    "bot type and event type not match: "
                    + f"bot - {bot.type}, event - {type(event)}"
                )
            break
        except NameError as e:
            logger.warning(f"create_message() error: {e}, retry {try_times}")
            if try_times == 3:
                raise e
            try_times += 1
            await asyncio.sleep(5)


@matcher.handle()
async def delete_message(
    bot: Union[qq_Bot, dc_Bot],
    event: Union[GroupRecallNoticeEvent, MessageDeleteEvent],
):
    logger.debug("into delete_message()")
    try_times = 1
    while True:
        try:
            if isinstance(bot, qq_Bot) and isinstance(event, GroupRecallNoticeEvent):
                await delete_qq_to_dc(event, dc_bot, with_webhook_links, just_delete)
            elif isinstance(bot, dc_Bot) and isinstance(event, MessageDeleteEvent):
                await delete_dc_to_qq(event, qq_bot, just_delete)
            else:
                logger.error(
                    "bot type and event type not match: "
                    + f"bot - {bot.type}, event - {type(event)}"
                )
            break
        except NameError as e:
            logger.warning(f"delete_message() error: {e}, retry {try_times}")
            if try_times == 3:
                raise e
            try_times += 1
            await asyncio.sleep(5)
