#!/usr/bin/env bash
set -euo pipefail

test -f .claude-plugin/plugin.json
test -f skills/causal-repair/SKILL.md
test -f skills/cr/SKILL.md
test -f skills/fix/SKILL.md
test -f skills/review/SKILL.md
test -f skills/goal/SKILL.md
test -f commands/cr.md
test -f commands/fix.md
test -f commands/review.md
test -f commands/goal.md
test -f agents/root-cause-investigator.md
test -f agents/root-cause-judge.md
test -f agents/workaround-reviewer.md
test -f agents/repair-verifier.md
test -f scripts/set-agent-models.py
test -f scripts/create-checkpoint.sh
test -f scripts/create-patch-manifest.py
test -f scripts/validate-rca-gate.py
test -f scripts/validate-ledger.py
test -f scripts/verify-witnesses.py
test -f scripts/verify-coverage.py
test -f scripts/mutate.py
test -f scripts/run-counterfactual.py
test -f scripts/evaluate-fixtures.py
test -f scripts/hooks/pre-tool-use.py
test -f examples/rca-gate.example.json
test -f examples/hooks/settings.example.json
test -f docs/hooks.md
test -f tests/test_set_agent_models.py
test -f tests/test_patch_manifest.py
test -f tests/test_hooks_pre_tool_use.py
test -f tests/test_validate_rca_gate.py
test -f tests/test_validate_ledger.py
test -f tests/test_verify_witnesses.py
test -f tests/test_verify_coverage.py
test -f tests/test_run_counterfactual.py
test -f fixtures/python-null-profile/repo/profile.py
test -f fixtures/python-null-profile/repo/test_profile.py
test -f fixtures/python-null-profile/patches/good-normalize-display-name.patch
test -f fixtures/python-null-profile/patches/bad-null-empty-string.patch
test -f fixtures/python-null-profile/patches/bad-hardcoded-legacy.patch

python -m json.tool .claude-plugin/plugin.json >/dev/null
python -m json.tool evals/evals.json >/dev/null
python -m json.tool examples/rca-gate.example.json >/dev/null
python -m json.tool examples/hooks/settings.example.json >/dev/null

grep -q '"name": "causal-repair"' .claude-plugin/plugin.json
! grep -q '"hooks"' .claude-plugin/plugin.json
grep -q '^description:' skills/causal-repair/SKILL.md
grep -q '^description:' skills/cr/SKILL.md
grep -q '^description:' skills/fix/SKILL.md
grep -q '^description:' skills/review/SKILL.md
grep -q '^description:' skills/goal/SKILL.md
grep -q '^description:' commands/cr.md
grep -q '^description:' commands/fix.md
grep -q '^description:' commands/review.md
grep -q '^description:' commands/goal.md

echo "causal-repair plugin structure is valid"
