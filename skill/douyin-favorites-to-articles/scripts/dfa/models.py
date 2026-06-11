from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class VideoStatus(StrEnum):
    DISCOVERED = "discovered"
    MEDIA_PREPARED = "media_prepared"
    EXTRACTED = "extracted"
    WRITTEN = "written"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class VideoRef:
    video_id: str
    source_url: str
    title: str | None = None
    author_name: str | None = None


@dataclass(frozen=True)
class VideoRecord:
    video_id: str
    source_url: str
    title: str | None
    author_name: str | None
    status: VideoStatus
    failed_stage: str | None
    article_path: str | None
