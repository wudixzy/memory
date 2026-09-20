# 83. Phase 1A Controlled Targeting Fast-Track Plan

> Branch: `exp/minimal-exploratory-memory-validation`
> Baseline: `bd4541698f37639e9a29a3e79543cda56609c047`
> Status: researcher-approved protocol reset after S1C
> Goal: stop actor micro-optimization and obtain the first direct C3-vs-C2 targeting-value evidence.

## 1. Why this reset exists

The S1C development verdict was:

```text
STOP_CURRENT_MINIMALIST_ACTOR_FORMULATION
```

The old stepwise autonomous actor has now been tested against replay, K* wording,
history representation, a stronger same-family model, and strict structured output.
The remaining failures are dominated by task-execution noise that is not the Phase 1A
scientific variable.

No further actor micro-experiments are authorized.

Phase 1A asks one narrow question:

> Does history-derived targeted exploration locate/acquire the requested object more
> effectively than a fair structured generic exploration policy on the frozen
> receptacle-search target distribution?

This plan changes the measurement instrument, not the full memory method.
Established Memory in the full method may still contain procedure/tool/recovery/
strategy knowledge. Phase 1A only isolates the receptacle-search targeting function.

## 2. Historical evidence remains valid but is no longer a blocker

Keep docs/67–82 and all actor-development artifacts unchanged as historical/negative
evidence.

Do not:

- promote the old actor manifest;
- weaken the old Phase 1 runner's pending-actor fail-closed checks;
- rerun Gate B1/B1-R;
- create S2/P4/P5 actor variants.

Implement a separately versioned protocol and runner:

```text
phase1a-controlled-targeting-v2
```

The untouched 12-task B1-R reservation remains sealed for possible later robustness
work. It is not a prerequisite for this controlled Phase 1A run.

## 3. Controlled Targeting Actor

The new measurement instrument has two layers.

### 3.1 Search selector — the only online policy decision

The selector receives only public, condition-symmetric information:

- parsed public task target type;
- current public observation;
- remaining public candidate receptacles;
- inspected-candidate ledger with raw public observations;
- the same canonical established search guidance K*;
- exactly one exploration policy:
  - C2: frozen generic H;
  - C3: frozen history-derived H.

The selector outputs only:

```json
{"candidate_index": <legal index>}
```

Use one frozen model/config for both arms. Default choice for this protocol:

```text
provider: dashscope
model: qwen3.8-max
thinking: false
temperature: 0
output: strict dynamic JSON schema
```

The candidate index schema must be rebuilt from the exact current remaining candidate
list. No retry, clamp, semantic repair, fallback model, or condition-specific prompt.

### 3.2 Shared deterministic executor

The executor is identical for C2 and C3 and uses public carrier facts only.

For one selected candidate:

1. execute the exact admissible `go to <candidate>` action;
2. inspect the returned public observation;
3. if the candidate is closed and exact `open <candidate>` is admissible, execute it;
4. inspect the returned public observation;
5. if an exact requested target object is publicly visible and the matching
   `take <object> from <candidate>` action is admissible, execute it;
6. mark the candidate inspected and record the raw public result.

The executor never:

- chooses which candidate to inspect;
- takes a non-target object;
- uses hidden placement/PDDL/expert plans/evaluator labels;
- infers a target from semantic similarity such as soapbar -> soapbottle;
- changes behavior by C2/C3 condition.

If the target is already publicly visible before a selector call, mechanically acquire
the exact target without spending a candidate-probe decision.

## 4. Public task parser and local ledger

Implement a deterministic parser over the public ALFWorld task instruction sufficient
for the frozen Phase 1A families. It may extract:

```text
target_object_type
downstream operation/destination metadata for logging
```

Phase 1A targeting stops at successful target acquisition, so downstream clean/heat/
cool/place execution is not part of the primary outcome.

Maintain an episode-local public ledger:

```text
target_object_type
remaining_candidates
inspected_candidates
raw observations per inspected candidate
target_visible
target_acquired
environment actions
```

This ledger is execution state, not persistent memory.

## 5. Candidate set and probe budget

Derive candidates only from public admissible `go to <entity>` actions and public
entity/receptacle facts.

Freeze the controlled probe budget to:

```text
max_candidate_probes = 2
```

This inherits the previously frozen Phase 1A intent of at most two local candidate
visits, but expresses the budget at the controlled selector's semantic unit rather
than raw environment action count.

C2 and C3 use the identical budget.

A candidate probe may contain the deterministic navigation/open/take actions required
to inspect that selected candidate. These environment actions are logged but do not
create extra selector decisions.

## 6. Primary experiment arms

The fast-track first pass runs only:

```text
C2 = canonical K* + fair structured generic exploration H
C3 = canonical K* + history-derived targeted H
```

C1 is deferred, not deleted. Run it only if C3-vs-C2 produces a signal worth
decomposing into generic-exploration versus established-only effects.

Do not change the frozen C2 scientific principle. Adapt its surface representation only
as required by the new selector interface; it must remain generic, structured,
history-free, and outcome-blind.

## 7. Primary outcomes

The scientific unit is the unique target task, n = 20.

Primary outcomes:

1. `target_acquired_within_probe_budget` (binary);
2. `candidate_probes_to_acquisition` (1, 2, or not acquired within budget);
3. paired C3-vs-C2 win/tie/loss derived from acquisition first, then fewer candidate
   probes.

Secondary telemetry:

- environment actions to acquisition;
- selector calls;
- token/cost;
- chosen candidate sequence;
- target location evidence as observed publicly during execution.

Full ALFWorld task success is not a Phase 1A primary metric in this controlled run.

## 8. Source -> B/C -> H

Before target execution, generate real source-derived H from the existing frozen Source
5 reservation.

### 8.1 Source histories

Do not use the retired autonomous actor.

Generate each source history with a deterministic canonical-K* incumbent search executor
using public observations/actions only. The existing Source 5 are simple pick-and-place
tasks; after exact target acquisition, mechanically complete the public destination
placement so B receives a real completed source trajectory.

No hidden placement/oracle/expert plan is allowed.

### 8.2 B/C

Reuse the already validated B/C responsibility boundary and prompts. Do not redesign the
method in this cycle.

Before paid B/C calls, fix the outstanding provenance invariant:

- B/C artifacts must carry mandatory `source_task_id`, source seed/history identity,
  and hashes sufficient for `freeze_source_h_entry()` to establish referential binding.

If live C narrows applicability relative to the currently frozen public Phase 1A
contract, do not silently broaden it after target outcomes. Either reject that H from
this pilot or freeze a public-only narrower applicability contract before any target
execution.

Run B/C once per Source task under one frozen offline model config.

Preserve:

- B=NONE;
- C=NONE;
- rejected/non-applicable H.

Do not replace a source post hoc merely to obtain useful H.

If zero live H entries survive, STOP and report negative source evidence. Do not run
targets.

If >=1 live same-family H survives, freeze the source-H manifest before targets.

## 9. Target assignment and paired execution

Keep the existing 20-target public-only Target partition unchanged.

Assign frozen same-family H using the existing outcome-blind deterministic assignment.
Do not inspect target outcomes when assigning H.

For each target:

1. instantiate one frozen replay specification;
2. instantiate paired C2/C3 episodes from that same spec;
3. verify actual pairing before selector calls;
4. run one C2 and one C3 controlled probe;
5. no repetitions in the first pass.

Total first-pass target executions:

```text
20 scientific target units
x 2 arms
x 1 execution
= 40 controlled episodes
```

Do not add C1 or repetitions before reviewing this signal.

## 10. Minimal implementation/readiness checks

This reset explicitly rejects another long feasibility-test ladder.

Allowed before paid calls:

- focused unit tests for parser/ledger/executor;
- no-model replay/pairing test;
- fake-selector test proving C2/C3 differ only in H;
- leakage test;
- structured-output candidate-enum test;
- one no-model/synthetic mechanical smoke.

Not authorized:

- paid actor pilot;
- new actor reliability gate;
- model sweep;
- prompt A/B test;
- K*/history variants;
- per-task tuning.

After these checks, commit/push one immutable transition and proceed directly to Source
B/C/H and then the 20-target C2/C3 run.

## 11. Analysis and stop rule

First-pass report must emphasize paired target units, not episode count.

Report:

- C2/C3 acquisition counts;
- paired win/tie/loss;
- paired candidate-probe differences;
- failure/abstention cases;
- H/source clustering and which H was assigned to which targets;
- complete negative evidence.

Do not over-interpret n=20.

Decision after first pass:

- clear favorable C3 signal -> add C1/repetitions/independent robustness as the next
  scientific step;
- no or adverse signal -> inspect H quality / hypothesis itself before adding system
  complexity;
- implementation failure -> fix only the blocking bug, not actor quality generally.

## 12. Forbidden scope

Until the first C2/C3 targeting result is reviewed, do not:

- run B1-R;
- revive the autonomous actor;
- add a second selector model;
- change K*;
- change history representation;
- implement Stage1/A/native cold start;
- run B2/B3 beyond the Source->B/C/H work required here;
- run Phase 2+;
- resample Source or Target;
- use hidden/evaluator information.

The next meaningful milestone is not another feasibility result.

It is:

```text
first real paired C3-vs-C2 targeting-value result on the frozen 20 targets
```
