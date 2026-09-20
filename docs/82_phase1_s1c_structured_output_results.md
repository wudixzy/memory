# Phase 1A S1C Strict Structured-Output Development Diagnostic

## Scope and execution identity

S1C was the final actor-formulation development diagnostic. It was not an
admission gate and it was not a Phase 1A target run. No B1-R, B2, B3, second
model, prompt/K*/history change, or target execution was performed.

The no-model transition was committed and pushed at:

```text
75db5dd448130eab2fc8e7b0358e617cd3243901
exp: prepare strict S1C actor diagnostic
```

The five episodes executed at that same HEAD. The successful protocol-consistent
run is:

```text
artifacts/exploratory_memory_mvp/stronger-actor-s1c-qwen38max-jsonschema-20260920-75db5dd-rerun1
```

An earlier attempt was preserved separately at:

```text
artifacts/exploratory_memory_mvp/stronger-actor-s1c-qwen38max-jsonschema-20260920-75db5dd
```

It made zero model/API calls and failed during the first carrier preflight
because the default Python interpreter lacked the pinned ALFWorld/TextWorld
dependencies. The same preflight succeeded in the repository's
`memory-automanual` Conda environment; this infrastructure-only attempt was
not used as a scientific episode and was not overwritten.

## Frozen stack and intervention

| component | S1C setting |
| --- | --- |
| provider | DashScope-compatible direct transport, proxy variables cleared |
| model | `qwen3.8-max` |
| thinking | `false` |
| temperature | `0` |
| K* | canonical v1 |
| model-visible history | actions-only |
| actor prompt | `actor_action_index_probe_runtime_v1` |
| step cap | `32` |
| action interface | zero-based `action_index` |
| tasks | the same five saved P0 development tasks |
| scientific intervention | strict dynamic structured output only |

The actor manifest remained:

```text
selection_status = candidate_pending_independent_reliability_gate
```

S1C did not promote the actor or change the canonical K*.

At each step the runner built and validated a fresh provider request:

```json
{
  "type": "json_schema",
  "json_schema": {
    "name": "alfworld_actor_action_index_probe",
    "strict": true,
    "schema": {
      "type": "object",
      "properties": {
        "action_index": {"type": "integer", "enum": [0, "...", "N-1"]},
        "probe_status": {
          "type": "string",
          "enum": ["NOT_ACTIVE", "ACTIVE", "EVIDENCE_OBTAINED", "ABORTED"]
        }
      },
      "required": ["action_index", "probe_status"],
      "additionalProperties": false
    }
  }
}
```

The actual enum is the exact integer range for that step's ordered
`current_state.admissible_actions`. Structured-output requests omitted
`max_tokens`. Invalid schema paths, malformed responses, and invalid indices
fail closed; there is no clamping, rewrite, fallback action, or retry.

## Replay and pairing

The runner reused the saved P0 references from:

```text
artifacts/exploratory_memory_mvp/paired-actor-stack-p0-p1-p2-20260920-359e08e-rerun1
```

All five no-model preflights completed before the first S1C transport was
created. Every actual episode used the saved replay specification and matched
the saved P0 public initial fingerprint. Pairing was valid for all five tasks.

| task | replay SHA-256 | public initial fingerprint | pairing |
| --- | --- | --- | --- |
| Laptop → Desk | `fbdc8d9541ac5dbb3aa11507026e9b7d2f51decebfb51ce17f90b925f573ec7d` | `a0027e8b0249344bf81475d15fad3936066547d5da2a07e3560da5f35ea4f840` | valid |
| SoapBar → Cabinet | `d1cb55d4b27cec25b9f3c4a5d8b80427038a4e72dcd9d63578dd8f9a6c58ae4a` | `080e5ab166e57d024e6aca9b97901a22c64319d564df24cdd93d2b0c7f3db74c` | valid |
| Apple → Fridge | `376d0b2f9f3a48f755ca64b3111927df64984c0b5c995a4e36387b4836ed80f2` | `1b981390b4bf797a10629184e82b3c18d396c786684331d6cdbf824c3e7c97b4` | valid |
| Mug → Shelf | `ce8c376643370953f75e6d8678f357db12cf15829e77d2ec51ed4edbed5b35e6` | `747d54ac50ae9a54cef349152a696ea006f6532868d3d07033c37d87c7906aa2` | valid |
| Mug → CoffeeMachine | `364e300c060c7c6d580357a2b9a66846d7ae18e035a97638475268e791d8306a` | `ac8ccfa8e5729e409b371df9b61cff37edba659b5f95a84d03187e61df7c35dc` | valid |

The full preflight evidence is in:

```text
.../preflight_summary.json
.../tasks/*/preflight.json
.../tasks/*/pairing_proof.json
```

## Per-task results

Each path below is relative to the S1C runtime root above. Every task retains
the complete stepwise actor input/prompt, structured-output request, raw and
parsed response, ordered admissible actions, action-index validation, resolved
action, environment result, step record, execution, usage, and model-event
artifacts.

| task | result | steps / cap | invalid action index | structured-output failures | actor calls | artifact |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| Laptop → Desk | won | 4 / 32 | 0 | 0 | 4 | `tasks/000_db485ebd50e7/S1C` |
| SoapBar → Cabinet | step cap, not won | 32 / 32 | 0 | 0 | 32 | `tasks/001_4d0e4849f544/S1C` |
| Apple → Fridge | step cap, not won | 32 / 32 | 0 | 0 | 32 | `tasks/002_9fa5d3902fe0/S1C` |
| Mug → Shelf | won | 12 / 32 | 0 | 0 | 12 | `tasks/003_a04b6f263f6d/S1C` |
| Mug → CoffeeMachine | step cap, not won | 32 / 32 | 0 | 0 | 32 | `tasks/004_6cf8b7e81791/S1C` |

The root trajectory index is:

```text
trajectory_manifest.json
```

## Mechanical output-contract audit

The run contained 112 actor calls across five episodes. A post-run audit found:

```text
dynamic schemas:                 112 / 112
action-index enums matched list: 112 / 112
strict flag true:                112 / 112
max_tokens in structured calls:  0 / 112
invalid structured outputs:      0
invalid action-index steps:      0
post-hoc corrections:            0
pairing-valid episodes:          5 / 5
```

This shows that the strict output path removed the S1 Coffee one-past-end
interface failure in this run. It does not show that the actor selected the
right semantic action or completed the task.

## Token and cost telemetry

Aggregate provider-reported usage saved in the runtime is:

```text
model calls:          112
input tokens:         178,003
cached input tokens:   31,744
output tokens:          1,464
renderer estimate:      0.1009373 CNY
```

The existing local renderer uses the qwen3.8-flash planning-pricing basis for
its displayed estimate, so `0.1009373 CNY` is not a provider-billed
qwen3.8-max cost claim. For a rough planning comparison only, applying the
qwen3.8-max list-price basis used in the earlier S1 report (`12 CNY/M`
uncached input, `1.5 CNY/M` cached input, `36 CNY/M` output) gives about
`1.8554 CNY`; the provider billing total was not returned and should not be
treated as exact.

Per-task usage remains in each `S1C/usage.json`, and raw request/response
telemetry remains in each `S1C/model_events.jsonl`.

## Development verdict

The frozen development rule was:

```text
>=4/5 success + 0 invalid + at least 2 of Apple/Shelf/Coffee success
    -> STRONG_IMPROVEMENT
3/5
    -> RESEARCHER_REVIEW_REQUIRED
<=2/5
    -> STOP_CURRENT_MINIMALIST_ACTOR_FORMULATION
```

S1C produced:

```text
success:                 2 / 5
invalid action index:    0
Apple/Shelf/Coffee wins: 1 / 3
development verdict:     STOP_CURRENT_MINIMALIST_ACTOR_FORMULATION
```

The result is not a Gate B1 result and does not justify a fresh independent
gate or a Phase 1A target run.

## S1 comparison and interpretation

| task | S1 | S1C | narrow observation |
| --- | --- | --- | --- |
| Laptop → Desk | won, 4 | won, 4 | completion preserved |
| SoapBar → Cabinet | step cap | step cap | no coarse improvement |
| Apple → Fridge | step cap | step cap | no coarse improvement |
| Mug → Shelf | won, 7 | won, 12 | completion preserved, slower |
| Mug → CoffeeMachine | invalid at call 4 | step cap, no invalid | interface failure removed, semantic completion not recovered |

The cleanest attributable effect is mechanical: S1C prevented the saved S1
`action_index: 57` when the current list ended at index 56. Because S1C then
continued with valid actions but still failed to complete CoffeeMachine, the
structured constraint should not be described as a semantic actor rescue.
The unchanged Apple and SoapBar failures, and the mixed completion profile,
remain negative development evidence about the complete actor stack.

## Scientific boundary and stop

This cycle supports only the following narrow statement:

> On these five replay-paired development episodes, a strict per-step dynamic
> action-index schema made the actor interface fail closed and eliminated the
> observed out-of-range index event, but it did not produce the pre-registered
> strong-improvement development result.

It does not support claims that C3 beats C2, that H is effective, that the
persistent-memory system works, that native cold start works, or that the
actor passed independent reliability admission. The actor manifest remains
pending. Gate B1-R, B2/B3, and all Phase 1A targets remain prohibited pending
researcher review.
