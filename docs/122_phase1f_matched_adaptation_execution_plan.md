# Phase 1F-MA — Matched-Adaptation Execution Plan

Date: 2026-09-22

Branch: `exp/minimal-exploratory-memory-validation`

Status: preparation authorized; **population gate failed**, so there is no
selected registry, transition, or model execution in this cycle. See
`docs/123_phase1f_population_gate_blocker.md`.

The versioned runner/analyzer and fake-transport tests were prepared and
verified without model/API calls. They do not contain a selected population
and cannot open the failed gate.

Protocol: `phase1f-matched-adaptation-v1`

## 1. Purpose and evidence boundary

This is a bounded development validation of exactly one adaptation dimension:
the no-activated-H composition in T. It is not a new open-ended tuning cycle,
a confirmatory evaluation, or a paper-level superiority test. It follows the
Phase 1F attribution in `docs/120` and refines the proposed protocol in
`docs/121`.

The experiment asks whether giving T the frozen generic C2 opportunity only
when it has no activated H changes the Flash/Max attribution picture. It does
not select a policy by trying variants until one beats G.

No model/API call is permitted until all of these are true:

1. a public-only census establishes a disjoint development/formal population
   boundary and at least four eligible fresh tasks per family;
2. the selected 16-task registry, task order, seeds, replay specs and public
   initial fingerprints are frozen and committed;
3. T1 code, analysis code and no-model checks are frozen and committed in the
   immutable transition;
4. the active repository contract is updated and reread to reflect the
   specific authorization for the six frozen streams.

The population/public-formal separation gate was audited against the frozen
public registries and local split inventory and failed. Stop before model
calls. Do not shrink to 12, borrow B1-R, consume a protected formal pool, or
create a nominal transition without a frozen eligible registry.

## 2. One permitted composition change

The arms are:

| Arm | Per-task probe policy |
|---|---|
| `G` | Frozen generic C2, at most two candidate probes, then canonical continuation if needed. |
| `T0` | Frozen active-H retrieval. Valid H activation uses the frozen targeted probe. Valid NONE/empty active pool goes directly to canonical continuation. |
| `T1` / `T-Hybrid` | Same active-H retrieval. Valid H activation uses exactly the frozen T0 targeted probe. Valid NONE/empty active pool uses frozen generic C2 with T1's own current Established Memory, then the same canonical continuation if needed. |

T1 does not call C2 after a valid H activation. An invalid/error H retrieval
retains the frozen fail-closed behavior and does not become a no-H fallback.
The only policy difference between T0 and T1 is the valid no-H branch.

On T1 no-H episodes, generic C2 is ordinary generic exploration, not an H. It
does not activate or consume an H, enter Exploration History, bind to a
comparison, or increment H lifecycle counts. Its real public observations and
actions remain in the episode evidence and continue through the unchanged
offline A/B/C pipeline. With no H consumed, A receives no synthetic
comparison attribution.

## 3. Population design and protection gate

The required population is exactly 16 fresh development-only tasks:

```text
4 pick_and_place_simple
4 pick_clean_then_place_in_recep
4 pick_cool_then_place_in_recep
4 pick_heat_then_place_in_recep
```

Interleave in the frozen family order `simple → clean → cool → heat`, repeated
four times. Use a committed deterministic salt and stable public hashing.
Selection is without replacement and before any Phase 1F arm outcome.

The census must enumerate all available pinned/public ALFWorld split task IDs
and use only public entry-time information for eligibility: public task/family
identity, instruction, reset observation, ordered admissible actions and
public affordances. Apply the already frozen controlled-search eligibility
predicate: a successful public reset, parseable public target, no exact target
take action visible at entry, and at least two public candidate receptacles.
Persist each inclusion/exclusion reason. Do not read PDDL, hidden placement,
oracle routes, outcomes or expected winners.

Before selection, exclude every task used or reserved by Phase 1A–1E, Phase 1B
development, protected B1-R, and any other committed protected population.
The census must identify a whole split or an equally auditable boundary for
Phase 1F development and leave a distinct public split/population untouched
for future formal confirmatory evaluation. Do not infer this boundary from a
small residual registry. Record the exact boundary and disjointness proof in
the transition. If no defensible separation exists, stop and return for
researcher review.

Persist the full public census, prior/protected exclusion manifest, formal
reserve boundary, eligible development universe, selected tasks/order,
requested seeds, replay specs, public fingerprints, registry SHA-256 and
selected-ID SHA-256. The selected registry must contain no source-only or
hidden outcome fields.

## 4. Fresh, independent streams

Run six independent longitudinal streams over the same 16 task/replay
identities:

```text
Flash-G   Flash-T0   Flash-T1
Max-G     Max-T0     Max-T1
```

Each stream starts from the same Phase 1 warm-start specification but owns
independent mutable state:

```text
G:  canonical K*
T0: canonical K*, with empty active H, consumed H, archive and comparison ledger
T1: canonical K*, with empty active H, consumed H, archive and comparison ledger
```

No state or model output is imported from Phase 1C/1D/1E or shared across
streams. Within a stream, tasks execute sequentially. Independent streams may
run in parallel only if the provider/runtime can safely isolate their
artifacts; sequential stream scheduling is acceptable.

Every role within a stream uses one model:

```text
Flash: qwen3.8-flash, thinking=false, temperature=0
Max:   qwen3.8-max,   thinking=false, temperature=0
```

No model-specific prompt changes or mixed-role models are allowed.

## 5. Fixed outcomes and reporting

The primary outcome is environment actions to exact target acquisition. For
each model report per-task values and paired contrasts:

```text
T1 - T0   # primary adaptation contrast
T0 - G
T1 - G
```

Summarize by family and first/second half; do not require statistical
significance. Report T0/T1 H-active and no-H subsets descriptively. For T1
no-H episodes also preserve the generic candidate sequence, generic probe
action count, direct acquisition-in-probe indicator, and continuation action
count.

Mechanism observations remain secondary and minimal: H creation/activation and
backlog, archive size, B OPEN/NONE/errors, C CREATE/NONE/errors, A evidence
role/comparison assessment, comparison status/identity operations, and
failure/context telemetry. Do not redefine metrics after results.

## 6. No-model compatibility verification (replaces paid calibration)

The four-task model calibration block proposed in `docs/121` is intentionally
removed. It offered no post-calibration selection or parameter adaptation and
would consume fresh task episodes without answering a separate scientific
question. This execution plan replaces it with no-model compatibility and
smoke verification:

* unit and fake-transport tests for T0/T1 branch routing and lifecycle;
* carrier public-reset preflight for all 16 selected tasks, checking the
  frozen public fingerprints without solving tasks;
* branch-coverage proving the T1 H-active and no-H paths;
* prepare-only mode proving no model transport is initialized;
* paired replay/public-state identity checks for all arms.

This smoke phase makes zero model/API calls and executes no candidate probe or
task-solving action. It does not consume additional scientific tasks.

## 7. Execution discipline

After the immutable transition is pushed, execute exactly:

```text
16 tasks × 6 independent streams = 96 episodes
```

No retries, task replacements, prompt/model/policy changes, result-driven
stopping, second adaptation, or fallback model. Preserve scientific/model
failures. A genuine infrastructure failure may stop the affected execution;
do not silently rerun it.

## 8. Interpretation categories

Use the categories frozen by the researcher:

* `COMPOSITION_MISMATCH_GENERAL`
* `TRANSFER_MISMATCH_SUPPORTED`
* `CAPABILITY_DEPENDENCE_REMAINS`
* `MEMORY_EVOLUTION_REGIME_REMAINS`
* `INSUFFICIENT_EVIDENCE`
* `INVALID`

Interpret both action outcomes and offline-state changes. If T1 changes A
assessments, C CREATE/NONE, comparison closure or H backlog as well as online
cost, describe the online-composition/offline-evolution coupling; do not call
it merely an immediate generic-probe benefit. This remains development
evidence, and formal evaluation remains unauthorized pending researcher
review.
