#!/usr/bin/env python3
"""Run executable fixture evaluations for Causal Repair.

This script checks both behavior and workaround shape:

- known-good patches must pass tests and avoid workaround patterns
- known-bad patches may fail tests, or may pass tests while still being flagged
  as test-specific/workaround-shaped
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "python-null-profile"

WORKAROUND_PATTERNS = [
    ("fixture-specific legacy branch", re.compile(r"user_id\s*==\s*[\"']legacy[\"']")),
    ("empty-string null fallback", re.compile(r"return\s+[\"'][\"']")),
    ("direct null special-case without normalization boundary", re.compile(r"profile\[[\"']name[\"']\]\s+is\s+None")),
]


def run(cmd: Sequence[str], cwd: Path, *, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True, check=check)


def copy_fixture(workdir: Path) -> Path:
    src = FIXTURE / "repo"
    dst = workdir / "repo"
    shutil.copytree(src, dst)
    return dst


def apply_patch(repo: Path, patch_path: Path) -> subprocess.CompletedProcess:
    return run(["git", "apply", str(patch_path)], repo)


def run_fixture_tests(repo: Path) -> subprocess.CompletedProcess:
    # Use stdlib only. The fixture test_profile.py can still be used manually
    # with pytest, but CI should not require extra dependencies.
    runner = repo / "_fixture_runner.py"
    runner.write_text(
        "from profile import get_display_name\n"
        "assert get_display_name('alice') == 'Alice'\n"
        "assert get_display_name('legacy') == 'Anonymous'\n"
        "try:\n"
        "    get_display_name('missing')\n"
        "except KeyError:\n"
        "    pass\n"
        "else:\n"
        "    raise AssertionError('missing user must raise KeyError')\n",
        encoding="utf-8",
    )
    return run([sys.executable, str(runner)], repo)


def init_repo(repo: Path) -> None:
    run(["git", "init"], repo, check=True)
    run(["git", "config", "user.email", "fixture@example.com"], repo, check=True)
    run(["git", "config", "user.name", "Fixture"], repo, check=True)
    run(["git", "add", "."], repo, check=True)
    run(["git", "commit", "-m", "fixture base"], repo, check=True)


def changed_diff(repo: Path) -> str:
    return run(["git", "diff", "HEAD"], repo, check=True).stdout


def workaround_findings(diff_text: str) -> List[str]:
    findings = []
    for label, pattern in WORKAROUND_PATTERNS:
        if pattern.search(diff_text):
            findings.append(label)
    return findings


def evaluate_patch(patch_name: str, *, expected_tests_pass: bool, expected_workaround: bool) -> bool:
    patch_path = FIXTURE / "patches" / patch_name
    with tempfile.TemporaryDirectory() as tmp:
        repo = copy_fixture(Path(tmp))
        init_repo(repo)
        applied = apply_patch(repo, patch_path)
        if applied.returncode != 0:
            print(f"FAIL {patch_name}: patch did not apply", file=sys.stderr)
            print(applied.stderr, file=sys.stderr)
            return False

        result = run_fixture_tests(repo)
        tests_passed = result.returncode == 0
        if tests_passed != expected_tests_pass:
            expectation = "pass" if expected_tests_pass else "fail"
            print(f"FAIL {patch_name}: expected tests to {expectation}", file=sys.stderr)
            print(result.stdout, file=sys.stderr)
            print(result.stderr, file=sys.stderr)
            return False

        findings = workaround_findings(changed_diff(repo))
        is_workaround = bool(findings)
        if is_workaround != expected_workaround:
            expectation = "be flagged as workaround" if expected_workaround else "avoid workaround findings"
            print(f"FAIL {patch_name}: expected patch to {expectation}", file=sys.stderr)
            print("findings:", findings, file=sys.stderr)
            print(changed_diff(repo), file=sys.stderr)
            return False

        state = "tests passed" if tests_passed else "tests failed as expected"
        review = "workaround flagged" if is_workaround else "no workaround findings"
        print(f"PASS {patch_name}: {state}; {review}")
        return True


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate known-good and known-bad fixture patches")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parse_args(argv)
    checks = [
        evaluate_patch(
            "good-normalize-display-name.patch",
            expected_tests_pass=True,
            expected_workaround=False,
        ),
        evaluate_patch(
            "bad-null-empty-string.patch",
            expected_tests_pass=False,
            expected_workaround=True,
        ),
        evaluate_patch(
            "bad-hardcoded-legacy.patch",
            expected_tests_pass=True,
            expected_workaround=True,
        ),
    ]
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
