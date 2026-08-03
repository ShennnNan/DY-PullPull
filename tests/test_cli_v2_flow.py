import hashlib
import json
from pathlib import Path

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


def test_pullpull_account_command_enumerates_and_processes(
    monkeypatch, tmp_path, capsys
):
    from pullpull.article import ArticleMode
    from pullpull.batch import BatchResult
    import pullpull.cli as cli_module

    calls = {}

    def fake_enumerate(account_url, *, cookies_from_browser=None):
        calls["account_url"] = account_url
        calls["cookies"] = cookies_from_browser
        return ["video-a", "video-b"]

    class FakeRefiner:
        def refine(self, request):
            raise AssertionError("batch fake should receive refiner but not call it")

    def fake_process(
        videos,
        *,
        out_dir,
        mode,
        refiner,
        collector=None,
        cookies_from_browser=None,
    ):
        calls["videos"] = videos
        calls["out_dir"] = out_dir
        calls["mode"] = mode
        calls["batch_cookies"] = cookies_from_browser
        calls["refiner_type"] = type(refiner).__name__
        return BatchResult(total=2, completed=2, skipped=0, failed=0)

    monkeypatch.setattr(cli_module, "enumerate_account", fake_enumerate)
    monkeypatch.setattr(cli_module, "AgentRefiner", FakeRefiner)
    monkeypatch.setattr(cli_module, "process_account_videos", fake_process)

    result = cli_module.main(
        [
            "account",
            "https://www.douyin.com/user/MS4wLjAB",
            "--mode",
            "summary",
            "--out",
            str(tmp_path),
            "--cookies-from-browser",
            "chrome",
        ]
    )

    assert result == 0
    assert calls["mode"] is ArticleMode.SUMMARY
    assert calls["cookies"] == "chrome"
    assert calls["batch_cookies"] == "chrome"
    assert calls["videos"] == ["video-a", "video-b"]
    assert calls["out_dir"] == tmp_path
    output = capsys.readouterr().out
    assert "total: 2" in output
    assert "completed: 2" in output


def test_pullpull_account_command_uses_author_default_output(monkeypatch, capsys):
    from pullpull.account import AccountVideo
    from pullpull.batch import BatchResult
    import pullpull.cli as cli_module

    calls = {}

    def fake_enumerate(account_url, *, cookies_from_browser=None):
        return [
            AccountVideo(
                video_id="111",
                source_url="https://www.douyin.com/video/111",
                author="李海涛（直男）",
            )
        ]

    def fake_process(
        videos,
        *,
        out_dir,
        mode,
        refiner,
        collector=None,
        cookies_from_browser=None,
    ):
        calls["out_dir"] = out_dir
        return BatchResult(total=1, completed=1, skipped=0, failed=0)

    monkeypatch.setattr(cli_module, "enumerate_account", fake_enumerate)
    monkeypatch.setattr(cli_module, "process_account_videos", fake_process)

    result = cli_module.main(["account", "https://www.douyin.com/user/MS4wLjAB"])

    assert result == 0
    assert calls["out_dir"] == Path(
        r"D:\AI Skill\content-workspace\samples\李海涛（直男）"
    )
    output = capsys.readouterr().out
    assert "out:" in output


def test_pullpull_account_command_uses_url_hash_when_author_missing(
    monkeypatch, capsys
):
    from pullpull.batch import BatchResult
    import pullpull.cli as cli_module

    account_url = "https://www.douyin.com/user/no-author"
    calls = {}

    def fake_enumerate(account_url, *, cookies_from_browser=None):
        return []

    def fake_process(
        videos,
        *,
        out_dir,
        mode,
        refiner,
        collector=None,
        cookies_from_browser=None,
    ):
        calls["out_dir"] = out_dir
        return BatchResult(total=0, completed=0, skipped=0, failed=0)

    monkeypatch.setattr(cli_module, "enumerate_account", fake_enumerate)
    monkeypatch.setattr(cli_module, "process_account_videos", fake_process)

    result = cli_module.main(["account", account_url])

    digest = hashlib.sha256(account_url.encode("utf-8")).hexdigest()[:12]
    assert result == 0
    assert calls["out_dir"] == Path(
        rf"D:\AI Skill\content-workspace\samples\account-{digest}"
    )
    output = capsys.readouterr().out
    assert "out:" in output


def test_pullpull_finalize_supports_transcript_mode(tmp_path):
    import pullpull.cli as cli_module

    request_path = tmp_path / "123.request.json"
    response_path = tmp_path / "123.response.json"
    out_dir = tmp_path / "articles"
    request_path.write_text(
        json.dumps(
            {
                "video_id": "123",
                "title": "Test title",
                "source_url": "https://www.douyin.com/video/123",
                "author": "Tester",
                "published_at": "20260618",
                "raw_transcript": "raw text",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    response_path.write_text(
        json.dumps({"cleaned_transcript": "cleaned text"}, ensure_ascii=False),
        encoding="utf-8",
    )

    result = cli_module.main(
        [
            "finalize",
            str(request_path),
            str(response_path),
            "--mode",
            "transcript",
            "--out",
            str(out_dir),
        ]
    )

    article = (out_dir / "Test title.md").read_text(encoding="utf-8")
    assert result == 0
    assert "mode: transcript" in article
    assert "## 原文" in article
    assert "cleaned text" in article
    assert "## 核心观点" not in article
