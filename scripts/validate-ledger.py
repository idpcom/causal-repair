#!/usr/bin/env python3
"""Validate a Causal Repair ledger JSON file.

The ledger (`.causal-repair/ledger.json`) is the externalized state for
long-horizon repairs: the goal, the enumerated contract, and a plan of short
segments, each small enough for a small model to finish inside its effective
horizon and each ending in a mechanically checkable done criterion.

Long problems are not solved with long contexts. Each segment runs in a fresh
subagent that reads the ledger first; the handoff between segments is this
file, validated here — not conversation memory.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Dict, List, Optional, Sequence, Tuple

ALLOWED_SEGMENT_STATUS = {"pending", "in_progress", "done", "failed"}
ALLOWED_SEGMENT_KINDS = {
    "investigate",
    "rca",
    "contract-tests",
    "patch",
    "review",
    "verify",
}
MIN_TEXT_LEN = 12
MAX_ATTEMPTS = 2


def valid_text(value: object, min_len: int = MIN_TEXT_LEN) -> bool:
    return isinstance(value, str) and len(value.strip()) >= min_len


def validate_segment(index: int, item: object) -> List[str]:
    errors: List[str] = []
    prefix = f"segments[{index}]"
    if not isinstance(item, dict):
        return [f"{prefix} must be an object"]
    if not valid_text(item.get("id"), 2):
        errors.append(f"{prefix}.id is missing or too short")
    kind = item.get("kind")
    if not isinstance(kind, str) or kind not in ALLOWED_SEGMENT_KINDS:
        errors.append(
            f"{prefix}.kind must be one of: " + ", ".join(sorted(ALLOWED_SEGMENT_KINDS))
        )
    if not valid_text(item.get("objective"), 8):
        errors.append(f"{prefix}.objective is missing or too short")
    if not valid_text(item.get("done_criteria"), 4):
        errors.append(
            f"{prefix}.done_criteria is missing or too short (must be a runnable command "
            "or mechanically checkable condition)"
        )
    status = item.get("status")
    if not isinstance(status, str) or status not in ALLOWED_SEGMENT_STATUS:
        errors.append(
            f"{prefix}.status must be one of: " + ", ".join(sorted(ALLOWED_SEGMENT_STATUS))
        )
    if status == "done" and not valid_text(item.get("evidence"), 8):
        errors.append(f"{prefix}.evidence is required once the segment is done")
    return errors


def validate_ledger(data: Dict[str, object]) -> Tuple[bool, List[str]]:
    errors: List[str] = []

    if not valid_text(data.get("goal")):
        errors.append("goal is missing or too short")

    segments = data.get("segments")
    if not isinstance(segments, list) or not segments:
        errors.append("segments must be a non-empty list")
        segments = []

    seen_ids = set()
    in_progress = 0
    for index, item in enumerate(segments):
        errors.extend(validate_segment(index, item))
        if isinstance(item, dict):
            seg_id = item.get("id")
            if isinstance(seg_id, str):
                if seg_id in seen_ids:
                    errors.append(f"segments[{index}].id duplicates {seg_id!r}")
                seen_ids.add(seg_id)
            if item.get("status") == "in_progress":
                in_progress += 1

    if in_progress > 1:
        errors.append(
            "at most one segment may be in_progress (fresh-context relay: one segment at a time)"
        )

    attempts = data.get("attempts", 0)
    if not isinstance(attempts, int) or attempts < 0:
        errors.append("attempts must be a non-negative integer")
    elif attempts > MAX_ATTEMPTS:
        errors.append(
            f"attempts exceeds {MAX_ATTEMPTS}: stop, report evidence, and ask for guidance "
            "instead of stacking more rounds"
        )

    if not valid_text(data.get("stop_condition"), 8):
        errors.append("stop_condition is missing or too short")

    return not errors, errors


def load_ledger(path: Path) -> Dict[str, object]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("ledger must be a JSON object")
    return data


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate .causal-repair/ledger.json")
    parser.add_argument("path", type=Path, nargs="?", default=Path(".causal-repair/ledger.json"))
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    try:
        ledger = load_ledger(args.path)
        ok, errors = validate_ledger(ledger)
    except Exception as exc:
        print(f"invalid ledger: {exc}", file=sys.stderr)
        return 2

    if not ok:
        for error in errors:
            print(f"invalid ledger: {error}", file=sys.stderr)
        return 2

    print(f"valid ledger: {args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
