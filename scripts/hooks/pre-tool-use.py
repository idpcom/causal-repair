#!/usr/bin/env python3
"""Causal Repair PreToolUse hook.

This hook blocks Claude Code write tools until a mechanical checkpoint and a
valid RCA gate exist. It also blocks common shell write/destructive paths before
RCA. This is not an OS sandbox, but it closes the easy tool-level escape hatches.

Claude Code hook payload schemas can evolve, so this script accepts several
common field names instead of depending on one exact shape.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

WRITE_TOOLS = {"Edit", "MultiEdit", "Write", "NotebookEdit"}
DANGEROUS_BASH_RE = re.compile(
    r"(?:^|[;&|\s])("
    r"git\s+reset\s+--hard(?:\s|$|[;&|])|"
    r"git\s+clean\s+-[A-Za-z]*[xdfXf][A-Za-z]*(?:\s|$|[;&|])|"
    r"git\s+checkout\s+--\s+\.(?:\s|$|[;&|])|"
    r"rm\s+-[A-Za-z]*[rf][A-Za-z]*\s+/(?:\s|$|[;&|])|"
    r"rm\s+-[A-Za-z]*[rf][A-Za-z]*\s+\.(?:\s|$|[;&|])"
    r")"
)
STRICT_BASH_WRITE_RE = re.compile(
    r"("
    r"sed\s+-i|"
    r"perl\s+-pi|"
    r"\btee\b|"
    r">>|"
    r">[^&]|"
    r"\bmv\b|"
    r"\bcp\b|"
    r"\brm\b|"
    r"\btouch\b|"
    r"\btruncate\b|"
    r"\bgit\s+apply\b|"
    r"\bapply_patch\b|"
    r"\bpatch\b|"
    r"\bpython(?:3)?\s+-c\b|"
    r"\bpython(?:3)?\s+-\s*<<|"
    r"\bnode\s+-e\b|"
    r"\bruby\s+-e\b|"
    r"\bsh\s+-c\b|"
    r"\bbash\s+-c\b"
    r")"
)
ALLOWED_CAUSAL_REPAIR_BASH = (
    "scripts/create-checkpoint.sh",
    "scripts/create-patch-manifest.py",
    "scripts/validate-rca-gate.py",
    "scripts/run-counterfactual.py",
    ".causal-repair/",
)
REQUIRED_RCA_FIELDS = [
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


def run(cmd: Sequence[str], cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, text=True, capture_output=True)


def git_root(cwd: Optional[Path] = None) -> Optional[Path]:
    result = run(["git", "rev-parse", "--show-toplevel"], cwd=cwd)
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip())


def env_bool(env: Dict[str, str], key: str, default: bool) -> bool:
    value = env.get(key)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off", ""}


def tool_name(payload: Dict[str, object]) -> str:
    for key in ("tool_name", "toolName", "name"):
        value = payload.get(key)
        if isinstance(value, str):
            return value
    tool = payload.get("tool")
    if isinstance(tool, dict):
        value = tool.get("name")
        if isinstance(value, str):
            return value
    return ""


def tool_input(payload: Dict[str, object]) -> Dict[str, object]:
    for key in ("tool_input", "toolInput", "input", "parameters", "args"):
        value = payload.get(key)
        if isinstance(value, dict):
            return value
    tool = payload.get("tool")
    if isinstance(tool, dict):
        value = tool.get("input")
        if isinstance(value, dict):
            return value
    return {}


def collect_paths(value: object) -> List[str]:
    paths: List[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            if key in {"path", "file_path", "filepath", "notebook_path"} and isinstance(nested, str):
                paths.append(nested)
            else:
                paths.extend(collect_paths(nested))
    elif isinstance(value, list):
        for nested in value:
            paths.extend(collect_paths(nested))
    return paths


def causal_repair_only_paths(paths: Iterable[str]) -> bool:
    items = list(paths)
    if not items:
        return False
    return all(
        p.startswith(".causal-repair/")
        or p == ".causal-repair"
        or "/.causal-repair/" in p
        for p in items
    )


def valid_checkpoint_dir(path: Path) -> bool:
    base = path / "base-commit.txt"
    status = path / "status-short.txt"
    if not base.exists() or not status.exists():
        return False
    base_text = base.read_text(encoding="utf-8", errors="replace").strip()
    return bool(re.fullmatch(r"[0-9a-fA-F]{40}", base_text))


def latest_valid_checkpoint(root: Path) -> Optional[Path]:
    checkpoints = root / ".causal-repair" / "checkpoints"
    if checkpoints.exists():
        for item in sorted([p for p in checkpoints.iterdir() if p.is_dir()], reverse=True):
            if valid_checkpoint_dir(item):
                return item
    return None


def has_checkpoint(root: Path) -> bool:
    return latest_valid_checkpoint(root) is not None


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


def validate_counterfactual(value: object) -> List[str]:
    errors: List[str] = []
    if not isinstance(value, dict):
        return ["counterfactual_check must be an object with command, result, and evidence"]
    command = value.get("command")
    result = value.get("result")
    evidence = value.get("evidence")
    if not valid_text(command, 4):
        errors.append("counterfactual_check.command is missing or too short")
    if not isinstance(result, str) or result not in ALLOWED_COUNTERFACTUAL_RESULTS:
        errors.append("counterfactual_check.result must be pass, failed, or incomplete")
    if not valid_text(evidence):
        errors.append("counterfactual_check.evidence is missing or too short")
    return errors


def validate_contract_clauses(value: object) -> List[str]:
    # Mirrors scripts/validate-rca-gate.py (the schema is intentionally
    # duplicated between the CLI validator and this hook — keep in sync).
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


def validate_checkpoint_reference(root: Path, value: object) -> List[str]:
    if not isinstance(value, str) or not value.strip():
        return ["checkpoint must be a path string"]
    checkpoint = Path(value)
    if not checkpoint.is_absolute():
        checkpoint = root / checkpoint
    if not checkpoint.exists():
        return ["checkpoint path does not exist"]
    if not valid_checkpoint_dir(checkpoint):
        return ["checkpoint path is missing a valid base-commit.txt"]
    return []


def validate_rca_gate(root: Path) -> Tuple[bool, List[str]]:
    gate_path = root / ".causal-repair" / "rca-gate.json"
    if not gate_path.exists():
        return False, ["missing .causal-repair/rca-gate.json"]
    try:
        data = json.loads(gate_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return False, [f"invalid rca-gate.json: {exc}"]
    if not isinstance(data, dict):
        return False, ["rca-gate.json must be a JSON object"]

    errors: List[str] = []
    for field in REQUIRED_RCA_FIELDS:
        if field not in data or not non_empty(data[field]):
            errors.append(f"missing or empty RCA field: {field}")
    for field in TEXT_RCA_FIELDS:
        if field in data and not valid_text(data[field]):
            errors.append(f"RCA field too short: {field}")

    status = data.get("contract_invariant_status")
    if not isinstance(status, str) or status not in ALLOWED_CONTRACT_STATUS:
        errors.append("contract_invariant_status must be explicit, inferred, or unknown")

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
        if len(tests) < 2:
            errors.append(
                "tests_to_run must contain at least 2 commands: the visible reproduction "
                "and the authored contract tests"
            )
        if not any(CONTRACT_TESTS_TOKEN in item for item in tests):
            errors.append(
                f"tests_to_run must reference the authored contract tests ({CONTRACT_TESTS_TOKEN}*)"
            )

    if "checkpoint" in data:
        errors.extend(validate_checkpoint_reference(root, data["checkpoint"]))

    return not errors, errors


def ledger_gate(root: Path) -> Tuple[bool, str]:
    """Ledger-Relay enforcement (only when .causal-repair/ledger.json exists).

    The ledger externalizes long-horizon state into segments. Production writes
    are allowed only while a `patch`-kind segment is in_progress, so a model
    cannot drift into editing during investigation/review segments. Enforces
    the enforcement-relevant subset of scripts/validate-ledger.py.
    """
    ledger_path = root / ".causal-repair" / "ledger.json"
    if not ledger_path.exists():
        return True, "no ledger (single-segment mode)"
    try:
        data = json.loads(ledger_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return False, f"ledger.json is unreadable: {exc}"
    if not isinstance(data, dict) or not isinstance(data.get("segments"), list):
        return False, "ledger.json must be an object with a segments list"
    active = [
        s for s in data["segments"]
        if isinstance(s, dict) and s.get("status") == "in_progress"
    ]
    if len(active) > 1:
        return False, "ledger has multiple in_progress segments; relay runs one segment at a time"
    if not active:
        return False, "ledger has no in_progress segment; mark the active segment before editing"
    if active[0].get("kind") != "patch":
        return False, (
            "active ledger segment is "
            f"{active[0].get('kind')!r}, not 'patch'; production edits are only allowed "
            "inside a patch segment"
        )
    return True, "active patch segment"


def bash_command(input_data: Dict[str, object]) -> str:
    for key in ("command", "cmd", "script"):
        value = input_data.get(key)
        if isinstance(value, str):
            return value
    return ""


def allowed_causal_repair_command(command: str) -> bool:
    return any(token in command for token in ALLOWED_CAUSAL_REPAIR_BASH)


def evaluate(payload: Dict[str, object], cwd: Optional[Path] = None, env: Optional[Dict[str, str]] = None) -> Tuple[bool, str]:
    env = env or dict(os.environ)
    root = git_root(cwd)
    if root is None:
        return True, "not a git repository"

    name = tool_name(payload)
    input_data = tool_input(payload)
    paths = collect_paths(input_data)

    if name == "Bash":
        command = bash_command(input_data)
        if DANGEROUS_BASH_RE.search(command):
            return False, "Causal Repair blocked destructive git/shell command. Use checkpoint/patch-manifest-based revert instead."
        if env_bool(env, "CAUSAL_REPAIR_STRICT_BASH_WRITES", True):
            has_gate, errors = validate_rca_gate(root)
            if STRICT_BASH_WRITE_RE.search(command) and not allowed_causal_repair_command(command) and not has_gate:
                return False, "Causal Repair blocked write-like Bash before a valid RCA gate: " + "; ".join(errors)
        return True, "bash allowed"

    if name not in WRITE_TOOLS:
        return True, "non-write tool allowed"

    if causal_repair_only_paths(paths):
        return True, "causal-repair metadata edit allowed"

    if env_bool(env, "CAUSAL_REPAIR_REQUIRE_CHECKPOINT", True) and not has_checkpoint(root):
        return False, "Causal Repair blocked edit: create a valid checkpoint first with `bash scripts/create-checkpoint.sh`."

    if env_bool(env, "CAUSAL_REPAIR_REQUIRE_RCA", True):
        ok, errors = validate_rca_gate(root)
        if not ok:
            return False, "Causal Repair blocked edit: valid RCA gate required before patching. " + "; ".join(errors)

    ok, message = ledger_gate(root)
    if not ok:
        return False, "Causal Repair blocked edit: " + message

    return True, "write allowed"


def read_payload() -> Dict[str, object]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("hook input must be a JSON object")
    return value


def main() -> int:
    try:
        payload = read_payload()
        allowed, message = evaluate(payload)
    except Exception as exc:
        print(f"Causal Repair hook error: {exc}", file=sys.stderr)
        return 2

    if allowed:
        return 0

    print(message, file=sys.stderr)
    # Claude Code PreToolUse hooks can block tool execution with a blocking
    # non-zero exit. Exit 2 is used so the message is visible to the model.
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
