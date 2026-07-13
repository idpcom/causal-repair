#!/usr/bin/env bash
# Verification gate 1: confirm each model answers AND can use tools through the
# router, before spending on the full matrix. Tool-use is the biggest external
# risk (OpenRouter models must honor Anthropic-shaped tool calls via LiteLLM).
set -uo pipefail

source /work/bench/start-router.sh
trap 'kill ${ROUTER_PID} 2>/dev/null || true' EXIT

MODELS=$(python3 -c "import json;print('\n'.join(json.load(open('/work/bench/config.json'))['models'].values()))")

fail=0
while IFS= read -r model; do
    [ -z "$model" ] && continue
    echo "=================================================="
    echo "MODEL: $model"

    # 1) plain completion
    if claude -p "Reply with exactly: OK" --model "$model" --output-format json \
         >/tmp/plain.json 2>/tmp/plain.err; then
        echo "  [plain]    ok"
    else
        echo "  [plain]    FAIL"; cat /tmp/plain.err; fail=1; continue
    fi

    # 2) tool-use probe: the model must actually create a file with its tools
    probe=$(mktemp -d)
    ( cd "$probe" && claude -p "Create a file named ok.txt containing the text hi. Use your tools." \
        --model "$model" --permission-mode bypassPermissions --max-turns 6 \
        >/tmp/tool.out 2>/tmp/tool.err )
    if [ -f "$probe/ok.txt" ]; then
        echo "  [tool-use] ok"
    else
        echo "  [tool-use] FAIL (no file created — model may not do Anthropic tool calls via the router)"
        tail -5 /tmp/tool.err 2>/dev/null
        fail=1
    fi
    rm -rf "$probe"
done <<< "$MODELS"

echo "=================================================="
if [ "$fail" -eq 0 ]; then
    echo "SMOKE PASS — all models answer and use tools. Safe to run the matrix."
else
    echo "SMOKE FAIL — fix routing/tool-use before running the matrix."
fi
exit $fail
