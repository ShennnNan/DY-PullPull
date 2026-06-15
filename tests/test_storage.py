import pytest

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


def test_update_metadata_backfills_title_and_author(tmp_path):
    library = Library(tmp_path / "library.db")
    library.add_video(VideoRef("123", "https://www.douyin.com/video/123"))

    library.update_metadata("123", title="真实标题", author_name="真实作者")

    record = library.get_video("123")
    assert record.title == "真实标题"
    assert record.author_name == "真实作者"
    assert record.status is VideoStatus.DISCOVERED  # 不改状态


def test_update_metadata_preserves_existing_when_value_is_none(tmp_path):
    library = Library(tmp_path / "library.db")
    library.add_video(VideoRef("123", "https://www.douyin.com/video/123", "原标题", "原作者"))

    library.update_metadata("123", title=None, author_name="新作者")

    record = library.get_video("123")
    assert record.title == "原标题"
    assert record.author_name == "新作者"


def test_update_metadata_unknown_video_raises(tmp_path):
    library = Library(tmp_path / "library.db")
    with pytest.raises(KeyError):
        library.update_metadata("missing", title="x", author_name="y")
