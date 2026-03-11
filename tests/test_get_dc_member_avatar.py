from tests.conftest import create_bot
from tests.data import guild_member

from nonebug import App
import pytest


@pytest.mark.asyncio
async def test_member_avatar_exist(app: App) -> None:
    from nonebot_plugin_dcqq_relay.utils import get_dc_member_avatar

    async with app.test_api() as ctx:
        _, dc_bot = create_bot(ctx)

        guild_id = 1
        user_id = 2
        call_data: dict[str, int] = {"guild_id": guild_id, "user_id": user_id}
        prefix_url = (
            f"https://cdn.discordapp.com/guilds/{guild_id}/users/{user_id}/avatars"
        )

        avatar = "x"
        ctx.should_call_api(
            api="get_guild_member",
            data=call_data,
            result=guild_member(member_avatar=avatar),
        )
        assert (
            await get_dc_member_avatar(dc_bot, **call_data)
            == f"{prefix_url}/{avatar}.webp"
        )

        avatar = "a_xx"
        ctx.should_call_api(
            api="get_guild_member",
            data=call_data,
            result=guild_member(member_avatar=avatar),
        )
        assert (
            await get_dc_member_avatar(dc_bot, **call_data)
            == f"{prefix_url}/{avatar}.gif"
        )


@pytest.mark.asyncio
async def test_uesr_avatar_exist(app: App) -> None:
    from nonebot_plugin_dcqq_relay.utils import get_dc_member_avatar

    async with app.test_api() as ctx:
        _, dc_bot = create_bot(ctx)

        guild_id = 1
        user_id = 2
        call_data: dict[str, int] = {"guild_id": guild_id, "user_id": user_id}
        prefix_url = f"https://cdn.discordapp.com/avatars/{user_id}"

        avatar = "x"
        ctx.should_call_api(
            api="get_guild_member",
            data=call_data,
            result=guild_member(user_avatar=avatar),
        )
        assert (
            await get_dc_member_avatar(dc_bot, **call_data)
            == f"{prefix_url}/{avatar}.webp"
        )

        avatar = "a_xx"
        ctx.should_call_api(
            api="get_guild_member",
            data=call_data,
            result=guild_member(user_avatar=avatar),
        )
        assert (
            await get_dc_member_avatar(dc_bot, **call_data)
            == f"{prefix_url}/{avatar}.gif"
        )


@pytest.mark.asyncio
async def test_all_avatar_not_exist(app: App) -> None:
    from nonebot_plugin_dcqq_relay.utils import get_dc_member_avatar

    async with app.test_api() as ctx:
        _, dc_bot = create_bot(ctx)

        call_data: dict[str, int] = {"guild_id": 1, "user_id": 2}

        ctx.should_call_api(
            api="get_guild_member",
            data=call_data,
            result=guild_member(),
        )
        assert await get_dc_member_avatar(dc_bot, **call_data) == ""
