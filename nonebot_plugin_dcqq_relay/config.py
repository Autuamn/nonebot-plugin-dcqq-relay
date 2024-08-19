from typing import Optional

from nonebot import get_plugin_config
from pydantic import BaseModel


class Link(BaseModel):
    dc_guild_id: int
    dc_channel_id: int
    qq_group_id: int


class LinkWithoutWebhook(Link):
    webhook_id: Optional[int] = None
    webhook_token: Optional[str] = None


class LinkWithWebhook(Link):
    webhook_id: int
    webhook_token: str


class Config(BaseModel):
    dcqq_relay_channel_links: list[LinkWithoutWebhook] = []
    """QQ群绑定"""
    dcqq_relay_unmatch_beginning: list[str] = ["/"]
    """不转发的消息开头"""
    dcqq_relay_only_to_me: bool = False
    discord_proxy: Optional[str] = None


plugin_config = get_plugin_config(Config)
