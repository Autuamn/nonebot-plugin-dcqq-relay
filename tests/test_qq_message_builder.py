from base64 import b64decode
import datetime
from unittest.mock import patch

from tests.conftest import create_bot, fake_request
from tests.data import (
    amr_bytes,
    channel,
    get_test_links,
    guild_member,
    guild_message_create_event,
    guild_preview,
    message_get,
    message_reference,
    message_snapshot,
    role,
    send_group_msg_data,
    test_mp4_bytes,
    test_png_bytes,
)

from nonebot.adapters.discord import (
    MessageSegment as DCMessageSegment,
)
from nonebot.adapters.discord.api import Attachment, Embed, Snowflake, StickerItem
from nonebot.adapters.discord.exception import ActionFailed
from nonebot.adapters.onebot.v11 import (
    Message as QQMessage,
    MessageSegment as QQMessageSegment,
)
from nonebot.compat import type_validate_python
from nonebot.drivers import Response
from nonebug import App
import pytest
from pytest_httpserver import HTTPServer
from sqlalchemy import select
from sqlalchemy.util import b64encode


@pytest.mark.asyncio
async def test_handle_reply(app: App) -> None:
    with patch(
        target="nonebot_plugin_dcqq_relay.utils.with_webhook_links",
        new_callable=get_test_links,
    ):
        from nonebot_plugin_dcqq_relay import matcher
        from nonebot_plugin_dcqq_relay.model import MsgID

        from nonebot_plugin_orm import get_session

        async with app.test_matcher(matcher) as ctx:
            _, dc_bot = create_bot(ctx)

            ctx.receive_event(dc_bot, guild_message_create_event())
            ctx.should_pass_rule()
            ctx.should_call_api(
                api="get_version_info",
                data={},
                result={"app_name": "other"},
            )
            ctx.should_call_api(
                api="send_group_msg",
                data=send_group_msg_data(),
                result={"message_id": 2},
            )

        async with get_session() as session:
            msgids = await session.scalars(
                select(MsgID).filter(MsgID.dcid == int("1" * 18))
            )
            count = 0
            for msgid in msgids:
                count += 1
                await session.delete(msgid)
            await session.commit()
            assert count == 1


@pytest.mark.asyncio
async def test_handle_attachment(app: App, httpserver: HTTPServer) -> None:
    from nonebot_plugin_dcqq_relay.dc_to_qq import MessageBuilder

    httpserver.expect_request("/test.png").respond_with_data(test_png_bytes)
    url = httpserver.url_for("/test.png")
    async with app.test_api() as ctx:
        _, bot = create_bot(ctx)
        builder = MessageBuilder()

        attachment = Attachment(
            id=Snowflake(0),
            filename="",
            size=1,
            url=url,
            proxy_url=url,
            content_type="image/png",
        )
        result = await builder.handle_attachment(attachment, bot)
        assert isinstance(result, QQMessageSegment)
        assert result.type == "image"
        assert result.data["file"] == f"base64://{b64encode(test_png_bytes)}"

        attachment.content_type = "video/mp4"
        result = await builder.handle_attachment(attachment, bot)
        assert isinstance(result, QQMessageSegment)
        assert result.type == "video"
        assert result.data["file"] == f"base64://{b64encode(test_png_bytes)}"

        attachment.content_type = "text/plain"
        result = await builder.handle_attachment(attachment, bot)
        assert isinstance(result, QQMessageSegment)
        assert result.type == "file"
        assert result.data["file"] == test_png_bytes

        httpserver.expect_request("/test.amr").respond_with_data(amr_bytes)
        url = httpserver.url_for("/test.amr")
        attachment.url = url
        attachment.filename = "test.amr"
        attachment.content_type = "audio/ogg"
        attachment.duration_secs = 1.0
        result = await builder.handle_attachment(attachment, bot)
        assert isinstance(result, QQMessageSegment)
        assert result.type == "record"
        assert (
            b64decode(str(result.data["file"]).replace("base64://", ""))[:3] == b"ID3"
        )


@pytest.mark.asyncio
async def test_handle_sticker(app: App) -> None:
    from nonebot_plugin_dcqq_relay.dc_to_qq import MessageBuilder

    async with app.test_api() as ctx:
        _, bot = create_bot(ctx)
        builder = MessageBuilder()
        event = guild_message_create_event()

        sticker_name = "Test Sticker"
        seg_msg = event.get_message()
        event.sticker_items = [
            type_validate_python(
                StickerItem, {"id": 0, "name": sticker_name, "format_type": 1}
            )
        ]
        result = await builder.build(seg_msg, bot, event)
        assert isinstance(result, QQMessage)
        assert len(result) == 3
        assert result[2].data == {"text": f"[{sticker_name}]"}


@pytest.mark.asyncio
async def test_handle_referenced_message(app: App) -> None:
    from nonebot_plugin_dcqq_relay.dc_to_qq import MessageBuilder
    from nonebot_plugin_dcqq_relay.model import MsgID

    from nonebot_plugin_orm import get_session

    async with app.test_api() as ctx:
        _, bot = create_bot(ctx)
        builder = MessageBuilder()
        event = guild_message_create_event()

        dc_msg_id = 1
        qq_msg_id = 2
        async with get_session() as session:
            session.add(MsgID(dcid=dc_msg_id, qqid=qq_msg_id))
            await session.commit()

        seg_msg = event.get_message()
        event.referenced_message = message_get(id=str(dc_msg_id))
        result = await builder.build(seg_msg, bot, event)

        async with get_session() as session:
            msgids = await session.scalars(
                select(MsgID).filter(MsgID.dcid == dc_msg_id)
            )
            for msgid in msgids:
                await session.delete(msgid)
            await session.commit()

        assert isinstance(result, QQMessage)
        assert len(result) == 3
        assert result[2].data["id"] == str(qq_msg_id)


@pytest.mark.asyncio
async def test_handle_message_snapshots(app: App, httpserver: HTTPServer) -> None:
    from nonebot_plugin_dcqq_relay.dc_to_qq import MessageBuilder

    httpserver.expect_request("/test.png").respond_with_data(test_png_bytes)
    url = httpserver.url_for("/test.png")

    async with app.test_api() as ctx:
        _, bot = create_bot(ctx)
        builder = MessageBuilder()
        event = guild_message_create_event(content="")

        guild_id = 1
        content = "test"
        embed_title = "Title"
        sticker_name = "sticker"
        timestamp = datetime.datetime.now()
        guild_name = "Test Guild"

        event.message_snapshots = [
            message_snapshot(content, url, embed_title, sticker_name, timestamp)
        ]
        event.message_reference = message_reference(guild_id=str(guild_id))
        seg_msg = event.get_message()

        ctx.should_call_api(
            api="get_guild_preview",
            data={"guild_id": guild_id},
            result=guild_preview(name=guild_name),
        )
        result = await builder.build(seg_msg, bot, event)

        # 验证结果
        assert isinstance(result, QQMessage)
        assert len(result) == 7  # 至少包含这些段
        assert result[1].data == {"text": "↱ 已转发：\n"}
        assert result[2].data == {"text": content}
        assert result[3].data == {"text": f"{embed_title}\n"}
        assert result[4].data["file"] == f"base64://{b64encode(test_png_bytes)}"
        assert result[5].data == {"text": f"[{sticker_name}]"}
        assert result[6].data == {
            "text": f"\n{guild_name} "
            + timestamp.astimezone(
                datetime.timezone(datetime.timedelta(hours=8))
            ).strftime("%Y/%m/%d %H:%M")
        }

        event.message_snapshots = [message_snapshot(content, timestamp=timestamp)]

        ctx.should_call_api(
            api="get_guild_preview",
            data={"guild_id": guild_id},
            exception=ActionFailed(
                Response(
                    status_code=404,
                    content=b'{"message": "Unknown Guild", "code": 10003}',
                )
            ),
        )
        result = await builder.build(seg_msg, bot, event)
        assert result[3].data == {
            "text": "\n"
            + timestamp.astimezone(
                datetime.timezone(datetime.timedelta(hours=8))
            ).strftime("%Y/%m/%d %H:%M")
        }


@pytest.mark.asyncio
async def test_convert_attachment(app: App) -> None:
    from nonebot_plugin_dcqq_relay.dc_to_qq import MessageBuilder

    async with app.test_api() as ctx:
        _, bot = create_bot(ctx)
        builder = MessageBuilder()
        event = guild_message_create_event()

        filename = "test"
        seg = DCMessageSegment.attachment(filename)
        result = await builder.convert(seg, bot, event)
        assert isinstance(result, QQMessageSegment)
        assert result.type == "text"
        assert result.data["text"] == f"[{filename}]"

        filename = "t" * 20
        seg = DCMessageSegment.attachment(filename)
        result = await builder.convert(seg, bot, event)
        assert isinstance(result, QQMessageSegment)
        assert result.type == "text"
        assert result.data["text"] == "[文件]"


@pytest.mark.asyncio
async def test_convert_sticker(app: App) -> None:
    with patch(
        "nonebot_plugin_dcqq_relay.dc_to_qq.get_file_bytes", new_callable=fake_request
    ):
        from nonebot_plugin_dcqq_relay.dc_to_qq import MessageBuilder

        async with app.test_api() as ctx:
            _, bot = create_bot(ctx)
            builder = MessageBuilder()
            event = guild_message_create_event()

            seg = DCMessageSegment.sticker(0)
            result = await builder.convert(seg, bot, event)
            assert isinstance(result, QQMessageSegment)
            assert result.type == "image"
            assert result.data["file"] == f"base64://{b64encode(test_png_bytes)}"


@pytest.mark.asyncio
async def test_convert_embed(app: App, httpserver: HTTPServer) -> None:
    from nonebot_plugin_dcqq_relay.dc_to_qq import MessageBuilder

    httpserver.expect_request("/test.png").respond_with_data(test_png_bytes)
    httpserver.expect_request("/test.mp4").respond_with_data(test_mp4_bytes)
    image_url = httpserver.url_for("/test.png")
    video_url = httpserver.url_for("/test.mp4")
    async with app.test_api() as ctx:
        _, bot = create_bot(ctx)
        builder = MessageBuilder()
        event = guild_message_create_event()

        auther_name = "test"
        auther_url = "http://test"
        title = "Test Embed"
        embed_url = "http://test/embed"
        thumbnail_url = "http://thumbnail"
        description = "description"
        field_name = "Field1"
        field_value = "x"
        embed = {
            "title": title,
            "description": description,
            "url": embed_url,
            "image": {"url": image_url},
            "thumbnail": {"url": thumbnail_url},
            "video": {"proxy_url": video_url},
            "author": {"name": auther_name, "url": auther_url},
            "fields": [{"name": field_name, "value": field_value}],
        }

        seg = DCMessageSegment.embed(type_validate_python(Embed, embed))
        result = await builder.convert(seg, bot, event)
        assert isinstance(result, QQMessage)
        assert len(result) == 8
        assert result[0].data == {"text": f"{auther_name}({auther_url}\udb40\udc20):\n"}
        assert result[1].data == {"text": f"{title}({embed_url}\udb40\udc20)\n"}
        assert result[2].data == {"text": f"{thumbnail_url}\n"}
        assert result[3].data == {"text": f"{description}\n"}
        assert result[4].data == {"text": f"{field_name}\n{field_value}\n"}
        assert result[5].type == "image"
        assert result[5].data["file"] == f"base64://{b64encode(test_png_bytes)}"
        assert result[6].data == {"text": "\n"}
        assert result[7].type == "video"
        assert result[7].data["file"] == f"base64://{b64encode(test_mp4_bytes)}"


@pytest.mark.asyncio
async def test_convert_custom_emoji(app: App) -> None:
    with patch(
        "nonebot_plugin_dcqq_relay.dc_to_qq.get_file_bytes", new_callable=fake_request
    ):
        from nonebot_plugin_dcqq_relay.dc_to_qq import MessageBuilder

        async with app.test_api() as ctx:
            _, bot = create_bot(ctx)
            builder = MessageBuilder()
            event = guild_message_create_event()

            seg = DCMessageSegment.custom_emoji("", "")
            result = await builder.convert(seg, bot, event)
            assert isinstance(result, QQMessageSegment)
            assert result.type == "image"
            assert result.data["file"] == f"base64://{b64encode(test_png_bytes)}"


@pytest.mark.asyncio
async def test_convert_mention_user(app: App) -> None:
    from nonebot_plugin_dcqq_relay.dc_to_qq import MessageBuilder

    async with app.test_api() as ctx:
        _, bot = create_bot(ctx)
        builder = MessageBuilder()
        event = guild_message_create_event()

        user_id = 1
        username = "test"
        global_name = "Test"
        seg = DCMessageSegment.mention_user(user_id)
        ctx.should_call_api(
            api="get_guild_member",
            data={"guild_id": int("6" * 18), "user_id": user_id},
            result=guild_member(str(user_id), username, global_name),
        )
        result = await builder.convert(seg, bot, event)
        assert isinstance(result, QQMessageSegment)
        assert result.data == {"text": f"@{global_name}({username})"}

        nick = "TT"
        seg = DCMessageSegment.mention_user(user_id)
        ctx.should_call_api(
            api="get_guild_member",
            data={"guild_id": int("6" * 18), "user_id": user_id},
            result=guild_member(str(user_id), username, global_name, nick),
        )
        result = await builder.convert(seg, bot, event)
        assert isinstance(result, QQMessageSegment)
        assert result.data == {"text": f"@{nick}({username})"}


@pytest.mark.asyncio
async def test_convert_mention_role(app: App) -> None:
    from nonebot_plugin_dcqq_relay.dc_to_qq import MessageBuilder

    async with app.test_api() as ctx:
        _, bot = create_bot(ctx)
        builder = MessageBuilder()
        event = guild_message_create_event()

        role_id = 1
        name = "test"
        seg = DCMessageSegment.mention_role(role_id)
        ctx.should_call_api(
            api="get_guild_role",
            data={"guild_id": int("6" * 18), "role_id": role_id},
            result=role(str(role_id), name),
        )
        result = await builder.convert(seg, bot, event)
        assert isinstance(result, QQMessageSegment)
        assert result.data == {"text": f"@{name}"}


@pytest.mark.asyncio
async def test_convert_mention_channel(app: App) -> None:
    from nonebot_plugin_dcqq_relay.dc_to_qq import MessageBuilder

    async with app.test_api() as ctx:
        _, bot = create_bot(ctx)
        builder = MessageBuilder()
        event = guild_message_create_event()

        channel_id = 1
        name = "test"
        seg = DCMessageSegment.mention_channel(channel_id)
        ctx.should_call_api(
            api="get_channel",
            data={"channel_id": channel_id},
            result=channel(str(channel_id), name=name),
        )
        result = await builder.convert(seg, bot, event)
        assert isinstance(result, QQMessageSegment)
        assert result.data == {"text": f"#{name}"}


@pytest.mark.asyncio
async def test_convert_mention_everyone(app: App) -> None:
    from nonebot_plugin_dcqq_relay.dc_to_qq import MessageBuilder

    async with app.test_api() as ctx:
        _, bot = create_bot(ctx)
        builder = MessageBuilder()
        event = guild_message_create_event()

        seg = DCMessageSegment.mention_everyone()
        result = await builder.convert(seg, bot, event)
        assert isinstance(result, QQMessageSegment)
        assert result.type == "at"
        assert result.data["qq"] == "all"


@pytest.mark.asyncio
async def test_convert_text(app: App) -> None:
    from nonebot_plugin_dcqq_relay.dc_to_qq import MessageBuilder

    async with app.test_api() as ctx:
        _, bot = create_bot(ctx)
        builder = MessageBuilder()
        event = guild_message_create_event()

        content = "test"
        seg = DCMessageSegment.text(content)
        result = await builder.convert(seg, bot, event)
        assert isinstance(result, QQMessageSegment)
        assert result.type == "text"
        assert result.data["text"] == content


@pytest.mark.asyncio
async def test_convert_timestamp(app: App) -> None:
    from nonebot_plugin_dcqq_relay.dc_to_qq import MessageBuilder

    async with app.test_api() as ctx:
        _, bot = create_bot(ctx)
        builder = MessageBuilder()
        event = guild_message_create_event()

        timestamp = 1773238053
        seg = DCMessageSegment.timestamp(timestamp)
        result = await builder.convert(seg, bot, event)
        assert isinstance(result, QQMessageSegment)
        assert result.type == "text"
        assert result.data["text"] == f"<t:{timestamp}>"

        timestamp = datetime.datetime.now()
        seg = DCMessageSegment.timestamp(timestamp)
        result = await builder.convert(seg, bot, event)
        assert isinstance(result, QQMessageSegment)
        assert result.type == "text"
        assert result.data["text"] == f"<t:{int(timestamp.timestamp())}>"
