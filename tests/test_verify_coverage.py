from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify-coverage.py"

BASE_MAIN = '''def clamp(x, lo, hi):
    """Constrain x to [lo, hi]."""
    if x > hi:
        return hi
    return x
'''

GOOD_MAIN = '''def clamp(x, lo, hi):
    """Constrain x to [lo, hi]."""
    if x < lo:
        return lo
    if x > hi:
        return hi
    return x
'''

BASE_OTHER = '''def greet(name):
    """Return a greeting."""
    return "hello " + str(name)
'''

# scope creep: out-of-scope behavior change in a module no witness looks at
CREEP_OTHER = '''def greet(name):
    """Return a greeting."""
    return "HELLO " + str(name)
'''

TESTS = '''from main import clamp

def clause_1():
    assert clamp(-5, 0, 10) == 0
    assert clamp(1, 2, 10) == 2

WITNESSES = {1: clause_1}
'''

GATE = {"contract_clauses": [
    {"clause": "values below lo clamp to lo", "status": "broken", "covered_by": "clause_1"},
]}


def make_repo(main_src: str, other_src: str) -> Path:
    tmp = Path(tempfile.mkdtemp())
    (tmp / "main.py").write_text(BASE_MAIN, encoding="utf-8")
    (tmp / "other.py").write_text(BASE_OTHER, encoding="utf-8")
    for cmd in (["git", "init"], ["git", "config", "user.email", "a@b.c"],
                ["git", "config", "user.name", "a"], ["git", "add", "-A"],
                ["git", "commit", "-m", "base"]):
        subprocess.run(cmd, cwd=tmp, capture_output=True, check=True)
    (tmp / "main.py").write_text(main_src, encoding="utf-8")
    (tmp / "other.py").write_text(other_src, encoding="utf-8")
    meta = tmp / ".causal-repair"
    meta.mkdir()
    (meta / "contract-tests.py").write_text(TESTS, encoding="utf-8")
    (meta / "rca-gate.json").write_text(json.dumps(GATE), encoding="utf-8")
    return tmp


def gate(repo: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), "--repo", str(repo)],
                          capture_output=True, text=True)


class VerifyCoverageTest(unittest.TestCase):
    def test_clean_fix_passes(self) -> None:
        repo = make_repo(GOOD_MAIN, BASE_OTHER)
        self.addCleanup(lambda: shutil.rmtree(repo))
        r = gate(repo)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        result = json.loads((repo / ".causal-repair" / "coverage-result.json").read_text())
        self.assertTrue(result["ok"])
        self.assertIn("clamp", result["change_surface"])

    def test_scope_creep_rejected(self) -> None:
        repo = make_repo(GOOD_MAIN, CREEP_OTHER)
        self.addCleanup(lambda: shutil.rmtree(repo))
        r = gate(repo)
        self.assertEqual(r.returncode, 2)
        self.assertIn("greet", r.stderr)
        self.assertIn("no broken/at-risk witness", r.stderr)

    def test_no_changing_clause_rejected(self) -> None:
        repo = make_repo(GOOD_MAIN, BASE_OTHER)
        self.addCleanup(lambda: shutil.rmtree(repo))
        g = {"contract_clauses": [
            {"clause": "values below lo clamp to lo", "status": "held", "covered_by": "x"}]}
        (repo / ".causal-repair" / "rca-gate.json").write_text(json.dumps(g), encoding="utf-8")
        r = gate(repo)
        self.assertEqual(r.returncode, 2)
        self.assertIn("no broken/at-risk clause", r.stderr)


if __name__ == "__main__":
    unittest.main()
