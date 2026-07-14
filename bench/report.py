#!/usr/bin/env python3
"""Aggregate bench/results/results.jsonl into per-cell metrics.

Headline metric is the genuine-fix rate. The gaming rate (visible test passes
but held-out fails or the diff is workaround-shaped) is what the harness is
meant to reduce. Small n, so a Wilson 95% interval is printed and the tool
refuses to over-claim.

The final block answers the core question directly: does the Qwen+MiMo harness
(C4) reach the Kimi baseline (C3), and does it beat the small-model baselines
(C1/C2)?
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Sequence

BENCH_DIR = Path(__file__).resolve().parent
LABELS = ["genuine_fix", "gamed", "broken", "apply_fail"]


def fisher_exact_greater(a: int, b: int, c: int, d: int) -> float:
    """One-sided Fisher exact p (P[X >= a]) for the 2x2 table
    [[a, b], [c, d]] = [[cond1 genuine, cond1 not], [cond2 genuine, cond2 not]].
    Stdlib hypergeometric; fine for the small n this benchmark produces."""
    n = a + b + c + d
    row1, col1 = a + b, a + c
    denom = math.comb(n, col1)
    p = 0.0
    for x in range(a, min(row1, col1) + 1):
        if col1 - x > c + d:
            continue
        p += math.comb(row1, x) * math.comb(c + d, col1 - x) / denom
    return min(1.0, p)


def bootstrap_diff_ci(rows1: List[dict], rows2: List[dict], iters: int = 5000,
                      seed: int = 0) -> tuple[float, float]:
    """95% CI for genuine-rate difference (cond1 - cond2), resampling TASKS
    (cluster bootstrap) so repeated reps of one task don't fake independence."""
    import random as _random
    rng = _random.Random(seed)
    by_task1: Dict[str, List[int]] = defaultdict(list)
    by_task2: Dict[str, List[int]] = defaultdict(list)
    for r in rows1:
        by_task1[r["task"]].append(1 if r["label"] == "genuine_fix" else 0)
    for r in rows2:
        by_task2[r["task"]].append(1 if r["label"] == "genuine_fix" else 0)
    tasks = sorted(set(by_task1) | set(by_task2))
    diffs = []
    for _ in range(iters):
        sample = [tasks[rng.randrange(len(tasks))] for _ in tasks]
        n1 = k1 = n2 = k2 = 0
        for t in sample:
            k1 += sum(by_task1.get(t, [])); n1 += len(by_task1.get(t, []))
            k2 += sum(by_task2.get(t, [])); n2 += len(by_task2.get(t, []))
        if n1 and n2:
            diffs.append(k1 / n1 - k2 / n2)
    if not diffs:
        return (0.0, 0.0)
    diffs.sort()
    return (diffs[int(0.025 * len(diffs))], diffs[int(0.975 * len(diffs)) - 1])


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score 95% CI for a binomial proportion."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def load(path: Path) -> List[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def cost_of(row: dict) -> Optional[float]:
    """Prefer our token-based real cost; fall back to Claude's (unreliable for
    routed non-Anthropic models) only if the estimate is absent."""
    eng = row.get("engine") or {}
    c = eng.get("cost_est_usd")
    if isinstance(c, (int, float)):
        return c
    c = eng.get("cost_usd")
    return c if isinstance(c, (int, float)) else None


def duration_of(row: dict) -> Optional[float]:
    eng = row.get("engine") or {}
    d = eng.get("duration_s")
    return d if isinstance(d, (int, float)) else None


def summarize_cell(rows: List[dict]) -> dict:
    n = len(rows)
    counts = {lab: sum(1 for r in rows if r["label"] == lab) for lab in LABELS}
    gf = counts["genuine_fix"]
    lo, hi = wilson(gf, n)
    costs = [c for c in (cost_of(r) for r in rows) if c is not None]
    durs = [d for d in (duration_of(r) for r in rows) if d is not None]
    total = sum(costs) if costs else None
    return {
        "n": n,
        "counts": counts,
        "genuine_fix_rate": gf / n if n else 0.0,
        "genuine_fix_ci": (lo, hi),
        "gaming_rate": counts["gamed"] / n if n else 0.0,
        "apply_fail_rate": counts["apply_fail"] / n if n else 0.0,
        "total_cost": round(total, 4) if total is not None else None,
        "mean_cost": round(total / len(costs), 5) if costs else None,
        # amortized cost of one genuine fix: how much you pay per success
        "cost_per_genuine": round(total / gf, 4) if (total is not None and gf) else None,
        "mean_duration_s": round(sum(durs) / len(durs), 1) if durs else None,
    }


def pct(x: float) -> str:
    return f"{100 * x:5.1f}%"


def print_table(cells: Dict[str, dict]) -> None:
    header = f"{'cell':<26} {'n':>3} {'genuine':>8} {'95% CI':>15} {'gamed':>7} {'apply_fail':>10} {'cost$':>8}"
    print(header)
    print("-" * len(header))
    for name, s in cells.items():
        lo, hi = s["genuine_fix_ci"]
        ci = f"[{pct(lo).strip()},{pct(hi).strip()}]"
        cost = f"{s['total_cost']:.3f}" if s["total_cost"] is not None else "  -  "
        print(
            f"{name:<26} {s['n']:>3} {pct(s['genuine_fix_rate']):>8} {ci:>15} "
            f"{pct(s['gaming_rate']):>7} {pct(s['apply_fail_rate']):>10} {cost:>8}"
        )


def print_cost_table(cells: Dict[str, dict]) -> None:
    """Cost accounting per cell. All figures are the token-based estimate
    (cached input counted at full price = conservative upper bound); the
    authoritative per-batch spend is the OpenRouter credits delta printed by
    run.py. cost/genuine is the amortized price of one real fix."""
    print("\nCost (USD, token-based estimate; upper bound):")
    header = (f"{'cell':<26} {'runs':>5} {'$/run':>8} {'total$':>9} "
              f"{'$/genuine':>10} {'~s/run':>7}")
    print(header)
    print("-" * len(header))
    grand = 0.0
    for name, s in cells.items():
        mc = f"{s['mean_cost']:.4f}" if s["mean_cost"] is not None else "  -  "
        tot = s["total_cost"] if s["total_cost"] is not None else None
        tots = f"{tot:.3f}" if tot is not None else "  -  "
        cpg = f"{s['cost_per_genuine']:.4f}" if s["cost_per_genuine"] is not None else "  -  "
        dur = f"{s['mean_duration_s']:.0f}" if s["mean_duration_s"] is not None else "  -  "
        if tot is not None:
            grand += tot
        print(f"{name:<26} {s['n']:>5} {mc:>8} {tots:>9} {cpg:>10} {dur:>7}")
    print("-" * len(header))
    print(f"{'TOTAL':<26} {'':>5} {'':>8} {grand:>9.3f}")


def by_bug_class(rows: List[dict]) -> None:
    groups: Dict[tuple, List[dict]] = defaultdict(list)
    for r in rows:
        groups[(r["cell"], r.get("bug_class", "?"))].append(r)
    print("\nGenuine-fix rate by bug class:")
    classes = sorted({r.get("bug_class", "?") for r in rows})
    cells = sorted({r["cell"] for r in rows})
    head = f"{'cell':<26}" + "".join(f"{c[:12]:>14}" for c in classes)
    print(head)
    for cell in cells:
        line = f"{cell:<26}"
        for cls in classes:
            g = groups.get((cell, cls), [])
            if g:
                rate = sum(1 for r in g if r["label"] == "genuine_fix") / len(g)
                line += f"{pct(rate):>14}"
            else:
                line += f"{'-':>14}"
        print(line)


def genuine_counts(rows: List[dict]) -> tuple[int, int]:
    g = sum(1 for r in rows if r["label"] == "genuine_fix")
    return g, len(rows)


def pairwise_stats(by_cell: Dict[str, List[dict]], pairs: List[tuple[str, str]]) -> None:
    """Fisher exact (one-sided, cond1 > cond2 on genuine) + task-cluster
    bootstrap CI of the rate difference, restricted to shared tasks."""
    print("\nPairwise comparisons (genuine rate, cond1 vs cond2):")
    for c1, c2 in pairs:
        if c1 not in by_cell or c2 not in by_cell:
            continue
        shared = {r["task"] for r in by_cell[c1]} & {r["task"] for r in by_cell[c2]}
        r1 = [r for r in by_cell[c1] if r["task"] in shared]
        r2 = [r for r in by_cell[c2] if r["task"] in shared]
        if not r1 or not r2:
            continue
        g1, n1 = genuine_counts(r1)
        g2, n2 = genuine_counts(r2)
        p = fisher_exact_greater(g1, n1 - g1, g2, n2 - g2)
        lo, hi = bootstrap_diff_ci(r1, r2)
        print(f"  {c1} ({g1}/{n1}) vs {c2} ({g2}/{n2}) on {len(shared)} shared task(s): "
              f"diff {100*(g1/n1-g2/n2):+.1f} pts, boot95 [{100*lo:+.1f},{100*hi:+.1f}], "
              f"Fisher one-sided p={p:.3f}")


def comparison(cells: Dict[str, dict]) -> None:
    print("\n" + "=" * 60)
    print("CORE QUESTION")
    print("=" * 60)

    def rate(name: str) -> Optional[float]:
        return cells[name]["genuine_fix_rate"] if name in cells else None

    c1, c2, c3, c4 = (rate(x) for x in (
        "C1-qwen-baseline", "C2-mimo-baseline", "C3-kimi-baseline", "C4-qwen-mimo-harness"))

    if c4 is not None and c3 is not None:
        gap = c4 - c3
        verb = "reaches/exceeds" if gap >= 0 else "falls short of"
        print(f"C4 harness ({pct(c4).strip()}) {verb} Kimi bar C3 ({pct(c3).strip()}); "
              f"gap {gap*100:+.1f} pts")
    if c4 is not None and c1 is not None:
        print(f"Harness lift over Qwen baseline (C4-C1): {(c4-c1)*100:+.1f} pts")
    if c4 is not None and c2 is not None:
        print(f"Harness lift over MiMo baseline (C4-C2): {(c4-c2)*100:+.1f} pts")
    print("\nNote: small n — read the Wilson intervals above before concluding. "
          "Overlapping intervals mean the difference is not yet significant.")


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Aggregate benchmark results")
    p.add_argument("--results", type=Path, default=BENCH_DIR / "results" / "results.jsonl")
    p.add_argument("--by-bug-class", action="store_true")
    return p.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    if not args.results.exists():
        print(f"no results at {args.results}")
        return 1
    rows = load(args.results)
    if not rows:
        print("results file is empty")
        return 1

    by_cell: Dict[str, List[dict]] = defaultdict(list)
    for r in rows:
        by_cell[r["cell"]].append(r)

    # Preserve config cell order if available, else sorted.
    order = ["qwen-baseline", "mimo-baseline", "kimi-baseline", "harness"]
    ordered = [c for c in order if c in by_cell] + sorted(c for c in by_cell if c not in order)

    cells = {name: summarize_cell(by_cell[name]) for name in ordered}
    print_table(cells)
    print_cost_table(cells)
    if args.by_bug_class:
        by_bug_class(rows)
    comparison(cells)
    pairwise_stats(by_cell, [
        ("harness", "qwen-baseline"),
        ("harness", "mimo-baseline"),
        ("harness", "kimi-baseline"),
    ])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
