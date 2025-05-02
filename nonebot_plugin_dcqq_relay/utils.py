import re
import ssl
from typing import Optional, Union

import pysilk
from pydub import AudioSegment
from io import BytesIO

from nonebot import logger
from nonebot.adapters import Bot
from nonebot.internal.driver import Request
from nonebot.adapters.discord import (
    Bot as dc_Bot,
    GuildMessageCreateEvent,
    GuildMessageDeleteEvent,
)
from nonebot.adapters.discord.api import UNSET, Missing
from nonebot.adapters.discord.exception import ActionFailed
from nonebot.adapters.onebot.v11 import (
    GroupMessageEvent,
    GroupRecallNoticeEvent,
)
from nonebot.compat import model_dump

from .config import LinkWithoutWebhook, LinkWithWebhook, plugin_config

channel_links: list[LinkWithoutWebhook] = plugin_config.dcqq_relay_channel_links
discord_proxy = plugin_config.discord_proxy


async def check_messages(
    event: Union[
        GroupMessageEvent,
        GuildMessageCreateEvent,
        GroupRecallNoticeEvent,
        GuildMessageDeleteEvent,
    ],
) -> bool:
    """检查消息"""
    logger.debug("into check_messages()")
    if isinstance(event, GroupMessageEvent):
        return any(event.group_id == link.qq_group_id for link in channel_links)
    elif isinstance(event, GuildMessageCreateEvent):
        if not (
            re.match(r".*?\[QQ:\d*?\]$", event.author.username)
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
    elif isinstance(event, GuildMessageDeleteEvent):
        return any(
            event.guild_id == link.dc_guild_id
            and event.channel_id == link.dc_channel_id
            for link in channel_links
        )


async def check_to_me(
    event: Union[
        GroupMessageEvent,
        GuildMessageCreateEvent,
        GroupRecallNoticeEvent,
        GuildMessageDeleteEvent,
    ],
) -> bool:
    if isinstance(event, (GroupMessageEvent, GuildMessageCreateEvent)):
        return event.to_me
    return True


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


async def get_file_bytes(bot: Bot, url: str, proxy: Optional[str] = None) -> bytes:
    try:
        resp = await bot.adapter.request(Request("GET", url, proxy=proxy))
        if isinstance(resp.content, bytes):
            return resp.content
        else:
            raise TypeError("Response content is not bytes")
    except ssl.SSLError as e:
        if url.startswith("http://"):
            raise e
        url = url.replace("https://", "http://")
        return await get_file_bytes(bot, url, proxy)


async def get_webhook(
    bot: dc_Bot, link: LinkWithoutWebhook
) -> Union[LinkWithWebhook, int]:
    if link.webhook_id and link.webhook_token:
        return LinkWithWebhook(**model_dump(link))
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
            return build_link(link, bot_webhook.id, bot_webhook.token)
    except Exception as e:
        logger.error(
            f"get webhook error, Discord channel id: {link.dc_channel_id}, error: {e}"
        )
    try:
        create_webhook = await bot.create_webhook(
            channel_id=link.dc_channel_id, name=str(link.dc_channel_id)
        )
        if create_webhook.token:
            return build_link(link, create_webhook.id, create_webhook.token)
    except Exception as e:
        logger.error(
            f"create webhook error, Discord channel id: {link.dc_channel_id}, "
            + f"error: {e}"
        )
    logger.error(
        f"failed to get or create webhook, Discord channel id: {link.dc_channel_id}"
    )
    return link.dc_channel_id


def build_link(
    link: LinkWithoutWebhook, webhook_id: int, webhook_token: str
) -> LinkWithWebhook:
    return LinkWithWebhook(
        webhook_id=webhook_id,
        webhook_token=webhook_token,
        **model_dump(link, exclude={"webhook_id", "webhook_token"}),
    )


def pydub_transform(origin_bytes: bytes, input_type: str, output_type: str) -> bytes:
    output_buffer = BytesIO()  # 创建内存文件对象

    audio = AudioSegment.from_file(BytesIO(origin_bytes), format=input_type)
    audio.export(output_buffer, format=output_type, bitrate="128k")

    output_buffer.seek(0)  # 重置指针
    return output_buffer.read()


def skil_to_ogg(skil_bytes: bytes) -> bytes:
    output_buffer = BytesIO()

    pcm_bytes = pysilk.decode(skil_bytes, True, sample_rate=44100)
    audio = AudioSegment.from_file(BytesIO(pcm_bytes), format="wav")
    audio.export(output_buffer, format="ogg")

    output_buffer.seek(0)
    return output_buffer.read()


async def get_dc_member_avatar(bot: dc_Bot, guild_id: int, user_id: int) -> str:
    member = await bot.get_guild_member(guild_id=guild_id, user_id=user_id)
    if member.avatar is not UNSET and (avatar := member.avatar):
        return (
            f"https://cdn.discordapp.com/guilds/{guild_id}/users/{user_id}/avatars/{avatar}."
            + ("gif" if re.match(r"^a_.*", avatar) else "webp")
        )
    elif (user := member.user) and user is not UNSET and user.avatar:
        return f"https://cdn.discordapp.com/avatars/{user_id}/{user.avatar}." + (
            "gif" if re.match(r"^a_.*", user.avatar) else "webp"
        )
    else:
        return ""
