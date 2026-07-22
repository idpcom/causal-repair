---
description: Fix a failing test or regression with Causal Repair.
argument-hint: "[failing test command or bug symptom]"
---

Fix this request using the Causal Repair workflow. Default to the fast path
(single agent, compact artifacts, reasoning proportional to the bug); escalate
to the full multi-agent workflow only on repeated failure, multi-file
contracts, or an unclear causal path.

Request:

```text
$ARGUMENTS
```

Before editing code, prove the root cause with:

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

Write `.causal-repair/contract-tests.py` covering every clause (negative case per error contract) before patching.

Reject symptom-only conditionals, broad fallback/default masking, broad try/catch, sleeps/retries, test-specific behavior — and under-fit patches that leave a documented clause (especially error contracts) unimplemented.

Finish only after the original failing test, the contract tests, and adjacent tests pass, or report exactly why validation is incomplete.

Keep the transcript lean: report pass/fail and the first failing line rather than pasting full diffs or full stdout — the on-disk artifacts are the record.
