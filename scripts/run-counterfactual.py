#!/usr/bin/env python3
"""Run the counterfactual command recorded in an RCA gate.

This does not prove causality by itself, but it prevents a gate from claiming a
counterfactual result that does not match the command's actual exit status.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
from typing import Dict, Optional, Sequence, Tuple

EXPECTED_EXIT = {
    "pass": 0,
    "failed": 1,
}


def load_gate(path: Path) -> Dict[str, object]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("RCA gate must be a JSON object")
    return data


def output_tail(value: Optional[str], *, limit: int = 4000) -> str:
    return (value or "")[-limit:]


def command_uses_claude_bare(command: str) -> bool:
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()

    has_bare = "--bare" in tokens
    has_claude = any(Path(token).name == "claude" for token in tokens)
    if has_bare and has_claude:
        return True

    # Fallback for wrapped commands such as: bash -lc "claude --print --bare ..."
    return bool(
        re.search(r"(?:^|[;&|`$()\s])claude(?:\s|$)", command)
        and re.search(r"(?:^|\s)--bare(?:\s|$|[;&|])", command)
    )


def repo_root(cwd: Path) -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=str(cwd),
        text=True,
        capture_output=True,
        check=False,
    )
    stdout = (result.stdout or "").strip()
    if result.returncode != 0 or not stdout:
        return cwd.resolve()
    return Path(stdout)


def counterfactual(data: Dict[str, object]) -> Dict[str, object]:
    value = data.get("counterfactual_check")
    if not isinstance(value, dict):
        raise ValueError("counterfactual_check must be an object")
    command = value.get("command")
    result = value.get("result")
    if not isinstance(command, str) or not command.strip():
        raise ValueError("counterfactual_check.command must be a non-empty string")
    if command_uses_claude_bare(command):
        raise ValueError("counterfactual_check.command must not use `claude --bare` because it disables hooks/plugins required by causal-repair")
    if not isinstance(result, str) or result not in {"pass", "failed", "incomplete"}:
        raise ValueError("counterfactual_check.result must be pass, failed, or incomplete")
    return value


def run_counterfactual(gate_path: Path, *, cwd: Optional[Path] = None, timeout: int = 120) -> Tuple[bool, Dict[str, object]]:
    data = load_gate(gate_path)
    cf = counterfactual(data)
    expected = str(cf["result"])
    command = str(cf["command"])
    root = repo_root(cwd or gate_path.parent.parent)

    if expected == "incomplete":
        return True, {
            "status": "skipped",
            "reason": "counterfactual result is recorded as incomplete",
            "command": command,
            "expected": expected,
        }

    completed = subprocess.run(
        command,
        cwd=str(root),
        shell=True,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    actual_pass = completed.returncode == 0
    actual = "pass" if actual_pass else "failed"
    ok = actual == expected
    return ok, {
        "status": "matched" if ok else "mismatch",
        "command": command,
        "expected": expected,
        "actual": actual,
        "exit_code": completed.returncode,
        "stdout": output_tail(completed.stdout),
        "stderr": output_tail(completed.stderr),
    }


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run and verify an RCA gate counterfactual command")
    parser.add_argument("path", type=Path, nargs="?", default=Path(".causal-repair/rca-gate.json"))
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--output", type=Path, default=Path(".causal-repair/counterfactual-result.json"))
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    try:
        ok, result = run_counterfactual(args.path, timeout=args.timeout)
    except Exception as exc:
        print(f"counterfactual execution error: {exc}", file=sys.stderr)
        return 2

    output = args.output if args.output.is_absolute() else args.path.parent.parent / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
