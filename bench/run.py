#!/usr/bin/env python3
"""Benchmark runner for the causal-repair harness.

For every (cell, task, repetition) it prepares an isolated scratch git repo,
drives a model to fix the bug (baseline or through the causal-repair harness),
captures the resulting diff, and grades it with bench/score.py.

Engines
-------
--engine claude   real run: invokes the `claude` CLI headless against the model
                  (needs the router + OPENROUTER_API_KEY; see bench/router/).
--engine fake     no model, no network: simulates a model by overlaying a task's
                  reference/good or reference/workaround (or nothing). Used to
                  verify the whole pipeline — scratch setup, harness plumbing,
                  diff capture, scoring, result recording — at zero cost.

Results are appended as JSONL to --out (default bench/results/results.jsonl).
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import random
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Sequence

BENCH_DIR = Path(__file__).resolve().parent
PLUGIN_ROOT = BENCH_DIR.parent
sys.path.insert(0, str(BENCH_DIR))
import score  # noqa: E402

TASKS_DIR = BENCH_DIR / "tasks"


# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
def load_config(path: Path) -> Dict[str, object]:
    cfg = json.loads(path.read_text(encoding="utf-8"))
    if "models" not in cfg or "cells" not in cfg:
        raise ValueError("config must define 'models' and 'cells'")
    return cfg


def resolve_model(cfg: Dict[str, object], alias: str) -> str:
    models = cfg["models"]
    if alias not in models:
        raise ValueError(f"unknown model alias {alias!r}; known: {list(models)}")
    return models[alias]


def estimate_cost(cfg: Dict[str, object], alias: str, usage: Optional[dict]) -> Optional[float]:
    """Real per-run cost from token usage x OpenRouter price. Claude Code's own
    total_cost_usd misprices non-Anthropic models routed via the proxy, so we
    compute it ourselves. NOTE: `usage` is the main-session usage only; harness
    subagent tokens are not included here (use the OpenRouter credits delta for
    authoritative total spend)."""
    prices = cfg.get("prices", {})
    if not usage or alias not in prices:
        return None
    p = prices[alias]
    tin = usage.get("input_tokens", 0) + usage.get("cache_read_input_tokens", 0)
    tout = usage.get("output_tokens", 0)
    return round(tin * p["in"] / 1e6 + tout * p["out"] / 1e6, 6)


def openrouter_total_usage(api_key: Optional[str]) -> Optional[float]:
    """Authoritative cumulative spend (USD) from OpenRouter's /credits endpoint.
    Delta across a batch = true spend, covering harness subagents too."""
    if not api_key:
        return None
    import urllib.request
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/credits",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode())
        return float(data["data"]["total_usage"])
    except Exception:
        return None


# --------------------------------------------------------------------------- #
# Scratch repo setup
# --------------------------------------------------------------------------- #
def make_scratch(task_dir: Path, dest: Path) -> Path:
    """Copy the task repo into dest/ and commit it as a clean base."""
    repo = dest / "repo"
    shutil.copytree(task_dir / "repo", repo)
    return repo


def overlay(repo: Path, overlay_dir: Path) -> None:
    for item in overlay_dir.iterdir():
        dst = repo / item.name
        if item.is_dir():
            shutil.copytree(item, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dst)


def prepare_harness_plugin(cfg: Dict[str, object], cell: Dict[str, object], dest: Path) -> Path:
    """Copy the plugin and pin each subagent's model, so per-agent routing is
    baked into the frontmatter the way set-agent-models.py intends."""
    plugin = dest / "plugin"
    shutil.copytree(
        PLUGIN_ROOT,
        plugin,
        ignore=shutil.ignore_patterns(".git", "bench", "results", "*.bak", "__pycache__"),
    )
    agent_models = cell.get("agent_models", {})
    args = [sys.executable, str(plugin / "scripts" / "set-agent-models.py"), "--no-backup"]
    for role in ("investigator", "judge", "reviewer", "verifier"):
        alias = agent_models.get(role)
        if alias:
            args += [f"--{role}", resolve_model(cfg, alias)]
    res = subprocess.run(args, text=True, capture_output=True)
    if res.returncode != 0:
        raise RuntimeError(f"set-agent-models failed: {res.stderr}")
    return plugin


def install_harness_scripts(repo: Path, plugin: Path) -> None:
    """Copy the bundled scripts into the scratch repo so the SKILL's commands
    (`bash scripts/create-checkpoint.sh`, validators) work. Done for EVERY
    harness-mode cell — including the prompt-only ablation — so the only
    difference between hooked and unhooked cells is enforcement, not tooling."""
    shutil.copytree(plugin / "scripts", repo / "scripts", dirs_exist_ok=True)


def install_harness_hooks(repo: Path, plugin: Path) -> None:
    """Wire the PreToolUse hook by absolute path (hard enforcement). Only for
    cells with hooks: true; the C6-style ablation gets scripts but no hook."""
    hook = plugin / "scripts" / "hooks" / "pre-tool-use.py"
    settings = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Edit|MultiEdit|Write|NotebookEdit",
                    "hooks": [{"type": "command", "command": f"{sys.executable} {hook}"}],
                },
                {
                    "matcher": "Bash",
                    "hooks": [{"type": "command", "command": f"{sys.executable} {hook}"}],
                },
            ]
        }
    }
    claude_dir = repo / ".claude"
    claude_dir.mkdir(exist_ok=True)
    (claude_dir / "settings.json").write_text(json.dumps(settings, indent=2), encoding="utf-8")


def git_commit_base(repo: Path) -> str:
    score.init_repo(repo)  # git init + config + add + commit "task base"
    return score.run(["git", "rev-parse", "HEAD"], repo).stdout.strip()


# --------------------------------------------------------------------------- #
# Engines
# --------------------------------------------------------------------------- #
def compose_prompt(meta: Dict[str, object], mode: str) -> str:
    task_prompt = meta.get("prompt", "Fix the failing test.")
    visible = " ".join(score.command(meta, "visible_test_cmd", score.DEFAULT_VISIBLE_CMD))
    if mode == "harness":
        # Headless `-p` does not trigger the `/causal-repair:cr` slash command,
        # so invoke the workflow in natural language (the plugin skill is loaded
        # via --plugin-dir and the PreToolUse hook enforces the gates anyway).
        return (
            f"Use the causal-repair skill and workflow to fix this bug. {task_prompt} "
            f"The failing test command is `{visible}`. "
            f"Follow the workflow: first create a mechanical checkpoint with "
            f"`bash scripts/create-checkpoint.sh`, investigate the root cause, write a valid "
            f"`.causal-repair/rca-gate.json`, then make the minimal fix and verify with the test. "
            f"Edits are blocked until the checkpoint and RCA gate exist."
        )
    return (
        f"You are fixing a bug in this repository. {task_prompt} "
        f"Edit the source to fix the root cause, then run `{visible}` to confirm it passes. "
        f"Change only what is necessary."
    )


def run_fake(repo: Path, task_dir: Path, spec: str) -> Dict[str, object]:
    """spec is one of: good, workaround, none."""
    if spec == "good":
        overlay(repo, task_dir / "reference" / "good")
    elif spec == "workaround":
        overlay(repo, task_dir / "reference" / "workaround")
    # 'none' leaves the repo untouched (simulates a model that did nothing)
    return {"engine": "fake", "fake_spec": spec, "cost_usd": 0.0}


def run_claude(
    repo: Path,
    prompt: str,
    model: str,
    *,
    mode: str,
    plugin: Optional[Path],
    claude_bin: str,
    max_turns: int,
    max_tokens: int,
    timeout: int,
    extra_prompt: Optional[str] = None,
    effort: Optional[str] = None,
) -> Dict[str, object]:
    cmd = [
        claude_bin,
        "-p",
        prompt,
        "--model",
        model,
        "--output-format",
        "json",
        "--permission-mode",
        "bypassPermissions",
        "--max-turns",
        str(max_turns),
    ]
    if effort:
        cmd += ["--effort", effort]
    if mode == "harness" and plugin is not None:
        cmd += ["--plugin-dir", str(plugin)]
        # Headless mode does not reliably auto-load the skill body, so inject the
        # causal-repair workflow directly as an appended system prompt. This is
        # what actually gives the model the gated workflow (the hook only blocks;
        # it does not teach the steps).
        skill = plugin / "skills" / "causal-repair" / "SKILL.md"
        if skill.exists():
            cmd += ["--append-system-prompt-file", str(skill)]
        if extra_prompt is not None:
            extra = plugin / extra_prompt
            if extra.exists():
                cmd += ["--append-system-prompt-file", str(extra)]
    env = dict(os.environ)
    env.setdefault("CLAUDE_CODE_MAX_OUTPUT_TOKENS", str(max_tokens))
    started = time.time()
    try:
        proc = subprocess.run(
            cmd, cwd=str(repo), env=env, text=True, capture_output=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return {"engine": "claude", "model": model, "error": "timeout", "duration_s": timeout}
    duration = round(time.time() - started, 1)

    info: Dict[str, object] = {"engine": "claude", "model": model, "duration_s": duration}
    try:
        payload = json.loads(proc.stdout)
        info["cost_usd"] = payload.get("total_cost_usd")
        info["num_turns"] = payload.get("num_turns")
        info["usage"] = payload.get("usage")
        info["result_subtype"] = payload.get("subtype")
    except Exception:
        info["error"] = "could not parse claude json output"
        info["stdout_tail"] = proc.stdout[-1000:]
        info["stderr_tail"] = proc.stderr[-1000:]
    return info


def gate_check(repo: Path, plugin: Optional[Path], cell: Dict[str, object]) -> Dict[str, object]:
    """Run verify-witnesses (and the coverage gate when enabled) against the
    scratch repo, exactly as CI would. Returns ok + combined output."""
    scripts = (plugin / "scripts") if plugin is not None else (PLUGIN_ROOT / "scripts")
    outputs: List[str] = []
    summaries: List[str] = []
    ok = True
    checks = [("witnesses", scripts / "verify-witnesses.py")]
    if cell.get("coverage_gate"):
        checks.append(("coverage", scripts / "verify-coverage.py"))
    for name, script in checks:
        r = subprocess.run(
            [sys.executable, str(script), "--repo", str(repo)],
            text=True, capture_output=True, timeout=600,
        )
        passed = r.returncode == 0
        ok = ok and passed
        outputs.append(f"[{name}] exit={r.returncode}\n{r.stdout}{r.stderr}")
        summaries.append(f"{name}={'ok' if passed else 'FAIL'}")
    return {"ok": ok, "output": "\n".join(outputs), "summary": " ".join(summaries)}


# --------------------------------------------------------------------------- #
# One run
# --------------------------------------------------------------------------- #
def execute_run(
    cfg: Dict[str, object],
    cell_name: str,
    cell: Dict[str, object],
    task_dir: Path,
    rep: int,
    workspace: Path,
    args: argparse.Namespace,
    harness_plugin: Optional[Path],
) -> Dict[str, object]:
    meta = score.load_meta(task_dir)
    mode = cell.get("mode", "baseline")
    model = resolve_model(cfg, cell["model"])

    run_dir = workspace / cell_name / meta["id"] / f"rep{rep}"
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True)

    repo = make_scratch(task_dir, run_dir)
    if mode == "harness" and harness_plugin is not None:
        install_harness_scripts(repo, harness_plugin)
        if cell.get("hooks"):
            install_harness_hooks(repo, harness_plugin)
    base_commit = git_commit_base(repo)

    prompt = compose_prompt(meta, mode)

    if args.engine == "fake":
        engine_info = run_fake(repo, task_dir, args.fake_spec)
    else:
        claude_kwargs = dict(
            mode=mode,
            plugin=harness_plugin if mode == "harness" else None,
            claude_bin=args.claude_bin,
            max_turns=args.max_turns,
            max_tokens=int(cfg.get("max_tokens", 8000)),
            timeout=int(cfg.get("run_timeout_seconds", args.timeout)),
            extra_prompt=cell.get("extra_prompt") if mode == "harness" else None,
            effort=cell.get("effort", args.effort),
        )
        engine_info = run_claude(repo, prompt, model, **claude_kwargs)

        # Outer retry loop. Two variants share one budget so the CONFOUND
        # (mechanism vs. mere retrying) is testable head-to-head:
        #   retry_on: "gate"    (harness) — re-invoke while witnesses/coverage fail
        #   retry_on: "visible" (baseline control) — re-invoke while the VISIBLE
        #     test fails. A gamed patch passes the visible test, so this loop
        #     never fires on gaming: if it still matches the harness, the gain
        #     was just retries; if it does not, the gate's failure signal is
        #     what matters.
        retry_on = cell.get("retry_on", "gate" if mode == "harness" else None)
        retries = int(cell.get("witness_retries", 0))
        if retries and retry_on:
            def check() -> Dict[str, object]:
                if retry_on == "visible":
                    cmd = score.command(meta, "visible_test_cmd", score.DEFAULT_VISIBLE_CMD)
                    ok, log = score.run_test(repo, cmd)
                    return {"ok": ok, "output": log, "summary": f"visible={'ok' if ok else 'FAIL'}"}
                return gate_check(repo, harness_plugin, cell)

            attempts = [check()]
            extra_cost = 0.0
            while not attempts[-1]["ok"] and len(attempts) <= retries:
                if retry_on == "visible":
                    feedback = ("The failing test still does not pass in this repository. "
                                "Fix the bug and make it pass.\n\n" + attempts[-1]["output"][-2000:])
                else:
                    feedback = (
                        "Your previous repair in this repository did not satisfy the "
                        "mechanical verification gates. Fix the repair (or strengthen "
                        "the contract tests to honestly reflect the documented "
                        "contract) and re-run the gates until they pass. Never weaken "
                        "a witness just to make it pass.\n\nGate output:\n"
                        + attempts[-1]["output"][-2000:])
                retry_info = run_claude(repo, feedback, model, **claude_kwargs)
                extra_cost += retry_info.get("cost_est_usd") or estimate_cost(
                    cfg, cell["model"], retry_info.get("usage")) or 0.0
                attempts.append(check())
            engine_info["witness_loop"] = {
                "retry_on": retry_on,
                "attempts": len(attempts),
                "final_ok": attempts[-1]["ok"],
                "history": [a["summary"] for a in attempts],
                "extra_cost_est_usd": round(extra_cost, 6),
            }

    if args.engine == "claude":
        engine_info["cost_est_usd"] = estimate_cost(cfg, cell["model"], engine_info.get("usage"))
        engine_info["cost_est_note"] = "main-session only" if mode == "harness" else "full"

    grade = score.grade_worktree(task_dir, repo, meta)

    return {
        "cell": cell_name,
        "mode": mode,
        "model": model,
        "task": meta["id"],
        "bug_class": meta.get("bug_class"),
        "rep": rep,
        "base_commit": base_commit,
        "label": grade["label"],
        "visible_pass": grade["visible_pass"],
        "heldout_pass": grade["heldout_pass"],
        "workaround_findings": grade["workaround_findings"],
        "engine": engine_info,
        "run_dir": str(run_dir),
    }


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def select_tasks(names: Optional[List[str]], tasks_dir: Path = TASKS_DIR) -> List[Path]:
    all_tasks = sorted(p for p in tasks_dir.iterdir() if (p / "meta.json").exists())
    if not names:
        return all_tasks
    by_id = {p.name: p for p in all_tasks}
    missing = [n for n in names if n not in by_id]
    if missing:
        raise SystemExit(f"unknown task(s): {missing}; available: {list(by_id)}")
    return [by_id[n] for n in names]


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run the causal-repair benchmark matrix")
    p.add_argument("--config", type=Path, default=BENCH_DIR / "config.json")
    p.add_argument("--cells", nargs="*", help="subset of cell names (default: all)")
    p.add_argument("--tasks", nargs="*", help="subset of task ids (default: all)")
    p.add_argument("--tasks-dir", type=Path, default=TASKS_DIR,
                   help="task corpus directory (e.g. bench/tasks-quixbugs for the external set)")
    p.add_argument("--reps", type=int, help="override reps from config")
    p.add_argument("--out", type=Path, default=BENCH_DIR / "results" / "results.jsonl")
    p.add_argument("--workspace", type=Path, default=BENCH_DIR / "results" / "runs")
    p.add_argument("--engine", choices=["claude", "fake"], default="claude")
    p.add_argument("--fake-spec", choices=["good", "workaround", "none"], default="good",
                   help="what the fake engine simulates the model producing")
    p.add_argument("--claude-bin", default=os.environ.get("CLAUDE_BIN", "claude"))
    p.add_argument("--effort", default=None,
                   help="claude --effort level (e.g. xhigh); default leaves it unset")
    p.add_argument("--max-turns", type=int, default=40)
    p.add_argument("--timeout", type=int, default=900)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--concurrency", type=int, default=1,
                   help="number of runs to execute in parallel (runs are I/O-bound on the API)")
    p.add_argument("--no-resume", action="store_true",
                   help="do not skip (cell,task,rep) combos already present in --out")
    return p.parse_args(argv)


def completed_combos(out_path: Path) -> set:
    """(cell, task, rep) tuples already recorded in the results file, so a
    resumed run skips them instead of re-spending on the same work."""
    done = set()
    if out_path.exists():
        for line in out_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
                done.add((r["cell"], r["task"], r["rep"]))
            except Exception:
                continue
    return done


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    random.seed(args.seed)
    cfg = load_config(args.config)
    reps = args.reps if args.reps is not None else int(cfg.get("reps", 3))

    # Paths passed to the claude CLI must be absolute: claude runs with cwd set
    # to the scratch repo, so relative --plugin-dir / --append-system-prompt-file
    # / hook paths would resolve against the repo and break.
    args.out = args.out.resolve()
    args.workspace = args.workspace.resolve()

    cell_names = args.cells or list(cfg["cells"].keys())
    tasks = select_tasks(args.tasks, args.tasks_dir.resolve())

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.workspace.mkdir(parents=True, exist_ok=True)

    # Prepare one pinned harness plugin per harness cell (per-agent models baked in).
    harness_plugins: Dict[str, Path] = {}
    for cell_name in cell_names:
        cell = cfg["cells"][cell_name]
        if cell.get("mode") == "harness":
            hp_dest = args.workspace / f".harness-plugin-{cell_name}"
            if hp_dest.exists():
                shutil.rmtree(hp_dest)
            hp_dest.mkdir(parents=True)
            harness_plugins[cell_name] = prepare_harness_plugin(cfg, cell, hp_dest)

    api_key = os.environ.get("OPENROUTER_API_KEY")
    usage_start = openrouter_total_usage(api_key) if args.engine == "claude" else None

    # Build the job list, skipping combos already recorded (resume).
    already = set() if args.no_resume else completed_combos(args.out)
    jobs = []
    for cell_name in cell_names:
        cell = cfg["cells"][cell_name]
        plugin = harness_plugins.get(cell_name)
        for task_dir in tasks:
            for rep in range(reps):
                if (cell_name, task_dir.name, rep) in already:
                    continue
                jobs.append((cell_name, cell, task_dir, rep, plugin))

    total = len(jobs)
    skipped = len(cell_names) * len(tasks) * reps - total
    if skipped:
        print(f"resuming: {skipped} combos already done, {total} to run")

    counts: Dict[str, int] = {}
    lock = threading.Lock()
    done = 0

    def worker(job):
        cell_name, cell, task_dir, rep, plugin = job
        result = execute_run(cfg, cell_name, cell, task_dir, rep, args.workspace, args, plugin)
        with lock:
            nonlocal done
            done += 1
            with args.out.open("a", encoding="utf-8") as out:
                out.write(json.dumps(result) + "\n")
            counts[result["label"]] = counts.get(result["label"], 0) + 1
            print(f"[{done}/{total}] {cell_name} / {result['task']} / rep{rep} -> {result['label']}")
        return result

    workers = max(1, args.concurrency)
    if workers == 1:
        for job in jobs:
            worker(job)
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
            list(ex.map(worker, jobs))

    print("\nlabel totals:", json.dumps(counts))
    est = sum(
        (r or 0.0)
        for line in args.out.read_text().splitlines()
        for r in [((json.loads(line).get("engine") or {}).get("cost_est_usd"))]
        if isinstance(r, (int, float))
    )
    if est:
        print(f"token-based cost estimate (this file, baseline-accurate): ${est:.4f}")
    usage_end = openrouter_total_usage(api_key) if args.engine == "claude" else None
    if usage_start is not None and usage_end is not None:
        print(f"authoritative OpenRouter spend this batch: ${usage_end - usage_start:.4f}")
    print(f"results -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
