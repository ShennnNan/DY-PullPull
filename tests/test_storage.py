from dfa.models import VideoRef, VideoStatus
from dfa.storage import Library


def test_add_video_is_idempotent(tmp_path):
    library = Library(tmp_path / "library.db")
    ref = VideoRef("123", "https://www.douyin.com/video/123", "标题", "作者")

    first = library.add_video(ref)
    second = library.add_video(ref)

    assert first.video_id == "123"
    assert second.video_id == "123"
    assert library.count_videos() == 1


def test_stage_transition_and_failure_recovery(tmp_path):
    library = Library(tmp_path / "library.db")
    library.add_video(VideoRef("123", "https://www.douyin.com/video/123"))

    library.mark_status("123", VideoStatus.EXTRACTED)
    library.record_failure("123", "article", "ARTICLE_VALIDATION_FAILED", "缺少摘要")
    failed = library.get_video("123")
    assert failed.status is VideoStatus.FAILED
    assert failed.failed_stage == "article"

    library.mark_status("123", VideoStatus.WRITTEN)
    recovered = library.get_video("123")
    assert recovered.status is VideoStatus.WRITTEN
    assert recovered.failed_stage is None


def test_completed_video_has_article_path(tmp_path):
    library = Library(tmp_path / "library.db")
    library.add_video(VideoRef("123", "https://www.douyin.com/video/123"))

    library.complete_video("123", "articles/123-title.md")

    record = library.get_video("123")
    assert record.status is VideoStatus.COMPLETED
    assert record.article_path == "articles/123-title.md"
