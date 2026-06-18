from __future__ import annotations

import argparse
import json
from pathlib import Path

from pullpull.account import enumerate_account
from pullpull.article import (
    ArticleMode,
    finalize,
    parse_refined,
    read_request,
    request_from_collected,
    write_request,
)
from pullpull.batch import process_account_videos
from pullpull.pull import collect, pull


class AgentRefiner:
    """Explicit boundary for Codex/agent refinement during batch runs.

    Batch logic must call a Refiner and must fail loudly when no AI cleanup
    backend is connected, because raw ASR text is not a valid final article.
    """

    def refine(self, request):
        raise RuntimeError(
            "AI refinement backend is not connected. Use request/finalize flow "
            "or provide an automatic Refiner."
        )


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
    request = read_request(Path(args.request))
    response = json.loads(Path(args.response).read_text(encoding="utf-8-sig"))
    refined = parse_refined(response)
    path = finalize(Path(args.out), request, refined)
    print(f"article:  {path}")
    return 0


def _cmd_account(args) -> int:
    mode = ArticleMode(args.mode)
    videos = enumerate_account(
        args.account_url,
        cookies_from_browser=args.cookies_from_browser,
    )
    result = process_account_videos(
        videos,
        out_dir=Path(args.out),
        mode=mode,
        refiner=AgentRefiner(),
        cookies_from_browser=args.cookies_from_browser,
    )
    print(f"total: {result.total}")
    print(f"completed: {result.completed}")
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
    p_account.add_argument("--out", default="./articles", help="输出目录（默认 ./articles）")
    p_account.add_argument(
        "--cookies-from-browser",
        default=None,
        help="复用浏览器登录态，如 chrome / edge",
    )
    p_account.set_defaults(func=_cmd_account)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
