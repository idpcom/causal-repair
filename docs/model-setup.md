# Model Setup

Causal Repair assumes your Claude Code provider, proxy, or router is already configured.

For normal use, you only need to change model names.

## The only thing this plugin controls

Causal Repair controls subagent model routing through the `model:` field in each agent file:

```text
agents/root-cause-investigator.md
agents/root-cause-judge.md
agents/workaround-reviewer.md
agents/repair-verifier.md
```

Claude Code supports a `model` frontmatter field for subagents. It can be `sonnet`, `opus`, `haiku`, `fable`, a full model ID, or `inherit`.

## Current default routing

```text
root-cause-investigator -> haiku
root-cause-judge        -> sonnet
workaround-reviewer     -> haiku
repair-verifier         -> haiku
main patch author       -> your Claude Code session model
```

## Fastest way: apply a profile

Use this if your environment already recognizes `qwen3-coder-plus` and `xiaomi/mimo-v2.5-pro`.

```bash
python scripts/set-agent-models.py --profile qwen-mimo
```

This writes:

```text
root-cause-investigator -> qwen3-coder-plus
root-cause-judge        -> xiaomi/mimo-v2.5-pro
workaround-reviewer     -> qwen3-coder-plus
repair-verifier         -> qwen3-coder-plus
```

Then reload Claude Code plugins:

```text
/reload-plugins
```

## Other bundled profiles

List profiles:

```bash
python scripts/set-agent-models.py --list-profiles
```

Apply Qwen to every Causal Repair subagent:

```bash
python scripts/set-agent-models.py --profile qwen-only
```

Restore the original Claude defaults:

```bash
python scripts/set-agent-models.py --profile default
```

Use stronger Claude routing:

```bash
python scripts/set-agent-models.py --profile safe-claude
```

## Custom model names

Use the exact model names registered in your environment:

```bash
python scripts/set-agent-models.py \
  --investigator qwen3-coder-plus \
  --judge xiaomi/mimo-v2.5-pro \
  --reviewer qwen3-coder-plus \
  --verifier qwen3-coder-plus
```

Set one model for all Causal Repair subagents:

```bash
python scripts/set-agent-models.py --all qwen3-coder-plus
```

Print current models:

```bash
python scripts/set-agent-models.py --print
```

Preview changes:

```bash
python scripts/set-agent-models.py --profile qwen-mimo --dry-run
```

## Manual edit

You can also edit the files directly.

Example:

```yaml
model: qwen3-coder-plus
```

or:

```yaml
model: xiaomi/mimo-v2.5-pro
```

After editing installed plugin files, run:

```text
/reload-plugins
```

## Main patch model

The actual patch author is the main Claude Code session unless the task is delegated to a specific subagent. Choose it when you start Claude Code or with `/model`.

Examples:

```bash
claude --model qwen3-coder-plus --plugin-dir .
```

or inside Claude Code:

```text
/model qwen3-coder-plus
```

## Global override

Claude Code can also force every subagent to one model through `CLAUDE_CODE_SUBAGENT_MODEL`.

```bash
export CLAUDE_CODE_SUBAGENT_MODEL="qwen3-coder-plus"
```

Use this only for quick tests. It overrides per-agent `model:` fields, so it prevents the Qwen/MiMo split.

To return to the plugin's per-agent routing:

```bash
unset CLAUDE_CODE_SUBAGENT_MODEL
```

## Recommended mapping

For your Qwen/MiMo setup:

```text
root-cause-investigator -> qwen3-coder-plus
root-cause-judge        -> xiaomi/mimo-v2.5-pro
workaround-reviewer     -> qwen3-coder-plus
repair-verifier         -> qwen3-coder-plus
main patch author       -> qwen3-coder-plus or your preferred coding model
```

Rationale:

- Qwen handles codebase search, repair workflow planning, diff sniffing, and test summaries.
- MiMo handles the reasoning-heavy RCA judgment step.
- The main model writes the actual patch after the RCA gate passes.

## If a model is not applied

1. Run:

```bash
python scripts/set-agent-models.py --print
```

2. Check that `CLAUDE_CODE_SUBAGENT_MODEL` is not overriding the files:

```bash
echo "$CLAUDE_CODE_SUBAGENT_MODEL"
```

3. Confirm the model name is exactly the name registered in your existing Claude Code environment.

4. Reload plugins:

```text
/reload-plugins
```
