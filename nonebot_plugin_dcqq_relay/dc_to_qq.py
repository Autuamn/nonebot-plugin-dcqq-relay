import asyncio
import re

from nonebot import logger
from nonebot.adapters.discord import (
    Bot as dc_Bot,
    MessageCreateEvent,
    MessageDeleteEvent,
)
from nonebot.adapters.discord.api import UNSET
from nonebot.adapters.onebot.v11 import (
    Bot as qq_Bot,
    Message,
    MessageSegment,
)
from nonebot_plugin_orm import get_session
from sqlalchemy import select

from .config import LinkWithWebhook, plugin_config
from .model import MsgID
from .utils import get_dc_member_name, get_file_bytes

discord_proxy = plugin_config.discord_proxy


async def get_dc_channel_name(bot: dc_Bot, guild_id: int, channel_id: int) -> str:
    channels = await bot.get_guild_channels(guild_id=guild_id)
    channel = next(channel for channel in channels if channel.id == channel_id)
    return (
        channel.name
        if channel.name is not UNSET and channel.name is not None
        else "(error:无名频道)"
    )


async def get_dc_role_name(bot: dc_Bot, guild_id: int, role_id: int) -> str:
    roles = await bot.get_guild_roles(guild_id=guild_id)
    role = next(role for role in roles if role.id == role_id)
    return role.name


async def build_qq_message(
    bot: dc_Bot, event: MessageCreateEvent
) -> tuple[Message, list[str]]:
    qq_message = Message(
        MessageSegment.text(
            (
                event.member.nick
                if event.member is not UNSET
                and event.member.nick is not UNSET
                and event.member.nick
                else event.author.global_name or ""
            )
            + f"(@{event.author.username}):\n"
        )
    )
    img_url_list: list[str] = []
    message = (
        event
        if event.content
        else (
            await bot.get_channel_message(
                channel_id=event.channel_id, message_id=event.message_id
            )
        )
    )
    content = message.content
    text_begin = 0
    for embed in re.finditer(
        r"<(?P<type>(@!|@&|@|#|/|:|a:|t:))(?P<param>.+?)>",
        content,
    ):
        if text := content[text_begin : embed.pos + embed.start()]:
            qq_message += MessageSegment.text(text)
        text_begin = embed.pos + embed.end()
        if embed.group("type") in ("@!", "@"):
            nick, username = await get_dc_member_name(
                bot, event.guild_id, int(embed.group("param"))
            )
            qq_message += MessageSegment.text("@" + nick + f"({username})")
        elif embed.group("type") == "@&":
            qq_message += MessageSegment.text(
                "@"
                + (
                    await get_dc_role_name(
                        bot, event.guild_id, int(embed.group("param"))
                    )
                    if event.guild_id is not UNSET
                    else f"(error:未知用户组)({embed.group('param')})"
                )
            )
        elif embed.group("type") == "#":
            qq_message += MessageSegment.text(
                "#"
                + (
                    await get_dc_channel_name(
                        bot, event.guild_id, int(embed.group("param"))
                    )
                    if event.guild_id is not UNSET
                    else f"(error:未知频道)({embed.group('param')})"
                )
            )
        elif embed.group("type") == "/":
            pass
        elif embed.group("type") in (":", "a:"):
            if len(cut := embed.group("param").split(":")) == 2:
                if not cut[1]:
                    qq_message += MessageSegment.text(cut[0])
                else:
                    qq_message.append(
                        MessageSegment.image(
                            await get_file_bytes(
                                "https://cdn.discordapp.com/emojis/"
                                + cut[1]
                                + "."
                                + ("gif" if embed.group("type") == "a:" else "webp"),
                                discord_proxy,
                            )
                        )
                    )
            else:
                qq_message += MessageSegment.text(embed.group())
        else:
            if embed.group().isdigit():
                qq_message += MessageSegment.text(f'<t:{embed.group("param")}>')
            else:
                qq_message += MessageSegment.text(embed.group())
    if text := content[text_begin:]:
        qq_message += MessageSegment.text(text)

    if event.mention_everyone:
        qq_message += MessageSegment.at("all")

    if attachments := message.attachments:
        for attachment in attachments:
            if attachment.content_type is not UNSET and re.match(
                r"image/(gif|jpeg|png|webp)", attachment.content_type, 0
            ):
                img_url_list.append(attachment.url)
        logger.debug(img_url_list)

    return qq_message, img_url_list


async def create_dc_to_qq(
    bot: dc_Bot,
    event: MessageCreateEvent,
    qq_bot: qq_Bot,
    channel_links: list[LinkWithWebhook],
):
    """discord 消息转发到 QQ"""
    event.get_message()
    message, img_url_list = await build_qq_message(bot, event)
    link = next(
        link for link in channel_links if link.dc_channel_id == event.channel_id
    )

    async with get_session() as session:
        if (
            event.message_reference is not UNSET
            and (message_id := event.message_reference.message_id)
            and message_id is not UNSET
            and (
                reply_id := await session.scalar(
                    select(MsgID.qqid).filter(MsgID.dcid == message_id).fetch(1)
                )
            )
        ):
            message += MessageSegment.reply(reply_id)

    if img_url_list:
        get_img_tasks = [get_file_bytes(url, discord_proxy) for url in img_url_list]
        imgs = await asyncio.gather(*get_img_tasks)
        message.extend(MessageSegment.image(img) for img in imgs)

    try_times = 1
    while True:
        try:
            send = await qq_bot.send_group_msg(
                group_id=link.qq_group_id, message=message
            )
            break
        except NameError as e:
            logger.warning(f"retry {try_times}")
            if try_times >= 3:
                raise e
            try_times += 1
            await asyncio.sleep(5)

    async with get_session() as session:
        session.add(MsgID(dcid=event.id, qqid=send["message_id"]))
        await session.commit()


async def delete_dc_to_qq(
    event: MessageDeleteEvent,
    qq_bot: qq_Bot,
    just_delete: list,
):
    if (id := event.id) in just_delete:
        just_delete.remove(id)
        return
    try_times = 1
    while True:
        try:
            async with get_session() as session:
                if msgids := await session.scalars(
                    select(MsgID).filter(MsgID.dcid == event.id)
                ):
                    for msgid in msgids:
                        await qq_bot.delete_msg(message_id=msgid.qqid)
                        just_delete.append(msgid.qqid)
                        await session.delete(msgid)
                    await session.commit()
            break
        except UnboundLocalError or TypeError or NameError as e:
            logger.warning(f"retry {try_times}")
            if try_times == 3:
                raise e
            try_times += 1
            await asyncio.sleep(5)
