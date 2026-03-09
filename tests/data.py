from typing import Any

from nonebot.adapters.discord import (
    UNSET,
    GuildMessageCreateEvent,
    GuildMessageDeleteEvent,
)
from nonebot.adapters.discord.api import (
    Attachment,
    Channel,
    Embed,
    File,
    GuildMember,
    GuildPreview,
    MessageGet,
    Role,
    Snowflake,
    User,
    Webhook,
)
from nonebot.adapters.discord.utils import model_dump
from nonebot.adapters.onebot.v11 import (
    GroupMessageEvent,
    GroupRecallNoticeEvent,
)
from nonebot.adapters.onebot.v11.event import Sender
from nonebot.adapters.onebot.v11.message import (
    Message as QQMessage,
    MessageSegment as QQMessageSegment,
)
from nonebot.compat import type_validate_python


def webhook(
    id: str = "1", token: str | None = "xx", application_id: str | None = "12345"
) -> Webhook:
    wh = type_validate_python(
        Webhook,
        {
            "id": id,
            "type": 1,
            "application_id": application_id,
            "channel_id": None,
            "name": None,
            "avatar": None,
        },
    )
    if token is not None:
        wh.token = token
    return wh


def webhooks_list(
    ids: list[str] | None = None,
    tokens: list[str | None] | None = None,
    application_ids: list[str | None] | None = None,
) -> list[Webhook]:
    if ids is None:
        ids = ["1"]
    if tokens is None:
        tokens = ["xx"]
    if application_ids is None:
        application_ids = ["12345"]
    return [
        webhook(id, token, application_id)
        for id, token, application_id in zip(ids, tokens, application_ids, strict=False)
    ]


def user(
    id: str = "3" * 18,
    username: str = "autuamn_end",
    global_name: str | None = "Autuamn End",
    avatar: str | None = None,
) -> User:
    return User(
        id=Snowflake(id),
        username=username,
        discriminator="",
        global_name=global_name,
        avatar=avatar,
    )


def message_get(channel_id: str = "2" * 18, content: str = "test") -> MessageGet:
    return type_validate_python(
        MessageGet,
        {
            "type": 0,
            "content": content,
            "mentions": [],
            "mention_roles": [],
            "attachments": [],
            "embeds": [],
            "timestamp": "2026-02-28T02:39:14.231000+00:00",
            "edited_timestamp": None,
            "id": "1" * 18,
            "channel_id": channel_id,
            "author": user().model_dump(),
            "pinned": False,
            "mention_everyone": False,
            "tts": False,
        },
    )


def guild_message_create_event(
    guild_id: str = "6" * 18,
    channel_id: str = "2" * 18,
    webhook_id: str | None = None,
    to_me: bool = False,
    content: str = "test",
) -> GuildMessageCreateEvent:
    ev = type_validate_python(
        GuildMessageCreateEvent,
        {
            "to_me": to_me,
            "guild_id": guild_id,
            **model_dump(message_get(channel_id, content)),
        },
    )
    if webhook_id is not None:
        ev.webhook_id = Snowflake(webhook_id)
    return ev


def channel(
    id: str = "4" * 18, guild_id: str = "6" * 18, name: str = "test"
) -> Channel:
    return type_validate_python(
        Channel,
        {
            "id": id,
            "type": 0,
            "guild_id": guild_id,
            "name": name,
        },
    )


def guild_member(
    id: str = "3" * 18,
    username: str = "autuamn_end",
    global_name: str = "Autuamn End",
    nick: str | None = None,
    unset_user: bool = False,
    member_avatar: str | None = None,
    user_avatar: str | None = None,
) -> GuildMember:
    ev = type_validate_python(
        GuildMember,
        {
            "flags": 2,
            "joined_at": "2023-11-07T03:44:23.842000+00:00",
            "roles": [],
            "user": user(id, username, global_name, user_avatar).model_dump(),
        },
    )
    if nick is not None:
        ev.nick = nick
    if member_avatar is not None:
        ev.avatar = member_avatar
    if unset_user:
        ev.user = UNSET
    return ev


def role(id: str = "5" * 18, name: str = "test") -> Role:
    return type_validate_python(
        Role,
        {
            "id": id,
            "name": name,
            "description": None,
            "permissions": "0",
            "position": 11,
            "color": 0,
            "hoist": False,
            "managed": False,
            "mentionable": False,
        },
    )


def guild_preview(id: str = "6" * 18, name: str = "name") -> GuildPreview:
    return type_validate_python(
        GuildPreview,
        {
            "id": id,
            "name": name,
            "features": [],
            "approximate_member_count": 0,
            "approximate_presence_count": 0,
            "emojis": [],
            "stickers": [],
        },
    )


def send_group_msg_data(
    group_id: int = 10001,
    message: QQMessage | list[QQMessageSegment] | str = "test",
    id: str = "3" * 18,
    username: str = "autuamn_end",
    global_name: str | None = "Autuamn End",
):
    if isinstance(message, str):
        message = [QQMessageSegment.text(message)]
    elif isinstance(message, QQMessage):
        message = list(message)

    message = [QQMessageSegment.text(f"{global_name}(@{username}):\n\n"), *message]

    return {
        "group_id": group_id,
        "message": message,
    }


def group_message_event(
    message: QQMessage | str = "test",
    group_id: int = 10001,
    to_me: bool = False,
    username: str = "sb",
    user_id: int = 10003,
) -> GroupMessageEvent:
    if isinstance(message, str):
        raw_message = message
        message = QQMessage([QQMessageSegment(type="text", data={"text": message})])
    else:
        raw_message = message.extract_plain_text()

    return GroupMessageEvent(
        time=1772777414,
        self_id=12345,
        post_type="message",
        sub_type="normal",
        user_id=user_id,
        message_type="group",
        message_id=2,
        message=message,
        original_message=message,
        raw_message=raw_message,
        font=14,
        sender=Sender(
            user_id=user_id,
            nickname="0",
            card=username,
        ),
        group_id=group_id,
        to_me=to_me,
    )


def execute_webhook_data(
    content: str = "test",
    files: list[File] | None = None,
    embeds: list[Embed] | None = None,
    username: str = "sb",
    user_id: int = 10003,
) -> dict[str, Any]:
    if files is None:
        files = []
    if embeds is None:
        embeds = []
    avatar_url = f"https://q.qlogo.cn/g?b=qq&nk={user_id}&s=100"
    return {
        "webhook_id": 1,
        "token": "x",
        "content": content,
        "files": files,
        "embeds": embeds,
        "username": f"{username} [QQ:{user_id}]",
        "avatar_url": avatar_url,
        "wait": True,
    }


def execute_webhook_result(
    content: str = "test",
    files: list[File] | None = None,
    embeds: list[Embed] | None = None,
    username: str = "sb [QQ:10003]",
    global_name: str | None = None,
) -> MessageGet:
    if files is None:
        files = []
    if embeds is None:
        embeds = []
    attachments: list[Attachment] = [
        Attachment(
            id=Snowflake("0"), filename=file.filename, size=1, url="1", proxy_url="1"
        )
        for file in files
    ]
    return type_validate_python(
        MessageGet,
        {
            "type": 0,
            "content": content,
            "mentions": [],
            "mention_roles": [],
            "attachments": attachments,
            "embeds": embeds,
            "timestamp": "2026-03-06T06:10:15.391000+00:00",
            "edited_timestamp": None,
            "id": "0",
            "channel_id": "0",
            "author": user(username=username, global_name=global_name).model_dump(),
            "pinned": False,
            "mention_everyone": False,
            "tts": False,
        },
    )


def get_test_links() -> list:
    from nonebot_plugin_dcqq_relay.config import LinkWithWebhook

    return [
        LinkWithWebhook(
            dc_guild_id=int("6" * 18),
            dc_channel_id=int("2" * 18),
            qq_group_id=10001,
            webhook_id=1,
            webhook_token="x",
        )
    ]


def group_recall_event(
    message_id: int = 1, group_id: int = 10001
) -> GroupRecallNoticeEvent:
    return GroupRecallNoticeEvent(
        time=0,
        self_id=12345,
        post_type="notice",
        notice_type="group_recall",
        user_id=10003,
        group_id=group_id,
        message_id=message_id,
        operator_id=10003,
    )


def guild_message_delete_event(
    message_id: str = "1", guild_id: str = "6" * 18, channel_id: str = "2" * 18
) -> GuildMessageDeleteEvent:
    return type_validate_python(
        GuildMessageDeleteEvent,
        {"id": message_id, "channel_id": channel_id, "guild_id": guild_id},
    )


skil_b64 = (
    "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"
)
amr_b64 = (
    "IyFBTVIKDB9Ub+B3bZWcmm4KKGAMzMeY+uqCzqCG3Snh8gx4iC8AavmYL7vgdgW8DPFNhsNk5F2W68uxP7"
    + "oMrdlKx2SiW7OLVR3D2gznOTt5mz2zuBNa5IxqDHiQsONtl4f9ZttpfwgM+kLOc2plXDzCeKBcWgwfiF"
    + "T7a8L2uGrChquGDDzM+M9PDwRQgxkC0I4MaULN++Z4CSHeZ7K2SgxpzmvfarmkPaYLK+BeDGmQCN/rhF"
    + "7InV1jESwMa1TOzm1PZB6GUuAKJgyFzM3t73mXIAPxv0tkDJjo6f/jWGWVkrjgwRYMLELLz8wwfsSWqg"
    + "7gsAwsiMv6a3IXnE3lfsucDGnWzPt/oG8MhOXFPn4MAOzNe35Fbm2vc8cNiAxrzBDzY7mRm5pHzE5qDG"
    + "nM859n+RUfiyOcOFYMB86N+9uiJxlVKOVCLAxpZ/17bx09fCha0J9sDA5CRXtnVbZ/WUWVPE4MBTl823"
    + "tTL4ilLAtwpgyFZxTb7lukfJHZjWV6DGJU5c/8pA4KubKkCNYMLMyFzutWih1i7/g11AwA7IPzf6MWHk"
    + "ZFayFeDGlCqd/qEA6otnonSjAMYuz7muVwqBalRg8kcAzMlM3bzHCuYoIL7w0ADCzOi9Pr0Jy48h+TV9"
    + "AMLOwiXm4Wj6S0mxiFxgwOZyfby4wVuLopMCaqDABUHtNjJU8JiObLi0IMAEZM709C2vx6h2mv9gxpzh"
    + "N9/33FUbHTOMuEDA7kiE9/RW6gtoePgEIMaVSFznlUb2d+cN4pZAwO7O7XfaEIW1sCSH98DAB50tvvrt"
    + "S2i7YyXBQMa8xsb29F7qymM8UeFAzEO23ffcE22nklkaSoDA5nTvtnyMVVj2M2lewMxMyH+u6q1qPIYJ"
    + "g/qAws7JP95xnoHzr8RrwGDGKIhZt/nyePOgye41gMaewl3/j4VL+yhqkWJAwOiIR37sDqeE1X1084DM"
    + "SShq/vsmbXVFHyHNYMaWrLdLvs7W0svAJHJg=="
)
