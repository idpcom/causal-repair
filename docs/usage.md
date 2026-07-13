# Usage

## Local plugin run

```bash
claude --plugin-dir .
```

Then invoke:

```text
/causal-repair:causal-repair fix the failing test. Test command: npm test -- user.service.test.ts
```

## With a symptom only

```text
/causal-repair:causal-repair users sometimes get an empty profile after login
```

Claude Code should first find or create a reproduction path before editing.

## With dynamic workflow

```text
/causal-repair:causal-repair use a dynamic workflow to fix the failing API regression without adding workaround conditionals
```

For larger fixes, the skill should load `resources/workflow-template.md` and ask Claude Code to generate a workflow from the template.

## Expected final report

```text
Root cause:
Causal path:
Fix:
Why this is not a workaround:
Rejected alternatives:
Validation:
Remaining risk:
```
