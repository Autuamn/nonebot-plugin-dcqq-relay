import datetime
from typing import Optional
from nonebot_plugin_orm import Model
from sqlalchemy import BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from pydantic import BaseModel, Field
from nonebot.adapters.discord.api.types import Missing, UNSET, MessageFlag, MessageType
from nonebot.adapters.discord.api.model import (
    Embed,
    Attachment,
    User,
    Sticker,
    StickerItem,
    DirectComponent,
)


class MsgID(Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    dcid: Mapped[int] = mapped_column(type_=BigInteger())
    qqid: Mapped[int]


class MessageSnapshots(BaseModel):
    message: "MessageSnapshotMessage"


class MessageSnapshotMessage(BaseModel):
    type: MessageType
    content: str
    embeds: list[Embed]
    attachments: list[Attachment]
    timestamp: datetime.datetime
    edited_timestamp: Optional[datetime.datetime] = Field(...)
    flags: Missing[MessageFlag] = UNSET
    mentions: list[User]
    mention_roles: Missing[list[str]] = UNSET
    stickers: Missing[list[Sticker]] = UNSET
    sticker_items: Missing[list[StickerItem]] = UNSET
    components: Missing[list[DirectComponent]] = UNSET
