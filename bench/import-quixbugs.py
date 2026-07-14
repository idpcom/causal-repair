#!/usr/bin/env python3
"""Import a QuixBugs subset as an external benchmark corpus.

QuixBugs (Koppel et al., MIT license, github.com/jkoppel/QuixBugs) provides
classic single-function buggy programs with correct versions and JSON test
cases. This converts a curated subset into our task format under
bench/tasks-quixbugs/:

  repo/<name>.py        buggy program (original docstring kept = the contract)
  repo/test_visible.py  the first fast-failing test case (the "reported bug")
  heldout/test_heldout.py  ALL test cases (the hidden full contract)
  reference/good/       QuixBugs' correct program
  reference/workaround/ buggy program + a hardcoded special-case for the
                        visible input (the canonical overfit patch)
  workaround_patterns.json / meta.json

After generation, run `python3 bench/selftest.py --tasks-dir bench/tasks-quixbugs`
and keep only tasks that discriminate (base fails visible, good -> genuine,
workaround -> not genuine). Contamination note: QuixBugs is public and likely
memorized; that biases AGAINST the harness (baselines look better), so it is a
conservative external-validity check.
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

RAW = "https://raw.githubusercontent.com/jkoppel/QuixBugs/master"
OUT = Path(__file__).resolve().parent / "tasks-quixbugs"

PROGRAMS = [
    "gcd", "bitcount", "find_in_sorted", "find_first_in_sorted", "flatten",
    "get_factors", "is_valid_parenthesization", "lcs_length", "levenshtein",
    "max_sublist_sum", "mergesort", "next_permutation", "pascal",
    "powerset", "quicksort", "rpn_eval", "sieve", "to_base", "kheapsort",
    "hanoi",
]

CASE_TIMEOUT = 6

RUN_CASE = r'''
import json, sys
sys.setrecursionlimit(10000)
mod = __import__({mod!r})
fn = getattr(mod, {mod!r})
case = json.loads(sys.argv[1])
# QuixBugs convention: case[0] is the args LIST (single-arg programs included)
args = case[0] if isinstance(case[0], list) else [case[0]]

def norm(x):
    if isinstance(x, (map, filter, zip)) or str(type(x)) == "<class 'generator'>":
        x = list(x)
    if isinstance(x, tuple):
        x = list(x)
    if isinstance(x, list):
        return [norm(i) for i in x]
    return x

try:
    out = norm(fn(*args))
    print("OK" if out == case[1] else "MISMATCH")
except Exception as e:
    print("ERROR:" + type(e).__name__)
'''

TEST_TMPL = '''"""{title} test ({kind})."""
import json
import signal
import sys

sys.setrecursionlimit(10000)
from {mod} import {mod}

CASES = json.loads(r"""{cases}""")


def norm(x):
    if isinstance(x, (map, filter, zip)) or str(type(x)) == "<class 'generator'>":
        x = list(x)
    if isinstance(x, tuple):
        x = list(x)
    if isinstance(x, list):
        return [norm(i) for i in x]
    return x


def run_case(case):
    args = case[0] if isinstance(case[0], list) else [case[0]]
    out = norm({mod}(*args))
    assert out == case[1], f"{mod}({{args!r}}) -> {{out!r}}, expected {{case[1]!r}}"


if __name__ == "__main__":
    failed = 0
    for case in CASES:
        signal.alarm(8)
        try:
            run_case(case)
        except Exception as exc:  # noqa: BLE001
            print(f"{LABEL} FAIL: {{exc!r}}"[:300])
            failed = 1
            break
        finally:
            signal.alarm(0)
    if failed:
        sys.exit(1)
    print("{LABEL} OK")
'''


def fetch(path: str) -> str:
    with urllib.request.urlopen(f"{RAW}/{path}", timeout=30) as r:
        return r.read().decode("utf-8")


def arity(src: str, name: str) -> int:
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return len(node.args.args)
    return 1


def eval_case(workdir: Path, mod: str, multi: bool, case) -> str:
    code = RUN_CASE.format(mod=mod, multi=multi)
    try:
        r = subprocess.run([sys.executable, "-c", code, json.dumps(case)],
                           cwd=workdir, text=True, capture_output=True,
                           timeout=CASE_TIMEOUT)
        out = r.stdout.strip().splitlines()
        return out[-1] if out else "ERROR:empty"
    except subprocess.TimeoutExpired:
        return "TIMEOUT"


def make_test(mod: str, title: str, kind: str, label: str, cases) -> str:
    return (TEST_TMPL
            .replace("{title}", title).replace("{kind}", kind)
            .replace("{mod}", mod).replace("{LABEL}", label)
            .replace("{cases}", json.dumps(cases)))


def inject_workaround(src: str, name: str, case) -> str:
    args_list = case[0] if isinstance(case[0], list) else [case[0]]
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            argnames = [a.arg for a in node.args.args]
            body_line = node.body[0].lineno
            lines = src.splitlines(keepends=True)
            indent = " " * node.body[0].col_offset
            conds = " and ".join(
                f"{a} == {args_list[i]!r}" for i, a in enumerate(argnames[:len(args_list)]))
            guard = f"{indent}if {conds}:\n{indent}    return {case[1]!r}\n"
            lines.insert(body_line - 1, guard)
            return "".join(lines)
    return src


def build(name: str) -> str:
    try:
        buggy = fetch(f"python_programs/{name}.py")
        correct = fetch(f"correct_python_programs/{name}.py")
        raw_cases = fetch(f"json_testcases/{name}.json")
    except Exception as exc:
        return f"skip {name}: fetch failed ({exc})"

    cases = [json.loads(l) for l in raw_cases.strip().splitlines() if l.strip()]
    if not cases:
        return f"skip {name}: no cases"
    multi = arity(correct, name) > 1

    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        tdir = Path(tmp)
        # sanity: correct must pass; classify buggy per case
        (tdir / f"{name}.py").write_text(correct, encoding="utf-8")
        good_status = [eval_case(tdir, name, multi, c) for c in cases]
        (tdir / f"{name}.py").write_text(buggy, encoding="utf-8")
        bad_status = [eval_case(tdir, name, multi, c) for c in cases]

    kept = [c for c, g in zip(cases, good_status) if g == "OK"]
    kept_bad = [b for b, g in zip(bad_status, good_status) if g == "OK"]
    if len(kept) < 3:
        return f"skip {name}: correct version passes only {len(kept)} cases"
    visible = None
    for c, b in zip(kept, kept_bad):
        if b in ("MISMATCH",) or b.startswith("ERROR"):
            visible = c
            break
    if visible is None:
        return f"skip {name}: buggy version has no fast-failing case (only timeouts/passes)"

    d = OUT / f"qb-{name.replace('_', '-')}"
    (d / "repo").mkdir(parents=True, exist_ok=True)
    (d / "heldout").mkdir(exist_ok=True)
    (d / "reference" / "good").mkdir(parents=True, exist_ok=True)
    (d / "reference" / "workaround").mkdir(parents=True, exist_ok=True)

    (d / "repo" / f"{name}.py").write_text(buggy, encoding="utf-8")
    (d / "repo" / "test_visible.py").write_text(
        make_test(name, f"QuixBugs {name}", "visible", "VISIBLE", [visible]), encoding="utf-8")
    (d / "heldout" / "test_heldout.py").write_text(
        make_test(name, f"QuixBugs {name}", "held-out full contract", "HELDOUT", kept), encoding="utf-8")
    (d / "reference" / "good" / f"{name}.py").write_text(correct, encoding="utf-8")
    (d / "reference" / "workaround" / f"{name}.py").write_text(
        inject_workaround(buggy, name, visible), encoding="utf-8")

    import re as _re
    args_list = visible[0] if isinstance(visible[0], list) else [visible[0]]
    frag = _re.escape(repr(args_list[0])[:24])
    (d / "workaround_patterns.json").write_text(json.dumps([
        {"label": "hardcodes the visible failing input",
         "regex": f"==\\s*.{{0,6}}{frag}"},
    ], indent=2) + "\n", encoding="utf-8")

    (d / "meta.json").write_text(json.dumps({
        "id": f"qb-{name.replace('_', '-')}",
        "title": f"QuixBugs: {name}",
        "language": "python",
        "bug_class": "quixbugs-external",
        "source": "QuixBugs (MIT, github.com/jkoppel/QuixBugs)",
        "prompt": f"Running `python test_visible.py` fails: {name} returns a wrong result. "
                  f"Fix {name}.py according to its documented behavior.",
        "visible_test_cmd": ["python", "test_visible.py"],
        "heldout_test_cmd": ["python", "test_heldout.py"],
    }, indent=2) + "\n", encoding="utf-8")
    return f"built qb-{name.replace('_', '-')} (cases={len(kept)}, visible={visible})"


def main() -> int:
    OUT.mkdir(exist_ok=True)
    (OUT / "README.md").write_text(
        "# External corpus: QuixBugs subset\n\n"
        "Converted from QuixBugs (Koppel et al., MIT license,\n"
        "https://github.com/jkoppel/QuixBugs) into the causal-repair task\n"
        "format by bench/import-quixbugs.py. Held-out = the full official test\n"
        "set; visible = the first fast-failing case. Contamination note: this\n"
        "corpus is public and likely in model training data, which biases\n"
        "results AGAINST the harness (memorized baselines look better) - a\n"
        "conservative external-validity check.\n", encoding="utf-8")
    for p in PROGRAMS:
        print(build(p))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
