# Hooks

Causal Repair can be strengthened with a Claude Code `PreToolUse` hook, but hook enforcement is intentionally opt-in.

Do not auto-register this hook from `.claude-plugin/plugin.json` for global skill installs. Claude Code runs hook commands from the active project context, so a relative command such as `python scripts/hooks/pre-tool-use.py` fails in projects that do not contain this repository. Use an absolute path in user or project settings when you want hook enforcement.

## What the hook blocks

`scripts/hooks/pre-tool-use.py` blocks:

- `Edit`, `MultiEdit`, `Write`, and `NotebookEdit` when no valid checkpoint exists
- those same write tools when `.causal-repair/rca-gate.json` is missing or invalid
- destructive `Bash` commands such as `git reset --hard`, `git clean -xdf`, and `rm -fr .`
- common write-like Bash commands before RCA by default, including `sed -i`, `tee`, `>`, `>>`, `mv`, `cp`, `rm`, `touch`, `truncate`, `git apply`, `apply_patch`, `patch`, `python -c`, `node -e`, `ruby -e`, `sh -c`, and `bash -c`

The hook allows edits under `.causal-repair/` so the agent can create `rca-gate.json`, checkpoint metadata, and patch manifests.

## Install

Hook enforcement is not registered automatically by the plugin manifest. Add it only where you want hard enforcement.

Use an absolute path to this repository's hook script. For example, on Windows global skill installs:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|MultiEdit|Write|NotebookEdit",
        "hooks": [
          {
            "type": "command",
            "command": "python C:/Users/dongpan.lim/.claude/skills/causal-repair/scripts/hooks/pre-tool-use.py"
          }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python C:/Users/dongpan.lim/.claude/skills/causal-repair/scripts/hooks/pre-tool-use.py"
          }
        ]
      }
    ]
  }
}
```

For a portable example, copy `examples/hooks/settings.example.json` and replace `YOUR_USER` or the full path with the actual install location.

If you install the hook into a project-level Claude Code settings file, every developer using that project needs the same absolute path or an equivalent local path. If you install it into user-level settings, it affects all Claude Code projects for that user.

If your Claude Code version uses a different matcher syntax, keep the same absolute command and adapt the matcher fields.

## Required files before patching

Before the first production edit, Causal Repair should create:

```text
.causal-repair/checkpoints/<timestamp>-<base-commit>/base-commit.txt
.causal-repair/checkpoints/<timestamp>-<base-commit>/status-short.txt
.causal-repair/rca-gate.json
```

The checkpoint must be a real checkpoint directory from `scripts/create-checkpoint.sh`; a bare `.causal-repair/pre-existing.diff` fallback is not accepted by the hook.

Create the checkpoint:

```bash
bash scripts/create-checkpoint.sh
```

Create or write the RCA gate:

```text
.causal-repair/rca-gate.json
```

Validate it:

```bash
python scripts/validate-rca-gate.py .causal-repair/rca-gate.json
```

Verify the recorded counterfactual command against its actual exit status:

```bash
python scripts/run-counterfactual.py .causal-repair/rca-gate.json
```

See:

```text
examples/rca-gate.example.json
```

## RCA gate strictness

The gate validator rejects empty ceremony fields. It requires:

- narrative fields with enough detail, not just `"x"`
- `contract_invariant_status` as `explicit`, `inferred`, or `unknown`
- `contract_clauses` as a non-empty list of `{clause, status, covered_by}` objects enumerating the documented contract of the code under repair (status: `broken`, `held`, or `at-risk`)
- `counterfactual_check` as an object with `command`, `result`, and `evidence`
- no `claude --bare` in causal-repair counterfactual commands, because `--bare` disables hooks/plugins required by this workflow
- `workaround_reject_rules` as a non-empty list
- `tests_to_run` with at least 2 commands, including the authored contract tests (`.causal-repair/contract-tests*`) — the visible reproduction alone is rejected
- `checkpoint` pointing to a real checkpoint directory with a 40-character base commit

`run-counterfactual.py` then executes `counterfactual_check.command` and checks that the exit status matches `counterfactual_check.result` (`pass` means exit 0, `failed` means non-zero, `incomplete` skips execution with an explicit skipped result).

## Strict Bash write mode

Strict Bash write blocking is enabled by default.

To disable it only while debugging the hook:

```bash
export CAUSAL_REPAIR_STRICT_BASH_WRITES=0
```

## Environment switches

```bash
export CAUSAL_REPAIR_REQUIRE_CHECKPOINT=1
export CAUSAL_REPAIR_REQUIRE_RCA=1
export CAUSAL_REPAIR_STRICT_BASH_WRITES=1
```

Set any of these to `0` only for debugging the hook itself.

## Limitations

- Hooks block Claude Code tool calls, not arbitrary OS-level writes outside Claude Code.
- Bash parsing is conservative, not a shell sandbox. Shell obfuscation can still beat regexes.
- Counterfactual execution verifies command exit status, not semantic truth.
- If you do not opt into hook settings, the plugin falls back to instruction-level guardrails.
- A malicious repository can still execute code when you run its tests. Use normal sandboxing for untrusted repositories.
