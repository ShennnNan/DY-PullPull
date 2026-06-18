from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from pullpull.pull import Collected

ENGINE_NAME = "funasr-paraformer-zh"


class ArticleMode(StrEnum):
    TRANSCRIPT = "transcript"
    SUMMARY = "summary"

# 交给 AI（代理或自动后端）的整理指令。约束：不改原意、不增删事实，只清洗与总结。
DEFAULT_INSTRUCTIONS = (
    "你在整理一段抖音视频的自动语音转写文本。请完成两件事，并只输出 JSON："
    "1) cleaned_transcript：在不改变原意、不增删事实的前提下，修正同音字、错误的英文术语"
    "（如 codes/code is → Codex、prom → prompt、三体/道德经等专有名词）、明显漏字与错误断句，"
    "保留原本的口语风格；"
    "2) summary：用简体中文要点式总结这段内容的核心信息。"
    '输出格式：{"summary": "...", "cleaned_transcript": "..."}'
)


@dataclass(frozen=True)
class RefineRequest:
    video_id: str
    title: str | None
    source_url: str
    author: str | None
    published_at: str | None
    raw_transcript: str
    instructions: str = DEFAULT_INSTRUCTIONS


@dataclass(frozen=True)
class RefinedArticle:
    summary: str | None
    cleaned_transcript: str


class Refiner(Protocol):
    """整理后端：把整理请求变成清洗原文 + 总结。代理或自动后端（Ollama/API）都实现它。"""

    def refine(self, request: RefineRequest) -> RefinedArticle: ...


def request_from_collected(collected: Collected, source_url: str) -> RefineRequest:
    media = collected.media
    return RefineRequest(
        video_id=collected.video_id,
        title=media.title,
        source_url=source_url,
        author=media.author_name,
        published_at=media.published_at,
        raw_transcript=collected.transcript,
    )


def write_request(path: Path, request: RefineRequest) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(asdict(request), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def read_request(path: Path) -> RefineRequest:
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    return RefineRequest(**data)


def parse_refined(
    data: dict, *, mode: ArticleMode = ArticleMode.SUMMARY
) -> RefinedArticle:
    """从响应 JSON 解析并校验对应模式的必填字段。"""
    cleaned = str(data.get("cleaned_transcript", "")).strip()
    if not cleaned:
        raise ValueError("响应缺少 cleaned_transcript")

    if mode is ArticleMode.TRANSCRIPT:
        return RefinedArticle(summary=None, cleaned_transcript=cleaned)

    summary = str(data.get("core_viewpoints") or data.get("summary") or "").strip()
    if not summary:
        raise ValueError("响应缺少 core_viewpoints")
    return RefinedArticle(summary=summary, cleaned_transcript=cleaned)


def render_article(
    *,
    request: RefineRequest,
    refined: RefinedArticle,
    mode: ArticleMode = ArticleMode.SUMMARY,
) -> str:
    """渲染最终文章 Markdown：来源 frontmatter + 模式化正文。"""
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


def finalize(
    out_dir: Path | str,
    request: RefineRequest,
    refined: RefinedArticle,
    *,
    mode: ArticleMode = ArticleMode.SUMMARY,
) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    article_path = out_dir / f"{request.video_id}.md"
    article_path.write_text(
        render_article(request=request, refined=refined, mode=mode), encoding="utf-8"
    )
    return article_path


def finalize_with_refiner(
    out_dir: Path | str,
    request: RefineRequest,
    refiner: Refiner,
    *,
    mode: ArticleMode = ArticleMode.SUMMARY,
) -> Path:
    """自动后端路径（P3 复用）：调用 refiner 产出整理结果再落盘。"""
    return finalize(out_dir, request, refiner.refine(request), mode=mode)
