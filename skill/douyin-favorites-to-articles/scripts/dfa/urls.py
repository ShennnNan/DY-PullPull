from __future__ import annotations

import hashlib
import re
from urllib.parse import parse_qs, urlsplit, urlunsplit


_VIDEO_PATH = re.compile(r"/video/(\d+)")
_ALLOWED_HOSTS = {"douyin.com", "www.douyin.com", "v.douyin.com"}


def normalize_source_url(source_url: str) -> str:
    value = source_url.strip()
    parsed = urlsplit(value)
    host = (parsed.hostname or "").lower()
    if host not in _ALLOWED_HOSTS and not host.endswith(".douyin.com"):
        raise ValueError("仅支持 douyin.com 域名的链接")

    path = parsed.path.rstrip("/") or "/"
    query = parse_qs(parsed.query)
    modal_id = query.get("modal_id", [None])[0]
    if modal_id and modal_id.isdigit():
        path = f"/video/{modal_id}"

    return urlunsplit(("https", host, path, "", ""))


def video_id_from_url(source_url: str) -> str:
    normalized = normalize_source_url(source_url)
    match = _VIDEO_PATH.search(urlsplit(normalized).path)
    if match:
        return match.group(1)

    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    return f"url-{digest}"
