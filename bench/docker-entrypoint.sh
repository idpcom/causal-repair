#!/usr/bin/env bash
# Start the router, point Claude Code at it, then run the benchmark.
# All container arguments are forwarded to bench/run.py.
set -euo pipefail

source /work/bench/start-router.sh
trap 'kill ${ROUTER_PID} 2>/dev/null || true' EXIT

cd /work
echo "[entrypoint] running: python3 bench/run.py $*"
exec python3 bench/run.py "$@"
