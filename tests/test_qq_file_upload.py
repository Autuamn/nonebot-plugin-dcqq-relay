from tests.conftest import create_bot
from tests.data import test_png_bytes

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebug import App
import pytest
from sqlalchemy.util import b64encode


def test_split_messages() -> None:
    from nonebot_plugin_dcqq_relay.dc_to_qq import split_messages
    from nonebot_plugin_dcqq_relay.qq_to_dc import MessageBuilder

    types = list(MessageBuilder()._mapping.keys())
    messages = Message([MessageSegment(type, {}) for type in types])
    combinable, files = split_messages(messages)

    assert len(combinable) == 2
    assert len(combinable[0]) == (len(types) - 2)
    assert len(combinable[1]) == 1
    assert len(files) == 1


@pytest.mark.asyncio
async def test_napcat(app: App) -> None:
    from nonebot_plugin_dcqq_relay.dc_to_qq import gather_send

    async with app.test_api() as ctx:
        bot, _ = create_bot(ctx)
        qq_group_id = 1
        file_name = "test.png"
        msg_to_send: list[Message] = []
        files: list[Message] = [
            Message(
                [MessageSegment("file", {"file": test_png_bytes, "name": file_name})]
            )
        ]
        ctx.should_call_api("get_version_info", {}, {"app_name": "NapCat.Onebot"})
        ctx.should_call_api(
            "send_group_msg",
            {
                "group_id": 1,
                "message": [
                    MessageSegment(
                        type="file",
                        data={
                            "file": f"base64://{b64encode(test_png_bytes)}",
                            "name": "test.png",
                        },
                    )
                ],
            },
        )
        await gather_send(bot, qq_group_id, msg_to_send, files)


@pytest.mark.asyncio
async def test_lagrange(app: App) -> None:
    from nonebot_plugin_dcqq_relay.dc_to_qq import cache_dir, gather_send

    async with app.test_api() as ctx:
        bot, _ = create_bot(ctx)
        qq_group_id = 1
        file_name = "test.png"
        file_path = (cache_dir / file_name).as_posix()
        msg_to_send: list[Message] = []
        files = [
            Message(
                [MessageSegment("file", {"file": test_png_bytes, "name": file_name})]
            )
        ]
        ctx.should_call_api("get_version_info", {}, {"app_name": "Lagrange.OneBot"})
        ctx.should_call_api(
            "upload_group_file",
            {
                "group_id": qq_group_id,
                "file": file_path,
                "name": file_name,
                "folder": "",
            },
        )
        await gather_send(bot, qq_group_id, msg_to_send, files)
