from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate-rca-gate.py"
CHECKPOINT = ROOT / "scripts" / "create-checkpoint.sh"
RCA_EXAMPLE = ROOT / "examples" / "rca-gate.example.json"

spec = importlib.util.spec_from_file_location("validate_rca_gate", SCRIPT)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)


def run(cmd, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True, check=True)


class ValidateRcaGateTest(unittest.TestCase):
    def make_repo(self) -> Path:
        tmp = Path(tempfile.mkdtemp())
        run(["git", "init"], tmp)
        run(["git", "config", "user.email", "test@example.com"], tmp)
        run(["git", "config", "user.name", "Test User"], tmp)
        (tmp / "app.py").write_text("print('hello')\n", encoding="utf-8")
        run(["git", "add", "app.py"], tmp)
        run(["git", "commit", "-m", "initial"], tmp)
        return tmp

    def test_rejects_empty_ceremony_gate(self) -> None:
        data = {key: "x" for key in mod.REQUIRED_FIELDS}
        data["contract_invariant_status"] = "unknown"
        ok, errors = mod.validate_gate(data)
        self.assertFalse(ok)
        self.assertTrue(any("too short" in error for error in errors))
        self.assertTrue(any("counterfactual_check" in error for error in errors))

    def test_rejects_missing_contract_clauses(self) -> None:
        data = json.loads(RCA_EXAMPLE.read_text(encoding="utf-8"))
        del data["contract_clauses"]
        ok, errors = mod.validate_gate(data)
        self.assertFalse(ok)
        self.assertTrue(any("contract_clauses" in error for error in errors))

    def test_rejects_malformed_contract_clause(self) -> None:
        data = json.loads(RCA_EXAMPLE.read_text(encoding="utf-8"))
        data["contract_clauses"] = [{"clause": "x", "status": "maybe", "covered_by": ""}]
        ok, errors = mod.validate_gate(data)
        self.assertFalse(ok)
        self.assertTrue(any("contract_clauses[0].clause" in error for error in errors))
        self.assertTrue(any("contract_clauses[0].status" in error for error in errors))
        self.assertTrue(any("contract_clauses[0].covered_by" in error for error in errors))

    def test_rejects_visible_only_tests_to_run(self) -> None:
        # A gate whose validation is just the visible reproduction must fail:
        # that is exactly the under-fit gaming pattern seen in benchmarking.
        data = json.loads(RCA_EXAMPLE.read_text(encoding="utf-8"))
        data["tests_to_run"] = ["python _fixture_runner.py"]
        ok, errors = mod.validate_gate(data)
        self.assertFalse(ok)
        self.assertTrue(any("at least 2 commands" in error for error in errors))
        self.assertTrue(any("contract-tests" in error for error in errors))

    def test_rejects_tests_without_contract_tests_reference(self) -> None:
        data = json.loads(RCA_EXAMPLE.read_text(encoding="utf-8"))
        data["tests_to_run"] = ["python _fixture_runner.py", "python -m pytest test_profile.py"]
        ok, errors = mod.validate_gate(data)
        self.assertFalse(ok)
        self.assertTrue(any("contract-tests" in error for error in errors))

    def test_rejects_claude_bare_counterfactual(self) -> None:
        data = json.loads(RCA_EXAMPLE.read_text(encoding="utf-8"))
        data["counterfactual_check"]["command"] = "claude --print --bare 'fix this'"
        ok, errors = mod.validate_gate(data)
        self.assertFalse(ok)
        self.assertTrue(any("claude --bare" in error for error in errors))

    def test_valid_example_with_real_checkpoint(self) -> None:
        repo = self.make_repo()
        self.addCleanup(lambda: shutil.rmtree(repo))
        checkpoint = run(["bash", str(CHECKPOINT)], repo).stdout.strip()
        data = json.loads(RCA_EXAMPLE.read_text(encoding="utf-8"))
        data["checkpoint"] = checkpoint
        gate_path = repo / ".causal-repair" / "rca-gate.json"
        gate_path.write_text(json.dumps(data), encoding="utf-8")

        ok, errors = mod.validate_gate(data, gate_path=gate_path)
        self.assertTrue(ok, errors)

    def test_rejects_fake_checkpoint(self) -> None:
        repo = self.make_repo()
        self.addCleanup(lambda: shutil.rmtree(repo))
        checkpoint = repo / ".causal-repair" / "checkpoints" / "fake"
        checkpoint.mkdir(parents=True, exist_ok=True)
        (checkpoint / "base-commit.txt").write_text("x\n", encoding="utf-8")
        (checkpoint / "status-short.txt").write_text("\n", encoding="utf-8")
        data = json.loads(RCA_EXAMPLE.read_text(encoding="utf-8"))
        data["checkpoint"] = str(checkpoint)
        gate_path = repo / ".causal-repair" / "rca-gate.json"
        gate_path.write_text(json.dumps(data), encoding="utf-8")

        ok, errors = mod.validate_gate(data, gate_path=gate_path)
        self.assertFalse(ok)
        self.assertTrue(any("base-commit" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
