from __future__ import annotations

import argparse
from pathlib import Path

from pullpull.pull import pull


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="P1 单条闭环：抖音链接 → yt-dlp 下载 → FunASR 转写 → Markdown",
    )
    parser.add_argument("url", help="抖音视频分享链接")
    parser.add_argument(
        "--out",
        default="./articles",
        help="Markdown 输出目录（默认 ./articles）",
    )
    parser.add_argument(
        "--cookies-from-browser",
        default=None,
        help="复用浏览器登录态，如 chrome / edge（处理需登录内容时）",
    )
    args = parser.parse_args(argv)

    result = pull(
        args.url,
        Path(args.out),
        cookies_from_browser=args.cookies_from_browser,
    )
    print(f"video_id: {result.video_id}")
    print(f"title:    {result.title}")
    print(f"markdown: {result.markdown_path}")
    print(f"chars:    {len(result.transcript)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
