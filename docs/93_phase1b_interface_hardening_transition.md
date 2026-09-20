# Phase 1B Interface Hardening Transition

Status: no-model transition checkpoint

## Scope

This transition implements the contracts in `docs/92_phase1b_interface_hardening_design.md`
against the existing Phase 1B longitudinal runner. It is not Round-2 and does
not change the frozen 12-task stream, models, K*, executor, or task order.

## Changed implementation surface

- `phase1b_contract.py`: sanitized B→C projection; future-H boundary checks;
  temporal evidence events; A epistemic schema and dynamic memory-ID targets;
  identity-only reconciliation; deterministic evidence assessment binding;
  material ADD/REFINE/SPECIALIZE/MERGE operations.
- `run_phase1b_longitudinal.py`: fact commit before semantic stages; strict
  Phase 1B A output; fail-closed B→C/C/reconciliation stages without factual
  rollback; continuation event action retention.
- `prompts_phase1b.py` and `prompts.py`: corrected role boundaries and temporal
  visibility instructions.
- `tests/test_phase1b_longitudinal.py`: fake transport and no-model regression
  coverage.

## Pre-call checkpoint

The following must pass before any DashScope call:

```text
focused Phase 1B tests
MVP/Phase 1 regressions
Ruff
Python compile checks
git diff --check
```

The checkpoint must also confirm that the current acceptance run starts from
canonical K*, empty H/comparison/evidence state and uses the frozen 12-task
development stream. The subsequent acceptance run is one immutable stream;
there is no retry or second tuning pass.

The runner uses the explicit `--round acceptance` label for this run. This is
deliberately distinct from the historical Round-0/Round-1 development labels
and does not create a Round-2.

## Acceptance review boundary

The acceptance result is judged on leakage, evidence binding, temporal
attribution, memory materialization, and H/comparison identity. Descriptive
task success or model cost is not a readiness criterion. The old Round-1
negative evidence remains preserved and the old 12 tasks remain development
only.
