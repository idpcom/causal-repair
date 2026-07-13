# Design

Causal Repair is built around gates rather than confidence.

## Problem

When a coding agent sees a failing test, it may overfit to the visible failure:

- add a narrow conditional
- add a fallback value
- catch and suppress the error
- weaken the test
- retry or sleep around timing issues

These changes can pass the test while leaving the underlying contract broken.

## Approach

Causal Repair changes the order of work:

```text
failure evidence -> root-cause investigation -> RCA gate -> minimal patch -> workaround review -> validation
```

The patch is not allowed until the RCA gate is complete.

## Gate fields

The RCA gate must include:

- failure evidence
- causal path
- broken invariant or contract
- root-cause location
- why it is the cause rather than only the symptom
- minimal valid patch shape
- workaround reject rules
- validation commands

## Model routing

Fast models are useful for:

- evidence extraction
- file search
- independent hypothesis generation
- workaround review
- validation summaries

Stronger models should handle:

- RCA judgment
- patch authoring
- final merge decisions

## Failure policy

If review or validation fails, revert the attempted patch and restart from RCA using the new evidence. Do not stack workaround patches on top of failed workaround patches.
