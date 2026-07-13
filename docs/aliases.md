# Aliases

Causal Repair keeps the full marketplace skill name and also exposes short aliases.

## Short skill aliases

Use these if your Claude Code version exposes plugin skills:

```text
/causal-repair:cr
/causal-repair:fix
/causal-repair:review
/causal-repair:goal
```

## Short command aliases

Use these if your Claude Code version exposes plugin commands:

```text
/causal-repair:cr
/causal-repair:fix
/causal-repair:review
/causal-repair:goal
```

Both skill and command alias files are included so the plugin has a short entry point across Claude Code versions that prefer one mechanism over the other.

## Why the namespace is still long

Plugin commands are normally namespaced by the plugin name. This repository keeps the plugin name `causal-repair` for marketplace clarity and searchability.

If you want a shorter namespace, publish or install a variant whose plugin manifest name is `cr`. Then the commands become:

```text
/cr:cr
/cr:fix
/cr:review
/cr:goal
```

Recommended daily use with the current marketplace name:

```text
/causal-repair:cr fix the failing test
```
