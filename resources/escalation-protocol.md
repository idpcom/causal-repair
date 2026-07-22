# Escalation protocol (reference material)

This file holds the detail that `skills/causal-repair/SKILL.md` only
summarizes: the full multi-agent investigation template and the Ledger-Relay
segment schema. Like `resources/workflow-template.md`, it is reference
material, not an auto-running script — the skill points here only when it
actually escalates, so ordinary fast-path repairs never load it.

## Full investigation template

Use the bundled subagents:

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

Synthesis (`root-cause-judge`): do not choose by majority vote alone; prefer
the hypothesis that explains both the symptom and the causal path; reject
hypotheses that only describe the final failing assertion. See
`agents/root-cause-judge.md` for its full approval criteria.

## Ledger-Relay: full segment schema

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
