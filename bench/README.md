# Causal Repair Benchmark

Measures whether the causal-repair harness lets **low-weight self-hostable
models (Qwen3.6-35B-A3B + MiMo-V2.5)** reach the bug-fixing quality of an
unharnessed reference model (**Kimi K2.7**), for an intranet where large hosted
LLMs are unavailable.

The plugin ships no way to run a model against a task and score its fix, so this
directory builds that: a task corpus, a runner that drives Claude Code (baseline
or through the harness) via OpenRouter inside a Docker sandbox, a deterministic
scorer, and an aggregator.

## The core question

Does the Qwen+MiMo **harness** (C4) reach the **Kimi baseline** (C3), and does it
beat the small-model baselines (C1/C2)?

| Cell | Config | Role |
|------|--------|------|
| C1 | Qwen alone, no harness | small-model baseline |
| C2 | MiMo alone, no harness | small-model baseline |
| C3 | Kimi alone, no harness | **reference bar (target)** |
| C4 | Qwen+MiMo through causal-repair, hooks enforced | **treatment** |

Models (OpenRouter ids, in `config.json`; `:floor` = cheapest provider):
`qwen/qwen3.6-35b-a3b`, `xiaomi/mimo-v2.5`, `moonshotai/kimi-k2.7-code`.
C4 routing: patch-author + judge = Qwen (best coder); investigator/reviewer/
verifier = MiMo (best agentic, cheapest output).

## How a fix is scored (`score.py`)

Each task has a **visible** failing test (shown to the model) and a **held-out**
contract test (never shown), plus task-specific `workaround_patterns.json`.

- `visible_pass` — the given test now passes
- `heldout_pass` — the hidden contract holds (catches symptom-only fixes)
- `workaround` — the diff matches a workaround regex

Label: `genuine_fix` (visible ∧ heldout ∧ no workaround) · `gamed` (visible but
heldout fails or workaround) · `broken` (visible still fails) · `apply_fail`
(no change). Harness plumbing (`.causal-repair/`, `.claude/`, `scripts/`) is
excluded from the diff scan. Held-out is copied in only *after* the model run.

## Task corpus (`tasks/`)

9 small single-file stdlib tasks across distinct workaround archetypes:
null-contract, off-by-one, error-masking (×2), test-overfit (×2), state-leak,
symptom-conditional, normalization. Extend by adding a `tasks/<id>/` with
`repo/`, `heldout/`, `workaround_patterns.json`, `meta.json`, and `reference/
{good,workaround}/` overlays.

## Verification gates (run in order)

**Gate A — corpus is well-formed (zero cost, offline):**
```bash
python3 bench/selftest.py
```
Asserts, per task: base fails the visible test, `reference/good` → `genuine_fix`,
`reference/workaround` → not `genuine_fix`. This proves each task actually
discriminates a real fix from a workaround.

**Gate B — pipeline works (zero cost, offline):** the `fake` engine simulates a
model by overlaying a reference, exercising scratch setup, harness scaffold,
diff capture, scoring, and recording without any LLM:
```bash
python3 bench/run.py --engine fake --fake-spec good        # -> all genuine_fix
python3 bench/run.py --engine fake --fake-spec workaround   # -> all gamed
```

**Gate C — router + tool-use work (small cost):** before the matrix, confirm each
model answers *and* uses tools through the router:
```bash
OPENROUTER_API_KEY=sk-or-... bench/run-container.sh --smoke
```
If tool-use fails here, the harness cannot run — fix routing first.

## Running the real benchmark

Everything runs in the Docker sandbox; results land on the host in
`bench/results/`.

```bash
export OPENROUTER_API_KEY=sk-or-...

# cheap first: validate one task end-to-end on the two cheap cells
bench/run-container.sh --cells C1-qwen-baseline C2-mimo-baseline \
    --tasks python-null-profile --reps 1

# then the full matrix (all cells, all tasks, reps from config.json)
bench/run-container.sh

# aggregate
python3 bench/report.py --by-bug-class
```

`run.py` flags: `--cells`, `--tasks`, `--reps`, `--engine {claude,fake}`,
`--max-turns`. Config knobs (`config.json`): `models`, `reps`, `max_tokens`,
`run_timeout_seconds`, and per-cell `agent_models`.

## Cost

All three models are cheap; MiMo is the cheapest ($0.105/$0.28 per 1M). Kimi
(C3, one cell) and the multi-agent C4 dominate spend. Full matrix
(9 tasks × 4 cells × 3 reps) is roughly **$3–5**. Keep it down with `:floor`
routing, tight `max_tokens`, and fewer `--reps`. `report.py` prints total spend.

## Architecture notes

- Claude Code speaks the Anthropic Messages API; OpenRouter is OpenAI-shaped, so
  **LiteLLM** (`router/litellm.config.yaml`) fronts OpenRouter with an Anthropic
  `/v1/messages` endpoint and routes on the request `model` field — this is what
  preserves per-agent routing (investigator=MiMo vs judge=Qwen). Do **not** set
  `CLAUDE_CODE_SUBAGENT_MODEL`; it would collapse the split.
- The harness cell copies the plugin, pins each subagent's model with
  `scripts/set-agent-models.py`, installs the bundled `scripts/` and a
  PreToolUse hook (absolute path) into the scratch repo, and invokes
  `/causal-repair:cr`. The hook enforces checkpoint + valid RCA gate before edits.
- The benchmark uses OpenRouter as a stand-in for the *same weights* the 2-GPU
  intranet deployment self-hosts, so results transfer.
