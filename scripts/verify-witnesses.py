#!/usr/bin/env python3
"""Proof-Carrying Repair witness checker.

A patch must carry mechanically checkable evidence, not a claim of correctness.
The RCA gate lists contract_clauses each with a status (broken/held/at-risk).
`.causal-repair/contract-tests.py` must expose one witness function per clause
and a WITNESSES dict mapping the 1-based clause index to it:

    def clause_1(): ...   # asserts clause 1; raises on violation
    def clause_2(): ...
    WITNESSES = {1: clause_1, 2: clause_2, ...}

Two witnesses are enforced:

  STATE (per clause) — each clause's witness must PASS on the patched working
    tree (the fix restores every clause), and on the checkpointed BASE code it
    must FAIL for broken/at-risk clauses and PASS for held clauses. This is what
    a claim of status *predicts*; a mismatch (e.g. a "broken" clause whose test
    already passes on the buggy base, or an "at-risk" clause the patch leaves
    unimplemented) is rejected. A missing witness for any clause is rejected.

  STRENGTH — deterministic mutants of the patched target files must be killed by
    the full witness suite (mutation score >= threshold); if the gate documents
    an error contract, a `raise`-removal mutant must be killed. Catches vacuous
    tests that are present but assert nothing.

Exit 0 = both hold; 2 = a witness failed. Writes witness-result.json.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

_spec = importlib.util.spec_from_file_location("mutate", Path(__file__).resolve().parent / "mutate.py")
mutate = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(mutate)

EXCLUDE = (".causal-repair/", ".claude/", "scripts/", "__pycache__/")
DEFAULT_MUT_THRESHOLD = 0.5


def run(cmd: Sequence[str], cwd: Path, env: Optional[dict] = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True, env=env)


def _env(repo: Path) -> dict:
    e = dict(os.environ)
    e["PYTHONPATH"] = str(repo) + os.pathsep + e.get("PYTHONPATH", "")
    return e


def changed_targets(repo: Path) -> List[str]:
    out = run(["git", "diff", "--name-only", "HEAD"], repo).stdout.splitlines()
    targets = []
    for rel in out:
        rel = rel.strip()
        if not rel or not rel.endswith(".py"):
            continue
        if any(rel.startswith(p) for p in EXCLUDE) or "__pycache__/" in rel:
            continue
        targets.append(rel)
    return targets


CLAUSE_DRIVER = (
    "import importlib.util as u\n"
    "s=u.spec_from_file_location('ct', {tests!r})\n"
    "m=u.module_from_spec(s); s.loader.exec_module(m)\n"
    "m.WITNESSES[{idx}]()\n"
)


def witness_indices(repo: Path, tests_rel: str) -> Optional[List[int]]:
    """Load WITNESSES keys without executing clause bodies against any code."""
    code = (
        "import importlib.util as u, json, sys\n"
        f"s=u.spec_from_file_location('ct', {tests_rel!r})\n"
        "m=u.module_from_spec(s); s.loader.exec_module(m)\n"
        "print(json.dumps(sorted(int(k) for k in m.WITNESSES)))\n"
    )
    r = run([sys.executable, "-c", code], repo, env=_env(repo))
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        return None


def run_clause(repo: Path, tests_rel: str, idx: int) -> bool:
    r = run([sys.executable, "-c", CLAUSE_DRIVER.format(tests=tests_rel, idx=idx)], repo, env=_env(repo))
    return r.returncode == 0


def base_tree(repo: Path, targets: List[str], tmp: Path) -> Path:
    base = tmp / "base"
    shutil.copytree(repo, base, ignore=shutil.ignore_patterns(".git", "__pycache__"))
    for rel in targets:
        head = run(["git", "show", f"HEAD:{rel}"], repo)
        if head.returncode == 0:
            (base / rel).write_text(head.stdout, encoding="utf-8")
    return base


def state_witness(repo: Path, tests_rel: str, gate: Dict[str, object],
                  targets: List[str]) -> Tuple[bool, Dict[str, object]]:
    clauses = gate.get("contract_clauses", [])
    idxs = witness_indices(repo, tests_rel)
    if idxs is None:
        return False, {"error": "contract-tests.py has no importable WITNESSES dict"}
    problems = []
    with tempfile.TemporaryDirectory() as tmp:
        base = base_tree(repo, targets, Path(tmp))
        details = []
        for i, clause in enumerate(clauses, 1):
            status = clause.get("status")
            if i not in idxs:
                problems.append(f"clause {i} ({status}) has no witness in WITNESSES")
                continue
            patched_pass = run_clause(repo, tests_rel, i)
            base_pass = run_clause(base, tests_rel, i)
            expect_base_pass = status == "held"
            row = {"clause": i, "status": status, "patched_pass": patched_pass, "base_pass": base_pass}
            details.append(row)
            if not patched_pass:
                problems.append(f"clause {i} ({status}) witness FAILS on the patch (not restored)")
            if base_pass != expect_base_pass:
                if status == "held":
                    problems.append(f"clause {i} marked held but its witness fails on base")
                else:
                    problems.append(f"clause {i} marked {status} but its witness already passes on the buggy base (weak/vacuous test)")
    return (not problems), {"problems": problems, "clauses": details, "witness_indices": idxs}


def has_error_contract(gate: Dict[str, object]) -> bool:
    text = json.dumps(gate.get("contract_clauses", []))
    return any(k in text for k in ("raise", "Error", "Exception", "must reject", "must raise"))


def full_suite_pass(repo: Path, tests_rel: str, idxs: List[int]) -> bool:
    return all(run_clause(repo, tests_rel, i) for i in idxs)


def strength_witness(repo: Path, tests_rel: str, targets: List[str], gate: Dict[str, object],
                     idxs: List[int], threshold: float) -> Tuple[bool, Dict[str, object]]:
    total = killed = raise_seen = raise_killed = 0
    for rel in targets:
        path = repo / rel
        original = path.read_text(encoding="utf-8")
        try:
            muts = mutate.generate(original)
        except SyntaxError:
            muts = []
        for desc, mutated in muts:
            path.write_text(mutated, encoding="utf-8")
            try:
                survived = full_suite_pass(repo, tests_rel, idxs)
            finally:
                path.write_text(original, encoding="utf-8")
            total += 1
            if not survived:
                killed += 1
            if desc.startswith("remove raise"):
                raise_seen += 1
                raise_killed += 0 if survived else 1
    score = (killed / total) if total else 0.0
    need_raise = has_error_contract(gate)
    raise_ok = (not need_raise) or raise_seen == 0 or raise_killed > 0
    ok = total > 0 and score >= threshold and raise_ok
    return ok, {
        "mutation_score": round(score, 3), "threshold": threshold,
        "killed": killed, "total": total,
        "error_contract_required": need_raise,
        "raise_mutants_seen": raise_seen, "raise_mutants_killed": raise_killed,
        "raise_witness_ok": raise_ok,
    }


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Proof-Carrying Repair witness checker")
    p.add_argument("--repo", type=Path, default=Path("."))
    p.add_argument("--gate", type=Path, default=Path(".causal-repair/rca-gate.json"))
    p.add_argument("--tests", default=".causal-repair/contract-tests.py")
    p.add_argument("--threshold", type=float, default=DEFAULT_MUT_THRESHOLD)
    return p.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    repo = args.repo.resolve()
    if not (repo / args.tests).exists():
        print(f"witness FAIL: missing {args.tests}", file=sys.stderr)
        return 2
    try:
        gate = json.loads((repo / args.gate).read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"witness FAIL: unreadable RCA gate: {exc}", file=sys.stderr)
        return 2
    targets = changed_targets(repo)
    if not targets:
        print("witness FAIL: no changed production files to witness", file=sys.stderr)
        return 2

    state_ok, state_info = state_witness(repo, args.tests, gate, targets)
    idxs = state_info.get("witness_indices") or []
    strength_ok, strength_info = strength_witness(repo, args.tests, targets, gate, idxs, args.threshold) \
        if idxs else (False, {"error": "no witnesses to run for strength"})
    ok = state_ok and strength_ok

    result = {"ok": ok, "targets": targets,
              "state_witness": {"ok": state_ok, **state_info},
              "strength_witness": {"ok": strength_ok, **strength_info}}
    (repo / ".causal-repair").mkdir(exist_ok=True)
    (repo / ".causal-repair" / "witness-result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    if ok:
        print(f"witnesses hold: {len(state_info.get('clauses', []))} clauses, "
              f"mutation score {strength_info.get('mutation_score')}")
        return 0
    for pb in state_info.get("problems", []):
        print(f"witness FAIL (state): {pb}", file=sys.stderr)
    if not strength_ok and state_ok:
        print(f"witness FAIL (strength): score {strength_info.get('mutation_score')} < {args.threshold} "
              f"or error-contract raise-mutant survived", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
