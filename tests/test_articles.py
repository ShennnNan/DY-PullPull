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
