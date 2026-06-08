# Douyin Favorites v0.1 Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a self-contained Codex Skill foundation that registers one Douyin URL, stores deterministic state in SQLite, accepts a local transcript, prepares an article request for Codex, validates the generated Markdown, updates the collection index, and removes temporary data.

**Architecture:** Keep the distributable runtime inside `skill/douyin-favorites-to-articles/`. A thin Python launcher calls focused standard-library modules for paths, URL identity, SQLite state, temporary workspaces, article contracts, and CLI orchestration. v0.1 deliberately accepts an existing local transcript; later plans replace that input boundary with browser-assisted media extraction, `faster-whisper`, and OCR without changing storage or article interfaces.

**Tech Stack:** Python 3.11+, standard library (`argparse`, `sqlite3`, `dataclasses`, `pathlib`, `json`), pytest, Codex Skill metadata.

---

## Scope Split

The approved design contains several independently changing subsystems. Implement them as separate plans:

1. **v0.1 Foundation:** repository hygiene, Skill shell, URL identity, SQLite state, transcript-to-article contract, cleanup, and end-to-end fixture test. This document.
2. **v0.2 Local Media:** temporary media preparation, FFmpeg integration, CUDA detection, `faster-whisper`, CPU fallback, and model configuration.
3. **v0.3 Favorites Collection:** independent browser profile, manual login, favorites scrolling, incremental collection, human-verification pause, keyframes, and OCR.
4. **v0.4 Commercial Release:** `doctor`, customer-facing installation material, sensitive-data scanning, release ZIP, clean-Windows acceptance testing, and versioning.

v0.1 must produce working, testable software on its own. It must not pretend media extraction exists.

## File Map

```text
.gitignore
LICENSE
pyproject.toml
docs/
  customer/
    privacy.md
  superpowers/
    plans/
      2026-06-08-douyin-favorites-v0.1-foundation.md
skill/
  douyin-favorites-to-articles/
    SKILL.md
    agents/
      openai.yaml
    references/
      article-format.md
      error-codes.md
    scripts/
      dfa_cli.py
      dfa/
        __init__.py
        articles.py
        cli.py
        models.py
        paths.py
        storage.py
        urls.py
        workspace.py
tests/
  test_articles.py
  test_cli_flow.py
  test_paths.py
  test_skill_layout.py
  test_storage.py
  test_urls.py
  test_workspace.py
```

Responsibilities:

- `paths.py`: resolve and initialize local data directories.
- `models.py`: define stable statuses and immutable data records.
- `urls.py`: normalize source URLs and derive deterministic video IDs.
- `storage.py`: own the SQLite schema, idempotent registration, transitions, and failures.
- `workspace.py`: create and clean per-video temporary directories.
- `articles.py`: prepare article request JSON, validate Markdown, publish articles, and rebuild `index.md`.
- `cli.py`: expose use cases without embedding storage or file logic.
- `dfa_cli.py`: make the CLI executable from the Skill folder.
- `SKILL.md`: tell Codex exactly when and how to invoke the scripts and write the article.
- `references/`: hold detailed article and error contracts so `SKILL.md` stays concise.

### Task 1: Bootstrap the Repository and Skill Layout

**Files:**
- Create: `.gitignore`
- Create: `LICENSE`
- Create: `pyproject.toml`
- Create: `tests/test_skill_layout.py`
- Create: `skill/douyin-favorites-to-articles/` with the Skill Creator initializer

- [ ] **Step 1: Create the Python test configuration**

Create `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=75"]
build-backend = "setuptools.build_meta"

[project]
name = "douyin-favorites-analyzer"
version = "0.1.0"
description = "Local Codex Skill for turning personal Douyin favorites into Markdown articles"
requires-python = ">=3.11"

[project.optional-dependencies]
dev = [
    "pytest>=8.3,<9",
    "PyYAML>=6.0,<7",
]

[tool.setuptools]
packages = []

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["skill/douyin-favorites-to-articles/scripts"]
addopts = "-q"
```

- [ ] **Step 2: Write the failing layout test**

Create `tests/test_skill_layout.py`:

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skill" / "douyin-favorites-to-articles"


def test_skill_has_required_layout():
    assert (SKILL / "SKILL.md").is_file()
    assert (SKILL / "agents" / "openai.yaml").is_file()
    assert (SKILL / "scripts" / "dfa_cli.py").is_file()
    assert (SKILL / "scripts" / "dfa" / "__init__.py").is_file()
    assert (SKILL / "references" / "article-format.md").is_file()
    assert (SKILL / "references" / "error-codes.md").is_file()
```

- [ ] **Step 3: Install development dependencies and verify the test fails**

Run:

```powershell
$python = "C:\Users\imqia\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
& $python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest tests/test_skill_layout.py -v
```

Expected: FAIL because the Skill files do not exist.

If that bundled path differs on another Codex installation, call the Codex workspace dependency locator and assign its returned Python executable to `$python`.

- [ ] **Step 4: Initialize the Skill with the official helper**

Run:

```powershell
$skillCreator = "C:\Users\imqia\.codex\skills\.system\skill-creator"
& .\.venv\Scripts\python.exe "$skillCreator\scripts\init_skill.py" `
  douyin-favorites-to-articles `
  --path skill `
  --resources scripts,references `
  --interface "display_name=抖音收藏文章提炼" `
  --interface "short_description=把个人抖音收藏增量整理为本地 Markdown 文章" `
  --interface "default_prompt=同步我本人可访问的抖音收藏，并将新增内容整理为本地文章。"
New-Item -ItemType Directory -Force "skill\douyin-favorites-to-articles\scripts\dfa" | Out-Null
New-Item -ItemType File -Force "skill\douyin-favorites-to-articles\scripts\dfa\__init__.py" | Out-Null
New-Item -ItemType File -Force "skill\douyin-favorites-to-articles\scripts\dfa_cli.py" | Out-Null
New-Item -ItemType File -Force "skill\douyin-favorites-to-articles\references\article-format.md" | Out-Null
New-Item -ItemType File -Force "skill\douyin-favorites-to-articles\references\error-codes.md" | Out-Null
```

Remove any generated example files that are not listed in the file map.

- [ ] **Step 5: Add privacy-first repository exclusions**

Create `.gitignore`:

```gitignore
.venv/
__pycache__/
*.py[cod]
.pytest_cache/
.coverage
htmlcov/
dist/
build/
*.egg-info/

data/
browser-profile/
temp/
logs/
articles/
*.db
*.db-shm
*.db-wal
*.sqlite
*.sqlite3
*.mp4
*.webm
*.m4a
*.mp3
*.wav
*.flac
*.cookie
cookies.txt
```

- [ ] **Step 6: Add the proprietary license notice**

Create `LICENSE`:

```text
Copyright (c) 2026. All rights reserved.

This repository and its distributable Skill are proprietary software.
No permission is granted to copy, modify, redistribute, sublicense, or resell
the software except under a separate written license from the copyright owner.
```

- [ ] **Step 7: Run the layout test**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_skill_layout.py -v
```

Expected: PASS.

- [ ] **Step 8: Commit**

```powershell
git add .gitignore LICENSE pyproject.toml tests/test_skill_layout.py skill/douyin-favorites-to-articles
git commit -m "chore: scaffold distributable Codex skill"
```

### Task 2: Define Local Data Paths

**Files:**
- Create: `skill/douyin-favorites-to-articles/scripts/dfa/paths.py`
- Create: `tests/test_paths.py`

- [ ] **Step 1: Write the failing path tests**

Create `tests/test_paths.py`:

```python
from dfa.paths import AppPaths


def test_initialize_creates_expected_directories(tmp_path):
    paths = AppPaths.from_root(tmp_path)
    paths.initialize()

    assert paths.database == tmp_path / "library.db"
    assert paths.articles.is_dir()
    assert paths.browser_profile.is_dir()
    assert paths.logs.is_dir()
    assert paths.temp.is_dir()


def test_default_root_uses_local_app_data(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    paths = AppPaths.default()

    assert paths.root == tmp_path / "DouyinFavoritesToArticles"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_paths.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'dfa.paths'`.

- [ ] **Step 3: Implement the path object**

Create `skill/douyin-favorites-to-articles/scripts/dfa/paths.py`:

```python
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppPaths:
    root: Path
    database: Path
    articles: Path
    browser_profile: Path
    logs: Path
    temp: Path

    @classmethod
    def from_root(cls, root: Path) -> "AppPaths":
        resolved = root.expanduser().resolve()
        return cls(
            root=resolved,
            database=resolved / "library.db",
            articles=resolved / "articles",
            browser_profile=resolved / "browser-profile",
            logs=resolved / "logs",
            temp=resolved / "temp",
        )

    @classmethod
    def default(cls) -> "AppPaths":
        local_app_data = os.environ.get("LOCALAPPDATA")
        base = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
        return cls.from_root(base / "DouyinFavoritesToArticles")

    def initialize(self) -> None:
        for directory in (
            self.root,
            self.articles,
            self.browser_profile,
            self.logs,
            self.temp,
        ):
            directory.mkdir(parents=True, exist_ok=True)
```

- [ ] **Step 4: Run tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_paths.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```powershell
git add skill/douyin-favorites-to-articles/scripts/dfa/paths.py tests/test_paths.py
git commit -m "feat: add isolated local data paths"
```

### Task 3: Normalize URLs and Derive Stable Video IDs

**Files:**
- Create: `skill/douyin-favorites-to-articles/scripts/dfa/models.py`
- Create: `skill/douyin-favorites-to-articles/scripts/dfa/urls.py`
- Create: `tests/test_urls.py`

- [ ] **Step 1: Write failing URL identity tests**

Create `tests/test_urls.py`:

```python
from dfa.urls import normalize_source_url, video_id_from_url


def test_normalizes_tracking_query_and_fragment():
    source = "https://www.douyin.com/video/7412345678901234567?previous_page=web_code_link#x"
    assert normalize_source_url(source) == "https://www.douyin.com/video/7412345678901234567"


def test_extracts_numeric_video_id():
    source = "https://www.douyin.com/video/7412345678901234567"
    assert video_id_from_url(source) == "7412345678901234567"


def test_short_link_gets_stable_url_identity():
    source = "https://v.douyin.com/AbCdEf/"
    first = video_id_from_url(source)
    second = video_id_from_url(source)
    assert first == second
    assert first.startswith("url-")
    assert len(first) == 20


def test_rejects_non_douyin_hosts():
    try:
        normalize_source_url("https://example.com/video/1")
    except ValueError as error:
        assert str(error) == "仅支持 douyin.com 域名的链接"
    else:
        raise AssertionError("non-Douyin URL should be rejected")
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_urls.py -v
```

Expected: FAIL because `dfa.urls` does not exist.

- [ ] **Step 3: Add shared models**

Create `skill/douyin-favorites-to-articles/scripts/dfa/models.py`:

```python
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
```

- [ ] **Step 4: Implement URL normalization**

Create `skill/douyin-favorites-to-articles/scripts/dfa/urls.py`:

```python
from __future__ import annotations

import hashlib
import re
from urllib.parse import parse_qs, urlsplit, urlunsplit


_VIDEO_PATH = re.compile(r"/video/(\d+)")
_ALLOWED_HOSTS = {"douyin.com", "www.douyin.com", "v.douyin.com"}


def normalize_source_url(source_url: str) -> str:
    value = source_url.strip()
    parsed = urlsplit(value)
    host = (parsed.hostname or "").lower()
    if host not in _ALLOWED_HOSTS and not host.endswith(".douyin.com"):
        raise ValueError("仅支持 douyin.com 域名的链接")

    path = parsed.path.rstrip("/") or "/"
    query = parse_qs(parsed.query)
    modal_id = query.get("modal_id", [None])[0]
    if modal_id and modal_id.isdigit():
        path = f"/video/{modal_id}"

    return urlunsplit(("https", host, path, "", ""))


def video_id_from_url(source_url: str) -> str:
    normalized = normalize_source_url(source_url)
    match = _VIDEO_PATH.search(urlsplit(normalized).path)
    if match:
        return match.group(1)

    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    return f"url-{digest}"
```

- [ ] **Step 5: Run tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_urls.py -v
```

Expected: 4 passed.

- [ ] **Step 6: Commit**

```powershell
git add skill/douyin-favorites-to-articles/scripts/dfa/models.py skill/douyin-favorites-to-articles/scripts/dfa/urls.py tests/test_urls.py
git commit -m "feat: add deterministic Douyin URL identity"
```

### Task 4: Build the SQLite State Store

**Files:**
- Create: `skill/douyin-favorites-to-articles/scripts/dfa/storage.py`
- Create: `tests/test_storage.py`

- [ ] **Step 1: Write failing storage tests**

Create `tests/test_storage.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_storage.py -v
```

Expected: FAIL because `dfa.storage` does not exist.

- [ ] **Step 3: Implement the SQLite library**

Create `skill/douyin-favorites-to-articles/scripts/dfa/storage.py`:

```python
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
```

- [ ] **Step 4: Run tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_storage.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```powershell
git add skill/douyin-favorites-to-articles/scripts/dfa/storage.py tests/test_storage.py
git commit -m "feat: persist idempotent video processing state"
```

### Task 5: Manage Per-Video Temporary Workspaces

**Files:**
- Create: `skill/douyin-favorites-to-articles/scripts/dfa/workspace.py`
- Create: `tests/test_workspace.py`

- [ ] **Step 1: Write failing workspace tests**

Create `tests/test_workspace.py`:

```python
import os
import time

from dfa.workspace import TaskWorkspace, clean_stale_workspaces


def test_workspace_create_and_cleanup(tmp_path):
    workspace = TaskWorkspace(tmp_path, "123")
    workspace.create()
    (workspace.root / "transcript.txt").write_text("hello", encoding="utf-8")

    assert workspace.root.is_dir()
    workspace.cleanup()
    assert not workspace.root.exists()


def test_cleanup_removes_only_stale_directories(tmp_path):
    stale = TaskWorkspace(tmp_path, "old")
    fresh = TaskWorkspace(tmp_path, "new")
    stale.create()
    fresh.create()
    old = time.time() - 48 * 60 * 60
    os.utime(stale.root, (old, old))

    removed = clean_stale_workspaces(tmp_path, older_than_hours=24)

    assert removed == ["old"]
    assert not stale.root.exists()
    assert fresh.root.exists()
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_workspace.py -v
```

Expected: FAIL because `dfa.workspace` does not exist.

- [ ] **Step 3: Implement workspace lifecycle**

Create `skill/douyin-favorites-to-articles/scripts/dfa/workspace.py`:

```python
from __future__ import annotations

import shutil
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TaskWorkspace:
    temp_root: Path
    video_id: str

    @property
    def root(self) -> Path:
        return self.temp_root / self.video_id

    def create(self) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        return self.root

    def cleanup(self) -> None:
        if self.root.exists():
            shutil.rmtree(self.root)


def clean_stale_workspaces(temp_root: Path, older_than_hours: int = 24) -> list[str]:
    if not temp_root.exists():
        return []

    cutoff = time.time() - older_than_hours * 60 * 60
    removed: list[str] = []
    for candidate in sorted(temp_root.iterdir()):
        if candidate.is_dir() and candidate.stat().st_mtime < cutoff:
            shutil.rmtree(candidate)
            removed.append(candidate.name)
    return removed
```

- [ ] **Step 4: Run tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_workspace.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```powershell
git add skill/douyin-favorites-to-articles/scripts/dfa/workspace.py tests/test_workspace.py
git commit -m "feat: manage temporary analysis workspaces"
```

### Task 6: Define the Codex Article Contract

**Files:**
- Create: `skill/douyin-favorites-to-articles/scripts/dfa/articles.py`
- Create: `tests/test_articles.py`

- [ ] **Step 1: Write failing article tests**

Create `tests/test_articles.py`:

```python
import json

from dfa.articles import (
    REQUIRED_HEADINGS,
    prepare_article_request,
    publish_article,
    validate_article,
)
from dfa.models import VideoRef


ARTICLE = """# 整理标题

## 来源信息

- 原标题：测试
- 作者：作者
- 发布时间：未知
- 收藏时间：未知
- 原链接：https://www.douyin.com/video/123

## 内容摘要

这是摘要。

## 整理后的正文

这是正文。

## 关键词

测试、知识

## 可行动要点

- 执行一项操作。

## 提取说明

- 语音转写：成功
- OCR：未执行
- 内容完整性：仅依据语音文本
"""


def test_prepare_request_contains_source_and_transcript(tmp_path):
    target = prepare_article_request(
        tmp_path,
        VideoRef("123", "https://www.douyin.com/video/123", "测试", "作者"),
        "完整转写文本",
    )

    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["video"]["video_id"] == "123"
    assert payload["transcript"] == "完整转写文本"
    assert payload["required_headings"] == list(REQUIRED_HEADINGS)


def test_validate_article_reports_missing_heading():
    errors = validate_article("# 标题\n\n## 来源信息\n")
    assert "缺少章节：## 内容摘要" in errors


def test_publish_article_writes_article_and_index(tmp_path):
    article_source = tmp_path / "draft.md"
    article_source.write_text(ARTICLE, encoding="utf-8")
    articles = tmp_path / "articles"
    ref = VideoRef("123", "https://www.douyin.com/video/123", "测试", "作者")

    published = publish_article(articles, ref, article_source)

    assert published.name == "123.md"
    assert published.read_text(encoding="utf-8") == ARTICLE
    index = (articles / "index.md").read_text(encoding="utf-8")
    assert "[整理标题](123.md)" in index
    assert "作者" in index
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_articles.py -v
```

Expected: FAIL because `dfa.articles` does not exist.

- [ ] **Step 3: Implement request, validation, publication, and index rebuild**

Create `skill/douyin-favorites-to-articles/scripts/dfa/articles.py`:

```python
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from dfa.models import VideoRef


REQUIRED_HEADINGS = (
    "## 来源信息",
    "## 内容摘要",
    "## 整理后的正文",
    "## 关键词",
    "## 可行动要点",
    "## 提取说明",
)


def prepare_article_request(
    workspace: Path,
    video: VideoRef,
    transcript: str,
) -> Path:
    if not transcript.strip():
        raise ValueError("转写文本不能为空")
    workspace.mkdir(parents=True, exist_ok=True)
    target = workspace / "article-request.json"
    target.write_text(
        json.dumps(
            {
                "video": {
                    "video_id": video.video_id,
                    "source_url": video.source_url,
                    "title": video.title,
                    "author_name": video.author_name,
                },
                "transcript": transcript,
                "ocr_text": "",
                "required_headings": list(REQUIRED_HEADINGS),
                "grounding_rule": "仅依据提取材料整理，不猜测缺失内容。",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return target


def validate_article(content: str) -> list[str]:
    errors: list[str] = []
    if not re.search(r"^#\s+\S+", content, re.MULTILINE):
        errors.append("缺少一级标题")
    for heading in REQUIRED_HEADINGS:
        if heading not in content:
            errors.append(f"缺少章节：{heading}")
    if "douyin.com" not in content:
        errors.append("来源信息中缺少抖音原链接")
    return errors


def _title_from_markdown(content: str) -> str:
    match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if not match:
        raise ValueError("文章缺少一级标题")
    return match.group(1).strip()


def publish_article(
    articles_dir: Path,
    video: VideoRef,
    article_source: Path,
) -> Path:
    content = article_source.read_text(encoding="utf-8")
    errors = validate_article(content)
    if errors:
        raise ValueError("；".join(errors))

    articles_dir.mkdir(parents=True, exist_ok=True)
    target = articles_dir / f"{video.video_id}.md"
    shutil.copyfile(article_source, target)
    rebuild_index(articles_dir)
    return target


def rebuild_index(articles_dir: Path) -> Path:
    entries: list[str] = []
    for article in sorted(articles_dir.glob("*.md")):
        if article.name == "index.md":
            continue
        content = article.read_text(encoding="utf-8")
        title = _title_from_markdown(content)
        author_match = re.search(r"^- 作者[：:]\s*(.+)$", content, re.MULTILINE)
        author = author_match.group(1).strip() if author_match else "未知作者"
        entries.append(f"- [{title}]({article.name}) - {author}")

    index = articles_dir / "index.md"
    body = "# 抖音收藏文章目录\n\n"
    body += "\n".join(entries) if entries else "尚未生成文章。"
    body += "\n"
    index.write_text(body, encoding="utf-8")
    return index
```

- [ ] **Step 4: Run tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_articles.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```powershell
git add skill/douyin-favorites-to-articles/scripts/dfa/articles.py tests/test_articles.py
git commit -m "feat: define grounded article publication contract"
```

### Task 7: Expose the v0.1 CLI Flow

**Files:**
- Create: `skill/douyin-favorites-to-articles/scripts/dfa/cli.py`
- Modify: `skill/douyin-favorites-to-articles/scripts/dfa_cli.py`
- Create: `tests/test_cli_flow.py`

- [ ] **Step 1: Write the failing CLI flow test**

Create `tests/test_cli_flow.py`:

```python
import json

from dfa.cli import main
from dfa.models import VideoStatus
from dfa.storage import Library


ARTICLE = """# CLI 测试文章

## 来源信息

- 原标题：测试
- 作者：测试作者
- 发布时间：未知
- 收藏时间：未知
- 原链接：https://www.douyin.com/video/123

## 内容摘要

摘要。

## 整理后的正文

正文。

## 关键词

测试

## 可行动要点

- 验证流程。

## 提取说明

- 语音转写：成功
- OCR：未执行
- 内容完整性：仅依据语音文本
"""


def test_cli_register_prepare_finalize_flow(tmp_path, capsys):
    data_root = tmp_path / "data"
    transcript = tmp_path / "transcript.txt"
    transcript.write_text("这是一段本地转写文本。", encoding="utf-8")

    assert main(["--data-root", str(data_root), "init"]) == 0
    assert main(
        [
            "--data-root",
            str(data_root),
            "add-url",
            "https://www.douyin.com/video/123",
            "--title",
            "测试",
            "--author",
            "测试作者",
        ]
    ) == 0
    assert main(
        [
            "--data-root",
            str(data_root),
            "prepare",
            "123",
            "--transcript",
            str(transcript),
        ]
    ) == 0

    request_path = data_root / "temp" / "123" / "article-request.json"
    request = json.loads(request_path.read_text(encoding="utf-8"))
    assert request["transcript"] == "这是一段本地转写文本。"

    draft = data_root / "temp" / "123" / "article.md"
    draft.write_text(ARTICLE, encoding="utf-8")
    assert main(
        [
            "--data-root",
            str(data_root),
            "finalize",
            "123",
            "--article",
            str(draft),
        ]
    ) == 0

    record = Library(data_root / "library.db").get_video("123")
    assert record.status is VideoStatus.COMPLETED
    assert (data_root / "articles" / "123.md").is_file()
    assert (data_root / "articles" / "index.md").is_file()
    assert not (data_root / "temp" / "123").exists()
    assert "completed" in capsys.readouterr().out
```

- [ ] **Step 2: Run the test to verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_cli_flow.py -v
```

Expected: FAIL because `dfa.cli` does not exist.

- [ ] **Step 3: Implement the CLI**

Create `skill/douyin-favorites-to-articles/scripts/dfa/cli.py`:

```python
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
```

- [ ] **Step 4: Add the executable launcher**

Replace `skill/douyin-favorites-to-articles/scripts/dfa_cli.py` with:

```python
from dfa.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run the CLI test and full unit suite**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_cli_flow.py -v
.\.venv\Scripts\python.exe -m pytest -v
```

Expected: CLI flow passes; full suite passes.

- [ ] **Step 6: Commit**

```powershell
git add skill/douyin-favorites-to-articles/scripts/dfa/cli.py skill/douyin-favorites-to-articles/scripts/dfa_cli.py tests/test_cli_flow.py
git commit -m "feat: add transcript-to-article CLI workflow"
```

### Task 8: Write and Validate the Codex Skill

**Files:**
- Modify: `skill/douyin-favorites-to-articles/SKILL.md`
- Modify: `skill/douyin-favorites-to-articles/agents/openai.yaml`
- Modify: `skill/douyin-favorites-to-articles/references/article-format.md`
- Modify: `skill/douyin-favorites-to-articles/references/error-codes.md`
- Create: `docs/customer/privacy.md`

- [ ] **Step 1: Write the article contract reference**

Replace `skill/douyin-favorites-to-articles/references/article-format.md` with:

```markdown
# 文章格式

读取 `article-request.json` 后，根据 `transcript` 和 `ocr_text` 写入工作目录中的 `article.md`。

必须包含：

1. `#` 一级标题
2. `## 来源信息`
3. `## 内容摘要`
4. `## 整理后的正文`
5. `## 关键词`
6. `## 可行动要点`
7. `## 提取说明`

来源信息必须保留原链接。只整理提取材料中能够支持的内容，删除口头重复并修复明显断句。材料缺失时在“提取说明”中明确标注，不补写未经支持的事实。
```

- [ ] **Step 2: Write the error reference**

Replace `skill/douyin-favorites-to-articles/references/error-codes.md` with:

```markdown
# 错误码

- `ARTICLE_VALIDATION_FAILED`：文章缺少必要章节、一级标题或原链接。根据 CLI 输出补齐文章，再重新执行 `finalize`。
- `AUTH_REQUIRED`：登录态不存在或已失效。后续浏览器版本必须暂停并要求用户手动登录。
- `HUMAN_VERIFICATION_REQUIRED`：出现验证码或风控。禁止自动绕过，等待用户手动处理。
- `SOURCE_UNAVAILABLE`：视频失效、私密或当前账号不可访问。
- `MEDIA_PREPARE_FAILED`：后续媒体版本无法生成临时音频或关键帧。
- `TRANSCRIPTION_FAILED`：后续 Whisper 版本转写失败。
- `OCR_FAILED`：后续 OCR 版本提取失败；纯语音内容仍可继续。
```

- [ ] **Step 3: Replace the generated Skill instructions**

Replace `skill/douyin-favorites-to-articles/SKILL.md` with:

```markdown
---
name: douyin-favorites-to-articles
description: 将用户本人可访问的抖音收藏或抖音分享链接增量整理为本地 Markdown 文章。用于首次初始化、添加链接、准备文章、校验并发布文章、查看处理状态、重试失败项目或清理临时数据。仅处理用户合法访问的内容；不得绕过登录、验证码、风控或访问控制。
---

# 抖音收藏文章提炼

将 Skill 根目录记为 `$SKILL_ROOT`。先解析可用的 Python：优先使用系统 `python`；如果系统命令不存在，使用 Codex 工作区依赖定位工具返回的 Python 可执行文件。将结果记为 `$PYTHON`。

使用：

```powershell
& $PYTHON "$SKILL_ROOT\scripts\dfa_cli.py" <参数>
```

## 初始化

先运行：

```powershell
& $PYTHON "$SKILL_ROOT\scripts\dfa_cli.py" init
```

默认数据保存在 `%LOCALAPPDATA%\DouyinFavoritesToArticles`。除非用户明确指定测试目录，不要把数据写入 Skill 或 Git 仓库。

## v0.1 单链接流程

1. 使用 `add-url <抖音链接> [--title 标题] [--author 作者]` 注册链接。
2. v0.1 仅接受已经存在的本地 UTF-8 转写文本。使用 `prepare <video-id> --transcript <文本路径>` 生成 `article-request.json`。
3. 读取 `article-request.json`。写文章前读取 [references/article-format.md](references/article-format.md)。
4. 将文章写入同一临时目录的 `article.md`。
5. 运行 `finalize <video-id> --article <article.md 路径>`。
6. 只有 CLI 输出 `completed` 后才向用户报告完成。

不要声称 v0.1 已经支持视频下载、Whisper、OCR 或收藏页自动抓取。

## 状态与清理

- 使用 `status` 查看已注册条目。
- 使用 `cleanup --older-than-hours 24` 清理过期临时目录。
- `finalize` 成功后会立即删除该视频的临时目录。
- `finalize` 失败时读取 [references/error-codes.md](references/error-codes.md)，修复文章后重试。

## 内容约束

- 仅依据转写和 OCR 材料整理。
- 保留原链接。
- 不猜测缺失事实。
- 不发布、转载或上传视频内容。
- 遇到验证码或风控时暂停，要求用户手动处理。
```

- [ ] **Step 4: Regenerate `agents/openai.yaml`**

Run:

```powershell
$skillCreator = "C:\Users\imqia\.codex\skills\.system\skill-creator"
& .\.venv\Scripts\python.exe "$skillCreator\scripts\generate_openai_yaml.py" `
  "skill\douyin-favorites-to-articles" `
  --interface "display_name=抖音收藏文章提炼" `
  --interface "short_description=把个人抖音收藏增量整理为本地 Markdown 文章" `
  --interface "default_prompt=添加一个抖音链接，并根据本地转写材料整理成 Markdown 文章。"
```

- [ ] **Step 5: Add the customer privacy statement outside the Skill**

Create `docs/customer/privacy.md`:

```markdown
# 隐私与使用边界

- 本工具仅处理购买者本人合法访问的抖音内容。
- 默认数据目录位于购买者本机 `%LOCALAPPDATA%\DouyinFavoritesToArticles`。
- 登录态、SQLite、文章、日志和临时文件不得上传到 GitHub 或反馈工单。
- 工具不保存抖音密码，不绕过验证码、风控或访问限制。
- 临时媒体将在文章成功发布后删除。
- 用户应自行确认其整理、引用和使用内容的行为符合平台规则、版权和隐私要求。
```

- [ ] **Step 6: Validate the Skill**

Run:

```powershell
$skillCreator = "C:\Users\imqia\.codex\skills\.system\skill-creator"
& .\.venv\Scripts\python.exe "$skillCreator\scripts\quick_validate.py" "skill\douyin-favorites-to-articles"
.\.venv\Scripts\python.exe -m pytest tests/test_skill_layout.py -v
```

Expected: validator reports a valid skill; layout test passes.

- [ ] **Step 7: Commit**

```powershell
git add skill/douyin-favorites-to-articles docs/customer/privacy.md
git commit -m "feat: document Codex article workflow"
```

### Task 9: Verify the v0.1 Release Boundary

**Files:**
- Modify: `tests/test_cli_flow.py`

- [ ] **Step 1: Add a regression test for invalid articles**

Append to `tests/test_cli_flow.py`:

```python
def test_finalize_failure_preserves_workspace_and_records_failure(tmp_path):
    data_root = tmp_path / "data"
    main(["--data-root", str(data_root), "init"])
    main(
        [
            "--data-root",
            str(data_root),
            "add-url",
            "https://www.douyin.com/video/456",
        ]
    )
    workspace = data_root / "temp" / "456"
    workspace.mkdir(parents=True)
    invalid = workspace / "article.md"
    invalid.write_text("# 不完整文章\n", encoding="utf-8")

    result = main(
        [
            "--data-root",
            str(data_root),
            "finalize",
            "456",
            "--article",
            str(invalid),
        ]
    )

    record = Library(data_root / "library.db").get_video("456")
    assert result == 2
    assert record.status is VideoStatus.FAILED
    assert record.failed_stage == "article"
    assert workspace.exists()
```

- [ ] **Step 2: Run the focused regression test**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_cli_flow.py::test_finalize_failure_preserves_workspace_and_records_failure -v
```

Expected: PASS.

- [ ] **Step 3: Run all automated checks**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
$skillCreator = "C:\Users\imqia\.codex\skills\.system\skill-creator"
& .\.venv\Scripts\python.exe "$skillCreator\scripts\quick_validate.py" "skill\douyin-favorites-to-articles"
git diff --check
git status --short
```

Expected:

- All pytest tests pass.
- Skill validation succeeds.
- `git diff --check` emits no errors.
- `git status --short` lists only the intended v0.1 files before the final commit.

- [ ] **Step 4: Perform a manual smoke test in a disposable data directory**

Run:

```powershell
$smoke = Join-Path $env:TEMP "dfa-v01-smoke"
Remove-Item -Recurse -Force $smoke -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $smoke | Out-Null
"这是用于冒烟测试的本地转写文本。" | Set-Content -Encoding UTF8 "$smoke\transcript.txt"
.\.venv\Scripts\python.exe "skill\douyin-favorites-to-articles\scripts\dfa_cli.py" --data-root "$smoke\data" init
.\.venv\Scripts\python.exe "skill\douyin-favorites-to-articles\scripts\dfa_cli.py" --data-root "$smoke\data" add-url "https://www.douyin.com/video/789" --title "冒烟测试" --author "本地测试"
.\.venv\Scripts\python.exe "skill\douyin-favorites-to-articles\scripts\dfa_cli.py" --data-root "$smoke\data" prepare 789 --transcript "$smoke\transcript.txt"
Get-Content -Raw "$smoke\data\temp\789\article-request.json"
```

Expected: request JSON contains video ID `789`, the normalized Douyin URL, title, author, transcript, required headings, and grounding rule.

Do not commit the disposable smoke directory.

- [ ] **Step 5: Commit**

```powershell
git add tests/test_cli_flow.py
git commit -m "test: verify v0.1 article workflow boundary"
```

## v0.1 Completion Criteria

- The Skill passes `quick_validate.py`.
- The repository test suite passes.
- A Douyin URL is normalized and registered idempotently.
- A UTF-8 local transcript produces an `article-request.json`.
- Codex can follow `SKILL.md` to create the required Markdown article.
- Invalid articles remain retryable and record `ARTICLE_VALIDATION_FAILED`.
- Valid articles are published, indexed, marked `completed`, and their temporary directory is removed.
- No implementation or documentation claims that v0.1 downloads video, runs Whisper, performs OCR, or scans the favorites page.
- All runtime data remains outside the repository by default.
