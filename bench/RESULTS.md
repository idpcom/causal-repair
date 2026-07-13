# Benchmark results

Question: in a closed intranet where large hosted LLMs are unavailable, can the
causal-repair harness lift low-weight self-hostable models (Qwen3.6-35B-A3B +
MiMo-V2.5) to the bug-fixing quality of an unharnessed Kimi K2.6?

Setup: all runs go through OpenRouter behind a LiteLLM (Anthropic-compatible)
router in the Docker sandbox. Raw per-run data is in `bench/results/matrix.jsonl`
(gitignored). Protocol and task-adoption rule were pre-registered in
`bench/PREREG.md` before any measurement.

**Metric — genuine-fix**: the patch passes the visible test AND a hidden
held-out contract test AND matches no task-specific workaround pattern.
**gamed** = passes the visible test but violates the contract (`bench/score.py`).

**Cells** (Qwen+MiMo harness routing throughout; Qwen authors patches/judges,
MiMo investigates/reviews/verifies):

| cell | what it is |
|---|---|
| C1 / C2 | Qwen / MiMo alone (baseline) |
| C3 | Kimi K2.6 alone — the reference bar |
| C5 | harness v0.4.0: machine-checked contract-clause gate |
| C6 | prompt-only ablation: same guidance text, hooks OFF |
| C7 | harness v0.4.1: per-clause proof-carrying witnesses (fail-on-base + mutation) |
| C8 | harness v0.4.2: C7 + change-surface coverage gate + CI-style runner-enforced retry loop |
| C9 | confound control: Qwen + equal-budget retry loop on visible-test failure, no gate |

Corpus: the reported comparison runs on the 6 pre-registered "hard" tasks where
the small baselines game (adopted by the pre-registered rule: baseline genuine
≤ 50% in screening).

## Main result — full ladder (6 adopted tasks)

| cell | mechanism | n | genuine | 95% CI |
|---|---|---|---|---|
| C9 Qwen + retry (no gate) | retry only | 18 | 6% | [1, 26] |
| C1 Qwen baseline | — | 13 | 15% | [4, 42] |
| C2 MiMo baseline | — | 13 | 31% | [13, 58] |
| C6 prompt-only | guidance, no enforcement | 18 | 33% | [16, 56] |
| C5 harness v0.4.0 | contract-clause gate | 21 | 52% | [32, 72] |
| C7 harness v0.4.1 | per-clause witnesses | 18 | 67% | [44, 84] |
| **C8 harness v0.4.2** | coverage gate + runner loop | 18 | **78%** | [55, 91] |
| C3 Kimi K2.6 | reference bar | 21 | 71% | [50, 86] |

Monotone ladder: 6 → 15 → 31 → 33 → 52 → 67 → 78, with Kimi at 71.

- **The harness lifts Qwen+MiMo to / slightly past the unharnessed Kimi bar**
  (C8 78% vs Kimi 71%; diff +6 pts, task-cluster bootstrap 95% CI [−22, +44],
  Fisher p = 0.47 — indistinguishable). `window-averages`, which Kimi solves
  0/3, is 3/3 under C8.
- **Enforcement, not guidance, is the active ingredient.** The same workflow
  text delivered prompt-only with no hook (C6) sits at baseline level (33%);
  the enforced gate (C5) adds it back.
- Per-step increments (C5→C7→C8) are directional at this n (e.g. C8 vs C7
  +11 pts, p = 0.36); the ladder endpoints and the confound below carry the
  significance.

## Validation — is the effect real?

Red-team checks; the four biggest "we're fooling ourselves" threats are
eliminated.

1. **Not a workaround-regex artifact.** Relabeling every run behavior-only
   (visible ∧ held-out, ignoring the regexes) gives *identical* genuine counts
   for every cell. Gaming is detected by held-out behavior, not heuristics.

2. **The Kimi bar is not infra-handicapped.** On the adopted set Kimi's
   non-genuine runs are 6/6 real gaming, 0 infra failures. (Earlier Kimi
   timeouts were a wrong-provider bug, fixed by pinning the official Moonshot
   provider before these runs.)

3. **The scorer is not fooled (manual audit).** Sampled C8 genuine diffs are
   real, complete fixes (e.g. window-averages adds `k < 1 → ValueError` *and*
   fixes the off-by-one — the full contract Kimi missed). The one
   gamed-with-gates-ok run is a genuinely incomplete fix (LIFO + IndexError but
   not OverflowError); held-out correctly fails. Labels match reality.

4. **Not "just retrying / more compute" (confound control C9).** C9 = plain
   Qwen + an equal-budget outer loop that retries on *visible-test* failure, no
   gate.

   | cell | genuine | gamed | retry fired |
   |---|---|---|---|
   | Qwen baseline (C1) | 15% | 11 | — |
   | Qwen + visible-retry (C9) | 6% | 17 | **0/18** |
   | C8 (gate-driven loop) | 78% | 4 | ~half |

   The loop fires 0/18 for C9 because every gamed patch *passes* the visible
   test — a naive loop can't see the failure. C9 vs C1: p = 0.936 (retrying adds
   nothing). **C8 vs C9: +72 pts, p < 0.001.** The gain comes from the gate's
   failure signal (contract witnesses expose gaming the visible test hides), not
   from extra attempts.

Still open (magnitude/scope, not existence): run-to-run variance at higher n;
generalization to non-adopted and freshly authored tasks; per-step significance;
a second small-model family.

## Cost

Recorded per run (`engine.cost_est_usd` = token × OpenRouter price; authoritative
per-batch spend is the OpenRouter `/credits` delta). `$/genuine` = amortized
price of one real fix. Token estimate counts cached input at full price, so it
is a conservative upper bound.

| cell | runs | $/run | $/genuine | ~s/run |
|---|---|---|---|---|
| C1 Qwen baseline | 53 | 0.021 | 0.030 | 18 |
| C2 MiMo baseline | 53 | 0.016 | 0.022 | 48 |
| C3 Kimi K2.6 | 51 | 0.100 | 0.200 | 237 |
| C5 harness v0.4.0 | 27 | 0.132 | 0.210 | 149 |
| C6 prompt-only | 18 | 0.116 | 0.349 | 111 |
| C7 harness v0.4.1 | 18 | 0.143 | 0.215 | 173 |
| C8 harness v0.4.2 | 18 | 0.186 | 0.239 | 96 |
| C9 Qwen + retry | 18 | 0.020 | 0.354 | 12 |

- **`$/genuine` is the bottom line**: C8 ($0.239) ≈ Kimi ($0.200) per successful
  fix — Kimi-level quality at roughly Kimi-level amortized cost, and far cheaper
  self-hosted (electricity vs API). C9 and C6 are the worst buys — you pay for
  many failed runs.
- C8 adds ~$0.04/run over C7 for the coverage gate + retries.

## Operational findings

- **Kimi routing:** only the official "Moonshot AI" OpenRouter provider executes
  Kimi file-edit tool calls; third-party hosts loop without editing. Pinned via
  `provider.order` in `bench/router/litellm.config.yaml`.
- **Headless harness:** `claude -p` needs the natural-language workflow prompt +
  `--append-system-prompt-file SKILL.md` + absolute paths.
- **Cost accounting:** Claude Code's `total_cost_usd` misprices routed
  non-Anthropic models (~30× high); use token × price + the OpenRouter credits
  delta instead.
