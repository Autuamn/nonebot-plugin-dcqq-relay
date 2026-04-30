from tests.data import amr_bytes, skil_bytes

from nonebug import App


def test_silk_input(app: App) -> None:
    from nonebot_plugin_dcqq_relay.utils import skil_to_ogg

    ogg_bytes = skil_to_ogg(skil_bytes)
    assert isinstance(ogg_bytes, bytes)
    assert len(ogg_bytes) > 0
    assert ogg_bytes[:4] == b"OggS"


def test_amr_input(app: App) -> None:
    from nonebot_plugin_dcqq_relay.utils import skil_to_ogg

    ogg_bytes = skil_to_ogg(amr_bytes)
    assert isinstance(ogg_bytes, bytes)
    assert len(ogg_bytes) > 0
    assert ogg_bytes[:4] == b"OggS"
