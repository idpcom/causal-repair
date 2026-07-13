from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "set-agent-models.py"

spec = importlib.util.spec_from_file_location("set_agent_models", SCRIPT)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)


def write_agent(path: Path, text: str) -> None:
    path.write_text(textwrap.dedent(text), encoding="utf-8")


class SetAgentModelsTest(unittest.TestCase):
    def test_updates_model_only_in_frontmatter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "agent.md"
            write_agent(
                path,
                """
                ---
                name: sample
                model: haiku
                ---

                Body line that mentions model: not-a-frontmatter-model
                """,
            )

            mod.update_model(path, "qwen3-coder-plus", backup=False)

            text = path.read_text(encoding="utf-8")
            self.assertIn("model: qwen3-coder-plus", text.split("---", 2)[1])
            self.assertIn("model: not-a-frontmatter-model", text)
            self.assertEqual(mod.current_model(path), "qwen3-coder-plus")

    def test_adds_model_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "agent.md"
            write_agent(
                path,
                """
                ---
                name: sample
                tools: Read
                ---

                Body
                """,
            )

            mod.update_model(path, "sonnet", backup=False)

            self.assertEqual(mod.current_model(path), "sonnet")

    def test_supports_crlf_frontmatter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "agent.md"
            path.write_bytes(b"---\r\nname: sample\r\nmodel: haiku\r\n---\r\n\r\nBody\r\n")

            mod.update_model(path, "xiaomi/mimo-v2.5-pro", backup=False)

            self.assertEqual(mod.current_model(path), "xiaomi/mimo-v2.5-pro")

    def test_supports_utf8_bom(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "agent.md"
            path.write_bytes("\ufeff---\nname: sample\nmodel: haiku\n---\n\nBody\n".encode("utf-8"))

            mod.update_model(path, "qwen3-coder-plus", backup=False)

            self.assertEqual(mod.current_model(path), "qwen3-coder-plus")

    def test_rejects_invalid_model_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "agent.md"
            write_agent(
                path,
                """
                ---
                name: sample
                model: haiku
                ---
                """,
            )

            with self.assertRaises(ValueError):
                mod.update_model(path, "bad model with spaces", backup=False)

    def test_conflicting_profile_and_all_is_error(self) -> None:
        args = mod.parse_args(["--profile", "qwen-mimo", "--all", "haiku"])
        with self.assertRaises(ValueError):
            mod.build_updates(args)

    def test_profile_returns_expected_mapping(self) -> None:
        args = mod.parse_args(["--profile", "qwen-mimo"])
        updates = mod.build_updates(args)
        self.assertEqual(updates["investigator"], "qwen3-coder-plus")
        self.assertEqual(updates["judge"], "xiaomi/mimo-v2.5-pro")


if __name__ == "__main__":
    unittest.main()
