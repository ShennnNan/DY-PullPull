import json
import os
from pathlib import Path

import pytest

from dfa.media import MediaResult
from pullpull.pull import PullResult, pull, render_markdown


class FakeRunner:
    """模拟 yt-dlp：把要写入工作目录的文件预置好。"""

    def __init__(self, *, writes):
        self.writes = writes
        self.calls = []

    def run(self, url, options):
        self.calls.append((url, options))
        home = Path(options["paths"]["home"])
        for name, content in self.writes.items():
            (home / name).write_text(content, encoding="utf-8")


class FakeTranscriber:
    def __init__(self, text):
        self.text = text
        self.seen = []

    def transcribe(self, media_path):
        self.seen.append(Path(media_path))
        return self.text


def _info_json(title="标题", uploader="作者", upload_date="20260616"):
    return json.dumps(
        {"title": title, "uploader": uploader, "upload_date": upload_date},
        ensure_ascii=False,
    )


URL = "https://www.douyin.com/video/123"


def test_render_markdown_has_frontmatter_and_transcript():
    media = MediaResult(Path("123.mp4"), "标题", "作者", "20260616")
    md = render_markdown(
        video_id="123", source_url=URL, media=media, transcript="一段文字"
    )
    assert "video_id: 123" in md
    assert f"source_url: {URL}" in md
    assert "engine: funasr-paraformer-zh" in md
    assert "# 标题" in md
    assert "## 原文" in md
    assert "一段文字" in md


def test_pull_downloads_transcribes_and_writes_markdown(tmp_path):
    runner = FakeRunner(writes={"123.mp4": "fakebytes", "123.info.json": _info_json()})
    transcriber = FakeTranscriber("这是转写结果")
    out_dir = tmp_path / "articles"

    result = pull(URL, out_dir, runner=runner, transcriber=transcriber)

    assert isinstance(result, PullResult)
    assert result.video_id == "123"
    assert result.title == "标题"
    md_path = out_dir / "标题.md"
    assert md_path.exists()
    body = md_path.read_text(encoding="utf-8")
    assert "这是转写结果" in body
    assert f"source_url: {URL}" in body
    # 转写器拿到的是下载出来的真实媒体文件
    assert transcriber.seen and transcriber.seen[0].name == "123.mp4"


def test_pull_cleans_up_temporary_media(tmp_path):
    captured = {}

    class CapturingTranscriber:
        def transcribe(self, media_path):
            path = Path(media_path)
            captured["media_path"] = path
            assert path.exists()  # 转写时临时媒体仍在
            return "x"

    runner = FakeRunner(writes={"123.mp4": "fakebytes", "123.info.json": _info_json()})
    pull(URL, tmp_path / "articles", runner=runner, transcriber=CapturingTranscriber())

    # 返回后临时工作目录及媒体被清除，本地只保留 Markdown
    assert not captured["media_path"].exists()
    assert not captured["media_path"].parent.exists()


@pytest.mark.skipif(
    not os.environ.get("PULLPULL_RUN_INTEGRATION"),
    reason="设置 PULLPULL_RUN_INTEGRATION=1 才跑真实下载+转写",
)
def test_real_pull(tmp_path):
    url = os.environ.get(
        "PULLPULL_TEST_URL", "https://www.douyin.com/video/7647748711631703311"
    )
    result = pull(url, tmp_path / "articles")
    assert result.markdown_path.exists()
    assert result.transcript
