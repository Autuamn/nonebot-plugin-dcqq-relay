import asyncio
from typing import Any, Callable, Optional
from collections.abc import Coroutine
from nonebot import logger
from nonebot.adapters.discord import (
    Bot as dc_Bot,
    GuildMessageCreateEvent,
    GuildMessageDeleteEvent,
)
from nonebot.adapters.discord.message import (
    MessageSegment as dc_MS,
    Message as dc_M,
)
from nonebot.adapters.discord.api import UNSET, Attachment, StickerItem, MessageGet
from nonebot.adapters.onebot.v11 import (
    Bot as qq_Bot,
    Message as qq_M,
    MessageSegment as qq_MS,
)
from nonebot.adapters.onebot.utils import f2s
from nonebot_plugin_orm import get_session
from sqlalchemy import select

from .config import LinkWithWebhook, plugin_config
from .model import MsgID
from .utils import get_dc_member_name, get_file_bytes, pydub_transform

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


async def create_dc_to_qq(
    bot: dc_Bot,
    event: GuildMessageCreateEvent,
    qq_bot: qq_Bot,
    channel_links: list[LinkWithWebhook],
):
    """discord 消息转发到 QQ"""
    logger.debug("into create_dc_to_qq()")
    link = next(
        link for link in channel_links if link.dc_channel_id == event.channel_id
    )

    attrs = ("content", "embeds", "components", "sticker_items")
    if not any(getattr(event, attr) for attr in attrs):
        message_get = await bot.get_channel_message(
            channel_id=event.channel_id, message_id=event.message_id
        )
        for attr in attrs:
            setattr(event, attr, getattr(message_get, attr))
    seg_msg = event.get_message()

    messages = await MessageBuilder().build(seg_msg, bot, event)

    try_times = 1
    while True:
        try:
            sends = [
                await qq_bot.send_group_msg(group_id=link.qq_group_id, message=message)
                for message in messages
            ]
            break
        except NameError as e:
            logger.warning(f"create_dc_to_qq() error: {e}, retry {try_times}")
            if try_times >= 3:
                raise e
            try_times += 1
            await asyncio.sleep(5)

    async with get_session() as session:
        for send in sends:
            session.add(MsgID(dcid=event.id, qqid=send["message_id"]))
        await session.commit()
    logger.debug("finish create_dc_to_qq()")


async def delete_dc_to_qq(
    event: GuildMessageDeleteEvent,
    qq_bot: qq_Bot,
    just_delete: list,
):
    logger.debug("into delete_dc_to_qq()")
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
            logger.debug("finish delete_dc_to_qq()")
            break
        except UnboundLocalError or TypeError or NameError as e:
            logger.warning(f"delete_dc_to_qq() error: {e}, retry {try_times}")
            if try_times == 3:
                raise e
            try_times += 1
            await asyncio.sleep(5)


class MessageBuilder:
    _mapping: dict[
        str,
        Callable[
            [dc_MS, dc_Bot, GuildMessageCreateEvent],
            Coroutine[Any, Any, Optional[qq_MS]],
        ],
    ]

    def __init__(self):
        self._mapping = {
            "attachment": self.attachment,
            "sticker": self.sticker,
            "embed": self.embed,
            "component": self.component,
            "custom_emoji": self.custom_emoji,
            "mention_user": self.mention_user,
            "mention_role": self.mention_role,
            "mention_channel": self.mention_channel,
            "mention_everyone": self.mention_everyone,
            "text": self.text,
            "timestamp": self.timestamp,
        }

    async def build(
        self, seg_msg: dc_M, bot: dc_Bot, event: GuildMessageCreateEvent
    ) -> list[qq_M]:
        result: list[Coroutine[Any, Any, Optional[qq_MS]]] = [self.build_sender(event)]

        if event.content or event.embeds or event.components:
            result.extend(self.convert(seg, bot, event) for seg in seg_msg)

        result.extend(
            self.handle_attachment(attachment, bot, event)
            for attachment in event.attachments
        )

        if event.sticker_items:
            result.extend(
                self.handle_sticker(sticker) for sticker in event.sticker_items
            )

        if referenced_message := event.referenced_message:
            result.append(self.handle_referenced_message(referenced_message))

        send_msg = await asyncio.gather(*result)
        send_msg = [seg for seg in send_msg if seg is not None]

        combinable = qq_M(
            [seg for seg in send_msg if seg.type in ["text", "image", "reply"]]
        )

        records = [qq_M(seg) for seg in send_msg if seg.type == "record"]

        videos = [qq_M(seg) for seg in send_msg if seg.type == "video"]

        return [combinable, *records, *videos]

    def convert(
        self, seg: dc_MS, bot: dc_Bot, event: GuildMessageCreateEvent
    ) -> Coroutine[Any, Any, Optional[qq_MS]]:
        seg_type = seg.type
        if seg_type in self._mapping:
            res = self._mapping[seg_type](seg, bot, event)
        else:
            res = self.other(seg, bot, event)

        return res

    async def handle_attachment(
        self, attachment: Attachment, bot: dc_Bot, event: GuildMessageCreateEvent
    ) -> qq_MS:
        filename = attachment.filename
        content_type = (
            attachment.content_type if attachment.content_type is not UNSET else ""
        )
        filetype = filename.split(".")[-1]
        if "image" in content_type:
            return qq_MS.image(
                await get_file_bytes(bot, attachment.url, discord_proxy), type_=filetype
            )
        if "video" in content_type:
            return qq_MS.video(await get_file_bytes(bot, attachment.url, discord_proxy))
        if "audio" in content_type and hasattr(attachment, "duration_secs"):
            return qq_MS.record(
                await get_file_bytes(bot, attachment.url, discord_proxy)
                if filetype.lower == "mp3"
                else pydub_transform(
                    await get_file_bytes(bot, attachment.url, discord_proxy),
                    filetype,
                    "mp3",
                )
            )
        return qq_MS(
            "file",
            {
                "file": f2s(await get_file_bytes(bot, attachment.url, discord_proxy)),
                "name": filename,
            },
        )

    async def handle_sticker(self, sticker: StickerItem) -> Optional[qq_MS]:
        return qq_MS.text(f"[{sticker.name}]")
        # WIP

    async def handle_referenced_message(
        self, referenced: MessageGet
    ) -> Optional[qq_MS]:
        async with get_session() as session:
            if reply_id := await session.scalar(
                select(MsgID.qqid).filter(MsgID.dcid == referenced.id).limit(1)
            ):
                return qq_MS.reply(reply_id)

    async def build_sender(self, event: GuildMessageCreateEvent) -> qq_MS:
        return qq_MS.text(
            (
                event.member.nick
                if event.member is not UNSET
                and event.member.nick is not UNSET
                and event.member.nick
                else event.author.global_name or ""
            )
            + f"(@{event.author.username}):\n\n"
        )

    async def attachment(
        self, seg: dc_MS, bot: dc_Bot, event: GuildMessageCreateEvent
    ) -> Optional[qq_MS]:
        filename = seg.data["attachment"].filename
        if hasattr(seg.data["attachment"], "duration_secs"):
            return
        else:
            return qq_MS.text(f"[{filename}]" if len(filename) < 10 else "[文件]")

    async def sticker(
        self, seg: dc_MS, bot: dc_Bot, event: GuildMessageCreateEvent
    ) -> qq_MS:
        return qq_MS.image(
            await get_file_bytes(
                bot,
                f"https://cdn.discordapp.com/stickers/{seg.data['id']}.gif",
                discord_proxy,
            )
        )

    async def embed(
        self, seg: dc_MS, bot: dc_Bot, event: GuildMessageCreateEvent
    ) -> qq_MS:
        return qq_MS.text(f"\n<Embed:{seg.data['embed'].title}>\n")

    async def component(
        self, seg: dc_MS, bot: dc_Bot, event: GuildMessageCreateEvent
    ) -> qq_MS:
        return qq_MS.text(f"\n{seg}\n")

    async def custom_emoji(
        self, seg: dc_MS, bot: dc_Bot, event: GuildMessageCreateEvent
    ) -> qq_MS:
        return qq_MS.image(
            await get_file_bytes(
                bot,
                "https://cdn.discordapp.com/emojis/"
                + seg.data["id"]
                + "."
                + ("gif" if seg.data["animated"] is True else "webp"),
                discord_proxy,
            )
        )

    async def mention_user(
        self, seg: dc_MS, bot: dc_Bot, event: GuildMessageCreateEvent
    ) -> qq_MS:
        nick, username = await get_dc_member_name(
            bot, event.guild_id, int(seg.data["user_id"])
        )
        return qq_MS.text("@" + nick + f"({username})")

    async def mention_role(
        self, seg: dc_MS, bot: dc_Bot, event: GuildMessageCreateEvent
    ) -> qq_MS:
        return qq_MS.text(
            "@" + await get_dc_role_name(bot, event.guild_id, int(seg.data["role_id"]))
        )

    async def mention_channel(
        self, seg: dc_MS, bot: dc_Bot, event: GuildMessageCreateEvent
    ) -> qq_MS:
        return qq_MS.text(
            "#"
            + await get_dc_channel_name(
                bot, event.guild_id, int(seg.data["channel_id"])
            )
        )

    async def mention_everyone(
        self, seg: dc_MS, bot: dc_Bot, event: GuildMessageCreateEvent
    ) -> qq_MS:
        return qq_MS.at("all")

    async def text(
        self, seg: dc_MS, bot: dc_Bot, event: GuildMessageCreateEvent
    ) -> qq_MS:
        return qq_MS.text(seg.data["text"])

    async def timestamp(
        self, seg: dc_MS, bot: dc_Bot, event: GuildMessageCreateEvent
    ) -> qq_MS:
        return qq_MS.text(str(seg))

    async def other(
        self, seg: dc_MS, bot: dc_Bot, event: GuildMessageCreateEvent
    ) -> qq_MS:
        return qq_MS.text(f"\n{seg}\n")
