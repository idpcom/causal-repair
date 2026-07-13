# Causal Repair benchmark sandbox.
#
# Bundles: node + Claude Code CLI, python + git, and a LiteLLM router that
# fronts OpenRouter with an Anthropic-compatible API. No secrets are baked in;
# OPENROUTER_API_KEY is injected at `docker run` time.
FROM node:20-slim

# System deps: python, git, curl (health check), build tools for some pip wheels.
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-pip python3-venv git curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Claude Code CLI.
RUN npm install -g @anthropic-ai/claude-code

# Router. LiteLLM exposes an Anthropic /v1/messages endpoint in front of OpenRouter.
RUN pip3 install --no-cache-dir --break-system-packages "litellm[proxy]"

# Run as the image's existing non-root user (node, uid 1000).
WORKDIR /work
COPY --chown=node:node . /work
USER node
ENV HOME=/home/node

# The router listens here; entrypoint points Claude Code at it.
ENV ROUTER_PORT=4000
EXPOSE 4000

ENTRYPOINT ["bash", "/work/bench/docker-entrypoint.sh"]
# Default: run the full matrix. Override with e.g. `--engine fake` or a subset.
CMD []
