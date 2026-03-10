import uuid

from tests.conftest import create_bot
from tests.data import amr_bytes, group_message_event, test_mp4_bytes, test_png_bytes

from anyio import Path
from nonebot.adapters.onebot.v11 import (
    Message as QQMessage,
    MessageSegment as QQMessageSegment,
)
from nonebug import App
import pytest
from pytest_httpserver import HTTPServer


@pytest.mark.asyncio
async def test_build_should_not_empty(app: App, httpserver: HTTPServer) -> None:
    from nonebot_plugin_dcqq_relay.qq_to_dc import MessageBuilder

    async with app.test_api() as ctx:
        bot, _ = create_bot(ctx)
        builder = MessageBuilder()
        seg_msg = QQMessage()
        text, _, _ = await builder.build(seg_msg, bot, group_message_event())
        assert text == "[未知消息]"


@pytest.mark.asyncio
async def test_extract_plain_text(app: App) -> None:
    from nonebot_plugin_dcqq_relay.qq_to_dc import MessageBuilder, MsgResult

    msg_res = [MsgResult(text="a"), MsgResult(text="b")]
    assert MessageBuilder().extract_plain_text(msg_res) == "ab"


@pytest.mark.asyncio
async def test_convert_text(app: App) -> None:
    from nonebot_plugin_dcqq_relay.qq_to_dc import MessageBuilder, MsgResult

    async with app.test_api() as ctx:
        bot, _ = create_bot(ctx)
        builder = MessageBuilder()

        result = await builder.convert(
            seg=QQMessageSegment.text("@everyone, @here, xxx"),
            bot=bot,
            event=group_message_event(),
        )
        assert result.text == MsgResult(text="@.everyone, @.here, xxx").text


@pytest.mark.asyncio
async def test_convert_at(app: App) -> None:
    from nonebot_plugin_dcqq_relay.qq_to_dc import MessageBuilder, MsgResult

    async with app.test_api() as ctx:
        bot, _ = create_bot(ctx)
        builder = MessageBuilder()

        result = await builder.convert(
            seg=QQMessageSegment.at("0"),
            bot=bot,
            event=group_message_event(),
        )
        assert result.text == MsgResult(text="@everyone").text
        assert result.ensure_text

        result = await builder.convert(
            seg=QQMessageSegment.at("all"),
            bot=bot,
            event=group_message_event(),
        )
        assert result.text == MsgResult(text="@everyone").text
        assert result.ensure_text

        result = await builder.convert(
            seg=QQMessageSegment("at", {"user_id": "all"}),
            bot=bot,
            event=group_message_event(),
        )
        assert result.text == MsgResult(text="@everyone").text
        assert result.ensure_text

        name = "test"
        qq = "10001"
        result = await builder.convert(
            seg=QQMessageSegment("at", {"user_id": qq, "name": name}),
            bot=bot,
            event=group_message_event(),
        )
        assert (
            result.text
            == MsgResult(text=f"[{name}](mailto:{qq}@qq.com)[QQ:{qq}] ").text
        )
        assert result.ensure_text

        name = "test"
        qq = "10001"
        group_id = 10001
        ctx.should_call_api(
            api="get_group_member_info",
            data={"group_id": group_id, "user_id": qq, "no_cache": True},
            result={
                "group_id": group_id,
                "user_id": int(qq),
                "nickname": name,
            },
        )
        result = await builder.convert(
            seg=QQMessageSegment.at(10001),
            bot=bot,
            event=group_message_event(group_id=group_id),
        )
        assert (
            result.text
            == MsgResult(text=f"[{name}](mailto:{qq}@qq.com)[QQ:{qq}] ").text
        )
        assert result.ensure_text


@pytest.mark.asyncio
async def test_convert_face(app: App) -> None:
    from nonebot_plugin_dcqq_relay.qq_to_dc import MessageBuilder, MsgResult

    async with app.test_api() as ctx:
        bot, _ = create_bot(ctx)
        builder = MessageBuilder()

        result = await builder.convert(
            seg=QQMessageSegment(
                type="face",
                data={
                    "id": "337",
                    "raw": {
                        "faceIndex": 337,
                        "faceText": "[花朵脸]",
                        "faceType": 3,
                        "packId": "1",
                        "stickerId": "22",
                    },
                },
            ),
            bot=bot,
            event=group_message_event(),
        )
        assert result.text == MsgResult(text="[花朵脸]").text
        assert result.ensure_text


@pytest.mark.asyncio
async def test_convert_mface(app: App, httpserver: HTTPServer) -> None:
    from nonebot_plugin_dcqq_relay.qq_to_dc import MessageBuilder, MsgResult

    httpserver.expect_request("/test.png").respond_with_data(test_png_bytes)
    url = httpserver.url_for("/test.png")
    async with app.test_api() as ctx:
        bot, _ = create_bot(ctx)
        builder = MessageBuilder()
        summary = "[test]"
        result = await builder.convert(
            seg=QQMessageSegment(
                "mface",
                {
                    "summary": summary,
                    "url": url,
                },
            ),
            bot=bot,
            event=group_message_event(),
        )
        assert result.text == MsgResult(text=summary).text
        assert result.file is not None
        assert result.file.content == test_png_bytes
        assert result.file.filename == f"{summary}.gif"


@pytest.mark.asyncio
async def test_convert_image(app: App, httpserver: HTTPServer) -> None:
    from nonebot_plugin_dcqq_relay.qq_to_dc import MessageBuilder, MsgResult

    httpserver.expect_request("/test.png").respond_with_data(test_png_bytes)
    url = httpserver.url_for("/test.png")
    async with app.test_api() as ctx:
        bot, _ = create_bot(ctx)
        builder = MessageBuilder()
        file = "test.png"
        result = await builder.convert(
            seg=QQMessageSegment(
                "image",
                {
                    "summary": "",
                    "file": file,
                    "url": url,
                },
            ),
            bot=bot,
            event=group_message_event(),
        )
        assert result.text == MsgResult(text="[图片]").text
        assert result.file is not None
        assert result.file.content == test_png_bytes
        assert result.file.filename == file


@pytest.mark.asyncio
async def test_convert_record(app: App, httpserver: HTTPServer) -> None:
    from nonebot_plugin_dcqq_relay.qq_to_dc import MessageBuilder, MsgResult

    httpserver.expect_request("/test.amr").respond_with_data(amr_bytes)
    url = httpserver.url_for("/test.amr")
    async with app.test_api() as ctx:
        from nonebot_plugin_localstore import get_cache_dir

        path = Path(get_cache_dir("test") / "test.amr")
        await path.write_bytes(amr_bytes)

        bot, _ = create_bot(ctx)
        builder = MessageBuilder()
        file = "test.amr"
        result = await builder.convert(
            seg=QQMessageSegment(
                "record",
                {
                    "file": file,
                    "path": path.as_posix(),
                    "url": url,
                },
            ),
            bot=bot,
            event=group_message_event(),
        )
        assert result.text == MsgResult(text="[语音]").text
        assert result.file is not None
        assert len(result.file.content) > 0
        assert result.file.filename == "voice-message.ogg"

        result = await builder.convert(
            seg=QQMessageSegment(
                "record",
                {
                    "file": file,
                    "url": url,
                },
            ),
            bot=bot,
            event=group_message_event(),
        )
        assert result.text == MsgResult(text="[语音]").text
        assert result.file is not None
        assert len(result.file.content) > 0
        assert result.file.filename == "voice-message.ogg"

        result = await builder.convert(
            seg=QQMessageSegment(
                "record",
                {
                    "file": path.as_uri(),
                },
            ),
            bot=bot,
            event=group_message_event(),
        )
        assert result.text == MsgResult(text="[语音]").text
        assert result.file is not None
        assert len(result.file.content) > 0
        assert result.file.filename == "voice-message.ogg"


@pytest.mark.asyncio
async def test_convert_video(app: App, httpserver: HTTPServer) -> None:
    from nonebot_plugin_dcqq_relay.qq_to_dc import MessageBuilder, MsgResult

    httpserver.expect_request("/test.mp4").respond_with_data(test_mp4_bytes)
    url = httpserver.url_for("/test.mp4")
    async with app.test_api() as ctx:
        from nonebot_plugin_localstore import get_cache_dir

        path = Path(get_cache_dir("test") / "test.mp4")
        await path.write_bytes(test_mp4_bytes)

        bot, _ = create_bot(ctx)
        builder = MessageBuilder()
        file = str(uuid.uuid1())
        result = await builder.convert(
            seg=QQMessageSegment(
                type="video",
                data={
                    "file": file,
                    "url": url,
                },
            ),
            bot=bot,
            event=group_message_event(),
        )
        assert result.text == MsgResult(text=f"[{file}.mp4]").text
        assert result.file is not None
        assert len(result.file.content) > 0
        assert result.file.filename == file + ".mp4"

        result = await builder.convert(
            seg=QQMessageSegment(
                "video",
                {
                    "file": file,
                    "url": url,
                    "path": path.as_posix(),
                },
            ),
            bot=bot,
            event=group_message_event(),
        )
        assert result.text == MsgResult(text=f"[{file}.mp4]").text
        assert result.file is not None
        assert len(result.file.content) > 0
        assert result.file.filename == file + ".mp4"

        result = await builder.convert(
            seg=QQMessageSegment(
                "video",
                {
                    "file": file,
                    "url": path.as_posix(),
                },
            ),
            bot=bot,
            event=group_message_event(),
        )
        assert result.text == MsgResult(text=f"[{file}.mp4]").text
        assert result.file is not None
        assert len(result.file.content) > 0
        assert result.file.filename == file + ".mp4"


@pytest.mark.asyncio
async def test_convert_file(app: App, httpserver: HTTPServer) -> None:
    from nonebot_plugin_dcqq_relay.qq_to_dc import MessageBuilder, MsgResult

    httpserver.expect_request("/test.mp4").respond_with_data(test_mp4_bytes)
    url = httpserver.url_for("/test.mp4")
    async with app.test_api() as ctx:
        from nonebot_plugin_localstore import get_cache_dir

        path = Path(get_cache_dir("test") / "test.mp4")
        await path.write_bytes(test_mp4_bytes)

        bot, _ = create_bot(ctx)
        builder = MessageBuilder()
        file = "test.mp4"
        file_id = "/" + str(uuid.uuid1())
        result = await builder.convert(
            seg=QQMessageSegment(
                "file",
                {
                    "file": file,
                    "url": url,
                },
            ),
            bot=bot,
            event=group_message_event(),
        )
        assert result.text == MsgResult(text=f"[{file}]").text
        assert result.file is not None
        assert len(result.file.content) > 0
        assert result.file.filename == file

        ctx.should_call_api(
            "get_file",
            {"file_id": file_id},
            {
                "file": path.as_posix(),
                "file_name": file,
            },
        )
        result = await builder.convert(
            seg=QQMessageSegment(
                "file",
                {
                    "file": file,
                    "file_id": file_id,
                },
            ),
            bot=bot,
            event=group_message_event(),
        )
        assert result.text == MsgResult(text=f"[{file}]").text
        assert result.file is not None
        assert len(result.file.content) > 0
        assert result.file.filename == file

        result = await builder.convert(
            seg=QQMessageSegment(
                "file",
                {"file": file},
            ),
            bot=bot,
            event=group_message_event(),
        )
        assert result.text == MsgResult(text=f"[{file}]").text
        assert result.file is None
        assert result.ensure_text


@pytest.mark.asyncio
async def test_convert_forward(app: App) -> None:
    from nonebot_plugin_dcqq_relay.qq_to_dc import MessageBuilder, MsgResult

    async with app.test_api() as ctx:
        bot, _ = create_bot(ctx)
        builder = MessageBuilder()

        result = await builder.convert(
            QQMessageSegment(type="forward", data={"id": "1"}),
            bot,
            group_message_event(),
        )
        assert result.text == MsgResult(text="[合并转发]").text
        assert result.ensure_text


@pytest.mark.asyncio
async def test_convert_rps(app: App) -> None:
    from nonebot_plugin_dcqq_relay.qq_to_dc import MessageBuilder, MsgResult

    async with app.test_api() as ctx:
        bot, _ = create_bot(ctx)
        builder = MessageBuilder()

        result = await builder.convert(
            QQMessageSegment(type="rps"),
            bot,
            group_message_event(),
        )
        assert result.text == MsgResult(text="[猜拳]").text
        assert result.ensure_text

        result = await builder.convert(
            QQMessageSegment(type="rps", data={"result": "3"}),
            bot,
            group_message_event(),
        )
        assert result.text == MsgResult(text="[猜拳：布]").text
        assert result.ensure_text


@pytest.mark.asyncio
async def test_convert_dice(app: App) -> None:
    from nonebot_plugin_dcqq_relay.qq_to_dc import MessageBuilder, MsgResult

    async with app.test_api() as ctx:
        bot, _ = create_bot(ctx)
        builder = MessageBuilder()

        result = await builder.convert(
            QQMessageSegment(type="dice"),
            bot,
            group_message_event(),
        )
        assert result.text == MsgResult(text="[掷骰子]").text
        assert result.ensure_text

        result = await builder.convert(
            QQMessageSegment(type="dice", data={"result": "4"}),
            bot,
            group_message_event(),
        )
        assert result.text == MsgResult(text="[掷骰子：4]").text
        assert result.ensure_text


@pytest.mark.asyncio
async def test_convert_other(app: App) -> None:
    from nonebot_plugin_dcqq_relay.qq_to_dc import MessageBuilder, MsgResult

    async with app.test_api() as ctx:
        bot, _ = create_bot(ctx)
        builder = MessageBuilder()

        seg = QQMessageSegment("other", {"other": "xx"})

        result = await builder.convert(seg, bot, group_message_event())
        assert (
            result.text
            == MsgResult(
                text=f"[不支持的类型](type: {seg.type}, data: {seg.data})"
            ).text
        )
        assert result.ensure_text
