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


def create_webhook_result(application_id: int) -> Webhook:
    return type_validate_python(
        Webhook,
        {
            "id": "1",
            "type": 1,
            "application_id": application_id,
            "token": "x",
            "channel_id": None,
            "name": None,
            "avatar": None,
        },
    )


def get_channel_webhooks_result(application_id: int) -> list[Webhook]:
    return [create_webhook_result(application_id)]


def get_channel_message_result(
    url: str = "x", channel_id: str = "2" * 18
) -> MessageGet:
    return type_validate_python(
        MessageGet,
        {
            "type": 0,
            "content": "",
            "mentions": [],
            "mention_roles": [],
            "attachments": [],
            "embeds": [],
            "timestamp": "2026-02-28T02:39:14.231000+00:00",
            "edited_timestamp": None,
            "id": "1" * 18,
            "channel_id": channel_id,
            "author": {
                "id": "3" * 18,
                "username": "autuamn_end",
                "avatar": "a" * 32,
                "discriminator": "0",
                "global_name": "Autuamn End",
            },
            "pinned": False,
            "mention_everyone": False,
            "tts": False,
            "message_snapshots": [
                {
                    "message": {
                        "type": 0,
                        "content": (
                            f"0 <#{'4' * 18}> "
                            + f" 1 <@{'3' * 18}>"
                            + f" 2 <@&{'5' * 18}>"
                        ),
                        "mentions": [
                            {
                                "id": "3" * 18,
                                "username": "autuamn_end",
                                "avatar": "a" * 32,
                                "discriminator": "0",
                                "global_name": "Autuamn End",
                            }
                        ],
                        "mention_roles": ["5" * 18],
                        "attachments": [
                            {
                                "id": "0" * 18,
                                "filename": "test.png",
                                "size": 391,
                                "url": url,
                                "proxy_url": url,
                                "content_type": "image/png",
                            }
                        ],
                        "embeds": [],
                        "timestamp": "2026-02-28T01:42:01.496000+00:00",
                        "edited_timestamp": None,
                        "sticker_items": [
                            {
                                "id": "0" * 18,
                                "name": "ek244",
                                "format_type": 4,
                            }
                        ],
                    }
                }
            ],
        },
    )


def dc_complex_forward_event(
    url: str = "x",
    guild_id: str = "6" * 18,
    channel_id: str = "2" * 18,
    webhook_id: str | None = None,
    to_me: bool = False,
) -> GuildMessageCreateEvent:
    ev = type_validate_python(
        GuildMessageCreateEvent,
        {
            "to_me": to_me,
            "guild_id": guild_id,
            **model_dump(get_channel_message_result(url, channel_id)),
        },
    )

    if webhook_id is not None:
        ev.webhook_id = Snowflake(webhook_id)

    return ev


def get_channel_result() -> Channel:
    return type_validate_python(
        Channel,
        {
            "id": "4" * 18,
            "type": 0,
            "guild_id": "6" * 18,
            "name": "test",
        },
    )


def get_guild_member_result(
    id: str = "3" * 18,
    username: str = "autuamn_end",
    global_name: str = "Autuamn End",
    nick: str | None = None,
    unset_user: bool = False,
) -> GuildMember:
    ev = type_validate_python(
        GuildMember,
        {
            "flags": 2,
            "joined_at": "2023-11-07T03:44:23.842000+00:00",
            "roles": [],
            "user": {
                "id": id,
                "username": username,
                "avatar": "a" * 32,
                "discriminator": "0",
                "global_name": global_name,
            },
        },
    )
    if nick is not None:
        ev.nick = nick
    if unset_user:
        ev.user = UNSET
    return ev


def get_guild_role_result() -> Role:
    return type_validate_python(
        Role,
        {
            "id": "5" * 18,
            "name": "test",
            "description": None,
            "permissions": "0",
            "position": 11,
            "color": 15105570,
            "hoist": False,
            "managed": False,
            "mentionable": False,
        },
    )


def get_guild_preview_result() -> GuildPreview:
    return type_validate_python(
        GuildPreview,
        {
            "id": "6" * 18,
            "name": "test",
            "features": [],
            "approximate_member_count": 0,
            "approximate_presence_count": 0,
            "emojis": [],
            "stickers": [],
        },
    )


def send_group_msg_result():
    return {
        "group_id": 10001,
        "message": [
            QQMessageSegment(
                type="text", data={"text": "Autuamn End(@autuamn_end):\n\n"}
            ),
            QQMessageSegment(type="text", data={"text": "↱ 已转发：\n"}),
            QQMessageSegment(type="text", data={"text": "0 "}),
            QQMessageSegment(type="text", data={"text": "#test"}),
            QQMessageSegment(type="text", data={"text": "  1 "}),
            QQMessageSegment(type="text", data={"text": "@Autuamn End(autuamn_end)"}),
            QQMessageSegment(type="text", data={"text": " 2 "}),
            QQMessageSegment(type="text", data={"text": "@test"}),
            QQMessageSegment(
                type="image",
                data={
                    "file": "base64://iVBORw0KGgoAAAANSUhEUgAAAEYAAAAaCAYAAAAKYioIAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAAFiUAABYlAUlSJPAAAAEcSURBVFhH7ZABCsMwDAP7/093eMxgTBxJSbtuTQ9MSSPLjrb9oQkdzLatlSH1WgvlCabBaqEYTzAFSwbDvOetMCFbd4B5B1TkQPyc659g9qWCOZorA2XnfjUYX8o983mE6MF4oXsHqlijHmjp3l0F8qyI+l4/dFUHZ3rDI8oc1tNwbVUV0L3XjEDDHVZnKNoW9JzPt2R2CdTPaCIz+xhsP1TNLOKPRqUw0hNhe08P5gxmwrl1MMZoOLcPxhgJ52eCmelnUGf0tPEOOqqDM94/44FQvCtt3pFyzE0ZdG+4hikVpafS5v+0oy/tBvHs/65AnV9p83/5Rb6IsszRxB3UPVo9LD/rXdeBGkbGw4mV+ctgjqIKxVg6mJp9fwGt8jszqRET6QAAAABJRU5ErkJggg==",
                    "type": "png",
                    "cache": "true",
                    "proxy": "true",
                    "timeout": None,
                },
            ),
            QQMessageSegment(type="text", data={"text": "[ek244]"}),
            QQMessageSegment(type="text", data={"text": "\ntest 2026/02/28 09:42"}),
        ],
    }


def qq_complex_event(
    message: QQMessage | str = "test",
    group_id: int = 10001,
    to_me: bool = False,
    username: str = "sb",
    user_id: int = 10003,
) -> GroupMessageEvent:
    message = (
        QQMessage([QQMessageSegment(type="text", data={"text": message})])
        if isinstance(message, str)
        else message
    )
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
        raw_message="1",
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
    files: list[File] = [],  # noqa: B006
    embeds: list[Embed] = [],  # noqa: B006
    username: str = "sb",
    user_id: int = 10003,
) -> dict[str, Any]:
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
    files: list[File] = [],  # noqa: B006
    embeds: list[Embed] = [],  # noqa: B006
    username: str = "sb [QQ:10003]",
) -> MessageGet:
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
            "author": {
                "id": "0",
                "username": username,
                "avatar": "x",
                "discriminator": "0",
            },
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
