from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from dfa.models import VideoRecord, VideoRef, VideoStatus


SCHEMA = """
CREATE TABLE IF NOT EXISTS videos (
    video_id TEXT PRIMARY KEY,
    source_url TEXT NOT NULL,
    title TEXT,
    author_name TEXT,
    status TEXT NOT NULL,
    failed_stage TEXT,
    article_path TEXT,
    collected_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    attempt_count INTEGER NOT NULL DEFAULT 1,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    error_code TEXT,
    error_message TEXT,
    FOREIGN KEY(video_id) REFERENCES videos(video_id)
);

CREATE TABLE IF NOT EXISTS artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id TEXT NOT NULL,
    artifact_type TEXT NOT NULL,
    path TEXT NOT NULL,
    created_at TEXT NOT NULL,
    cleaned_at TEXT,
    FOREIGN KEY(video_id) REFERENCES videos(video_id)
);
"""


def _now() -> str:
    return datetime.now(UTC).isoformat()


class Library:
    def __init__(self, database: Path):
        self.database = database
        self.database.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def add_video(self, ref: VideoRef) -> VideoRecord:
        timestamp = _now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO videos (
                    video_id, source_url, title, author_name, status,
                    collected_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(video_id) DO UPDATE SET
                    source_url = excluded.source_url,
                    title = COALESCE(excluded.title, videos.title),
                    author_name = COALESCE(excluded.author_name, videos.author_name),
                    updated_at = excluded.updated_at
                """,
                (
                    ref.video_id,
                    ref.source_url,
                    ref.title,
                    ref.author_name,
                    VideoStatus.DISCOVERED.value,
                    timestamp,
                    timestamp,
                ),
            )
        return self.get_video(ref.video_id)

    def get_video(self, video_id: str) -> VideoRecord:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT video_id, source_url, title, author_name, status,
                       failed_stage, article_path
                FROM videos WHERE video_id = ?
                """,
                (video_id,),
            ).fetchone()
        if row is None:
            raise KeyError(video_id)
        return VideoRecord(
            video_id=row["video_id"],
            source_url=row["source_url"],
            title=row["title"],
            author_name=row["author_name"],
            status=VideoStatus(row["status"]),
            failed_stage=row["failed_stage"],
            article_path=row["article_path"],
        )

    def count_videos(self) -> int:
        with self._connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM videos").fetchone()
        return int(row["count"])

    def list_videos(self) -> list[VideoRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT video_id, source_url, title, author_name, status,
                       failed_stage, article_path
                FROM videos ORDER BY collected_at, video_id
                """
            ).fetchall()
        return [
            VideoRecord(
                video_id=row["video_id"],
                source_url=row["source_url"],
                title=row["title"],
                author_name=row["author_name"],
                status=VideoStatus(row["status"]),
                failed_stage=row["failed_stage"],
                article_path=row["article_path"],
            )
            for row in rows
        ]

    def mark_status(self, video_id: str, status: VideoStatus) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE videos
                SET status = ?, failed_stage = NULL, updated_at = ?
                WHERE video_id = ?
                """,
                (status.value, _now(), video_id),
            )
        if cursor.rowcount != 1:
            raise KeyError(video_id)

    def record_failure(
        self,
        video_id: str,
        stage: str,
        error_code: str,
        error_message: str,
    ) -> None:
        timestamp = _now()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE videos
                SET status = ?, failed_stage = ?, updated_at = ?
                WHERE video_id = ?
                """,
                (VideoStatus.FAILED.value, stage, timestamp, video_id),
            )
            if cursor.rowcount != 1:
                raise KeyError(video_id)
            connection.execute(
                """
                INSERT INTO jobs (
                    video_id, stage, started_at, finished_at,
                    error_code, error_message
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (video_id, stage, timestamp, timestamp, error_code, error_message),
            )

    def complete_video(self, video_id: str, article_path: str) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE videos
                SET status = ?, failed_stage = NULL, article_path = ?, updated_at = ?
                WHERE video_id = ?
                """,
                (VideoStatus.COMPLETED.value, article_path, _now(), video_id),
            )
        if cursor.rowcount != 1:
            raise KeyError(video_id)
