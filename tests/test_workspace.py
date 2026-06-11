import os
import time

from dfa.workspace import TaskWorkspace, clean_stale_workspaces


def test_workspace_create_and_cleanup(tmp_path):
    workspace = TaskWorkspace(tmp_path, "123")
    workspace.create()
    (workspace.root / "transcript.txt").write_text("hello", encoding="utf-8")

    assert workspace.root.is_dir()
    workspace.cleanup()
    assert not workspace.root.exists()


def test_cleanup_removes_only_stale_directories(tmp_path):
    stale = TaskWorkspace(tmp_path, "old")
    fresh = TaskWorkspace(tmp_path, "new")
    stale.create()
    fresh.create()
    old = time.time() - 48 * 60 * 60
    os.utime(stale.root, (old, old))

    removed = clean_stale_workspaces(tmp_path, older_than_hours=24)

    assert removed == ["old"]
    assert not stale.root.exists()
    assert fresh.root.exists()
