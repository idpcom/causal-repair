# Hardening Notes

This plugin is still an instruction-level harness. It cannot physically prevent every bad edit, but it now tries to reduce the biggest failure modes with mechanical checkpoints, patch manifests, counterfactual checks, script tests, and executable fixture evals.

## Addressed weaknesses

### Gate without enforcement

The skill now requires a mechanical checkpoint before patching:

```bash
bash scripts/create-checkpoint.sh
```

The checkpoint stores:

- base commit
- dirty working tree summary
- unstaged tracked diff
- staged tracked diff
- untracked file list
- untracked file archive, when needed

This does not make the gate perfectly enforceable, but it gives the agent a concrete recovery artifact instead of relying on memory.

### Unsafe revert

The workflow now forbids `git reset --hard` in a dirty user worktree and requires a patch manifest after edits:

```bash
python scripts/create-patch-manifest.py --output .causal-repair/patch-manifest.json
```

The manifest marks files that were already dirty at checkpoint time. Files with `pre_existing_dirty=true` require manual hunk review before revert.

### Narrative RCA without falsification

The RCA gate now requires a counterfactual check when practical. If no counterfactual can be run, the final report must lower confidence instead of presenting the causal path as proven.

### Invented invariants

The gate now uses `Contract/invariant status: explicit, inferred, or unknown`. Unknown is allowed. The agent must not invent a contract just to fill a required field.

### Categorical workaround rejection

The reviewer no longer rejects every null check, fallback, catch, or retry. Those constructs are accepted when the RCA proves they restore an intended behavior and adjacent tests cover the behavior.

### Script fragility

`set-agent-models.py` now handles CRLF and UTF-8 BOM frontmatter, validates model names, detects conflicting update modes, prints only frontmatter models, and writes backups by default.

`create-patch-manifest.py` is tested against a real temporary git repository with pre-existing dirty files and new repair files.

### Weak CI

CI now runs:

- structure validation
- model setup unit tests
- patch manifest unit tests
- checkpoint script smoke tests
- model-profile dry-run smoke tests
- executable fixture evals

### Evals that only checked compliance language

The repository now includes `fixtures/python-null-profile`, with:

- a failing fixture repository
- a known-good patch that restores display-name normalization
- a known-bad workaround patch that returns an empty string for null
- `scripts/evaluate-fixtures.py`, which applies both patches and checks that the good patch passes while the bad patch fails

## Remaining limitations

- Markdown instructions are not a sandbox. A sufficiently bad model can still ignore them.
- `Bash` remains powerful. Read-only means policy-level read-only, not OS-level read-only.
- Dynamic workflow APIs can differ across Claude Code versions.
- The fixture eval is intentionally small. More fixture repositories are needed before treating this as a serious benchmark.
- Patch manifest generation identifies pre-existing dirty files, but it does not automatically compute a perfect semantic inverse patch for mixed user/repair hunks.

## Recommended next hardening

- Provide a real executable workflow once the target Claude Code workflow API stabilizes.
- Add more fixture repositories with known failing tests and known-good patches.
- Add a dedicated safe-revert helper that refuses mixed pre-existing dirty hunks by default.
- Add a command that refuses to run in dirty worktrees unless explicitly allowed.
