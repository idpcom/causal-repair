# Qwen-only profile

Use this when all Claude Code traffic should go to Qwen3-Coder through the DashScope Claude Code proxy.

```bash
export ANTHROPIC_BASE_URL="https://dashscope-intl.aliyuncs.com/api/v2/apps/claude-code-proxy"
# Set your provider auth token in your shell before starting Claude Code.
export CLAUDE_CODE_SUBAGENT_MODEL="qwen3-coder-plus"
claude --model qwen3-coder-plus --plugin-dir .
```

This profile is simple, but it does not mix Qwen and MiMo. For mixed routing, use a router profile.
