#!/usr/bin/env python3
"""Validate a Causal Repair RCA gate JSON file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shlex
import sys
from typing import Dict, List, Optional, Sequence, Tuple

REQUIRED_FIELDS = [
    "failure_evidence",
    "causal_path",
    "broken_behavior",
    "contract_invariant_status",
    "contract_clauses",
    "root_cause_location",
    "cause_not_symptom",
    "counterfactual_check",
    "minimal_patch_shape",
    "workaround_reject_rules",
    "tests_to_run",
    "checkpoint",
]
TEXT_RCA_FIELDS = [
    "failure_evidence",
    "causal_path",
    "broken_behavior",
    "root_cause_location",
    "cause_not_symptom",
    "minimal_patch_shape",
]
ALLOWED_CONTRACT_STATUS = {"explicit", "inferred", "unknown"}
ALLOWED_COUNTERFACTUAL_RESULTS = {"pass", "failed", "incomplete"}
ALLOWED_CLAUSE_STATUS = {"broken", "held", "at-risk"}
CONTRACT_TESTS_TOKEN = ".causal-repair/contract-tests"
MIN_TEXT_LEN = 12


def non_empty(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return bool(value)
    return True


def valid_text(value: object, min_len: int = MIN_TEXT_LEN) -> bool:
    return isinstance(value, str) and len(value.strip()) >= min_len


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


def valid_checkpoint_dir(path: Path) -> bool:
    base = path / "base-commit.txt"
    status = path / "status-short.txt"
    if not base.exists() or not status.exists():
        return False
    base_text = base.read_text(encoding="utf-8", errors="replace").strip()
    return bool(re.fullmatch(r"[0-9a-fA-F]{40}", base_text))


def validate_checkpoint_reference(gate_path: Path, value: object) -> List[str]:
    if not isinstance(value, str) or not value.strip():
        return ["checkpoint must be a path string"]
    checkpoint = Path(value)
    if not checkpoint.is_absolute():
        checkpoint = gate_path.parent.parent / checkpoint
    if not checkpoint.exists():
        return ["checkpoint path does not exist"]
    if not valid_checkpoint_dir(checkpoint):
        return ["checkpoint path is missing a valid base-commit.txt"]
    return []


def validate_counterfactual(value: object) -> List[str]:
    if not isinstance(value, dict):
        return ["counterfactual_check must be an object with command, result, and evidence"]
    errors: List[str] = []
    command = value.get("command")
    if not valid_text(command, 4):
        errors.append("counterfactual_check.command is missing or too short")
    elif command_uses_claude_bare(command):
        errors.append("counterfactual_check.command must not use `claude --bare` because it disables hooks/plugins required by causal-repair")
    result = value.get("result")
    if not isinstance(result, str) or result not in ALLOWED_COUNTERFACTUAL_RESULTS:
        errors.append("counterfactual_check.result must be pass, failed, or incomplete")
    if not valid_text(value.get("evidence")):
        errors.append("counterfactual_check.evidence is missing or too short")
    return errors


def validate_contract_clauses(value: object) -> List[str]:
    """The gate must enumerate the documented contract of the code under repair.

    Each clause records what the docs/docstring promise, whether the current
    code holds it, and which command verifies it. This is what prevents a patch
    that satisfies only the visible test while silently dropping a documented
    behavior (especially error contracts such as "invalid input raises").
    """
    if not isinstance(value, list) or not value:
        return ["contract_clauses must be a non-empty list of clause objects"]
    errors: List[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            errors.append(
                f"contract_clauses[{index}] must be an object with clause, status, and covered_by"
            )
            continue
        if not valid_text(item.get("clause"), 8):
            errors.append(f"contract_clauses[{index}].clause is missing or too short")
        status = item.get("status")
        if not isinstance(status, str) or status not in ALLOWED_CLAUSE_STATUS:
            errors.append(
                f"contract_clauses[{index}].status must be one of: "
                + ", ".join(sorted(ALLOWED_CLAUSE_STATUS))
            )
        if not valid_text(item.get("covered_by"), 4):
            errors.append(f"contract_clauses[{index}].covered_by is missing or too short")
    return errors


def validate_gate(data: Dict[str, object], *, gate_path: Optional[Path] = None) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    for field in REQUIRED_FIELDS:
        if field not in data or not non_empty(data[field]):
            errors.append(f"missing or empty field: {field}")

    for field in TEXT_RCA_FIELDS:
        if field in data and not valid_text(data[field]):
            errors.append(f"field too short: {field}")

    status = data.get("contract_invariant_status")
    if not isinstance(status, str) or status not in ALLOWED_CONTRACT_STATUS:
        errors.append(
            "contract_invariant_status must be one of: "
            + ", ".join(sorted(ALLOWED_CONTRACT_STATUS))
        )

    if "counterfactual_check" in data:
        errors.extend(validate_counterfactual(data["counterfactual_check"]))

    if "contract_clauses" in data:
        errors.extend(validate_contract_clauses(data["contract_clauses"]))

    reject_rules = data.get("workaround_reject_rules")
    if not isinstance(reject_rules, list) or not all(valid_text(item, 6) for item in reject_rules):
        errors.append("workaround_reject_rules must be a non-empty list of strings")

    tests = data.get("tests_to_run")
    if not isinstance(tests, list) or not tests or not all(valid_text(item, 4) for item in tests):
        errors.append("tests_to_run must be a non-empty list of command strings")
    else:
        # The visible reproduction alone is not validation: the gate must also
        # run the authored contract tests, or a symptom-only patch passes.
        if len(tests) < 2:
            errors.append(
                "tests_to_run must contain at least 2 commands: the visible reproduction "
                "and the authored contract tests"
            )
        if not any(CONTRACT_TESTS_TOKEN in item for item in tests):
            errors.append(
                f"tests_to_run must reference the authored contract tests ({CONTRACT_TESTS_TOKEN}*)"
            )

    if gate_path is not None and "checkpoint" in data:
        errors.extend(validate_checkpoint_reference(gate_path, data["checkpoint"]))

    return not errors, errors


def load_gate(path: Path) -> Dict[str, object]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("RCA gate must be a JSON object")
    return data


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate .causal-repair/rca-gate.json")
    parser.add_argument("path", type=Path, nargs="?", default=Path(".causal-repair/rca-gate.json"))
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    try:
        gate = load_gate(args.path)
        ok, errors = validate_gate(gate, gate_path=args.path)
    except Exception as exc:
        print(f"invalid RCA gate: {exc}", file=sys.stderr)
        return 2

    if not ok:
        for error in errors:
            print(f"invalid RCA gate: {error}", file=sys.stderr)
        return 2

    print(f"valid RCA gate: {args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
