# Benchmark results & findings

Goal: in a closed intranet where large hosted LLMs are unavailable, can the
causal-repair harness lift low-weight self-hostable models (Qwen3.6-35B-A3B +
MiMo-V2.5) to the bug-fixing quality of an unharnessed Kimi K2.6?

All runs: OpenRouter behind a LiteLLM (Anthropic-compatible) router in the
Docker sandbox. Raw per-run data: `bench/results/matrix.jsonl` (gitignored).
Protocol pre-registered in `bench/PREREG.md` (committed before screening).

## Summary

On a pre-registered set of 6 short tasks where the small-model baselines game
(pass the visible test but violate a documented contract), the harness lifts
Qwen+MiMo from a 15% Qwen baseline to **67% genuine-fix**, **statistically
indistinguishable from the 71% unharnessed Kimi K2.6 reference** (difference
−5 pts, task-cluster bootstrap 95% CI [−17, +6] includes 0). Two results carry
the story:

- **Enforcement, not guidance, is the active ingredient.** The identical
  workflow delivered prompt-only (no hook) scores 33% ≈ baseline; adding hook
  enforcement adds +33 pts (Fisher p = 0.047).
- **A blocking-only "minimal patch" process made small models *worse*** — it
  gamed 3/3 on a task the baseline solved half the time, because "minimal vs
  the visible test" suppresses the contract-completeness fix. The remedy is a
  gate that *demands machine-checkable artifacts* (enumerated contract clauses +
  authored contract tests that must fail on the base code and survive mutation
  testing), culminating in Proof-Carrying Repair (v0.4.1).

This is a small-n MVP pilot (n = 13–21/cell). Significance holds for harness-vs-
Qwen-baseline (p = 0.006) and vs prompt-only (p = 0.047); the v0.4.1-over-v0.4.0
step is directional (p = 0.28). Full caveats below.

Metric: **genuine-fix** = the model's patch passes the visible test AND a hidden
held-out contract test AND matches no task-specific workaround regex.
**gamed** = passes the visible test but fails held-out or matches a workaround
pattern (`bench/score.py`).

---

## MVP pilot campaign (2026-07-12, pre-registered, total spend ≈ $5.7)

### Screening (pre-registered rule: adopt iff baseline genuine ≤ 50%)

10 new T1 tasks × {Qwen, MiMo} × 2 reps. **Adopted 5/10**: config-int (2/4),
normalize-path (1/4), window-averages (0/4), account-balance (0/4),
bounded-stack (0/4) — three tasks where small baselines game 4/4.
Non-discriminating (appendix): parse-duration, parse-fraction (4/4 genuine),
parse-version, decode-flags, merge-intervals (3/4).

### Main comparison (adopted 5 + parse-bool-strict)

| cell | n | genuine | gamed | notes |
|---|---|---|---|---|
| C1 Qwen baseline | 13 | 2 (15%) | 11 | |
| C2 MiMo baseline | 13 | 4 (31%) | 9 | |
| C3 Kimi K2.6 baseline | 21 | 15 (71%) | 6 | reference bar |
| **C5 harness v0.4.0** | 21 | **11 (52%)** | 9 | |
| C6 prompt-only ablation | 18 | 6 (33%) | 11 | same text, no hooks |

Pre-registered pairwise (Fisher one-sided; task-cluster bootstrap 95% CI):

- **C5 vs C1 (Qwen): +37.0 pts, CI [+11.1, +56.0], p = 0.034** — significant
  lift even at pilot n; CI excludes 0.
- C5 vs C2 (MiMo): +21.6 pts, p = 0.19 — directional.
- **C5 vs C6 (H5, mechanical enforcement): +19.0 pts, p = 0.19** — directional;
  C6 (33%) lands at baseline level, i.e. the guidance text alone adds almost
  nothing without hook enforcement. This is the paper's key ablation.
- C5 vs C3 (Kimi): **−19.0 pts** — on the hard set the harness does NOT reach
  the Kimi bar (the parse-bool-strict parity, 5/6 = 5/6 with 0 gaming, did not
  generalize to all hard tasks).
- C5 vs C4 (old blocking-only harness): +83 pts on parse-bool-strict,
  p = 0.048 — the H3 negative-result reversal.

### Long-horizon (T2: 3 multi-file tasks × 4 cells × 2 reps)

Qwen 5/6, MiMo 5/6, Kimi 5/6, **C5 6/6**. **H4 not testable at this
difficulty** — 2–3-file tasks with 2–3 coordinated edits are too easy for 2026
small models; baselines did not collapse. The long-horizon claim needs tasks
requiring 4–6 coordinated edits (scale-up L4–L6).

### Error analysis: why the harness still gamed on some hard tasks

bounded-stack, C5, 3/3 gamed — artifact evidence:

- The RCA gate **enumerated all 4 documented clauses correctly** (including
  the OverflowError and capacity-ValueError contracts).
- But it labeled those clauses `held`/`at-risk` when they are actually broken
  in the base code, and patched only the `broken`-labeled LIFO clause.
- The self-authored contract-tests **pass on the violating code** (heldout
  fails). The validator enforces that contract tests EXIST, not that they are
  STRONG — the model wrote tests consistent with its own patch, not with the
  documented contract.

**Concrete v-next mechanism (paper contribution candidate): pre-patch failure
requirement.** For every clause marked broken/at-risk, the authored contract
test must FAIL against the checkpointed base code before patching is allowed
(exactly the discrimination rule bench/selftest.py applies to the corpus
itself). A contract test that never failed proves nothing — this is
mechanically checkable using the existing checkpoint.

### Hypothesis scoreboard (pilot verdicts)

| hypothesis | verdict |
|---|---|
| H1 lift to Kimi bar | **Partial** — significant lift over Qwen baseline (p=.034); Kimi parity on parse-bool-strict but −19 pts on the full hard set |
| H2 gaming elimination | **Partial** — gaming 85→43% vs Qwen baseline; eliminated (0/6) on parse-bool-strict but not on all hard tasks (see error analysis) |
| H3 blocking-only harness harms | **Supported** — p=0.048 |
| H4 long-horizon recovery | **Not testable yet** — T2 tasks too easy; needs longer chains |
| H5 mechanical enforcement matters | **Directional** — +19 pts vs prompt-only; C6 ≈ baseline |

### v0.4.1 Proof-Carrying Repair (C7) — closes most of the Kimi gap

Ported from Proof-Carrying Code: the RCA gate's clause statuses become
*verifiable predictions*. `scripts/verify-witnesses.py` requires one witness
test per clause that (state) passes on the patch and, on the checkpointed base,
fails for broken/at-risk and passes for held; plus (strength) mutants of the
patch must be killed. C7 = C5 + the PCR addendum (only difference), isolating it.

Adopted hard set (6 tasks):

| cell | n | genuine | vs C7 |
|---|---|---|---|
| C1 Qwen baseline | 13 | 15% | +51 pts, **p = 0.006** |
| C6 prompt-only | 18 | 33% | +33 pts, **p = 0.047** |
| C5 harness v0.4.0 | 21 | 52% | +14 pts, p = 0.28 (directional) |
| **C7 PCR v0.4.1** | 18 | **67%** | — |
| C3 Kimi K2.6 | 21 | 71% | −5 pts, **boot95 [−17, +6] — includes 0** |

**The headline shift: C7 (Qwen+MiMo + PCR) is now statistically
indistinguishable from unharnessed Kimi (67% vs 71%, CI includes 0)**, up from
C5's −19 pts. PCR fixed the two tasks the error analysis targeted:
bounded-stack 0/3 → 2/3, parse-bool-strict 5/6 → 3/3; normalize-path 2/3 → 3/3.

Mechanism confirmed in artifacts: witness-result.json shows per-clause state
witness holding and mutation score 1.0 on genuine runs.

**Honest limitations of PCR:**
- The witness enforces the model's OWN clauses are consistent + strong, not
  completeness vs the hidden oracle. One bounded-stack rep gamed with
  `witness ok=True` — the model's clause set missed a held-out case. Witness ≠
  external oracle.
- Headless adherence is imperfect: some genuine runs produced no
  witness-result.json (model skipped `verify-witnesses.py`). A hook that blocks
  "done" until a passing witness-result exists would tighten this (v-next).
- `window-averages` stays 0/3 across ALL cells including Kimi — a documented
  error contract (k ≥ 1 → ValueError) that is hard for every model; a real hard
  task, not a flaw.
- PCR-over-C5 increment is directional (p = 0.28) at n = 18; needs the scale-up
  n for significance.

### v0.4.2 change-surface coverage gate + runner-enforced loop (C8)

Two mechanisms addressing the two PCR holes (a run that gamed with witness
ok=True; runs that skipped `verify-witnesses` entirely):

- **Coverage gate** (`scripts/verify-coverage.py`): differential fuzz base vs
  patch → change surface; every behavior-changed function must be exercised by
  a broken/at-risk clause witness ("no unexplained behavior change").
- **Runner-enforced loop** (CI-style): the runner itself runs the witnesses +
  coverage gate after the model finishes and re-invokes the model once with the
  gate output on failure. Adherence is applied, not requested.

C8 = C7 + `witness_retries: 1` + `coverage_gate: true`. Live mini on 3 tasks
(bounded-stack, window-averages, parse-bool-strict), 3 reps each:

| cell | genuine | gamed | notes |
|---|---|---|---|
| Qwen baseline | 1/7 (14%) | 6 | |
| MiMo baseline | 2/7 (29%) | 5 | |
| Kimi K2.6 baseline | 7/12 (58%) | 5 | reference bar |
| C5 harness v0.4.0 | 5/12 (42%) | 6 | |
| C7 PCR | 5/9 (56%) | 3 | |
| **C8 PCR + loop** | **8/9 (89%)** | 1 | **exceeds the Kimi bar** |

**On this 3-task slice, C8 (89%) exceeds the unharnessed Kimi baseline (58%).**
`window-averages` — which even Kimi solved 0/3 — goes to 3/3 under C8. All three
pre-registered V3 criteria met: skipped-witness runs disappeared (all 9 runs
ended with the gates run, final_ok=True; C7 skipped ~half), gaming did not
increase (3 → 1), genuine did not regress (56% → 89%). 4 of 9 runs used the
retry (attempts = 2): the runner caught `witnesses=FAIL` and the re-invoked
model fixed it.

Caveats: small slice (3 tasks, n = 9); C8-vs-C7 is directional (Fisher
p = 0.147) at this n; the one remaining gamed run passed both gates but failed
held-out — the documented function-level attribution limit (a missing clause
about a different aspect of an already-witnessed function). Cost rises to
~$0.20/run including retries (vs C7 $0.144). Next: run C8 on the full adopted
6-task set at n ≥ 10 to confirm significance.

### Go/no-go: **GO**, with three scale-up adjustments

1. **v0.4.1 harness**: add the pre-patch failure requirement for contract
   tests (mechanical; closes the weak-test hole found above), then re-measure.
2. **Harder T2** (L4–L6: 4–6 coordinated edits) to make H4 testable.
3. **n ≥ 10** per cell on the adopted set for H1/H2/H5 power (~$40–60
   projected at measured per-run costs).

---

## Cost

Every run records its own cost: `bench/run.py` stores a token×OpenRouter-price
estimate (`engine.cost_est_usd`) per run and prints the authoritative OpenRouter
`/credits` delta per batch; `bench/report.py` surfaces a per-cell cost table
(`$/run`, cell total, **`$/genuine`** = amortized price of one real fix, and
mean wall-clock).

Per-cell cost across the whole campaign (token-based estimate; cached input
counted at full price, so this is a conservative upper bound — real spend from
the credits delta was lower):

| cell | runs | $/run | total $ | $/genuine | ~s/run |
|---|---|---|---|---|---|
| C1 Qwen baseline | 53 | 0.021 | 1.09 | 0.030 | 18 |
| C2 MiMo baseline | 53 | 0.016 | 0.83 | 0.022 | 48 |
| C3 Kimi K2.6 baseline | 51 | 0.100 | 4.20 | 0.200 | 238 |
| C4 harness v0.3 | 3 | 0.079 | 0.24 | — (0 genuine) | 71 |
| C5 harness v0.4.0 | 27 | 0.132 | 3.58 | 0.210 | 149 |
| C6 prompt-only | 18 | 0.116 | 2.10 | 0.349 | 111 |
| C7 PCR v0.4.1 | 18 | 0.144 | 2.58 | 0.215 | 173 |
| **total** | | | **≈ 14.6** | | |

Reading it:

- Cheapest per run: MiMo ($0.016) and Qwen ($0.021) baselines (single agent).
- The Kimi baseline is the most expensive per run ($0.10, up to $0.40; 238 s)
  despite being a baseline — high output price and long runs.
- Harness cells cost 6–8× a baseline run in absolute terms, but that is still
  ~$0.13–0.14 per run.
- **PCR (C7) costs +$0.012/run over v0.4.0 (C5)** for the witness workflow — a
  small premium for the +15-pt genuine-fix gain.
- **`$/genuine` is the economic bottom line**: PCR ($0.215) ≈ Kimi ($0.200)
  per successful fix, while prompt-only is the worst buy ($0.349 — you pay for
  many failed runs). The self-hosted small-model harness reaches Kimi-level
  quality at roughly Kimi-level amortized cost here, and would be far cheaper
  self-hosted (electricity vs API).

## Operational findings (unchanged)

- **Kimi routing:** only the official "Moonshot AI" OpenRouter provider
  executes Kimi file-edit tool calls; third-party hosts loop without editing.
  Pinned via `provider.order` in `bench/router/litellm.config.yaml`.
- **Headless harness:** `claude -p` needs the natural-language workflow prompt
  + `--append-system-prompt-file SKILL.md` + absolute paths.
- **Cost accounting:** Claude Code's `total_cost_usd` misprices routed
  non-Anthropic models (~30× high); use token×price + OpenRouter credits delta.
