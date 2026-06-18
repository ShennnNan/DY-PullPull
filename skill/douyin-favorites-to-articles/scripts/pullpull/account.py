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
