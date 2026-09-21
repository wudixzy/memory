# Phase 1D Flash Long-Horizon Semantic Review

## 1. Scope and evidence boundary

This is a no-new-model post-run review of the immutable Phase 1D runtime:

```text
artifacts/exploratory_memory_mvp/phase1d-long-horizon-v1-20260921-ac0bb2b
```

It uses public task/trajectory artifacts, visible B/C/A outputs, compact
exploration-history inputs, state snapshots, reconciliation artifacts, and
mechanical telemetry. It does not use PDDL placement, hidden answers, oracle
routes, or a semantic judge model. H2 labels below describe whether a C
proposal repeats the exploration records that were actually shown to C; they
are not claims about objective optimality.

The extraction was performed with the existing deterministic utility
`experiments/exploratory_memory_mvp/analyze_phase1c_h2_audit.py`, pointed at
the Phase 1D runtime. The local extracted artifact is:

```text
artifacts/exploratory_memory_mvp/phase1d-long-horizon-v1-20260921-ac0bb2b/h2_audit/extracted_cases.json
```

## 2. H2 audit population

There were 32 T episodes and 23 cases where C reached a persisted parsed
output while non-empty exploration history was supplied to the history-aware
path. All 23 had a valid history selection: 14 selected three records, five
selected two, and four selected one; there were zero selected-ID integrity
errors.

Nine cases were excluded from semantic CREATE/NONE classification:

* six B→C handoff fail-closed skips because the B contract contained a source
  entity;
* two C schema failures (`C NONE result has unexpected fields`);
* one B=`NONE` case.

These are reported as execution-quality limitations, not silently folded into
the H2 labels.

| H2 population | Count |
|---|---:|
| C=`CREATE` | 5 |
| C=`NONE` | 18 |
| Excluded/skipped | 9 |

## 3. CREATE classification

The exact labels are a manual review of scope, hypothesis, realization
pattern, Functional Contract, and retrieved records. The frozen C schema has
no hidden semantic score and no automatic similarity threshold was used.

| Global task | New proposal | Closest visible prior record | Label | Review rationale |
|---:|---|---|---|---|
| 33 | condiment open-surface-first | `exploration-h-25626a5f4ca5e1ce`, also condiment/open-surface-first | `REDUNDANT_NEAR_DUPLICATE` | C was shown the prior saltshaker/condiment record and proposed the same comparison and realization for peppershaker. The object rename is not a meaningful new local experiment. Reconciliation correctly returned `REFINE_EXISTING`, but a new H was still retained. |
| 38 | plate open-surface-first | mug and generic search records | `MATERIALLY_DIFFERENT` | The realization is familiar, but plate/dishware scope and the stated comparison against dish-storage order are a distinct public target class not represented by the retrieved records. |
| 42 | spatula open-surface-first versus stoveburner-first | pan/stoveburner and knife/open-surface records | `MATERIALLY_DIFFERENT` | The proposal tests whether the appliance-specific cookware prior transfers to a utensil. That is a different local comparison, not merely a renamed pan. |
| 56 | garbage-can checkpoint for food search | egg fridge-first/open-surface-first records | `MATERIALLY_DIFFERENT` | The hybrid open-surface → garbage-can realization addresses a non-standard receptacle branch absent from the selected prior proposals. |
| 64 | cup open-surface-first | mug open-surface-first | `JUSTIFIED_RETEST` | This is close to the mug record and remains a fragmentation risk, but C explicitly scopes the retest to cup/drinkware and states why cup versus mug is unresolved. The evidence is enough for a descriptive justified-retest label, not for declaring the distinction useful. |

Aggregate CREATE labels:

| Label | Count |
|---|---:|
| `MATERIALLY_DIFFERENT` | 3 |
| `JUSTIFIED_RETEST` | 1 |
| `REDUNDANT_NEAR_DUPLICATE` | 1 |
| `UNCLEAR` | 0 |

The clear duplicate is task 33. It is the strongest evidence of a C-side
redundant CREATE despite relevant history. Task 64 is the nearest unresolved
boundary case; it should be monitored in later validation rather than
retroactively merged by a rule.

## 4. NONE classification

The C=`NONE` schema contains no reason field. These labels therefore mean
only that suppression is or is not semantically consistent with the history
visible in the input; they do not report the model's unobserved reason.

| Label | Tasks | Review |
|---|---|---|
| `REASONABLE_SUPPRESSION` | 34, 37, 39, 41, 43, 44, 45, 46, 48, 49, 50, 52, 53, 54, 55, 63 | The retrieved records include the same object class, the same comparison, or a sufficiently broad family-level alternative. Examples include repeated condiment, mug, egg, tomato, watch, and lettuce cases. |
| `POSSIBLE_OVER_SUPPRESSION` | 35, 51 | Bread and potato were suppressed using tomato/egg/perishable-food records. The public functional comparison is related, but the target-specific scope differs; without a C reason it is not possible to tell whether the broader family evidence was intentionally sufficient. |
| `UNCLEAR` | 0 | No included case required an indeterminate label after inspecting the visible records. |

This is not evidence that NONE behavior is solved. In particular, the two
possible over-suppression cases show why future review must retain C's visible
history context and not infer rationale from the decision string alone.

## 5. Recurring exploration families

The dominant realization pattern remains some form of open-surface-first
search. The suffix also contains meaningful scoped variants:

* condiment versus generic food search;
* dishware (`plate`, `cup`) versus mug or food;
* utensil versus appliance-bound cookware;
* a non-standard garbage-can checkpoint for perishable food;
* living-room personal/decorative-item search.

Thus the archive is not a list of unrelated arbitrary strings. At the same
time, the one peppershaker CREATE is a direct near-duplicate of a visible
saltshaker hypothesis, and the cup CREATE is close to an existing mug
hypothesis. The correct description is limited duplication plus scoped
diversity, not either perfect deduplication or unbounded semantic explosion.

## 6. Root-cause localization

| Potential source | Evidence in this suffix | Judgment |
|---|---|---|
| `B_REPETITIVE_DIAGNOSIS` | B returned `OPEN` on 31/32 episodes, but the visible contracts describe several distinct unresolved comparisons. | Not established as the earliest clear cause in the H2 population. Broad OPEN behavior is a quality risk, not by itself a duplicate diagnosis. |
| `HISTORY_RETRIEVAL_MISS` | All 23 included C cases received one to three valid selected history IDs; selection integrity errors were zero. | No clear retrieval miss among the auditable C cases. |
| `C_REDUNDANT_CREATE_DESPITE_RELEVANT_HISTORY` | Task 33 received the exact condiment prior and still proposed the same open-surface comparison. | One clear case. This is the earliest evidenced cause for the confirmed duplicate. |
| `RECONCILIATION_IDENTITY_FRAGMENTATION` | Task 33 was mapped to the existing comparison with `REFINE_EXISTING`; final comparison count grew 17→21 rather than exploding. Task 64 remains a borderline new comparison. | No systematic identity failure demonstrated; one boundary case remains a scale-quality risk. |
| `INSUFFICIENT_EVIDENCE` | C=`NONE` provides no reason, and tasks 35/51 have related but not identical target scopes. | Two possible over-suppression cases cannot be localized further without changing the protocol. |

The 9 excluded cases are fail-closed interface events, not evidence that
history retrieval was semantically absent. They reduce proposal throughput but
did not roll back the corresponding facts or state.

## 7. Lifecycle and state pressure

The T state trajectory was:

| N | Total H | Active H | Consumed H | Exploration History | Comparisons |
|---:|---:|---:|---:|---:|---:|
| 32 | 21 | 8 | 13 | 13 | 17 |
| 40 | 23 | 7 | 16 | 16 | 18 |
| 48 | 24 | 6 | 18 | 18 | 19 |
| 56 | 25 | 5 | 20 | 20 | 20 |
| 64 | 26 | 3 | 23 | 23 | 21 |

Five Hs were created in the suffix and ten existing Hs were activated and
consumed. The active backlog fell by five, even though the archive grew by
ten. This does not show persistent active-H backlog explosion. Comparisons
grew by four, with no `RESOLVED` status generated by consolidation.

The state remains bounded in this 64-task stream, but the result is not a
guarantee of indefinite scalability. The two near-duplicate boundary cases
and the possible NONE over-suppression cases should be included in the next
cross-model review.

## 8. Context growth

The following are character counts from actually assembled Phase 1C/Phase 1D
JSON inputs, reported descriptively. The populations are only cases where the
corresponding artifact existed, so these are not token-equivalent claims.

| Input | Phase 1C N=1–32 median | Phase 1D N=33–64 median | Phase 1D first → last |
|---|---:|---:|---:|
| History retrieval input | 6,238 | 13,594 | 11,392 → 18,107 |
| C input | 33,316 | 61,104 | 44,692 → 74,848 |
| Reconciliation input | 15,389 | 26,906 | 26,734 → 29,282 |
| Reconciliation prompt | 19,366 | 32,173 | 31,941 → 34,843 |

The compact reconciliation context remained much smaller than a raw evidence
archive and no context-limit or malformed-output event was mechanically
attributed to input size. Nevertheless, C and history-retrieval context grew
substantially with history and should be measured in cross-model validation.

## 9. H1, H2, and H3 interpretation

### H1 — history changes future exploration

Supported as a mechanism observation. T activated H on 10/32 suffix tasks,
and those episodes had a `-53` paired action delta, while the 22 no-H episodes
had a `+2` delta. The archive and H-specific candidate sequences therefore
continued to alter future behavior. This does not establish that every H was
correct.

### H2 — history reduces repeated exploratory experiments

Partially supported but unresolved. History was actually retrieved in all 23
auditable C cases. Fifteen of eighteen NONE decisions were consistent with
visible prior comparisons; two were possible over-suppression cases. CREATE
contained three materially different proposals, one justified retest, and one
clear near-duplicate. The evidence argues against systematic overproduction
in this suffix, but it does not establish reliable duplicate suppression.

### H3 — accumulated history improves cumulative search cost

The descriptive signal persisted and strengthened in this continuation:
`Delta(33:64)=-51`, changing the cumulative total from `-41` at N=32 to
`-92` at N=64. The signal is concentrated in H-active tasks. This remains a
single-stream development observation, not a causal or paper-level estimate.

## 10. Correctness assessment

No correctness or infrastructure blocker invalidated the Phase 1D paired
stream:

* source G/T state digests matched the Phase 1C endpoint;
* all 32 suffix pairs passed public pairing checks;
* no task was retried or replaced;
* all model calls were Flash calls under the frozen configuration;
* all target acquisitions and evidence stores were persisted;
* all 32 A stages accepted an epistemic assessment;
* no evidence or H-consumption rollback was observed.

The six B→C source-entity rejections and two malformed C outputs are real
semantic throughput limitations. They were correctly fail-closed and did not
corrupt persistent facts, so they are not classified as an invalid experiment
or as a reason to change the frozen method inside this run.

## 11. Final Phase 1D interpretation

Primary interpretation: **`SCALE_POSITIVE`**, with a known H2 quality
limitation.

The marginal action signal persists, H-active episodes remain the main source
of the difference, active-H backlog does not grow monotonically, and the H2
audit finds limited rather than systematic redundant production. The evidence
does not support a claim of general exploratory-memory superiority, full-task
benefit, or native-cold-start benefit.

## 12. Recommendation

Recommend **`PROCEED_TO_CROSS_MODEL_VALIDATION`** under the exact frozen
Phase 1C/1D protocol. This does not authorize a Max call automatically. A
researcher must separately approve a second model and freeze the comparison
before it runs. If the second-model review reproduces a healthy mechanism,
stop tuning development streams, freeze Method/Evaluation v1, and move to
fresh formal longitudinal streams.
