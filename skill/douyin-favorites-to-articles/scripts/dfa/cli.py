from __future__ import annotations

import argparse
from pathlib import Path

from dfa.articles import prepare_article_request, publish_article
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

    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("video_id")
    prepare.add_argument("--transcript", type=Path, required=True)

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

    if args.command == "prepare":
        transcript = args.transcript.read_text(encoding="utf-8")
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
