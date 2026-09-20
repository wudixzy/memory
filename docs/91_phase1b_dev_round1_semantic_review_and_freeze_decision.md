# Phase 1B-Dev Round-1 Semantic Review and Freeze Decision

## Review boundary

This review reads the saved Round-1 artifacts at:

`artifacts/exploratory_memory_mvp/phase1b-dev-round1-20260920-d9f14a1`

and compares them with the Round-0 artifacts at:

`artifacts/exploratory_memory_mvp/phase1b-dev-round0-20260920-985431c-env39`.

There was no Round-2 and no additional model call.  The old 12-task stream
remains development-only.

## 1. Task-by-task review

### 1 — SprayBottle → Toilet

Round-1 artifact: `tasks/01-fe5a5bac7cf1`

The endpoint patch changed B from Round-0 `NONE` to `OPEN`.  B identifies the
first low-information receptacle visit (`bathtubbasin_1`) versus a
semantically likely surface and C creates a future-facing object-type search
H grounded at `go to countertop_1`.  A returns `NO_CHANGE` and keeps both
search-order questions unresolved.  This is a plausible acquisition-level
comparison, and the H does not contain source entity IDs outside
`source_grounding`.

The new behavior is useful but also broadens the comparison family from
open-surface versus closed-storage ordering to object-type semantic priors.
The run does not establish whether that is the same comparison or a distinct
one.

### 2 — Apple → Fridge (clean)

Round-1 artifact: `tasks/02-f13421bdbb8a`

The task retrieves the H created in task 1.  Its probe selects
`diningtable_1` and acquires the apple in two actions.  This is the clearest
Round-1 chain of H creation → retrieval → probe evidence → A update.

However, A's `evidence_basis` says the apple was visible in the *initial*
observation.  The saved `initial_state.json` lists `diningtable_1` but does not
list `apple_3`; the apple appears only in the observation after navigation in
the probe trace.  A has therefore confused a later public observation with
entry visibility.  The update itself is scoped and unresolved, but the
temporal evidence attribution is not reliable.

### 3 — Pot → Shelf (cool)

Round-1 artifact: `tasks/03-b74ce78e8759`

The H from task 2 is consumed.  B says `pot_2` was visible on `countertop_3`
in the initial observation, but the saved `initial_state.json` contains only
the receptacle entity list; the target appears later in the continuation.
C then proposes direct navigation to `countertop_3` and uses it as its
source-grounded entry action.  This is a source-answer leakage path through
B's diagnosis: C did not receive the full trajectory directly, but B's
model-generated diagnosis carried the later source entity into the C input.

The mechanical local-C check did not reject this because it only excluded the
completed trajectory, not every source-specific answer repeated by B.  The
new comparison is therefore not trustworthy as a clean local-C instantiation.

### 4 — Egg → GarbageCan (heat)

Round-1 artifact: `tasks/04-6ce98e7a5d4c`

The public continuation acquired `egg_1` at `countertop_2` after 21 actions;
the evidence package is present.  C nevertheless emitted `countertop_1` and
`countertop_2` in `probe_spec.adaptive_policy`, outside `source_grounding`.
The future-H validator rejected the candidate with:

`Future-facing H contains a source entity id`

The runner preserved the raw C response and marked the task failed before
materializing post-task memory.  This is a genuine C boundary failure, not an
infrastructure outage.  Fail-closed behavior is correct, but the closed loop
cannot be called healthy when a source-answer-like H is generated in one of
the 12 tasks.

### 5 — Lettuce → DiningTable (cool)

Round-1 artifact: `tasks/05-2c4282a03bda`

B/C propose a fridge/domain-prior search comparison.  A abstains.  The
reconciliation raw response uses `EVIDENCE_OBTAINED` as an evidence reference
and is rejected.  The strengthened reconciliation input explicitly supplied
`current_evidence_id` and `available_evidence_refs`, so this is not fixed by
the batch and remains a model/interface execution failure.

### 6 — Egg → SideTable (heat)

Round-1 artifact: `tasks/06-5d23b34e43af`

The endpoint patch prevents the Round-0 `NONE because won=false` failure. B
opens an acquisition-level search comparison, C creates a grounded local H,
and A conservatively returns `NO_CHANGE`.  Reconciliation adds a new open
comparison.  This is an improvement in endpoint interpretation, although the
new comparison identity is not clearly related to the earlier open-surface
comparison.

### 7 — Ladle → DiningTable (clean)

Round-1 artifact: `tasks/07-da7ce681f998`

B/C create a visible-first candidate.  The reconciliation model's rationale
recognizes that its candidate is effectively the same as an active
open-surface H, but still emits `ADD`/`NEW`; it also emits
`EVIDENCE_OBTAINED` as a ref.  The validator rejects the response.  This is
direct evidence of comparison identity drift and unresolved evidence-binding
failure, not merely a cosmetic schema problem.

### 8 — Bread → CounterTop (cool)

Round-1 artifact: `tasks/08-44c3f607e337`

The H is retrieved and probes `diningtable_1` and `countertop_1`; the target
is acquired later at `countertop_2`.  A produces a scoped update and keeps
comparative questions unresolved.  Reconciliation returns
`REFINE_EXISTING`, `keep_candidate_h=false`, and `comparison_status=RESOLVED`.

The available trace contains one H probe plus a continuation acquisition; it
does not provide a matched incumbent/alternative comparison that justifies
global resolution.  The status transition is therefore an unsupported
semantic closure.  It also differs from the many other responses that keep
the same type of evidence `OPEN`.

### 9 — Book → Sofa

Round-1 artifact: `tasks/09-b878c93dba49`

The target is acquired immediately through the public direct-visibility path.
B returns `NONE` consistently with the established direct-navigation memory,
and A returns `NO_CHANGE`.  This is a useful negative/control case.  It does
not repair the broader temporal attribution issue because the role outputs
are short and the direct target is already part of the first public state in
this case.

### 10 — Mug → Cabinet (heat)

Round-1 artifact: `tasks/10-c54897aeed0d`

B/C diagnose an open-surface alternative and A emits a scoped unresolved
update.  Reconciliation again uses `EVIDENCE_OBTAINED` instead of an actual
evidence ID and fails closed.  The task preserves its B/C/A artifacts, but no
H/comparison materialization is valid.

### 11 — DishSponge → Toilet (clean)

Round-1 artifact: `tasks/11-c97d1a722822`

The target is acquired immediately from a public direct-visibility state. B
returns `NONE` because an established direct-navigation memory already
explains the behavior; A returns `NO_CHANGE`.  This is semantically
reasonable and demonstrates that the endpoint patch does not force OPEN on
every acquisition trace.

### 12 — Apple → GarbageCan (heat)

Round-1 artifact: `tasks/12-32c555941b2f`

B/C diagnose open-surface priority and A returns a scoped update with
unresolved questions.  This is better calibrated than Round-0 task 12, whose
`still_unresolved` was empty.  Reconciliation nonetheless emits
`ADD`/`NEW` while explicitly saying that an existing comparison is `RESOLVED`,
and uses `EVIDENCE_OBTAINED` as a ref.  The validator rejects it.  This is a
second direct example that the batch did not stabilize comparison identity or
evidence references.

## 2. Root-cause status after the one batch

| Round-0 root cause | Round-1 status | evidence |
|---|---|---|
| Acquisition endpoint was unclear to B/A | `PARTIALLY_FIXED` | task 1 now opens a comparison; task 6 no longer rejects acquisition solely because `won=false`; task 2/3 still misattribute observation timing |
| Reconciliation evidence refs/operation targets | `UNCHANGED` | four validation failures in tasks 5, 7, 10, 12 despite explicit ref lists |
| A dropped unresolved uncertainty | `IMPROVED` | task 12 and other updates retain unresolved questions; this part of the batch is promising but not sufficient alone |
| Near-duplicate comparison/H identity | `REGRESSED` | Round-1 ends with three comparison IDs; task 7 explicitly recognizes a duplicate but chooses `ADD`; task 8 marks a still-open search issue `RESOLVED` |
| C source/future separation | `REGRESSED / NOT FIXED` | task 3 receives a later source entity through B diagnosis; task 4 future H contains source IDs and is rejected |
| H activation/consumption lifecycle | `MECHANICALLY FIXED` | task 2 and task 8 show activation and consumption; no consumed H was silently reactivated |

## 3. Closed-loop evidence

There is one meaningful partial chain:

`task 1 C creates h-fee841cb3e0fa22a`
→ `task 2 retrieval activates it`
→ `task 2 probe acquires apple in two actions`
→ `task 2 A emits a scoped direct-visibility update`.

This supports that the runtime can carry a future-facing H into a later task
and that H can change the controlled search behavior.  It does **not** show
that the H's hypothesis is comparatively true: the task has no matched
incumbent/alternative outcome and A itself preserves unresolved questions.

The chain is also not enough for freeze because the same stream contains the
C source-answer boundary failure and repeated reconciliation failures.

## 4. Final freeze decision

### `NOT_READY_METHOD_RETHINK`

The longitudinal implementation is not semantically healthy enough to freeze
for a fresh 40–60 task scale experiment.  The decision is not a claim that a
particular model is incapable.  It is based on method/contract evidence:

1. 4 of the 8 reconciliation calls that reached the stage fail the explicit
   evidence-reference contract;
2. comparison identity drifts into multiple related records, including an
   unsupported `RESOLVED` status;
3. C can still carry source-specific entity IDs into future-facing H, and B's
   diagnosis can leak later source entities into C indirectly;
4. one of the 12 Round-1 task states fails before memory materialization;
5. a successful H→probe→A chain exists, but its epistemic interpretation is
   not yet reliable enough for scale evaluation.

Per the frozen protocol, there is no Round-2 and no additional tuning in this
cycle.  The next step requires researcher-level method/interface redesign
review, not a larger task run or a new model sweep.

## 5. Prohibited next steps from this cycle

Do not use the old 12 tasks as an independent gate, do not run fresh targets,
do not start a 40–60 task experiment, and do not claim C3 value or full
persistent-memory effectiveness.  The Round-0 fail/negative evidence and all
Round-1 raw artifacts remain preserved for redesign review.
