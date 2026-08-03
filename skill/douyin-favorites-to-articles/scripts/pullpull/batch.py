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
    parse_refined,
    read_request,
    request_from_collected,
    write_request,
)
from pullpull.filenames import article_path_for
from pullpull.pull import Collected, collect
from pullpull.transcribe import FunasrTranscriber, Transcriber


@dataclass(frozen=True)
class BatchResult:
    total: int
    completed: int
    skipped: int
    failed: int


@dataclass(frozen=True)
class PrepareResult:
    total: int
    prepared: int
    skipped: int
    failed: int


@dataclass(frozen=True)
class RefinePreparedResult:
    total: int
    completed: int
    failed: int


@dataclass(frozen=True)
class RenameArticlesResult:
    total: int
    renamed: int
    skipped: int
    failed: int


class Collector(Protocol):
    def collect(
        self, url: str, *, cookies_from_browser: str | None = None
    ) -> Collected: ...


class DefaultCollector:
    def __init__(self, transcriber: Transcriber | None = None) -> None:
        self.transcriber = transcriber or FunasrTranscriber()

    def collect(
        self, url: str, *, cookies_from_browser: str | None = None
    ) -> Collected:
        return collect(
            url,
            cookies_from_browser=cookies_from_browser,
            transcriber=self.transcriber,
        )


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


def _is_prepared(
    record: dict | None,
    mode: ArticleMode,
    request_path: Path,
) -> bool:
    return bool(
        record
        and record.get("status") == "prepared"
        and record.get("mode") == mode.value
        and request_path.is_file()
    )


def prepare_account_videos(
    videos: list[AccountVideo],
    *,
    out_dir: Path | str,
    mode: ArticleMode,
    collector: Collector | None = None,
    cookies_from_browser: str | None = None,
) -> PrepareResult:
    """Download and transcribe account videos into resumable refine requests."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    requests_dir = out_dir / ".requests"
    requests_dir.mkdir(parents=True, exist_ok=True)
    collector = collector or DefaultCollector()
    index = _load_index(out_dir)
    records = index.setdefault("videos", {})

    prepared = 0
    skipped = 0
    failed = 0
    for video in videos:
        request_path = requests_dir / f"{video.video_id}.{mode.value}.request.json"
        existing = records.get(video.video_id)
        if _is_completed(existing, mode) or _is_prepared(
            existing, mode, request_path
        ):
            skipped += 1
            continue

        try:
            collected = collector.collect(
                video.source_url,
                cookies_from_browser=cookies_from_browser,
            )
            request = _request_from_video(video, collected)
            request_path = write_request(
                requests_dir / f"{request.video_id}.{mode.value}.request.json",
                request,
            )
        except Exception as error:  # noqa: BLE001
            failed += 1
            records[video.video_id] = {
                "video": asdict(video),
                "mode": mode.value,
                "status": "failed",
                "stage": "prepare",
                "error": str(error),
            }
            _save_index(out_dir, index)
            continue

        prepared += 1
        records[request.video_id] = {
            "video": asdict(video),
            "mode": mode.value,
            "status": "prepared",
            "request_path": str(request_path),
            "raw_chars": len(request.raw_transcript),
        }
        _save_index(out_dir, index)

    return PrepareResult(
        total=len(videos),
        prepared=prepared,
        skipped=skipped,
        failed=failed,
    )


def finalize_account_video(
    *,
    out_dir: Path | str,
    request_path: Path | str,
    response_path: Path | str,
    mode: ArticleMode,
) -> Path:
    """Finalize one prepared account item and mark it completed in index.json."""
    out_dir = Path(out_dir)
    request = read_request(Path(request_path))
    response = json.loads(Path(response_path).read_text(encoding="utf-8-sig"))
    index = _load_index(out_dir)
    records = index.setdefault("videos", {})
    try:
        refined = parse_refined(response, mode=mode)
        article_path = finalize(out_dir, request, refined, mode=mode)
    except Exception as error:  # noqa: BLE001
        record = records.setdefault(request.video_id, {})
        record.update(
            {
                "mode": mode.value,
                "status": "failed",
                "stage": "refine",
                "error": str(error),
            }
        )
        _save_index(out_dir, index)
        raise

    record = records.setdefault(request.video_id, {})
    record.update(
        {
            "mode": mode.value,
            "status": "completed",
            "request_path": str(Path(request_path)),
            "response_path": str(Path(response_path)),
            "article_path": str(article_path),
        }
    )
    record.pop("stage", None)
    record.pop("error", None)
    _save_index(out_dir, index)
    return article_path


def refine_prepared_account_videos(
    *,
    out_dir: Path | str,
    mode: ArticleMode,
    refiner: Refiner,
    limit: int | None = None,
) -> RefinePreparedResult:
    """Refine prepared requests, write responses, and finalize their articles."""
    out_dir = Path(out_dir)
    index = _load_index(out_dir)
    records = index.setdefault("videos", {})
    candidates: list[tuple[str, dict, Path]] = []
    for video_id, record in records.items():
        request_path = Path(str(record.get("request_path") or ""))
        retryable = record.get("status") == "prepared" or (
            record.get("status") == "failed" and record.get("stage") == "refine"
        )
        if (
            retryable
            and record.get("mode") == mode.value
            and request_path.is_file()
        ):
            candidates.append((video_id, record, request_path))
    if limit is not None:
        candidates = candidates[:limit]

    completed = 0
    failed = 0
    for video_id, record, request_path in candidates:
        response_path = request_path.with_name(
            request_path.name.replace(".request.json", ".response.json")
        )
        try:
            request = read_request(request_path)
            refined = refiner.refine(request)
            response_path.write_text(
                json.dumps(
                    {
                        "core_viewpoints": refined.summary,
                        "cleaned_transcript": refined.cleaned_transcript,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            finalize_account_video(
                out_dir=out_dir,
                request_path=request_path,
                response_path=response_path,
                mode=mode,
            )
        except Exception as error:  # noqa: BLE001
            failed += 1
            current_index = _load_index(out_dir)
            current_record = current_index.setdefault("videos", {}).setdefault(
                video_id, {}
            )
            current_record.update(
                {
                    "status": "failed",
                    "stage": "refine",
                    "error": str(error),
                }
            )
            _save_index(out_dir, current_index)
            continue
        completed += 1

    return RefinePreparedResult(
        total=len(candidates),
        completed=completed,
        failed=failed,
    )


def rename_completed_articles(out_dir: Path | str) -> RenameArticlesResult:
    """Migrate completed numeric article filenames to readable title filenames."""
    out_dir = Path(out_dir)
    out_root = out_dir.resolve()
    index = _load_index(out_dir)
    records = index.setdefault("videos", {})
    total = 0
    renamed = 0
    skipped = 0
    failed = 0

    for record in records.values():
        if record.get("status") != "completed":
            continue
        total += 1
        try:
            request_path = Path(str(record.get("request_path") or ""))
            old_path = Path(str(record.get("article_path") or ""))
            try:
                old_path.resolve().relative_to(out_root)
            except ValueError as error:
                raise ValueError(f"文章路径不在归档目录内：{old_path}") from error
            request = read_request(request_path)
            new_path = article_path_for(
                out_dir, request.title, request.video_id
            )
            if old_path == new_path:
                skipped += 1
                continue
            if not old_path.is_file():
                if new_path.is_file():
                    record["article_path"] = str(new_path)
                    record.pop("rename_error", None)
                    skipped += 1
                    _save_index(out_dir, index)
                    continue
                raise FileNotFoundError(f"文章文件不存在：{old_path}")
            if new_path.exists():
                raise FileExistsError(f"标题目标已存在：{new_path}")
            old_path.rename(new_path)
            record["article_path"] = str(new_path)
            record.pop("rename_error", None)
            renamed += 1
            _save_index(out_dir, index)
        except Exception as error:  # noqa: BLE001
            failed += 1
            record["rename_error"] = str(error)
            _save_index(out_dir, index)

    return RenameArticlesResult(
        total=total,
        renamed=renamed,
        skipped=skipped,
        failed=failed,
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
