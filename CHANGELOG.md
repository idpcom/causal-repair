# Changelog

## 0.4.4

Context-footprint pass: the harness improves outcomes but was loading far more
context per repair than needed, especially on the (now-default) fast path.
This release trims what gets loaded and narrated without changing any gate,
schema, or decision rule — a pure context-reduction pass, not a behavior
change.

- `skills/causal-repair/SKILL.md`: added a "keep the transcript lean"
  instruction (report pass/fail + first failing line, not full
  diffs/stdout/file dumps — the on-disk artifacts are the record). Compressed
  the multi-agent investigation section and the Ledger-Relay section to a
  short trigger + pointer; the full instructions moved, unchanged, to the new
  `resources/escalation-protocol.md` (same lazy-load pattern already used by
  `resources/workflow-template.md`) so the fast path — the default for most
  repairs — no longer loads escalation-only detail it never uses.
- Alias skills/commands (`cr`, `fix`, `goal`, `review`) got the same
  lean-transcript one-liner for consistency.
- The four subagents (`root-cause-investigator`, `root-cause-judge`,
  `workaround-reviewer`, `repair-verifier`) each got one added rule bounding
  their own report to short excerpts/first-failure-lines instead of full
  dumps — this is where multi-agent escalation previously multiplied context
  the most (2+ investigators + judge + reviewer + verifier reports stacking
  in one conversation).
- No change to REQUIRED_FIELDS, validators, hook enforcement, or any approval
  criterion; `fixtures/python-null-profile` behavior is unaffected.

## 0.4.3

Field deployments showed the always-on full workflow REGRESSES below baseline
on task distributions where the bare model already solves most bugs (~70%
genuine): the multi-agent ceremony adds cost, drift, and non-completion on easy
bugs while adding no protection value there. Controlled runs confirmed the
harness only pays off where baselines game, and that heavy deliberation on
trivial bugs is itself a failure mode.

- Made the workflow adaptive (triage): the FAST PATH is now the default —
  single agent, no subagent fan-out, compact gate artifacts (checkpoint,
  enumerated contract clauses, per-clause contract tests, gate file are ALL
  still mandatory; they are cheap and carry the anti-gaming value), reasoning
  proportional to the bug.
- Escalation to the full multi-agent workflow (investigator fan-out, judge,
  adversarial reviewer, verifier, Ledger-Relay) now requires evidence: two
  fast-path failures, multi-file/interlocking contracts, an unclear causal
  path, prior workaround-shaped patches, or an explicit user request.
- PCR addendum: witnesses scale with the contract (one clause = one witness);
  witness ceremony must not outgrow the contract.
- Alias skills/commands updated to state the fast-path default.

## 0.4.2

- Added Proof-Carrying Repair (v0.4.1): `scripts/verify-witnesses.py` requires one witness test per contract clause that passes on the patch and, on the checkpointed base, fails for broken/at-risk clauses and passes for held ones, plus a mutation-strength check (`scripts/mutate.py`). Catches mislabeled clause status, unimplemented clauses, and vacuous tests.
- Added the change-surface coverage gate (v0.4.2): `scripts/verify-coverage.py` differential-fuzzes base vs patch and requires every behavior-changed function to be exercised by a broken/at-risk witness ("no unexplained behavior change").
- Added runner-enforced gate loop in the benchmark: the runner itself runs the witness and coverage gates after a harness run and re-invokes the model with the gate output on failure (CI-style), driving gate adherence to 100%.
- Documented mechanisms in `docs/coverage-gate.md`; results and cost accounting in `bench/RESULTS.md`.

## 0.4.0

Benchmarking showed the v0.3 workflow could make small models WORSE on contract-under-fit bugs: the RCA gate scoped to the visible symptom, `tests_to_run` accepted the visible test alone, and the reviewer only caught workaround shapes. 0.4.0 redesigns the workflow around contract completeness and long-horizon repair.

- Added required `contract_clauses` to the RCA gate (each documented behavior of the code under repair with status broken/held/at-risk), enforced by both `scripts/validate-rca-gate.py` and the PreToolUse hook.
- Required authored contract tests: `tests_to_run` must contain at least 2 commands including `.causal-repair/contract-tests*`; the visible reproduction alone is rejected.
- Added a pre-patch "write contract tests" step to the skill (one assertion per clause, one negative case per documented error contract).
- Redefined "minimal patch" as minimal relative to the documented contract, not the visible test.
- Extended the workaround reviewer with under-fit rejection rules (unimplemented/untested documented clauses, especially error contracts) alongside the existing over-fit shape rules.
- Extended the repair verifier to run contract tests and report per-clause pass/fail.
- Added the Ledger-Relay long-horizon protocol: `.causal-repair/ledger.json` externalizes goal/contract/segment state, `scripts/validate-ledger.py` validates it, and the hook blocks production edits unless the active ledger segment has `kind: "patch"` (no ledger file = unchanged single-segment behavior).
- Rewrote `resources/workflow-template.md` as Ledger-Relay orchestration with fresh-context segments and mechanical handoff gates.
- Rewrote `docs/rca-gate.md` to match the machine-checked JSON schema.
- Removed automatic hook registration from `.claude-plugin/plugin.json` so global skill installs do not run relative hook paths inside unrelated projects.
- Updated hook documentation and examples to use explicit opt-in settings with an absolute hook script path.
- Updated structure validation to require that plugin manifest hooks remain absent.
- Rejected `claude --bare` in RCA gate counterfactual commands because it disables hooks/plugins required by causal-repair.
- Kept empty stdout/stderr handling for no-output Claude runs without allowing bare causal-repair execution.

## 0.3.2

- Fixed destructive Bash matching so `rm -fr .` is classified as destructive instead of only write-like.
- Added `scripts/run-counterfactual.py` to execute the command recorded in `rca-gate.json` and compare actual exit status with the recorded result.
- Added unit tests for counterfactual execution, including mismatch detection and incomplete-result skipping.
- Updated CI to smoke-test the RCA gate validator and counterfactual runner.
- Updated skill and hook documentation to require counterfactual execution verification when practical.

## 0.3.1

- Fixed fixture patch files so `git apply` can apply them without `--recount`.
- Fixed model frontmatter parsing for files with leading blank lines before `---`.
- Added a test-passing hardcoded workaround fixture patch and updated fixture evaluation to flag it.
- Hardened the PreToolUse hook so write-like Bash blocking is enabled by default.
- Added default blocking for `git apply`, `apply_patch`, `patch`, `python -c`, `node -e`, `ruby -e`, `sh -c`, and `bash -c` before a valid RCA gate.
- Strengthened checkpoint validation so fake/empty checkpoint files do not pass.
- Strengthened RCA gate validation to reject empty ceremony fields and require structured counterfactual evidence.
- Added hook registration to `.claude-plugin/plugin.json` while keeping standalone settings examples for Claude Code versions that require manual hook setup.

## 0.3.0

- Added optional Claude Code PreToolUse hook enforcement via `scripts/hooks/pre-tool-use.py`.
- Added `.causal-repair/rca-gate.json` validation via `scripts/validate-rca-gate.py`.
- Added hook tests covering checkpoint enforcement, RCA gate enforcement, metadata edits, dangerous Bash blocking, and strict Bash write mode.
- Added hook setup documentation and example settings under `docs/hooks.md` and `examples/hooks/settings.example.json`.
- Updated the main skill to write and validate an RCA gate file before production edits when hooks are installed.

## 0.2.0

- Added mechanical checkpoint creation via `scripts/create-checkpoint.sh`.
- Added patch manifest generation via `scripts/create-patch-manifest.py`.
- Added unit tests for model routing and patch manifest behavior.
- Added executable fixture evals under `fixtures/python-null-profile`.
- Added `scripts/evaluate-fixtures.py` to verify known-good and known-bad patches.
- Updated CI to run structure validation, unit tests, checkpoint smoke tests, fixture evals, and model dry-runs.
- Hardened Causal Repair instructions with checkpoint, counterfactual, patch manifest, safe-revert, and no-invented-invariant gates.

## 0.1.0

- Initial marketplace-style Claude Code plugin layout.
- Added `causal-repair` skill.
- Added root-cause investigation, RCA judge, workaround review, and repair verification subagents.
- Added dynamic workflow reference template.
- Added minimal examples and starter eval definitions.
