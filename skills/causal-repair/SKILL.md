---
name: causal-repair
description: Performs root-cause-first code repair for failing tests, regressions, and workaround-prone bug fixes. Use when the user asks to fix tests, debug a regression, improve a bad patch, reduce workaround if-statements, or require RCA before code changes.
---

# Causal Repair

Use this skill to fix bugs without falling into symptom-only workarounds.

Primary rule:

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

If hook enforcement is installed, Edit/Write/MultiEdit/NotebookEdit will be blocked until a checkpoint and `.causal-repair/rca-gate.json` exist.

## Inputs

Use `$ARGUMENTS` as the user's repair request. It may contain:

- a failing test command
- a failing test name
- a stack trace or error message
- a bug symptom
- a target file, module, branch, or PR context

If the user gave a test command, run it before editing. If no command is given, inspect the project for the most relevant test or reproduction path.

## Two paths: fast by default, escalate on evidence

The anti-workaround protection comes from the ARTIFACTS (checkpoint, contract
clauses, per-clause contract tests, gate file) — not from ceremony. Produce the
artifacts on every repair, but spend orchestration only where the bug earns it.

**FAST PATH (default for every repair).** Work single-agent. No investigator
fan-out, no judge/reviewer/verifier subagents, no dynamic workflow:

1. Checkpoint (`bash scripts/create-checkpoint.sh` or the manual equivalent).
2. Reproduce the failure once and read the docstring/spec of the code under
   repair. Enumerate ALL documented contract clauses — this is the step that
   prevents symptom-only fixes and it is cheap. Do not skip it because the bug
   looks trivial.
3. Write a compact `.causal-repair/rca-gate.json` directly (all required
   fields; for a short, obvious causal path the counterfactual may be recorded
   as `result: incomplete` with one sentence of justification).
4. Write `.causal-repair/contract-tests.py` (one witness per clause, negative
   case per error contract) and confirm the broken-clause witnesses FAIL on the
   current buggy code.
5. Patch minimally against the contract. Run the visible test + contract
   tests. Create the patch manifest. Self-review the diff against the
   workaround reject rules (no subagent).

Keep reasoning proportional to the bug: for a one-clause, single-file fix, do
not deliberate at length or re-investigate settled questions — enumerate,
test, patch, verify, stop. Deep analysis on a trivial bug is itself a failure
mode (it increases non-completion without improving the fix).

**ESCALATE to the full workflow below** only when at least one holds:

- the fast path failed twice (visible or contract tests still failing, or a
  witness cannot be made to hold honestly)
- the contract spans multiple files/modules, or more than ~4 interlocking
  clauses
- the causal path is still unclear after the first reproduction
- prior patches in this repo already added workaround-shaped logic
- the user explicitly asks for the full/multi-agent workflow

Escalation adds: diverse investigator fan-out, the root-cause judge, executed
counterfactuals, the adversarial workaround-reviewer and repair-verifier
subagents, and the Ledger-Relay protocol for long-horizon repairs. De-escalate
back to the fast path when the blocking question is resolved.

## Required workflow

### 0. Create a mechanical checkpoint

Before any code modification, create a checkpoint that can protect unrelated user work.

If this plugin repository is available, prefer the bundled script:

```bash
bash scripts/create-checkpoint.sh
```

If the script is not available, run the equivalent commands manually:

```bash
mkdir -p .causal-repair
git rev-parse --show-toplevel
git rev-parse HEAD
git status --short
git diff --binary > .causal-repair/pre-existing.diff
git diff --cached --binary > .causal-repair/pre-existing-staged.diff
git ls-files --others --exclude-standard -z > .causal-repair/pre-existing-untracked.zlist
```

If the working tree has unrelated edits, do not rely on semantic memory to revert. Either:

1. work only on files that are not already modified, or
2. ask the user to commit/stash unrelated changes, or
3. create a separate worktree/branch when possible.

The final report must include the base commit and the checkpoint files used.

### 1. Capture failing evidence first

Before any code modification:

1. Run or inspect the failing test/reproduction.
2. Record the exact command, failing test name, stack trace, and relevant output.
3. Identify the first failing assertion or thrown error.
4. Save `git status --short`, `git diff --stat`, and the base commit.

If the evidence cannot be captured, mark the RCA gate incomplete.

### 2. Investigate root cause before patching

Use the bundled subagents when available:

- `root-cause-investigator` for read-only investigation
- `root-cause-judge` for gate approval
- `workaround-reviewer` for post-patch review
- `repair-verifier` for validation evidence

For non-trivial failures, use at least two different investigation prompts or model routes when available. Diversity matters more than count. If every investigator uses the same model and evidence, treat agreement as weak evidence, not proof.

Each investigation must produce:

```text
- exact failing symptom
- execution path from test/input to failure
- observed invariant, contract, or state transition that appears broken
- whether the invariant is explicit, inferred, or unknown
- documented contract clauses of the code under repair (from its
  docstring/comments/spec), each marked broken, held, or at-risk —
  including error contracts and edge cases the visible test does not touch
- likely root-cause file/function
- evidence from code or runtime output
- counterfactual check that could falsify the hypothesis
- minimal valid patch shape (minimal relative to the documented contract,
  not relative to the visible test)
- workaround patterns to reject
```

Enumerate only clauses the code actually documents — do not invent a contract. But enumerate ALL of them: the most common failure is a patch that satisfies the visible test while silently dropping a documented behavior (especially "invalid input must raise").

### 3. Apply the RCA gate and write rca-gate.json

Do not edit production code until the root-cause gate has all required fields:

```text
RCA Gate
- Failure evidence:
- Causal path:
- Broken behavior:
- Contract/invariant status: explicit, inferred, or unknown
- Contract clauses: each documented behavior with status broken/held/at-risk
- Root-cause location:
- Why this is the cause, not only a symptom:
- Counterfactual check:
- Minimal valid patch shape:
- Workaround reject rules:
- Tests to run after patching: visible reproduction AND authored contract tests
- Checkpoint files:
```

If an invariant is unknown, say so. Do not invent one to fill the form. The gate can pass with `Contract/invariant status: unknown` only when the counterfactual check and runtime evidence still support the causal path.

When hook enforcement is installed, write the approved gate to:

```text
.causal-repair/rca-gate.json
```

Use the schema shown in `examples/rca-gate.example.json`, then validate it:

```bash
python scripts/validate-rca-gate.py .causal-repair/rca-gate.json
```

### 4. Run and verify a counterfactual check when practical

Before patching, perform at least one lightweight check that can falsify the root-cause hypothesis. Examples:

- Add a temporary log/assertion/probe and remove it before the final patch.
- Run the failing test with a narrowed input that should bypass the suspected path.
- Compare behavior before and after reverting the suspected local change.
- Confirm that changing an unrelated branch does not affect the failure.

Record the check in `.causal-repair/rca-gate.json` as:

```json
{
  "counterfactual_check": {
    "command": "the exact command to run",
    "result": "pass | failed | incomplete",
    "evidence": "what the command proves or why it is incomplete"
  }
}
```

If this plugin repository is available and the result is not `incomplete`, verify the recorded result against the command's real exit status:

```bash
python scripts/run-counterfactual.py .causal-repair/rca-gate.json
```

If no counterfactual check is practical, record `result: incomplete`, explain why, and lower confidence. Do not present the causal path as proven.

### 4.5 Write contract tests before patching

Before touching production code, write `.causal-repair/contract-tests.py` (allowed by the hook — it lives under `.causal-repair/`). It must:

1. Contain at least one assertion per contract clause recorded in the RCA gate.
2. Include at least one negative case for every documented error contract (e.g. asserting that invalid input raises the documented exception).
3. Be runnable standalone: `python .causal-repair/contract-tests.py` exits 0 on success, non-zero on any violated clause.

Add it to the gate's `tests_to_run`. The validator rejects a gate whose `tests_to_run` does not reference `.causal-repair/contract-tests*` — the visible reproduction alone is not validation.

These tests are the mechanical defense against under-fit patches: a fix that satisfies the visible test but drops a documented behavior must fail here before review even starts.

### 5. Patch minimally and create a patch manifest

When the RCA gate is satisfied:

1. Make the smallest production change that restores the FULL documented contract recorded in the gate's contract clauses. "Minimal" means minimal relative to the contract, not relative to the visible test — a change that makes the visible test pass while leaving a documented clause (especially an error contract) unimplemented is under-fit, not minimal.
2. Keep the diff on the causal path.
3. Avoid broad refactors unless the RCA gate proves they are necessary.
4. Do not change tests to match broken behavior unless the test itself is proven wrong.
5. Create a patch manifest after editing.

If this plugin repository is available, run:

```bash
python scripts/create-patch-manifest.py --output .causal-repair/patch-manifest.json
```

The manifest must show:

- changed files
- whether each file was already dirty at checkpoint time
- whether each file is safe for automatic revert
- new untracked files created after the checkpoint
- `git diff --check` result

If the script is unavailable, manually report the same fields. Files marked `pre_existing_dirty=true` require manual hunk review before revert.

### 6. Review workaround risk without categorical bans

After patching, review the diff against these rejection rules.

Reject and revert the patch if it:

- adds a condition that only handles the observed failing case
- checks a failing test name, fixture, literal error string, or narrow magic value
- adds broad `catch`, `try`, `except`, `rescue`, or `finally` behavior that hides the real error
- adds default values, null coalescing, empty arrays, empty objects, sleeps, retries, or fallbacks that mask invalid state
- changes test fixtures instead of fixing production logic
- makes the original test pass while weakening the domain contract
- changes code outside the causal path without explaining why
- lacks adjacent regression validation
- leaves any contract clause from the RCA gate unimplemented or untested (under-fit) — especially documented error contracts
- has no authored contract tests, or the contract tests lack a negative case for a documented error contract

Do not categorically reject null checks, retries, fallback values, or catches. They are valid only when the RCA gate explains the contract they restore and the validation covers the adjacent behavior.

### 7. Verify

Run:

1. the original failing test or reproduction
2. the authored contract tests: `python .causal-repair/contract-tests.py`
3. adjacent tests around the changed module
4. the smallest relevant regression suite available

Also report:

```bash
git diff --stat
git diff --check
python scripts/create-patch-manifest.py --output .causal-repair/patch-manifest.json
```

If verification fails or the workaround review rejects the diff:

1. do not use `git reset --hard` in a dirty user worktree
2. revert only the files/hunks listed in the patch manifest or checkpoint
3. files with `pre_existing_dirty=true` require manual hunk review
4. keep the evidence
5. restart from root-cause investigation
6. stop after two rounds with no new evidence

### 8. Final response format

End with:

```text
Base commit:
Checkpoint:
RCA gate file:
Counterfactual execution:
Patch manifest:
Root cause:
Causal path:
Contract/invariant status:
Contract clauses: <each clause: restored | held | NOT COVERED>
Counterfactual check:
Fix:
Why this is not a workaround:
Why this is not under-fit (every documented clause covered):
Rejected alternatives:
Validation:
Remaining risk:
```

If validation could not be run, say exactly why and what command the user should run.

## Long-horizon protocol (Ledger-Relay)

Long problems are not solved with long contexts. When the repair spans multiple files, needs several dependent fixes, or you notice context drift (forgetting the goal, re-investigating settled questions), switch to the ledger:

1. **Initialize** `.causal-repair/ledger.json` (allowed by the hook) with the goal, the enumerated contract clauses, and a plan of segments. Validate it:

```bash
python scripts/validate-ledger.py .causal-repair/ledger.json
```

Each segment must be small enough to finish in one focused subagent run (≤ 8 turns) and must have a `done_criteria` that is a runnable command or mechanically checkable condition — never "looks correct".

```json
{
  "goal": "one-sentence repair goal",
  "segments": [
    {"id": "s1-investigate", "kind": "investigate", "objective": "...",
     "done_criteria": "command", "status": "pending"},
    {"id": "s2-rca", "kind": "rca", "objective": "...", "done_criteria": "python scripts/validate-rca-gate.py .causal-repair/rca-gate.json", "status": "pending"},
    {"id": "s3-contract-tests", "kind": "contract-tests", "objective": "...", "done_criteria": "python .causal-repair/contract-tests.py exits non-zero on the buggy code", "status": "pending"},
    {"id": "s4-patch", "kind": "patch", "objective": "...", "done_criteria": "python .causal-repair/contract-tests.py", "status": "pending"},
    {"id": "s5-review", "kind": "review", "objective": "...", "done_criteria": "reviewer verdict recorded", "status": "pending"},
    {"id": "s6-verify", "kind": "verify", "objective": "...", "done_criteria": "original + contract + adjacent tests pass", "status": "pending"}
  ],
  "attempts": 0,
  "stop_condition": "two rounds without new evidence"
}
```

2. **Relay**: run exactly one segment at a time. Mark it `in_progress`, delegate it to a fresh subagent whose prompt contains only the ledger contents and the segment objective (never rely on conversation memory as the handoff), check its `done_criteria` mechanically, record `evidence`, mark `done`, then move on. When hook enforcement is installed, production edits are blocked unless the active segment has `kind: "patch"`.

3. **Failure**: mark the segment `failed`, revert with the patch manifest if code changed, record what was learned in `evidence`, increment `attempts`, and re-plan the remaining segments. After two attempts without new evidence, stop and report per the stop conditions.

The ledger is the single source of truth. Any subagent that disagrees with the ledger re-reads the repository evidence instead of trusting its own recollection.

## Dynamic workflow option

For larger fixes, ask Claude Code to use a dynamic workflow. Load the template at:

```text
${CLAUDE_SKILL_DIR}/../../resources/workflow-template.md
```

Use it when:

- the failure touches many files
- multiple hypotheses are plausible
- prior patches already added workaround logic
- the user explicitly asks for dynamic workflow, ultracode, multi-agent repair, or model ensemble behavior

The dynamic workflow must preserve the same gates: checkpoint first, evidence first, RCA before patch, counterfactual execution when practical, `.causal-repair/rca-gate.json` before production edits when hooks are installed, patch manifest after patch, workaround review after patch, verification before done.

## Arguments

User request:

```text
$ARGUMENTS
```
