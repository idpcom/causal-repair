---
description: Review a patch for workaround-shaped fixes using Causal Repair rules.
argument-hint: "[optional patch, PR, or review target]"
---

Review the current patch or requested target using Causal Repair workaround rules.

Target:

```text
$ARGUMENTS
```

Reject the patch if it:

- adds symptom-only conditionals
- depends on a test name, fixture name, literal error string, or narrow magic value
- adds broad catch behavior that hides invalid state
- adds fallback/default masking without restoring the invariant
- uses sleeps/retries without proving the timing root cause
- changes tests or fixtures to fit broken production behavior
- changes code outside the causal path without explaining why
- leaves a documented contract clause of the modified code unimplemented or untested (under-fit) — read the docstring; documented error behavior must still raise, with a test proving it

Return:

```text
Verdict: ACCEPT or REJECT
Reason:
Evidence from diff:
Causal-path alignment:
Contract clauses check:
Workaround risk:
Under-fit risk:
Required follow-up:
```

Quote only the diff hunks relevant to your verdict, not the full diff.
