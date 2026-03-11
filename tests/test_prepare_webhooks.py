from unittest.mock import patch

from tests.conftest import create_bot
from tests.data import webhook, webhooks_list

from nonebug import App
import pytest


@pytest.mark.asyncio
async def test_link_with_webhook(app: App) -> None:
    async with app.test_api() as ctx:
        from nonebot_plugin_dcqq_relay.config import LinkWithoutWebhook, LinkWithWebhook

        _, dc_bot = create_bot(ctx)
        channel_ids: list[int] = [1, 2, 3, 4, 5]
        ids: list[str] = ["1", "2", "3", "4"]
        tokens: list[str | None] = ["xx", "xxx", None, "xxxx"]
        application_ids: list[str | None] = ["12345", "54321", "23145", None]
        channel_links: list[LinkWithoutWebhook] = [
            LinkWithoutWebhook(
                dc_guild_id=1,
                dc_channel_id=channel_ids[0],
                qq_group_id=10001,
                webhook_id=1,
                webhook_token="x",
            ),
            LinkWithoutWebhook(
                dc_guild_id=1,
                dc_channel_id=channel_ids[1],
                qq_group_id=10002,
            ),
            LinkWithoutWebhook(
                dc_guild_id=1,
                dc_channel_id=channel_ids[2],
                qq_group_id=10003,
            ),
            LinkWithoutWebhook(
                dc_guild_id=1,
                dc_channel_id=channel_ids[3],
                qq_group_id=10003,
            ),
        ]
        with patch("nonebot_plugin_dcqq_relay.utils.channel_links", channel_links):
            from nonebot_plugin_dcqq_relay import prepare_webhooks
            import nonebot_plugin_dcqq_relay.utils as utils

            ctx.should_call_api(
                "get_channel_webhooks",
                {"channel_id": channel_ids[1]},
                webhooks_list(ids, tokens, application_ids),
            )
            ctx.should_call_api(
                "get_channel_webhooks",
                {"channel_id": channel_ids[2]},
                webhooks_list(ids[1:], tokens[1:], application_ids[1:]),
            )
            ctx.should_call_api(
                "create_webhook",
                {"channel_id": channel_ids[2], "name": str(channel_ids[2])},
                webhook(ids[0], tokens[0], application_ids[0]),
            )
            ctx.should_call_api(
                "get_channel_webhooks",
                {"channel_id": channel_ids[3]},
                exception=Exception(),
            )
            ctx.should_call_api(
                "create_webhook",
                {"channel_id": channel_ids[3], "name": str(channel_ids[3])},
                exception=Exception(),
            )
            await prepare_webhooks(dc_bot)

            assert utils.with_webhook_links == [
                LinkWithWebhook(**channel_links[0].model_dump()),
                LinkWithWebhook(
                    **channel_links[1].model_dump(exclude_none=True),
                    webhook_id=int(ids[0]),
                    webhook_token=str(tokens[0]),
                ),
                LinkWithWebhook(
                    **channel_links[2].model_dump(exclude_none=True),
                    webhook_id=int(ids[0]),
                    webhook_token=str(tokens[0]),
                ),
            ]
