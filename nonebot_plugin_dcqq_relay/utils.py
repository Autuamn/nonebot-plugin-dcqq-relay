import asyncio
from io import BytesIO
import re
import ssl

from filetype import match
from nonebot import logger
from nonebot.adapters import Bot
from nonebot.adapters.discord import (
    Bot as dc_Bot,
    GuildMessageCreateEvent,
    GuildMessageDeleteEvent,
    is_not_unset,
)
from nonebot.adapters.discord.exception import ActionFailed
from nonebot.adapters.onebot.v11 import (
    Bot as qq_Bot,
    GroupMessageEvent,
    GroupRecallNoticeEvent,
)
from nonebot.compat import model_dump
from nonebot.internal.driver import Request
from pydub import AudioSegment
import pysilk

from .config import LinkWithoutWebhook, LinkWithWebhook, channel_links

with_webhook_links: list[LinkWithWebhook] = []


def check_messages(
    event: (
        GroupMessageEvent
        | GuildMessageCreateEvent
        | GroupRecallNoticeEvent
        | GuildMessageDeleteEvent
    ),
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


def check_to_me(
    event: (
        GroupMessageEvent
        | GuildMessageCreateEvent
        | GroupRecallNoticeEvent
        | GuildMessageDeleteEvent
    ),
) -> bool:
    if isinstance(event, GroupMessageEvent | GuildMessageCreateEvent):
        return event.to_me
    return True


def get_link(
    bot: qq_Bot | dc_Bot,
    event: (
        GroupMessageEvent
        | GuildMessageCreateEvent
        | GroupRecallNoticeEvent
        | GuildMessageDeleteEvent
    ),
) -> LinkWithWebhook | None:
    return next(
        (
            link
            for link in with_webhook_links
            if (
                (link.dc_channel_id == event.channel_id)
                if isinstance(event, GuildMessageCreateEvent | GuildMessageDeleteEvent)
                else False
            )
            or (
                (link.qq_group_id == event.group_id)
                if isinstance(event, GroupMessageEvent | GroupRecallNoticeEvent)
                else False
            )
        ),
        None,
    )


async def get_dc_member_name(
    bot: dc_Bot, guild_id: int, user_id: int
) -> tuple[str, str]:
    try:
        member = await bot.get_guild_member(guild_id=guild_id, user_id=user_id)
        if (nick := member.nick) and is_not_unset(nick):
            return nick, member.user.username if is_not_unset(member.user) else ""
        elif is_not_unset(member.user) and (global_name := member.user.global_name):
            return global_name, member.user.username
        else:
            return "", str(user_id)
    except ActionFailed as e:
        if e.message == "Unknown User":
            return "(error:未知用户)", str(user_id)
        elif e.message == "Unknown Guild":
            user = await bot.get_user(user_id=user_id)
            return user.global_name or "", user.username
        else:
            raise e


async def get_file_bytes(bot: Bot, url: str, proxy: str | None = None) -> bytes:
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


async def get_webhook(bot: dc_Bot, link: LinkWithoutWebhook) -> LinkWithWebhook | int:
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
        if bot_webhook and is_not_unset(bot_webhook.token):
            return build_link(link, bot_webhook.id, bot_webhook.token)
    except Exception as e:
        logger.error(
            f"get webhook error, Discord channel id: {link.dc_channel_id}, error: {e}"
        )
    try:
        create_webhook = await bot.create_webhook(
            channel_id=link.dc_channel_id, name=str(link.dc_channel_id)
        )
        if is_not_unset(create_webhook.token):
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


async def get_webhooks(bot: dc_Bot) -> list[int]:
    global with_webhook_links
    task = [get_webhook(bot, link) for link in channel_links]
    links = await asyncio.gather(*task)
    with_webhook_links.extend(
        link for link in links if isinstance(link, LinkWithWebhook)
    )
    return [link for link in links if isinstance(link, int)]


def pydub_transform(origin_bytes: bytes, input_type: str, output_type: str) -> bytes:
    output_buffer = BytesIO()  # 创建内存文件对象

    audio = AudioSegment.from_file(BytesIO(origin_bytes), format=input_type)
    audio.export(output_buffer, format=output_type, bitrate="128k")

    output_buffer.seek(0)  # 重置指针
    return output_buffer.read()


def skil_to_ogg(origi_bytes: bytes) -> bytes:
    output_buffer = BytesIO()

    ft_match = match(origi_bytes)
    if not ft_match:
        pcm_bytes = pysilk.decode(origi_bytes, True, sample_rate=24000)
        audio = AudioSegment.from_file(BytesIO(pcm_bytes), format="wav")
    else:
        audio = AudioSegment.from_file(BytesIO(origi_bytes), format=ft_match.extension)
    audio.export(output_buffer, format="ogg")

    output_buffer.seek(0)
    return output_buffer.read()


async def get_dc_member_avatar(bot: dc_Bot, guild_id: int, user_id: int) -> str:
    member = await bot.get_guild_member(guild_id=guild_id, user_id=user_id)
    if (avatar := member.avatar) and is_not_unset(avatar):
        return (
            f"https://cdn.discordapp.com/guilds/{guild_id}/users/{user_id}/avatars/{avatar}."
            + ("gif" if re.match(r"^a_.*", avatar) else "webp")
        )
    elif (user := member.user) and is_not_unset(user) and user.avatar is not None:
        return f"https://cdn.discordapp.com/avatars/{user_id}/{user.avatar}." + (
            "gif" if re.match(r"^a_.*", user.avatar) else "webp"
        )
    else:
        return ""
