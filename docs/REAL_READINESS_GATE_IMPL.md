# Readiness implementation

`PC_ENGINE/core/real_readiness.py` exposes a deterministic evaluator with explicit blockers. The evaluator is pure and has no exchange or credential side effects.

The current minimums are 1,000 Market States, 1,000 outcomes and one eligible outcome group, plus all operational validation checks. These are conservative engineering defaults, not claims that the system currently has those samples.
