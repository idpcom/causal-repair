# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

This is **not application code** — it is the **Causal Repair Claude Code plugin** itself. The deliverable is a set of Markdown skill/agent/command definitions plus Python/bash scripts that get loaded *into* Claude Code to enforce a root-cause-first bug-fixing workflow. The "runtime" is Claude Code loading these files; there is no server, no build, and no package to compile.

The workflow the plugin enforces is a sequence of gates: mechanical checkpoint → failing evidence → parallel root-cause investigation → RCA gate → counterfactual execution → minimal patch → patch manifest → workaround review → verification. See `README.md` "How it works" and `skills/causal-repair/SKILL.md` for the authoritative description.

## Commands

There is no build step. All validation is what CI (`.github/workflows/validate.yml`) runs:

```bash
# Structure/manifest validation (asserts exact file set + plugin.json invariants)
bash scripts/validate-structure.sh

# Unit tests
python -m unittest discover -s tests -p 'test_*.py'

# Run a single test module / case
python -m unittest tests.test_validate_rca_gate
python -m unittest tests.test_validate_rca_gate.TestValidateRcaGate.<method>

# Fixture eval: applies good + two bad patches to fixtures/python-null-profile
python scripts/evaluate-fixtures.py

# Model-routing profile dry-run
python scripts/set-agent-models.py --list-profiles
python scripts/set-agent-models.py --profile qwen-mimo --dry-run
```

Load the plugin locally for manual testing: `claude --plugin-dir .`, then `/reload-plugins` after edits.

## Architecture

**Two components define the plugin surface** (both are Markdown with YAML frontmatter — no code):
- `skills/` — five skills (`causal-repair` is canonical; `cr`, `fix`, `goal`, `review` are thin aliases/variants). Skills embed the full workflow prose and `$ARGUMENTS`.
- `agents/` — four read-only-by-policy subagents: `root-cause-investigator`, `root-cause-judge`, `workaround-reviewer`, `repair-verifier`. Their `model:` frontmatter is rewritten by `scripts/set-agent-models.py`.
- `commands/` — slash-command entry points mirroring the skills.

**The enforcement mechanism is the `.causal-repair/` working-directory contract**, produced/consumed by the scripts:
- `scripts/create-checkpoint.sh` writes `.causal-repair/checkpoints/<ts>/` with `base-commit.txt`, `status-short.txt`, and diff/untracked snapshots.
- `.causal-repair/rca-gate.json` is the gate the model must author before patching.
- `scripts/create-patch-manifest.py` records which changed files are safe to auto-revert (vs. `pre_existing_dirty`).
- `scripts/run-counterfactual.py` re-runs the gate's recorded command and checks the exit status matches.

**RCA-gate schema is duplicated in two places that MUST stay in sync.** The field list, text-length minimums, allowed contract statuses, and counterfactual validation live independently in both `scripts/validate-rca-gate.py` and `scripts/hooks/pre-tool-use.py` (`REQUIRED_FIELDS`/`REQUIRED_RCA_FIELDS`, `TEXT_RCA_FIELDS`, `ALLOWED_CONTRACT_STATUS`, `ALLOWED_COUNTERFACTUAL_RESULTS`). Change one, change the other, and update `tests/` for both.

**The PreToolUse hook** (`scripts/hooks/pre-tool-use.py`) is the hard-enforcement path: it blocks `Edit/Write/MultiEdit/NotebookEdit` and write-like `Bash` (regex-matched) until a valid checkpoint + RCA gate exist, and blocks destructive git/shell commands outright. It tolerates multiple hook-payload field-name shapes on purpose. Behavior is toggled by env vars: `CAUSAL_REPAIR_REQUIRE_CHECKPOINT`, `CAUSAL_REPAIR_REQUIRE_RCA`, `CAUSAL_REPAIR_STRICT_BASH_WRITES`. Edits confined to `.causal-repair/` paths are always allowed so the workflow can bootstrap itself.

## Invariants when editing

- **`plugin.json` must NOT declare `"hooks"`.** `validate-structure.sh` asserts `! grep '"hooks"'`. Hooks are opt-in: users wire them in project/user `settings.json` with an **absolute** path (relative hook commands break global skill installs — this is the reason for the many recent "hook opt-in" commits). See `docs/hooks.md` and `examples/hooks/settings.example.json`.
- **`validate-structure.sh` hard-codes the expected file set.** Adding/removing/renaming any skill, agent, command, script, test, or fixture requires updating that script or CI fails.
- Every skill and command file must start with a `description:` frontmatter line (asserted by structure validation).
- Scripts target the standard library only (no third-party deps); tests run on plain `python -m unittest`.
- Version lives in both `VERSION` and `.claude-plugin/plugin.json` — keep them aligned and update `CHANGELOG.md`.

## Fixtures

`fixtures/python-null-profile/` is the behavioral test bed: a `repo/` with a real bug plus three `patches/` — one good (`good-normalize-display-name`) and two bad (`bad-null-empty-string`, `bad-hardcoded-legacy`). `evaluate-fixtures.py` asserts the good patch passes without workaround findings and both bad patches are flagged or fail behavior checks. This is the ground truth for whether the workaround-review logic actually discriminates.
