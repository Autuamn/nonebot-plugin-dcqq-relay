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

from nonebot_plugin_dcqq_relay.config import Link, plugin_config

channel_links: list[Link] = plugin_config.dcqq_relay_channel_links
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
    async with aiohttp.ClientSession() as session:  # noqa: SIM117
        async with session.get(url, proxy=proxy) as response:
            return await response.read()
