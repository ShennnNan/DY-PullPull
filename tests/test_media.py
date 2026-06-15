import json
import os
from pathlib import Path

import pytest

from dfa.media import MediaError, MediaResult, build_options, download_media
from dfa.models import VideoRef


class FakeRunner:
    """模拟 yt-dlp：把要写的文件和要抛的异常预置好。"""

    def __init__(self, *, writes=None, error=None):
        self.writes = writes or {}
        self.error = error
        self.calls = []

    def run(self, url, options):
        self.calls.append((url, options))
        if self.error is not None:
            raise self.error
        home = Path(options["paths"]["home"])
        for name, content in self.writes.items():
            (home / name).write_text(content, encoding="utf-8")


REF = VideoRef("7", "https://www.douyin.com/video/7", None, None)


def _info_json(title="标题", uploader="作者", upload_date="20260605"):
    return json.dumps(
        {"title": title, "uploader": uploader, "upload_date": upload_date},
        ensure_ascii=False,
    )


def test_build_options_requests_infojson_and_output_template(tmp_path):
    options = build_options(tmp_path, "7", None)
    assert options["writeinfojson"] is True
    assert "%(id)s" in options["outtmpl"]
    assert options["paths"]["home"] == str(tmp_path)
    assert "cookiesfrombrowser" not in options


def test_build_options_adds_cookies_from_browser(tmp_path):
    options = build_options(tmp_path, "7", "chrome")
    assert options["cookiesfrombrowser"] == ("chrome",)


def test_download_returns_media_path_and_metadata(tmp_path):
    runner = FakeRunner(writes={"7.mp4": "binary", "7.info.json": _info_json()})

    result = download_media(REF, tmp_path, runner=runner)

    assert isinstance(result, MediaResult)
    assert result.media_path.name == "7.mp4"
    assert result.title == "标题"
    assert result.author_name == "作者"
    assert result.published_at == "20260605"
    assert runner.calls[0][0] == REF.source_url


def test_download_maps_unavailable_to_source_unavailable(tmp_path):
    runner = FakeRunner(error=RuntimeError("Video is unavailable or has been deleted"))

    with pytest.raises(MediaError) as excinfo:
        download_media(REF, tmp_path, runner=runner)

    assert excinfo.value.code == "SOURCE_UNAVAILABLE"


def test_download_maps_private_to_source_unavailable(tmp_path):
    runner = FakeRunner(error=RuntimeError("This video is private"))

    with pytest.raises(MediaError) as excinfo:
        download_media(REF, tmp_path, runner=runner)

    assert excinfo.value.code == "SOURCE_UNAVAILABLE"


def test_download_maps_generic_error_to_media_prepare_failed(tmp_path):
    runner = FakeRunner(error=RuntimeError("connection reset"))

    with pytest.raises(MediaError) as excinfo:
        download_media(REF, tmp_path, runner=runner)

    assert excinfo.value.code == "MEDIA_PREPARE_FAILED"


def test_download_without_media_file_raises_prepare_failed(tmp_path):
    # 只写了 info.json，没有媒体文件 → 视为准备失败
    runner = FakeRunner(writes={"7.info.json": _info_json()})

    with pytest.raises(MediaError) as excinfo:
        download_media(REF, tmp_path, runner=runner)

    assert excinfo.value.code == "MEDIA_PREPARE_FAILED"


@pytest.mark.skipif(
    not os.environ.get("DFA_RUN_INTEGRATION"),
    reason="设置 DFA_RUN_INTEGRATION=1 才跑真实 yt-dlp 下载",
)
def test_real_download_public_video(tmp_path):
    from dfa.media import YtDlpRunner

    url = os.environ.get(
        "DFA_TEST_URL", "https://www.douyin.com/video/7647748711631703311"
    )
    result = download_media(
        VideoRef("itest", url), tmp_path, runner=YtDlpRunner()
    )
    assert result.media_path.exists()
    assert result.media_path.stat().st_size > 0
