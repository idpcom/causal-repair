# Causal Repair

**Making small, self-hostable coding models fix bugs like a frontier model.**

Causal Repair is a Claude Code plugin plus an evaluation harness. The plugin
turns bug fixing into a root-cause-first workflow that forces every patch to
carry *mechanically checkable evidence* that it restored the code's documented
contract — not merely that it made the visible test pass. It targets the way
small or fast models "fix" a failing test: a symptom-only `if` branch, a broad
fallback, or a patch that quietly drops a documented behavior (for example an
error contract the visible test never exercises).

The plugin gives Claude Code a reusable skill, a small team of specialized
subagents (evidence, root-cause judgment, workaround review, validation), and
opt-in hooks that block edits until the evidence exists. The gates demand
artifacts — enumerated contract clauses, authored tests that must fail on the
buggy code and survive mutation, and no behavior change a test can't explain —
and verify them with plain scripts, so the guarantee comes from the checker,
not the model's good intentions.

In a pilot benchmark aimed at the intranet-deployment case (large hosted models
unavailable), **Qwen3.6-35B + MiMo-V2.5 running under the harness matched, then
exceeded, an unharnessed Kimi K2.6 reference** on tasks where the bare small
models game the test. See [Results](#results) — including honest small-sample
caveats.

## Why this exists

Small or fast coding models often pass the visible test by patching the symptom instead of repairing the violated contract. Causal Repair makes that behavior harder by requiring:

- failing evidence before edits
- an explicit causal path
- explicit, inferred, or unknown contract/invariant status
- enumeration of the documented contract clauses of the code under repair
- authored contract tests (one negative case per documented error contract) before patching
- an executed counterfactual check when practical
- a root-cause gate before patching
- optional, explicitly configured hook enforcement before write tools run
- a patch manifest after edits
- adversarial review after patching, for workaround shapes and for under-fit patches
- original, contract, and adjacent test validation
- patch revert and re-analysis when the patch fails review

The rule is simple:

```text
No checkpoint, no patch.
No RCA, no patch.
No causal path, no patch.
No contract enumeration, no patch.
No executed counterfactual, no confidence.
No contract tests, no validation.
No patch manifest, no safe revert.
No workaround review, no done.
```

## Results

We benchmarked whether the harness lets two low-weight, self-hostable models
(Qwen3.6-35B-A3B + MiMo-V2.5) reach the bug-fixing quality of an unharnessed
reference model (Kimi K2.6) — the intranet-deployment question where large
hosted LLMs are unavailable. All runs go through OpenRouter behind an
Anthropic-compatible router in a Docker sandbox. Protocol and adoption rules
were pre-registered before measurement (`bench/PREREG.md`); the full report,
including per-task data and limitations, is in
[`bench/RESULTS.md`](bench/RESULTS.md).

The metric is **genuine-fix**: the patch passes the visible test AND a hidden
held-out contract test AND matches no workaround pattern. **gamed** = passes the
visible test but violates the contract.

**Progression of the design (each version fixes a failure the previous one's
measurement exposed), on the pre-registered set of tasks where small baselines
game:**

| version | mechanism added | genuine-fix |
|---|---|---|
| baseline (Qwen alone) | — | 15% |
| prompt-only (guidance, no enforcement) | — | 33% |
| v0.3 (blocking-only "minimal patch") | forbids edits before an RCA gate | **worse** — gamed 3/3 on a task baselines solved 50% |
| v0.4.0 | machine-checked contract-clause gate | 52% |
| v0.4.1 (Proof-Carrying Repair) | per-clause witness tests must fail on base + survive mutation | 67% |
| **v0.4.2** | change-surface coverage gate + CI-style runner-enforced retry loop | **89%\*** |
| Kimi K2.6 (unharnessed reference bar) | — | 58–71% |

\* v0.4.2 (89%) is measured on a 3-task live slice where the same Kimi bar is
58%; v0.4.0/v0.4.1 (52/67%) and the 71% Kimi figure are on the wider 6-task
set. Small n throughout (see below).

Findings:

- **The harness lets Qwen+MiMo match, then exceed, the unharnessed Kimi
  reference.** v0.4.1 is statistically indistinguishable from Kimi on the
  6-task set (67% vs 71%, bootstrap 95% CI on the difference includes 0);
  v0.4.2 reaches 89% on the 3-task slice vs Kimi's 58%, including a task Kimi
  itself solves 0/3.
- **Mechanical enforcement is the active ingredient, not the guidance.** The
  same instructions delivered prompt-only (no hook) land at baseline level
  (33%); adding enforcement adds +33 pts (Fisher p = 0.047). Having the runner
  itself re-invoke the model on a failed gate (CI-style) drove gate adherence
  from ~50% to 100%.
- **A blocking-only process can make small models *worse*.** "Minimal patch vs
  the visible test" suppresses the contract-completeness fix. The remedy is a
  gate that *demands machine-checkable evidence* — enumerated contract clauses,
  authored tests that must fail on the buggy base and survive mutation, and no
  behavior change a witness can't explain — rather than merely forbidding edits.

Honest caveats: this is a small-n pilot ($/cell n = 9–21); the step-to-step
increments are directional (e.g. v0.4.2-over-v0.4.1 Fisher p = 0.15); the
witnesses check a patch's internal consistency, strength, and change-surface
coverage, not completeness against a hidden oracle (one v0.4.2 run passed every
gate yet still failed held-out); and long-horizon multi-file tasks at this
difficulty did not yet separate the conditions. Full data, statistics, cost,
and limitations are in [`bench/RESULTS.md`](bench/RESULTS.md); the mechanisms
are described in [`docs/coverage-gate.md`](docs/coverage-gate.md).

## Plugin layout

```text
causal-repair/
├── .claude-plugin/
│   └── plugin.json
├── skills/
│   ├── causal-repair/
│   │   └── SKILL.md
│   ├── cr/
│   │   └── SKILL.md
│   └── fix/
│       └── SKILL.md
├── agents/
│   ├── root-cause-investigator.md
│   ├── root-cause-judge.md
│   ├── workaround-reviewer.md
│   └── repair-verifier.md
├── docs/
│   ├── hooks.md
│   └── model-setup.md
├── examples/
│   ├── hooks/
│   ├── minimal-session.md
│   ├── model-profiles/
│   └── rca-gate.example.json
├── fixtures/
│   └── python-null-profile/
├── resources/
│   └── workflow-template.md
├── scripts/
│   ├── create-checkpoint.sh
│   ├── create-patch-manifest.py
│   ├── evaluate-fixtures.py
│   ├── hooks/pre-tool-use.py
│   ├── run-counterfactual.py
│   ├── set-agent-models.py
│   └── validate-rca-gate.py
├── tests/
│   ├── test_hooks_pre_tool_use.py
│   ├── test_patch_manifest.py
│   ├── test_run_counterfactual.py
│   ├── test_set_agent_models.py
│   └── test_validate_rca_gate.py
├── evals/
│   └── evals.json
├── CHANGELOG.md
├── LICENSE
└── README.md
```

This follows the Claude Code plugin layout: marketplace-ready plugins contain a `.claude-plugin/plugin.json` manifest, optional `skills/`, optional `agents`, and supporting files at the plugin root.

## Install for local testing

Clone the repository:

```bash
git clone https://github.com/idpcom/causal-repair.git
cd causal-repair
```

Run Claude Code with this plugin loaded directly:

```bash
claude --plugin-dir .
```

Then invoke the skill:

```text
/causal-repair:causal-repair fix the failing test. Test command: npm test -- user.service.test.ts
```

You can also pass a symptom instead of a command:

```text
/causal-repair:causal-repair the login regression is failing after the token refactor
```

After edits to the plugin, run this inside Claude Code:

```text
/reload-plugins
```

## Install as a local skills-directory plugin

You can also keep the plugin in your personal Claude Code skills directory:

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/idpcom/causal-repair.git ~/.claude/skills/causal-repair
```

Restart Claude Code or run `/reload-plugins`.

## Marketplace distribution

This repository is structured as a Claude Code plugin, so it can be submitted to a Claude Code plugin marketplace after validation.

Recommended pre-submit checks:

```bash
claude plugin validate .
claude --plugin-dir .
```

Then test:

```text
/causal-repair:causal-repair fix the failing test in a small sample repo
```

## Model routing setup

Causal Repair can be run with only model names. Provider names are not required.

Preview the bundled profile:

```bash
python scripts/set-agent-models.py --profile examples/model-profiles/default.json --dry-run
```

Apply it:

```bash
python scripts/set-agent-models.py --profile examples/model-profiles/default.json
```

Print current plugin routing:

```bash
python scripts/set-agent-models.py --print
```

Then reload Claude Code plugins:

```text
/reload-plugins
```

See `docs/model-setup.md` for the full model-name-only setup.

## Hook enforcement

The optional PreToolUse hook blocks write tools until a checkpoint and valid RCA gate exist.

Hook enforcement is not registered automatically in `.claude-plugin/plugin.json`. Global skill installs run hook commands from the active project, so relative hook commands can fail in projects that do not contain this plugin repository.

Use project or user settings only when you want hard enforcement, and use an absolute path to the installed hook script:

```bash
python C:/Users/dongpan.lim/.claude/skills/causal-repair/scripts/hooks/pre-tool-use.py
```

Example settings:

```text
examples/hooks/settings.example.json
```

Required RCA gate file:

```text
.causal-repair/rca-gate.json
```

Validate it:

```bash
python scripts/validate-rca-gate.py .causal-repair/rca-gate.json
```

Verify the recorded counterfactual command against its actual exit status:

```bash
python scripts/run-counterfactual.py .causal-repair/rca-gate.json
```

See `docs/hooks.md` for installation and limitations.

## Mechanical guardrails

Create a checkpoint before edits:

```bash
bash scripts/create-checkpoint.sh
```

This records:

- current base commit
- dirty working tree summary
- unstaged diff
- staged diff
- untracked file list and contents

Create a patch manifest after edits:

```bash
python scripts/create-patch-manifest.py --output .causal-repair/patch-manifest.json
```

Validate an RCA gate:

```bash
python scripts/validate-rca-gate.py .causal-repair/rca-gate.json
```

Verify the recorded counterfactual command against its actual exit status:

```bash
python scripts/run-counterfactual.py .causal-repair/rca-gate.json
```

Run all local validation:

```bash
bash scripts/validate-structure.sh
python -m unittest discover -s tests -p 'test_*.py'
python scripts/evaluate-fixtures.py
```

The fixture eval applies a known-good patch, a failing workaround patch, and a test-passing hardcoded workaround patch to `fixtures/python-null-profile`. The good patch must pass without workaround findings, while both bad patches must be flagged or fail behavior checks.

## How it works

Causal Repair splits repair into gates:

1. **Mechanical checkpoint**  
   Capture base commit, dirty state, staged/unstaged diffs, and untracked files before editing.

2. **Optional hook-enforced RCA gate**  
   When explicitly configured, the PreToolUse hook blocks Edit/Write tools until checkpoint and `.causal-repair/rca-gate.json` exist.

3. **Evidence capture**  
   Run the failing command or inspect the failure report. Record the exact symptom before changing code.

4. **Parallel root-cause investigation**  
   Use diverse investigators to find the execution path, observed broken behavior, and contract/invariant status without inventing a contract.

5. **Root-cause judgment**  
   Compare competing hypotheses and approve only an evidence-backed RCA with a counterfactual check when practical.

6. **Counterfactual execution**  
   Run the command recorded in `.causal-repair/rca-gate.json` and verify that the observed exit status matches the recorded result.

7. **Contract tests, then minimal repair**  
   Enumerate the documented contract clauses of the code under repair, write `.causal-repair/contract-tests.py` covering each clause (negative case per error contract), then make the smallest production change that restores the full documented contract — minimal against the contract, not against the visible test.

8. **Patch manifest**  
   Record which files changed, which were already dirty, and which are safe for automatic revert.

9. **Workaround review**  
   Reject symptom-only conditionals and masking fallbacks (over-fit) and patches that leave a documented contract clause unimplemented (under-fit), but do not categorically reject valid null checks, catches, fallbacks, or retries.

10. **Verification**  
   Run the original failing test and adjacent regression tests. If review or tests fail, revert only patch-manifest-safe changes or require manual hunk review.

## Included subagents

### `root-cause-investigator`

Read-only investigator for failing tests. It reconstructs the execution path and identifies broken invariants before patching.

### `root-cause-judge`

Evidence-based judge that compares multiple hypotheses and decides whether patching is allowed.

### `workaround-reviewer`

Adversarial reviewer that rejects workaround-shaped diffs.

### `repair-verifier`

Validation agent that runs the original and adjacent tests and summarizes pass/fail evidence.

## Dynamic workflow support

The skill can ask Claude Code to use a dynamic workflow for larger fixes. See:

```text
resources/workflow-template.md
```

The template is intentionally stored as reference material rather than an auto-running script. It tells Claude Code how to fan out investigators, gate patching, run review, and stop after repeated non-progress.

## Safety and limitations

- This plugin does not guarantee a correct fix.
- It is a process guardrail, not a replacement for human code review.
- It intentionally slows down edits until checkpoint/RCA evidence exists.
- Hooks are opt-in because automatic relative hook commands break global skill installs.
- Hooks block Claude Code tool calls, not arbitrary OS-level writes outside Claude Code.
- `Bash` access is powerful; read-only investigation is a policy, not an OS-level sandbox.
- Counterfactual execution verifies exit status, not semantic truth.
- It works best when the user provides a failing test command, stack trace, or reproducible symptom.
- If the repository lacks tests, the verifier must state that validation is incomplete.

## License

MIT
