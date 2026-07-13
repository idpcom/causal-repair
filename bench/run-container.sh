#!/usr/bin/env bash
# Build the sandbox image and run the benchmark inside it.
#
# Usage:
#   OPENROUTER_API_KEY=sk-or-... bench/run-container.sh [args for bench/run.py]
#
# Examples:
#   OPENROUTER_API_KEY=... bench/run-container.sh --smoke           # router smoke (gate 1)
#   OPENROUTER_API_KEY=... bench/run-container.sh --tasks python-null-profile --reps 1
#   OPENROUTER_API_KEY=... bench/run-container.sh                   # full matrix
#
# Results land on the host in bench/results/ (bind-mounted).
set -euo pipefail

: "${OPENROUTER_API_KEY:?export OPENROUTER_API_KEY first}"

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IMAGE="causal-repair-bench:latest"

echo "[run-container] building ${IMAGE}"
docker build -f "${REPO_ROOT}/bench/Dockerfile" -t "${IMAGE}" "${REPO_ROOT}"

mkdir -p "${REPO_ROOT}/bench/results"

# --smoke is handled here (one tiny call per model through the router) rather
# than in run.py, so it can gate the expensive matrix.
if [ "${1:-}" = "--smoke" ]; then
    echo "[run-container] router smoke test"
    docker run --rm \
        -e OPENROUTER_API_KEY \
        --entrypoint bash \
        "${IMAGE}" /work/bench/smoke.sh
    exit $?
fi

# Network is left at Docker default (egress needed for OpenRouter). To lock it
# down to OpenRouter only, run behind an egress proxy / firewall on the host.
docker run --rm \
    -e OPENROUTER_API_KEY \
    -e LITELLM_MASTER_KEY \
    -v "${REPO_ROOT}/bench/results:/work/bench/results" \
    "${IMAGE}" "$@"
