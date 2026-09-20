# Phase 1A Stronger Actor Development Diagnostic (S1)

## Scope

This was one development diagnostic, not an actor-admission gate and not a
Phase 1A target experiment. The only scientific intervention was the actor
model:

```text
transition commit: 4c3d413266e978007a6fbeb6e2ab895f240c0c68
execution HEAD:    4c3d413266e978007a6fbeb6e2ab895f240c0c68
```

| Component | Saved P0 reference | S1 |
| --- | --- | --- |
| carrier/runtime | ALFWorld TextWorld, pinned replay | identical |
| K* | canonical v1 | canonical v1 |
| model-visible history | `actions_only` | `actions_only` |
| prompt | `actor_action_index_probe_runtime_v1` | identical |
| temperature | `0` | `0` |
| thinking | `false` | `false` |
| step cap | `32` | `32` |
| action interface | zero-based `action_index` | identical |
| model | `qwen3.8-flash` | `qwen3.8-max` |

The S1 candidate was frozen before its first task call in:

```text
experiments/exploratory_memory_mvp/cases/phase1_stronger_actor_manifest.json
manifest_sha256: 4d0204f62d5c42c6174066067561beceec18ac3514ff088e1bf5e8fc92a186d5
actor_manifest_sha256: c381b6d0ad70c2f1d40ca8345a6300d44aed8aae26ab88d90a133be6960547f2
```

`qwen3.8-max` was selected as one public DashScope Max-tier candidate in the
same Qwen family, not from a task outcome. The selection reference is the
[official qwen3.8-max Model Studio page](https://help.aliyun.com/en/model-studio/qwen3-8-max).
The candidate remains
`candidate_pending_independent_reliability_gate`.

## Replay and parity

The runner loaded the saved P0 artifacts from:

```text
artifacts/exploratory_memory_mvp/paired-actor-stack-p0-p1-p2-20260920-359e08e-rerun1
```

Before creating a model client, it validated all five tasks against their
stored `replay_spec.json`, task/seed identity, saved P0 public initial
fingerprint, canonical K* digest, actions-only history, prompt/runtime fields,
and action-index interface. It then instantiated the actual S1 episode from
the saved replay specification and wrote a valid P0-reference/S1 pairing proof.

All five pairing proofs were valid. No P0 episode was rerun and no task was
retried after a scientific failure.

S1 runtime root:

```text
artifacts/exploratory_memory_mvp/stronger-actor-s1-qwen38max-20260920-4c3d413
```

The root retains `run_metadata.json`, `preflight_summary.json`, the frozen
manifest/task snapshots, `trajectory_manifest.json`, and
`stronger_actor_diagnostic_summary.json`. Every task directory retains:

```text
replay_spec.json
pairing_proof.json
paired_initial_states.json
preflight.json
S1/initial_state.json
S1/run_config.json
S1/actor_input.json and actor_prompt.json
S1/steps/*/{actor_input,actor_prompt,actor_raw_response,actor_parsed}.json
S1/steps/*/{action_validation,environment_result,step,usage}.json
S1/execution.json
S1/episode_summary.json
S1/usage.json and model_events.jsonl
```

The runtime artifacts are ignored by the repository artifact policy but remain
available locally at the exact path above for trajectory review.

## P0 versus S1

`won` and step counts are mechanical carrier results.
`failed_invalid_action_index` is an actor-interface failure, not a carrier
pairing failure.

| task | P0 result | S1 result | pairing | S1 interpretation |
| --- | --- | --- | --- | --- |
| Laptop → Desk | won, 11 steps, 0 invalid | won, 4 steps, 0 invalid | valid | completion preserved and shorter on this one case |
| SoapBar → Cabinet | step cap, 32, 0 invalid | step cap, 32, 0 invalid | valid | same coarse failure; S1 still drifted into a hand-towel interaction loop after acquiring `soapbottle_3` |
| Apple → Fridge | won, 18, 0 invalid | step cap, 32, 0 invalid | valid | regression on this paired development case; S1 repeatedly inspected/looked after the heat sequence and did not place the apple |
| Mug → Shelf | step cap, 32, 0 invalid | won, 7, 0 invalid | valid | clear improvement on this one cool task |
| Mug → CoffeeMachine | step cap, 32, 0 invalid | invalid at action call 4 after 3 executed steps | valid | no completion; the model returned `action_index: 57` while the current admissible list had indices `0..56` |

The exact task artifact directories are:

```text
tasks/000_db485ebd50e7/S1  Laptop → Desk
tasks/001_4d0e4849f544/S1  SoapBar → Cabinet
tasks/002_9fa5d3902fe0/S1  Apple → Fridge
tasks/003_a04b6f263f6d/S1  Mug → Shelf
tasks/004_6cf8b7e81791/S1  Mug → CoffeeMachine
```

The CoffeeMachine invalid response and complete admissible list are in:

```text
tasks/004_6cf8b7e81791/S1/steps/004/actor_raw_response.json
tasks/004_6cf8b7e81791/S1/steps/004/actor_parsed.json
tasks/004_6cf8b7e81791/S1/steps/004/action_validation.json
tasks/004_6cf8b7e81791/S1/steps/004/error.json
```

## Mechanical aggregate

```text
episodes:              5
successes:             2/5
step-cap failures:     2/5
invalid action steps:  1
valid pairings:        5/5
model calls:           79
input tokens:          119,875
output tokens:         1,044
cached input tokens:   17,408
```

The existing MVP usage renderer labels its per-call estimate with the
qwen3.8-flash pricing basis, so its raw aggregate field (`0.0756318 CNY`) is
not a valid qwen3.8-max cost estimate. For review, the token totals above
give a separate Beijing list-price planning estimate of approximately
`1.2933 CNY`, using `12 CNY / 1M` uncached input, `1.5 CNY / 1M` cached input,
and `36 CNY / 1M` output as listed on the official qwen3.8-max page. This is
not a provider-billed amount; the raw per-call usage remains in each
`usage.json`.

## Development selection rule

The pre-registered development heuristic was:

```text
strong improvement:
  success >= 4/5
  invalid action index = 0
  at least 2 wins among Apple / Shelf / CoffeeMachine

3/5 or mixed behavior: RESEARCHER_REVIEW_REQUIRED
<=2/5: insufficient evidence to spend a fresh Gate B1-R
```

S1 produced `2/5` successes, one invalid action step, and one win among the
three key diagnostic tasks. The mechanical development verdict is therefore:

```text
INSUFFICIENT_EVIDENCE_TO_SPEND_FRESH_GATE_B1_R
```

This is not a new admission result. The committed actor manifest was not
changed and no actor was promoted to `passed_independent_reliability_gate`.

## Negative evidence and interpretation

The stronger model did not provide a clean stack-level rescue in this five-task
set. It preserved a fast Laptop success and repaired the Shelf cool task, but
it regressed the previously successful Apple task, did not repair SoapBar,
and produced an invalid action index on CoffeeMachine. Thus the result is
mixed rather than a reliable model-capability attribution. The unchanged
K*/prompt/history stack means S1 is useful as a diagnostic observation, but it
does not isolate whether the remaining transformation/search failures are
model capability, carrier/task interaction, or stack reliability.

No second model was tested. No prompt, K*, history mode, step cap, task
membership, B/C/H/A component, Gate B1-R, B2/B3, or Phase 1A target was
changed or run.

## Handoff

The next decision is researcher review. If a final actor stack is changed
after this development evidence, the old Gate B1 and this S1 run must remain
development/negative evidence; a fresh independent in-domain actor gate must
be frozen and run before any Phase 1A target matrix.
