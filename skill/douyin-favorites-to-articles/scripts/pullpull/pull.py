from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

from dfa.media import DownloadRunner, MediaResult, YtDlpRunner, download_media
from dfa.models import VideoRef
from dfa.urls import video_id_from_url

from pullpull.filenames import article_path_for
from pullpull.transcribe import FunasrTranscriber, Transcriber

ENGINE_NAME = "funasr-paraformer-zh"


@dataclass(frozen=True)
class Collected:
    """一次下载+转写的结果（不落盘），供 P1 写原文 md 或 P2 构造整理请求复用。"""

    video_id: str
    media: MediaResult
    transcript: str


@dataclass(frozen=True)
class PullResult:
    video_id: str
    title: str | None
    transcript: str
    markdown_path: Path


def collect(
    source_url: str,
    *,
    runner: DownloadRunner | None = None,
    transcriber: Transcriber | None = None,
    cookies_from_browser: str | None = None,
) -> Collected:
    """下载 + 转写单条链接，临时媒体用后即删，返回内存中的结果。"""
    runner = runner or YtDlpRunner()
    transcriber = transcriber or FunasrTranscriber()

    provisional_id = video_id_from_url(source_url)
    with tempfile.TemporaryDirectory(prefix="pullpull-") as tmp:
        workspace = Path(tmp)
        video = VideoRef(video_id=provisional_id, source_url=source_url)
        media = download_media(
            video,
            workspace,
            runner=runner,
            cookies_from_browser=cookies_from_browser,
        )
        # yt-dlp 用真实视频 ID 命名媒体文件，以它作为产物的稳定 ID。
        video_id = media.media_path.stem
        transcript = transcriber.transcribe(media.media_path)

    return Collected(video_id=video_id, media=media, transcript=transcript)


def render_markdown(
    *,
    video_id: str,
    source_url: str,
    media: MediaResult,
    transcript: str,
) -> str:
    """渲染 P1 的原文 Markdown：来源 frontmatter + 标题 + 转写原文。

    总结（## 总结）属于 P2，由 article.render_article 产出。
    """
    title = media.title or video_id
    lines = [
        "---",
        f"video_id: {video_id}",
        f"source_url: {source_url}",
        f"title: {title}",
        f"author: {media.author_name or ''}",
        f"published_at: {media.published_at or ''}",
        f"engine: {ENGINE_NAME}",
        "---",
        "",
        f"# {title}",
        "",
        "## 原文",
        "",
        transcript,
        "",
    ]
    return "\n".join(lines)


def pull(
    source_url: str,
    out_dir: Path | str,
    *,
    runner: DownloadRunner | None = None,
    transcriber: Transcriber | None = None,
    cookies_from_browser: str | None = None,
) -> PullResult:
    """P1 单条闭环：下载 → 转写 → 写一份原文 Markdown。"""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    collected = collect(
        source_url,
        runner=runner,
        transcriber=transcriber,
        cookies_from_browser=cookies_from_browser,
    )

    markdown_path = article_path_for(
        out_dir,
        collected.media.title,
        collected.video_id,
    )
    markdown_path.write_text(
        render_markdown(
            video_id=collected.video_id,
            source_url=source_url,
            media=collected.media,
            transcript=collected.transcript,
        ),
        encoding="utf-8",
    )
    return PullResult(
        video_id=collected.video_id,
        title=collected.media.title,
        transcript=collected.transcript,
        markdown_path=markdown_path,
    )
