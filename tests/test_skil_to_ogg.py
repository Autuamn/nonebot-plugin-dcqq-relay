from base64 import b64decode

from tests.data import amr_b64, skil_b64

from nonebug import App


def test_silk_input(app: App) -> None:
    from nonebot_plugin_dcqq_relay.utils import skil_to_ogg

    ogg_bytes = skil_to_ogg(b64decode(skil_b64))
    assert isinstance(ogg_bytes, bytes)
    assert len(ogg_bytes) > 0
    assert ogg_bytes[:4] == b"OggS"


def test_amr_input(app: App) -> None:
    from nonebot_plugin_dcqq_relay.utils import skil_to_ogg

    ogg_bytes = skil_to_ogg(b64decode(amr_b64))
    assert isinstance(ogg_bytes, bytes)
    assert len(ogg_bytes) > 0
    assert ogg_bytes[:4] == b"OggS"
