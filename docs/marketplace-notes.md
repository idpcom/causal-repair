# Marketplace Notes

This repository is prepared as a Claude Code plugin package.

## Required structure

- `.claude-plugin/plugin.json` defines plugin metadata.
- `skills/causal-repair/SKILL.md` defines the user-facing skill.
- `agents/*.md` defines supporting subagents.
- `resources/` contains reference material that the skill can load on demand.

## Validation checklist

Before submitting to a marketplace:

```bash
claude plugin validate .
claude --plugin-dir .
```

Then run a small real-world smoke test:

```text
/causal-repair:causal-repair fix a failing test in this sample repository
```

The expected behavior is that Claude Code captures failing evidence and completes an RCA gate before editing code.
