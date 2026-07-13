---
name: goal
description: Short skill alias for goal-style Causal Repair. Use when a bug fix should continue until RCA, workaround review, and validation criteria are met.
---

# Causal Repair Goal

Use a goal-style Causal Repair loop for:

```text
$ARGUMENTS
```

Continue until all completion criteria are met:

1. The RCA gate is complete.
2. The patch is on the causal path.
3. The diff passes workaround review.
4. The original failing test passes.
5. Adjacent regression tests pass, or validation is explicitly marked incomplete with the exact blocker.
6. The final report includes Root cause, Causal path, Fix, Why this is not a workaround, Rejected alternatives, Validation, and Remaining risk.

Stop after 12 turns or two rounds with no new root-cause evidence.
