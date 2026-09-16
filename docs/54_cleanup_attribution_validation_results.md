# Cleanup / attribution validation results

Date: 2026-09-16
Branch: `exp/minimal-exploratory-memory-validation`
Carrier: ALFWorld TextWorld
Main model: DashScope `qwen3.8-flash`, `enable_thinking=false`, temperature `0`

This is a cleanup and attribution experiment. It is not evidence that the
complete persistent-memory method works, and it does not support a benchmark
or performance claim.

All paid calls in the scientific runs used the direct DashScope transport. The
proxy variables were removed and `NO_PROXY=*` was set.

## 1. Clean C packets

The hand-written packets in
`experiments/exploratory_memory_mvp/cases/local_c_packets.json` now contain
only entry-state facts and Functional-Contract-relevant facts. They no longer
contain the earlier meta-boundary text or the P005 wording that effectively
asked C whether to try an open-access surface before closed storage.

The cleaned P002 packet says, in substance:

```text
The entry observation names multiple open and closed candidate receptacles,
including a desk and cabinets. The requested object is not visible in the
entry observation.

The local function under comparison is selecting a search realization before
acquiring the requested object while preserving a state from which it can be
carried to its destination.
```

The cleaned P005 packet says, in substance:

```text
The entry observation names closed cabinets and accessible surfaces such as a
countertop and sinks. The requested object is not visible in the entry
observation.

The local function under comparison is selecting a search realization before
acquiring the requested object while preserving the downstream placement
contract.
```

The completed source trajectory, later source observations, target metadata,
and evaluator fields remain outside the C packet. C was rerun only for the
source cases needed by transfer:

| source | old hint removed? | C | independently synthesized alternative | future H review | entry grounding |
|---|---:|---|---|---|---|
| P002 Pencil | yes | `CREATE` | open-surface inspection before closed-container search, with an explicit local deviation/fallback policy | future-facing; no `desk_1` or other source entity ID | legal `go to desk_1` |
| P005 SoapBottle-417 | yes | `CREATE` | surface-first search over accessible surfaces before closed storage | future-facing; no `countertop_1` or other source entity ID | legal `go to countertop_1` |

The P002 and P005 outputs are concrete local policies rather than
`explore more`, and neither required the old researcher phrase to produce an
alternative. This small retest does not establish that C will remain reliable
on a larger sample.

Source C artifacts:

```text
artifacts/exploratory_memory_mvp/experiment_c-qwen38-clean-20260916/
```

## 2. Clean A: E1-only boundary

`A` now accepts an `environment_outcome` containing exactly the actual E1
outcome. `e0_reference`, E0 actions/counts/results, matched-control fields, and
other counterfactual fields are rejected by the public-input validator. E0 is
still kept in researcher-side transfer results.

The existing three transfer episodes were rebuilt from their saved E1 traces
and A was rerun without rerunning the target environments:

| pair | old A output | E1-only A output | direct review |
|---|---|---|---|
| P002 → Laptop | `NO_CHANGE` | `NO_CHANGE` | Preserves uncertainty about the failed/looping probe and does not treat the failed episode as evidence against the whole hypothesis. |
| P005 → SprayBottle | `UPDATE / SPECIALIZE` | `UPDATE / REFINE` | Still scope-limited and bound to the observed countertop→pickup→placement trace; it no longer uses a matched E0 result and does not claim universal superiority. |
| P005 → SoapBottle-414 | `NO_CHANGE` | `NO_CHANGE` | Keeps the result local to the observed wrong-object/failed episode and does not falsify surface-first search generally. |

The SprayBottle update therefore remains supportable from E1 alone, but the
operation became more conservative. A's output is an auditable model proposal;
it is not materialized into a production memory store and it never reactivates
the consumed H.

Clean A artifacts:

```text
artifacts/exploratory_memory_mvp/clean-a-e1-only-20260916/
```

## 3. Laptop attribution ladder

The primary 3A comparison deliberately held the original P002→Laptop H fixed
and added only mechanically derived runtime state. The state contains the
ordered receptacle IDs appearing in executed public `go to` actions and the
count of executed probe actions. It does not select a location, declare an
observation informative, or choose a fallback route.

| arm | H | result |
|---|---|---|
| original Qwen run | original H, no runtime state | 24 steps, desk/shelf loop, no evidence status, step cap, not won |
| 3A Qwen diagnostic | exactly the original H plus `probe_runtime_state` | 6 steps, won; `ACTIVE, ACTIVE, ACTIVE, EVIDENCE_OBTAINED`, then H removed and the original placement completed |
| 3B stronger actor | not run | The loop disappeared in 3A, so a stronger-model diagnostic was not needed. |

The corrected 3A trace was:

```text
go to desk_1
go to shelf_1
go to bed_1
take laptop_1 from bed_1       # EVIDENCE_OBTAINED / probe-ready
go to desk_1
put laptop_1 in/on desk_1
```

At the third action the runtime record already contained
`visited_receptacles=["desk_1", "shelf_1"]`, which gave the actor a factual
progress record and removed the prior two-location oscillation. Every action
in the diagnostic passed exact current-state admissibility.

This is strong evidence for an actor-interface/state-representation problem
in the original Laptop failure. It is not evidence that the H policy itself
was independently optimal. A supplemental run with the newly cleaned H also
completed, but it is not used for the primary attribution because it changes H
as well as the interface.

Primary diagnostic artifact:

```text
artifacts/exploratory_memory_mvp/laptop-e1-qwen38-runtime-state-original-h-20260916/
```

## 4. New negative/fallback target

The final directly selected target is:

```text
source: P005 SoapBottle-417
target: pick_clean_then_place_in_recep-Apple-None-Microwave-14/
        trial_T20190909_120203_117379
```

The target has accessible surfaces and closed storage, and its acquisition
subproblem has the same local Functional Contract as H. The additional clean
and microwave-placement steps are downstream state that must remain possible.
The evaluator-side fact that the apple is in `fridge_1` was used only to select
the target and was not injected as an oracle location. After the actor legally
visited and opened the fridge, the resulting action/observation was ordinary
public E1 evidence and could therefore appear in the trajectory and A input.

An E0 preflight completed once in 26 steps under the same Qwen configuration
and 32-step cap. The formal matched runs exposed a reproducibility problem:

| run | E0 | E1 with source H |
|---|---|---|
| matched run 1 | failed at 20 executed steps when Qwen emitted an inadmissible `take apple_4 from fridge_1` | 12 steps, won |
| matched run 2 | failed at 19 executed steps on another inadmissible object action | 11 steps, won |

The E1 traces did exercise the intended local behavior: the actor visited
open surfaces without finding the requested apple, moved to the closed fridge,
acquired the apple, emitted `EVIDENCE_OBTAINED`, removed runtime H, and then
completed the ordinary clean-and-place continuation. All E1 actions passed the
exact current-state legality check.

The trace is useful evidence that a negative surface observation can coexist
with H termination and successful downstream continuation. It is **not** a
clean paired negative-fallback result, because the matched E0 control failed
twice even though the preflight succeeded. Also, in these E1 runs the actor
kept H active while moving from the exhausted surface search into closed
storage; H terminated after acquisition rather than immediately after the
negative surface result. Thus the strict claim “negative probe stops, ordinary
policy resumes, and E0/E1 are cleanly comparable” remains unestablished.

The first E1-only A output was `NO_CHANGE`, preserving the lack of a clean
counterfactual comparison. The repeat produced `UPDATE / REFINE` with a
scope-limited surface-first guidance and unresolved comparative action counts.
The latter is still E1-only and contains no E0 result, but its phrase
“effective strategy” is stronger than a single E1 success warrants; this is a
small model-conservatism concern, not a deterministic A rule failure.

Selected target artifacts:

```text
artifacts/exploratory_memory_mvp/transfer-p005-to-clean-apple-microwave-14-qwen38-clean-20260916/
artifacts/exploratory_memory_mvp/transfer-p005-to-clean-apple-microwave-14-qwen38-clean-20260916-v2/
```

## 5. Final attribution

| issue | implementation/interface evidence | model evidence | method evidence | current judgment |
|---|---|---|---|---|
| C candidate dependence | Fact-only P002/P005 packets still yielded `CREATE`; future H had no source IDs | No clean-packet failure observed in two retests | No new method-level evidence | C synthesis is not the leading problem in this sample |
| A E0 leakage | Validator and runner now enforce E1-only input; old SprayBottle `SPECIALIZE` became E1-only `REFINE` | Output varies between conservative `NO_CHANGE` and `UPDATE` on difficult episodes | No clear A mechanism failure; mild overstatement risk on the repeat Apple output | Boundary fix supported; keep direct review for conservatism |
| Laptop loop | Same original H succeeds when only mechanical progress state is exposed | No stronger model was necessary | H/one-shot lifecycle completed and task continued | Interface/state representation is the leading explanation |
| Apple E0 instability | Matched initial public states and legality checks are correct; preflight can complete | Two formal E0 runs fail on hallucinated/inadmissible object actions despite temperature 0 | E1 can stop H and finish, but strict negative fallback comparison is not isolated | Qwen execution/reproducibility is the leading explanation; method fallback remains unresolved |
| Overall method | C/A boundaries and H lifecycle are auditable | Small-sample actor behavior is variable | No clean causal paired fallback result | Do not make a broader method claim yet |

## 6. Conclusion and next recommendation

Supported by this cleanup cycle:

1. C does not appear to depend on the removed researcher-written candidate
   hint for the two source cases needed by transfer.
2. A can be run on deployable E1 evidence only; the previous SprayBottle update
   remains possible but becomes more conservative.
3. The Laptop loop is best localized to the actor's public progress-state
   interface, not to B and not, on this evidence, to an unavoidable H-authority
   failure.
4. A source-generated H can drive a different target through negative local
   observations, H consumption/termination, and successful downstream task
   continuation.

Not supported:

1. a reproducible E0/E1 negative-fallback comparison under the current Qwen
   actor;
2. a claim that surface-first H is generally better than the incumbent;
3. a claim that the full persistent-memory method works.

The MVP should not move to broader evaluation from this report without first
isolating the remaining actor reproducibility/fallback issue. The next cycle,
if run, should stay small and directly reviewed; it should not add retrieval,
Stage 1, a search controller, or semantic rule-based fallbacks.
