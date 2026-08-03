from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol

from dfa.media import parse_browser_cookie_source
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
            options["cookiesfrombrowser"] = parse_browser_cookie_source(
                cookies_from_browser
            )
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
                author=entry.get("uploader")
                or entry.get("channel")
                or entry.get("creator"),
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


def write_account_manifest(
    path: Path | str,
    videos: list[AccountVideo],
    *,
    account_url: str,
    account_name: str | None = None,
    declared_count: int | None = None,
) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "account_url": account_url,
        "account_name": account_name,
        "declared_count": declared_count,
        "accessible_count": len(videos),
        "videos": [asdict(video) for video in videos],
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def read_account_manifest(
    path: Path | str,
) -> tuple[dict, list[AccountVideo]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict) or not isinstance(payload.get("videos"), list):
        raise ValueError("账户清单必须包含 videos 数组")

    videos: list[AccountVideo] = []
    seen: set[str] = set()
    for item in payload["videos"]:
        if not isinstance(item, dict):
            raise ValueError("账户清单中的视频记录必须是对象")
        source_url = normalize_source_url(str(item.get("source_url") or ""))
        video_id = str(item.get("video_id") or video_id_from_url(source_url))
        if video_id in seen:
            continue
        seen.add(video_id)
        videos.append(
            AccountVideo(
                video_id=video_id,
                source_url=source_url,
                title=item.get("title"),
                author=item.get("author"),
                published_at=item.get("published_at"),
            )
        )
    return payload, videos
