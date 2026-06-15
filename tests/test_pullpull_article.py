import json
from pathlib import Path

import pytest

from dfa.media import MediaResult
from pullpull.article import (
    RefinedArticle,
    RefineRequest,
    finalize,
    finalize_with_refiner,
    parse_refined,
    read_request,
    render_article,
    request_from_collected,
    write_request,
)
from pullpull.pull import Collected

URL = "https://www.douyin.com/video/123"


def _request(**overrides):
    base = dict(
        video_id="123",
        title="标题",
        source_url=URL,
        author="作者",
        published_at="20260616",
        raw_transcript="codes 很强 prom 也好",
    )
    base.update(overrides)
    return RefineRequest(**base)


def test_request_from_collected_pulls_metadata():
    media = MediaResult(Path("123.mp4"), "标题", "作者", "20260616")
    collected = Collected(video_id="123", media=media, transcript="原始转写")

    request = request_from_collected(collected, URL)

    assert request.video_id == "123"
    assert request.author == "作者"
    assert request.published_at == "20260616"
    assert request.raw_transcript == "原始转写"
    assert request.instructions  # 带默认整理指令


def test_request_roundtrip(tmp_path):
    request = _request()
    path = write_request(tmp_path / "123.request.json", request)

    assert read_request(path) == request


def test_parse_refined_valid():
    refined = parse_refined(
        {"summary": "要点", "cleaned_transcript": "清洗后的原文"}
    )
    assert refined == RefinedArticle("要点", "清洗后的原文")


@pytest.mark.parametrize(
    "payload",
    [
        {"cleaned_transcript": "只有原文"},
        {"summary": "只有总结"},
        {"summary": "  ", "cleaned_transcript": "x"},
        {},
    ],
)
def test_parse_refined_rejects_incomplete(payload):
    with pytest.raises(ValueError):
        parse_refined(payload)


def test_render_article_has_summary_then_transcript():
    md = render_article(
        request=_request(),
        refined=RefinedArticle("这是总结", "这是清洗后的原文"),
    )
    assert "## 总结" in md
    assert "## 原文" in md
    assert md.index("## 总结") < md.index("## 原文")
    assert "这是总结" in md
    assert "这是清洗后的原文" in md
    assert "video_id: 123" in md
    assert "refined_by: agent" in md


def test_finalize_writes_article(tmp_path):
    path = finalize(
        tmp_path / "articles",
        _request(),
        RefinedArticle("总结", "原文"),
    )
    assert path.name == "123.md"
    body = path.read_text(encoding="utf-8")
    assert "总结" in body and "原文" in body


def test_finalize_with_refiner_uses_backend(tmp_path):
    class FakeRefiner:
        def refine(self, request):
            assert request.video_id == "123"
            return RefinedArticle("自动总结", "自动清洗：Codex 很强 prompt 也好")

    path = finalize_with_refiner(tmp_path / "articles", _request(), FakeRefiner())

    body = path.read_text(encoding="utf-8")
    assert "自动总结" in body
    assert "Codex 很强 prompt 也好" in body
