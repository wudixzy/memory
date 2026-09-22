# Phase 1E Max Prefix 1–61 Diagnostic

Status: **incomplete-prefix diagnostic only**. This is diagnostic evidence from a valid completed prefix of an infrastructure-invalid preregistered stream. It is not the final Phase 1E cross-model result, and no final Phase 1E category is selected here.

## 1. Purpose and boundary

This no-model audit reconstructs the completed Max tasks 1–61 because the interrupted runtime did not produce final paired-results or stream-summary files. It does not resume the stream, infer tasks 62–64, or modify any saved Phase 1E runtime artifact.

The audit reads only the frozen combined registry and public saved runtime artifacts: run config, registry snapshot, completed G/T summaries, public pairing-proof fields, model request events, selected T-state checkpoints, and C/retrieval/reconciliation inputs needed for mechanism and H2 extraction. It does not read PDDL, hidden placements, oracle routes, or hidden task answers. H2 judgments compare only the Functional Contract, history actually visible to C, and that episode's C proposal; later acquisition outcomes are not used to decide semantic duplication.

## 2. Prefix validation and reproducible artifact

The read-only utility is [analyze_phase1e_prefix.py](../experiments/exploratory_memory_mvp/analyze_phase1e_prefix.py). Its reusable entry point is `validate_completed_prefix(runtime_root, registry=None)`, returning normalized task rows plus registry/runtime identity metadata. It reads only the preregistered task directories for 1–61 and their artifacts; it does not open or inspect later episode directories. It verifies registry digest/order, G/T completed summaries, task/seed identity, public pairing proofs and initial fingerprints, duplicate/missing prefix indices, and Max-only model requests.

Completed but unacquired episodes are valid scientific rows. The validator accepts `target_acquired=false` with `actions_to_target_acquisition=null`, preserves the row as censored, and computes paired action deltas only when both G and T acquired the target and have measured acquisition-action counts. Arm acquisition/censoring counts are reported separately.

The machine-readable artifact is:

```text
artifacts/exploratory_memory_mvp/phase1e-max-prefix-diagnostic-v1-20260922/diagnostic-final.json
```

Schema: `phase1e-max-completed-prefix-diagnostic-v1`.

| Integrity check | Result |
|---|---|
| Combined registry SHA-256 | `a46ecec068060ccc264dcc994b74e088776b98e3b9f2c31982bfb83a3e5b1a7f` |
| Selected-ID SHA-256 | `69cf0bc660df2283aa55b668aece2cecca39da73d76e31e886968da003bc3fe7` |
| Runtime registry snapshot | exact match |
| Completed prefix | 61 paired tasks / 122 arm episodes |
| Missing or duplicate prefix indices | 0 |
| Pairing/public-fingerprint failures | 0 |
| Model request events | 500; all `qwen3.8-max` |
| Both arms acquired exact target | 61/61 |
| Censored/unpaired acquisition measurements | 0 in this prefix |

Diagnostic artifact SHA-256: `b1ab60c6d237eb0c115339bdea2b98a81de3db1707c54d2b6fcb075b0d1bcdf7`.

The immutable source runtime remains `artifacts/exploratory_memory_mvp/phase1e-cross-model-max-v1-20260922-0ada221`. The diagnostic is stored outside it.

## 3. Prefix behavior

The metric is environment actions to exact target acquisition, not full ALFWorld task success. `Delta = T − G`; positive values mean T used more actions to acquisition in this descriptive prefix. All pairs here are uncensored, so every task contributes to paired summaries.

| N | G actions | T actions | Delta | T lower / equal / higher | Paired measurements |
|---:|---:|---:|---:|---:|---:|
| 8 | 111 | 109 | -2 | 3 / 4 / 1 | 8 |
| 16 | 191 | 207 | +16 | 4 / 7 / 5 | 16 |
| 24 | 299 | 315 | +16 | 10 / 7 / 7 | 24 |
| 32 | 349 | 378 | +29 | 11 / 11 / 10 | 32 |
| 40 | 411 | 458 | +47 | 12 / 13 / 15 | 40 |
| 48 | 496 | 536 | +40 | 17 / 16 / 15 | 48 |
| 56 | 581 | 621 | +40 | 21 / 17 / 18 | 56 |
| 61 | 618 | 662 | +44 | 24 / 18 / 19 | 61 |

### Segments and H activation

| Tasks | Subset | n | G | T | Delta | T lower / equal / higher | Mean paired delta | Median |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1–32 | all | 32 | 349 | 378 | +29 | 11 / 11 / 10 | +0.91 | 0 |
|  | H-active | 11 | 65 | 73 | +8 | 0 / 7 / 4 | +0.73 | 0 |
|  | no-H | 21 | 284 | 305 | +21 | 11 / 4 / 6 | +1.00 | -1 |
| 33–61 | all | 29 | 269 | 284 | +15 | 13 / 7 / 9 | +0.52 | 0 |
|  | H-active | 10 | 75 | 61 | -14 | 3 / 4 / 3 | -1.40 | 0 |
|  | no-H | 19 | 194 | 223 | +29 | 10 / 3 / 6 | +1.53 | -1 |
| 1–61 | all | 61 | 618 | 662 | +44 | 24 / 18 / 19 | +0.72 | 0 |
|  | H-active | 21 | 140 | 134 | -6 | 3 / 11 / 7 | -0.29 | 0 |
|  | no-H | 40 | 478 | 528 | +50 | 21 / 7 / 12 | +1.25 | -1 |

These are post-hoc descriptive strata, not randomized causal estimates. The positive total T−G is concentrated in no-H episodes; H-active behavior is not directionally uniform, with a small positive delta in tasks 1–32 and a negative delta in tasks 33–61.

### Family totals

Each cell is `n, G/T/Delta`.

| Family | 1–32 | 33–61 | 1–61 |
|---|---|---|---|
| `pick_and_place_simple` | 8, 126/123/-3 | 8, 66/80/+14 | 16, 192/203/+11 |
| `pick_clean_then_place_in_recep` | 8, 55/59/+4 | 7, 59/67/+8 | 15, 114/126/+12 |
| `pick_cool_then_place_in_recep` | 8, 105/109/+4 | 7, 86/77/-9 | 15, 191/186/-5 |
| `pick_heat_then_place_in_recep` | 8, 63/87/+24 | 7, 58/60/+2 | 15, 121/147/+26 |

### Largest paired deltas

Largest T-higher examples were task 53 Watch→Safe (`G=2`, `T=16`, `+14`, no-H), tasks 16 Apple→GarbageCan, 20 Potato→GarbageCan, and 28 Mug→Cabinet (each `+9`, no-H), and task 34 Egg→Microwave (`+8`, no-H). Largest T-lower examples were task 55 Lettuce→CounterTop (`15` vs `3`, `-12`, H-active), task 50 Mug→CoffeeMachine (`9` vs `3`, `-6`, H-active), task 5 SoapBottle→Toilet (`-4`, no-H), and tasks 8 Tomato→GarbageCan and 18 Knife→CounterTop (each `-3`, no-H). These outliers do not establish a general mechanism attribution.

## 4. Mechanism trajectory

Counts are cumulative. `New H` is the increase in persisted H entries since the previous checkpoint; `activated in interval` counts actual activations in that interval. C `INVALID` includes invalid B→C handoffs and two C SchemaErrors; `SKIPPED` means the C path was not run.

| N | B OPEN / invalid | C CREATE / NONE / invalid / skipped | H total / active / consumed / superseded | New H | Activated in interval | Archive | Comparisons (status) | Reconciliation cumulative |
|---:|---:|---:|---:|---:|---:|---:|---|---|
| 8 | 8 / 0 | 7 / 0 / 1 / 0 | 6 / 2 / 2 / 2 | 6 | 2 | 2 | 2 (OPEN) | ADD 2, REFINE 4 |
| 16 | 16 / 0 | 10 / 1 / 5 / 0 | 9 / 1 / 6 / 2 | 3 | 4 | 6 | 3 (OPEN) | ADD 3, REFINE 6, NO_NEW_H 2 |
| 24 | 24 / 0 | 16 / 1 / 7 / 0 | 15 / 4 / 7 / 4 | 6 | 1 | 7 | 6 (OPEN) | ADD 6, REFINE 9, NO_NEW_H 2 |
| 32 | 32 / 0 | 22 / 2 / 8 / 0 | 21 / 5 / 11 / 5 | 6 | 4 | 11 | 9 (OPEN) | ADD 9, REFINE 12, NO_NEW_H 3 |
| 40 | 39 / 1 | 24 / 2 / 13 / 1 | 23 / 4 / 14 / 5 | 2 | 3 | 14 | 11 (OPEN) | ADD 11, REFINE 12, NO_NEW_H 3 |
| 48 | 46 / 2 | 28 / 2 / 16 / 2 | 27 / 4 / 18 / 5 | 4 | 4 | 18 | 14 (OPEN) | ADD 14, REFINE 13, NO_NEW_H 3 |
| 56 | 54 / 2 | 32 / 2 / 20 / 2 | 30 / 4 / 21 / 5 | 3 | 3 | 21 | 17 (OPEN) | ADD 17, REFINE 13, NO_NEW_H 4 |
| 61 | 59 / 2 | 34 / 2 / 23 / 2 | 32 / 6 / 21 / 5 | 2 | 0 | 21 | 19 (OPEN) | ADD 19, REFINE 13, NO_NEW_H 4 |

At task 61, B was OPEN on 59 episodes and invalid on 2. C had 34 parsed CREATE, 2 parsed NONE, 23 invalid/fail-closed and 2 skipped. Of the 23 invalid C paths, 21 were source-answer B→C handoff rejections; tasks 10 and 54 had saved SchemaError artifacts with no parsed C output. The 36 parsed C decisions map to reconciliation ADD 19, REFINE_EXISTING 13 and NO_NEW_H 4.

The active-H backlog was 5 at N=32, fell to 4 at N=40–56, and was 6 at N=61. Across tasks 33–61, 11 H entries were persisted and 10 H activations occurred; two entries were added and no H activated in tasks 57–61. The archive grew from 11 to 21 and the comparison ledger from 9 to 19, all still OPEN. This shows accumulation and a short recent interval without activation, but not a demonstrated unbounded backlog failure.

## 5. H2 audit population

The extractor found 37 T episodes where history records were available to the retrieval stage and C was reached. In 36, at least one record was actually present in C's `relevant_exploration_history`:

| C-visible outcome | Count | Treatment |
|---|---:|---|
| CREATE with parsed output | 32 | Manually classified below |
| NONE with parsed output | 2 | Manually classified below |
| C failed; no parsed output | 2 | Preserved as invalid; no semantic label |

Additional prefix exclusions: C path not reached, 23; history records were available in the saved retrieval input but none were visible to C, 1 (task 19); no archive records available to retrieval, 1. Task 19's history retrieval has a saved `DashScopeError` and no parsed result; C was subsequently called with an empty history and returned CREATE. It is not classified as an H2 CREATE because no prior record was visible to C. Tasks 10 and 54 had non-empty C-visible history, but C failed and has no parsed decision; they are not counted as CREATE or NONE.

## 6. CREATE semantic classification

Labels compare each C proposal to the records actually supplied to that C call. The listed `closest prior` is an exploration ID from that visible input. Rationales describe observed scope, hypothesis and realization differences; they are not claims about hidden model reasoning or objective strategy quality.

| Task / target | Closest prior exploration ID | Label | Observable rationale |
|---|---|---|---|
| 3 cool Egg→SinkBasin | `exploration-h-25331a9a4337e940` | MATERIALLY_DIFFERENT | Cooling-appliance-first is a task-function priority, not broad semantic surface ordering. |
| 4 heat Apple→Fridge | `exploration-h-25331a9a4337e940` | MATERIALLY_DIFFERENT | Heating-appliance-first is driven by the processing station, not general target likelihood. |
| 5 SoapBottle→Toilet | `exploration-h-25331a9a4337e940` | MATERIALLY_DIFFERENT | Explicit open-horizontal-surface-first contrasts with broad plausible-receptacle ordering. |
| 6 clean SoapBar→Cabinet | `exploration-h-25331a9a4337e940` | MATERIALLY_DIFFERENT | Hygiene-specific plausible storage/surface filtering adds fixture exclusion absent from generic search. |
| 7 cool Tomato→Microwave | `exploration-h-25331a9a4337e940` | MATERIALLY_DIFFERENT | Dedicated cooling appliance introduces a downstream-function priority. |
| 8 heat Tomato→GarbageCan | `exploration-h-25331a9a4337e940` | MATERIALLY_DIFFERENT | Perishable-food cold-storage priority is a new object/function prior. |
| 9 SaltShaker→Cabinet | `exploration-h-25331a9a4337e940` | MATERIALLY_DIFFERENT | Destination-type matching is a different candidate-selection rule from generic likely-surface ordering. |
| 13 Watch→Safe | `exploration-h-10f29a4d820ad738` | MATERIALLY_DIFFERENT | Checks exact named-destination accessibility rather than the destination receptacle type. |
| 14 clean SoapBar→CounterTop | `exploration-h-0e1c57e08374931a` | MATERIALLY_DIFFERENT | Closed hygiene-storage-first differs from broad hygiene semantic filtering. |
| 18 clean Knife→CounterTop | `exploration-h-25331a9a4337e940` | MATERIALLY_DIFFERENT | Kitchen-utensil/open-counter priority narrows generic target-likelihood ordering. |
| 20 heat Potato→GarbageCan | `exploration-h-25331a9a4337e940` | MATERIALLY_DIFFERENT | Cold-storage-first for food in a heat task is not generic semantic search. |
| 22 clean Cloth→CounterTop | `exploration-h-25331a9a4337e940` | MATERIALLY_DIFFERENT | Fabric-associated-holder-first introduces a receptacle class absent from the visible general prior. |
| 23 cool Mug→CoffeeMachine | `exploration-h-e6c23949f174b273` | MATERIALLY_DIFFERENT | Tests acquiring a target already at the named destination, rather than checking destination access before search. |
| 24 heat Mug→CoffeeMachine | `exploration-h-10f29a4d820ad738` | MATERIALLY_DIFFERENT | Heating-appliance-first is driven by transformation function, not final-destination type. |
| 25 Mug→Desk | `exploration-h-10f29a4d820ad738` | MATERIALLY_DIFFERENT | Searches a non-destination instance of the destination class, unlike destination-type-first. |
| 26 clean Cloth→CounterTop | `exploration-h-9354131b9c1fc01f` | REDUNDANT_NEAR_DUPLICATE | The visible prior already prioritizes fabric-associated/towelholder receptacles for cloth; C repeats its scope and local realization. |
| 27 cool Pan→CounterTop | `exploration-h-3ef3b43e4c09a8cb` | MATERIALLY_DIFFERENT | Open cooking surface for cookware differs from cooling-appliance and named-destination-first priorities. |
| 28 heat Mug→Cabinet | `exploration-h-25331a9a4337e940` | MATERIALLY_DIFFERENT | Heating-appliance-first for a mug is a new function-specific candidate class. |
| 30 clean Pan→CounterTop | `exploration-h-513b9268f2d9e8ad` | REDUNDANT_NEAR_DUPLICATE | Visible prior already proposes pan/cookware search at an open cooking surface; the clean-task version preserves the same acquisition realization. |
| 31 cool Potato→Microwave | `exploration-h-3ef3b43e4c09a8cb` | MATERIALLY_DIFFERENT | Open preparation/cooking surface for food contrasts with the visible cooling-appliance-first policy. |
| 34 clean Egg→Microwave | `exploration-h-9ca77aa6b36d0b57` | MATERIALLY_DIFFERENT | Open cooking surfaces for egg invert the visible perishable-food cold-storage priority. |
| 40 heat Mug→Cabinet | `exploration-h-c63cb319e69ea08c` | MATERIALLY_DIFFERENT | Open-horizontal-surface-first is an explicit alternative to heating-appliance-first for mugs. |
| 42 clean Spatula→Drawer | `exploration-h-513b9268f2d9e8ad` | JUSTIFIED_RETEST | Retests open-cooking-surface-first for spatula rather than pan; object-class transfer is meaningful. |
| 44 heat Mug→Cabinet | `exploration-h-f98f1efb76abeeb5` | MATERIALLY_DIFFERENT | Beverage-associated appliance surface differs from general open-horizontal-surface-first. |
| 45 SaltShaker→Drawer | `exploration-h-25331a9a4337e940` | MATERIALLY_DIFFERENT | Condiment-specific open-surface priority specializes candidate class beyond the broad prior. |
| 48 heat Mug→CoffeeMachine | `exploration-h-f98f1efb76abeeb5` | JUSTIFIED_RETEST | Same broad mug/open-surface idea, but the visible prior had a closed-storage destination; this one has a beverage-appliance destination. |
| 49 SaltShaker→Drawer | `exploration-h-25331a9a4337e940` | MATERIALLY_DIFFERENT | Condiment/open-surface ordering differs from records visible here; the similar task-45 H was not in this C-visible archive. |
| 50 clean Mug→CoffeeMachine | `exploration-h-9c5cdfaad8ecd2c0` | REDUNDANT_NEAR_DUPLICATE | Visible prior already covers mug + beverage destination + open-horizontal-surface-first; changing downstream transform leaves the local acquisition probe equivalent. |
| 51 cool Potato→Microwave | `exploration-h-488efac368bb5d8f` | JUSTIFIED_RETEST | Retests open preparation surfaces for root vegetables after a broader food/cooling-scope prior. |
| 53 Watch→Safe | `exploration-h-25331a9a4337e940` | MATERIALLY_DIFFERENT | Closed personal-storage-first contrasts with generic semantic surface/storage order. |
| 57 Pencil→Shelf | `exploration-h-25331a9a4337e940` | MATERIALLY_DIFFERENT | Office/work-surface-first introduces a public object-domain prior. |
| 58 clean Knife→CounterTop | `exploration-h-8fc4a41253abddd7` | JUSTIFIED_RETEST | Re-tests open-surface-first for a knife rather than condiment; transfer to utensil/clean scope is meaningful. |

Aggregate: `MATERIALLY_DIFFERENT=25`, `JUSTIFIED_RETEST=4`, `REDUNDANT_NEAR_DUPLICATE=3`, `UNCLEAR=0`. Task 50 is the strongest identity-fragmentation example: C saw a near-identical mug/open-surface/beverage-destination record, but reconciliation returned `ADD`. Tasks 26 and 30 were C-level redundant CREATEs despite directly relevant visible records; reconciliation returned `REFINE_EXISTING` but still retained additional H entries.

## 7. NONE decisions

The frozen NONE schema has no reason field. The label below describes whether suppression is consistent with the history visible to C; it is not an attribution of the model's unobserved reason.

| Task | Closest visible history ID | Label | Observable basis |
|---:|---|---|---|
| 11 cool Egg→SinkBasin | `exploration-h-3ef3b43e4c09a8cb` | REASONABLE_SUPPRESSION | A directly relevant cooling-appliance-first record was visible in a cool-task context; suppression is consistent with avoiding an equivalent probe. |
| 29 Pencil→Shelf | `exploration-h-25331a9a4337e940` | POSSIBLE_OVER_SUPPRESSION | Visible records covered generic semantic search and destination priority, but not office/work-surface-first for pencils; NONE gives no explanation. |

Aggregate: `REASONABLE_SUPPRESSION=1`, `POSSIBLE_OVER_SUPPRESSION=1`, `UNCLEAR=0`.

## 8. Recurring exploration patterns

The proposals are not all one generic “open surface first” family. The visible packets distinguish several local comparison functions:

* processing-appliance-first (especially heating or cooling equipment), where the prior is tied to the task's transformation function;
* open cooking/preparation surfaces for food, cookware, utensils, or condiments;
* destination-type or exact-destination-first, which asks whether the named destination or a receptacle of that type should be checked before broad search;
* object-domain priors such as hygiene storage, fabric-associated holders, personal storage, and office/work surfaces;
* narrower beverage-appliance or other task-specific surface variants.

Some are materially scoped distinctions, not duplicates merely because they mention a surface, kitchen, or open receptacle. The three cases labeled `REDUNDANT_NEAR_DUPLICATE` are stronger than lexical overlap: tasks 26 and 30 repeated visible cloth/fabric-holder and cookware/open-cooking-surface acquisition patterns; task 50 repeated a visible mug/beverage-destination/open-surface local probe despite a different downstream transformation. The four `JUSTIFIED_RETEST` cases change an object or public task domain while retaining a related local realization. These are reviewer judgments over the C-visible packets, not claims that a proposal is objectively useful or successful.

## 9. Root-cause localization and state pressure

| Candidate source | Prefix evidence | Diagnostic judgment |
|---|---|---|
| `B_REPETITIVE_DIAGNOSIS` | B returned OPEN on 59/61 episodes. Yet among the auditable C cases, many contracts ask materially different local questions. | Broad OPEN frequency is a possible upstream throughput/quality concern, but the prefix does not show that repeated B diagnosis is the earliest cause of the three confirmed near-duplicate CREATEs. |
| `HISTORY_RETRIEVAL_MISS` | Task 19 has a saved `DashScopeError`; C was called with empty history even though records were available to the retrieval input. For the other C-visible cases, selected records are real IDs from the retrieval input. | One concrete miss; no evidence of widespread ID/selection corruption in the cases reviewed. |
| `C_REDUNDANT_CREATE_DESPITE_RELEVANT_HISTORY` | Tasks 26, 30 and 50 received relevant prior records and still emitted proposals judged near-duplicate. | Earliest clear semantic source for those cases. |
| `RECONCILIATION_IDENTITY_FRAGMENTATION` | Task 50's near-duplicate proposal was reconciled as ADD. Tasks 26 and 30 were REFINE_EXISTING but still resulted in additional H entries. | A contributing downstream identity issue, clearest at task 50; not evidence of wholesale ledger corruption. |
| `INSUFFICIENT_EVIDENCE` | C=NONE has no reason field; two C SchemaErrors and one retrieval error prevent semantic attribution. | Limits interpretation of suppression/error cases; do not infer model rationale. |

At N=61 the persistent state contained 32 H entries: 21 consumed, 6 active and 5 superseded; the Exploration History archive held 21 records and the ledger had 19 OPEN comparisons. Across tasks 33–61, 11 H entries were added and 10 H activations occurred. Thus new H formation and testing were roughly matched over this suffix; active H grew only from 5 at N=32 to 6 at N=61. Comparison count grew by 10, all OPEN, so the notable scale pressure is continuing comparison-state growth and unresolved identity, not a demonstrated runaway active-H backlog. The final five tasks added two H and activated none; that short interval is worth watching but is not enough to establish a persistent lifecycle failure.

Overall, `21 H / 19 comparisons / 21 archived explorations` is consistent with a mixture of useful semantic variety and occasional duplication/identity fragmentation—not a cleanly diverse set, but not evidence of systematic overproduction in this prefix. The 25 materially different CREATE labels outweigh three clear repeats, while repeated OPEN decisions and an all-OPEN ledger leave the long-run accumulation question unresolved.

## 10. Context and failure telemetry

Supplemental sizes below are serialized JSON input byte counts, not tokenizer-derived token counts. They describe only saved inputs that existed in the prefix; they do not establish model-context equivalence or causal context effects.

| Input | Through N=32: n / median / max bytes | Through N=61: n / median / max bytes |
|---|---:|---:|
| History-retrieval input | 24 / 6,493 / 10,340 | 37 / 8,342 / 21,553 |
| C input | 25 / 12,088 / 25,120 | 38 / 16,232 / 104,777 |
| Reconciliation input | 25 / 14,848 / 30,404 | 38 / 24,002.5 / 46,178 |

The maximum C input is a substantial outlier relative to the median and indicates that continued context growth should be measured. This audit found no evidence that bytes alone caused the saved semantic failures; it does not infer a context-limit failure.

Saved fail-closed events in this prefix include 21 B→C contract rejections, two C SchemaErrors (tasks 10 and 54), and the task-19 history-retrieval `DashScopeError`. They are retained as visible failures. The mechanical pairing, identity, state-summary, and Max-only request checks passed for all 61 completed pairs. Task 62's temporary-storage failure belongs to the separate resume audit; this diagnostic did not read or reconstruct it.

## 11. Descriptive comparison with frozen Flash audits

The frozen Flash H2 audit for tasks 1–32 classified 20 CREATE proposals as 14 materially different, 5 justified retests and 1 near-duplicate; its 10 NONE cases were 6 reasonable suppressions, 2 possible over-suppressions and 2 unclear. The Phase 1D Flash suffix audit classified 5 CREATEs as 3 materially different, 1 justified retest and 1 near-duplicate, plus 18 NONE cases as 16 reasonable suppressions and 2 possible over-suppressions.

The Max prefix has 32 classified CREATEs (25 materially different, 4 justified retests, 3 near-duplicates) and only two parsed C=NONE cases (one reasonable suppression and one possible over-suppression); two additional C cases failed before a parsed decision. The different denominators and the incomplete Max prefix make these distributions descriptive only. They do not support a final cross-model verdict. In particular, Max's larger CREATE count may reflect more B/C opportunities or different fail-closed rates as well as semantic behavior.

## 12. Interpretation boundary

The validated prefix shows a descriptive Max T−G acquisition-action difference of `+44` through task 61. That total is concentrated in no-H episodes (`+50`), while H-active episodes sum to `-6`; within tasks 33–61, the H-active subset is `-14` and no-H is `+29`. This does not isolate a causal H effect: activation is not randomized, and these are post-hoc subsets.

The public artifacts support a mixed mechanism reading: H proposals often expressed meaningfully distinct local comparisons, some equivalent repeats passed C, one retrieval call failed, and reconciliation occasionally fragmented identity. In this prefix, H creation and activation were near-balanced over tasks 33–61 and no correctness corruption was found by the prefix validator. The positive aggregate action delta is therefore a real descriptive warning, but its source is not uniquely identified by these summaries.

**No final Phase 1E category is selected.** This is an `INCOMPLETE_PREFIX_DIAGNOSTIC_ONLY` for a preregistered 1–64 stream that remains infrastructure-invalid until the separately authorized tasks 62–64 continuation and full-stream reconstruction are complete. It is not a final cross-model result and does not authorize a method change.
