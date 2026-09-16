# Corrected B/C boundary retest

Date: 2026-09-16
Branch: `exp/minimal-exploratory-memory-validation`
Carrier: ALFWorld TextWorld
Cases: 11 curated cases (5 P, 3 N1, 3 N2)
Model: DashScope `qwen3.8-flash`, thinking disabled, temperature 0

This report tests only the corrected B/C interface. It is not evidence that
the full persistent-memory method works.

## 1. Interface correction

The previous B input put the current successful A execution under
`established_memories[].historical_experience`. The corrected public payload
has four separate top-level fields:

```json
{
  "current_task": {"task_id": "...", "seed": 42},
  "current_initial_state": {
    "observation": "...",
    "admissible_actions": ["..."],
    "won": false
  },
  "current_trajectory": {
    "executed_actions": ["..."],
    "steps": ["..."],
    "final": {"won": true, "reward": 1.0}
  },
  "pre_update_established_memories": [
    {
      "memory_id": "...",
      "scope": "...",
      "guidance": "...",
      "prior_comparison_evidence": null
    }
  ]
}
```

`current_trajectory` is the incumbent A execution being diagnosed. The
pre-update memory contains only information established before that execution.
The full carrier capability document remains an artifact for C and is not
included in B's payload or prompt.

The implementation also adds mechanical checks for the four-field shape,
trajectory/memory separation, evaluator leakage, and capability-payload
leakage. `run_b.py` now prepares and audits every B input and prompt before it
creates any model client. The `--prepare-only` mode was used for the
pre-payment representation audit. C's prompt and synthesis logic were not
changed; its input path was adapted from the old memory key to the new
pre-update-memory key.

## 2. Representative old vs. new public input

For the AlarmClock P case, the old shape was structurally similar to:

```json
{
  "current_task_and_state": {
    "task_id": "pick_and_place_simple-AlarmClock-None-Desk-314/...",
    "observation": "...",
    "admissible_actions": ["..."]
  },
  "established_memories": [
    {
      "memory_id": "established-search-listed-order-alarmclock",
      "historical_experience": {
        "executed_actions": ["look", "go to bed_1", "..."],
        "final": {"won": true}
      }
    }
  ]
}
```

The new artifact separates the same information as follows:

```json
{
  "current_task": {
    "task_id": "pick_and_place_simple-AlarmClock-None-Desk-314/...",
    "seed": 42
  },
  "current_initial_state": {
    "observation": "... Your task is to: put a alarmclock in desk.",
    "admissible_actions": ["go to bed_1", "go to dresser_1", "..."],
    "won": false
  },
  "current_trajectory": {
    "executed_actions": [
      "look", "go to bed_1", "...", "go to dresser_1",
      "take alarmclock_2 from dresser_1", "..."
    ],
    "completed_requested_sequence": true,
    "final": {"won": true, "reward": 1.0}
  },
  "pre_update_established_memories": [
    {
      "memory_id": "established-search-listed-order-alarmclock",
      "guidance": "Search visible receptacles in the order presented...",
      "prior_comparison_evidence": null
    }
  ]
}
```

The complete corrected inputs are in the ignored audit artifacts under
`artifacts/exploratory_memory_mvp/b-interface-audit-20260916/` and the main
run artifacts under
`artifacts/exploratory_memory_mvp/experiment_a-qwen38-b-boundary-20260916/`.

## 3. Representation audit before paid calls

The no-model preparation run generated 11 B inputs and 11 B prompts. I
manually inspected:

* P: `alfworld-p-001-alarmclock`;
* N1: `alfworld-n1-001-alarmclock-resolved`;
* N2: `alfworld-n2-001-book-redundant-observation`.

The audit confirmed:

* `current_trajectory` is explicit and separate from
  `pre_update_established_memories`;
* the current trajectory is not serialized as `historical_experience`;
* the oracle alternative and oracle outcome are absent;
* P/N1/N2 labels and evaluator rationale are absent;
* `capabilities.json`, `real_capabilities`, and the full capability fields are
  absent from the B prompt;
* all 11 preparation artifacts had `usage.status: not_started` before paid
  calls.

A full scan of all 22 B input/prompt artifacts for evaluator keys, oracle
fields, `historical_experience`, and capability-document fields returned zero
matches. The evaluator-only `case_definition.json` files remain outside the
model input path.

## 4. Corrected B prompt semantics

The main prompt now defines the boundary directly:

```text
B: decide which incumbent comparison is worth opening.
C: later construct and ground one concrete local test.
```

B is told to make only these judgments:

1. identify a meaningful local incumbent behavior in the completed trajectory;
2. distinguish feasibility evidence from comparative evidence that would close
   the incumbent's preferred/default status;
3. judge whether resolving that comparison could materially change future
   policy under the memory scope.

The prompt explicitly says:

```text
Do not propose, name, ground, verify, or execute a concrete alternative.
Do not require evidence that a concrete alternative already exists.
C will synthesize and ground an alternative only after B returns OPEN.

A successful incumbent establishes feasibility, not comparative superiority.
An alternative being absent from memory is not evidence that the comparison is
resolved.
```

The previous wording that asked B to determine whether supplied evidence
supported a different executable realization was removed. B does not receive
the full `capabilities.json` document.

Both decisions now use an explicit auditable schema:

```json
{
  "decision": "OPEN | NONE",
  "incumbent_segment": "short description or null",
  "evidence_status": {
    "feasibility_support": "short statement",
    "comparative_support": "short statement",
    "policy_relevance": "short statement"
  },
  "functional_contract": {
    "available_state": "...",
    "local_function": "...",
    "required_downstream_state": "...",
    "constraints": ["..."]
  },
  "warrant": "short final justification"
}
```

For `NONE`, the segment and contract may be `null`; the three evidence fields
and the warrant remain required. For `OPEN`, the segment and contract are
required. These are concise visible task judgments, not hidden reasoning.

## 5. Experiment-A B result

The main run made exactly one corrected B call per case. All 11 responses
parsed under the new schema. The case type below is evaluator-side and was not
provided to B.

| case | type | B | incumbent segment summary | comparative-support summary | policy-relevance summary |
|---|---|---|---|---|---|
| AlarmClock → Desk, 314 | P | OPEN | Sequential search through listed receptacles before the dresser | Memory supports the order but gives no evidence it is more efficient or preferred | Reducing repeated empty-container work could change future search policy |
| Pencil → Shelf, 310 | P | OPEN | Opens cabinets 1, 3, 2, and 4 before checking the desk | No evidence justifies checking the desk last | Rigid O(N) search cost could materially affect future policy |
| Plate → Dresser, 218 | P | OPEN | Checks drawers and other surfaces before the sidetable | Exhaustive order works but is not comparatively established | A better order could reduce step count and time |
| SoapBottle → Cabinet, 414 | P | OPEN | Linear search through all listed receptacles | No evidence supports exhaustive search over targeted search | Search cost and efficiency could change future policy |
| SoapBottle → Cabinet, 417 | P | OPEN | Checks cabinets before the countertop | Cabinet-first is feasible but not shown preferred | Location-order policy generalization and cost could change |
| AlarmClock → Desk, 314 | N1 | NONE | — | Existing memory records matched comparative evidence and the preferred route | The policy is already established for this scope |
| SoapBottle → Cabinet, 414 | N1 | NONE | — | Existing memory records the 30-step vs. 6-step comparison | Reopening would not add policy guidance |
| Pencil → Shelf, 310 | N1 | NONE | — | Existing memory records the 14-step vs. 5-step comparison | The preferred route is already established |
| Book → Sofa, 229 | N2 | NONE | — | No meaningful incumbent conflict is exposed | Redundant observation behavior is not policy-relevant here |
| Laptop → Desk, 306 | N2 | NONE | — | No policy gap or relevant inefficiency is exposed | Resolving it would not change future behavior |
| Candle → Toilet, 427 | N2 | NONE | — | The observed behavior is adequate for this simple scope | No material policy change is indicated |

Counts:

| type | OPEN | NONE |
|---|---:|---:|
| P | 5 | 0 |
| N1 | 0 | 3 |
| N2 | 0 | 3 |

This is the intended qualitative separation: B opened all five unresolved,
policy-relevant comparisons without being shown the hidden alternative, while
rejecting all six controls. No segment-hint diagnostic was needed.

## 6. C results and offline execution review

C was run only for the five B=`OPEN` cases. All five returned `CREATE`, and
the mechanical action/entity grounding check passed for all five. That check
does not establish semantic locality, contract matching, or executability.

| case | C | mechanically grounded | real local actions executed | probe evidence assessment |
|---|---|---:|---:|---|
| AlarmClock → Desk, 314 | CREATE | yes | no; stopped after `go to dresser_1` because `open drawer_1` was not admissible there | Not credible: it also proposed non-target `alarmclock_1` |
| Pencil → Shelf, 310 | CREATE | yes | yes: `go to desk_1`, `examine desk_1` | Credible local discovery/cost evidence; target was visible at the endpoint |
| Plate → Dresser, 218 | CREATE | yes | yes: open-surface checks through `sidetable_1` | Credible local discovery evidence; target was visible at the endpoint |
| SoapBottle → Cabinet, 414 | CREATE | yes | yes: countertop and sink checks | A useful negative result is possible, although it did not locate the target |
| SoapBottle → Cabinet, 417 | CREATE | yes | yes: `go to countertop_1`, `examine countertop_1` | Credible local discovery/cost evidence; target was visible at the endpoint |

The P001 result is an observed C synthesis/execution failure, not a B failure:
mechanical grounding accepted the strings because the entity names had been
observed, but it did not check the action's state-dependent legality or target
identity. C was intentionally not patched in this cycle; the failure is
recorded for a future C-specific investigation.

## 7. One E0/E1 diagnostic pair

Because P005 supplied a credible grounded local probe, one matched online pair
was run for `alfworld-p-005-soapbottle-417`. Initial public states matched and
both actor calls recorded `proxy_disabled: true`.

| condition | exploratory memory visible | local exploratory actions followed | execution result |
|---|---:|---:|---|
| E0 established only | no | not applicable | Actor planned a cabinet route, then execution stopped after an inadmissible target action; task not won |
| E1 established + exploratory | yes | yes, exact contiguous proposal | Executed the two-action countertop probe; task not won, but the target was exposed |

E1 therefore shows visibility and local following for this case. It does not
show a matched task-success or cost improvement: E0's actor plan failed before
completing its incumbent route, and E1 stopped after the local discovery probe.
No E2 was run because E1 was not ignored. The pair is an authority/execution
diagnostic, not evidence that the full method works.

## 8. Telemetry and reproducibility

All model calls used DashScope directly with proxy environment variables
removed, `NO_PROXY=*`, an empty urllib proxy handler, `qwen3.8-flash`,
`enable_thinking=false`, `preserve_thinking=false`, and `temperature=0`.

The corrected Experiment-A run used 11 B calls and 5 C calls:

| stage | calls | input tokens | output tokens | cached input | estimated cost |
|---|---:|---:|---:|---:|---:|
| B | 11 | 64,641 | 3,003 | 20,480 | CNY 0.0406384 uncached component; total unknown because cached rate is console-specific |
| C | 5 | 11,952 | 1,537 | 0 | CNY 0.0137115 |
| E0/E1 actor | 2 | 4,298 | 90 | 0 | CNY 0.0036814 |

Main artifacts:

```text
artifacts/exploratory_memory_mvp/experiment_a-qwen38-b-boundary-20260916/
artifacts/exploratory_memory_mvp/online-p005-qwen38-boundary-20260916/
```

Commands used for the representation audit and paid stages (with proxy
variables removed) were:

```bash
env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY \
  -u http_proxy -u https_proxy -u all_proxy \
  NO_PROXY='*' no_proxy='*' PYTHONPATH=src \
  conda run --no-capture-output -n memory-automanual \
  python experiments/exploratory_memory_mvp/run_b.py \
  --prepare-only \
  --output artifacts/exploratory_memory_mvp/b-interface-audit-20260916

env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY \
  -u http_proxy -u https_proxy -u all_proxy \
  NO_PROXY='*' no_proxy='*' PYTHONPATH=src \
  conda run --no-capture-output -n memory-automanual \
  python experiments/exploratory_memory_mvp/run_experiment_a.py \
  --allow-network --env-file /home/coolboy/projects/memory/.env \
  --prompt-variant optimized \
  --output artifacts/exploratory_memory_mvp/experiment_a-qwen38-b-boundary-20260916

env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY \
  -u http_proxy -u https_proxy -u all_proxy \
  NO_PROXY='*' no_proxy='*' PYTHONPATH=src \
  conda run --no-capture-output -n memory-automanual \
  python experiments/exploratory_memory_mvp/run_online_pair.py \
  --experiment-a artifacts/exploratory_memory_mvp/experiment_a-qwen38-b-boundary-20260916 \
  --case alfworld-p-005-soapbottle-417 \
  --output artifacts/exploratory_memory_mvp/online-p005-qwen38-boundary-20260916 \
  --env-file /home/coolboy/projects/memory/.env --allow-network
```

## 9. Failure localization

* **Previous B implementation/prompt was mis-specified: confirmed.** The
  corrected information boundary and role wording changed P recall from the
  previous 0/5 to 5/5 while preserving 6/6 negative-control rejection. This
  directly supports the conclusion that the earlier all-NONE result was at
  least substantially caused by B being asked to do part of C's job and by the
  blurred input representation.
* **Segment localization is not the main bottleneck in this retest.** B gave a
  sensible local segment for every P case, so the permitted segment-hint
  diagnostic was unnecessary.
* **Comparative-status/policy-relevance judgment is not the observed B
  bottleneck on these 11 cases.** B distinguished feasibility-only P memory
  from comparative-evidence N1 memory and low-value N2 cases. This is a small,
  hand-curated, one-shot result and does not establish general capability.
* **C synthesis/grounding remains a separate weakness.** One of five C
  proposals was not executable despite passing mechanical grounding. The
  current action validator checks syntax and observed entities, not state
  legality or semantic target identity.
* **Online evidence remains ambiguous.** E1 followed the exploratory memory
  and exposed the target, but E0's actor execution failed and neither
  condition completed the task. The pair cannot support a method-level online
  success claim.

The strongest conclusion for this cycle is therefore: the previous B/C
interface was materially mis-specified, and correcting it makes the small
curated B gate behave as intended. C's one-shot synthesis and online actor
authority still require separate experiments. No full persistent-memory claim
is made.

## 10. Verification

Focused MVP tests: 9 passed. Ruff, compilation, and `git diff --check` passed.
The full repository test suite retains the two known AppWorld setup/data
errors documented in `docs/36_appworld_final_sanity_probe_results.md`; those
are unrelated to this ALFWorld/Qwen retest.
