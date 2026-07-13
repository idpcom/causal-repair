#!/usr/bin/env bash
set -euo pipefail

checkpoint_root="${1:-.causal-repair/checkpoints}"
repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
base_commit="$(git rev-parse HEAD)"
checkpoint_dir="$checkpoint_root/$stamp-$base_commit"
mkdir -p "$checkpoint_dir"

git rev-parse --show-toplevel > "$checkpoint_dir/repo-root.txt"
git rev-parse HEAD > "$checkpoint_dir/base-commit.txt"
git status --short > "$checkpoint_dir/status-short.txt"
git diff --binary > "$checkpoint_dir/pre-existing.diff"
git diff --cached --binary > "$checkpoint_dir/pre-existing-staged.diff"
git ls-files --others --exclude-standard -z > "$checkpoint_dir/pre-existing-untracked.zlist"

if [ -s "$checkpoint_dir/pre-existing-untracked.zlist" ]; then
  tar --null -czf "$checkpoint_dir/pre-existing-untracked.tar.gz" \
    --files-from "$checkpoint_dir/pre-existing-untracked.zlist"
fi

cat > "$checkpoint_dir/README.txt" <<EOF
Causal Repair checkpoint

Base commit: $base_commit
Created UTC: $stamp

Files:
- status-short.txt: dirty working tree summary before repair
- pre-existing.diff: unstaged tracked changes before repair
- pre-existing-staged.diff: staged tracked changes before repair
- pre-existing-untracked.zlist: NUL-delimited untracked file list before repair
- pre-existing-untracked.tar.gz: untracked file contents, if any existed

Do not use git reset --hard in a dirty user worktree. Use this checkpoint to
separate pre-existing user changes from the causal-repair patch.
EOF

printf '%s\n' "$checkpoint_dir"
