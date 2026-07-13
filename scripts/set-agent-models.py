#!/usr/bin/env python3
"""Update Causal Repair subagent model frontmatter fields.

This script edits the plugin's Markdown agent files in place. It assumes your
Claude Code provider, proxy, or router is already configured. You only pass the
model names that your environment already accepts.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import shutil
import sys
from typing import Dict, Iterable, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
AGENTS = {
    "investigator": ROOT / "agents" / "root-cause-investigator.md",
    "judge": ROOT / "agents" / "root-cause-judge.md",
    "reviewer": ROOT / "agents" / "workaround-reviewer.md",
    "verifier": ROOT / "agents" / "repair-verifier.md",
}

PROFILES = {
    "default": {
        "investigator": "haiku",
        "judge": "sonnet",
        "reviewer": "haiku",
        "verifier": "haiku",
    },
    "qwen-only": {
        "investigator": "qwen3-coder-plus",
        "judge": "qwen3-coder-plus",
        "reviewer": "qwen3-coder-plus",
        "verifier": "qwen3-coder-plus",
    },
    "qwen-mimo": {
        "investigator": "qwen3-coder-plus",
        "judge": "xiaomi/mimo-v2.5-pro",
        "reviewer": "qwen3-coder-plus",
        "verifier": "qwen3-coder-plus",
    },
    "safe-claude": {
        "investigator": "sonnet",
        "judge": "opus",
        "reviewer": "sonnet",
        "verifier": "haiku",
    },
}

MODEL_NAME_RE = re.compile(r"^[A-Za-z0-9._:/@+\-]+$")
FRONTMATTER_START_RE = re.compile(r"^\ufeff?---\r?\n")
FRONTMATTER_END_RE = re.compile(r"\r?\n---\r?\n", re.MULTILINE)
MODEL_LINE_RE = re.compile(r"^model:\s*(.*)$", re.MULTILINE)


def normalize_frontmatter_start(text: str) -> str:
    """Allow UTF-8 BOM and leading blank lines before YAML frontmatter.

    Some editors and tests produce Markdown with one or more blank lines before
    the opening `---`. The skill files should not do this, but the model routing
    helper should be robust enough to update them safely.
    """
    text = text.lstrip("\ufeff")
    return text.lstrip(" \t\r\n")


def split_frontmatter(text: str, path: Path) -> Tuple[str, str, str]:
    """Return frontmatter, body, newline style for a Markdown file."""
    text = normalize_frontmatter_start(text)
    start = FRONTMATTER_START_RE.match(text)
    if not start:
        raise ValueError(f"missing YAML frontmatter: {path}")

    newline = "\r\n" if "\r\n" in start.group(0) else "\n"
    end = FRONTMATTER_END_RE.search(text, start.end())
    if not end:
        raise ValueError(f"unterminated YAML frontmatter: {path}")

    frontmatter = text[: end.start() + len(newline)]
    body = text[end.start() + len(newline) :]
    return frontmatter, body, newline


def validate_model_name(model: str) -> None:
    if not model or not model.strip():
        raise ValueError("model name must not be empty")
    if not MODEL_NAME_RE.match(model):
        raise ValueError(
            "model name contains unsupported characters. "
            "Use the exact registered model id, for example qwen3-coder-plus."
        )


def update_model(path: Path, model: str, *, backup: bool = True) -> None:
    validate_model_name(model)
    if not path.exists():
        raise FileNotFoundError(f"agent file not found: {path}")

    text = path.read_text(encoding="utf-8-sig")
    frontmatter, body, newline = split_frontmatter(text, path)

    if MODEL_LINE_RE.search(frontmatter):
        frontmatter = MODEL_LINE_RE.sub(f"model: {model}", frontmatter, count=1)
    else:
        frontmatter = frontmatter.rstrip("\r\n") + newline + f"model: {model}" + newline

    if backup:
        backup_path = path.with_suffix(path.suffix + ".bak")
        shutil.copyfile(path, backup_path)

    path.write_text(frontmatter + body, encoding="utf-8", newline="")


def current_model(path: Path) -> str:
    text = path.read_text(encoding="utf-8-sig")
    frontmatter, _, _ = split_frontmatter(text, path)
    match = MODEL_LINE_RE.search(frontmatter)
    return match.group(1).strip() if match else "inherit"


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Update Causal Repair subagent model fields."
    )
    parser.add_argument(
        "--profile",
        choices=sorted(PROFILES),
        help="Apply a named model profile",
    )
    parser.add_argument("--investigator", help="Model for root-cause-investigator")
    parser.add_argument("--judge", help="Model for root-cause-judge")
    parser.add_argument("--reviewer", help="Model for workaround-reviewer")
    parser.add_argument("--verifier", help="Model for repair-verifier")
    parser.add_argument(
        "--all",
        dest="all_model",
        help="Set the same model for every Causal Repair subagent",
    )
    parser.add_argument(
        "--print",
        action="store_true",
        help="Print current model fields without changing files",
    )
    parser.add_argument(
        "--list-profiles",
        action="store_true",
        help="Print bundled model profiles",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned updates without changing files",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Do not write .bak files before editing agent files",
    )
    return parser


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    return make_parser().parse_args(argv)


def print_profiles() -> None:
    for profile, values in PROFILES.items():
        print(f"[{profile}]")
        for name in AGENTS:
            print(f"  {name}: {values[name]}")


def explicit_updates(args: argparse.Namespace) -> Dict[str, str]:
    updates = {}
    for name in AGENTS:
        model = getattr(args, name)
        if model:
            updates[name] = model
    return updates


def build_updates(args: argparse.Namespace) -> Dict[str, str]:
    explicit = explicit_updates(args)
    sources = [bool(args.profile), bool(args.all_model), bool(explicit)]
    if sum(sources) > 1:
        raise ValueError(
            "conflicting model update modes: choose exactly one of --profile, --all, "
            "or explicit per-agent flags"
        )

    if args.profile:
        return dict(PROFILES[args.profile])
    if args.all_model:
        validate_model_name(args.all_model)
        return {name: args.all_model for name in AGENTS}

    for model in explicit.values():
        validate_model_name(model)
    return explicit


def print_current_models(names: Iterable[str] = AGENTS) -> None:
    for name in names:
        path = AGENTS[name]
        print(f"{name}: {current_model(path)}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)

    if args.list_profiles:
        print_profiles()
        return 0

    if args.print:
        print_current_models()
        return 0

    try:
        updates = build_updates(args)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if not updates:
        print("No model updates requested. Use --help for examples.", file=sys.stderr)
        return 2

    for name, model in updates.items():
        old = current_model(AGENTS[name])
        if args.dry_run:
            print(f"would update {name}: {old} -> {model}")
        else:
            update_model(AGENTS[name], model, backup=not args.no_backup)
            print(f"updated {name}: {old} -> {model}")

    if not args.dry_run:
        print("Run /reload-plugins in Claude Code after editing installed plugin files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
