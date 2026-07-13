# Qwen plus MiMo router profile

Use this when Qwen and MiMo should be used by different Causal Repair subagents.

You need a Claude-compatible or Anthropic-compatible router that accepts multiple model IDs and routes them to the right backend.

```bash
export ANTHROPIC_BASE_URL="http://127.0.0.1:3456"
# Set provider or router authentication in your shell if your router requires it.
```

Then update the plugin agent files:

```bash
python scripts/set-agent-models.py \
  --investigator qwen3-coder-plus \
  --judge xiaomi/mimo-v2.5-pro \
  --reviewer qwen3-coder-plus \
  --verifier qwen3-coder-plus
```

Start Claude Code:

```bash
claude --model qwen3-coder-plus --plugin-dir .
```

Recommended split:

```text
Qwen -> root-cause-investigator, workaround-reviewer, repair-verifier
MiMo -> root-cause-judge
```
