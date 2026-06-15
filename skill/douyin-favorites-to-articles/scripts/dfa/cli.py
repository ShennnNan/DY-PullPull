from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from dfa import extractor
from dfa.articles import prepare_article_request, publish_article
from dfa.devices import resolve_whisper_config
from dfa.media import MediaError, YtDlpRunner, download_media
from dfa.models import VideoRef, VideoStatus
from dfa.paths import AppPaths
from dfa.storage import Library
from dfa.urls import normalize_source_url, video_id_from_url
from dfa.workspace import TaskWorkspace, clean_stale_workspaces


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dfa")
    parser.add_argument("--data-root", type=Path)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init")

    add_url = subparsers.add_parser("add-url")
    add_url.add_argument("url")
    add_url.add_argument("--title")
    add_url.add_argument("--author")

    fetch = subparsers.add_parser("fetch")
    fetch.add_argument("video_id")
    fetch.add_argument("--cookies-from-browser", dest="cookies_from_browser")

    transcribe = subparsers.add_parser("transcribe")
    transcribe.add_argument("video_id")
    transcribe.add_argument("--model")
    transcribe.add_argument("--device")

    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("video_id")
    prepare.add_argument("--transcript", type=Path, required=True)

    pull = subparsers.add_parser("pull")
    pull.add_argument("url")
    pull.add_argument("--cookies-from-browser", dest="cookies_from_browser")
    pull.add_argument("--model")
    pull.add_argument("--device")

    finalize = subparsers.add_parser("finalize")
    finalize.add_argument("video_id")
    finalize.add_argument("--article", type=Path, required=True)

    subparsers.add_parser("status")

    cleanup = subparsers.add_parser("cleanup")
    cleanup.add_argument("--older-than-hours", type=int, default=24)
    return parser


def _video_ref(library: Library, video_id: str) -> VideoRef:
    record = library.get_video(video_id)
    return VideoRef(
        video_id=record.video_id,
        source_url=record.source_url,
        title=record.title,
        author_name=record.author_name,
    )


def _detect_cuda() -> bool:
    """探测是否存在可用 CUDA 设备。失败一律视为不可用（由 CPU 兜底）。"""
    try:
        import ctranslate2

        return ctranslate2.get_cuda_device_count() > 0
    except Exception:  # noqa: BLE001
        return False


def _do_fetch(
    library: Library,
    paths: AppPaths,
    video_id: str,
    cookies_from_browser: str | None,
) -> int:
    workspace = TaskWorkspace(paths.temp, video_id)
    workspace.create()
    ref = _video_ref(library, video_id)
    try:
        result = download_media(
            ref,
            workspace.root,
            runner=YtDlpRunner(),
            cookies_from_browser=cookies_from_browser,
        )
    except MediaError as error:
        library.record_failure(video_id, "media", error.code, error.message)
        print(f"failed: {error.code}: {error.message}")
        return 2

    library.update_metadata(video_id, title=result.title, author_name=result.author_name)
    (workspace.root / "media.json").write_text(
        json.dumps(
            {"media_file": result.media_path.name, "published_at": result.published_at},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    library.mark_status(video_id, VideoStatus.MEDIA_PREPARED)
    print(f"media_prepared: {result.media_path}")
    return 0


def _do_transcribe(
    library: Library,
    paths: AppPaths,
    video_id: str,
    model: str | None,
    device: str | None,
) -> int:
    workspace = TaskWorkspace(paths.temp, video_id)
    media_meta_path = workspace.root / "media.json"
    if not media_meta_path.is_file():
        print("failed: MEDIA_PREPARE_FAILED: 未找到已下载媒体，请先运行 fetch")
        return 2
    media_meta = json.loads(media_meta_path.read_text(encoding="utf-8"))
    media_path = workspace.root / media_meta["media_file"]

    env = dict(os.environ)
    if model:
        env["DFA_WHISPER_MODEL"] = model
    if device:
        env["DFA_WHISPER_DEVICE"] = device
    config = resolve_whisper_config(env, cuda_available=_detect_cuda())

    try:
        extraction = extractor.transcribe(media_path, config)
    except extractor.ExtractionError as error:
        library.record_failure(video_id, "transcription", error.code, error.message)
        print(f"failed: {error.code}: {error.message}")
        return 2

    (workspace.root / "transcript.txt").write_text(extraction.transcript, encoding="utf-8")
    request = prepare_article_request(
        workspace.root,
        _video_ref(library, video_id),
        extraction.transcript,
        published_at=media_meta.get("published_at"),
    )
    library.mark_status(video_id, VideoStatus.EXTRACTED)
    print(f"device: {extraction.device}/{extraction.model} ({extraction.duration:.0f}s)")
    print(f"article_request: {request}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    paths = AppPaths.from_root(args.data_root) if args.data_root else AppPaths.default()
    paths.initialize()
    library = Library(paths.database)

    if args.command == "init":
        removed = clean_stale_workspaces(paths.temp)
        print(f"initialized: {paths.root}")
        print(f"stale_workspaces_removed: {len(removed)}")
        return 0

    if args.command == "add-url":
        normalized = normalize_source_url(args.url)
        ref = VideoRef(
            video_id=video_id_from_url(normalized),
            source_url=normalized,
            title=args.title,
            author_name=args.author,
        )
        record = library.add_video(ref)
        print(f"video_id: {record.video_id}")
        print(f"status: {record.status.value}")
        return 0

    if args.command == "fetch":
        return _do_fetch(library, paths, args.video_id, args.cookies_from_browser)

    if args.command == "transcribe":
        return _do_transcribe(library, paths, args.video_id, args.model, args.device)

    if args.command == "pull":
        normalized = normalize_source_url(args.url)
        video_id = video_id_from_url(normalized)
        library.add_video(VideoRef(video_id=video_id, source_url=normalized))
        print(f"video_id: {video_id}")
        code = _do_fetch(library, paths, video_id, args.cookies_from_browser)
        if code != 0:
            return code
        return _do_transcribe(library, paths, video_id, args.model, args.device)

    if args.command == "prepare":
        transcript = args.transcript.read_text(encoding="utf-8-sig")
        workspace = TaskWorkspace(paths.temp, args.video_id)
        request = prepare_article_request(
            workspace.create(),
            _video_ref(library, args.video_id),
            transcript,
        )
        library.mark_status(args.video_id, VideoStatus.EXTRACTED)
        print(f"article_request: {request}")
        return 0

    if args.command == "finalize":
        workspace = TaskWorkspace(paths.temp, args.video_id)
        try:
            target = publish_article(
                paths.articles,
                _video_ref(library, args.video_id),
                args.article,
            )
        except ValueError as error:
            library.record_failure(
                args.video_id,
                "article",
                "ARTICLE_VALIDATION_FAILED",
                str(error),
            )
            print(f"failed: {error}")
            return 2
        library.complete_video(args.video_id, str(target))
        workspace.cleanup()
        print(f"completed: {target}")
        return 0

    if args.command == "status":
        for record in library.list_videos():
            print(f"{record.video_id}\t{record.status.value}\t{record.source_url}")
        return 0

    if args.command == "cleanup":
        removed = clean_stale_workspaces(paths.temp, args.older_than_hours)
        print(f"removed: {len(removed)}")
        return 0

    raise AssertionError(args.command)
