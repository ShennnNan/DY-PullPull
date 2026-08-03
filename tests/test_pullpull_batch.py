import json
from pathlib import Path

from dfa.media import MediaResult
from pullpull.account import AccountVideo
from pullpull.article import ArticleMode, RefinedArticle
from pullpull.batch import (
    BatchResult,
    PrepareResult,
    RenameArticlesResult,
    RefinePreparedResult,
    finalize_account_video,
    prepare_account_videos,
    process_account_videos,
    rename_completed_articles,
    refine_prepared_account_videos,
)
from pullpull.pull import Collected


class FakeCollector:
    def __init__(self, transcripts):
        self.transcripts = transcripts
        self.calls = []

    def collect(self, url, *, cookies_from_browser=None):
        self.calls.append((url, cookies_from_browser))
        video_id = url.rsplit("/", 1)[-1]
        media = MediaResult(
            Path(f"{video_id}.mp4"), f"标题{video_id}", "作者", "20260618"
        )
        return Collected(
            video_id=video_id,
            media=media,
            transcript=self.transcripts[video_id],
        )


class FakeRefiner:
    def __init__(self):
        self.calls = []

    def refine(self, request):
        self.calls.append(request.video_id)
        return RefinedArticle(
            summary=f"核心观点 {request.video_id}",
            cleaned_transcript=f"顺畅原文 {request.raw_transcript}",
        )


def _videos():
    return [
        AccountVideo(
            "111", "https://www.douyin.com/video/111", "标题111", "作者", "20260618"
        ),
        AccountVideo(
            "222", "https://www.douyin.com/video/222", "标题222", "作者", "20260618"
        ),
    ]


def test_process_account_videos_writes_transcript_articles_and_index(tmp_path):
    collector = FakeCollector({"111": "原始一", "222": "原始二"})
    refiner = FakeRefiner()

    result = process_account_videos(
        _videos(),
        out_dir=tmp_path,
        mode=ArticleMode.TRANSCRIPT,
        collector=collector,
        refiner=refiner,
    )

    body = (tmp_path / "标题111.md").read_text(encoding="utf-8")
    assert result == BatchResult(total=2, completed=2, skipped=0, failed=0)
    assert body.count("## 原文") == 1
    assert "## 核心观点" not in body
    assert "顺畅原文 原始一" in body
    assert (tmp_path / "index.json").is_file()


def test_process_account_videos_writes_summary_articles(tmp_path):
    collector = FakeCollector({"111": "原始一", "222": "原始二"})
    refiner = FakeRefiner()

    process_account_videos(
        _videos(),
        out_dir=tmp_path,
        mode=ArticleMode.SUMMARY,
        collector=collector,
        refiner=refiner,
    )

    body = (tmp_path / "标题111.md").read_text(encoding="utf-8")
    assert "## 核心观点" in body
    assert "核心观点 111" in body
    assert "## 原文" in body


def test_process_account_videos_skips_completed_same_mode(tmp_path):
    collector = FakeCollector({"111": "原始一", "222": "原始二"})
    refiner = FakeRefiner()

    process_account_videos(
        _videos(),
        out_dir=tmp_path,
        mode=ArticleMode.TRANSCRIPT,
        collector=collector,
        refiner=refiner,
    )
    second = process_account_videos(
        _videos(),
        out_dir=tmp_path,
        mode=ArticleMode.TRANSCRIPT,
        collector=collector,
        refiner=refiner,
    )

    assert second == BatchResult(total=2, completed=0, skipped=2, failed=0)


def test_process_account_videos_records_failure_and_continues(tmp_path):
    class FailingCollector(FakeCollector):
        def collect(self, url, *, cookies_from_browser=None):
            if url.endswith("/111"):
                raise RuntimeError("download failed")
            return super().collect(url, cookies_from_browser=cookies_from_browser)

    result = process_account_videos(
        _videos(),
        out_dir=tmp_path,
        mode=ArticleMode.TRANSCRIPT,
        collector=FailingCollector({"222": "原始二"}),
        refiner=FakeRefiner(),
    )

    assert result == BatchResult(total=2, completed=1, skipped=0, failed=1)
    index_text = (tmp_path / "index.json").read_text(encoding="utf-8")
    assert "download failed" in index_text
    assert (tmp_path / "标题222.md").is_file()


def test_prepare_account_videos_writes_requests_and_resumes(tmp_path):
    collector = FakeCollector({"111": "原始一", "222": "原始二"})

    first = prepare_account_videos(
        _videos(),
        out_dir=tmp_path,
        mode=ArticleMode.SUMMARY,
        collector=collector,
        cookies_from_browser=r"edge:D:\auth",
    )
    second = prepare_account_videos(
        _videos(),
        out_dir=tmp_path,
        mode=ArticleMode.SUMMARY,
        collector=collector,
        cookies_from_browser=r"edge:D:\auth",
    )

    assert first == PrepareResult(total=2, prepared=2, skipped=0, failed=0)
    assert second == PrepareResult(total=2, prepared=0, skipped=2, failed=0)
    assert len(collector.calls) == 2
    assert collector.calls[0][1] == r"edge:D:\auth"
    assert (tmp_path / ".requests" / "111.summary.request.json").is_file()
    index = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
    assert index["videos"]["111"]["status"] == "prepared"


def test_finalize_account_video_writes_article_and_updates_index(tmp_path):
    prepare_account_videos(
        _videos()[:1],
        out_dir=tmp_path,
        mode=ArticleMode.SUMMARY,
        collector=FakeCollector({"111": "原始一"}),
    )
    request_path = tmp_path / ".requests" / "111.summary.request.json"
    response_path = tmp_path / ".requests" / "111.summary.response.json"
    response_path.write_text(
        json.dumps(
            {
                "core_viewpoints": "核心观点",
                "cleaned_transcript": "清洗后的原文",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    article_path = finalize_account_video(
        out_dir=tmp_path,
        request_path=request_path,
        response_path=response_path,
        mode=ArticleMode.SUMMARY,
    )

    assert article_path == tmp_path / "标题111.md"
    assert "## 核心观点" in article_path.read_text(encoding="utf-8")
    index = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
    assert index["videos"]["111"]["status"] == "completed"


def test_refine_prepared_account_videos_writes_responses_and_articles(tmp_path):
    prepare_account_videos(
        _videos(),
        out_dir=tmp_path,
        mode=ArticleMode.SUMMARY,
        collector=FakeCollector({"111": "原始一", "222": "原始二"}),
    )

    result = refine_prepared_account_videos(
        out_dir=tmp_path,
        mode=ArticleMode.SUMMARY,
        refiner=FakeRefiner(),
    )

    assert result == RefinePreparedResult(total=2, completed=2, failed=0)
    assert (tmp_path / ".requests" / "111.summary.response.json").is_file()
    assert (tmp_path / "标题111.md").is_file()
    index = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
    assert index["videos"]["111"]["status"] == "completed"


def test_refine_failure_does_not_revert_an_earlier_completion(tmp_path):
    prepare_account_videos(
        _videos(),
        out_dir=tmp_path,
        mode=ArticleMode.SUMMARY,
        collector=FakeCollector({"111": "原始一", "222": "原始二"}),
    )

    class SecondFailsRefiner(FakeRefiner):
        def refine(self, request):
            if request.video_id == "222":
                raise RuntimeError("AI unavailable")
            return super().refine(request)

    result = refine_prepared_account_videos(
        out_dir=tmp_path,
        mode=ArticleMode.SUMMARY,
        refiner=SecondFailsRefiner(),
    )

    assert result == RefinePreparedResult(total=2, completed=1, failed=1)
    index = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
    assert index["videos"]["111"]["status"] == "completed"
    assert index["videos"]["222"]["status"] == "failed"


def test_rename_completed_articles_migrates_id_filename_and_index(tmp_path):
    request_path = tmp_path / ".requests" / "111.summary.request.json"
    request_path.parent.mkdir(parents=True)
    request_path.write_text(
        json.dumps(
            {
                "video_id": "111",
                "title": "申请博士：RP/PS怎么写？",
                "source_url": "https://www.douyin.com/video/111",
                "author": "作者",
                "published_at": "20260727",
                "raw_transcript": "原文",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    old_path = tmp_path / "111.md"
    old_path.write_text("video_id: 111\n", encoding="utf-8")
    (tmp_path / "index.json").write_text(
        json.dumps(
            {
                "videos": {
                    "111": {
                        "status": "completed",
                        "mode": "summary",
                        "request_path": str(request_path),
                        "article_path": str(old_path),
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    result = rename_completed_articles(tmp_path)

    expected = tmp_path / "申请博士：RP／PS怎么写？.md"
    assert result == RenameArticlesResult(total=1, renamed=1, skipped=0, failed=0)
    assert expected.is_file()
    assert not old_path.exists()
    index = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
    assert index["videos"]["111"]["article_path"] == str(expected)
