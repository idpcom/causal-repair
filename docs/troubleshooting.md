# Troubleshooting

## The skill does not appear

Run:

```text
/reload-plugins
```

If running locally, start Claude Code with:

```bash
claude --plugin-dir .
```

## The command name is unexpected

Marketplace plugins namespace skills by plugin name. This plugin exposes:

```text
/causal-repair:causal-repair
```

## The agent edits code too early

Tell Claude Code:

```text
Use the causal-repair RCA gate. Do not edit until the gate is complete.
```

## The verifier cannot run tests

The verifier should report the exact blocker and the command the user should run locally.

## Dynamic workflow is not used

Ask explicitly:

```text
Use a dynamic workflow with causal-repair.
```

The skill should then load `resources/workflow-template.md` and generate a workflow from it.
