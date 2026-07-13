#!/usr/bin/env bash
# Sourced helper: start the LiteLLM router, wait for health, and export the
# Anthropic-compatible env that Claude Code needs. Sets ROUTER_PID for cleanup.
#
#   source bench/start-router.sh
#
# Requires OPENROUTER_API_KEY. Sets ANTHROPIC_BASE_URL / ANTHROPIC_API_KEY.

: "${OPENROUTER_API_KEY:?set OPENROUTER_API_KEY}"
export LITELLM_MASTER_KEY="${LITELLM_MASTER_KEY:-sk-bench-local}"
ROUTER_PORT="${ROUTER_PORT:-4000}"
_ROUTER_CFG="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/router/litellm.config.yaml"

echo "[router] starting LiteLLM on :${ROUTER_PORT}"
litellm --config "${_ROUTER_CFG}" --port "${ROUTER_PORT}" >/tmp/litellm.log 2>&1 &
ROUTER_PID=$!

for i in $(seq 1 60); do
    if curl -sf "http://127.0.0.1:${ROUTER_PORT}/health/liveliness" >/dev/null 2>&1 \
       || curl -sf "http://127.0.0.1:${ROUTER_PORT}/health" >/dev/null 2>&1; then
        echo "[router] up"
        break
    fi
    if ! kill -0 "${ROUTER_PID}" 2>/dev/null; then
        echo "[router] died; log:"; cat /tmp/litellm.log; return 1 2>/dev/null || exit 1
    fi
    sleep 2
    [ "$i" -eq 60 ] && { echo "[router] never came up"; cat /tmp/litellm.log; return 1 2>/dev/null || exit 1; }
done

export ANTHROPIC_BASE_URL="http://127.0.0.1:${ROUTER_PORT}"
export ANTHROPIC_API_KEY="${LITELLM_MASTER_KEY}"
export ANTHROPIC_AUTH_TOKEN="${LITELLM_MASTER_KEY}"
# Never set CLAUDE_CODE_SUBAGENT_MODEL here — it collapses per-agent routing.
