from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "scripts" / "hooks" / "pre-tool-use.py"
CHECKPOINT = ROOT / "scripts" / "create-checkpoint.sh"
RCA_EXAMPLE = ROOT / "examples" / "rca-gate.example.json"

spec = importlib.util.spec_from_file_location("pre_tool_use", HOOK)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)


def run(cmd, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True, check=True)


class PreToolUseHookTest(unittest.TestCase):
    def make_repo(self) -> Path:
        tmp = Path(tempfile.mkdtemp())
        run(["git", "init"], tmp)
        run(["git", "config", "user.email", "test@example.com"], tmp)
        run(["git", "config", "user.name", "Test User"], tmp)
        (tmp / "app.py").write_text("print('hello')\n", encoding="utf-8")
        run(["git", "add", "app.py"], tmp)
        run(["git", "commit", "-m", "initial"], tmp)
        return tmp

    def create_checkpoint(self, repo: Path) -> str:
        return run(["bash", str(CHECKPOINT)], repo).stdout.strip()

    def write_valid_rca_gate(self, repo: Path, checkpoint: str) -> None:
        target = repo / ".causal-repair" / "rca-gate.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        data = json.loads(RCA_EXAMPLE.read_text(encoding="utf-8"))
        data["checkpoint"] = checkpoint
        target.write_text(json.dumps(data), encoding="utf-8")

    def write_fake_checkpoint_and_gate(self, repo: Path) -> None:
        checkpoint = repo / ".causal-repair" / "checkpoints" / "fake"
        checkpoint.mkdir(parents=True, exist_ok=True)
        (checkpoint / "base-commit.txt").write_text("x\n", encoding="utf-8")
        (checkpoint / "status-short.txt").write_text("\n", encoding="utf-8")
        gate = {key: "x" for key in mod.REQUIRED_RCA_FIELDS}
        gate["contract_invariant_status"] = "unknown"
        target = repo / ".causal-repair" / "rca-gate.json"
        target.write_text(json.dumps(gate), encoding="utf-8")

    def test_blocks_edit_without_checkpoint(self) -> None:
        repo = self.make_repo()
        self.addCleanup(lambda: shutil.rmtree(repo))
        allowed, message = mod.evaluate(
            {"tool_name": "Edit", "tool_input": {"file_path": "app.py"}},
            cwd=repo,
            env={},
        )
        self.assertFalse(allowed)
        self.assertIn("checkpoint", message)

    def test_blocks_edit_without_rca_gate(self) -> None:
        repo = self.make_repo()
        self.addCleanup(lambda: shutil.rmtree(repo))
        self.create_checkpoint(repo)
        allowed, message = mod.evaluate(
            {"tool_name": "Edit", "tool_input": {"file_path": "app.py"}},
            cwd=repo,
            env={},
        )
        self.assertFalse(allowed)
        self.assertIn("RCA gate", message)

    def test_blocks_fake_checkpoint_and_empty_gate(self) -> None:
        repo = self.make_repo()
        self.addCleanup(lambda: shutil.rmtree(repo))
        self.write_fake_checkpoint_and_gate(repo)
        allowed, message = mod.evaluate(
            {"tool_name": "Edit", "tool_input": {"file_path": "app.py"}},
            cwd=repo,
            env={},
        )
        self.assertFalse(allowed)
        self.assertIn("valid checkpoint", message + " checkpoint")

    def test_allows_edit_after_checkpoint_and_valid_rca_gate(self) -> None:
        repo = self.make_repo()
        self.addCleanup(lambda: shutil.rmtree(repo))
        checkpoint = self.create_checkpoint(repo)
        self.write_valid_rca_gate(repo, checkpoint)
        allowed, message = mod.evaluate(
            {"tool_name": "Edit", "tool_input": {"file_path": "app.py"}},
            cwd=repo,
            env={},
        )
        self.assertTrue(allowed, message)

    def test_blocks_edit_when_gate_lacks_contract_clauses(self) -> None:
        repo = self.make_repo()
        self.addCleanup(lambda: shutil.rmtree(repo))
        checkpoint = self.create_checkpoint(repo)
        target = repo / ".causal-repair" / "rca-gate.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        data = json.loads(RCA_EXAMPLE.read_text(encoding="utf-8"))
        data["checkpoint"] = checkpoint
        del data["contract_clauses"]
        target.write_text(json.dumps(data), encoding="utf-8")
        allowed, message = mod.evaluate(
            {"tool_name": "Edit", "tool_input": {"file_path": "app.py"}},
            cwd=repo,
            env={},
        )
        self.assertFalse(allowed)
        self.assertIn("contract_clauses", message)

    def test_blocks_edit_when_tests_are_visible_only(self) -> None:
        repo = self.make_repo()
        self.addCleanup(lambda: shutil.rmtree(repo))
        checkpoint = self.create_checkpoint(repo)
        target = repo / ".causal-repair" / "rca-gate.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        data = json.loads(RCA_EXAMPLE.read_text(encoding="utf-8"))
        data["checkpoint"] = checkpoint
        data["tests_to_run"] = ["python _fixture_runner.py"]
        target.write_text(json.dumps(data), encoding="utf-8")
        allowed, message = mod.evaluate(
            {"tool_name": "Edit", "tool_input": {"file_path": "app.py"}},
            cwd=repo,
            env={},
        )
        self.assertFalse(allowed)
        self.assertIn("contract-tests", message)

    def _gate_and_checkpoint(self, repo: Path) -> None:
        checkpoint = self.create_checkpoint(repo)
        self.write_valid_rca_gate(repo, checkpoint)

    def _write_ledger(self, repo: Path, active_kind: str | None) -> None:
        segments = [
            {"id": "s1", "kind": "investigate", "objective": "find the root cause path",
             "done_criteria": "python test_visible.py", "status": "done",
             "evidence": "reproduced and traced the failure"},
        ]
        if active_kind is not None:
            segments.append(
                {"id": "s2", "kind": active_kind, "objective": "do the active segment work",
                 "done_criteria": "python .causal-repair/contract-tests.py",
                 "status": "in_progress"}
            )
        ledger = {
            "goal": "Repair the documented contract end to end.",
            "segments": segments,
            "attempts": 0,
            "stop_condition": "two rounds without new evidence",
        }
        (repo / ".causal-repair" / "ledger.json").write_text(json.dumps(ledger), encoding="utf-8")

    def test_ledger_blocks_edit_outside_patch_segment(self) -> None:
        repo = self.make_repo()
        self.addCleanup(lambda: shutil.rmtree(repo))
        self._gate_and_checkpoint(repo)
        self._write_ledger(repo, active_kind="review")
        allowed, message = mod.evaluate(
            {"tool_name": "Edit", "tool_input": {"file_path": "app.py"}},
            cwd=repo,
            env={},
        )
        self.assertFalse(allowed)
        self.assertIn("patch", message)

    def test_ledger_blocks_edit_with_no_active_segment(self) -> None:
        repo = self.make_repo()
        self.addCleanup(lambda: shutil.rmtree(repo))
        self._gate_and_checkpoint(repo)
        self._write_ledger(repo, active_kind=None)
        allowed, message = mod.evaluate(
            {"tool_name": "Edit", "tool_input": {"file_path": "app.py"}},
            cwd=repo,
            env={},
        )
        self.assertFalse(allowed)
        self.assertIn("no in_progress segment", message)

    def test_ledger_allows_edit_in_patch_segment(self) -> None:
        repo = self.make_repo()
        self.addCleanup(lambda: shutil.rmtree(repo))
        self._gate_and_checkpoint(repo)
        self._write_ledger(repo, active_kind="patch")
        allowed, message = mod.evaluate(
            {"tool_name": "Edit", "tool_input": {"file_path": "app.py"}},
            cwd=repo,
            env={},
        )
        self.assertTrue(allowed, message)

    def test_no_ledger_keeps_existing_behavior(self) -> None:
        repo = self.make_repo()
        self.addCleanup(lambda: shutil.rmtree(repo))
        self._gate_and_checkpoint(repo)
        allowed, message = mod.evaluate(
            {"tool_name": "Edit", "tool_input": {"file_path": "app.py"}},
            cwd=repo,
            env={},
        )
        self.assertTrue(allowed, message)

    def test_allows_causal_repair_metadata_edit_before_gate(self) -> None:
        repo = self.make_repo()
        self.addCleanup(lambda: shutil.rmtree(repo))
        allowed, message = mod.evaluate(
            {"tool_name": "Write", "tool_input": {"file_path": ".causal-repair/rca-gate.json"}},
            cwd=repo,
            env={},
        )
        self.assertTrue(allowed, message)

    def test_blocks_reset_hard_even_clean_worktree(self) -> None:
        repo = self.make_repo()
        self.addCleanup(lambda: shutil.rmtree(repo))
        allowed, message = mod.evaluate(
            {"tool_name": "Bash", "tool_input": {"command": "git reset --hard HEAD"}},
            cwd=repo,
            env={},
        )
        self.assertFalse(allowed)
        self.assertIn("destructive", message)

    def test_blocks_rm_fr_dot(self) -> None:
        repo = self.make_repo()
        self.addCleanup(lambda: shutil.rmtree(repo))
        allowed, message = mod.evaluate(
            {"tool_name": "Bash", "tool_input": {"command": "rm -fr ."}},
            cwd=repo,
            env={},
        )
        self.assertFalse(allowed)
        self.assertIn("destructive", message)

    def test_bash_write_blocks_by_default_before_gate(self) -> None:
        repo = self.make_repo()
        self.addCleanup(lambda: shutil.rmtree(repo))
        self.create_checkpoint(repo)
        allowed, message = mod.evaluate(
            {"tool_name": "Bash", "tool_input": {"command": "sed -i s/hello/world/ app.py"}},
            cwd=repo,
            env={},
        )
        self.assertFalse(allowed)
        self.assertIn("write-like Bash", message)

    def test_python_c_write_blocks_by_default_before_gate(self) -> None:
        repo = self.make_repo()
        self.addCleanup(lambda: shutil.rmtree(repo))
        self.create_checkpoint(repo)
        allowed, message = mod.evaluate(
            {"tool_name": "Bash", "tool_input": {"command": "python -c \"open('app.py','w').write('x')\""}},
            cwd=repo,
            env={},
        )
        self.assertFalse(allowed)
        self.assertIn("write-like Bash", message)

    def test_git_apply_blocks_by_default_before_gate(self) -> None:
        repo = self.make_repo()
        self.addCleanup(lambda: shutil.rmtree(repo))
        self.create_checkpoint(repo)
        allowed, message = mod.evaluate(
            {"tool_name": "Bash", "tool_input": {"command": "git apply fix.patch"}},
            cwd=repo,
            env={},
        )
        self.assertFalse(allowed)
        self.assertIn("write-like Bash", message)


if __name__ == "__main__":
    unittest.main()
