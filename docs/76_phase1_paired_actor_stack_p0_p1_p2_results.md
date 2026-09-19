# Phase 1 Paired Actor-Stack Diagnostic: P0/P1/P2 Results

## Scope and status

This is the development diagnostic specified by `docs/75_phase1_paired_actor_stack_diagnostic_plan.md`. It is not Gate B1 admission evidence and is not a Phase 1A target experiment.

The run compared:

| Variant | K* | Model-visible history |
| --- | --- | --- |
| P0 | canonical K* v1 | `actions_only` |
| P1 | development candidate K* v2b | `actions_only` |
| P2 | development candidate K* v2b | unified `interaction_history=[{action, observation}]` |

P2 does not expose the duplicate `executed_action_history` or `action_observation_history` fields. No prompt, model, temperature, thinking mode, step cap, task membership, B/C/H/A component, actor status, or canonical K* was changed during the run.

The no-model transition commit was `359e08e234d8d9a3233d7e8c3e4f509cef38799e`. The execution used the same commit. The committed actor manifest remains `candidate_pending_independent_reliability_gate`, and K* v2b remains a development candidate.

## Execution and reproducibility

The first attempted run failed closed during carrier initialization because the default Python environment did not contain the pinned ALFWorld/TextWorld dependencies. It made no model call and is retained at:

`artifacts/exploratory_memory_mvp/paired-actor-stack-p0-p1-p2-20260920-359e08e`

The protocol-consistent run used the existing Python 3.9 `memory-automanual` environment, the pinned repository carrier, a new non-overwriting output directory, and direct transport with proxy variables removed. It completed all 15 episodes at:

`artifacts/exploratory_memory_mvp/paired-actor-stack-p0-p1-p2-20260920-359e08e-rerun1`

The run root contains:

* `run_metadata.json`
* `task_manifest_snapshot.json`
* `trajectory_manifest.json`
* `paired_diagnostic_summary.json`

Each of the five task directories contains `replay_spec.json`, `paired_initial_states.json`, and `pairing_proofs.json` with `p0_p1`, `p0_p2`, and `p1_p2` proofs. All 15 episode summaries report valid pairing, and all three proofs are valid for every task. The execution episodes were created from the frozen replay specification before actor calls; pairing metadata was not included in actor inputs.

The artifact audit found 417 step directories. Each step retains actor input/prompt/raw response/parsed response, ordered current admissible actions, action index and validation, resolved environment action, environment result, `step.json`, and usage. Episode-level execution, summary, configuration, and usage artifacts are also present. No infrastructure failure or invalid action index occurred in the completed run.

The frozen digests used by the run were:

```text
task manifest: 5895aac538f1d1c39f9242ed82ec6a61a05ce4bba3ad3d6ab4ba1bb1eb11c90b
K* v1:         331728a3e001c8a3bc7e992d7605ee428501c34d0d5d8fed75a19abd98314447
K* v2b:        15bd0fe9d287c3413612138bba165817600b510028774c364c460d5f6bcaa658
actor manifest:00816f2eeb6626dfd68ec20943aef0f755e689fa657587a2f6af628aad8c3a94
```

## Per-task results

`completed` means the carrier reported `won=true`; `step_cap_reached` means the episode used all 32 actor steps without completion. These are mechanical outcomes only.

| Task | P0 | P1 | P2 |
| --- | --- | --- | --- |
| Laptop -> Desk | won, 11 steps | step cap, 32 | won, 4 |
| SoapBar -> Cabinet | step cap, 32 | step cap, 32 | step cap, 32 |
| Apple -> Fridge | won, 18 | step cap, 32 | step cap, 32 |
| Mug -> Shelf | step cap, 32 | step cap, 32 | step cap, 32 |
| Mug -> CoffeeMachine | step cap, 32 | step cap, 32 | step cap, 32 |

Exact episode artifact paths are listed in `trajectory_manifest.json` and in `paired_diagnostic_summary.json`. The task directories are:

```text
tasks/000_db485ebd50e7  Laptop -> Desk
tasks/001_4d0e4849f544  SoapBar -> Cabinet
tasks/002_9fa5d3902fe0  Apple -> Fridge
tasks/003_a04b6f263f6d  Mug -> Shelf
tasks/004_6cf8b7e81791  Mug -> CoffeeMachine
```

## Mechanical aggregate

| Variant | Wins | Step-cap episodes | Steps / actor calls | Input tokens | Output tokens | Cached input tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| P0 | 2/5 | 3/5 | 125 | 198,949 | 1,937 | 40,960 |
| P1 | 0/5 | 5/5 | 160 | 251,876 | 2,488 | 56,320 |
| P2 | 1/5 | 4/5 | 132 | 267,460 | 2,083 | 95,872 |
| **Total** | **3/15** | **12/15** | **417** | **718,285** | **6,508** | **193,152** |

The usage artifacts report `0.0551648 CNY` in accounted costs across the run. This is not a complete billing claim: several per-episode usage files have no accounted cost because provider pricing/usage fields were incomplete. The exact per-call telemetry remains in each `usage.json` and `model_events.jsonl`.

## P2 history-interface audit

The saved P2 actor inputs contain `interaction_history` and do not contain `executed_action_history` or `action_observation_history`. P0/P1 inputs retain the actions-only field. This confirms that the intended interface intervention was present in the actual model-visible inputs, rather than only in run configuration.

## Interpretation limits

This five-task set is a development diagnostic, not an independent reliability gate. The outcomes do not establish that K* v2b is better or worse in general, that raw observation history improves the actor, or that any memory method is effective.

The paired mechanical result is mixed and should be reviewed from the raw traces:

* P0 succeeded on Laptop and Apple; P1 succeeded on neither of those tasks.
* P2 recovered the Laptop task in four steps but did not recover the transformation tasks.
* All three variants reached the step cap on SoapBar and both cool tasks.
* There were zero invalid action-index events and zero carrier/API failures in the completed run.

The result therefore preserves useful negative evidence for the next manual D0/P0/P1/P2 trajectory comparison, but it does not isolate a model capability effect from K* v2b or interaction-history effects. In particular, P0 vs P1 isolates the K* change under actions-only history, P1 vs P2 isolates the history representation under v2b, and P0 vs P2 combines both changes.

## Stop conditions respected

This cycle did not run:

* fresh Gate B1-R;
* a second actor;
* B2 or B3;
* source-H generation/freeze;
* Phase 1A targets;
* prompt tuning, semantic phase/controller logic, retrieval, Stage 1, or longitudinal memory.

The raw trajectories are retained locally for researcher review. No actor-admission status or canonical K* promotion was performed.
