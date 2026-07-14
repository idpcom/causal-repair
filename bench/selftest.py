#!/usr/bin/env python3
"""Self-test the benchmark task corpus (no model, no network).

For every task under bench/tasks/ this asserts the task is well-formed:

  1. base repo: the visible test FAILS (it is a real failing-test task)
  2. reference/good overlay  -> scorer label == genuine_fix
  3. reference/workaround overlay -> scorer label != genuine_fix (ideally "gamed")

This guards against a common authoring bug: a task whose held-out tests or
workaround regexes don't actually discriminate a real fix from a workaround.
Run it in CI before spending any tokens.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import score  # noqa: E402  (local import after sys.path tweak)

TASKS_DIR = Path(__file__).resolve().parent / "tasks"


def build_worktree(task_dir: Path, tmp: Path, overlay: str | None) -> Path:
    repo = tmp / "repo"
    shutil.copytree(task_dir / "repo", repo)
    # Commit the clean buggy base first, so an overlaid fix appears as a diff
    # (mirrors what the runner does: model edits a committed base).
    score.init_repo(repo)
    if overlay is not None:
        src = task_dir / "reference" / overlay
        for item in src.iterdir():
            dst = repo / item.name
            if item.is_dir():
                shutil.copytree(item, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dst)
    return repo


def check_task(task_dir: Path) -> list[str]:
    meta = score.load_meta(task_dir)
    errors: list[str] = []

    # 1. base must fail the visible test
    with tempfile.TemporaryDirectory() as tmp:
        repo = build_worktree(task_dir, Path(tmp), overlay=None)
        visible_cmd = score.command(meta, "visible_test_cmd", score.DEFAULT_VISIBLE_CMD)
        ok, _ = score.run_test(repo, visible_cmd)
        if ok:
            errors.append("base repo already passes the visible test (not a failing task)")

    # 2. reference good fix must grade genuine_fix
    good = task_dir / "reference" / "good"
    if not good.exists():
        errors.append("missing reference/good overlay")
    else:
        with tempfile.TemporaryDirectory() as tmp:
            repo = build_worktree(task_dir, Path(tmp), overlay="good")
            result = score.grade_worktree(task_dir, repo, meta)
            if result["label"] != "genuine_fix":
                errors.append(f"reference/good graded {result['label']!r}, expected genuine_fix: {result}")

    # 3. reference workaround must NOT grade genuine_fix
    workaround = task_dir / "reference" / "workaround"
    if not workaround.exists():
        errors.append("missing reference/workaround overlay")
    else:
        with tempfile.TemporaryDirectory() as tmp:
            repo = build_worktree(task_dir, Path(tmp), overlay="workaround")
            result = score.grade_worktree(task_dir, repo, meta)
            if result["label"] == "genuine_fix":
                errors.append(f"reference/workaround graded genuine_fix (scorer cannot catch it): {result}")

    return errors


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Self-test a task corpus")
    ap.add_argument("--tasks-dir", type=Path, default=TASKS_DIR)
    args = ap.parse_args()
    tasks = sorted(p for p in args.tasks_dir.resolve().iterdir() if (p / "meta.json").exists())
    if not tasks:
        print("no tasks found", file=sys.stderr)
        return 1
    failed = 0
    for task_dir in tasks:
        errors = check_task(task_dir)
        if errors:
            failed += 1
            print(f"FAIL {task_dir.name}")
            for e in errors:
                print(f"    - {e}")
        else:
            print(f"PASS {task_dir.name}")
    print(f"\n{len(tasks) - failed}/{len(tasks)} tasks well-formed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
