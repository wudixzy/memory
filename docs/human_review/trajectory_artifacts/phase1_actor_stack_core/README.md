# Core Phase 1A Actor-Stack Trajectories

This directory contains a deliberately small, tracked subset of the complete
raw D0/D1/D2 runtime artifacts for collaborator review. The files are copied
from the original saved runs; they are not reconstructed or rerun.

## Provenance

| variant | original run root | history mode | source status |
|---|---|---|---|
| D0 | `artifacts/exploratory_memory_mvp/gate-b1-qwen38-c1-20260919-ef44ff2-automanual/` | original Gate B1 actor history | `ORIGINAL SAVED ARTIFACT` |
| D1 | `artifacts/exploratory_memory_mvp/actor-stack-dev-d1-20260920-bd72f86/` | `actions_only` | `ORIGINAL SAVED ARTIFACT` |
| D2 | `artifacts/exploratory_memory_mvp/actor-stack-dev-d2-20260920-bd72f86/` | `action_observation` | `ORIGINAL SAVED ARTIFACT` |

Each selected task directory is copied in full, including its `initial_state`,
`run_config`, per-step actor inputs/prompts/responses, ordered admissible
actions, `action_index`, resolved action, validation, environment results,
execution summary, usage, and failure artifacts where present.

The complete untracked run roots remain in the local workspace. This tracked
subset is intended to make the central comparisons reviewable on GitHub
without committing all 10 tasks from all three runs.

## Selected complete trajectories

The same four task identities are included for all three variants:

| task directory | reason for inclusion | D0 | D1 | D2 |
|---|---|---:|---:|---:|
| `000_db485ebd50e7` | Laptop success control across all variants | win, 11 | win, 6 | win, 5 |
| `002_a04b6f263f6d` | persistent Shelf cool failure / carrier-contract review | cap, 32 | cap, 32 | cap, 32 |
| `005_6cf8b7e81791` | D1 improvement followed by D2 invalid-index failure | cap, 32 | win, 9 | invalid, 17 |
| `006_4d0e4849f544` | D0 success followed by D1/D2 regression | win, 13 | cap, 32 | cap, 32 |

Layout:

```text
d0_gate_b1/tasks/<task-directory>/c1_rep00/...
d1_actor_stack_dev/tasks/<task-directory>/c1_rep00/...
d2_actor_stack_dev/tasks/<task-directory>/c1_rep00/...
```

Variant-level `run_metadata.json`, `calibration_summary.json` or
`diagnostic_summary.json`, and `trajectory_manifest.json` are included where
they exist, so the selected traces retain their original run configuration and
task identity metadata.

## Review cautions

* D0 is the historical Gate B1 run and remains negative evidence; D1/D2 are
  development diagnostics, not independent admission results.
* These artifacts contain actor-visible task/state/history and raw model
  responses. They do not contain API credentials or hidden PDDL/oracle fields.
* Do not infer a causal D1/D2 effect from this selected subset alone. Read the
  complete per-step traces and the result memo at
  `docs/74_phase1_actor_stack_d1_d2_results.md`.
