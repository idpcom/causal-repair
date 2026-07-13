from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "create-patch-manifest.py"
CHECKPOINT = ROOT / "scripts" / "create-checkpoint.sh"

spec = importlib.util.spec_from_file_location("create_patch_manifest", SCRIPT)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)


def run(cmd, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True, check=True)


class PatchManifestTest(unittest.TestCase):
    def make_repo(self) -> Path:
        tmp = Path(tempfile.mkdtemp())
        run(["git", "init"], tmp)
        run(["git", "config", "user.email", "test@example.com"], tmp)
        run(["git", "config", "user.name", "Test User"], tmp)
        (tmp / "app.py").write_text("def answer():\n    return 1\n", encoding="utf-8")
        (tmp / "README.md").write_text("fixture\n", encoding="utf-8")
        run(["git", "add", "app.py", "README.md"], tmp)
        run(["git", "commit", "-m", "initial"], tmp)
        return tmp

    def test_manifest_marks_pre_existing_dirty_files(self) -> None:
        repo = self.make_repo()
        self.addCleanup(lambda: shutil.rmtree(repo))

        (repo / "README.md").write_text("fixture\npre-existing user edit\n", encoding="utf-8")
        checkpoint = run(["bash", str(CHECKPOINT)], repo).stdout.strip()

        (repo / "app.py").write_text("def answer():\n    return 2\n", encoding="utf-8")
        (repo / "README.md").write_text("fixture\npre-existing user edit\nrepair also touched this\n", encoding="utf-8")
        (repo / "new_repair_file.txt").write_text("new repair artifact\n", encoding="utf-8")

        output = repo / ".causal-repair" / "patch-manifest.json"
        manifest = mod.build_manifest(Path(checkpoint), output, cwd=repo)

        self.assertTrue(output.exists())
        by_path = {entry["path"]: entry for entry in manifest["changed_files"]}
        self.assertFalse(by_path["app.py"]["pre_existing_dirty"])
        self.assertTrue(by_path["app.py"]["safe_auto_revert"])
        self.assertTrue(by_path["README.md"]["pre_existing_dirty"])
        self.assertFalse(by_path["README.md"]["safe_auto_revert"])
        self.assertIn("new_repair_file.txt", manifest["new_untracked_files"])

        loaded = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(loaded["schema_version"], 1)
        self.assertIn("Do not run git reset --hard", "\n".join(loaded["safe_revert_guidance"]))

    def test_parse_porcelain_paths_handles_renames(self) -> None:
        parsed = mod.parse_porcelain_paths("R  old.txt -> new.txt\n M app.py\n?? temp.txt\n")
        self.assertIn("old.txt", parsed)
        self.assertIn("new.txt", parsed)
        self.assertIn("app.py", parsed)
        self.assertIn("temp.txt", parsed)


if __name__ == "__main__":
    unittest.main()
