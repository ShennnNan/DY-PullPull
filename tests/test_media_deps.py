"""v0.2 媒体依赖可用性检查。装好 media 组依赖后应全部可导入。"""


def test_yt_dlp_importable():
    import yt_dlp  # noqa: F401


def test_faster_whisper_importable():
    from faster_whisper import WhisperModel  # noqa: F401
