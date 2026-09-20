# Phase 1B-Dev Round-0 Semantic Review

## Review scope and evidence rule

This review reads the saved Round-0 artifacts directly.  The runtime root is:

`artifacts/exploratory_memory_mvp/phase1b-dev-round0-20260920-985431c-env39`

The 12 task directories are the `tasks/*` children of that root.  Judgments
below refer to fields in `initial_state.json`, `execution.json`,
`evidence_package.json`, `retrieval/*`, `probe/*`, `a/*`, `b/*`, `c/*`,
`h_reconciliation/*`, `memory_before.json`, and `memory_after.json`.  No
hidden reasoning, PDDL placement, evaluator label, or oracle trajectory was
used.

The controlled loop deliberately stops at exact target acquisition.  The
environment's `won=false` therefore means that downstream clean/heat/cool/
place was not run, not that the public search endpoint failed.  This was not
made sufficiently explicit to every offline role; that distinction is
reviewed as a system-level issue below.

## 1. Task-by-task review

### Task 1 — SprayBottle → Toilet

Artifact: `tasks/01-fe5a5bac7cf1`

- Retrieval abstained because the active H pool was empty.
- The canonical continuation inspected `bathtubbasin_1`, observed `cloth_1`,
  then inspected `countertop_1` and took `spraybottle_1` at environment step
  3.  The exact sequence is in
  `continuation_search/continuation_trace.json`.
- B returned `NONE`.  This is semantically reasonable: the trace gives no
  discriminative comparison and the incumbent search reaches the object in
  two candidate inspections.  B's wording nevertheless describes the task as
  incomplete because `won=false`; that is endpoint confusion, not a reason to
  reopen a comparison.
- A returned `NO_CHANGE`, preserving the fact that no full placement result
  exists.  It did not invent comparative superiority.

Overall: healthy abstention and conservative update, with a repeated
acquisition-endpoint interpretation problem.

### Task 2 — Apple → Fridge (clean)

Artifact: `tasks/02-f13421bdbb8a`

- The public continuation checks cabinets `12` through `1`, then other
  receptacles, and acquires `apple_3` at `diningtable_1` after 26 environment
  actions.  The public sequence is recorded in
  `continuation_search/continuation_trace.json` and the terminal observation
  is in `execution.json`.
- B returns `OPEN` for the local cabinet-first versus open-surface search
  comparison.  The target segment and policy relevance are sensible; B does
  not name a concrete future entity as the alternative.
- C returns a grounded surface-first H.  Its entry action is
  `go to diningtable_1`, which is legal in the entry admissible-action list in
  `c/mechanical_grounding.json`.  The future policy is a local adaptive
  search pattern, not a fixed source route.
- A returns `NO_CHANGE` and explicitly retains uncertainty because only the
  incumbent was observed.  This is the appropriate conservative reading.
- Reconciliation returns `ADD` and creates
  `comparison-d10eb76341533b5b` plus `h-8193de80dea8dde3`.  The same current
  evidence is referenced as both supporting and inconclusive in
  `h_reconciliation/reconciliation_parsed.json`; this is not fatal, but it
  indicates that the evidence-role contract is underspecified.

Overall: the cleanest B→C→H creation case, but it is feasibility/inefficiency
evidence for the incumbent, not comparative proof of the new policy.

### Task 3 — Pot → Shelf (cool)

Artifact: `tasks/03-b74ce78e8759`

- The continuation inspects cabinets `9` through `1`, then reaches
  `countertop_3` and acquires `pot_2` at 20 actions.
- B returns `OPEN` for the same search-order comparison.  C proposes an
  open-surface-first local policy and grounds `go to stoveburner_1` against
  the public entry action list.
- A returns `NO_CHANGE`; one incumbent realization does not prove an
  alternative superior.
- Reconciliation returns `REFINE_EXISTING`, correctly reusing the comparison
  identity.  However, its `supporting_evidence_refs` points to task 2's
  evidence while the current task's evidence is placed in
  `inconclusive_evidence_refs`.  The rationale discusses task 3 facts.  This
  is a semantic provenance-binding error even though the mechanical schema
  accepted the response.

Overall: comparison identity consolidation works, but evidence-role binding
needs a stricter prompt/review contract.

### Task 4 — Egg → GarbageCan (heat)

Artifact: `tasks/04-6ce98e7a5d4c`

- Retrieval activates `h-51149cfcc7556cfd` from task 3.
- The H probe visits `stoveburner_1` and `countertop_1`; neither exposes the
  requested egg.  Both raw public observations are preserved in
  `probe/probe_summary.json` and `probe/steps/*`.
- The H is consumed after the two-probe budget.  Continuation then checks
  closed storage and reaches `countertop_2`, where the egg is acquired at
  overall action count 23.
- A returns `UPDATE/REFINE`, but keeps unresolved the question of whether
  open-surface priority is consistently superior and how to order open
  surfaces.  This is evidence-bound: the trace shows negative observations
  for the two probed candidates and later acquisition at another surface; it
  does not prove a global winner.
- B/C produce a new egg-oriented open-surface H and reconciliation refines the
  shared comparison.  The H lifecycle is correct: the old H is consumed and a
  new H is materialized rather than silently reactivated.

Overall: this is the strongest closed-loop probe example.  It shows negative
local probe evidence followed by fallback acquisition, while leaving the
comparison open.

### Task 5 — Lettuce → DiningTable (cool)

Artifact: `tasks/05-2c4282a03bda`

- Retrieval abstains even though `h-8e33dc5d7e64e573` is active and the public
  state contains mixed open and closed receptacles.  Abstention is allowed,
  but this is a possible relevance false negative for later review.
- Continuation checks cabinets `4` through `1`, then open locations, and
  acquires the lettuce at `diningtable_3` after 12 actions.
- B opens the same search comparison and C creates a grounded open-surface
  candidate.  A returns `NO_CHANGE`, correctly refusing to turn one incumbent
  trace into universal policy evidence.
- Reconciliation fails closed.  The raw model output uses the literal
  `EVIDENCE_OBTAINED` as an evidence reference instead of the actual
  `evidence-*` ID, and the saved validation error is in
  `h_reconciliation/validation_error.json`.  The candidate is therefore not
  materialized.

Overall: semantic decisions are mostly cautious, but the reconciliation
interface is not robust enough for the model to bind evidence IDs reliably.

### Task 6 — Egg → SideTable (heat)

Artifact: `tasks/06-5d23b34e43af`

- Retrieval activates `h-8e33dc5d7e64e573`.
- The H probe visits `stoveburner_1` and `countertop_1`; the second public
  observation exposes the egg and the controlled executor acquires it.  No
  continuation search is needed.  The H is consumed and the target is
  mechanically acquired within the probe.
- B returns `NONE` with the justification that `won=false` means no feasible
  incumbent exists.  A likewise returns `NO_CHANGE` and treats the episode as
  a failed full task.

This is the clearest endpoint-contract failure.  Under the frozen Phase 1B
protocol, acquisition is the controlled endpoint and downstream heating and
placement are intentionally not executed.  The public evidence is sufficient
to say that the incumbent/probe search reached the requested egg; it is not
sufficient to claim full task completion.  B/A should distinguish those two
facts instead of collapsing them into “no feasible realization.”

Overall: H lifecycle and mechanical evidence are healthy; B/A semantic input
needs an explicit acquisition-endpoint contract.

### Task 7 — Ladle → DiningTable (clean)

Artifact: `tasks/07-da7ce681f998`

- Retrieval abstains.  The continuation exhaustively checks cabinets `12`
  through `1`, then acquires the ladle from `countertop_2` after 24 actions.
- B returns `OPEN` and C produces a local open-surface-first policy grounded
  at `countertop_1`.  The C packet remains entry-local and does not contain
  the later `countertop_2` answer.
- A returns `UPDATE/REFINE` with an evidence basis tied to the actual trace.
  It preserves uncertainty about drawers rather than claiming a global
  optimum.
- Reconciliation fails closed because the model again uses
  `EVIDENCE_OBTAINED` instead of a real evidence ID.  The raw response and
  validation error are retained.

Overall: B/C and A are directionally evidence-bound; the same repeated
reconciliation formatting failure is a system-level interface problem.

### Task 8 — Bread → CounterTop (cool)

Artifact: `tasks/08-44c3f607e337`

- Retrieval abstains.  Continuation checks 13 cabinets before acquiring the
  bread from `countertop_2` at 29 actions.
- B returns `OPEN`, and C independently formulates another grounded
  open-surface-first policy without source entity leakage.  A returns
  `NO_CHANGE`, noting that an inefficient incumbent trace alone does not
  establish a universally valid alternative.
- Reconciliation returns `ADD` while naming the already existing comparison
  `comparison-d10eb76341533b5b`.  The frozen validator rejects this with
  `ADD must target a new comparison`, leaving the candidate unmaterialized.

Overall: fail-closed behavior prevents a duplicate comparison, but the model
does not consistently follow the operation/target contract.  This is not a
reason to silently coerce `ADD` into `REFINE_EXISTING`.

### Task 9 — Book → Sofa

Artifact: `tasks/09-b878c93dba49`

- The target is acquired from `armchair_1` after two actions.
- Retrieval abstains, B returns `NONE`, and A returns `NO_CHANGE`.  There is
  no meaningful inefficient comparison in this short trace.
- B again mentions the deliberate lack of downstream placement because
  `won=false`, but its decision itself is conservative and appropriate.

Overall: a useful negative/control case for abstention, with the same
endpoint wording issue.

### Task 10 — Mug → Cabinet (heat)

Artifact: `tasks/10-c54897aeed0d`

- Retrieval abstains because the H created in the same task is not available
  before the task.  Continuation checks 13 cabinets and later finds the mug
  on `shelf_1` after 37 actions.
- B opens the shared search-order comparison.  C proposes a shelf-aware
  open-surface policy grounded at `countertop_1`.
- A returns `UPDATE/REFINE` with a narrower public scope for rooms containing
  shelves and explicitly keeps unresolved ordering questions.  This is a
  reasonable scope specialization, but it is appended as a new established
  memory rather than reconciled with the existing open-surface entries.
- Reconciliation correctly returns `REFINE_EXISTING` and keeps the comparison
  open.

Overall: good example of a scoped refinement, but established-memory growth
is becoming redundant.

### Task 11 — DishSponge → Toilet (clean)

Artifact: `tasks/11-c97d1a722822`

- Retrieval activates `h-11eeff3edd2e80e4`.  The public state has mixed open
  and closed receptacles, so the family-level scope match is defensible.
- The probe visits `countertop_1` and `sinkbasin_1` without finding the
  dishsponge.  The H is consumed.  Continuation then visits
  `bathtubbasin_1` and acquires the target.
- B returns `NONE` because it again interprets the acquisition endpoint as a
  failed full task.  A nevertheless returns `UPDATE/REFINE`, adding bathroom
  open-surface evidence and retaining the unresolved question of ordering
  among bathtub/counter/sink surfaces.

The B/A disagreement is evidence that the current public package does not
make the endpoint semantics sufficiently legible.  It is not evidence that
the probe failed: the probe produced negative observations, terminated at its
budget, and the fallback acquired the target.

### Task 12 — Apple → GarbageCan (heat)

Artifact: `tasks/12-32c555941b2f`

- Retrieval abstains even though an active open-surface H exists.  The
  continuation checks 19 cabinets and acquires `apple_2` at `countertop_3`
  after 37 actions.
- B returns `OPEN`, and C produces another open-surface-first candidate.
- A returns `UPDATE/REFINE` but leaves `still_unresolved` empty.  No targeted
  alternative was executed in this task, so this is too strong: the trace
  supports an inefficient incumbent and a reason to test an alternative, not
  a resolved preference.  The guidance is also another near-duplicate of the
  same open-surface memory.
- Reconciliation keeps the comparison `OPEN`, which is more conservative than
  A, and creates a fifth H instance.  Its evidence reference is the current
  task's evidence in this case.

Overall: the clearest A over-generalization in the stream, even though the
final comparison status remains correctly unresolved.

## 2. Cross-task synthesis

### Execution health

The mechanical loop is operational for the controlled endpoint:

- all 12 pinned episodes initialized and reached exact target acquisition;
- all public continuation traces and H probe traces were retained;
- H activation was limited to one active H and each activated H was consumed;
- A and B/C inputs were produced from the same `memory_before` snapshot;
- no evaluator-only fields were observed in the public role packets during
  this review.

The three reconciliation validation failures are preserved rather than
repaired.  They are not carrier failures, but they prevent a clean semantic
claim that every C candidate was reconciled.

### Retrieval health

Retrieval activated three Hs and abstained nine times.  The three activations
were mechanically legitimate enough to execute: task 4 and task 6 concern
open-surface search, and task 11 presents a mixed open/closed bathroom search
state.  The abstentions on tasks 5, 8, and 12 are plausible under an
abstention-allowed policy, but they also show that the retriever did not
consistently carry the same unresolved comparison forward when the public
state looked similar.  Applicability and comparative relevance are not yet
clearly separated in the model-visible retrieval packet.

### B/C health

B repeatedly reopens the same broad open-surface versus closed-storage
comparison.  This is not automatically wrong: the comparison remains open
because no direct C3-style comparative experiment was executed.  However,
the B rationale often treats the full task as failed solely because the loop
stopped at acquisition.  The same endpoint misinterpretation produces
inconsistent decisions: task 2 and task 3 open a comparison on acquisition
traces, while task 6 and task 11 return `NONE` on equally valid acquisition
traces.

C generally satisfies the local fact-only boundary and produces grounded
entry actions.  Its outputs are highly repetitive: most candidates are
variants of “open surfaces first,” with task-specific wording rather than a
clearly distinct unresolved comparison.  This is not a duplicate-H explosion
because reconciliation keeps one comparison identity, but it is a warning
that C is repeatedly restating one family instead of accumulating a precise
comparison/evidence state.

### Evidence and A health

A shows useful conservatism in tasks 1, 2, 3, 5, 8, and 9.  It also records
negative probe evidence in the task 4 and task 11 evidence packages.  The
main weakness is uneven evidence calibration:

- task 6 treats acquisition as no valid evidence because of `won=false`;
- task 12 removes all unresolved questions after only incumbent evidence and
  no alternative probe;
- several updates add new established memories that are near-duplicates of
  prior open-surface guidance rather than refining a single established
  entry.

The evidence store retains raw public traces, so these are reconciliation and
semantic-update problems, not irreversible data loss.

### Reconciliation and lineage health

The single comparison identity is a positive result.  H lifecycle is also
correct: activated Hs become consumed, and later candidates receive new H
IDs.  The current run nevertheless has three important weaknesses:

1. the model sometimes emits a status label instead of an evidence ID;
2. the model sometimes emits `ADD` with an existing comparison ID;
3. accepted reconciliations can cite an older evidence item as supporting
   while placing the current evidence in the inconclusive list.

The validator fails closed for the first two, which is correct.  The third is
semantically wrong but schema-valid, so a prompt/contract correction is
needed before claiming a healthy closed loop.

## 3. Root-cause candidates before tuning

The following patterns recur across multiple tasks or directly violate the
frozen contract:

1. **Acquisition endpoint is not explicit enough to B/A.**  Tasks 6 and 11
   show valid acquisition/probe evidence being described as no feasible
   realization, while tasks 2 and 3 diagnose the same controlled endpoint as
   an incumbent.  This is a shared evidence-packaging/prompt issue.
2. **Reconciliation output contract is too weakly operationalized.**  Tasks 5
   and 7 use `EVIDENCE_OBTAINED` rather than an actual ID; task 8 violates the
   `ADD` target rule; tasks 3 and 4 mis-bind supporting/current evidence.
   These are repeated across independent model calls.
3. **A appends repetitive established entries and can close uncertainty too
   aggressively.**  Five updates accumulate, while task 12 removes all
   unresolved questions without an executed alternative.  This is a memory
   evolution issue, not a carrier issue.
4. **Retrieval abstention/relevance is variable.**  Similar public mixed
   receptacle states receive different retrieval decisions.  This is a
   candidate for review, but the evidence is not yet sufficient to add a
   retrieval heuristic or automatic applicability classifier.

The first three are strong enough to motivate one minimal batch tuning
proposal.  No task-specific rule, candidate ranking rule, or hidden-state
logic is justified.

## 4. Evidence that the method contract is not yet healthy

The requirement for a healthy longitudinal closure is at least one clear
chain of:

`B/C creates H_x → future task retrieves H_x → probe obtains evidence → A/
reconciliation changes the comparison or established state`.

Round-0 has a partial version: task 3 creates `h-51149cfcc7556cfd`, task 4
retrieves it, the probe records two negative public observations, and task 4
reconciliation creates `h-8e33dc5d7e64e573` while A refines established
guidance.  Task 6 later retrieves the refined H and acquires the target during
the probe.  This is meaningful closed-loop evidence, but B/A endpoint
confusion and the reconciliation binding failures prevent a clean freeze.

## 5. Round-0 conclusion

Round-0 is **not ready to freeze** and is not a reason to run a fresh scale
experiment yet.  The implementation preserves enough evidence to perform
one batch tuning.  The next document must define that batch before any code or
prompt change.  The original 12-task stream remains development-only and
must be reset before Round-1; no result from this stream can be reused as
independent admission or confirmatory evidence.
