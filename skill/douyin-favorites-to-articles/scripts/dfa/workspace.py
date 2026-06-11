from __future__ import annotations

import shutil
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TaskWorkspace:
    temp_root: Path
    video_id: str

    @property
    def root(self) -> Path:
        return self.temp_root / self.video_id

    def create(self) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        return self.root

    def cleanup(self) -> None:
        if self.root.exists():
            shutil.rmtree(self.root)


def clean_stale_workspaces(temp_root: Path, older_than_hours: int = 24) -> list[str]:
    if not temp_root.exists():
        return []

    cutoff = time.time() - older_than_hours * 60 * 60
    removed: list[str] = []
    for candidate in sorted(temp_root.iterdir()):
        if candidate.is_dir() and candidate.stat().st_mtime < cutoff:
            shutil.rmtree(candidate)
            removed.append(candidate.name)
    return removed
