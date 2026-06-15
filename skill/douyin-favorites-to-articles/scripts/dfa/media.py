from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from dfa.models import VideoRef

# 判定"视频不可访问"的消息特征（失效/私密/删除/不存在），其余下载错误归为准备失败。
_UNAVAILABLE_MARKERS = (
    "unavailable",
    "private",
    "deleted",
    "not available",
    "does not exist",
    "no longer",
)


class MediaError(Exception):
    """携带稳定错误码的媒体获取失败。"""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class MediaResult:
    media_path: Path
    title: str | None
    author_name: str | None
    published_at: str | None


class DownloadRunner(Protocol):
    def run(self, url: str, options: dict) -> None: ...


def build_options(workspace: Path, video_id: str, cookies_from_browser: str | None) -> dict:
    """构造 yt-dlp 选项：输出到工作目录、写 info.json，可选复用浏览器 Cookie。"""
    options: dict = {
        "outtmpl": "%(id)s.%(ext)s",
        "paths": {"home": str(workspace)},
        "writeinfojson": True,
        "quiet": True,
        "noprogress": True,
    }
    if cookies_from_browser:
        options["cookiesfrombrowser"] = (cookies_from_browser,)
    return options


def _map_error(error: Exception) -> MediaError:
    text = str(error).lower()
    if any(marker in text for marker in _UNAVAILABLE_MARKERS):
        return MediaError("SOURCE_UNAVAILABLE", f"视频不可访问：{error}")
    return MediaError("MEDIA_PREPARE_FAILED", f"媒体下载失败：{error}")


def _read_info(workspace: Path) -> dict:
    info_files = sorted(workspace.glob("*.info.json"))
    if not info_files:
        return {}
    return json.loads(info_files[0].read_text(encoding="utf-8"))


def _find_media_file(workspace: Path) -> Path | None:
    for candidate in sorted(workspace.iterdir()):
        if candidate.is_file() and not candidate.name.endswith(".json"):
            return candidate
    return None


def download_media(
    video: VideoRef,
    workspace: Path,
    *,
    runner: DownloadRunner,
    cookies_from_browser: str | None = None,
) -> MediaResult:
    """用 yt-dlp 把单条链接的媒体下载到工作目录，并解析元数据。"""
    workspace.mkdir(parents=True, exist_ok=True)
    options = build_options(workspace, video.video_id, cookies_from_browser)
    try:
        runner.run(video.source_url, options)
    except MediaError:
        raise
    except Exception as error:  # noqa: BLE001 — 统一映射为稳定错误码
        raise _map_error(error) from error

    media = _find_media_file(workspace)
    if media is None:
        raise MediaError("MEDIA_PREPARE_FAILED", "下载完成但未找到媒体文件")

    info = _read_info(workspace)
    author = info.get("uploader") or info.get("channel") or info.get("creator")
    return MediaResult(
        media_path=media,
        title=info.get("title"),
        author_name=author,
        published_at=info.get("upload_date"),
    )


class YtDlpRunner:
    """默认运行器：调用 yt-dlp 的 Python API。仅在真实下载（含集成测试）中使用。"""

    def run(self, url: str, options: dict) -> None:
        import yt_dlp

        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.download([url])
