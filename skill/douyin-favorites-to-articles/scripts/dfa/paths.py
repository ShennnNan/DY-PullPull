from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppPaths:
    root: Path
    database: Path
    articles: Path
    browser_profile: Path
    logs: Path
    temp: Path

    @classmethod
    def from_root(cls, root: Path) -> "AppPaths":
        resolved = root.expanduser().resolve()
        return cls(
            root=resolved,
            database=resolved / "library.db",
            articles=resolved / "articles",
            browser_profile=resolved / "browser-profile",
            logs=resolved / "logs",
            temp=resolved / "temp",
        )

    @classmethod
    def default(cls) -> "AppPaths":
        local_app_data = os.environ.get("LOCALAPPDATA")
        base = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
        return cls.from_root(base / "DouyinFavoritesToArticles")

    def initialize(self) -> None:
        for directory in (
            self.root,
            self.articles,
            self.browser_profile,
            self.logs,
            self.temp,
        ):
            directory.mkdir(parents=True, exist_ok=True)
