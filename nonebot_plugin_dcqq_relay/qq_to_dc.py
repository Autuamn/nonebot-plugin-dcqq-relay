import asyncio
import re
from typing import Optional

import filetype
from nonebot import logger
from nonebot.adapters.discord import Bot as dc_Bot
from nonebot.adapters.discord.api import UNSET, Embed, EmbedAuthor, File, MessageGet
from nonebot.adapters.discord.exception import NetworkError
from nonebot.adapters.onebot.v11 import (
    Bot as qq_Bot,
    GroupMessageEvent,
    GroupRecallNoticeEvent,
)
from nonebot.adapters.onebot.v11.event import Reply
from nonebot_plugin_orm import get_session
from sqlalchemy import select

from .config import LinkWithWebhook
from .qq_emoji_dict import qq_emoji_dict
from .model import MsgID
from .utils import get_dc_member_name, get_file_bytes


async def get_qq_member_name(bot: qq_Bot, group_id: int, user_id: int) -> str:
    return (
        await bot.get_group_member_info(
            group_id=group_id, user_id=user_id, no_cache=True
        )
    )["nickname"]


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


async def build_dc_file(file: str, url: str) -> File:
    """获取图片文件，用于发送到 Discord"""
    img_bytes = await get_file_bytes(url)
    if re.search(r"\.[a-z]+$", file):
        filename = file
    else:
        match = filetype.match(img_bytes)
        filename = file + ("." + match.extension) if match else ""
    return File(content=img_bytes, filename=filename)


async def build_dc_embeds(
    bot: qq_Bot,
    dc_bot: dc_Bot,
    reply: Reply,
    channel_link: LinkWithWebhook,
) -> list[Embed]:
    """处理 QQ 转 discord 中的回复部分"""

    logger.debug("into build_dc_embeds()")
    guild_id, channel_id = channel_link.dc_guild_id, channel_link.dc_channel_id

    author = ""
    timestamp = f"<t:{reply.time}:R>"

    async with get_session() as session:
        if reference_id := await session.scalar(
            select(MsgID.dcid).filter(MsgID.qqid == reply.message_id).fetch(1)
        ):
            dc_message = await dc_bot.get_channel_message(
                channel_id=channel_id, message_id=reference_id
            )
            if str(reply.sender.user_id) == bot.self_id:
                name, _ = await get_dc_member_name(
                    dc_bot, guild_id, dc_message.author.id
                )
                author = EmbedAuthor(
                    name=name + f"(@{dc_message.author.username})",
                    icon_url=await get_dc_member_avatar(
                        dc_bot, guild_id, dc_message.author.id
                    ),
                )
                timestamp = f"<t:{int(dc_message.timestamp.timestamp())}:R>"

            description = (
                f"{dc_message.content}\n\n"
                + timestamp
                + f"[[ ↑ ]](https://discord.com/channels/{guild_id}/{channel_id}/{reference_id})"
            )
        else:
            plaintext_msg = ""
            for msg in reply.message:
                if msg.type == "text":
                    # 文本
                    plaintext_msg += msg.data["text"] or ""
                elif msg.type == "face":
                    # QQ表情
                    plaintext_msg += (
                        "["
                        + qq_emoji_dict.get(
                            str(msg.data["id"]), "QQemojiID:" + str(msg.data["id"])
                        )
                        + "]"
                    )
                elif msg.type == "mface":
                    # 表情商城表情
                    if msg.data["summary"]:
                        plaintext_msg += msg.data["summary"]
                elif msg.type == "at":
                    # @人
                    qq = msg.data.get("user_id", None) or msg.data["qq"]
                    if qq in ["0", "all"]:
                        plaintext_msg += "@全体成员"
                    else:
                        plaintext_msg += (
                            "@"
                            + await get_qq_member_name(
                                bot, channel_link.qq_group_id, qq
                            )
                            + f"[QQ:{qq}] "
                        )
                elif msg.type == "image":
                    # 图片
                    plaintext_msg += "[图片]"
            description = f"{plaintext_msg}\n\n" + timestamp + "[ ? ]"

        if not author:
            author = EmbedAuthor(
                name=(reply.sender.card or reply.sender.nickname or "")
                + f"[QQ:{reply.sender.user_id}]",
                icon_url=f"https://q.qlogo.cn/g?b=qq&nk={reply.sender.user_id}&s=100",
            )

    embeds = [
        Embed(
            author=author,
            description=description,
        )
    ]
    return embeds


async def build_dc_message(
    bot: qq_Bot, event: GroupMessageEvent
) -> tuple[str, list[str], list[str]]:
    """获取 QQ 消息，用于发送到 discord"""

    logger.debug("into build_dc_message()")
    text = ""
    file_list: list[str] = []
    url_list: list[str] = []
    for msg in event.message:
        if msg.type == "text":
            # 文本
            text += (
                msg.data["text"]
                .replace("@everyone", "@.everyone")
                .replace("@here", "@.here")
            )
        elif msg.type == "face":
            # QQ表情
            text += (
                "["
                + qq_emoji_dict.get(
                    str(msg.data["id"]), "QQemojiID:" + str(msg.data["id"])
                )
                + "]"
            )
        elif msg.type == "mface":
            # 表情商城表情
            if msg.data["summary"] and msg.data["url"]:
                text += msg.data["summary"]
                file_list.append(msg.data["summary"] + ".gif")
                url_list.append(msg.data["url"])
            else:
                text += "[图片]"
                file_list.append(msg.data["id"] + ".gif")
                url_list.append(
                    f"https://gxh.vip.qq.com/club/item/parcel/item/{msg.data['id'][:2]}/{msg.data['id']}/raw300.gif"
                )
        elif msg.type == "marketface":
            # 表情商城表情
            file_list.append(msg.data["summary"] + ".gif")
            url_list.append(
                f"https://gxh.vip.qq.com/club/item/parcel/item/{msg.data['face_id'][:2]}/{msg.data['face_id']}/raw300.gif"
            )
        elif msg.type == "at":
            # @人
            qq = msg.data.get("user_id", None) or msg.data["qq"]
            if qq in ["0", "all"]:
                text += "@everyone"
            else:
                text += (
                    f"@{await get_qq_member_name(bot, event.group_id, qq)}"
                    + f"[QQ:{qq}] "
                )
        elif msg.type == "image":
            # 图片
            text += "[图片]"
            file_list.append(msg.data["file"])
            url_list.append(msg.data["url"].replace("https://", "http://"))
    return text, file_list, url_list


async def send_to_discord(
    bot: dc_Bot,
    webhook_id: int,
    token: str,
    text: Optional[str],
    img_files: Optional[list[str]],
    img_urls: Optional[list[str]],
    embed: Optional[list[Embed]],
    username: Optional[str],
    avatar_url: Optional[str],
) -> MessageGet:
    """用 webhook 发送到 discord"""

    logger.debug("into send_to_discord()")
    if img_files and img_urls:
        get_img_tasks = [
            build_dc_file(file, url) for file, url in zip(img_files, img_urls)
        ]
        files = await asyncio.gather(*get_img_tasks)
    else:
        files = None

    try_times = 1
    while True:
        try:
            send = await bot.execute_webhook(
                webhook_id=webhook_id,
                token=token,
                content=text or "",
                files=files,
                embeds=embed,
                username=username,
                avatar_url=avatar_url,
                wait=True,
            )
            break
        except NetworkError as e:
            logger.warning(f"send_to_discord() except NetworkError, retry {try_times}")
            if try_times == 3:
                raise e
            try_times += 1
            await asyncio.sleep(5)

    logger.debug("send")
    return send


async def create_qq_to_dc(
    bot: qq_Bot,
    event: GroupMessageEvent,
    dc_bot: dc_Bot,
    channel_links: list[LinkWithWebhook],
):
    """QQ 消息转发到 discord"""

    logger.debug("into create_qq_to_dc()")
    text, img_files, img_urls = await build_dc_message(bot, event)
    link = next(link for link in channel_links if link.qq_group_id == event.group_id)

    if reply := event.reply:
        embeds = await build_dc_embeds(bot, dc_bot, reply, link)
    else:
        embeds = None

    username = (
        f"{event.sender.card or event.sender.nickname} [QQ:{event.sender.user_id}]"
    )
    avatar = f"https://q.qlogo.cn/g?b=qq&nk={event.sender.user_id}&s=100"

    try_times = 1
    while True:
        try:
            send = await send_to_discord(
                dc_bot,
                link.webhook_id,
                link.webhook_token,
                text,
                img_files,
                img_urls,
                embeds,
                username,
                avatar,
            )
            break
        except NameError as e:
            logger.warning(f"create_qq_to_dc() except NameError, retry {try_times}")
            if try_times == 3:
                raise e
            try_times += 1
            await asyncio.sleep(5)

    if send:
        async with get_session() as session:
            session.add(MsgID(dcid=send.id, qqid=event.message_id))
            await session.commit()


async def delete_qq_to_dc(
    event: GroupRecallNoticeEvent,
    dc_bot: dc_Bot,
    channel_links: list[LinkWithWebhook],
    just_delete: list,
):
    logger.debug("into delete_qq_to_dc()")
    if (id := event.message_id) in just_delete:
        just_delete.remove(id)
        return
    try_times = 1
    while True:
        try:
            async with get_session() as session:
                if msgids := await session.scalars(
                    select(MsgID).filter(MsgID.qqid == event.message_id)
                ):
                    channel_id = next(
                        link.dc_channel_id
                        for link in channel_links
                        if link.qq_group_id == event.group_id
                    )
                    for msgid in msgids:
                        await dc_bot.delete_message(
                            message_id=msgid.dcid, channel_id=channel_id
                        )
                        just_delete.append(msgid.dcid)
                        await session.delete(msgid)
                    await session.commit()
            break
        except UnboundLocalError or TypeError or NameError as e:
            logger.warning(f"delete_qq_to_dc() except Error, retry {try_times}")
            if try_times == 3:
                raise e
            try_times += 1
            await asyncio.sleep(5)
