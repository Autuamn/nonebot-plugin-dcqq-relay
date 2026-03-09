from io import BytesIO

from nonebug import App
from pydub import AudioSegment


def test_wav_to_mp3(app: App) -> None:
    from nonebot_plugin_dcqq_relay.utils import pydub_transform

    silent = AudioSegment.silent(duration=100)
    buf = BytesIO()
    silent.export(buf, format="wav")
    wav_bytes = buf.getvalue()
    out = pydub_transform(wav_bytes, "wav", "mp3")
    assert isinstance(out, bytes)
    assert len(out) > 0
    assert out[:3] == b"ID3" or len(out) > 100


def test_identity_wav(app: App) -> None:
    from nonebot_plugin_dcqq_relay.utils import pydub_transform

    silent = AudioSegment.silent(duration=50)
    buf = BytesIO()
    silent.export(buf, format="wav")
    wav_bytes = buf.getvalue()
    out = pydub_transform(wav_bytes, "wav", "wav")
    assert isinstance(out, bytes)
    assert len(out) > 0
