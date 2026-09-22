# Phase 1F — Cross-Model Attribution and Tuning-Provenance Audit

Date: 2026-09-22
Branch: `exp/minimal-exploratory-memory-validation`
Type: deterministic no-model artifact analysis + historical protocol audit
Status: review complete; no model/API calls authorized

## 1. Purpose

Phase 1E transferred the frozen Flash-developed Phase 1C/1D protocol to an
independent `qwen3.8-max` G/T stream on the same 64 registered tasks. It found a
different behavioral direction, but it did not symmetrically calibrate the
protocol for both backbones. This audit asks what the saved public artifacts
and repository history can attribute, and what remains confounded.

The analysis is descriptive. It does not infer a model's hidden reasoning,
turn a single dependent stream into a causal estimate, or revise the Phase 1E
results.

## 2. Evidence boundary and reproducibility

The deterministic analyzer is:

```text
experiments/exploratory_memory_mvp/analyze_cross_model_attribution.py
```

It joins the frozen Phase 1E registry with the saved Phase 1C, Phase 1D, and
Phase 1E paired summaries and episode artifacts:

```text
experiments/exploratory_memory_mvp/cases/phase1e_cross_model_registry.json
artifacts/exploratory_memory_mvp/phase1c-scale-pilot-v1-20260921-60c2474/
artifacts/exploratory_memory_mvp/phase1d-long-horizon-v1-20260921-ac0bb2b/
artifacts/exploratory_memory_mvp/phase1e-max-combined-reconstruction-v1-20260922/
```

The registry SHA-256 is
`a46ecec068060ccc264dcc994b74e088776b98e3b9f2c31982bfb83a3e5b1a7f`.
The analyzer verifies 64 registered task identities, arm/task/seed identity,
public initial fingerprints, public replay identity fields, valid pairing,
and the action-accounting identity `probe actions + continuation actions =
episode actions`. It projects task-start/end memory to public-facing
Established Memory, future-facing H, comparison state, and saved semantic
decisions. It excludes raw historical evidence, source-only provenance,
hidden PDDL, evaluator answers, oracle routes, and model rationale.

Reproduction command:

```bash
PYTHONPATH=src:experiments:. python -m exploratory_memory_mvp.analyze_cross_model_attribution \
  --repo-root . \
  --output artifacts/exploratory_memory_mvp/phase1f-cross-model-attribution-v1-review-20260922
```

The writer deliberately refuses to overwrite an existing output directory;
choose another unused versioned path for a subsequent rebuild.

This review used the generated local audit at
`artifacts/exploratory_memory_mvp/phase1f-cross-model-attribution-v1-rebuild1/`.
Its `summary.json` SHA-256 is
`e2d27a469e7ca9de2c5093e64b6a141498536dd8a9f78f80c706e0151c9bbf80`; its
`aligned_task_rows.jsonl` SHA-256 is
`7d0cb31a84b69e30d8b4e2cbd1c5df89720d34f2d9042687ad29709ce39d4f64`.
These are derived audit artifacts, not edits to a frozen runtime.

The endpoint is environment actions to exact target acquisition, not full
ALFWorld task completion. `won=false` must not be reinterpreted as a complete
task failure: downstream transformation and placement were outside this
endpoint.

## 3. Aligned Flash/Max behavior

| Global tasks | Flash G | Flash T | Flash Δ T−G | Max G | Max T | Max Δ T−G |
|---:|---:|---:|---:|---:|---:|---:|
| 1–32 | 446 | 405 | −41 | 349 | 378 | +29 |
| 33–64 | 351 | 300 | −51 | 289 | 307 | +18 |
| 1–64 | 797 | 705 | −92 | 638 | 685 | +47 |

By family over all 16 paired tasks per family:

| Family | Flash G/T/Δ | Max G/T/Δ |
|---|---:|---:|
| `pick_and_place_simple` | 224 / 224 / 0 | 192 / 203 / +11 |
| `pick_clean_then_place_in_recep` | 166 / 139 / −27 | 120 / 131 / +11 |
| `pick_cool_then_place_in_recep` | 229 / 182 / −47 | 195 / 197 / +2 |
| `pick_heat_then_place_in_recep` | 178 / 160 / −18 | 131 / 154 / +23 |

The per-task median T−G delta is zero for each model, while the aggregate
differences arise from tails and subgroups. For Max, T was lower/equal/higher
than G on 26/18/20 tasks; the largest T overhead was +14 actions (task 53,
Watch→Safe), and the largest T saving was −12 (task 55, Lettuce→CounterTop).
Thus the +47 is not one single outlier, but neither is it a uniform per-task
penalty. For Flash the corresponding counts were 21/30/13 and the extrema
were +8 and −27.

## 4. Why Max-G is substantially lower than Flash-G

Under the same generic-probe/canonical-continuation protocol, Max-G used 638
actions versus Flash-G's 797, a descriptive difference of −159. The
decomposition is:

| G component, N=1–64 | Flash | Max | Max−Flash |
|---|---:|---:|---:|
| Generic probe environment actions | 194 | 171 | −23 |
| Targets acquired during generic probe | 11 | 30 | +19 acquisitions |
| Canonical continuation actions | 603 | 467 | −136 |
| Total acquisition actions | 797 | 638 | −159 |

The reduction appears across all four families (Max-G lower by 32, 46, 34,
and 47 actions respectively). The saved artifacts therefore support a
straightforward, but still descriptive, explanation: Max's generic selector
more often chose a candidate sequence that acquired the target within the
two-candidate probe, and fewer actions were then spent in continuation. The
per-task G difference is distributed (Max lower on 25 tasks, equal on 18,
higher on 21); maximum savings were −27 actions on tasks 2 and 47. It is not
explained by a single favorable outlier.

This is evidence of a model/backbone difference in the generic policy under
this frozen interface. It does not prove a general capability ranking across
models or environments.

## 5. No-H attribution

Here “no-H” means no H was actually activated by T on that episode. It does
not mean the task was assigned to a separate randomized no-memory condition.
The Phase 1E protocol gives G a generic C2 opportunity on every task, while T
with no activated H goes directly to canonical continuation.

### 5.1 Aggregate decomposition

| Model / interval | n | G actions | T actions | Δ T−G | T lower/equal/higher |
|---|---:|---:|---:|---:|---:|
| Flash 1–32 | 19 | 251 | 256 | +5 | 2 / 14 / 3 |
| Flash 33–64 | 22 | 220 | 222 | +2 | 6 / 12 / 4 |
| Flash 1–64 | 41 | 471 | 478 | +7 | 8 / 26 / 7 |
| Max 1–32 | 21 | 284 | 305 | +21 | 11 / 4 / 6 |
| Max 33–64 | 21 | 208 | 241 | +33 | 11 / 3 / 7 |
| Max 1–64 | 42 | 492 | 546 | +54 | 22 / 7 / 13 |

For Max no-H episodes, paired median Δ is −1 even though the sum is +54. The
aggregate is therefore tail-sensitive: 22 tasks favor T, 7 tie, and 13 favor
G. This is not a universal per-task no-H penalty.

### 5.2 Max-G generic-probe decomposition within no-H tasks

| Post-hoc G probe outcome group | n | G probe actions | G continuation | T continuation | Δ T−G |
|---|---:|---:|---:|---:|---:|
| G probe acquired target | 15 | 46 | 0 | 139 | +93 |
| G probe did not acquire target | 27 | 66 | 380 | 407 | −39 |
| Total | 42 | 112 | 380 | 546 | +54 |

Max-G acquired the target during generic probing on 15 of these 42 tasks. In
that observed subgroup, T's canonical-only path cost 139 actions where G
spent 46 probe actions and no continuation actions. In the 27 probe-miss
tasks, G spent 66 probe actions before continuing; T's total was 39 actions
lower. This makes `GENERIC_PROBE_DIRECT_VALUE` a plausible contributor to the
net cost, but the subgroup is post-hoc and not causal. T and G had separately
evolved Established Memory at task start. In Max no-H cases, the Established
Memory ID sets were the same on all 42 tasks, but full scope/guidance
projections were identical on only 8; content drift remains a confound.

Flash's no-H G probe acquired 8 targets in 41 tasks. Its probe-hit subgroup
contributed +31 T−G actions, while probe-miss cases contributed −24, net +7.
This is directionally consistent with a generic-opportunity cost that is much
larger under Max's stronger observed generic selector, while also showing
that the effect is not just “T skipped C2” on every task.

**No-H attribution label: `MIXED_OR_UNRESOLVED`.** There is direct descriptive
evidence that the generic opportunity often paid off for Max-G. Evolved
Established Memory differs across arms, and no-H task membership is
model-mediated, so the share of +54 attributable to the missing opportunity
cannot be isolated from state and selection differences. The aggregate is
tail-sensitive, not wholly outlier-dominated.

## 6. H-active intervention comparison

| Model / interval | n | G actions | T actions | Δ T−G | H-active T lower/equal/higher |
|---|---:|---:|---:|---:|---:|
| Flash 1–32 | 13 | 195 | 149 | −46 | 7 / 2 / 4 |
| Flash 33–64 | 10 | 131 | 78 | −53 | 6 / 2 / 2 |
| Flash 1–64 | 23 | 326 | 227 | −99 | 13 / 4 / 6 |
| Max 1–32 | 11 | 65 | 73 | +8 | 0 / 7 / 4 |
| Max 33–64 | 11 | 81 | 66 | −15 | 4 / 4 / 3 |
| Max 1–64 | 22 | 146 | 139 | −7 | 4 / 11 / 7 |

The H-active Max subset is near-neutral overall, not strongly adverse. It
changes from +8 in the first half to −15 in the suffix. This is consistent
with useful targeted behavior emerging in some later tasks, but the
post-treatment subgroup is not a causal estimate.

The task traces show a difference in how much H changes the candidate
sequence relative to G. In all 23 Flash H-active episodes, T's saved candidate
sequence differed from G's generic sequence. In Max, it differed on 13/22;
the full sequence was the same on 9/22 H-active tasks. This suggests Max's
targeted proposal often converged on a sequence its stronger generic selector
already chose, reducing the incremental behavioral room for H. It does not
show that those Hs were semantically empty.

The aligned public-facing H summaries, G/T sequences, paired deltas, and A
assessments were reviewed for all 23 Flash and 22 Max H-activated episodes.
Each task summary records actual activation; the corresponding T retrieval
input/response records the public activation context and selected registered
H.

Across the 11 tasks where both models activated an H, Flash's T−G sum was
−62 and Max's was −7. Within this matched subset the saved H preferences and
probe outcomes varied: Max sometimes selected the same sequence as G, while
other tasks used a distinct H-directed candidate and were neutral or
beneficial. Representative paired H/evidence review:

| Task | Flash H → G/T candidates; Δ; A role | Max H → G/T candidates; Δ; A role | What the saved artifacts show |
|---:|---|---|---|
| 2, clean Pan→CounterTop | Type-grouping search; `[cabinet_1,cabinet_2]` → `[cabinet_1,drawer_1]`; 0; SUPPORTING/PARTIALLY_RESOLVED | Semantically likely furniture/storage; `[stoveburner_1,stoveburner_2]` → same; 0; IRRELEVANT/REMAINS_OPEN | H scopes differ and Flash changes its sequence; Max's H and generic selector agree. Neither changes this task's measured action total. Flash T artifact: `artifacts/exploratory_memory_mvp/phase1c-scale-pilot-v1-20260921-60c2474/tasks/02-e5fbb2d17967/T`; Max T: `artifacts/exploratory_memory_mvp/phase1e-cross-model-max-v1-20260922-0ada221/tasks/002-e5fbb2d17967/T`. |
| 7, cool Tomato→Microwave | Perishable-food/fridge-first; `[cabinet_1,cabinet_2]` → `[fridge_1,countertop_1]`; +3; CONTRADICTING/PARTIALLY_RESOLVED | Scope text describes clean/hygiene-item search, although this is a cool-Tomato task; G and T both `[fridge_1,countertop_1]`; 0; INCONCLUSIVE/REMAINS_OPEN | A possible scope/retrieval compatibility concern is visible, but the H's guidance overlaps the selected public search direction. The identical G/T sequence means no incremental candidate change in this episode. |
| 55, cool Lettuce→CounterTop | Perishable food/open surfaces; `[cabinet_1,cabinet_2]` → `[countertop_1,countertop_2]`; −9; SUPPORTING/PARTIALLY_RESOLVED | Root-vegetable/open horizontal surfaces; `[fridge_1,countertop_1]` → `[countertop_1,countertop_2]`; −12; IRRELEVANT/REMAINS_OPEN | Both Hs direct the same public candidate sequence and both have lower paired action totals, despite different A interpretations. This is evidence that Max H can be behaviorally useful; it does not explain why Max A did not treat the evidence as comparative. Flash T: `artifacts/exploratory_memory_mvp/phase1d-long-horizon-v1-20260921-ac0bb2b/tasks/055-2763e0c4f901/T`; Max T: `artifacts/exploratory_memory_mvp/phase1e-cross-model-max-v1-20260922-0ada221/tasks/055-2763e0c4f901/T`. |
| 62, clean Cloth→Cabinet | Cloth/towelholder-specific; `[cabinet_1,cabinet_2]` → `[handtowelholder_1,handtowelholder_2]`; −2; CONTRADICTING/PARTIALLY_RESOLVED | Cloth/fabric-holder-specific; `[cabinet_1,countertop_1]` → `[towelholder_1,handtowelholder_1]`; −1; IRRELEVANT/REMAINS_OPEN | Both Hs use a related public carrier-class preference and both change the generic sequence; A's evidence interpretation still diverges. Max T is in the authorized resume segment: `artifacts/exploratory_memory_mvp/phase1e-max-resume-v1-20260922-authorized-continuation/tasks/062-ebd57bd3ea43/T`; Flash T: `artifacts/exploratory_memory_mvp/phase1d-long-horizon-v1-20260921-ac0bb2b/tasks/062-ebd57bd3ea43/T`. |

The table also illustrates why aggregate H quality cannot be assigned a
single score: there are matching/useful sequences (task 55), an H scope that
does not cleanly match the task family (task 7), and H-induced sequence
changes with no action saving (task 62). The task 7 mismatch may reflect an
overbroad retrieval or scope, but the present artifact alone cannot determine
which component caused it.

**H-quality reading:** Max H was not uniformly more redundant. The frozen
manual Max H2 audit classified 27/35 visible-history CREATE proposals as
materially different, 5 justified retests, and 3 near-duplicates; two parsed
NONE outputs were split one reasonable suppression/one possible
over-suppression, with two parse failures unclassified. Flash's combined
Phase 1C/1D reviewed CREATE cases were predominantly distinct or justified,
with two confirmed duplicates across 25 CREATEs. The strongest distinction
is therefore not simply “Max H is worse”: Max created far more often and its
H often overlapped the generic sequence, while many proposals remained
meaningfully scoped.

## 7. Memory-evolution regime and comparison status

| N=64 mechanism state | Flash | Max |
|---|---:|---:|
| B OPEN / NONE | 63 / 1 | 62 / 0 (2 invalid B outputs) |
| B→C fail-closed handoff rejects | 7 | 21 |
| C CREATE / NONE | 26 / 28 (2 invalid) | 37 / 2 (2 parse/schema failures) |
| H total / active / consumed | 26 / 3 / 23 | 35 / 8 / 22 (5 superseded) |
| Exploration History | 23 | 22 |
| Comparisons | 21: 17 partial, 4 open | 21: all open |
| T A evidence roles (64 T episodes) | 17 support, 5 contradict, 42 irrelevant | 1 contradict, 7 inconclusive, 56 irrelevant |
| T A comparison assessments (64 T episodes) | 22 partial, 42 remain open | 64 remain open |
| Reconciliation identity ops | 21 ADD, 10 REFINE, 25 NO_NEW_H | 21 ADD, 14 REFINE, 4 NO_NEW_H; 2 invalid |

The strongest artifact-grounded explanation for the `17 PARTIALLY_RESOLVED`
versus `21 OPEN` endpoint is the A epistemic assessment stream, not a hidden
epistemic power in reconciliation. Phase 1B contracts give A authority to
interpret actual consumed-H evidence; consolidation reconciles H/comparison
identity and cannot set epistemic status. Flash produced 22
`PARTIALLY_RESOLVED` assessments and 17 partial ledger entries. Max produced
no assessment beyond `REMAINS_OPEN`, and its 22 H-active episodes were mostly
`IRRELEVANT` or `INCONCLUSIVE` (14/22 and 7/22, respectively), with one
`CONTRADICTING`. Flash's H-active A roles were 17 `SUPPORTING`, 5
`CONTRADICTING`, and 1 `IRRELEVANT`.

This is a model-dependent semantic-output difference under the same frozen A
contract. It may also reflect different H content, selected probes, and
resulting evidence; the artifact comparison does not isolate A-model
calibration from evidence-distribution differences. Reconciliation counts
also differ, and Max's invalid reconciliation outputs can reduce identity
quality, but they cannot explain epistemic status because status is not its
authority. The fact that both models ended with 21 comparisons despite
different C throughput further cautions against reading comparison count as
epistemic progress.

The Max regime also had more C→H pressure: 37 valid CREATE vs 2 NONE, compared
with Flash 26 CREATE vs 28 NONE. Max had 21 B→C rejections versus Flash 7;
these are fail-closed quality limitations, not leakage into C. The Max H2
review did not find systematic duplicate creation, but Max's higher CREATE
rate, larger active backlog (8 vs 3), and all-open comparisons are legitimate
memory-evolution regime differences to test rather than fix post hoc.

## 8. Protocol development and tuning provenance

Classification meanings:

* `MODEL_AGNOSTIC_CORRECTNESS`: mechanical safety/identity invariant; not a
  preference calibrated to a model's outcomes.
* `FLASH_CONDITIONED_DEVELOPMENT`: repository evidence shows observed Flash
  behavior materially motivated a change.
* `SCIENTIFIC_PROTOCOL_CHOICE`: frozen design choice defining the contrast or
  measurement, not a model-tuned repair.
* `MIXED`: scientific design plus correctness or empirical adaptation with
  model-observed motivation.

| Component | Classification | Provenance and model exposure |
|---|---|---|
| A prompt/schema | `MIXED` | Initial system in `436307a`; prompt/operation contracts were adjusted in the Phase 1B batch (`d9f14a1`, docs/89) after the Flash-based Round-0 findings; layered epistemic/update fault isolation was later hardened as correctness (`c8daa67`, docs/100–101). |
| B prompt/schema | `FLASH_CONDITIONED_DEVELOPMENT` | Early B/C boundary and retest changes are recorded in docs/45 and commit `f5431ab`; Phase 1B Round-0/1 review used Flash semantic outputs, and the single batch changed B/A-facing endpoint language (docs/89). |
| B Functional Contract | `MIXED` | B-vs-C responsibility split is a scientific choice; later abstraction and source-answer tightening followed observed Round-1 leakage behavior (docs/91–96). |
| B→C firewall | `MIXED` | The projection/fail-closed boundary is a model-agnostic correctness rule, but its tightening was triggered by Flash Round-1 Task 3 indirect source-answer leakage (`b4928a0`, `0745fcd`, docs/91–94). |
| C prompt/schema | `MIXED` | Local facts/future-facing hypothesis boundaries are method constraints. Mechanical future-entity rejection and handoff conditioning were hardened after Flash Task 4/other saved-output failures (docs/49, docs/91–97). |
| C CREATE/NONE | `MIXED` | CREATE/NONE defines C's semantic role; history-visible proposals/NONE behavior and schemas were developed using Flash outputs in Phase 1C/1D (docs/87–89, 104–111). NONE has no reason field, so no rationale may be inferred. |
| H schema | `MIXED` | Source-grounding/future-facing separation is a method boundary; the mechanical firewall matured in response to observed source-entity leakage (docs/92, 96–101). |
| H one-shot lifecycle | `SCIENTIFIC_PROTOCOL_CHOICE` | One activation, consumption, and archive-on-actual-test were frozen as the hypothesis protocol before the Phase 1C/1D value run; not an outcome-driven repair. |
| Active-H retrieval | `SCIENTIFIC_PROTOCOL_CHOICE` | At most one active H with an abstention option is the frozen online policy; no evidence shows model-specific retrieval tuning before Phase 1E. |
| Exploration-history retrieval | `MIXED` | Offline-only, B=OPEN gate, top-3 real IDs were fixed to address repeated proposal risk; implementation/semantic observations were primarily Flash-informed, but selection was not outcome-ranked post hoc (docs/38, 88–89, 103–111). |
| Archive semantics | `MIXED` | “This experiment was tried” rather than true/false/confidence is a lifecycle/scientific constraint. Archive contents and use were assessed through Flash development artifacts, not calibrated separately for Max. |
| Comparison identity/reconciliation | `MIXED` | Identity-only authority is a method/correctness boundary. Prompt/schema and validators evolved after Flash evidence-reference, duplicate identity, and unsupported-status outputs (commits `985431c`, `d9f14a1`, `b4928a0`; docs/89–101). |
| Generic C2 | `SCIENTIFIC_PROTOCOL_CHOICE` | Generic candidate probing was frozen as the comparator in the Phase 1A controlled targeting plan/runner (`4462b1e`, `8103a79`, docs/83–85). No repository evidence shows C2 was tuned to help Flash or harm Max. |
| T no-H → canonical continuation | `SCIENTIFIC_PROTOCOL_CHOICE` | Deliberately defines targeted-H availability: no activated H means no generic fallback. It was frozen before Phase 1C and transferred unchanged; Phase 1C review explicitly notes this makes aggregate T−G an arm-protocol contrast, not pure H-content effect (docs/104–105, 103). This is a major asymmetry, not an accidental code bug. |
| Candidate budget = 2 | `SCIENTIFIC_PROTOCOL_CHOICE` | Shared cap frozen for G/T to define the controlled local-search opportunity; no evidence it was adjusted after Phase 1E outcomes (docs/83, 102–103). |
| Canonical continuation | `SCIENTIFIC_PROTOCOL_CHOICE` | Deterministic common continuation is a deliberate measurement instrument, not a model-specific planner. It was frozen for Phase 1C/1D and reused in Phase 1E. |
| Controlled acquisition endpoint | `MIXED` | Exact target acquisition is a deliberate narrow endpoint, not full task completion. Wording in A/B was clarified after Flash outputs confused `won=false` with task outcome (docs/105, 110–111); the endpoint itself remained unchanged. |
| Pairing, fact commit, legal exact-target execution, provenance binding | `MODEL_AGNOSTIC_CORRECTNESS` | These invariants constrain all model conditions. Phase 1E's segmented resume and state/pairing checks were mechanical, not model-adapted. |

### Asymmetric empirical exposure

1. The Phase 1B semantic stack (notably A/B/C/reconciliation prompts and
   schemas) had substantial Flash development exposure. Phase 1B's one tuning
   batch followed a 12-task Flash stream; the later correctness hardening also
   drew on Flash trace failures. The selector had separate Max use, but that
   does not make all offline semantics model-neutral.
2. Phase 1C and 1D then ran the complete evolving G/T process on Flash. Their
   prompts and state evolution were reviewed on Flash artifacts before being
   transferred unchanged into the independent Max stream.
3. Phase 1E is therefore a genuine **frozen-protocol cross-model transfer**
   test, but not a symmetric model-specific adaptation comparison.
4. Pairing, evidence persistence, exact identity, and fail-closed leakage
   checks should remain model-agnostic. They must not be relaxed to improve
   either model's score. H one-shot semantics and the acquisition endpoint are
   scientific protocol choices, not knobs to tune from this discrepancy.

## 9. Competing explanations

| Explanation | Evidence for | Evidence against / unresolved | Minimal discriminator |
|---|---|---|---|
| `BASE_POLICY_CAPABILITY` | Max-G used 159 fewer actions; generic-probe target acquisitions were 30 vs 11; continuation cost fell 136 actions. In no-H Max episodes, the generic probe acquired 15 targets. | One development population; task histories and Established Memory evolved independently by model. Better G does not alone explain Max's A/C/state regime. | On fresh matched tasks compare G, unchanged T, and a single pre-registered no-H-composition variant for both models; keep the model-role/config fixed within each stream. |
| `PROTOCOL_TRANSFER_MISMATCH` | T no-H omits C2 while G gets it every task; this asymmetry was intentionally frozen, not model-calibrated. Max no-H Δ is +54 and its G probes often acquire targets. Phase 1C/1D protocol/prompt development was Flash-conditioned. | Max H-active Δ is −7 overall and −15 in tasks 33–64; no-H result is confounded by separate evolved Established Memory. This does not prove the protocol is mismatched rather than capability-dependent. | Apply one identical T no-H policy change to both backbones and measure it against G and the frozen T composition on a disjoint held-out stream. |
| `MEMORY_EVOLUTION_REGIME_SHIFT` | Max has 37 CREATE/2 NONE, 21 B→C rejects, 8 active H, 21/21 comparisons OPEN, and no A assessment beyond REMAINS_OPEN; Flash has 26/28, 7 rejects, 3 active, and 17 partial comparisons. | Max H2 was mostly distinct/justified, H was actually activated, and no state corruption was found. The difference may be caused by different evidence/H rather than a defective Max protocol. | Keep all prompts/semantics frozen in the candidate test and annotate A/B/C/lifecycle trajectories; do not change A together with the primary policy manipulation. If it remains the leading issue, require a separately authorized follow-up rather than an in-run patch. |
| `MIXED` | Capability, intentional arm asymmetry, Flash-conditioned prompt development, and model-dependent A/B/C outputs all have direct artifact support. | Relative contribution of each factor is not identifiable from one stream/model and different evolved states. | Small symmetric matched-adaptation test; report the remaining state/evidence mediation explicitly. |
| `INSUFFICIENT_EVIDENCE` | There is no randomized assignment of H activation and no independent stream replication. | Several mechanical splits are strong and reproducible from saved traces; “nothing can be said” would underuse evidence. | Treat uncertainty as limits on attribution, not a reason to discard the descriptive findings. |

**Leading attribution: `MIXED`.** The strongest directly measured component is
the Max-versus-Flash generic-policy difference. The strongest design
confound is T's intentional no-H omission of the generic opportunity,
transferred without model-specific calibration. Model-dependent semantic
memory evolution is also substantial, especially A's comparison assessments
and B→C/C throughput. None alone is established as the primary cause of the
full +47.

## 10. What Phase 1E establishes—and does not

Phase 1E establishes that, on the same frozen 64-task development population,
an independent Max process formed and activated history-derived memory under
the transferred protocol, while its cumulative T arm used 47 more
target-acquisition actions than its paired G arm. Flash on the same task
population showed −92. It demonstrates **cross-model transfer non-robustness
of the current frozen G/T protocol's behavioral direction** on this stream.

It does **not** establish:

* that exploratory memory cannot help strong models;
* that Max failed only because it was untuned;
* a causal effect of H content alone (G/T no-H opportunities differ);
* full task completion, native cold-start performance, general memory
  superiority, or cross-benchmark generality;
* the result after reasonable symmetric model-specific/interface calibration.

The precise claim is conditional on the tested model, frozen prompts, memory
states, intentional no-H composition, controlled acquisition endpoint, and
one dependent stream per backbone.

## 11. Remaining uncertainty and recommendation

The next useful discriminator is a single bounded test of the no-H
composition, because it directly targets the largest visible Max cost source
without changing B/C/A semantics. Apply the same change to both models; retain
G and the original T protocol as references. Details and fixed budgets are in
`docs/121_phase1f_matched_adaptation_validation_plan.md`.

This is a proposed validation test, not current execution authority. No model
or API calls are authorized by this audit. Formal evaluation remains
unauthorized. The inspected Phase 1D registry's residual eligible family
counts (5 simple, 12 clean, 3 cool, 4 heat) cannot supply the proposed
calibration-plus-held-out allocation; this is not a full-corpus shortage
finding. The plan therefore has no frozen Phase 1F task membership and
requires a separate no-model public census that excludes all prior used IDs,
the protected B1-R reserve, and any formal holdout.
