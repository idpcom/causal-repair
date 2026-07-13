# Proof-Carrying Repair (addendum)

Your patch must carry mechanically checkable evidence, not a claim of
correctness. In addition to the standard causal-repair workflow, obey these
rules — the witness checker will reject a patch that does not.

## Contract tests must be structured one-witness-per-clause

Write `.causal-repair/contract-tests.py` so that every contract clause in the
RCA gate has its own witness function, and expose a `WITNESSES` dict mapping the
**1-based clause index** (matching the order of `contract_clauses` in
`.causal-repair/rca-gate.json`) to that function:

```python
from mymodule import thing   # import the code under repair

def clause_1():
    # assert what clause 1 promises; raise on violation
    ...

def clause_2():
    # an error contract: assert the documented exception is raised
    try:
        thing(bad_input)
    except ValueError:
        pass
    else:
        raise AssertionError("clause 2: invalid input must raise ValueError")

WITNESSES = {1: clause_1, 2: clause_2, ...}   # one entry per gate clause
```

Every clause needs an entry. A clause with no witness is rejected.

## The witnesses your tests must satisfy

Run, after patching:

```bash
python scripts/verify-witnesses.py --repo .
```

It enforces:

1. **State witness (per clause).** Each clause witness must PASS on your patched
   code (the fix restores every clause). On the checkpointed base code it must
   FAIL for clauses you marked `broken` or `at-risk`, and PASS for clauses you
   marked `held`. So:
   - A test that already passes on the buggy base is not evidence — it does not
     detect the broken behavior. Write it to actually exercise the violation.
   - Do not mislabel a broken clause as `held` to avoid work — the base run will
     contradict you.
   - Do not leave an `at-risk`/`broken` clause unimplemented — its witness will
     fail on your patch.

2. **Strength witness.** Deterministic mutants of your patched files must be
   killed by the suite; if any clause is an error contract, a mutant that
   deletes a `raise` must be caught. Vacuous tests (`assert True`) fail this.

If `verify-witnesses.py` reports a failure, your repair is NOT done: fix the
patch (or strengthen the tests to honestly reflect the contract) and re-run
until the witnesses hold. Never weaken a witness to make it pass — that defeats
the purpose. The final report must state `Witnesses: hold` only after the script
exits 0.
