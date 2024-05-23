from typing import Optional

from nonebot import get_plugin_config
from pydantic import BaseModel


class Link(BaseModel):
    dc_guild_id: int
    dc_channel_id: int
    qq_group_id: int


class LinkWithWebhook(Link):
    webhook_id: int
    webhook_token: str


class Config(BaseModel):
    dcqq_relay_channel_links: list[Link] = []
    """子频道绑定"""
    dcqq_relay_unmatch_beginning: list[str] = ["/"]
    """不转发的消息开头"""
    discord_proxy: Optional[str] = None


plugin_config = get_plugin_config(Config)
