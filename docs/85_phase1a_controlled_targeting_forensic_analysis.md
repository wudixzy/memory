# Phase 1A controlled-targeting v2 forensic analysis

Date: 2026-09-20
Branch: `exp/minimal-exploratory-memory-validation`
Analysis commit baseline: `32e53719be83b912e385b6a45eb1a9a5d9a68623`

This is an offline forensic analysis of the existing Source 5 -> B/C -> H and
20-target C2/C3 artifacts. It made zero model/API calls and did not rerun C2 or
C3. The original runtime artifacts and outcomes are unchanged.

Runtime sources:

```text
artifacts/exploratory_memory_mvp/phase1a-controlled-targeting-v2-source-20260920-8103a79
artifacts/exploratory_memory_mvp/phase1a-controlled-targeting-v2-targets-20260920-4f01e89
```

The frozen assignment artifact, not the earlier prose table, is the assignment
source of truth. The mismatch found in `docs/84` was a documentation-only
transcription error and was corrected without changing its runtime files or
digests.

## 1. Q1 — What does H add beyond C2?

The fixed C2 memory already contains these generic ideas:

* inspect unvisited public candidate receptacles before committing to a default;
* acquire the target if found;
* stop/abort local exploration and resume the established routine if the probe
  is negative;
* compare the alternative against the default in terms of actions/cost.

C2 does **not** specify an open-surface-before-closed-storage ordering. Its
realization pattern is generic alternate-candidate probing.

The following values are the future-facing H fields copied from the frozen source
manifest. The final column records the information not present in C2 as written.

| H / source | scope | hypothesis | guidance | realization pattern / adaptive policy | C2 does not contain |
|---|---|---|---|---|---|
| `phase1a-source-h-00` / `AlarmClock -> Desk-314` | “target object is not immediately visible and multiple receptacle types (open surfaces vs. closed containers) are present” | open surfaces such as beds/desks/dressers before closed drawers reduce cost when the target is on an open surface | identify open vs. closed; inspect one open surface first; then other open surfaces or fall back to drawers | “open/visible surfaces over closed containers”; adaptive policy explicitly classifies beds/desks/dressers/shelves vs. drawers/cabinets, then falls back | explicit open/closed partition and ordered open-surface preference |
| `phase1a-source-h-01` / `Pencil -> Shelf-310` | target hidden; multiple closed receptacles | open surfaces such as desks or high-probability locations before blind cabinet opening reduce cost | open surface first, then closed storage if absent | “open/low-friction before closed/high-friction”; adaptive policy names desk/open surface then closed cabinet | open/closed cost distinction and a first open-surface preference |
| `phase1a-source-h-02` / `Plate -> Dresser-218` | target hidden; multiple candidate receptacles in entry observation | tables/counters before drawers/cabinets reduce navigation and interaction steps | partition open-access vs. closed-storage; exhaust open-access before closed | explicit “Open Surface” vs. “Closed Storage” partition and ordered execution | category partition and exhaustive open-first order |
| `phase1a-source-h-03` / `SoapBottle -> Cabinet-414` | target hidden; multiple receptacle types | countertops/sinks before cabinets/drawers reduce search steps | open surface first, then other open surfaces, then closed storage | adaptive policy specifically selects a countertop or `sinkbasin` before cabinets/drawers | concrete countertop/sink preference |
| `phase1a-source-h-04` / `SoapBottle -> Cabinet-417` | liquid/hygiene target; multiple visible receptacle types | countertops/sinks before cabinets reduce steps for hygiene products | same open-surface-first order | nearest unvisited open surface, then closed storage | concrete countertop/sink preference plus object-type scope |

The Hs are therefore not textually identical to C2, and they contain a real
category-level preference. However, the four target-eligible Hs are highly
homogeneous: all express an open-surface-first heuristic, not four materially
different targeting hypotheses. The fifth H is narrower (“liquid or hygiene
product”) and was correctly rejected before target assignment; it is not evidence
in the target run.

The strongest careful reading is:

```text
H adds an open-access/open-surface versus closed-storage ordering.
It does not add a source-specific entity, location, or object answer.
The source-derived targeting content is low-diversity and close to a generic
open-surface heuristic.
```

## 2. Q2 — Did H change selector behavior?

The following table reads the existing saved selector artifacts only. `A/n`
means acquired after `n` candidate probes; `N/2` means not acquired within the
two-probe budget. Sequences are exact public candidate IDs selected by the saved
C2/C3 selector outputs. `delta_actions = C3 - C2`.

| target | assigned H | C2 sequence / result | C3 sequence / result | first choice differs? | full sequence differs? | delta actions |
|---|---|---|---|---|---|---:|
| `simple/SprayBottle -> Toilet-426` | h-02 | `countertop_1` / A/1 | `bathtubbasin_1, countertop_1` / A/2 | yes | yes | +1 |
| `clean/Apple -> Fridge-27` | h-02 | `cabinet_1, countertop_2` / N/2 | `countertop_1, countertop_2` / N/2 | yes | yes | 0 |
| `cool/Pot -> Shelf-1` | h-00 | `stoveburner_1` / A/1 | `stoveburner_1` / A/1 | no | no | 0 |
| `heat/Egg -> GarbageCan-2` | h-03 | `cabinet_1, fridge_1` / A/2 | `countertop_1, sinkbasin_1` / N/2 | yes | yes | -3 |
| `cool/Lettuce -> DiningTable-21` | h-02 | `cabinet_1, fridge_1` / N/2 | `diningtable_1, countertop_1` / N/2 | yes | yes | -2 |
| `heat/Egg -> SideTable-21` | h-02 | `countertop_1` / A/1 | `diningtable_1, fridge_1` / A/2 | yes | yes | +2 |
| `clean/Ladle -> DiningTable-27` | h-03 | `cabinet_1, diningtable_1` / A/2 | `countertop_1, countertop_2` / A/2 | yes | yes | 0 |
| `cool/Bread -> CounterTop-7` | h-01 | `cabinet_1, countertop_1` / N/2 | `diningtable_1, fridge_1` / N/2 | yes | yes | 0 |
| `simple/Book -> Sofa-229` | h-02 | `armchair_1` / A/1 | `coffeetable_1` / A/1 | yes | yes | 0 |
| `heat/Mug -> Cabinet-20` | h-01 | `cabinet_1, countertop_1` / N/2 | `countertop_1, coffeemachine_1` / N/2 | yes | yes | -1 |
| `clean/DishSponge -> Toilet-427` | h-03 | `bathtubbasin_1` / A/1 | `countertop_1, sinkbasin_1` / N/2 | yes | yes | 0 |
| `clean/DishSponge -> Cabinet-414` | h-01 | `bathtubbasin_1, countertop_1` / N/2 | `countertop_1, countertop_2` / N/2 | yes | yes | 0 |
| `clean/Apple -> Microwave-14` | h-03 | `cabinet_1, countertop_1` / N/2 | `countertop_1, countertop_2` / N/2 | yes | yes | 0 |
| `heat/Apple -> GarbageCan-12` | h-03 | `cabinet_1, fridge_1` / N/2 | `countertop_1` / A/1 | yes | yes | -2 |
| `heat/Potato -> GarbageCan-14` | h-03 | `cabinet_1, fridge_1` / N/2 | `countertop_1, countertop_2` / A/2 | yes | yes | 0 |
| `cool/Bread -> CounterTop-15` | h-00 | `cabinet_1, countertop_2` / N/2 | `diningtable_1, fridge_1` / N/2 | yes | yes | +1 |
| `cool/WineBottle -> Cabinet-17` | h-03 | `cabinet_1, fridge_1` / N/2 | `countertop_1, fridge_1` / N/2 | yes | yes | 0 |
| `cool/Mug -> CoffeeMachine-30` | h-01 | `cabinet_1, fridge_1` / N/2 | `countertop_1` / A/1 | yes | yes | -2 |
| `cool/Cup -> Microwave-30` | h-01 | `cabinet_1, fridge_1` / N/2 | `countertop_1, countertop_2` / N/2 | yes | yes | -2 |
| `heat/Plate -> CounterTop-28` | h-00 | `cabinet_1, countertop_2` / N/2 | `countertop_1, countertop_2` / N/2 | yes | yes | -1 |

Mechanical behavior totals:

* first-choice divergence: **19/20**; same first choice: **1/20**;
* complete two-probe sequence divergence: **19/20**; same full sequence: **1/20**;
* under the simple mechanical partition “closed storage = `cabinet`, `drawer`,
  or `fridge`”, C3's first candidate was non-closed in **20/20** targets,
  compared with **5/20** for C2;
* h-03 selected the explicitly named `countertop` class first in **7/7** of
  its assigned targets. The other Hs use broader or less sharply specified
  open-surface language, so exact subtype adherence is not always a well-defined
  binary judgment.

Thus H did not merely sit unused in the prompt. It produced a stable
open-first selector policy. The limitation is that this behavior is a common
coarse heuristic across source Hs, not clearly a diverse history-derived
targeting family.

## 3. Q3 — Deterministic public diagnostic for the 10 both-fail targets

For each target where both saved arms failed to acquire within two probes, I used
the same frozen replay specification and mechanically inspected the currently
admissible public candidate list. At each location the diagnostic used only exact
public `go to`, legal `open`, and exact requested-object `take` actions. It did
not read PDDL, hidden placement, oracle routes, evaluator labels, or target
outcomes. The diagnostic was not a new scientific arm and did not change the
original artifacts.

The inspection number is the number of public candidates inspected by this
exhaustive diagnostic, not the original two-probe budget. For the original C2/C3
sequences, neither arm's first two probes exposed an exact public target take
action in any row because these are the both-fail cases.

| target | H | public target source found | public inspection number / initial candidates | relation to H preference | primary interpretation |
|---|---|---|---:|---|---|
| `clean Apple -> Fridge-27` | h-02 | `diningtable_1` | 16 / 28 | broad open-access class is compatible | budget censoring; direction plausible but too coarse |
| `cool Lettuce -> DiningTable-21` | h-02 | `diningtable_3` | 9 / 20 | broad open-access class is compatible | budget censoring; direction plausible but too coarse |
| `cool Bread -> CounterTop-7` | h-01 | `countertop_2` | 16 / 33 | broad open surface is compatible | budget censoring |
| `heat Mug -> Cabinet-20` | h-01 | `shelf_1` | 21 / 29 | broad open surface is compatible | budget censoring |
| `clean DishSponge -> Cabinet-414` | h-01 | `toilet_1` | 17 / 19 | broad open/accessible class, but H does not define this subtype | budget censoring |
| `clean Apple -> Microwave-14` | h-03 | `fridge_1` | 12 / 20 | not in h-03's explicit countertop/sink preference | H direction unsupported for this target, with budget censoring |
| `cool Bread -> CounterTop-15` | h-00 | exact take action said `from countertop_1` | 12 / 27; selected `coffeemachine_1` | broadly open, but not a clean h-00 named subtype | other/unclear: remote public take semantics |
| `cool WineBottle -> Cabinet-17` | h-03 | `diningtable_2` | 25 / 40 | open, but outside h-03's explicit countertop/sink examples | H direction plausible but too coarse |
| `cool Cup -> Microwave-30` | h-01 | no exact public target take action exposed | all 54 inspected | cannot assess from public evidence | other/unclear: target not publicly exposed in this scan |
| `heat Plate -> CounterTop-28` | h-00 | `diningtable_1` | 15 / 29 | broadly open, but outside h-00's named examples | budget censoring plus coarse H class |

The `Bread -> CounterTop-15` row is important: at the selected
`coffeemachine_1` state, the public admissible list exposed
`take bread_1 from countertop_1`. The selected candidate and the source named by
the exact take action differed. This is public carrier behavior, not a hidden
lookup; it means “candidate inspected” and “receptacle named by a remote take
action” must not be conflated in post-hoc interpretation.

The `Cup -> Microwave-30` scan inspected all 54 dynamically available public
candidate locations without exposing an exact `take cup_* from ...` action. No
hidden answer is inferred from that absence; it remains a carrier/public-state
ambiguity.

The full derived public-only row data is in:

```text
docs/human_review/trajectory_artifacts/phase1a_controlled_targeting_v2_review/derived_public_both_fail_scan.json
```

## 4. Q4 — Paired environment-action cost

The existing episode artifacts give the following descriptive deltas:

| subset | n | C3 lower | equal | C3 higher | median delta | mean delta |
|---|---:|---:|---:|---:|---:|---:|
| all targets | 20 | 7 | 10 | 3 | 0 | -0.45 |
| both acquired | 5 | 0 | 3 | 2 | 0 | +0.60 |
| both failed | 10 | 4 | 5 | 1 | 0 | -0.50 |
| C2-only acquisition | 2 | 1 | 1 | 0 | -1.5 | -1.50 |
| C3-only acquisition | 3 | 2 | 1 | 0 | -2 | -1.33 |

The aggregate `C2 = 57` versus `C3 = 48` environment actions is therefore not
a uniform successful-probe efficiency advantage. The median paired difference is
zero, and on the matched both-acquired subset C3 is never lower. The reduction is
distributed across seven targets but includes several `-2`/`-3` cases and is
partly explained by C3 selecting open candidates that require no `open` action.
It is a real observed secondary cost pattern, but it should not be promoted to a
general C3 benefit.

## 5. Source clustering using the frozen assignment artifact

All rows below were regrouped from the actual
`target_h_assignments.json`; the earlier per-target memo labels were not used.

| assigned H | n | C2 acquired | C3 acquired | C2 wins | C3 wins | ties | first-choice divergence | both-fail |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| h-00 | 3 | 1 | 1 | 0 | 0 | 3 | 2 | 2 |
| h-01 | 5 | 0 | 1 | 0 | 1 | 4 | 5 | 4 |
| h-02 | 5 | 3 | 3 | 2 | 0 | 3 | 5 | 2 |
| h-03 | 7 | 3 | 3 | 2 | 2 | 3 | 7 | 2 |

The apparent positive acquisition count is not concentrated in one clean H
family. h-01 contributes the only positive C3 paired win in the source-cluster
table, while h-02 favors C2 by two wins and h-03 is mixed. With only 3–7 targets
per H and highly similar H content, these are dependent source-cluster
observations, not independent evidence for four targeting mechanisms.

## 6. Final research judgment

### Selected direction: **C — H is behaviorally distinctive and the endpoint may miss a narrow cost/evidence benefit**

This is the best fit among A/B/C, but it is a low-confidence forensic judgment,
not a positive targeting-value result.

Evidence for C:

1. H adds an open-first category preference absent from the literal C2 policy.
2. The preference changes behavior in 19/20 first decisions and 19/20 complete
   two-probe sequences.
3. The public both-fail diagnostic found six targets only after more than two
   candidate inspections even though their eventual public source was broadly
   compatible with an open-first direction. The fixed two-probe acquisition
   endpoint is therefore strongly budget-censored.
4. C3 used fewer environment actions on 7/20 targets, although the median was
   zero and the matched-acquisition subset did not improve.

Why this is not A: H diversity is weak and the Hs are close to a generic
open-surface heuristic, but H was not ignored and C3 behavior was not stable with
C2; it was consistently different.

Why this is not B: the public diagnostic does not show that the target
distribution generally contradicts open-first search. Most publicly discovered
both-fail targets were on broad open/accessible candidates, often simply too far
down the candidate list. There are counterexamples—especially the h-03/fridge
case—and several H subtype mismatches, but not a clean distribution-wide
refutation.

Important qualification: the current evidence also cannot show that the
open-first behavior is genuinely *history-derived* rather than a generic
heuristic that happened to be generated in all four source cases. The first pass
does not support a C3 superiority claim: paired acquisition was `C2 4 / tie 13 /
C3 3`, despite raw acquisition `7/20` versus `8/20`.

## 7. Review boundary and next-step constraint

The 20 target units are development evidence. Any later change to H content,
probe budget, endpoint, or C2/C3 construction must use a fresh untouched target
pool for confirmatory evidence. The current 20 targets must not be reused to
claim that a revised metric or revised H works.

No new paid experiment is proposed in this report. The minimum unresolved issue is
whether the observed lower action count is useful comparison-evidence efficiency
or merely the mechanical cost of selecting open candidates while failing to
acquire within a short budget. That distinction requires researcher design review
before any new protocol is frozen.
