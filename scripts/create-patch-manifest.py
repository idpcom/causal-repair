#!/usr/bin/env python3
"""Create a Causal Repair patch manifest.

The manifest records the current repository diff after a repair attempt and
marks files that were already dirty at the checkpoint. This gives reviewers and
revert steps a mechanical artifact instead of relying on the agent's memory.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Dict, List, Optional, Sequence, Set


def run_git(args: Sequence[str], *, cwd: Optional[Path] = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        check=check,
    )


def git_output(args: Sequence[str], *, cwd: Optional[Path] = None, check: bool = True) -> str:
    result = run_git(args, cwd=cwd, check=check)
    return result.stdout


def repo_root(cwd: Optional[Path] = None) -> Path:
    return Path(git_output(["rev-parse", "--show-toplevel"], cwd=cwd).strip())


def latest_checkpoint(root: Path) -> Optional[Path]:
    base = root / ".causal-repair" / "checkpoints"
    if not base.exists():
        return None
    candidates = [p for p in base.iterdir() if p.is_dir()]
    if not candidates:
        return None
    return sorted(candidates)[-1]


def parse_porcelain_paths(text: str) -> Set[str]:
    paths: Set[str] = set()
    for raw in text.splitlines():
        if not raw:
            continue
        body = raw[3:] if len(raw) > 3 else raw
        if " -> " in body:
            old, new = body.split(" -> ", 1)
            paths.add(old.strip())
            paths.add(new.strip())
        else:
            paths.add(body.strip())
    return {p for p in paths if p}


def parse_name_status(text: str, *, staged: bool, pre_existing: Set[str]) -> List[Dict[str, object]]:
    entries: List[Dict[str, object]] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0]
        path = parts[-1]
        old_path = parts[1] if len(parts) > 2 else None
        already_dirty = path in pre_existing or bool(old_path and old_path in pre_existing)
        entries.append(
            {
                "path": path,
                "old_path": old_path,
                "status": status,
                "staged": staged,
                "pre_existing_dirty": already_dirty,
                "safe_auto_revert": not already_dirty,
            }
        )
    return entries


def nul_list(path: Path) -> Set[str]:
    if not path.exists():
        return set()
    data = path.read_bytes()
    if not data:
        return set()
    return {item.decode("utf-8", errors="replace") for item in data.split(b"\0") if item}


def build_manifest(checkpoint: Optional[Path], output: Path, *, cwd: Optional[Path] = None) -> Dict[str, object]:
    root = repo_root(cwd)
    if checkpoint is None:
        checkpoint = latest_checkpoint(root)
    if checkpoint is None:
        raise FileNotFoundError("no checkpoint found; run scripts/create-checkpoint.sh first")
    if not checkpoint.is_absolute():
        checkpoint = root / checkpoint

    status_before_path = checkpoint / "status-short.txt"
    pre_existing_status = status_before_path.read_text(encoding="utf-8") if status_before_path.exists() else ""
    pre_existing_paths = parse_porcelain_paths(pre_existing_status)
    pre_existing_untracked = nul_list(checkpoint / "pre-existing-untracked.zlist")

    unstaged_name_status = git_output(["diff", "--name-status"], cwd=root)
    staged_name_status = git_output(["diff", "--cached", "--name-status"], cwd=root)
    current_status = git_output(["status", "--short"], cwd=root)
    diff_stat = git_output(["diff", "--stat"], cwd=root)
    staged_diff_stat = git_output(["diff", "--cached", "--stat"], cwd=root)
    diff_check = run_git(["diff", "--check"], cwd=root, check=False)
    staged_diff_check = run_git(["diff", "--cached", "--check"], cwd=root, check=False)

    changed_files = parse_name_status(unstaged_name_status, staged=False, pre_existing=pre_existing_paths)
    changed_files += parse_name_status(staged_name_status, staged=True, pre_existing=pre_existing_paths)

    current_untracked = set(git_output(["ls-files", "--others", "--exclude-standard"], cwd=root).splitlines())
    new_untracked = sorted(current_untracked - pre_existing_untracked)

    manifest: Dict[str, object] = {
        "schema_version": 1,
        "repo_root": str(root),
        "base_commit": (checkpoint / "base-commit.txt").read_text(encoding="utf-8").strip()
        if (checkpoint / "base-commit.txt").exists()
        else None,
        "head_commit": git_output(["rev-parse", "HEAD"], cwd=root).strip(),
        "checkpoint": str(checkpoint),
        "pre_existing_dirty_paths": sorted(pre_existing_paths),
        "changed_files": changed_files,
        "new_untracked_files": new_untracked,
        "current_status_short": current_status.splitlines(),
        "diff_stat": diff_stat,
        "staged_diff_stat": staged_diff_stat,
        "diff_check": {
            "exit_code": diff_check.returncode,
            "stdout": diff_check.stdout,
            "stderr": diff_check.stderr,
        },
        "staged_diff_check": {
            "exit_code": staged_diff_check.returncode,
            "stdout": staged_diff_check.stdout,
            "stderr": staged_diff_check.stderr,
        },
        "safe_revert_guidance": [
            "Do not run git reset --hard in a dirty user worktree.",
            "Files with pre_existing_dirty=true require manual hunk review before revert.",
            "Files with safe_auto_revert=true can usually be reverted if they belong only to the repair attempt.",
            "New untracked files can be removed only if they are listed in new_untracked_files and are part of the repair attempt.",
        ],
    }

    output = output if output.is_absolute() else root / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a Causal Repair patch manifest")
    parser.add_argument("--checkpoint", type=Path, help="Checkpoint directory from scripts/create-checkpoint.sh")
    parser.add_argument("--output", type=Path, default=Path(".causal-repair/patch-manifest.json"))
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    try:
        manifest = build_manifest(args.checkpoint, args.output)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(args.output)
    print(f"changed_files={len(manifest['changed_files'])}")
    print(f"new_untracked_files={len(manifest['new_untracked_files'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
