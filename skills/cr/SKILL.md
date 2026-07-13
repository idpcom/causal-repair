---
name: cr
description: Shortest skill alias for Causal Repair. Use for root-cause-first bug fixing with checkpointing, counterfactual RCA, and workaround rejection.
---

# CR

Run Causal Repair on:

```text
$ARGUMENTS
```

Required rules:

```text
No checkpoint, no patch.
No RCA, no patch.
No causal path, no patch.
No counterfactual check, no confidence.
No workaround review, no done.
```

Default to the FAST PATH: single agent, no subagent fan-out. Produce the
artifacts (checkpoint, contract clauses, per-clause contract tests, gate file)
compactly and keep reasoning proportional to the bug. Escalate to the full
multi-agent workflow only if the fast path fails twice, the contract spans
multiple files, or the causal path stays unclear.

Required flow:

1. Create a mechanical checkpoint before editing, preferably with `bash scripts/create-checkpoint.sh` when available.
2. Capture failing evidence.
3. Build an RCA gate with causal path, contract/invariant status, enumerated documented contract clauses (each broken/held/at-risk, error contracts included), counterfactual check, patch shape, reject rules, tests, and checkpoint files.
4. Do not invent invariants. Use `unknown` when the codebase does not state one — but enumerate every clause the code documents.
5. Write `.causal-repair/contract-tests.py` covering every clause (negative case per error contract) and add it to tests_to_run.
6. Patch minimally against the documented contract (not just the visible test) and record a patch manifest.
7. Review workaround risk without categorically rejecting valid null checks, catches, fallbacks, or retries — and reject under-fit patches that leave a documented clause unimplemented.
8. Validate with the original failing test, the contract tests, plus adjacent tests.
9. Never use `git reset --hard` in a dirty user worktree.

Final report must include:

```text
Base commit:
Checkpoint:
Root cause:
Causal path:
Contract/invariant status:
Counterfactual check:
Fix:
Why this is not a workaround:
Rejected alternatives:
Validation:
Remaining risk:
```
