# RCA Gate

The RCA gate is the required checkpoint before patching. When hook enforcement
is installed, the machine-checked form lives at `.causal-repair/rca-gate.json`
and is validated by `scripts/validate-rca-gate.py` (and independently by the
PreToolUse hook). The prose form mirrors the same fields:

```text
RCA Gate
- Failure evidence:
- Causal path:
- Broken behavior:
- Contract/invariant status: explicit, inferred, or unknown
- Contract clauses: each documented behavior with status broken/held/at-risk
- Root-cause location:
- Why this is the cause, not only a symptom:
- Counterfactual check: command, result (pass/failed/incomplete), evidence
- Minimal valid patch shape (minimal vs the documented contract, not the visible test):
- Workaround reject rules:
- Tests to run after patching: visible reproduction AND authored contract tests
- Checkpoint files:
```

## JSON schema (machine-checked)

Required fields in `.causal-repair/rca-gate.json`:

| field | rule |
|---|---|
| `failure_evidence`, `causal_path`, `broken_behavior`, `root_cause_location`, `cause_not_symptom`, `minimal_patch_shape` | non-empty text, length >= 12 |
| `contract_invariant_status` | `explicit`, `inferred`, or `unknown` |
| `contract_clauses` | non-empty list of `{clause, status, covered_by}`; `status` is `broken`, `held`, or `at-risk` |
| `counterfactual_check` | object `{command, result, evidence}`; `result` is `pass`, `failed`, or `incomplete`; no `claude --bare` |
| `workaround_reject_rules` | non-empty list of strings |
| `tests_to_run` | >= 2 commands, including a reference to `.causal-repair/contract-tests*` |
| `checkpoint` | path to a real checkpoint directory with a 40-char base commit |

See `examples/rca-gate.example.json` for a complete valid instance.

## Contract clauses

Enumerate every behavior the docstring/comments/spec of the code under repair
document — including error contracts ("invalid input must raise X") and edge
cases the visible test does not exercise. Do not invent clauses the code does
not document. The clause list is what prevents the under-fit failure mode: a
patch that satisfies the visible test while silently dropping a documented
behavior.

Before patching, write `.causal-repair/contract-tests.py` with at least one
assertion per clause and at least one negative case per error contract, and add
it to `tests_to_run`.

## Pass criteria

The gate passes only when:

- the failure was observed or a concrete reproduction path exists
- the execution path reaches the suspected root-cause location
- the contract status is stated honestly (unknown is allowed when runtime
  evidence still supports the causal path)
- every documented contract clause is enumerated with an honest status
- the proposed patch restores the full documented contract
- validation includes both the visible reproduction and the authored contract tests

## Fail criteria

The gate fails when:

- the hypothesis only restates the failing assertion
- the causal path is missing
- the clause list omits documented behavior (especially error contracts), or
  only mirrors what the visible test checks
- the patch shape is a fallback, broad catch, or test-specific branch
- the patch shape is minimal against the visible test instead of the contract
- validation is only the visible reproduction
- unrelated local changes make a safe patch impossible
