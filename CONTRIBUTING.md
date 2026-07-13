# Contributing

Thank you for improving Causal Repair.

## Design principles

- Keep the skill focused on root-cause-first repair.
- Do not add instructions that encourage symptom-only patches.
- Keep `SKILL.md` concise and move detailed references into supporting files.
- Prefer explicit gates over vague advice.
- Treat third-party model outputs as evidence candidates, not as patch authority.

## Local validation

```bash
claude plugin validate .
claude --plugin-dir .
```

Inside Claude Code:

```text
/causal-repair:causal-repair fix a small failing test in a sample repository
```

## Pull request checklist

- [ ] The RCA gate still appears before patching.
- [ ] Workaround rejection rules remain strict.
- [ ] README and examples are updated when behavior changes.
- [ ] The plugin manifest version is bumped when publishing a release.
