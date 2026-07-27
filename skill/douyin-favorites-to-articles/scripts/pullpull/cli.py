from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

from pullpull.account import enumerate_account, read_account_manifest
from pullpull.article import (
    ArticleMode,
    finalize,
    parse_refined,
    read_request,
    request_from_collected,
    write_request,
)
from pullpull.batch import (
    finalize_account_video,
    prepare_account_videos,
    process_account_videos,
    rename_completed_articles,
    refine_prepared_account_videos,
)
from pullpull.pull import collect, pull
from pullpull.refine_api import DeepSeekRefiner


DEFAULT_ACCOUNT_ROOT = Path(r"D:\AI Skill\content-workspace\samples")
_INVALID_PATH_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def _safe_path_name(value: str) -> str:
    cleaned = _INVALID_PATH_CHARS.sub("_", value)
    cleaned = re.sub(r"\s+", " ", cleaned).strip().strip(".")
    return cleaned or "account"


def _account_dir_name(account_url: str, videos) -> str:
    for video in videos:
        author = getattr(video, "author", None)
        if author:
            return _safe_path_name(str(author))
    digest = hashlib.sha256(account_url.encode("utf-8")).hexdigest()[:12]
    return f"account-{digest}"


def _resolve_account_out(account_url: str, out: str | None, videos) -> Path:
    if out:
        return Path(out)
    return DEFAULT_ACCOUNT_ROOT / _account_dir_name(account_url, videos)


class AgentRefiner:
    """Configured automatic refinement backend for direct account runs."""

    def __init__(self):
        self.backend = DeepSeekRefiner.from_environment()

    def refine(self, request):
        return self.backend.refine(request)


def _cmd_pull(args) -> int:
    result = pull(
        args.url, Path(args.out), cookies_from_browser=args.cookies_from_browser
    )
    print(f"video_id: {result.video_id}")
    print(f"title:    {result.title}")
    print(f"markdown: {result.markdown_path}")
    print(f"chars:    {len(result.transcript)}")
    return 0


def _cmd_request(args) -> int:
    collected = collect(args.url, cookies_from_browser=args.cookies_from_browser)
    request = request_from_collected(collected, args.url)
    path = write_request(
        Path(args.out) / f"{request.video_id}.request.json", request
    )
    print(f"video_id: {request.video_id}")
    print(f"request:  {path}")
    print(f"chars:    {len(request.raw_transcript)}")
    print("下一步：读取该 request，写出同名 .response.json（summary + cleaned_transcript），再 finalize。")
    return 0


def _cmd_finalize(args) -> int:
    mode = ArticleMode(args.mode)
    request = read_request(Path(args.request))
    response = json.loads(Path(args.response).read_text(encoding="utf-8-sig"))
    refined = parse_refined(response, mode=mode)
    path = finalize(Path(args.out), request, refined, mode=mode)
    print(f"article:  {path}")
    return 0


def _cmd_account(args) -> int:
    mode = ArticleMode(args.mode)
    videos = enumerate_account(
        args.account_url,
        cookies_from_browser=args.cookies_from_browser,
    )
    out_dir = _resolve_account_out(args.account_url, args.out, videos)
    result = process_account_videos(
        videos,
        out_dir=out_dir,
        mode=mode,
        refiner=AgentRefiner(),
        cookies_from_browser=args.cookies_from_browser,
    )
    print(f"out: {out_dir}")
    print(f"total: {result.total}")
    print(f"completed: {result.completed}")
    print(f"skipped: {result.skipped}")
    print(f"failed: {result.failed}")
    return 0 if result.failed == 0 else 2


def _cmd_account_prepare(args) -> int:
    mode = ArticleMode(args.mode)
    _, videos = read_account_manifest(Path(args.manifest))
    if args.limit is not None:
        videos = videos[: args.limit]
    out_dir = Path(args.out) if args.out else Path(args.manifest).parent
    result = prepare_account_videos(
        videos,
        out_dir=out_dir,
        mode=mode,
        cookies_from_browser=args.cookies_from_browser,
    )
    print(f"out: {out_dir}")
    print(f"total: {result.total}")
    print(f"prepared: {result.prepared}")
    print(f"skipped: {result.skipped}")
    print(f"failed: {result.failed}")
    return 0 if result.failed == 0 else 2


def _cmd_account_finalize(args) -> int:
    path = finalize_account_video(
        out_dir=Path(args.out),
        request_path=Path(args.request),
        response_path=Path(args.response),
        mode=ArticleMode(args.mode),
    )
    print(f"article: {path}")
    return 0


def _cmd_account_refine(args) -> int:
    result = refine_prepared_account_videos(
        out_dir=Path(args.out),
        mode=ArticleMode(args.mode),
        refiner=DeepSeekRefiner.from_environment(),
        limit=args.limit,
    )
    print(f"out: {args.out}")
    print(f"total: {result.total}")
    print(f"completed: {result.completed}")
    print(f"failed: {result.failed}")
    return 0 if result.failed == 0 else 2


def _cmd_account_rename_articles(args) -> int:
    result = rename_completed_articles(Path(args.out))
    print(f"out: {args.out}")
    print(f"total: {result.total}")
    print(f"renamed: {result.renamed}")
    print(f"skipped: {result.skipped}")
    print(f"failed: {result.failed}")
    return 0 if result.failed == 0 else 2


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="pullpull：抖音链接 → 下载 → FunASR 转写 → AI 整理（原文 + 总结）",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_pull = sub.add_parser("pull", help="P1：链接 → 含转写的 md")
    p_pull.add_argument("url", help="抖音视频分享链接")
    p_pull.add_argument("--out", default="./articles", help="输出目录（默认 ./articles）")
    p_pull.add_argument("--cookies-from-browser", default=None, help="复用浏览器登录态，如 chrome / edge")
    p_pull.set_defaults(func=_cmd_pull)

    p_req = sub.add_parser("request", help="P2-A：链接 → 下载转写 → 整理请求 json")
    p_req.add_argument("url", help="抖音视频分享链接")
    p_req.add_argument("--out", default="./articles", help="输出目录（默认 ./articles）")
    p_req.add_argument("--cookies-from-browser", default=None, help="复用浏览器登录态，如 chrome / edge")
    p_req.set_defaults(func=_cmd_request)

    p_fin = sub.add_parser("finalize", help="P2-B：整理请求 + 响应 → 文章 md（原文 + 总结）")
    p_fin.add_argument("request", help="<id>.request.json 路径")
    p_fin.add_argument("response", help="<id>.response.json 路径（summary + cleaned_transcript）")
    p_fin.add_argument(
        "--mode",
        choices=[mode.value for mode in ArticleMode],
        default=ArticleMode.SUMMARY.value,
        help="transcript=顺畅原文；summary=核心观点+顺畅原文",
    )
    p_fin.add_argument("--out", default="./articles", help="输出目录（默认 ./articles）")
    p_fin.set_defaults(func=_cmd_finalize)

    p_account = sub.add_parser("account", help="账号主页 → 批量处理视频")
    p_account.add_argument("account_url", help="抖音账号主页链接")
    p_account.add_argument(
        "--mode",
        choices=[mode.value for mode in ArticleMode],
        default=ArticleMode.TRANSCRIPT.value,
        help="transcript=顺畅原文；summary=核心观点+顺畅原文",
    )
    p_account.add_argument(
        "--out",
        default=None,
        help=r"输出目录（默认 D:\AI Skill\content-workspace\samples\<账号名>）",
    )
    p_account.add_argument(
        "--cookies-from-browser",
        default=None,
        help="复用浏览器登录态，如 chrome / edge",
    )
    p_account.set_defaults(func=_cmd_account)

    p_account_prepare = sub.add_parser(
        "account-prepare",
        help="账户清单 → 批量下载转写 → 整理请求",
    )
    p_account_prepare.add_argument("manifest", help="account-manifest.json 路径")
    p_account_prepare.add_argument(
        "--mode",
        choices=[mode.value for mode in ArticleMode],
        default=ArticleMode.SUMMARY.value,
        help="transcript=顺畅原文；summary=核心观点+顺畅原文",
    )
    p_account_prepare.add_argument(
        "--out",
        default=None,
        help="输出目录（默认使用 manifest 所在目录）",
    )
    p_account_prepare.add_argument(
        "--limit",
        type=int,
        default=None,
        help="仅处理清单前 N 条，用于样本验收",
    )
    p_account_prepare.add_argument(
        "--cookies-from-browser",
        default=None,
        help=r"浏览器或 browser:profile，例如 edge:D:\profile",
    )
    p_account_prepare.set_defaults(func=_cmd_account_prepare)

    p_account_finalize = sub.add_parser(
        "account-finalize",
        help="账户整理请求 + AI 响应 → Markdown + index.json",
    )
    p_account_finalize.add_argument("request", help="*.request.json 路径")
    p_account_finalize.add_argument("response", help="*.response.json 路径")
    p_account_finalize.add_argument(
        "--mode",
        choices=[mode.value for mode in ArticleMode],
        default=ArticleMode.SUMMARY.value,
    )
    p_account_finalize.add_argument("--out", required=True, help="账户归档目录")
    p_account_finalize.set_defaults(func=_cmd_account_finalize)

    p_account_refine = sub.add_parser(
        "account-refine",
        help="用 DeepSeek 批量清洗已准备的转写并定稿",
    )
    p_account_refine.add_argument("--out", required=True, help="账户归档目录")
    p_account_refine.add_argument(
        "--mode",
        choices=[mode.value for mode in ArticleMode],
        default=ArticleMode.SUMMARY.value,
    )
    p_account_refine.add_argument("--limit", type=int, default=None)
    p_account_refine.set_defaults(func=_cmd_account_refine)

    p_account_rename = sub.add_parser(
        "account-rename-articles",
        help="把已完成文章从视频 ID 文件名迁移为标题文件名",
    )
    p_account_rename.add_argument("--out", required=True, help="账户归档目录")
    p_account_rename.set_defaults(func=_cmd_account_rename_articles)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
