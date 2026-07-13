from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run-counterfactual.py"
CHECKPOINT = ROOT / "scripts" / "create-checkpoint.sh"
RCA_EXAMPLE = ROOT / "examples" / "rca-gate.example.json"

spec = importlib.util.spec_from_file_location("run_counterfactual", SCRIPT)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)


def run(cmd, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True, check=True)


class RunCounterfactualTest(unittest.TestCase):
    def make_repo(self) -> Path:
        tmp = Path(tempfile.mkdtemp())
        run(["git", "init"], tmp)
        run(["git", "config", "user.email", "test@example.com"], tmp)
        run(["git", "config", "user.name", "Test User"], tmp)
        (tmp / "ok.py").write_text("print('ok')\n", encoding="utf-8")
        run(["git", "add", "ok.py"], tmp)
        run(["git", "commit", "-m", "initial"], tmp)
        return tmp

    def write_gate(self, repo: Path, *, command: str, result: str) -> Path:
        checkpoint = run(["bash", str(CHECKPOINT)], repo).stdout.strip()
        data = json.loads(RCA_EXAMPLE.read_text(encoding="utf-8"))
        data["checkpoint"] = checkpoint
        data["counterfactual_check"] = {
            "command": command,
            "result": result,
            "evidence": "Counterfactual command output is checked by the test harness.",
        }
        gate = repo / ".causal-repair" / "rca-gate.json"
        gate.write_text(json.dumps(data), encoding="utf-8")
        return gate

    def test_matches_pass_result(self) -> None:
        repo = self.make_repo()
        self.addCleanup(lambda: shutil.rmtree(repo))
        gate = self.write_gate(repo, command="python ok.py", result="pass")
        ok, payload = mod.run_counterfactual(gate, cwd=repo)
        self.assertTrue(ok, payload)
        self.assertEqual(payload["actual"], "pass")

    def test_detects_mismatched_result(self) -> None:
        repo = self.make_repo()
        self.addCleanup(lambda: shutil.rmtree(repo))
        gate = self.write_gate(repo, command="python ok.py", result="failed")
        ok, payload = mod.run_counterfactual(gate, cwd=repo)
        self.assertFalse(ok)
        self.assertEqual(payload["expected"], "failed")
        self.assertEqual(payload["actual"], "pass")

    def test_handles_none_output_streams(self) -> None:
        repo = self.make_repo()
        self.addCleanup(lambda: shutil.rmtree(repo))
        gate = self.write_gate(repo, command="claude --print noop", result="pass")
        completed = subprocess.CompletedProcess(
            args="claude --print noop",
            returncode=0,
            stdout=None,
            stderr=None,
        )
        with patch.object(mod, "repo_root", return_value=repo), patch.object(mod.subprocess, "run", return_value=completed):
            ok, payload = mod.run_counterfactual(gate, cwd=repo)
        self.assertTrue(ok, payload)
        self.assertEqual(payload["stdout"], "")
        self.assertEqual(payload["stderr"], "")

    def test_rejects_claude_bare_command(self) -> None:
        repo = self.make_repo()
        self.addCleanup(lambda: shutil.rmtree(repo))
        gate = self.write_gate(repo, command="claude --print --bare noop", result="pass")
        with self.assertRaisesRegex(ValueError, "must not use `claude --bare`"):
            mod.run_counterfactual(gate, cwd=repo)

    def test_incomplete_is_skipped(self) -> None:
        repo = self.make_repo()
        self.addCleanup(lambda: shutil.rmtree(repo))
        gate = self.write_gate(repo, command="python ok.py", result="incomplete")
        ok, payload = mod.run_counterfactual(gate, cwd=repo)
        self.assertTrue(ok)
        self.assertEqual(payload["status"], "skipped")


if __name__ == "__main__":
    unittest.main()
