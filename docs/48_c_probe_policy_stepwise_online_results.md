# C probe policy and stepwise online retest

Date: 2026-09-16
Branch: `exp/minimal-exploratory-memory-validation`
Carrier: ALFWorld TextWorld
C cases: the existing five P cases
Online pairs: P001, P002, and P005
Model: DashScope `qwen3.8-flash`, `enable_thinking=false`, temperature `0`

This report tests the C representation and online execution mechanism only.
It is not evidence that the full persistent-memory method works.

## 1. Scope and frozen inputs

B was not changed or rerun. The existing corrected-B artifacts from
`experiment_a-qwen38-b-boundary-20260916/b` were reused. That run had already
produced `OPEN` for all five P cases. The new run generated C inputs by
mechanically converting the old ignored capability artifact to the new split
representation; no hidden evaluator fields were used.

All model calls were made with proxy variables removed, `NO_PROXY=*`, and the
transport's empty proxy handler. The C run made five model calls. The three
online pairs made 45 one-action actor calls in total.

## 2. C input/interface correction

The old C package was effectively:

```json
{
  "b_diagnosis": {"...": "..."},
  "established_memories": [{"...": "..."}],
  "real_capabilities": {
    "currently_admissible": ["..."],
    "observed_exact_actions": ["..."],
    "observed_entity_ids": ["..."]
  }
}
```

It did not explicitly provide the task instruction, the current public state,
or the incumbent trajectory context. Its capability fields also made a
cross-state union look like a sequence-executability guarantee.

The new C package is:

```json
{
  "b_diagnosis": {
    "decision": "OPEN",
    "incumbent_segment": "...",
    "evidence_status": {"...": "..."},
    "functional_contract": {"...": "..."},
    "warrant": "..."
  },
  "current_task": {
    "task_id": "...",
    "seed": 42,
    "instruction": "put ..."
  },
  "current_public_state": {
    "observation": "...",
    "admissible_actions": ["..."],
    "won": false
  },
  "current_trajectory_context": {
    "initial": {"...": "..."},
    "steps": [{"...": "..."}],
    "final": {"...": "..."}
  },
  "pre_update_established_memories": [{"...": "..."}],
  "real_capabilities": {
    "entry_state_capabilities": {
      "observation": "...",
      "currently_admissible_actions": ["..."],
      "currently_visible_or_referenced_entities": ["..."]
    },
    "historical_capability_vocabulary": {
      "action_schema": [{"...": "..."}],
      "action_names": ["..."],
      "observed_exact_actions": ["..."],
      "observed_entity_ids": ["..."]
    }
  }
}
```

`current_task.instruction` is mechanically extracted from the already public
ALFWorld initial observation. It is formatting, not a semantic case rule.
`entry_state_capabilities` is the only source used to validate C's first
action. `historical_capability_vocabulary` is reference evidence only; it does
not assert that a composed future sequence is executable.

The C package and prompt were prepared before model clients were created. The
representation audit covered all five P cases. A full scan of their C input
and prompt artifacts found no `case_type`, evaluator notes, expected decision,
oracle action/outcome, or hidden answer. The capability evidence was present
only because it is an intended C input, and was split into entry facts and
historical vocabulary.

Artifacts:

```text
artifacts/exploratory_memory_mvp/c-probe-policy-audit-20260916-v2/
artifacts/exploratory_memory_mvp/experiment_c-qwen38-probe-policy-20260916/
```

## 3. Probe-policy output correction

The old C contract required an open-loop action list:

```json
{
  "decision": "CREATE",
  "grounded_realization": {"actions": ["a1", "a2", "a3"]}
}
```

The new contract has one grounded entry action and an adaptive local policy:

```json
{
  "decision": "CREATE",
  "type": "exploratory",
  "scope": "...",
  "hypothesis": "...",
  "guidance": "...",
  "probe_spec": {
    "local_function": "...",
    "grounded_start": {
      "action": "exact currently admissible action",
      "why_grounded": "..."
    },
    "adaptive_policy": "react to the next real observation",
    "evidence_goal": "...",
    "stop_conditions": ["...", "..."],
    "required_downstream_state": "..."
  },
  "reason": "..."
}
```

There is no future `actions` list in the new schema. C may return
`{"decision":"NONE"}`. Mechanical validation checks JSON shape, the action
family/entity identity, and exact current admissibility of
`probe_spec.grounded_start.action`; it does not score locality, quality, or
informativeness.

The C prompt explicitly separates the entry-state capability from historical
vocabulary, forbids pre-planning later actions, and assigns future legality to
the online environment loop. It does not show the oracle alternative or
outcome.

## 4. Five-case C retest and direct review

All five responses parsed as `CREATE`; all five first actions passed the
mechanical entry-state check. The following semantic columns are direct review
of the task, C output, public capability evidence, and the real entry step,
not an automatic grader.

| case | C | target binding | contract match | grounded start legal | adaptive, not open-loop | local, not whole-task replan | potentially informative | selected online |
|---|---|---|---|---|---|---|---|---|
| P001 AlarmClock → Desk, 314 | CREATE | yes: alarmclock/dresser/desk | yes; local search contract | yes: `go to dresser_1` | yes | yes | yes; direct source discovery can compare search cost | yes, regression |
| P002 Pencil → Shelf, 310 | CREATE | yes: pencil/desk/shelf | yes; source-first search | yes: `go to desk_1` | yes | yes | yes; desk observation can discriminate local discovery | yes |
| P003 Plate → Dresser, 218 | CREATE | yes: plate/sidetable/dresser | yes; surface-first search | yes: `go to sidetable_1` | yes | yes | yes; positive or negative surface evidence | no, cap of three |
| P004 SoapBottle → Cabinet, 414 | CREATE | yes: soapbottle/countertop/sink/cabinet | yes; targeted surface search with fallback | yes: `go to countertop_1` | yes | yes | yes; absence on surfaces is still a possible negative result | no, weaker negative probe |
| P005 SoapBottle → Cabinet, 417 | CREATE | yes: soapbottle/countertop/cabinet | yes; surface-first search | yes: `go to countertop_1` | yes | yes | yes; direct source discovery can compare search cost | yes |

### P001 regression

The previous open-loop proposal passed a global entity check but failed in the
real state: after `go to dresser_1`, it attempted `open drawer_1`, which was
not admissible there, and used a wrong target instance. The corrected C output
for P001 contains only the legal entry action `go to dresser_1`; its policy
waits for the arrival observation before choosing a take/search action. The
real entry observation exposed both `alarmclock_1` and `alarmclock_2`, so the
new representation did not require C to guess a later object action.

## 5. Stepwise actor implementation

The actor now receives a fresh package for every decision:

```text
current task/instruction
+ latest public observation
+ latest admissible actions
+ established memory
+ short executed-action history
+ exploratory probe policy only in E1 while runtime guidance is active
```

It must return exactly:

```json
{
  "action": "one exact action from current_state.admissible_actions",
  "probe_status": "NOT_ACTIVE | ACTIVE | EVIDENCE_OBTAINED | ABORTED"
}
```

The runner validates the returned action against the current admissible set,
executes exactly one action on a persistent real ALFWorld episode, stores the
new observation/action set, and repeats. Every step has its own input, prompt,
visible response, parsed result, current-action validation, environment
result, and condition-level token/cost event. No open-loop actor action list is
accepted.

The persistent exploratory status starts as `active` in E1. When the actor
first reports `ACTIVE`, `EVIDENCE_OBTAINED`, or `ABORTED`, it becomes
`consumed`. The runtime copy remains in the current episode through `ACTIVE`
steps and is removed only after `EVIDENCE_OBTAINED` or `ABORTED`. It is never
returned to a future active pool.

## 6. Selected E0/E1 pairs

The three selected cases had correct target binding, a legal grounded start,
and a locally meaningful positive probe. Initial public states matched in each
pair. Every one of the 45 actor-selected actions was legal in the current
state; later legality was resolved by the real environment, not by the
historical capability union.

| case | condition | executed trace (compact) | steps | won | probe statuses | memory visible |
|---|---|---|---:|---:|---|---|
| P001 | E0 | desk → drawer1(open/close) → drawer2(open/close) → drawer3(open/close) → drawer4(open/close) → drawer5(open/close) → dresser → take → desk → put | 20 | yes | all `NOT_ACTIVE` | never |
| P001 | E1 | dresser → take alarmclock → desk → put | 4 | yes | `ACTIVE, ACTIVE, EVIDENCE_OBTAINED, NOT_ACTIVE` | steps 1–3 |
| P002 | E0 | desk → take pencil → shelf → put | 4 | yes | all `NOT_ACTIVE` | never |
| P002 | E1 | desk → take pencil → shelf → put | 4 | yes | `ACTIVE, EVIDENCE_OBTAINED, NOT_ACTIVE, NOT_ACTIVE` | steps 1–2 |
| P005 | E0 | cabinet1(open/close) → countertop → take soapbottle → cabinet1(open) → put | 8 | yes | all `NOT_ACTIVE` | never |
| P005 | E1 | countertop → take soapbottle → cabinet1(open) → put | 5 | yes | `ACTIVE, ACTIVE, EVIDENCE_OBTAINED, NOT_ACTIVE, NOT_ACTIVE` | steps 1–3 |

At each E1 step before probe completion, the actor saw the same full probe
policy plus the latest actual state. For example, in P001 the first action was
the C entry action. After the resulting observation showed the alarmclock, the
actor chose the currently admissible take action; after the carried-object
state, it chose the currently admissible destination action. This is adaptive
execution rather than replay of a precomputed sequence.

## 7. Online mechanism result

| case | exploratory memory visible | activated | entry executed | followed adaptively | probe evidence | stopped locally | continued original task | task completed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| P001 | yes | yes | yes | yes | yes: source found before the incumbent-style search | yes, before final placement | yes | yes |
| P002 | yes | yes | yes | yes | yes: desk observation exposed the target; the E0 actor independently made the same source choice | yes, before destination placement | yes | yes |
| P005 | yes | yes | yes | yes | yes: countertop observation exposed the target earlier | yes, before final placement | yes | yes |

P001 and P005 provide a useful paired cost contrast in this small run: E1
completed in 4 and 5 steps versus E0's 20 and 8. P002 verifies probe authority
and continuation but does not provide a clean between-condition cost contrast,
because E0 independently selected the same direct route. The evidence is
therefore mechanism evidence for these traces, not a general performance
estimate.

The three E1 runs show behavioral authority: the actor activated and followed
the exploratory memory in all three cases. There was no authority-ignore
failure, so no E2 diagnostic was run. All three E1 probes reached an explicit
evidence status, runtime guidance was then removed, and the actor completed
the original task.

## 8. Telemetry and artifacts

| stage | calls | input tokens | output tokens | estimated CNY |
|---|---:|---:|---:|---:|
| C | 5 | 42,749 | 2,469 | 0.0408655 |
| E0/E1 actor | 45 | 38,809 | 838 | 0.0333098 |
| total | 50 | 81,558 | 3,307 | 0.0741753 |

The C artifacts are under:

```text
artifacts/exploratory_memory_mvp/experiment_c-qwen38-probe-policy-20260916/
```

The online artifacts are under:

```text
artifacts/exploratory_memory_mvp/online-p001-qwen38-stepwise-20260916/
artifacts/exploratory_memory_mvp/online-p002-qwen38-stepwise-20260916/
artifacts/exploratory_memory_mvp/online-p005-qwen38-stepwise-20260916/
```

All runtime artifacts remain ignored and untracked.

## 9. Failure localization

* **C target binding:** no clear failure in these five outputs. The task
  instruction and public entry observation were sufficient for direct target
  binding in this small set.
* **C entry grounding:** no failure in this run. All five starts were exactly
  current-admissible and executed in a fresh real state.
* **C semantic probe quality:** the old P001 open-loop failure is fixed at the
  representation level. The remaining limitation is that the five semantic
  quality judgments are still direct review; P004 is a weaker negative probe,
  and C's heuristic claims should not be generalized from five cases.
* **Online exploratory-memory authority:** no failure observed. All three E1
  actors activated and followed the memory.
* **Stepwise actor legality/control:** no failure observed. All 45 actions
  passed exact current-state admissibility and were executed one at a time.
* **Task continuation after probe:** no failure observed in the selected
  pairs. All E1 actors removed runtime probe guidance after evidence and
  completed the original task.
* **Evidence ambiguity:** P002's E0 actor independently chose the same route,
  so its pair does not isolate a cost difference. The small sample also cannot
  distinguish whether the shorter E1 traces generalize beyond these fixed
  states.

The best conclusion is that the C/actor representation correction is
mechanically sound and produced credible local probes in these cases. It does
not establish broad C semantic reliability or the effectiveness of the full
persistent-memory method.

## 10. Verification and next recommendation

Focused tests: 13 passed. Ruff, compilation, and `git diff --check` passed.
The full repository suite retains the two known AppWorld setup/data errors
documented in `docs/36_appworld_final_sanity_probe_results.md`; no broad
benchmark sweep was run.

The next cycle should review the saved traces before adding any new mechanism.
The most useful follow-up is a small C-specific semantic review of target
binding, downstream-contract preservation, and negative evidence, followed by
carefully matched cases if that review remains positive. Do not add a
handcrafted transition planner or an automatic semantic probe score. Stage 1,
A reconciliation, and the full persistent-memory loop should remain deferred.
