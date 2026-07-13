from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify-witnesses.py"

BASE = '''class BoundedStack:
    def __init__(self, capacity):
        self.capacity = capacity
        self._items = []

    def push(self, x):
        self._items.append(x)

    def pop(self):
        return self._items.pop(0)
'''

GOOD = '''class BoundedStack:
    def __init__(self, capacity):
        if not isinstance(capacity, int) or capacity < 1:
            raise ValueError("capacity must be >= 1")
        self.capacity = capacity
        self._items = []

    def push(self, x):
        if len(self._items) >= self.capacity:
            raise OverflowError("full")
        self._items.append(x)

    def pop(self):
        return self._items.pop()
'''

INCOMPLETE = '''class BoundedStack:
    def __init__(self, capacity):
        self.capacity = capacity
        self._items = []

    def push(self, x):
        self._items.append(x)

    def pop(self):
        return self._items.pop()
'''

TESTS = '''from bstack import BoundedStack

def clause_1():
    s = BoundedStack(5)
    for x in (1, 2, 3):
        s.push(x)
    assert s.pop() == 3 and s.pop() == 2

def clause_2():
    s = BoundedStack(2); s.push(1); s.push(2)
    try:
        s.push(3)
    except OverflowError:
        pass
    else:
        raise AssertionError("must raise OverflowError")

def clause_3():
    try:
        BoundedStack(0)
    except ValueError:
        pass
    else:
        raise AssertionError("must raise ValueError")

WITNESSES = {1: clause_1, 2: clause_2, 3: clause_3}
'''

GATE = {
    "contract_clauses": [
        {"clause": "pop returns most recently pushed (LIFO)", "status": "broken", "covered_by": "clause_1"},
        {"clause": "push beyond capacity must raise OverflowError", "status": "at-risk", "covered_by": "clause_2"},
        {"clause": "capacity < 1 must raise ValueError", "status": "at-risk", "covered_by": "clause_3"},
    ]
}


def make_repo(fix: str) -> Path:
    tmp = Path(tempfile.mkdtemp())
    (tmp / "bstack.py").write_text(BASE, encoding="utf-8")
    for cmd in (["git", "init"], ["git", "config", "user.email", "a@b.c"],
                ["git", "config", "user.name", "a"], ["git", "add", "-A"],
                ["git", "commit", "-m", "base"]):
        subprocess.run(cmd, cwd=tmp, capture_output=True, check=True)
    (tmp / "bstack.py").write_text(fix, encoding="utf-8")  # patch in working tree
    meta = tmp / ".causal-repair"
    meta.mkdir()
    (meta / "contract-tests.py").write_text(TESTS, encoding="utf-8")
    (meta / "rca-gate.json").write_text(json.dumps(GATE), encoding="utf-8")
    return tmp


def verify(repo: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), "--repo", str(repo)],
                          capture_output=True, text=True)


class VerifyWitnessesTest(unittest.TestCase):
    def test_good_patch_witnesses_hold(self) -> None:
        repo = make_repo(GOOD)
        self.addCleanup(lambda: shutil.rmtree(repo))
        r = verify(repo)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_incomplete_patch_rejected(self) -> None:
        # only LIFO fixed; overflow + capacity clauses left unimplemented
        repo = make_repo(INCOMPLETE)
        self.addCleanup(lambda: shutil.rmtree(repo))
        r = verify(repo)
        self.assertEqual(r.returncode, 2)
        self.assertIn("witness FAIL (state)", r.stderr)
        self.assertIn("not restored", r.stderr)

    def test_missing_witness_rejected(self) -> None:
        repo = make_repo(GOOD)
        self.addCleanup(lambda: shutil.rmtree(repo))
        # drop clause_3 from WITNESSES -> a gate clause has no witness
        ct = (repo / ".causal-repair" / "contract-tests.py")
        ct.write_text(TESTS.replace(", 3: clause_3", ""), encoding="utf-8")
        r = verify(repo)
        self.assertEqual(r.returncode, 2)
        self.assertIn("no witness", r.stderr)


if __name__ == "__main__":
    unittest.main()
