# Model Routing Notes

Causal Repair is intentionally not a "make many small models vote" workflow.

Recommended routing:

- Use fast or lower-cost models for evidence capture, search, independent hypotheses, diff sniffing, and validation summaries.
- Use stronger models for RCA judgment, patch authoring, and final decisions.
- Treat Qwen, MiMo, or other external model outputs as candidate policies or critique material, not as patch authority.

## Recommended split

```text
fast model: root-cause-investigator
stronger model: root-cause-judge
stronger model: patch authoring
fast model: workaround-reviewer
fast model: repair-verifier
```

## Veto beats majority vote

A minority objection can block patching if it shows the causal path is missing or the patch is workaround-shaped.
