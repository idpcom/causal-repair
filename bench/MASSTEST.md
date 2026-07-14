# MASS TEST protocol

Goal: harden the field result (harness 89.4% vs GLM5.2 81.8% on 22 tasks × 3)
with (a) more statistical power, (b) an external public corpus, and (c) the
ablations that bound the claims honestly. Designed for the intranet GPU rig;
every cell/config below also runs on OpenRouter via `bench/run-container.sh`.

## Cells

Canonical (already measured in the field):

| cell | what |
|---|---|
| `qwen-baseline` / `mimo-baseline` | bare small models |
| `glm-baseline` (or `kimi-baseline`) | bare frontier reference |
| `harness` | v0.4.3 full harness, Qwen+MiMo |

Ablations (new — bound the claims):

| cell | question it answers |
|---|---|
| `harness-glm` (GLM in every role) | Does the harness lift the frontier too? Verifier literature predicts yes — this bounds "small beats frontier" to "small+harness ≥ bare frontier", and measures the ceiling. |
| `harness-qwen-only` | Does MiMo's agentic role matter, or is one small model enough? |
| `harness-mimo-only` | Symmetric: does Qwen's patch-authoring matter? |

## Corpora

1. **Internal (pre-registered)**: `bench/tasks/` — 22 tasks, selftest 22/22.
   Authored by us; zero contamination; adoption rule pre-registered in
   `PREREG.md`.
2. **External (public)**: `bench/tasks-quixbugs/` — 19 tasks converted from
   QuixBugs (MIT) by `bench/import-quixbugs.py`, selftest 19/19. Held-out =
   the full official test set per program; visible = the first fast-failing
   case; workaround reference = auto-generated hardcode of the visible input.
   **Contamination note**: QuixBugs is public and likely memorized — that
   inflates *baselines*, biasing AGAINST the harness, so it is a conservative
   external-validity check. Run with `--tasks-dir bench/tasks-quixbugs`.

## Sizing (power)

- Field pilot: harness vs GLM +7.6 pts at n = 66/cell → p = 0.16. To separate
  ~89% vs ~82% at α = .05, power .8 you need roughly **n ≈ 300/cell**
  (proportions this close need large n). Practical plan: **reps 5 over both
  corpora (41 tasks → 205 runs/cell)** gives p ≈ .05-level resolution for
  gaps ≥ 8 pts; treat anything smaller as parity.
- For harness-vs-small-baseline gaps (~20 pts), reps 3 over 41 tasks is ample.

## Suggested execution order (cheapest signal first)

```bash
# 1. External corpus, canonical cells (does the field result transfer to a
#    public benchmark?)
bench/run-container.sh --cells qwen-baseline mimo-baseline glm-baseline harness \
    --tasks-dir bench/tasks-quixbugs --reps 3 --concurrency 4 --effort xhigh \
    --out bench/results/mass.jsonl --workspace bench/results/mass-runs

# 2. Ablations on the internal corpus (bound the mechanism)
bench/run-container.sh --cells harness-glm harness-qwen-only harness-mimo-only \
    --reps 3 --concurrency 4 --effort xhigh \
    --out bench/results/mass.jsonl --workspace bench/results/mass-runs

# 3. Power top-up: canonical cells, both corpora, to reps 5
#    (resume skips everything already recorded in mass.jsonl)
bench/run-container.sh --cells qwen-baseline mimo-baseline glm-baseline harness \
    --reps 5 --concurrency 4 --effort xhigh \
    --out bench/results/mass.jsonl --workspace bench/results/mass-runs
bench/run-container.sh --cells qwen-baseline mimo-baseline glm-baseline harness \
    --tasks-dir bench/tasks-quixbugs --reps 5 --concurrency 4 --effort xhigh \
    --out bench/results/mass.jsonl --workspace bench/results/mass-runs
```

All runs append to one file with resume-by-(cell, task, rep); analysis via
`python3 bench/report.py --results bench/results/mass.jsonl --by-bug-class`.

## Pre-stated predictions (so results can't be re-narrated)

1. External corpus: harness > small baselines by a smaller margin than
   internally (contamination lifts baselines); gaming rate still lowest for
   the harness.
2. `harness-glm` ≥ `harness` ≥ `glm-baseline` — the harness lifts the frontier
   too; if `harness` > `harness-glm`, that is a surprising and publishable
   inversion.
3. `harness-qwen-only` and `harness-mimo-only` land between their bare
   baseline and the mixed harness; if either matches the mixed harness, the
   dual-model routing is not load-bearing.

## Reporting

- Per corpus AND pooled; never pool silently.
- Wilson CIs + pairwise Fisher/bootstrap (report.py) + per-bug-class table.
- Record the retry-loop conversion stats (gate-FAIL → genuine) — the
  mechanism metric that the field run confirmed (37/66 → 33 conversions).
