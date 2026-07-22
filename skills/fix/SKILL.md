---
name: fix
description: Short skill alias for Causal Repair. Use to fix failing tests, regressions, and workaround-prone bugs with root-cause-first repair.
---

# Causal Repair Fix

Use this short skill alias for the same workflow as `causal-repair`.

Default to the fast path: single agent, compact gate artifacts, reasoning
proportional to the bug. Escalate to the full multi-agent workflow only on
repeated failure, multi-file contracts, or an unclear causal path.

Request:

```text
$ARGUMENTS
```

Rules:

```text
No RCA, no patch.
No causal path, no patch.
No workaround review, no done.
```

Before editing code, complete the RCA gate:

```text
RCA Gate
- Failure evidence:
- Causal path:
- Broken invariant or contract:
- Contract clauses: each documented behavior with status broken/held/at-risk
- Root-cause location:
- Why this is the cause, not only a symptom:
- Minimal valid patch shape (minimal vs the documented contract, not the visible test):
- Workaround reject rules:
- Tests to run after patching: visible reproduction AND authored contract tests
```

Write `.causal-repair/contract-tests.py` covering every clause (negative case per error contract) before patching. Patch minimally against the documented contract, review the diff for workaround patterns AND unimplemented documented clauses, and validate with the original failing test, the contract tests, plus adjacent tests.

Keep the transcript lean: the files on disk are the record, so report pass/fail and the first failing line rather than pasting full diffs or full stdout.

Final report:

```text
Root cause:
Causal path:
Contract clauses: <each clause: restored | held | NOT COVERED>
Fix:
Why this is not a workaround:
Why this is not under-fit:
Rejected alternatives:
Validation:
Remaining risk:
```
