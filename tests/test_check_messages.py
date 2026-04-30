from unittest.mock import patch

from tests.data import (
    get_test_links,
    group_message_event,
    group_recall_event,
    guild_message_create_event,
    guild_message_delete_event,
)

from nonebug import App


@patch("nonebot_plugin_dcqq_relay.utils.channel_links", new_callable=get_test_links)
def test_group_message_matched(app: App) -> None:
    from nonebot_plugin_dcqq_relay.utils import check_messages

    event = group_message_event(group_id=10001)
    assert check_messages(event) is True


@patch("nonebot_plugin_dcqq_relay.utils.channel_links", new_callable=get_test_links)
def test_group_message_group_id_not_in_links(app: App) -> None:
    from nonebot_plugin_dcqq_relay.utils import check_messages

    event = group_message_event(group_id=99999)
    assert check_messages(event) is False


@patch("nonebot_plugin_dcqq_relay.utils.channel_links", new_callable=get_test_links)
def test_group_recall_matched(app: App) -> None:
    from nonebot_plugin_dcqq_relay.utils import check_messages

    event = group_recall_event()
    assert check_messages(event) is True


@patch(
    "nonebot_plugin_dcqq_relay.utils.with_webhook_links", new_callable=get_test_links
)
def test_guild_create_matched(app: App) -> None:
    from nonebot_plugin_dcqq_relay.utils import check_messages

    event = guild_message_create_event(webhook_id="2")
    assert check_messages(event) is True


@patch(
    "nonebot_plugin_dcqq_relay.utils.with_webhook_links", new_callable=get_test_links
)
def test_guild_create_same_webhook_id(app: App) -> None:
    from nonebot_plugin_dcqq_relay.utils import check_messages

    event = guild_message_create_event(webhook_id="1")
    assert check_messages(event) is False


@patch(
    "nonebot_plugin_dcqq_relay.utils.with_webhook_links", new_callable=get_test_links
)
def test_guild_create_guild_id_not_in_links(app: App) -> None:
    from nonebot_plugin_dcqq_relay.utils import check_messages

    event = guild_message_create_event(guild_id="1")
    assert check_messages(event) is False


@patch(
    "nonebot_plugin_dcqq_relay.utils.with_webhook_links", new_callable=get_test_links
)
def test_guild_create_channel_id_not_in_links(app: App) -> None:
    from nonebot_plugin_dcqq_relay.utils import check_messages

    event = guild_message_create_event(channel_id="1")
    assert check_messages(event) is False


@patch("nonebot_plugin_dcqq_relay.utils.channel_links", new_callable=get_test_links)
def test_guild_delete_matched(app: App) -> None:
    from nonebot_plugin_dcqq_relay.utils import check_messages

    event = guild_message_delete_event()
    assert check_messages(event) is True


@patch("nonebot_plugin_dcqq_relay.utils.channel_links", new_callable=get_test_links)
def test_guild_delete_guild_id_not_in_links(app: App) -> None:
    from nonebot_plugin_dcqq_relay.utils import check_messages

    event = guild_message_delete_event(guild_id="9" * 18)
    assert check_messages(event) is False


@patch("nonebot_plugin_dcqq_relay.utils.channel_links", new_callable=get_test_links)
def test_guild_delete_channel_id_not_in_links(app: App) -> None:
    from nonebot_plugin_dcqq_relay.utils import check_messages

    event = guild_message_delete_event(channel_id="9" * 18)
    assert check_messages(event) is False
