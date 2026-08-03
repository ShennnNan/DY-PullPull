from __future__ import annotations

import re
from pathlib import Path

_MAX_ARTICLE_STEM_LENGTH = 180
_WINDOWS_PUNCTUATION = str.maketrans(
    {
        "<": "＜",
        ">": "＞",
        ":": "：",
        '"': "＂",
        "/": "／",
        "\\": "＼",
        "|": "｜",
        "?": "？",
        "*": "＊",
    }
)
_WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}


def safe_article_stem(title: str | None, video_id: str) -> str:
    """Return a readable Windows-safe filename stem based on the video title."""
    stem = (title or video_id).translate(_WINDOWS_PUNCTUATION)
    stem = re.sub(r"[\x00-\x1f]", " ", stem)
    stem = re.sub(r"\s+", " ", stem).strip(" .")
    if not stem:
        stem = video_id
    if len(stem) > _MAX_ARTICLE_STEM_LENGTH:
        stem = f"{stem[: _MAX_ARTICLE_STEM_LENGTH - 1].rstrip(' .')}…"
    if stem.upper() in _WINDOWS_RESERVED_NAMES:
        stem = f"_{stem}"
    return stem


def _article_matches_video(path: Path, video_id: str) -> bool:
    try:
        with path.open("r", encoding="utf-8-sig", errors="ignore") as article:
            header = article.read(1024)
    except OSError:
        return False
    return bool(
        re.search(rf"(?m)^video_id: {re.escape(video_id)}\r?$", header)
    )


def article_path_for(
    out_dir: Path,
    title: str | None,
    video_id: str,
) -> Path:
    """Choose an idempotent title path without overwriting a same-title video."""
    stem = safe_article_stem(title, video_id)
    candidate = out_dir / f"{stem}.md"
    if not candidate.exists() or _article_matches_video(candidate, video_id):
        return candidate

    sequence = 2
    while True:
        candidate = out_dir / f"{stem} ({sequence}).md"
        if not candidate.exists() or _article_matches_video(candidate, video_id):
            return candidate
        sequence += 1
