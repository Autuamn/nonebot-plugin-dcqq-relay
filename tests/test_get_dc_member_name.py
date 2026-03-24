from tests.data import get_guild_member_result
from tests.utils import create_bot

from nonebot.adapters.discord.exception import ActionFailed
from nonebot.drivers import Response
from nonebug import App
import pytest


@pytest.mark.asyncio
async def test_nick_and_user_exist(app: App) -> None:
    from nonebot_plugin_dcqq_relay.utils import get_dc_member_name

    async with app.test_api() as ctx:
        _, dc_bot = create_bot(ctx)

        call_data: dict[str, int] = {"guild_id": 1, "user_id": 2}

        name = "Test1"
        username = "test"

        ctx.should_call_api(
            "get_guild_member",
            call_data,
            get_guild_member_result(nick=name, username=username),
        )
        assert await get_dc_member_name(dc_bot, **call_data) == (name, username)


@pytest.mark.asyncio
async def test_only_nick_exist(app: App) -> None:
    from nonebot_plugin_dcqq_relay.utils import get_dc_member_name

    async with app.test_api() as ctx:
        _, dc_bot = create_bot(ctx)

        call_data: dict[str, int] = {"guild_id": 1, "user_id": 2}

        name = "Test1"
        username = "test"

        ctx.should_call_api(
            "get_guild_member",
            call_data,
            get_guild_member_result(nick=name, username=username, unset_user=True),
        )
        assert await get_dc_member_name(dc_bot, **call_data) == (name, "")


@pytest.mark.asyncio
async def test_only_user_exist(app: App) -> None:
    from nonebot_plugin_dcqq_relay.utils import get_dc_member_name

    async with app.test_api() as ctx:
        _, dc_bot = create_bot(ctx)

        call_data: dict[str, int] = {"guild_id": 1, "user_id": 2}

        name = "Test"
        username = "test"

        ctx.should_call_api(
            "get_guild_member",
            call_data,
            get_guild_member_result(username=username, global_name=name),
        )
        assert await get_dc_member_name(dc_bot, **call_data) == (name, username)


@pytest.mark.asyncio
async def test_nick_and_user_not_exist(app: App) -> None:
    from nonebot_plugin_dcqq_relay.utils import get_dc_member_name

    async with app.test_api() as ctx:
        _, dc_bot = create_bot(ctx)

        call_data: dict[str, int] = {"guild_id": 1, "user_id": 2}

        ctx.should_call_api(
            "get_guild_member",
            call_data,
            get_guild_member_result(unset_user=True),
        )
        assert await get_dc_member_name(dc_bot, **call_data) == (
            "",
            str(call_data["user_id"]),
        )


@pytest.mark.asyncio
async def test_unknown_user_error(app: App) -> None:
    from nonebot_plugin_dcqq_relay.utils import get_dc_member_name

    async with app.test_api() as ctx:
        _, dc_bot = create_bot(ctx)

        call_data: dict[str, int] = {"guild_id": 1, "user_id": 2}

        ctx.should_call_api(
            "get_guild_member",
            call_data,
            exception=ActionFailed(
                Response(
                    status_code=404,
                    content=b'{"message": "Unknown User", "code": 10013}',
                )
            ),
        )
        assert await get_dc_member_name(dc_bot, **call_data) == (
            "(error:未知用户)",
            str(call_data["user_id"]),
        )


@pytest.mark.asyncio
async def test_unknown_guild_error(app: App) -> None:
    from nonebot_plugin_dcqq_relay.utils import get_dc_member_name

    async with app.test_api() as ctx:
        _, dc_bot = create_bot(ctx)

        call_data: dict[str, int] = {"guild_id": 1, "user_id": 2}

        name = "Test"
        username = "test"

        ctx.should_call_api(
            "get_guild_member",
            call_data,
            exception=ActionFailed(
                Response(
                    status_code=404,
                    content=b'{"message": "Unknown Guild", "code": 10003}',
                )
            ),
        )
        ctx.should_call_api(
            "get_user",
            {"user_id": call_data["user_id"]},
            get_guild_member_result(global_name=name, username=username).user,
        )
        assert await get_dc_member_name(dc_bot, **call_data) == (name, username)


@pytest.mark.asyncio
async def test_other_error(app: App) -> None:
    from nonebot_plugin_dcqq_relay.utils import get_dc_member_name

    async with app.test_api() as ctx:
        _, dc_bot = create_bot(ctx)

        call_data: dict[str, int] = {"guild_id": 1, "user_id": 2}

        ctx.should_call_api(
            "get_guild_member",
            call_data,
            exception=ActionFailed(Response(status_code=404)),
        )
        with pytest.RaisesExc(ActionFailed):
            await get_dc_member_name(dc_bot, **call_data)
