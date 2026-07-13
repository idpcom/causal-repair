# Causal Repair Dynamic Workflow Template (Ledger-Relay)

Use this reference when the user asks to run Causal Repair as a dynamic workflow, when a failure requires multiple independent investigations, or when the repair is long-horizon (multi-file, several dependent fixes).

Claude Code dynamic workflows are JavaScript orchestration scripts. The exact runtime APIs may vary by Claude Code version, so prefer asking Claude Code to generate the workflow from this template when needed.

## Core principle

Long problems are not solved with long contexts. The orchestration externalizes all state into `.causal-repair/ledger.json`, runs one short segment at a time in a fresh subagent, and validates every handoff mechanically:

- **Ledger** — goal, contract clauses, segment plan, per-segment status/evidence. Validated by `python scripts/validate-ledger.py`.
- **Relay** — each segment gets a fresh subagent whose prompt contains only the ledger and the segment objective. Conversation memory is never the handoff.
- **Mechanical gates** — a segment is done only when its `done_criteria` command exits 0, not when its agent says so.

## Orchestration intent

```text
Input:
- user repair request
- optional failing test command
- optional target files

Stages:
0. Create a mechanical checkpoint before edits.
1. Initialize the ledger: goal, documented contract clauses, segment plan.
   Validate with scripts/validate-ledger.py.
2. Segment: investigate (fan out diverse read-only investigations; MiMo-class
   agents are good here).
3. Segment: rca — judge approves; write .causal-repair/rca-gate.json and
   validate with scripts/validate-rca-gate.py (contract clauses required).
4. Segment: contract-tests — author .causal-repair/contract-tests.py, one
   assertion per clause, one negative case per error contract. Done when it
   FAILS on the buggy code (it must be able to detect the bug).
5. Run the counterfactual check (scripts/run-counterfactual.py).
6. Segment: patch — only now are production edits allowed (the hook enforces
   kind: "patch" in_progress). Minimal against the contract, not the visible
   test. Create the patch manifest after editing. Qwen-class coder agents are
   good here.
7. Segment: review — workaround reviewer checks over-fit shapes AND under-fit
   (unimplemented documented clauses).
8. Segment: verify — original reproduction + contract-tests + adjacent tests.
9. On failure: mark segment failed, revert only patch-manifest-safe hunks,
   record evidence in the ledger, increment attempts, re-plan.
10. Stop after two attempts with no new evidence (ledger validator enforces
    the attempts ceiling).
```

## Script shape

```javascript
export const meta = {
  name: 'causal-repair-ledger-relay',
  description: 'Segmented, ledger-driven root-cause repair for long-horizon fixes',
}

const request = args ?? 'Fix the failing test using causal repair.'

// Stage 0-1: checkpoint, then initialize and validate the ledger.
await agent(`
Create a mechanical checkpoint (bash scripts/create-checkpoint.sh), then write
.causal-repair/ledger.json for this request:

${request}

The ledger must contain: goal; documented contract clauses of the code under
repair; segments s1-investigate, s2-rca, s3-contract-tests, s4-patch,
s5-review, s6-verify (kind matching each name); attempts: 0; stop_condition.
Every done_criteria must be a runnable command. Validate with:
python scripts/validate-ledger.py .causal-repair/ledger.json
Do not edit production code.
`, { label: 'init-ledger' })

// Relay loop: one segment at a time, fresh context each time.
// Read the ledger between segments; never pass agent output directly onward.
const segments = ['s1-investigate', 's2-rca', 's3-contract-tests', 's4-patch', 's5-review', 's6-verify']
for (const id of segments) {
  await agent(`
Read .causal-repair/ledger.json. Set segment ${id} to in_progress (only one
segment may be in_progress). Execute ONLY that segment's objective. The ledger
is your entire context: if anything is unclear, re-read repository evidence
instead of guessing.
When the segment's done_criteria command exits 0, record evidence in the
ledger, mark the segment done, and stop.
If it cannot be satisfied, mark the segment failed with evidence and stop.
`, { label: id })

  // Mechanical gate between segments — do not proceed on a failed handoff.
  const check = await bash('python scripts/validate-ledger.py .causal-repair/ledger.json')
  if (check.exitCode !== 0) break
}

// Failure policy: revert patch-manifest-safe hunks, bump attempts, re-plan
// remaining segments. The ledger validator rejects attempts > 2: stop there
// and report per the skill's final response format.
```

## Model routing inside the relay

- `investigate`, `review`, `verify` segments: fast/agentic models (MiMo-class).
- `rca` judgment and `patch` authoring: the strongest coder available (Qwen-class).
- Never set `CLAUDE_CODE_SUBAGENT_MODEL` globally when mixed routing is intended.

## Stop conditions

- attempts exceeds 2 (ledger validator blocks further rounds)
- the same hypothesis fails its counterfactual twice
- validation cannot run at all (report exactly why and what command the user should run)
- the working tree is too dirty for safe repair (report, do not force)
