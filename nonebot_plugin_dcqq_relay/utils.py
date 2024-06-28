import re
from typing import Optional, Union

import aiohttp
from nonebot import logger
from nonebot.adapters.discord import (
    Bot as dc_Bot,
    MessageCreateEvent,
    MessageDeleteEvent,
)
from nonebot.adapters.discord.api import UNSET, Missing
from nonebot.adapters.discord.exception import ActionFailed
from nonebot.adapters.onebot.v11 import (
    Bot as qq_Bot,
    GroupMessageEvent,
    GroupRecallNoticeEvent,
)

from .config import LinkWithoutWebhook, LinkWithWebhook, plugin_config


channel_links: list[LinkWithoutWebhook] = plugin_config.dcqq_relay_channel_links
discord_proxy = plugin_config.discord_proxy


async def check_messages(
    bot: Union[qq_Bot, dc_Bot],
    event: Union[
        GroupMessageEvent,
        MessageCreateEvent,
        GroupRecallNoticeEvent,
        MessageDeleteEvent,
    ],
) -> bool:
    """检查消息"""
    logger.debug("into check_messages()")
    if isinstance(event, GroupMessageEvent):
        return any(event.group_id == link.qq_group_id for link in channel_links)
    elif isinstance(event, MessageCreateEvent):
        if not (
            re.match(r".*? \[QQ:\d*?\]$", event.author.username)
            and event.author.bot is True
        ):
            return any(
                event.guild_id == link.dc_guild_id
                and event.channel_id == link.dc_channel_id
                for link in channel_links
            )
        else:
            return False
    elif isinstance(event, GroupRecallNoticeEvent):
        return any(event.group_id == link.qq_group_id for link in channel_links)
    elif isinstance(event, MessageDeleteEvent):
        return any(
            event.guild_id == link.dc_guild_id
            and event.channel_id == link.dc_channel_id
            for link in channel_links
        )


async def get_dc_member_name(
    bot: dc_Bot, guild_id: Missing[int], user_id: int
) -> tuple[str, str]:
    try:
        if guild_id is not UNSET:
            member = await bot.get_guild_member(guild_id=guild_id, user_id=user_id)
            if (nick := member.nick) and nick is not UNSET:
                return nick, member.user.username if member.user is not UNSET else ""
            elif member.user is not UNSET and (global_name := member.user.global_name):
                return global_name, member.user.username
            else:
                return "", str(user_id)
        else:
            user = await bot.get_user(user_id=user_id)
            return user.global_name or "", user.username
    except ActionFailed as e:
        if e.message == "Unknown User":
            return "(error:未知用户)", str(user_id)
        else:
            raise e


async def get_file_bytes(url: str, proxy: Optional[str] = None) -> bytes:
    async with (
        aiohttp.ClientSession() as session,
        session.get(url, proxy=proxy) as response,
    ):
        return await response.read()


async def get_webhook(
    bot: dc_Bot, link: LinkWithoutWebhook
) -> Union[LinkWithWebhook, int]:
    if link.webhook_id and link.webhook_token:
        return LinkWithWebhook(**link.model_dump())
    try:
        channel_webhooks = await bot.get_channel_webhooks(channel_id=link.dc_channel_id)
        bot_webhook = next(
            (
                webhook
                for webhook in channel_webhooks
                if webhook.application_id == int(bot.self_id)
            ),
            None,
        )
        if bot_webhook and bot_webhook.token:
            return await build_link(link, bot_webhook.id, bot_webhook.token)
    except Exception as e:
        logger.error(
            f"get webhook error, Discord channel id: {link.dc_channel_id}, error: {e}"
        )
    try:
        create_webhook = await bot.create_webhook(
            channel_id=link.dc_channel_id, name=str(link.dc_channel_id)
        )
        if create_webhook.token:
            return await build_link(link, create_webhook.id, create_webhook.token)
    except Exception as e:
        logger.error(
            f"create webhook error, Discord channel id: {link.dc_channel_id}, "
            + f"error: {e}"
        )
    logger.error(
        f"failed to get or create webhook, Discord channel id: {link.dc_channel_id}"
    )
    return link.dc_channel_id


async def build_link(
    link: LinkWithoutWebhook, webhook_id: int, webhook_token: str
) -> LinkWithWebhook:
    return LinkWithWebhook(
        webhook_id=webhook_id,
        webhook_token=webhook_token,
        **link.model_dump(exclude={"webhook_id", "webhook_token"}),
    )
