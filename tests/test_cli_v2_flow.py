import json

import pytest

from dfa import cli
from dfa.extractor import ExtractionError, ExtractionResult
from dfa.media import MediaError, MediaResult
from dfa.models import VideoStatus
from dfa.storage import Library

URL = "https://www.douyin.com/jingxuan?modal_id=7647748711631703311"
VIDEO_ID = "7647748711631703311"


@pytest.fixture
def fake_pipeline(monkeypatch):
    """把真实下载/转写替换成写文件的假实现，并强制 CPU。"""

    def fake_download(video, workspace, *, runner, cookies_from_browser=None):
        (workspace / "v.mp4").write_text("fake-bytes", encoding="utf-8")
        return MediaResult(
            media_path=workspace / "v.mp4",
            title="真实标题",
            author_name="真实作者",
            published_at="20260605",
        )

    def fake_transcribe(media_path, config, **kwargs):
        return ExtractionResult(
            transcript="第一句\n第二句\n",
            device="cpu",
            model="small",
            duration=12.0,
        )

    monkeypatch.setattr(cli, "download_media", fake_download)
    monkeypatch.setattr(cli.extractor, "transcribe", fake_transcribe)
    monkeypatch.setattr(cli, "_detect_cuda", lambda: False)


def test_pull_runs_full_pipeline_to_article_request(tmp_path, capsys, fake_pipeline):
    data_root = tmp_path / "data"

    assert cli.main(["--data-root", str(data_root), "pull", URL]) == 0

    record = Library(data_root / "library.db").get_video(VIDEO_ID)
    assert record.status is VideoStatus.EXTRACTED
    assert record.title == "真实标题"
    assert record.author_name == "真实作者"

    request_path = data_root / "temp" / VIDEO_ID / "article-request.json"
    request = json.loads(request_path.read_text(encoding="utf-8"))
    assert request["transcript"] == "第一句\n第二句\n"
    assert request["video"]["published_at"] == "20260605"
    assert request["video"]["source_url"] == f"https://www.douyin.com/video/{VIDEO_ID}"
    assert (data_root / "temp" / VIDEO_ID / "transcript.txt").is_file()


def test_staged_fetch_then_transcribe(tmp_path, fake_pipeline):
    data_root = tmp_path / "data"
    cli.main(["--data-root", str(data_root), "add-url", URL])

    assert cli.main(["--data-root", str(data_root), "fetch", VIDEO_ID]) == 0
    mid = Library(data_root / "library.db").get_video(VIDEO_ID)
    assert mid.status is VideoStatus.MEDIA_PREPARED
    assert (data_root / "temp" / VIDEO_ID / "media.json").is_file()

    assert cli.main(["--data-root", str(data_root), "transcribe", VIDEO_ID]) == 0
    done = Library(data_root / "library.db").get_video(VIDEO_ID)
    assert done.status is VideoStatus.EXTRACTED


def test_fetch_failure_records_failure_and_returns_2(tmp_path, monkeypatch):
    data_root = tmp_path / "data"

    def boom(video, workspace, *, runner, cookies_from_browser=None):
        raise MediaError("SOURCE_UNAVAILABLE", "视频不可访问")

    monkeypatch.setattr(cli, "download_media", boom)

    cli.main(["--data-root", str(data_root), "add-url", URL])
    result = cli.main(["--data-root", str(data_root), "fetch", VIDEO_ID])

    record = Library(data_root / "library.db").get_video(VIDEO_ID)
    assert result == 2
    assert record.status is VideoStatus.FAILED
    assert record.failed_stage == "media"


def test_transcribe_without_fetch_returns_2(tmp_path):
    data_root = tmp_path / "data"
    cli.main(["--data-root", str(data_root), "add-url", URL])

    result = cli.main(["--data-root", str(data_root), "transcribe", VIDEO_ID])
    assert result == 2


def test_transcribe_failure_records_failure(tmp_path, monkeypatch, fake_pipeline):
    data_root = tmp_path / "data"
    cli.main(["--data-root", str(data_root), "add-url", URL])
    cli.main(["--data-root", str(data_root), "fetch", VIDEO_ID])

    def boom(media_path, config, **kwargs):
        raise ExtractionError("TRANSCRIPTION_FAILED", "转写失败")

    monkeypatch.setattr(cli.extractor, "transcribe", boom)
    result = cli.main(["--data-root", str(data_root), "transcribe", VIDEO_ID])

    record = Library(data_root / "library.db").get_video(VIDEO_ID)
    assert result == 2
    assert record.status is VideoStatus.FAILED
    assert record.failed_stage == "transcription"
