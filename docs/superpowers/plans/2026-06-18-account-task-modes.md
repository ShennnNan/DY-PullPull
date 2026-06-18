# Account Task Modes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build account-level Douyin archiving with two modes: `transcript` for AI-cleaned readable transcripts, and `summary` for core viewpoints plus AI-cleaned transcripts.

**Architecture:** Reuse the existing single-video `pullpull.pull.collect()` pipeline for download and ASR. Add focused modules for article modes, account enumeration, and batch execution with an index file for skip/resume. Keep AI behind the existing `Refiner` protocol so the batch runner can be tested with fake refiners and later connected to an automatic or agent-backed refiner.

**Tech Stack:** Python 3.11+, argparse, dataclasses, JSON files, yt-dlp Python API, pytest, existing `pullpull` and `dfa` modules.

---

## File Structure

- Modify `skill/douyin-favorites-to-articles/scripts/pullpull/article.py`
  - Add `ArticleMode`.
  - Allow transcript-only AI cleanup without requiring a summary.
  - Render `## 原文` for `transcript` and `## 核心观点` + `## 原文` for `summary`.
- Create `skill/douyin-favorites-to-articles/scripts/pullpull/account.py`
  - Enumerate account videos through an injectable yt-dlp runner.
  - Normalize account playlist entries into video URLs.
- Create `skill/douyin-favorites-to-articles/scripts/pullpull/batch.py`
  - Maintain `index.json`.
  - Process videos one by one through collect + refine + finalize.
  - Skip completed videos for the selected mode.
  - Record per-video failures.
- Modify `skill/douyin-favorites-to-articles/scripts/pullpull/cli.py`
  - Add `account <url> --mode transcript|summary --out ... --cookies-from-browser ...`.
- Modify `skill/douyin-favorites-to-articles/SKILL.md`
  - Document the two account modes and the current AI boundary.
- Test `tests/test_pullpull_article.py`
  - Update article-mode parsing and rendering tests.
- Create `tests/test_pullpull_account.py`
  - Test account enumeration from fake yt-dlp playlist entries.
- Create `tests/test_pullpull_batch.py`
  - Test skip/resume, failures, and per-mode Markdown outputs.
- Modify `tests/test_cli_v2_flow.py`
  - Test CLI argument wiring for `account`.

---

### Task 1: Article Modes And Rendering

**Files:**
- Modify: `skill/douyin-favorites-to-articles/scripts/pullpull/article.py`
- Test: `tests/test_pullpull_article.py`

- [ ] **Step 1: Write failing tests for transcript and summary parsing**

Add these imports in `tests/test_pullpull_article.py`:

```python
from pullpull.article import ArticleMode
```

Add these tests near the current `parse_refined` tests:

```python
def test_parse_transcript_refined_accepts_cleaned_only():
    refined = parse_refined(
        {"cleaned_transcript": "清洗后的顺畅原文"},
        mode=ArticleMode.TRANSCRIPT,
    )

    assert refined.summary is None
    assert refined.cleaned_transcript == "清洗后的顺畅原文"


def test_parse_summary_refined_accepts_core_viewpoints():
    refined = parse_refined(
        {"core_viewpoints": "第一，核心观点。第二，结论。", "cleaned_transcript": "顺畅原文"},
        mode=ArticleMode.SUMMARY,
    )

    assert refined.summary == "第一，核心观点。第二，结论。"
    assert refined.cleaned_transcript == "顺畅原文"


def test_parse_summary_refined_accepts_legacy_summary_key():
    refined = parse_refined(
        {"summary": "旧字段总结", "cleaned_transcript": "顺畅原文"},
        mode=ArticleMode.SUMMARY,
    )

    assert refined.summary == "旧字段总结"
    assert refined.cleaned_transcript == "顺畅原文"
```

Replace the existing incomplete payload parametrization with:

```python
@pytest.mark.parametrize(
    "payload, mode",
    [
        ({}, ArticleMode.TRANSCRIPT),
        ({"cleaned_transcript": "  "}, ArticleMode.TRANSCRIPT),
        ({"cleaned_transcript": "只有原文"}, ArticleMode.SUMMARY),
        ({"summary": "只有总结"}, ArticleMode.SUMMARY),
        ({"core_viewpoints": "只有观点"}, ArticleMode.SUMMARY),
        ({"summary": "  ", "cleaned_transcript": "x"}, ArticleMode.SUMMARY),
    ],
)
def test_parse_refined_rejects_incomplete(payload, mode):
    with pytest.raises(ValueError):
        parse_refined(payload, mode=mode)
```

- [ ] **Step 2: Run article tests and verify they fail**

Run:

```powershell
& '.\.venv\Scripts\python.exe' -m pytest tests\test_pullpull_article.py -q
```

Expected: FAIL because `ArticleMode` and `parse_refined(..., mode=...)` do not exist.

- [ ] **Step 3: Implement article mode model**

In `skill/douyin-favorites-to-articles/scripts/pullpull/article.py`, add:

```python
from enum import StrEnum
```

Add below `ENGINE_NAME`:

```python
class ArticleMode(StrEnum):
    TRANSCRIPT = "transcript"
    SUMMARY = "summary"
```

Change `RefinedArticle` to allow a transcript-only article:

```python
@dataclass(frozen=True)
class RefinedArticle:
    summary: str | None
    cleaned_transcript: str
```

Replace `parse_refined` with:

```python
def parse_refined(data: dict, *, mode: ArticleMode = ArticleMode.SUMMARY) -> RefinedArticle:
    """Parse AI output for transcript or summary mode."""
    cleaned = str(data.get("cleaned_transcript", "")).strip()
    if not cleaned:
        raise ValueError("响应缺少 cleaned_transcript")

    if mode is ArticleMode.TRANSCRIPT:
        return RefinedArticle(summary=None, cleaned_transcript=cleaned)

    summary = str(data.get("core_viewpoints") or data.get("summary") or "").strip()
    if not summary:
        raise ValueError("响应缺少 core_viewpoints")
    return RefinedArticle(summary=summary, cleaned_transcript=cleaned)
```

- [ ] **Step 4: Add rendering tests for both modes**

In `tests/test_pullpull_article.py`, replace `test_render_article_has_summary_then_transcript` with:

```python
def test_render_transcript_article_has_only_cleaned_transcript():
    md = render_article(
        request=_request(),
        refined=RefinedArticle(None, "这是清洗后的原文"),
        mode=ArticleMode.TRANSCRIPT,
    )

    assert "## 核心观点" not in md
    assert "## 总结" not in md
    assert "## 原文" in md
    assert "这是清洗后的原文" in md
    assert "mode: transcript" in md
    assert "video_id: 123" in md


def test_render_summary_article_has_core_viewpoints_then_transcript():
    md = render_article(
        request=_request(),
        refined=RefinedArticle("这是核心观点", "这是清洗后的原文"),
        mode=ArticleMode.SUMMARY,
    )

    assert "## 核心观点" in md
    assert "## 原文" in md
    assert md.index("## 核心观点") < md.index("## 原文")
    assert "这是核心观点" in md
    assert "这是清洗后的原文" in md
    assert "mode: summary" in md
    assert "refined_by: agent" in md
```

- [ ] **Step 5: Implement rendering by mode**

Change `render_article` signature:

```python
def render_article(
    *,
    request: RefineRequest,
    refined: RefinedArticle,
    mode: ArticleMode = ArticleMode.SUMMARY,
) -> str:
```

Replace its body with:

```python
    title = request.title or request.video_id
    lines = [
        "---",
        f"video_id: {request.video_id}",
        f"source_url: {request.source_url}",
        f"title: {title}",
        f"author: {request.author or ''}",
        f"published_at: {request.published_at or ''}",
        f"engine: {ENGINE_NAME}",
        f"mode: {mode.value}",
        "refined_by: agent",
        "---",
        "",
        f"# {title}",
        "",
    ]
    if mode is ArticleMode.SUMMARY:
        if not refined.summary:
            raise ValueError("summary mode requires core viewpoints")
        lines.extend(["## 核心观点", "", refined.summary, ""])
    lines.extend(["## 原文", "", refined.cleaned_transcript, ""])
    return "\n".join(lines)
```

Change `finalize` signature and call:

```python
def finalize(
    out_dir: Path | str,
    request: RefineRequest,
    refined: RefinedArticle,
    *,
    mode: ArticleMode = ArticleMode.SUMMARY,
) -> Path:
```

Inside `finalize`, call:

```python
render_article(request=request, refined=refined, mode=mode)
```

Change `finalize_with_refiner` signature and call:

```python
def finalize_with_refiner(
    out_dir: Path | str,
    request: RefineRequest,
    refiner: Refiner,
    *,
    mode: ArticleMode = ArticleMode.SUMMARY,
) -> Path:
    return finalize(out_dir, request, refiner.refine(request), mode=mode)
```

- [ ] **Step 6: Update existing article tests for the new dataclass**

Replace existing `RefinedArticle("总结", "原文")` calls with:

```python
RefinedArticle("总结", "原文")
```

Keep positional calls valid because the first field remains `summary`. Update assertions that look for `## 总结` to look for `## 核心观点`.

- [ ] **Step 7: Run article tests**

Run:

```powershell
& '.\.venv\Scripts\python.exe' -m pytest tests\test_pullpull_article.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit Task 1**

Run:

```powershell
git add -- skill/douyin-favorites-to-articles/scripts/pullpull/article.py tests/test_pullpull_article.py
git commit -m "feat: support transcript and summary article modes"
```

---

### Task 2: Account Video Enumeration

**Files:**
- Create: `skill/douyin-favorites-to-articles/scripts/pullpull/account.py`
- Test: `tests/test_pullpull_account.py`

- [ ] **Step 1: Write failing enumeration tests**

Create `tests/test_pullpull_account.py`:

```python
from pullpull.account import AccountVideo, YtDlpAccountEnumerator, enumerate_account


class FakePlaylistRunner:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def extract_info(self, url, options):
        self.calls.append((url, options))
        return self.payload


def test_enumerate_account_normalizes_entries_to_video_refs():
    runner = FakePlaylistRunner(
        {
            "entries": [
                {
                    "id": "111",
                    "url": "https://www.douyin.com/video/111?previous_page=x",
                    "title": "第一条",
                    "uploader": "作者",
                    "upload_date": "20260618",
                },
                {
                    "id": "222",
                    "webpage_url": "https://www.douyin.com/video/222",
                    "title": "第二条",
                    "creator": "作者",
                },
            ]
        }
    )

    videos = enumerate_account("https://www.douyin.com/user/MS4wLjAB", runner=runner)

    assert videos == [
        AccountVideo(
            video_id="111",
            source_url="https://www.douyin.com/video/111",
            title="第一条",
            author="作者",
            published_at="20260618",
        ),
        AccountVideo(
            video_id="222",
            source_url="https://www.douyin.com/video/222",
            title="第二条",
            author="作者",
            published_at=None,
        ),
    ]
    assert runner.calls[0][1]["extract_flat"] == "in_playlist"
    assert runner.calls[0][1]["skip_download"] is True


def test_enumerate_account_deduplicates_entries():
    runner = FakePlaylistRunner(
        {
            "entries": [
                {"id": "111", "url": "https://www.douyin.com/video/111"},
                {"id": "111", "url": "https://www.douyin.com/video/111?x=1"},
            ]
        }
    )

    videos = enumerate_account("https://www.douyin.com/user/MS4wLjAB", runner=runner)

    assert [video.video_id for video in videos] == ["111"]


def test_enumerator_passes_browser_cookies():
    runner = FakePlaylistRunner({"entries": []})

    YtDlpAccountEnumerator(runner=runner).enumerate(
        "https://www.douyin.com/user/MS4wLjAB",
        cookies_from_browser="chrome",
    )

    assert runner.calls[0][1]["cookiesfrombrowser"] == ("chrome",)
```

- [ ] **Step 2: Run enumeration tests and verify they fail**

Run:

```powershell
& '.\.venv\Scripts\python.exe' -m pytest tests\test_pullpull_account.py -q
```

Expected: FAIL because `pullpull.account` does not exist.

- [ ] **Step 3: Implement account enumeration module**

Create `skill/douyin-favorites-to-articles/scripts/pullpull/account.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from dfa.urls import normalize_source_url, video_id_from_url


@dataclass(frozen=True)
class AccountVideo:
    video_id: str
    source_url: str
    title: str | None = None
    author: str | None = None
    published_at: str | None = None


class PlaylistRunner(Protocol):
    def extract_info(self, url: str, options: dict) -> dict: ...


class YtDlpPlaylistRunner:
    def extract_info(self, url: str, options: dict) -> dict:
        import yt_dlp

        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
        return info or {}


class YtDlpAccountEnumerator:
    def __init__(self, runner: PlaylistRunner | None = None):
        self.runner = runner or YtDlpPlaylistRunner()

    def enumerate(
        self,
        account_url: str,
        *,
        cookies_from_browser: str | None = None,
    ) -> list[AccountVideo]:
        options: dict = {
            "extract_flat": "in_playlist",
            "skip_download": True,
            "quiet": True,
            "noprogress": True,
        }
        if cookies_from_browser:
            options["cookiesfrombrowser"] = (cookies_from_browser,)
        info = self.runner.extract_info(account_url, options)
        return _videos_from_playlist(info)


def _entry_url(entry: dict) -> str | None:
    raw = entry.get("webpage_url") or entry.get("url")
    if raw:
        value = str(raw)
        if value.startswith("http"):
            return value
    entry_id = str(entry.get("id") or "").strip()
    if entry_id.isdigit():
        return f"https://www.douyin.com/video/{entry_id}"
    return None


def _videos_from_playlist(info: dict) -> list[AccountVideo]:
    videos: list[AccountVideo] = []
    seen: set[str] = set()
    for entry in info.get("entries") or []:
        if not isinstance(entry, dict):
            continue
        raw_url = _entry_url(entry)
        if not raw_url:
            continue
        source_url = normalize_source_url(raw_url)
        video_id = video_id_from_url(source_url)
        if video_id in seen:
            continue
        seen.add(video_id)
        videos.append(
            AccountVideo(
                video_id=video_id,
                source_url=source_url,
                title=entry.get("title"),
                author=entry.get("uploader") or entry.get("channel") or entry.get("creator"),
                published_at=entry.get("upload_date"),
            )
        )
    return videos


def enumerate_account(
    account_url: str,
    *,
    runner: PlaylistRunner | None = None,
    cookies_from_browser: str | None = None,
) -> list[AccountVideo]:
    return YtDlpAccountEnumerator(runner=runner).enumerate(
        account_url,
        cookies_from_browser=cookies_from_browser,
    )
```

- [ ] **Step 4: Run enumeration tests**

Run:

```powershell
& '.\.venv\Scripts\python.exe' -m pytest tests\test_pullpull_account.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 2**

Run:

```powershell
git add -- skill/douyin-favorites-to-articles/scripts/pullpull/account.py tests/test_pullpull_account.py
git commit -m "feat: enumerate douyin account videos"
```

---

### Task 3: Batch Processing And Resume Index

**Files:**
- Create: `skill/douyin-favorites-to-articles/scripts/pullpull/batch.py`
- Test: `tests/test_pullpull_batch.py`

- [ ] **Step 1: Write failing batch tests**

Create `tests/test_pullpull_batch.py`:

```python
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
        media = MediaResult(Path(f"{video_id}.mp4"), f"标题{video_id}", "作者", "20260618")
        return Collected(video_id=video_id, media=media, transcript=self.transcripts[video_id])


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
        AccountVideo("111", "https://www.douyin.com/video/111", "标题111", "作者", "20260618"),
        AccountVideo("222", "https://www.douyin.com/video/222", "标题222", "作者", "20260618"),
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

    assert result == BatchResult(total=2, completed=2, skipped=0, failed=0)
    assert (tmp_path / "111.md").read_text(encoding="utf-8").count("## 原文") == 1
    assert "## 核心观点" not in (tmp_path / "111.md").read_text(encoding="utf-8")
    assert "顺畅原文 原始一" in (tmp_path / "111.md").read_text(encoding="utf-8")
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
```

- [ ] **Step 2: Run batch tests and verify they fail**

Run:

```powershell
& '.\.venv\Scripts\python.exe' -m pytest tests\test_pullpull_batch.py -q
```

Expected: FAIL because `pullpull.batch` does not exist.

- [ ] **Step 3: Implement batch module**

Create `skill/douyin-favorites-to-articles/scripts/pullpull/batch.py`:

```python
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
    def collect(self, url: str, *, cookies_from_browser: str | None = None) -> Collected: ...


class DefaultCollector:
    def collect(self, url: str, *, cookies_from_browser: str | None = None) -> Collected:
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
    return bool(record and record.get("status") == "completed" and record.get("mode") == mode.value)


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
            write_request(requests_dir / f"{request.video_id}.{mode.value}.request.json", request)
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
```

- [ ] **Step 4: Run batch tests**

Run:

```powershell
& '.\.venv\Scripts\python.exe' -m pytest tests\test_pullpull_batch.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 3**

Run:

```powershell
git add -- skill/douyin-favorites-to-articles/scripts/pullpull/batch.py tests/test_pullpull_batch.py
git commit -m "feat: process account videos with resumable index"
```

---

### Task 4: CLI Account Command

**Files:**
- Modify: `skill/douyin-favorites-to-articles/scripts/pullpull/cli.py`
- Test: `tests/test_cli_v2_flow.py`

- [ ] **Step 1: Write failing CLI test**

Append to `tests/test_cli_v2_flow.py`:

```python
from pullpull.article import ArticleMode


def test_account_command_enumerates_and_processes(monkeypatch, tmp_path, capsys):
    calls = {}

    def fake_enumerate(account_url, *, cookies_from_browser=None):
        calls["account_url"] = account_url
        calls["cookies"] = cookies_from_browser
        return ["video-a", "video-b"]

    class FakeRefiner:
        def refine(self, request):
            raise AssertionError("batch fake should receive refiner but not call it")

    def fake_process(videos, *, out_dir, mode, refiner, collector=None, cookies_from_browser=None):
        calls["videos"] = videos
        calls["out_dir"] = out_dir
        calls["mode"] = mode
        calls["batch_cookies"] = cookies_from_browser
        calls["refiner_type"] = type(refiner).__name__
        from pullpull.batch import BatchResult
        return BatchResult(total=2, completed=2, skipped=0, failed=0)

    import pullpull.cli as cli_module

    monkeypatch.setattr(cli_module, "enumerate_account", fake_enumerate)
    monkeypatch.setattr(cli_module, "AgentRefiner", FakeRefiner)
    monkeypatch.setattr(cli_module, "process_account_videos", fake_process)

    result = cli_module.main(
        [
            "account",
            "https://www.douyin.com/user/MS4wLjAB",
            "--mode",
            "summary",
            "--out",
            str(tmp_path),
            "--cookies-from-browser",
            "chrome",
        ]
    )

    assert result == 0
    assert calls["mode"] is ArticleMode.SUMMARY
    assert calls["cookies"] == "chrome"
    assert calls["batch_cookies"] == "chrome"
    assert calls["videos"] == ["video-a", "video-b"]
    output = capsys.readouterr().out
    assert "total: 2" in output
    assert "completed: 2" in output
```

- [ ] **Step 2: Run CLI test and verify it fails**

Run:

```powershell
& '.\.venv\Scripts\python.exe' -m pytest tests\test_cli_v2_flow.py::test_account_command_enumerates_and_processes -q
```

Expected: FAIL because the CLI has no `account` command and no `AgentRefiner`.

- [ ] **Step 3: Add an agent-backed refiner boundary**

In `skill/douyin-favorites-to-articles/scripts/pullpull/cli.py`, add imports:

```python
from pullpull.account import enumerate_account
from pullpull.article import ArticleMode, RefinedArticle
from pullpull.batch import process_account_videos
```

Add this class above `_cmd_pull`:

```python
class AgentRefiner:
    """Explicit boundary for Codex/agent refinement during batch runs.

    Batch logic must call a Refiner and must fail loudly when no AI cleanup
    backend is connected, because raw ASR text is not a valid final article.
    """

    def refine(self, request):
        raise RuntimeError(
            "AI refinement backend is not connected. Use request/finalize flow or provide an automatic Refiner."
        )
```

This class is intentionally explicit: it prevents silent publication of raw ASR text when the AI step is not wired.

- [ ] **Step 4: Add CLI account command**

Add:

```python
def _cmd_account(args) -> int:
    mode = ArticleMode(args.mode)
    videos = enumerate_account(
        args.account_url,
        cookies_from_browser=args.cookies_from_browser,
    )
    result = process_account_videos(
        videos,
        out_dir=Path(args.out),
        mode=mode,
        refiner=AgentRefiner(),
        cookies_from_browser=args.cookies_from_browser,
    )
    print(f"total: {result.total}")
    print(f"completed: {result.completed}")
    print(f"skipped: {result.skipped}")
    print(f"failed: {result.failed}")
    return 0 if result.failed == 0 else 2
```

In `main`, add this parser before `args = parser.parse_args(argv)`:

```python
    p_account = sub.add_parser("account", help="账号主页 → 批量处理视频")
    p_account.add_argument("account_url", help="抖音账号主页链接")
    p_account.add_argument(
        "--mode",
        choices=[mode.value for mode in ArticleMode],
        default=ArticleMode.TRANSCRIPT.value,
        help="transcript=顺畅原文；summary=核心观点+顺畅原文",
    )
    p_account.add_argument("--out", default="./articles", help="输出目录（默认 ./articles）")
    p_account.add_argument("--cookies-from-browser", default=None, help="复用浏览器登录态，如 chrome / edge")
    p_account.set_defaults(func=_cmd_account)
```

- [ ] **Step 5: Run CLI test**

Run:

```powershell
& '.\.venv\Scripts\python.exe' -m pytest tests\test_cli_v2_flow.py::test_account_command_enumerates_and_processes -q
```

Expected: PASS.

- [ ] **Step 6: Commit Task 4**

Run:

```powershell
git add -- skill/douyin-favorites-to-articles/scripts/pullpull/cli.py tests/test_cli_v2_flow.py
git commit -m "feat: add account batch cli command"
```

---

### Task 5: Skill Documentation And Full Test Run

**Files:**
- Modify: `skill/douyin-favorites-to-articles/SKILL.md`
- Optional after tests: `docs/WORKLOG.md`

- [ ] **Step 1: Update skill documentation**

In `skill/douyin-favorites-to-articles/SKILL.md`, add a section after "单链接自动流程（推荐）":

```markdown
## 账号批量流程

账号批量用于处理某个抖音账号下可枚举的视频：

```powershell
& $PYTHON "$SKILL_ROOT\scripts\pullpull_cli.py" account <账号主页URL> --mode transcript
& $PYTHON "$SKILL_ROOT\scripts\pullpull_cli.py" account <账号主页URL> --mode summary
```

- `transcript`：ASR 后用 AI 清洗错字、错句和断句，最终文章只输出 `## 原文`。
- `summary`：在 `transcript` 基础上总结核心观点，最终文章输出 `## 核心观点` 和 `## 原文`。
- 默认模式是 `transcript`。
- 批量任务会写 `index.json` 用于去重和断点续跑。
- 需要登录态时使用 `--cookies-from-browser chrome`，只处理用户本人合法可访问的内容。

当前 CLI 已保留 AI Refiner 边界。若未连接自动 AI 后端，批量流程会明确失败，不会把未经 AI 清洗的 ASR 原文伪装成最终文章。
```

- [ ] **Step 2: Run focused tests**

Run:

```powershell
& '.\.venv\Scripts\python.exe' -m pytest tests\test_pullpull_article.py tests\test_pullpull_account.py tests\test_pullpull_batch.py tests\test_cli_v2_flow.py -q
```

Expected: PASS.

- [ ] **Step 3: Run full test suite**

Run:

```powershell
& '.\.venv\Scripts\python.exe' -m pytest -q
```

Expected: PASS.

- [ ] **Step 4: Check CLI help**

Run:

```powershell
& '.\.venv\Scripts\python.exe' 'skill\douyin-favorites-to-articles\scripts\pullpull_cli.py' account --help
```

Expected output includes:

```text
--mode {transcript,summary}
--cookies-from-browser
```

- [ ] **Step 5: Commit Task 5**

Run:

```powershell
git add -- skill/douyin-favorites-to-articles/SKILL.md docs/WORKLOG.md
git commit -m "docs: document account task modes"
```

If `docs/WORKLOG.md` was not changed, run:

```powershell
git add -- skill/douyin-favorites-to-articles/SKILL.md
git commit -m "docs: document account task modes"
```

---

## Self-Review

Spec coverage:

- Two modes are covered in Task 1 and Task 4.
- Transcript mode produces cleaned `## 原文` through Task 1 and Task 3.
- Summary mode produces `## 核心观点` plus cleaned `## 原文` through Task 1 and Task 3.
- Intermediate request files are covered in Task 3 via `.requests/<video>.<mode>.request.json`.
- Account enumeration is covered in Task 2.
- Deduplication, resume, and per-video failures are covered in Task 3.
- CLI shape is covered in Task 4.
- Skill documentation is covered in Task 5.

Known implementation boundary:

- This plan wires the AI step through the existing `Refiner` protocol and makes the CLI fail clearly if no automatic refiner is connected. That preserves the user's requirement that final articles must be AI-cleaned and prevents accidental raw ASR output. A follow-up implementation can replace `AgentRefiner` with an OpenAI, local model, or Codex-agent file workflow while keeping the batch/index code unchanged.
