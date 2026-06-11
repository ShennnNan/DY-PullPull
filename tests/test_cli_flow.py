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


def test_prepare_strips_utf8_bom_from_transcript(tmp_path):
    data_root = tmp_path / "data"
    transcript = tmp_path / "transcript.txt"
    transcript.write_text("带 BOM 的转写文本。", encoding="utf-8-sig")

    main(["--data-root", str(data_root), "init"])
    main(["--data-root", str(data_root), "add-url", "https://www.douyin.com/video/321"])
    main(["--data-root", str(data_root), "prepare", "321", "--transcript", str(transcript)])

    request_path = data_root / "temp" / "321" / "article-request.json"
    request = json.loads(request_path.read_text(encoding="utf-8"))
    assert request["transcript"] == "带 BOM 的转写文本。"


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
