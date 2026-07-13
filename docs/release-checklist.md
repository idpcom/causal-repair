# Release Checklist

Before publishing a new marketplace version:

- [ ] Update `VERSION`.
- [ ] Update `.claude-plugin/plugin.json` version.
- [ ] Update `CHANGELOG.md`.
- [ ] Run `scripts/validate-structure.sh`.
- [ ] Run `claude plugin validate .`.
- [ ] Run a smoke test with `claude --plugin-dir .`.
- [ ] Confirm `/causal-repair:causal-repair` appears in `/help`.
- [ ] Confirm the skill captures evidence before edits.
- [ ] Confirm workaround-shaped patches are rejected.
- [ ] Tag the release.
