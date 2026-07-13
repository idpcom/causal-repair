# FAQ

## Is Causal Repair a patch generator?

No. It is a repair process guardrail. It makes Claude Code collect evidence, approve an RCA gate, review for workaround patterns, and validate before finishing.

## Does it require dynamic workflow?

No. Dynamic workflow is recommended for larger or ambiguous failures. Small fixes can use the skill directly.

## Can it use Qwen, MiMo, or other model outputs?

Yes, but those outputs should be treated as candidate investigation or critique material. They should not directly authorize a patch.

## Why not use majority vote?

Majority vote can still converge on a plausible workaround. Causal Repair prefers evidence-based judgment and veto rules.

## What if tests are unavailable?

The verifier must mark validation as incomplete and report the exact command or environment the user should run.
