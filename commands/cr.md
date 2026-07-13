---
description: Short alias for Causal Repair. Runs root-cause-first repair with checkpointing, counterfactual RCA, workaround review, and validation.
argument-hint: "[failing test command or bug symptom]"
---

Run Causal Repair on this request:

```text
$ARGUMENTS
```

Follow the Causal Repair rules:

```text
No checkpoint, no patch.
No RCA, no patch.
No causal path, no patch.
No counterfactual check, no confidence.
No workaround review, no done.
```

Default to the fast path: single agent, no subagent fan-out, compact gate
artifacts, reasoning proportional to the bug. Escalate to the full multi-agent
workflow only on repeated failure, multi-file contracts, or an unclear causal
path.

Required flow:

1. Create a mechanical checkpoint before editing, preferably with `bash scripts/create-checkpoint.sh` when available.
2. Capture failing evidence before editing.
3. Build an RCA gate with failure evidence, causal path, contract/invariant status, enumerated documented contract clauses (each broken/held/at-risk, error contracts included), counterfactual check, root-cause location, minimal patch shape, workaround reject rules, validation commands, and checkpoint files.
4. Do not patch until the RCA gate is complete.
5. Do not invent invariants. Use `unknown` when the codebase does not state one — but enumerate every clause the code documents.
6. Write `.causal-repair/contract-tests.py` covering every clause (negative case per error contract) and add it to the validation commands.
7. Patch minimally against the documented contract (not just the visible test) and record a patch manifest.
8. Review workaround risk without categorically rejecting valid null checks, catches, fallbacks, or retries — and reject under-fit patches that leave a documented clause unimplemented.
9. Run the original failing test, the contract tests, and adjacent tests.
10. Never use `git reset --hard` in a dirty user worktree.
11. Final report must include Base commit, Checkpoint, Root cause, Causal path, Contract/invariant status, Contract clauses (each restored/held/NOT COVERED), Counterfactual check, Fix, Why this is not a workaround, Why this is not under-fit, Rejected alternatives, Validation, and Remaining risk.
