# Minimal Session Example

## Direct invocation

```text
/causal-repair:causal-repair fix the failing test. Test command: npm test -- user.service.test.ts
```

## Expected behavior

Causal Repair should not edit files immediately. It should first capture the failing evidence and produce an RCA gate:

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

It should then write `.causal-repair/contract-tests.py` covering every enumerated clause. Only after that gate is complete should it edit code.

## Bad patch shape

```text
if (user.id === "fixture-user") {
  return defaultProfile;
}
```

This is rejected because it handles only the observed fixture.

## Better patch shape

```text
Restore the profile loading contract so every authenticated user follows the same validated lookup path.
```

The actual code depends on the project, but the fix should restore the invariant rather than special-case the symptom.

## Final report shape

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
