from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate-ledger.py"

spec = importlib.util.spec_from_file_location("validate_ledger", SCRIPT)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)


def make_ledger() -> dict:
    return {
        "goal": "Fix the failing parse_bool contract while keeping invalid input rejected.",
        "segments": [
            {
                "id": "s1-investigate",
                "kind": "investigate",
                "objective": "Reproduce the failure and enumerate documented contract clauses.",
                "done_criteria": "python test_visible.py",
                "status": "done",
                "evidence": "Visible test fails with KeyError('1'); docstring documents ValueError on invalid input.",
            },
            {
                "id": "s2-patch",
                "kind": "patch",
                "objective": "Restore the full documented contract in flags.py.",
                "done_criteria": "python .causal-repair/contract-tests.py",
                "status": "in_progress",
            },
        ],
        "attempts": 0,
        "stop_condition": "Two rounds without new evidence, or contract tests keep failing.",
    }


class ValidateLedgerTest(unittest.TestCase):
    def test_valid_ledger_passes(self) -> None:
        ok, errors = mod.validate_ledger(make_ledger())
        self.assertTrue(ok, errors)

    def test_rejects_empty_segments(self) -> None:
        ledger = make_ledger()
        ledger["segments"] = []
        ok, errors = mod.validate_ledger(ledger)
        self.assertFalse(ok)
        self.assertTrue(any("segments" in e for e in errors))

    def test_rejects_bad_kind_and_status(self) -> None:
        ledger = make_ledger()
        ledger["segments"][1]["kind"] = "vibes"
        ledger["segments"][1]["status"] = "sorta"
        ok, errors = mod.validate_ledger(ledger)
        self.assertFalse(ok)
        self.assertTrue(any(".kind" in e for e in errors))
        self.assertTrue(any(".status" in e for e in errors))

    def test_rejects_two_in_progress_segments(self) -> None:
        ledger = make_ledger()
        ledger["segments"][0]["status"] = "in_progress"
        ok, errors = mod.validate_ledger(ledger)
        self.assertFalse(ok)
        self.assertTrue(any("at most one segment" in e for e in errors))

    def test_rejects_duplicate_segment_ids(self) -> None:
        ledger = make_ledger()
        ledger["segments"][1]["id"] = ledger["segments"][0]["id"]
        ok, errors = mod.validate_ledger(ledger)
        self.assertFalse(ok)
        self.assertTrue(any("duplicates" in e for e in errors))

    def test_done_segment_requires_evidence(self) -> None:
        ledger = make_ledger()
        del ledger["segments"][0]["evidence"]
        ok, errors = mod.validate_ledger(ledger)
        self.assertFalse(ok)
        self.assertTrue(any("evidence is required" in e for e in errors))

    def test_rejects_attempts_beyond_limit(self) -> None:
        ledger = make_ledger()
        ledger["attempts"] = 3
        ok, errors = mod.validate_ledger(ledger)
        self.assertFalse(ok)
        self.assertTrue(any("attempts exceeds" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
