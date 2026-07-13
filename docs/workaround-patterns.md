# Workaround Patterns

Reject patches that match these patterns unless the RCA gate proves they restore the underlying invariant.

## Symptom-only conditional

```text
if observed failure case:
    return special value
```

Risk: passes the visible test while leaving other cases broken.

## Broad fallback

```text
return value || defaultValue
```

Risk: hides invalid state instead of repairing the data flow.

## Error suppression

```text
try:
    operation()
catch:
    return safeDefault
```

Risk: converts a real contract violation into silent data loss.

## Sleep or retry without cause

```text
sleep(1000)
retry()
```

Risk: masks nondeterminism without fixing ordering, locking, or lifecycle logic.

## Test-specific behavior

```text
if env == "test" or fixture == "known-fixture":
    behave differently
```

Risk: production remains broken.

## Fixture mutation

Changing test data to fit broken production behavior is not a fix unless the test fixture is demonstrably wrong.
