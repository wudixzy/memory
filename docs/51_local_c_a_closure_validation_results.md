# Local C transfer and A closure validation

Date: 2026-09-16
Branch: `exp/minimal-exploratory-memory-validation`
Carrier: ALFWorld TextWorld
Model: DashScope `qwen3.8-flash`, `enable_thinking=false`, temperature `0`

This is a small mechanism validation. It is not evidence that the complete
persistent-memory method works or that the observed step counts generalize.

## 1. Scope and frozen components

B was not changed or rerun. The frozen corrected B artifacts from
`experiment_a-qwen38-b-boundary-20260916/b` were used. The validation chain was:

```text
frozen B
  -> manually localized C packet
  -> source H
  -> different, manually scope-matched target
  -> matched stepwise E0/E1
  -> public evidence package
  -> minimal A reconciliation
```

The existing one-action actor, current admissibility checks, and one-shot
runtime lifecycle were retained. No Stage 1, retrieval, graph memory, or
automatic semantic grader was added.

All model commands removed `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY` and their
lower-case variants, set `NO_PROXY=*`, and used the direct DashScope transport.

## 2. Local C boundary

The old C package included a broad `current_trajectory_context`. The new C
package used for the three source calls was:

```json
{
  "b_diagnosis": "frozen B OPEN result",
  "current_task": {
    "task_id": "...",
    "seed": 42,
    "instruction": "visible task instruction"
  },
  "local_state_and_evidence": {
    "entry_state": {
      "observation": "source entry public observation",
      "admissible_actions": ["current source-entry actions"],
      "won": false
    },
    "public_evidence": [
      "manually reviewed facts needed to instantiate the local contract"
    ]
  },
  "pre_update_established_memories": ["public memory snapshot"],
  "real_capabilities": {
    "entry_state_capabilities": "entry observation and current actions",
    "historical_capability_vocabulary": "carrier schemas plus entry vocabulary"
  }
}
```

The complete source trajectory and its later observations were not passed as a
C field. B's already-generated diagnosis can of course describe the incumbent
segment because B legitimately saw the completed source trajectory; C was told
not to copy such source-specific descriptions into future H fields. The target
task/state/outcome, pair review notes, and evaluator/oracle fields were not in
the C package. The local packets were directly written for the three source
cases in `cases/local_c_packets.json`; no trajectory window or semantic
segmenter was used. A full scan of the prepared C inputs and prompts found no
target pair metadata or evaluator-only data. The word `oracle` in the prompt
appears only in instructions forbidding its use, not as a value.

The pre-payment audit artifacts are under:

```text
artifacts/exploratory_memory_mvp/experiment_c-qwen38-local-20260916-v3-audit/
```

## 3. C output and H representation

C now returns a future-facing `probe_spec` and a separate source-grounding
record. The source-grounding record contains the exact source entry action for
creation-time mechanical validation. It is not sent to a future target actor.
The target actor receives only:

```json
{
  "type": "exploratory",
  "scope": "future scope",
  "hypothesis": "local comparison hypothesis",
  "guidance": "one-shot guidance",
  "probe_policy": {
    "local_function": "...",
    "realization_pattern": "abstract local realization pattern",
    "capability_requirements": ["..."],
    "adaptive_policy": "react to target observations",
    "evidence_goal": "...",
    "stop_conditions": ["..."],
    "required_downstream_state": "..."
  }
}
```

There is no future action list. In all three source results, the future-facing
projection contained no source entity IDs such as `dresser_1`, `desk_1`, or
`countertop_1`; those appeared only in source-grounding/provenance fields when
needed. All three returned `CREATE`, and all three source entry actions passed
the mechanical current-admissibility check.

| source | C | source entry grounding | future H review |
|---|---|---|---|
| P001 AlarmClock | CREATE | legal `go to dresser_1` | abstract likely-receptacle prioritization; not used for transfer because its object-association policy was less general |
| P002 Pencil | CREATE | legal `go to desk_1` | reusable open-surface-first search before closed-container fallback; used below |
| P005 SoapBottle-417 | CREATE | legal `go to countertop_1` | reusable open-access-surface-first search before closed-container fallback; used twice below |

Direct review judged the P002 and P005 H policies concrete enough to test on a
different task without treating a source location as the future answer. P001
was retained as a local-C result but not selected for a transfer pair.

## 4. Manually selected source -> different-target pairs

The pair file is `cases/transfer_pairs.json`. Its `review_only` section is
researcher/evaluator-side metadata and is never copied into C, H, actor, or A
inputs. It records why the target was selected; target hidden location was
used only for selecting a clean positive/negative validation case.

| pair | source H | different target | scope-match review | intended evidence |
|---|---|---|---|---|
| `p002-pencil-to-laptop-306` | P002 open-surface-first | Laptop → Desk, trial `...075009_810389` | hidden-object pick-and-place; mixed open/closed receptacles; same locate-before-acquisition and downstream placement contract | positive candidate: target object is on an open surface |
| `p005-soapbottle-to-spraybottle-426` | P005 surface-first | SprayBottle → Toilet, trial `...155225_439006` | different bathroom pick-and-place; same hidden-object search and placement contract; open surfaces and closed containers | positive: target is on a countertop |
| `p005-soapbottle-to-soapbottle-414` | P005 surface-first | SoapBottle → Cabinet, trial `...110224_056978` | different bathroom pick-and-place; same local search/placement contract | negative: first countertop/sink probe does not expose the requested object; fallback is required |

The source C/H artifacts were created before any target episode was run. The
target H actor views contain neither `review_only` metadata nor source
grounding. The target A inputs also contain none of the pair review fields.

## 5. Target E0/E1 stepwise results

Every pair had matching target initial public observation and admissible action
lists. Every actor call returned one action, and every selected action passed
the exact current admissibility check before execution.

### P002 -> Laptop

```text
E0: desk -> drawer_1/open -> drawer_2/open -> drawer_3/open
    -> drawer_4/open -> drawer_5/open -> garbagecan -> bed
    -> take laptop -> desk -> put; 16 steps, won

E1: desk -> shelf -> desk -> shelf -> ...; 24 steps, step cap, not won
```

E1 activated H and executed a legal target-grounded entry (`go to desk_1`).
The actor then repeatedly revisited two open surfaces and never reached the
bed or an explicit fallback. The H policy said to move to an unvisited open
surface, but the actor did not maintain that semantic state reliably. This is
an online probe-control/termination failure, not an action-legality failure.

### P005 -> SprayBottle

```text
E0: countertop -> take spraybottle -> toilet -> put; 4 steps, won
E1: countertop -> take spraybottle -> toilet -> put; 4 steps, won
```

E1 activated the source-generated H, grounded its first action in the target
admissible set, found the requested object on the countertop, returned
`EVIDENCE_OBTAINED` (semantically `PROBE_EVIDENCE_READY`), removed runtime H,
and continued the original task. E0 independently chose the same direct route,
so this pair is mechanism/authority evidence, not a clean causal cost
contrast.

### P005 -> SoapBottle-414

```text
E0: 32-step cap, not won
E1: countertop -> examine countertop -> cabinet_1 -> open cabinet_1
    -> normal actor search/revisits; 32-step cap, not won
```

Evaluator-side replay confirmed that the first target surface showed a
`soapbar`, not the requested `soapbottle`; that hidden classification is not
in any model input. E1 nevertheless produced a useful negative probe trace:
the surface-first attempt did not expose the target, then emitted
`EVIDENCE_OBTAINED` and removed runtime H. The actor did not complete the
fallback search. E0 also failed to complete this difficult target under the
same step cap, so the pair demonstrates negative evidence and lifecycle
handling but not a task-success comparison.

### Online mechanism table

| pair | H visible | activated | target-time entry legal | evidence-ready status | H stopped locally | normal task resumed | completed |
|---|---:|---:|---:|---:|---:|---:|---:|
| P002 → Laptop | yes | yes | yes | no; loop hit cap | no | no | no |
| P005 → SprayBottle | yes | yes | yes | yes | yes | yes | yes |
| P005 → SoapBottle-414 | yes | yes | yes | yes; negative observation | yes | attempted, but failed to finish | no |

The consumed H lifecycle was correct in all E1 runs: persistent status changed
from `active` to `consumed` on activation; runtime H remained visible during
the active probe and was absent after `EVIDENCE_OBTAINED`. It was never
reactivated by A.

## 6. A input boundary and outputs

After each target episode, A received the following public package:

```json
{
  "pre_update_established_memories": "snapshot",
  "consumed_exploratory_memory": "full source H, including creation provenance",
  "target_task": {"task_id": "...", "seed": 42, "instruction": "..."},
  "target_trajectory": "public E1 observations/actions/outcomes",
  "probe_evidence": "public probe step records and status history",
  "environment_outcome": {
    "e1": "public summary",
    "e0_reference": "matched public baseline summary"
  },
  "provenance": ["source C", "target task", "target pair"]
}
```

No `review_only`, target classification, oracle location/outcome, evaluator
rationale, or researcher expected conclusion entered an A input. The A runner
also rejects those fields mechanically and preserves raw/parsed/error
artifacts.

| pair | A decision | direct review |
|---|---|---|
| P002 → Laptop | `NO_CHANGE` | Evidence is a failed/looping probe, not a test of the open-surface hypothesis; A correctly preserves uncertainty and identifies the control failure. |
| P005 → SprayBottle | `UPDATE`, `SPECIALIZE` | Adds a scope-limited open-surface-before-closed-container lesson supported by the target trace; does not claim universal optimality. E0 chose the same route, so the update is useful feasibility/comparative evidence but not a strong causal improvement claim. |
| P005 → SoapBottle-414 | `NO_CHANGE` | Binds the negative surface observation to this target and preserves uncertainty about other object types/layouts; does not reject the entire surface-first family. |

The stored post-update files are deliberately auditable proposals rather than
a production memory-store mutation. They include the pre-update snapshot,
A-selected updates, unresolved comparisons, and
`exploratory_memory_reactivated: false`.

## 7. Failure localization

| component | finding |
|---|---|
| local C boundary | supported on these three source cases: C operated without the completed source trajectory and produced concrete future policies |
| H transfer/source specificity | P002/P005 were sufficiently abstract for target injection; P001 was less general and was not transferred |
| C target binding | no clear binding failure in the selected source outputs |
| C entry grounding | 3/3 source entries legal; all target E1 first actions legal in their current target state |
| online exploratory-memory authority | no authority-ignore failure; all 3 E1 actors activated H |
| stepwise legality | 100% of the executed actor actions passed exact current-state admissibility |
| probe termination/fallback | current bottleneck: P002 looped; negative P005 did not finish fallback; valid stop status did not guarantee successful continuation |
| A evidence binding | supported qualitatively: one scope-limited update and two conservative `NO_CHANGE` decisions matched the public traces |

The strongest remaining failure is online stepwise probe control after the
first local observation: the actor needs to avoid revisiting already tested
locations, recognize when the local comparison is ready, and resume the task
without losing the downstream contract. This is not evidence against B, which
was frozen, and it is not evidence that the source/target scope match itself
was invalid.

## 8. Conclusion and next recommendation

Supported in this cycle:

1. A manually localized C boundary can produce an H whose future-facing policy
   is not a cached source action/entity answer.
2. The same H can be injected into a different, researcher-confirmed matching
   ALFWorld task, become behaviorally authoritative, and be grounded against
   target-current affordances.
3. A can consume public target evidence and make an evidence-bound,
   scope-limited update or conservatively make no update.

Not supported yet:

1. reliable positive transfer across target layouts;
2. negative-probe fallback and task continuation under actor control;
3. any general performance or method-level claim. E0 often independently
   selected the same route, and two targets hit the step cap.

This MVP is **not ready for broader evaluation**. The next cycle should isolate
the single remaining mechanism issue—robust local probe termination/fallback
and continuation—using a very small direct-review set. It should not add B
heuristics, automatic semantic state planners, retrieval, or large benchmark
sweeps.

## 9. Artifacts and telemetry

Source C run:

```text
artifacts/exploratory_memory_mvp/experiment_c-qwen38-local-20260916-v3/
```

Transfer/A runs:

```text
artifacts/exploratory_memory_mvp/transfer-p002-to-laptop-qwen38-20260916-v2/
artifacts/exploratory_memory_mvp/transfer-p005-to-spraybottle-qwen38-20260916/
artifacts/exploratory_memory_mvp/transfer-p005-to-soapbottle-414-qwen38-20260916/
```

Paid call totals were 3 C calls, 112 actor calls, and 3 A calls: 118 calls,
approximately 189,398 input tokens and 4,864 output tokens. The local C run's
uncached estimate was CNY 0.0129131; target runs used the published Qwen3.8
uncached estimate where available. The negative pair included cached input
tokens, so its complete cost is not treated as known.

Focused MVP tests, Ruff, compilation, and `git diff --check` were run after the
implementation changes. The full repository suite still has the two known
AppWorld setup/data errors documented in `docs/36_appworld_final_sanity_probe_results.md`.
