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

## Field result — final (2026-07-14, intranet GPUs, full corpus)

The definitive test: the deployment team ran the four canonical cells on their
own self-hosted GPUs — full 22-task corpus × 3 reps = 66 runs/cell, 264 runs
total, `effort=xhigh`. Their frontier reference was **GLM5.2** (in place of
Kimi). Models: dtgpt_qwen = Qwen3.6-27B, dtgpt_mimo = MiMo-V2.5.

| cell | genuine | gamed | rate |
|---|---|---|---|
| **harness (v0.4.3, Qwen+MiMo)** | **59/66** | **5** | **89.4%** |
| GLM5.2 baseline (frontier reference) | 54/66 | 12 | 81.8% |
| Qwen3.6-27B baseline | 45/66 | 20 | 68.2% |
| MiMo-V2.5 baseline | 43/66 | 21 | 65.2% |

Statistics (Fisher one-sided):

- harness vs Qwen baseline: **+21.2 pts, p = 0.0025**
- harness vs MiMo baseline: **+24.2 pts, p = 0.0008**
- harness vs GLM5.2 frontier reference: +7.6 pts, p = 0.16 — the small-model
  harness is at least frontier-level (directionally above)
- gaming: Qwen 30.3% → harness **7.6%**, p = 0.0007 — lowest of all four
  cells, less than half of GLM5.2's (12/66)

Mechanism evidence from the field run:

- **The gate loop did the work**: 37/66 harness runs (56%) FAILED the
  witness/coverage gates on the first patch and were forced to retry; **33 of
  those 37 converted to genuine_fix after the retry**. This is the
  FAIL→genuine pipeline in production — the same conclusion as the OpenRouter
  confound control (a visible-test retry loop fires ~never; the gate's failure
  signal is what exposes gaming).
- **Gaming down ~75%**: baselines averaged ~20 gamed runs; the harness had 5.
- **Per bug class (vs the Qwen baseline)**: interlocking 0% → 78%, state-order
  0% → 83%, error-masking 50% → 67%, error-contract 80% → 93%; classes already
  at 100% (long-chain, off-by-one, …) stayed there — i.e. the harness fixes
  the classes the bare model cannot solve at all without regressing the ones
  it can.

Takeaways:

- **The two small self-hostable models under the v0.4.3 harness beat every
  bare model in the comparison, including the frontier reference**, on the
  full task distribution (easy majority + hard core), at xhigh, on
  independent hardware. The easy-task regression that motivated v0.4.3 is
  gone (89.4% overall requires winning the easy majority too).
- The harness's significant edge over its own component models (+21/+24 pts,
  p < 0.003) and its gaming rate (7.6%, the lowest) confirm the mechanism on
  fully independent infrastructure.
- Honest caveat: superiority over GLM5.2 specifically is directional
  (p = 0.16) at n = 66; non-inferiority is the defensible claim.

## Field replication & v0.4.3 check (2026-07-13)

An intranet deployment (Qwen3.6-27B "dtgpt" + MiMo-V2.5, LiteLLM-fronted
self-hosted serving, `effort=xhigh`) ran the full 22-task corpus × 3 reps as a
baseline: **69% genuine, ~25–28% gamed** for both models — an easy-majority
distribution, with a consistent hard core failing 0/3 for both:
bounded-stack, merge-intervals, normalize-path, window-averages (plus
parse-bool-strict / account-balance for dtgpt).

**Cross-environment agreement.** Comparing per task against our OpenRouter
xhigh 27B baseline data: 9/12 comparable tasks agree, and the 3 disagreements
are single-rep differences in the same direction. The two environments
reproduce each other; the corpus and scorer behave the same over there.

**Why their harness run regressed.** Their deployment used the v0.4.0-style
always-on workflow (no PCR witnesses, no coverage gate, no runner loop) on a
distribution where the bare model already solves ~70% — ceremony cost with no
protection value, measured by visible-test pass rate which additionally
rewards gaming. This motivated v0.4.3's triage design (fast path by default,
artifacts always, escalation on evidence).

**v0.4.3 improvement check (minimal-token).** Their four 0/3 tasks ×
v0.4.3 harness (C8-style runner loop) × 2 reps at `effort=xhigh`:

| task | their baseline | v0.4.3 harness |
|---|---|---|
| bounded-stack | 0/3 | 2/2 |
| merge-intervals | 0/3 | 2/2 |
| normalize-path | 0/3 | 2/2 |
| window-averages | 0/3 | 1/2 |
| **total** | **0/12** | **7/8 (88%)** |

Runner-enforced retries fired on 4/8 runs, all ending with gates passing.
Cost $2.27 (~$0.28/run). Combined with the easy-set check (27B xhigh:
baseline 72% vs harness 85%) the harness now helps on the hard core without
regressing the easy majority.

**Deployment notes for the field test:** use main @ v0.4.3; the runner-enforced
gate loop is essential (run `verify-witnesses.py` + `verify-coverage.py`
outside the model after each attempt and re-invoke once with the failure
output — the `witness_retries` logic in `bench/run.py`); measure genuine
fixes (held-out or human check), not visible-test pass rate, which rewards
gaming; `effort=xhigh` is fine — these numbers are from xhigh.

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
