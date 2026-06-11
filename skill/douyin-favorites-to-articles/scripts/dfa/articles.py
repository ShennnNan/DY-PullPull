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
