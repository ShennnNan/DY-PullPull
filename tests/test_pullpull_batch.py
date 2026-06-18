from pathlib import Path

from dfa.media import MediaResult
from pullpull.account import AccountVideo
from pullpull.article import ArticleMode, RefinedArticle
from pullpull.batch import BatchResult, process_account_videos
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

    body = (tmp_path / "111.md").read_text(encoding="utf-8")
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

    body = (tmp_path / "111.md").read_text(encoding="utf-8")
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
    assert (tmp_path / "222.md").is_file()
