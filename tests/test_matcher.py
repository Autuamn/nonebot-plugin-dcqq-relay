from unittest.mock import patch

from tests.conftest import create_bot
from tests.data import (
    execute_webhook_data,
    execute_webhook_result,
    get_test_links,
    group_message_event,
    group_recall_event,
    guild_message_create_event,
    guild_message_delete_event,
    message_get,
    send_group_msg_data,
)

from nonebot.exception import FinishedException
from nonebug import App
import pytest
from sqlalchemy import select


@pytest.mark.asyncio
async def test_create_dc_to_qq(app: App) -> None:
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
async def test_create_dc_to_qq_ensure_message(app: App) -> None:
    with patch(
        target="nonebot_plugin_dcqq_relay.utils.with_webhook_links",
        new_callable=get_test_links,
    ):
        from nonebot_plugin_dcqq_relay import matcher
        from nonebot_plugin_dcqq_relay.model import MsgID

        from nonebot_plugin_orm import get_session

        async with app.test_matcher(matcher) as ctx:
            _, dc_bot = create_bot(ctx)

            ctx.receive_event(dc_bot, guild_message_create_event(content=""))
            ctx.should_pass_rule()
            ctx.should_call_api(
                api="get_channel_message",
                data={
                    "channel_id": int("2" * 18),
                    "message_id": int("1" * 18),
                },
                result=message_get(),
            )
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
async def test_create_qq_to_dc(
    app: App,
) -> None:
    with patch(
        target="nonebot_plugin_dcqq_relay.utils.with_webhook_links",
        new_callable=get_test_links,
    ):
        from nonebot_plugin_dcqq_relay import matcher
        from nonebot_plugin_dcqq_relay.model import MsgID

        from nonebot_plugin_orm import get_session

        async with app.test_matcher(matcher) as ctx:
            qq_bot, dc_bot = create_bot(ctx)
            dc_bot.adapter.driver._bots[dc_bot.self_id] = dc_bot

            ctx.receive_event(qq_bot, group_message_event())
            ctx.should_pass_rule()
            ctx.should_call_api(
                api="execute_webhook",
                data=execute_webhook_data(),
                result=execute_webhook_result(),
            )

        async with get_session() as session:
            msgids = await session.scalars(select(MsgID).filter(MsgID.dcid == 0))
            count = 0
            for msgid in msgids:
                count += 1
                await session.delete(msgid)
            await session.commit()
            assert count == 1


@pytest.mark.asyncio
async def test_delete_qq_to_dc(app: App) -> None:
    with patch(
        target="nonebot_plugin_dcqq_relay.utils.with_webhook_links",
        new_callable=get_test_links,
    ):
        from nonebot_plugin_dcqq_relay import matcher
        from nonebot_plugin_dcqq_relay.model import MsgID

        from nonebot_plugin_orm import get_session

        async with app.test_matcher(matcher) as ctx:
            qq_bot, dc_bot = create_bot(ctx)
            dc_bot.adapter.driver._bots[dc_bot.self_id] = dc_bot

            qq_msg_id = 12345
            dc_msg_id = 987654321
            async with get_session() as session:
                session.add(MsgID(dcid=dc_msg_id, qqid=qq_msg_id))
                await session.commit()

            ctx.receive_event(qq_bot, group_recall_event(qq_msg_id, group_id=10001))
            ctx.should_pass_rule()
            ctx.should_call_api(
                api="delete_message",
                data={"channel_id": int("2" * 18), "message_id": dc_msg_id},
                result=None,
            )

        async with get_session() as session:
            msgids = await session.scalars(
                select(MsgID).filter(MsgID.dcid == dc_msg_id)
            )
            count = 0
            for msgid in msgids:
                count += 1
                await session.delete(msgid)
            await session.commit()
            assert count == 0


@pytest.mark.asyncio
async def test_delete_dc_to_qq(app: App) -> None:
    with patch(
        target="nonebot_plugin_dcqq_relay.utils.with_webhook_links",
        new_callable=get_test_links,
    ):
        from nonebot_plugin_dcqq_relay import matcher
        from nonebot_plugin_dcqq_relay.model import MsgID

        from nonebot_plugin_orm import get_session

        async with app.test_matcher(matcher) as ctx:
            _, dc_bot = create_bot(ctx)

            dc_msg_id = int("1" * 18)
            qq_msg_id = 54321
            async with get_session() as session:
                session.add(MsgID(dcid=dc_msg_id, qqid=qq_msg_id))
                await session.commit()

            ctx.receive_event(dc_bot, guild_message_delete_event(str(dc_msg_id)))
            ctx.should_pass_rule()
            ctx.should_call_api("delete_msg", {"message_id": qq_msg_id}, None)

        async with get_session() as session:
            msgids = await session.scalars(
                select(MsgID).filter(MsgID.dcid == dc_msg_id)
            )
            count = 0
            for msgid in msgids:
                count += 1
                await session.delete(msgid)
            await session.commit()
            assert count == 0


@pytest.mark.asyncio
async def test_handle_get_link_none(app: App) -> None:
    from nonebot_plugin_dcqq_relay import message_relay

    async with app.test_matcher() as ctx:
        qq_bot, _ = create_bot(ctx)

        with pytest.RaisesExc(FinishedException):
            await message_relay(qq_bot, group_message_event(), None)


@pytest.mark.asyncio
async def test_handle_type_not_match(app: App) -> None:
    with patch(
        "nonebot_plugin_dcqq_relay.utils.with_webhook_links",
        new_callable=get_test_links,
    ):
        from nonebot_plugin_dcqq_relay import message_relay

        async with app.test_matcher() as ctx:
            qq_bot, _ = create_bot(ctx)

            await message_relay(qq_bot, guild_message_create_event())


@pytest.mark.asyncio
async def test_matcher_unmatch_beginning(app: App) -> None:
    from nonebot_plugin_dcqq_relay import NotStartswithRule

    from nonebot import on

    matcher = on(
        rule=NotStartswithRule(("/", "!")),
    )
    async with app.test_matcher(matcher) as ctx:
        qq_bot, _ = create_bot(ctx)
        ctx.receive_event(qq_bot, group_message_event("/cmd"))
        ctx.should_not_pass_rule()
        ctx.receive_event(qq_bot, group_message_event("!cmd"))
        ctx.should_not_pass_rule()
        ctx.receive_event(qq_bot, group_message_event("cmd"))
        ctx.should_pass_rule()


@pytest.mark.asyncio
async def test_matcher_only_to_me(app: App) -> None:
    from nonebot_plugin_dcqq_relay import check_to_me

    from nonebot import on

    matcher = on(
        rule=check_to_me,
    )
    async with app.test_matcher(matcher) as ctx:
        qq_bot, dc_bot = create_bot(ctx)

        ctx.receive_event(qq_bot, group_message_event())
        ctx.should_not_pass_rule()
        ctx.receive_event(qq_bot, group_message_event(to_me=True))
        ctx.should_pass_rule()

        ctx.receive_event(dc_bot, guild_message_create_event())
        ctx.should_not_pass_rule()
        ctx.receive_event(dc_bot, guild_message_create_event(to_me=True))
        ctx.should_pass_rule()

        ctx.receive_event(qq_bot, group_recall_event())
        ctx.should_pass_rule()
        ctx.receive_event(dc_bot, guild_message_delete_event())
        ctx.should_pass_rule()
