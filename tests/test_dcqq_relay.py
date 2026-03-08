from base64 import b64decode

from tests.data import (
    dc_complex_forward_event,
    execute_webhook_data,
    execute_webhook_result,
    get_channel_message_result,
    get_channel_result,
    get_guild_member_result,
    get_guild_preview_result,
    get_guild_role_result,
    group_recall_event,
    guild_message_delete_event,
    qq_complex_event,
    send_group_msg_result,
)
from tests.utils import create_bot, prepare_webhooks_calls

from nonebug import App
import pytest
from pytest_httpserver import HTTPServer
from sqlalchemy.exc import InvalidRequestError


@pytest.mark.asyncio
async def test_create_dc_to_qq(app: App, httpserver: HTTPServer) -> None:
    httpserver.expect_request("/test.png").respond_with_data(
        b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAEYAAAAaCAYAAAAKYioIAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAAFiUAABYlAUlSJPAAAAEcSURBVFhH7ZABCsMwDAP7/093eMxgTBxJSbtuTQ9MSSPLjrb9oQkdzLatlSH1WgvlCabBaqEYTzAFSwbDvOetMCFbd4B5B1TkQPyc659g9qWCOZorA2XnfjUYX8o983mE6MF4oXsHqlijHmjp3l0F8qyI+l4/dFUHZ3rDI8oc1tNwbVUV0L3XjEDDHVZnKNoW9JzPt2R2CdTPaCIz+xhsP1TNLOKPRqUw0hNhe08P5gxmwrl1MMZoOLcPxhgJ52eCmelnUGf0tPEOOqqDM94/44FQvCtt3pFyzE0ZdG+4hikVpafS5v+0oy/tBvHs/65AnV9p83/5Rb6IsszRxB3UPVo9LD/rXdeBGkbGw4mV+ctgjqIKxVg6mJp9fwGt8jszqRET6QAAAABJRU5ErkJggg=="
        )
    )
    url = httpserver.url_for("/test.png")

    from nonebot_plugin_dcqq_relay import matcher, prepare_webhooks

    async with app.test_matcher(matcher) as ctx:
        _, dc_bot = create_bot(ctx)
        prepare_webhooks_calls(ctx)

        await prepare_webhooks(dc_bot)
        ctx.receive_event(dc_bot, dc_complex_forward_event(url))
        ctx.should_pass_rule()

        ctx.should_call_api(
            "get_channel_message",
            {"channel_id": int("2" * 18), "message_id": int("1" * 18)},
            get_channel_message_result(url),
        )
        ctx.should_call_api(
            "get_channel",
            {"channel_id": int("4" * 18)},
            get_channel_result(),
        )
        ctx.should_call_api(
            "get_guild_member",
            {"guild_id": int("6" * 18), "user_id": int("3" * 18)},
            get_guild_member_result(),
        )
        ctx.should_call_api(
            "get_guild_role",
            {"guild_id": int("6" * 18), "role_id": int("5" * 18)},
            get_guild_role_result(),
        )
        ctx.should_call_api(
            "get_guild_preview",
            {"guild_id": int("6" * 18)},
            get_guild_preview_result(),
        )
        ctx.should_call_api(
            "get_version_info",
            {},
            {
                "app_name": "NapCat.Onebot",
            },
        )
        ctx.should_call_api(
            "send_group_msg",
            send_group_msg_result(),
        )


@pytest.mark.asyncio
async def test_create_qq_to_dc(
    app: App,
) -> None:
    from nonebot_plugin_dcqq_relay import matcher, prepare_webhooks

    async with app.test_matcher(matcher) as ctx:
        qq_bot, dc_bot = create_bot(ctx)
        prepare_webhooks_calls(ctx)
        await prepare_webhooks(dc_bot)

        dc_bot.adapter.driver._bots[dc_bot.self_id] = dc_bot

        ctx.receive_event(qq_bot, qq_complex_event())
        ctx.should_pass_rule()

        ctx.should_call_api(
            "execute_webhook",
            execute_webhook_data(),
            execute_webhook_result(),
        )


@pytest.mark.asyncio
async def test_delete_qq_to_dc(app: App) -> None:
    """QQ 撤回 -> 删除 DC 对应消息，并清理 DB"""
    from nonebot_plugin_dcqq_relay import matcher, prepare_webhooks
    from nonebot_plugin_dcqq_relay.model import MsgID

    from nonebot_plugin_orm import get_session

    async with app.test_matcher(matcher) as ctx:
        qq_bot, dc_bot = create_bot(ctx)
        prepare_webhooks_calls(ctx)
        await prepare_webhooks(dc_bot)

        qq_msg_id = 12345
        dc_msg_id = 987654321
        async with get_session() as session:
            session.add(MsgID(dcid=dc_msg_id, qqid=qq_msg_id))
            await session.commit()

        dc_bot.adapter.driver._bots[dc_bot.self_id] = dc_bot

        ctx.receive_event(qq_bot, group_recall_event(qq_msg_id, group_id=10001))
        ctx.should_pass_rule()
        ctx.should_call_api(
            "delete_message",
            {"channel_id": int("2" * 18), "message_id": dc_msg_id},
            None,
        )

    async with get_session() as session:
        with pytest.RaisesExc(InvalidRequestError):
            await session.delete(MsgID(dcid=dc_msg_id, qqid=qq_msg_id))


@pytest.mark.asyncio
async def test_delete_dc_to_qq(app: App) -> None:
    """DC 删除消息 -> 撤回 QQ 对应消息，并清理 DB"""
    from nonebot_plugin_dcqq_relay import matcher, prepare_webhooks
    from nonebot_plugin_dcqq_relay.model import MsgID

    from nonebot_plugin_orm import get_session

    async with app.test_matcher(matcher) as ctx:
        _, dc_bot = create_bot(ctx)
        prepare_webhooks_calls(ctx)
        await prepare_webhooks(dc_bot)

        dc_msg_id = int("1" * 18)
        qq_msg_id = 54321
        async with get_session() as session:
            session.add(MsgID(dcid=dc_msg_id, qqid=qq_msg_id))
            await session.commit()

        ctx.receive_event(dc_bot, guild_message_delete_event(str(dc_msg_id)))
        ctx.should_pass_rule()
        ctx.should_call_api("delete_msg", {"message_id": qq_msg_id}, None)

    with pytest.RaisesExc(InvalidRequestError):
        async with get_session() as session:
            await session.delete(MsgID(dcid=dc_msg_id, qqid=qq_msg_id))
