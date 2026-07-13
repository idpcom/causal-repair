# Commands

Causal Repair exposes both a marketplace skill and shorter command aliases.

## Primary skill

```text
/causal-repair:causal-repair fix the failing test
```

## Short aliases

```text
/causal-repair:cr fix the failing test
/causal-repair:fix fix the failing test
/causal-repair:review review the current diff
/causal-repair:goal fix the failing test with goal-style completion criteria
```

## Recommended daily command

Use this most of the time:

```text
/causal-repair:cr fix the failing test. Test command: npm test -- user.service.test.ts
```

## With Claude Code `/goal`

You can also combine it with Claude Code's built-in `/goal`:

```text
/goal use /causal-repair:cr to fix this bug. Finish only when the RCA gate is complete, the original and adjacent tests pass, the diff passes workaround review, and the final report includes root cause, causal path, fix, rejected alternatives, and validation.
```

## Namespace note

Plugin commands are namespaced by the plugin name. Because this plugin is named `causal-repair`, the short aliases are exposed as `/causal-repair:cr`, `/causal-repair:fix`, and similar commands.

If you want the namespace itself to be short, install or publish a variant with plugin name `cr`. Then the command style becomes `/cr:fix` or `/cr:cr` depending on the installed command name.
