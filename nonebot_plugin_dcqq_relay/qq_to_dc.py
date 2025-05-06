import asyncio
import re
from urllib.request import url2pathname
from pathlib import Path
from typing import Any, Callable, Optional
from collections.abc import Coroutine

import filetype
from nonebot import logger
from nonebot.adapters import Bot
from nonebot.adapters.discord import Bot as dc_Bot
from nonebot.adapters.discord.api import Embed, EmbedAuthor, File
from nonebot.adapters.discord.exception import NetworkError
from nonebot.adapters.onebot.v11 import (
    Bot as qq_Bot,
    GroupMessageEvent,
    GroupRecallNoticeEvent,
    Message,
    MessageSegment,
)
from nonebot.adapters.onebot.v11.event import Reply
from nonebot_plugin_orm import get_session
from sqlalchemy import select

from .config import LinkWithWebhook
from .qq_emoji_dict import qq_emoji_dict
from .model import MsgID
from .utils import get_file_bytes, skil_to_ogg


async def get_qq_member_name(bot: qq_Bot, group_id: int, user_id: int) -> str:
    return (
        await bot.get_group_member_info(
            group_id=group_id, user_id=user_id, no_cache=True
        )
    )["nickname"]


async def build_dc_file(bot: Bot, file: str, url: str) -> File:
    """获取文件，用于发送到 Discord"""
    img_bytes = await get_file_bytes(bot, url)
    if re.search(r"\.[a-z]+$", file):
        filename = file
    else:
        match = filetype.match(img_bytes)
        filename = file + ("." + match.extension) if match else ""
    return File(content=img_bytes, filename=filename)


async def create_qq_to_dc(
    bot: qq_Bot,
    event: GroupMessageEvent,
    dc_bot: dc_Bot,
    channel_links: list[LinkWithWebhook],
):
    """QQ 消息转发到 discord"""
    logger.debug("create qq to dc: start")
    link = next(link for link in channel_links if link.qq_group_id == event.group_id)
    builder = MessageBuilder()

    seg_msg = event.get_message()
    text, files, embeds = await builder.build(seg_msg, bot, event)

    if reply := event.reply:
        embeds = [await builder.handle_reply(reply, bot, link), *embeds]

    username = (
        f"{event.sender.card or event.sender.nickname} [QQ:{event.sender.user_id}]"
    )
    avatar = f"https://q.qlogo.cn/g?b=qq&nk={event.sender.user_id}&s=100"

    for try_times in range(3):
        try:
            send = await dc_bot.execute_webhook(
                webhook_id=link.webhook_id,
                token=link.webhook_token,
                content=text,
                files=files,
                embeds=embeds,
                username=username,
                avatar_url=avatar,
                wait=True,
            )
            break
        except (NameError, NetworkError) as e:
            logger.warning(f"create qq to dc error: {e}, retry {try_times + 1}")
            if try_times >= 2:
                continue
            await asyncio.sleep(5)
    else:
        logger.error("create qq to dc: failed")
        return

    async with get_session() as session:
        session.add(MsgID(dcid=send.id, qqid=event.message_id))
        await session.commit()

    logger.debug("create qq to dc: done")


async def delete_qq_to_dc(
    event: GroupRecallNoticeEvent,
    dc_bot: dc_Bot,
    channel_links: list[LinkWithWebhook],
    just_delete: list,
):
    logger.debug("delete qq to dc: start")
    if (id := event.message_id) in just_delete:
        just_delete.remove(id)
        return
    channel_id = next(
        link.dc_channel_id
        for link in channel_links
        if link.qq_group_id == event.group_id
    )
    for try_times in range(3):
        try:
            async with get_session() as session:
                if msgids := await session.scalars(
                    select(MsgID).filter(MsgID.qqid == event.message_id)
                ):
                    for msgid in msgids:
                        await dc_bot.delete_message(
                            message_id=msgid.dcid, channel_id=channel_id
                        )
                        just_delete.append(msgid.dcid)
                        await session.delete(msgid)
                    await session.commit()
            logger.debug("delete qq to dc: done")
            break
        except (UnboundLocalError, TypeError, NameError) as e:
            logger.warning(f"delete qq to dc error: {e}, retry {try_times + 1}")
            if try_times >= 2:
                continue
            await asyncio.sleep(5)
    else:
        logger.error("delete qq to dc: failed")


class MsgResult:
    """消息处理结果容器"""

    embed: Optional[Embed]
    ensure_text: bool
    file: Optional[File]
    text: Optional[str]

    __slots__ = ("embed", "ensure_text", "file", "text")

    def __init__(self, *, embed=None, ensure=False, file=None, text=None):
        self.embed = embed
        self.ensure_text = ensure
        self.file = file
        self.text = text


class MessageBuilder:
    _mapping: dict[
        str,
        Callable[
            [MessageSegment, qq_Bot, GroupMessageEvent],
            Coroutine[Any, Any, MsgResult],
        ],
    ]

    def __init__(self):
        self._mapping = {
            "text": self.text,
            "face": self.face,
            "mface": self.mface,
            "marketface": self.marketface,
            "at": self.at,
            "image": self.image,
            "record": self.record,
            "video": self.video,
            "file": self.file,
            "share": self.share,
            "contact": self.contact,
            "location": self.location,
            "music": self.music,
            "forward": self.forward,
            "xml": self.xml,
            "json": self.json,
        }

    async def build(
        self, seg_msg: Message, bot: qq_Bot, event: GroupMessageEvent
    ) -> tuple[str, list[File], list[Embed]]:
        result: list[Coroutine[Any, Any, MsgResult]] = []
        text: str = ""
        files: list[File] = []
        embeds: list[Embed] = []

        result.extend(self.convert(seg, bot, event) for seg in seg_msg)

        send_msg = await asyncio.gather(*result)

        for res in send_msg:
            text += (
                res.text
                if res.text and (res.ensure_text or seg_msg.extract_plain_text())
                else ""
            )
            files.append(res.file) if res.file else ...
            embeds.append(res.embed) if res.embed else ...

        if not (text or files or embeds):
            text = "[未知消息]"

        return text, files, embeds

    def convert(
        self, seg: MessageSegment, bot: qq_Bot, event: GroupMessageEvent
    ) -> Coroutine[Any, Any, MsgResult]:
        seg_type = seg.type
        if seg_type in self._mapping:
            res = self._mapping[seg_type](seg, bot, event)
        else:
            res = self.other(seg, bot, event)

        return res

    def extract_plain_text(self, msg_res: list[MsgResult]) -> str:
        return "".join([res.text for res in msg_res if res.text])

    async def handle_reply(
        self,
        reply: Reply,
        bot: qq_Bot,
        link: LinkWithWebhook,
    ) -> Embed:
        author = ""
        sender = reply.sender
        timestamp = f"<t:{reply.time}:R>"
        plaintext_msg = reply.message.extract_plain_text()
        guild_id, channel_id = link.dc_guild_id, link.dc_channel_id

        if (
            re.match(r"^.*?\(@.*?\):\n\n", plaintext_msg)
            and str(sender.user_id) == bot.self_id
        ):
            name = plaintext_msg.split("\n")[0][:-1]
            author = EmbedAuthor(name=name)
            plaintext_msg = "\n".join(plaintext_msg.split("\n")[2:])
        else:
            author = EmbedAuthor(
                name=(sender.card or sender.nickname or "") + f"[QQ:{sender.user_id}]",
                icon_url=f"https://q.qlogo.cn/g?b=qq&nk={sender.user_id}&s=100",
            )

        async with get_session() as session:
            reference_id = await session.scalar(
                select(MsgID.dcid).filter(MsgID.qqid == reply.message_id).limit(1)
            )
        if reference_id:
            description = (
                f"{plaintext_msg}\n\n"
                + timestamp
                + f"[[ ↑ ]](https://discord.com/channels/{guild_id}/{channel_id}/{reference_id})"
            )
        else:
            description = f"{plaintext_msg}\n\n{timestamp}[ ? ]"

        return Embed(
            author=author,
            description=description,
        )

    async def text(
        self, seg: MessageSegment, bot: qq_Bot, event: GroupMessageEvent
    ) -> MsgResult:
        content = (
            seg.data["text"]
            .replace("@everyone", "@.everyone")
            .replace("@here", "@.here")
        )
        return MsgResult(text=content)

    async def at(
        self, seg: MessageSegment, bot: qq_Bot, event: GroupMessageEvent
    ) -> MsgResult:
        data = seg.data
        qq = data.get("user_id") or data["qq"]

        if qq in ["0", "all"]:
            return MsgResult(text="@everyone")

        name = data.get("name")
        if not name:
            name = await get_qq_member_name(bot, event.group_id, qq)

        return MsgResult(text=f"[{name}](mailto:{qq}@qq.com)[QQ:{qq}] ")

    async def face(
        self, seg: MessageSegment, bot: qq_Bot, event: GroupMessageEvent
    ) -> MsgResult:
        face_id = str(seg.data["id"])
        emoji = qq_emoji_dict.get(face_id, f"QQemojiID:{face_id}")
        return MsgResult(text=f"[{emoji}]")

    async def mface(
        self, seg: MessageSegment, bot: qq_Bot, event: GroupMessageEvent
    ) -> MsgResult:
        data = seg.data

        if data.get("summary") and data.get("url"):
            return MsgResult(
                text=data["summary"],
                file=await build_dc_file(bot, f"{data['summary']}.gif", data["url"]),
            )

        return MsgResult(
            text="[动画表情]",
            file=await build_dc_file(
                bot,
                f"{data['id']}.gif",
                "https://gxh.vip.qq.com/club/item/parcel/item/"
                + f"{data['id'][:2]}/{data['id']}/raw300.gif",
            ),
        )

    async def marketface(
        self, seg: MessageSegment, bot: qq_Bot, event: GroupMessageEvent
    ) -> MsgResult:
        return MsgResult(
            text=seg.data["summary"],
            file=await build_dc_file(
                bot,
                f"{seg.data['summary']}.gif",
                "https://gxh.vip.qq.com/club/item/parcel/item/"
                + f"{seg.data['face_id'][:2]}/{seg.data['face_id']}/raw300.gif",
            ),
        )

    async def image(
        self, seg: MessageSegment, bot: qq_Bot, event: GroupMessageEvent
    ) -> MsgResult:
        return MsgResult(
            text="[图片]",
            file=await build_dc_file(bot, seg.data["file"][-40:], seg.data["url"]),
        )

    async def record(
        self, seg: MessageSegment, bot: qq_Bot, event: GroupMessageEvent
    ) -> MsgResult:
        if path := seg.data.get("path", ""):
            while True:
                if not Path(path).exists():
                    await asyncio.sleep(0.1)
                    continue
                record_bytes = Path(path).read_bytes()
                break
        elif url := seg.data.get("url", ""):
            record_bytes = await get_file_bytes(bot, url)
        else:
            path = url2pathname(seg.data["file"].removeprefix("file:"))
            record_bytes = Path(path).read_bytes()

        return MsgResult(
            text="[语音]",
            file=File(
                content=skil_to_ogg(record_bytes),
                filename="voice-message.ogg",
            ),
        )

    async def video(
        self, seg: MessageSegment, bot: qq_Bot, event: GroupMessageEvent
    ) -> MsgResult:
        filename = seg.data.get("file_name", "") or seg.data.get("file", "")
        url = seg.data["url"]

        if path := seg.data.get("path", ""):
            content = Path(path).read_bytes()
        elif re.match(r"[A-Z]:\\\\", url):
            content = Path(url).read_bytes()
        elif "http" in url:
            content = await get_file_bytes(bot, url)
        else:
            return MsgResult(text=f"[{filename}]")

        return MsgResult(
            text=f"[{filename}]",
            file=File(filename=filename, content=content),
        )

    async def file(
        self, seg: MessageSegment, bot: qq_Bot, event: GroupMessageEvent
    ) -> MsgResult:
        filename = seg.data.get("file_name", "") or seg.data.get("file", "")

        if "http" in seg.data.get("url", ""):
            content = await get_file_bytes(bot, seg.data["url"])
        elif file_id := seg.data.get("file_id", ""):
            file_info = await bot.call_api("get_file", file_id=file_id)
            content = Path(file_info["file"]).read_bytes()
        else:
            return MsgResult(text=f"[{filename}]")

        return MsgResult(
            text=f"[{filename}]", file=File(content=content, filename=filename)
        )

    async def share(
        self, seg: MessageSegment, bot: qq_Bot, event: GroupMessageEvent
    ) -> MsgResult:
        data = seg.data
        embed = Embed(
            title=data["title"],
            url=data["url"],
            description=data["content"],
            image=data["image"],
        )
        return MsgResult(embed=embed)

    async def contact(
        self, seg: MessageSegment, bot: qq_Bot, event: GroupMessageEvent
    ) -> MsgResult:
        contact_type = "好友" if seg.data["type"] == "qq" else "群"
        return MsgResult(ensure=True, text=f"<推荐{contact_type}：{seg.data['id']}>")

    async def location(
        self, seg: MessageSegment, bot: qq_Bot, event: GroupMessageEvent
    ) -> MsgResult:
        data = seg.data
        embed = Embed(
            title=data["title"],
            description=f"{data['content']}\nlat:{data['lat']}, lon: {data['lon']}",
        )
        return MsgResult(embed=embed)

    async def music(
        self, seg: MessageSegment, bot: qq_Bot, event: GroupMessageEvent
    ) -> MsgResult:
        return MsgResult(ensure=True, text="[音乐分享]")

    async def forward(
        self, seg: MessageSegment, bot: qq_Bot, event: GroupMessageEvent
    ) -> MsgResult:
        return MsgResult(ensure=True, text="[合并转发]")

    async def xml(
        self, seg: MessageSegment, bot: qq_Bot, event: GroupMessageEvent
    ) -> MsgResult:
        return (
            MsgResult(ensure=True, text=f"[xml 消息]({seg.data})")
            if len(seg) == 1
            else MsgResult()
        )

    async def json(
        self, seg: MessageSegment, bot: qq_Bot, event: GroupMessageEvent
    ) -> MsgResult:
        return (
            MsgResult(ensure=True, text=f"[json 消息]({seg.data})")
            if len(seg) == 1
            else MsgResult()
        )

    async def rps(
        self, seg: MessageSegment, bot: qq_Bot, event: GroupMessageEvent
    ) -> MsgResult:
        res = {"0": "", "1": "石头", "2": "剪刀", "3": "布"}[
            seg.data.get("result", "0")
        ]
        return MsgResult(ensure=True, text=f"[猜拳{'：' if res else ''}{res}]")

    async def dice(
        self, seg: MessageSegment, bot: qq_Bot, event: GroupMessageEvent
    ) -> MsgResult:
        res = seg.data.get("result", "")
        return MsgResult(ensure=True, text=f"[掷骰子{'：' if res else ''}{res}]")

    async def other(
        self, seg: MessageSegment, bot: qq_Bot, event: GroupMessageEvent
    ) -> MsgResult:
        return MsgResult(
            ensure=True, text=f"[不支持的类型](type: {seg.type}, data: {seg.data})"
        )
