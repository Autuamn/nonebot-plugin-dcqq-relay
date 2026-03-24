from tests.data import (
    dc_complex_forward_event,
    group_recall_event,
    guild_message_delete_event,
    qq_complex_event,
)
from tests.utils import create_bot

from nonebot.exception import FinishedException
from nonebug import App
import pytest


@pytest.mark.asyncio
async def test_handle_get_link_none(app: App) -> None:
    from nonebot_plugin_dcqq_relay import message_relay

    async with app.test_matcher() as ctx:
        qq_bot, _ = create_bot(ctx)

        with pytest.RaisesExc(FinishedException):
            await message_relay(qq_bot, qq_complex_event(), None)


@pytest.mark.asyncio
async def test_matcher_unmatch_beginning(app: App) -> None:
    from nonebot_plugin_dcqq_relay import NotStartswithRule

    from nonebot import on

    matcher = on(
        rule=NotStartswithRule(("/", "!")),
    )
    async with app.test_matcher(matcher) as ctx:
        qq_bot, _ = create_bot(ctx)
        ctx.receive_event(qq_bot, qq_complex_event("/cmd"))
        ctx.should_not_pass_rule()
        ctx.receive_event(qq_bot, qq_complex_event("!cmd"))
        ctx.should_not_pass_rule()
        ctx.receive_event(qq_bot, qq_complex_event("cmd"))
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

        ctx.receive_event(qq_bot, qq_complex_event())
        ctx.should_not_pass_rule()
        ctx.receive_event(qq_bot, qq_complex_event(to_me=True))
        ctx.should_pass_rule()

        ctx.receive_event(dc_bot, dc_complex_forward_event())
        ctx.should_not_pass_rule()
        ctx.receive_event(dc_bot, dc_complex_forward_event(to_me=True))
        ctx.should_pass_rule()

        ctx.receive_event(qq_bot, group_recall_event())
        ctx.should_pass_rule()
        ctx.receive_event(dc_bot, guild_message_delete_event())
        ctx.should_pass_rule()
