from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol

from pullpull.account import AccountVideo
from pullpull.article import (
    ArticleMode,
    RefineRequest,
    Refiner,
    finalize,
    request_from_collected,
    write_request,
)
from pullpull.pull import Collected, collect


@dataclass(frozen=True)
class BatchResult:
    total: int
    completed: int
    skipped: int
    failed: int


class Collector(Protocol):
    def collect(
        self, url: str, *, cookies_from_browser: str | None = None
    ) -> Collected: ...


class DefaultCollector:
    def collect(
        self, url: str, *, cookies_from_browser: str | None = None
    ) -> Collected:
        return collect(url, cookies_from_browser=cookies_from_browser)


def _index_path(out_dir: Path) -> Path:
    return out_dir / "index.json"


def _load_index(out_dir: Path) -> dict:
    path = _index_path(out_dir)
    if not path.is_file():
        return {"videos": {}}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _save_index(out_dir: Path, index: dict) -> None:
    _index_path(out_dir).write_text(
        json.dumps(index, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _request_from_video(video: AccountVideo, collected: Collected) -> RefineRequest:
    request = request_from_collected(collected, video.source_url)
    return RefineRequest(
        video_id=request.video_id,
        title=video.title or request.title,
        source_url=video.source_url,
        author=video.author or request.author,
        published_at=video.published_at or request.published_at,
        raw_transcript=request.raw_transcript,
        instructions=request.instructions,
    )


def _is_completed(record: dict | None, mode: ArticleMode) -> bool:
    return bool(
        record
        and record.get("status") == "completed"
        and record.get("mode") == mode.value
    )


def process_account_videos(
    videos: list[AccountVideo],
    *,
    out_dir: Path | str,
    mode: ArticleMode,
    refiner: Refiner,
    collector: Collector | None = None,
    cookies_from_browser: str | None = None,
) -> BatchResult:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    requests_dir = out_dir / ".requests"
    requests_dir.mkdir(parents=True, exist_ok=True)
    collector = collector or DefaultCollector()
    index = _load_index(out_dir)
    records = index.setdefault("videos", {})

    completed = 0
    skipped = 0
    failed = 0

    for video in videos:
        existing = records.get(video.video_id)
        if _is_completed(existing, mode):
            skipped += 1
            continue

        try:
            collected = collector.collect(
                video.source_url,
                cookies_from_browser=cookies_from_browser,
            )
            request = _request_from_video(video, collected)
            write_request(
                requests_dir / f"{request.video_id}.{mode.value}.request.json",
                request,
            )
            refined = refiner.refine(request)
            article_path = finalize(out_dir, request, refined, mode=mode)
        except Exception as error:  # noqa: BLE001
            failed += 1
            records[video.video_id] = {
                "video": asdict(video),
                "mode": mode.value,
                "status": "failed",
                "error": str(error),
            }
            _save_index(out_dir, index)
            continue

        completed += 1
        records[video.video_id] = {
            "video": asdict(video),
            "mode": mode.value,
            "status": "completed",
            "article_path": str(article_path),
        }
        _save_index(out_dir, index)

    return BatchResult(
        total=len(videos),
        completed=completed,
        skipped=skipped,
        failed=failed,
    )
