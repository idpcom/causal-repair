#!/usr/bin/env python3
"""Change-surface coverage gate: no unexplained behavior change.

Mechanically compares the checkpointed base code with the patched working tree
on a deterministic input pool (differential fuzzing, stdlib-only), yielding the
*change surface* — the set of functions whose observable behavior changed. It
then traces which target functions the broken/at-risk clause witnesses in
`.causal-repair/contract-tests.py` exercise, and enforces:

    every behavior-changed function must be exercised by a broken/at-risk
    clause witness.

A patch that alters behavior no witness looks at is either out of scope or has
an incomplete clause list — rejected either way. Attribution is function-level
(documented limit: a missing clause about a different aspect of the SAME
function can still slip through). Exit 0 = covered; 2 = unexplained change.
Writes `.causal-repair/coverage-result.json`.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

EXCLUDE = (".causal-repair/", ".claude/", "scripts/", "__pycache__/")

# Deterministic argument pool. Values chosen to exercise the corpus's domains
# (numbers, strings with units/separators/paths, containers, edge scalars).
POOL = [
    "0", "1", "-1", "3", "17",
    "0.0", "2.5",
    "''", "'a'", "' b '", "'0x10'", "'x,y'", "'/a//b'", "'3/4'", "'5m'",
    "'1.2.3'", "'read, Write'", "'a\\nb'", "'a\\nb\\n'",
    "[]", "[1, 2, 3]", "[[1, 2], [2, 3]]", "[[3, 4], [1, 2]]",
    "{}", "None", "True", "False",
]
MAX_CALLS_PER_FUNC = 24
CHILD_TIMEOUT = 60

# Child driver: enumerates deterministic calls over public functions/classes of
# a module and prints one JSON outcome per call. Runs identically on base and
# patched trees; any output difference is a behavior difference.
DRIVER = r'''
import inspect, itertools, json, random, sys

MODULE = sys.argv[1]
POOL = json.loads(sys.argv[2])
MAX_CALLS = int(sys.argv[3])

mod = __import__(MODULE)
values = [eval(v) for v in POOL]  # noqa: S307 - fixed literal pool

def outcome(fn, args):
    try:
        r = fn(*args)
        return {"kind": "return", "value": repr(r)[:120]}
    except Exception as exc:  # noqa: BLE001
        return {"kind": type(exc).__name__}

def arg_combos(fn, seed_name=""):
    # Seeded-random index sampling: deterministic yet dispersed across all
    # argument positions (lexicographic product only varies the last arg
    # within a small call budget).
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):
        return
    params = [p for p in sig.parameters.values()
              if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
    n = len(params)
    if n == 0:
        yield ()
        return
    rng = random.Random(f"pool:{seed_name}:{n}")
    seen = set()
    for _ in range(MAX_CALLS * 3):
        if len(seen) >= MAX_CALLS:
            return
        combo = tuple(rng.randrange(len(values)) for _ in range(n))
        if combo in seen:
            continue
        seen.add(combo)
        yield tuple(values[i] for i in combo)

results = []
names = sorted(n for n in dir(mod) if not n.startswith("_"))
for name in names:
    obj = getattr(mod, name)
    if inspect.isfunction(obj) and obj.__module__ == MODULE:
        for args in arg_combos(obj, name):
            results.append({"call": f"{name}{args!r}", "func": name,
                            "out": outcome(obj, args)})
    elif inspect.isclass(obj) and obj.__module__ == MODULE:
        # deterministic short method sequences on fresh instances
        ctor_combos = list(itertools.islice(arg_combos(obj.__init__, name), 6)) or [()]
        methods = sorted(m for m in dir(obj) if not m.startswith("_"))
        for ctor_args in ctor_combos:
            real_ctor = ctor_args[1:] if ctor_args else ()
            for m in methods:
                fn = getattr(obj, m, None)
                if not callable(fn):
                    continue
                for margs in itertools.islice(arg_combos(fn, f"{name}.{m}"), 4):
                    rmargs = margs[1:] if margs else ()
                    def run():
                        inst = obj(*real_ctor)
                        meth = getattr(inst, m)
                        return meth(*rmargs)
                    try:
                        r = run()
                        out = {"kind": "return", "value": repr(r)[:120]}
                    except Exception as exc:  # noqa: BLE001
                        out = {"kind": type(exc).__name__}
                    results.append({"call": f"{name}({real_ctor!r}).{m}{rmargs!r}",
                                    "func": f"{name}.{m}", "out": out})
print(json.dumps(results))
'''

# Child tracer: wraps target-module functions/methods with counters, then runs
# the given witness indices; prints the set of touched target functions.
TRACER = r'''
import importlib.util, json, sys

TESTS = sys.argv[1]
MODULES = json.loads(sys.argv[2])
IDXS = json.loads(sys.argv[3])

touched = set()

def wrap(qual, fn):
    def inner(*a, **k):
        touched.add(qual)
        return fn(*a, **k)
    return inner

for mname in MODULES:
    mod = __import__(mname)
    for name in dir(mod):
        if name.startswith("_"):
            continue
        obj = getattr(mod, name)
        if callable(obj) and getattr(obj, "__module__", None) == mname:
            if isinstance(obj, type):
                for m in dir(obj):
                    if m.startswith("_"):
                        continue
                    meth = getattr(obj, m, None)
                    if callable(meth):
                        try:
                            setattr(obj, m, wrap(f"{name}.{m}", meth))
                        except (AttributeError, TypeError):
                            pass
            else:
                setattr(mod, name, wrap(name, obj))

spec = importlib.util.spec_from_file_location("ct", TESTS)
ct = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ct)
for i in IDXS:
    try:
        ct.WITNESSES[i]()
    except Exception:  # noqa: BLE001 - coverage only; pass/fail is not our job
        pass
print(json.dumps(sorted(touched)))
'''


def run(cmd: Sequence[str], cwd: Path, timeout: int = CHILD_TIMEOUT) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(cwd) + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True,
                          timeout=timeout, env=env)


def changed_modules(repo: Path) -> List[str]:
    out = run(["git", "diff", "--name-only", "HEAD"], repo).stdout.splitlines()
    mods = []
    for rel in out:
        rel = rel.strip()
        if not rel.endswith(".py") or any(rel.startswith(p) for p in EXCLUDE):
            continue
        if "/" not in rel:  # corpus tasks keep modules at repo root
            mods.append(rel[:-3])
    return mods


def outcomes(repo: Path, module: str) -> Optional[List[dict]]:
    r = run([sys.executable, "-c", DRIVER, module, json.dumps(POOL),
             str(MAX_CALLS_PER_FUNC)], repo)
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        return None


def base_tree(repo: Path, mods: List[str], tmp: Path) -> Path:
    base = tmp / "base"
    shutil.copytree(repo, base, ignore=shutil.ignore_patterns(".git", "__pycache__"))
    for m in mods:
        head = run(["git", "show", f"HEAD:{m}.py"], repo)
        if head.returncode == 0:
            (base / f"{m}.py").write_text(head.stdout, encoding="utf-8")
    return base


def change_surface(repo: Path, base: Path, mods: List[str]) -> Tuple[Dict[str, List[str]], List[str]]:
    surface: Dict[str, List[str]] = {}
    errors: List[str] = []
    for m in mods:
        after = outcomes(repo, m)
        before = outcomes(base, m)
        if after is None or before is None:
            errors.append(f"module {m}: driver failed (import error or crash)")
            continue
        bmap = {r["call"]: r["out"] for r in before}
        for r in after:
            b = bmap.get(r["call"])
            if b is not None and b != r["out"]:
                surface.setdefault(r["func"], []).append(r["call"])
    return surface, errors


def witness_touched(repo: Path, mods: List[str], tests_rel: str,
                    idxs: List[int]) -> Optional[List[str]]:
    r = run([sys.executable, "-c", TRACER, tests_rel, json.dumps(mods),
             json.dumps(idxs)], repo)
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        return None


def changing_clause_indices(gate: Dict[str, object]) -> List[int]:
    idxs = []
    for i, c in enumerate(gate.get("contract_clauses", []), 1):
        if isinstance(c, dict) and c.get("status") in ("broken", "at-risk"):
            idxs.append(i)
    return idxs


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Change-surface coverage gate")
    p.add_argument("--repo", type=Path, default=Path("."))
    p.add_argument("--gate", type=Path, default=Path(".causal-repair/rca-gate.json"))
    p.add_argument("--tests", default=".causal-repair/contract-tests.py")
    return p.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    repo = args.repo.resolve()
    mods = changed_modules(repo)
    if not mods:
        print("coverage FAIL: no changed production modules", file=sys.stderr)
        return 2
    try:
        gate = json.loads((repo / args.gate).read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"coverage FAIL: unreadable gate: {exc}", file=sys.stderr)
        return 2
    idxs = changing_clause_indices(gate)
    if not idxs:
        print("coverage FAIL: gate has no broken/at-risk clause to explain any change",
              file=sys.stderr)
        return 2
    if not (repo / args.tests).exists():
        print(f"coverage FAIL: missing {args.tests}", file=sys.stderr)
        return 2

    with tempfile.TemporaryDirectory() as tmp:
        base = base_tree(repo, mods, Path(tmp))
        surface, errors = change_surface(repo, base, mods)
    touched = witness_touched(repo, mods, args.tests, idxs)
    if touched is None:
        print("coverage FAIL: could not trace witnesses (WITNESSES missing or import error)",
              file=sys.stderr)
        return 2

    uncovered = {f: calls[:5] for f, calls in surface.items() if f not in set(touched)}
    result = {
        "ok": not uncovered and not errors,
        "changed_modules": mods,
        "change_surface": {f: len(c) for f, c in surface.items()},
        "witness_touched": touched,
        "uncovered": uncovered,
        "driver_errors": errors,
    }
    (repo / ".causal-repair").mkdir(exist_ok=True)
    (repo / ".causal-repair" / "coverage-result.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8")

    if errors:
        for e in errors:
            print(f"coverage FAIL: {e}", file=sys.stderr)
        return 2
    if uncovered:
        for f, calls in uncovered.items():
            print(f"coverage FAIL: behavior of {f} changed but no broken/at-risk witness "
                  f"exercises it (e.g. {calls[0]})", file=sys.stderr)
        return 2
    print(f"coverage ok: {len(surface)} changed function(s), all witness-covered")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
