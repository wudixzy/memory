# Phase 2A Primary Semantic Review

Date: 2026-09-23
Evidence: frozen Phase 2A v2 primary replays only; no new model call was made
for this review. This is a curated diagnostic review, not a statistical or
paper-level claim.

## 1. Review boundary and alignment

The review applies the frozen rubric in
`docs/review_samples/phase2a_semantic_integration_v2/review_rubric.json`:
evidence fidelity, scope fidelity, preference overreach, useful learning,
contradiction handling, cross-model semantic agreement, and input-token cost.
`Preference overreach` means a memory update states a default, preference, or
superiority claim not supported by the available evidence.

No hidden PDDL, oracle route, evaluator answer, or model hidden reasoning was
used. Reviewed materials are the frozen model-visible trajectory, Candidate
+ Support, bounded pre-task Text Memory/prior Support, raw and parsed Stage 1/A
responses, validation, and proposed-mutation artifacts.

Two different pairings must not be conflated:

* Historical package alignment (`flash_t` versus `max_t`) is frozen as 8
  `EXACT_PUBLIC_TRAJECTORY`, 13 `SAME_TASK_DIFFERENT_TRAJECTORY`, and 4
  `UNPAIRED`. Those labels describe the historical source evidence.
* The primary new cross-model comparison aligns Flash and Max by the same
  frozen `source_episode_ref`. It contains 15 paired inputs. For each ref,
  Stage 1 input, task context, pre-task Established Memory, and prior Support
  view are identical. Stage 1 Candidate/Support and therefore the complete A
  input are model outputs and can differ; that is the object being reviewed,
  not a pairing failure.

Prior Support in this preparation was reconstructed from accepted historical
A/materialization/public-evidence artifacts; it is not native Stage 1
Support. Across the 15 appearances in either backbone's A inputs, there are
74 Existing Memory entries: 22 have selected prior Support and 52 explicitly
report it unavailable; 47 selected Support records are present. The inputs
are byte-equivalent across backbones for each matching source ref. The
primary set is small and curated; these counts are context, not an estimate
of Support efficacy. Native Support formation remains outside Phase 2A and
belongs to a later Phase 2B question.

## 2. Layer A — Stage 1 Candidate + Support

All 15 Stage 1 outputs per model passed dynamic event-reference and schema
validation. Grounding is traceable to actual visible trajectory events. On
the inspected clear examples, Stage 1 generally preserved the observed
search path, receptacle contents, target exposure/acquisition, and the
search-only endpoint. It did not have Existing Memory in its input.

Mechanical event membership is necessary but not sufficient for semantic
faithfulness. Several Candidates turn a single realization into strategy
language (`prioritize`, `yields rapid`, `can lead to faster`) before a direct
alternative comparison exists. That language is the Candidate under review,
not evidence that the preference is true. Other outputs are careful to state
that the trajectory demonstrates feasibility only. The distinction is
visible in both models; it is not resolved by a valid event reference.

Examples:

* Pan, `case_03/.../flash_t`: both new backbones saw the same three public
  events—stoveburner 1 contained a pot, stoveburner 2 exposed pan 1, then the
  exact take succeeded. Both Candidates captured the sequence. The observation
  supports feasibility of that route. It does not alone measure the
  counterfactual cost of listed-order search.
* Egg, `case_02/.../max_t`: the visible trace records the fridge-first search
  and eventual acquisition from a garbage can after a long traversal. Stage 1
  retained the failed early search and later atypical-location discovery;
  candidate wording differed in how strongly it generalized the lesson.
* Cloth, `case_05/.../flash_t`: the visible trace found the requested cloth in
  cabinet 4 after dedicated towel holders did not contain it. Stage 1
  preserved the negative holder observations and the eventual cabinet
  acquisition. It does not establish that either holder-first or
  listed-order is generally better.
* SoapBar, `case_09/.../max_t1`: Stage 1 reported an empty/non-target cabinet
  inspection followed by soapbar acquisition on a countertop. This is a
  useful negative-then-positive sequence, but not evidence that either
  receptacle class is globally preferred.

Assessment: Stage 1 is mechanically grounded and mostly trajectory-faithful
on the reviewed cases, but scope/preference language still needs downstream
review. No Stage 1 schema/interface blocker was observed. This supports the
search/acquisition-local integration claim only; it says nothing about full
task completion or native Support formation.

## 3. Layer B — restored A / Stage 2

Every intended A response is available and accepted after treating the
separately authorized Pan/Max A recovery as a separate response. Counts are:

| Model | A decisions | Update operations | `unresolved_boundary` entries |
|---|---|---|---:|
| Flash | 14 `UPDATE`, 1 `NO_CHANGE` | 7 `REFINE`, 5 `SUPPORT_ONLY`, 3 `SPECIALIZE` | 17 |
| Max | 10 `UPDATE`, 5 `NO_CHANGE` | 10 `REFINE`, 6 `SUPPORT_ONLY` | 0 |

Operation counts count updates, not decisions; a `NO_CHANGE` response may
still contain one or more `SUPPORT_ONLY` updates. Max's zero formal boundary
entries do not mean every Max guidance is unqualified: some caveats appear in
the guidance or `support_note`. Conversely, those prose caveats do not erase
the observed cross-model difference in how explicitly uncertainty is
represented.

Useful learning did not collapse into universal `NO_CHANGE`: both models
proposed grounded updates in most episodes, including support accumulation
and refinements. There are examples of sensible boundary handling, especially
the Flash Tomato/Egg/SoapBar cases. There are also potential
feasibility-to-preference promotions in proposed mutations from both models:

* In Tomato `flash_t`, a fridge-first failure followed by later acquisition
  led to a task-scoped preference/fallback Candidate. Flash A added explicit
  boundaries about wasted steps and narrow food scope; Max A's corresponding
  update promoted semantic-priority guidance without a formal unresolved
  boundary. In Tomato `max_t`, the actual historical realization was
  different: Flash retained two boundaries around semantic search, while Max
  favored listed-order traversal. These are not equivalent source
  trajectories, but each same-ref Flash/Max pair had identical input.
* In Egg `flash_t`, the target was found only after the high-prior locations
  were exhausted. Flash A generalized semantic priority with an explicit
  boundary; Max A emphasized listed order and fallback. In Egg `max_t`, Flash
  retained two caveats while Max again returned no formal boundary. The
  contrasting A outputs cannot be ranked against hidden “correct” location
  knowledge; the review uses only their visible evidence.
* In Pan `flash_t`, both Stage 1 outputs describe the target on the second
  stoveburner. Flash A adds support to a cookware memory; Max A refines the
  general listed-order memory and does not preserve the same local guidance.
  This is a semantic integration difference despite the same observed input.
* In Pan `max_t`, the original Max A response artifact was corrupt and is not
  reviewable. Its isolated recovered response refines the general listed-order
  memory with a cookware/stoveburner exception. Its `support_note` explicitly
  says the single trajectory establishes feasibility, not unconditional
  superiority. This recovery is not represented as the original response.
* In Lettuce `flash_t`, Flash proposes support accumulation on existing
  open-surface guidance while Max returns `NO_CHANGE` with a support-only
  proposal.
  These outputs are directionally close. For `max_t`, both update the
  listed-order memory despite differently phrased Candidates; neither adds a
  formal uncertainty boundary.
* In Cloth `flash_t`, the trajectory includes negative towelholder checks
  before finding the target in a cabinet. Flash's updated guidance still
  gives dedicated holders priority and includes a boundary; this is a
  potential preference-overreach case, not an established error. On
  `max_t`, Flash refines guidance while Max keeps listed-order guidance with
  support-only updates. The historical source trajectories differ, but the
  new models are paired on each exact source ref.
* In SoapBar, the restored Flash A explicitly distinguishes the attempted
  cabinet-first route from an untested speed comparison. Max A's recovered
  semantic output emphasizes adapting after a negative inspection and does
  not claim cabinet-first superiority. Both are more cautious than their
  historical Phase 1F A outputs, though their resulting guidance differs.
* In the topology chain, both models support generic listed-order memory on
  task 1. On task 2 / T0, Flash specializes toward open surfaces and records
  two boundaries; Max refines open-surface-first guidance with no formal
  boundary. The single successful surface realization does not directly
  compare it against closed-storage-first. On task 2 / T1, both return
  support-only/no-change for the generic listed-order memory; Max also attaches
  support to the clean routine even though the frozen endpoint is acquisition
  only, so that support must not be read as evidence that the cleaning/placement
  steps occurred.

The pattern is not simply “Flash learns, Max does not”: both propose retaining
useful information, but choose different update strength and boundary
expression.
Nor is Flash a ground truth: the Cloth and open-surface cases show that Flash
can also turn a one-trajectory realization into a preference-like rule.

### Per-appearance paired diagnostic

The following rows align the *new* model outputs by identical
`source_episode_ref`. Candidate descriptions are compact reviewer summaries
of visible Stage 1 content; A entries report proposed operations and explicit
boundary counts, not correctness labels.

| Source ref | Stage 1 evidence/Candidate focus | Flash A proposal | Max A proposal | Observable difference to review |
|---|---|---|---|---|
| `case_01/flash_t` | Tomato; fridge-first miss, later countertop acquisition; both candidates discuss semantic search/fallback | `UPDATE/SPECIALIZE`, 2 boundaries | `UPDATE/REFINE`, 0 | Max gives semantic-priority guidance without the explicit scope/waste boundary Flash records |
| `case_01/max_t` | Tomato; longer listed traversal to surface; Flash Candidate frames semantic locations, Max Candidate frames ordered traversal | `UPDATE/SPECIALIZE`, 2 | `UPDATE/REFINE`, 0 | Different proposed search abstraction from the same replay; not a historical Flash/Max trajectory match claim |
| `case_02/flash_t` | Egg; high-prior containers fail, atypical garbage-can acquisition | `UPDATE/REFINE`, 1 | `UPDATE/REFINE`, 0 | Flash retains a fallback/scope caveat; Max leans on listed traversal |
| `case_02/max_t` | Egg; fridge-first miss, then broad search and acquisition | `UPDATE/REFINE`, 2 | `UPDATE/REFINE`, 0 | Flash proposes task-aware priority with caveats; Max prefers listed order |
| `case_03/flash_t` | Pan; burner 1 has pot, burner 2 exposes pan, exact take succeeds | `UPDATE/SUPPORT_ONLY`, 0 | `UPDATE/REFINE`, 1 | Flash adds support to cookware guidance; Max revises the general listed-order entry |
| `case_03/max_t` | Pan; ordered traversal evidence; model Candidates differ in emphasis on the surface/burner realization | `UPDATE/REFINE`, 1 | `UPDATE/REFINE`, 0 (isolated recovered A) | Both target the general search entry; recovered Max text contains a cookware exception and explicitly limits the claim to feasibility |
| `case_04/flash_t` | Lettuce acquired on open surface | `UPDATE/SUPPORT_ONLY`, 1 | `NO_CHANGE/SUPPORT_ONLY`, 0 | Close direction; Flash records an explicit boundary, Max accumulates support without changing guidance |
| `case_04/max_t` | Lettuce; open-surface Candidate, but A retains listed-order guidance | `UPDATE/REFINE`, 2 | `UPDATE/REFINE`, 0 | Similar conservative base strategy, different explicit boundary treatment |
| `case_05/flash_t` | Cloth not in dedicated holders; found in closed cabinet | `UPDATE/REFINE`, 1 | `UPDATE/REFINE`, 0 | Both update search guidance; Flash still prioritizes semantic holders despite the negative observations |
| `case_05/max_t` | Cloth; specialized holder inspection followed by cabinet acquisition | `UPDATE/REFINE`, 1 | `NO_CHANGE/SUPPORT_ONLY`, 0 | Flash revises guidance; Max retains listed-order guidance and adds support only |
| `case_09/max_t1` | SoapBar; cabinet miss followed by countertop acquisition | `UPDATE/REFINE`, 2 | `UPDATE/REFINE`, 0 | Both reject unconditional cabinet-first superiority in prose, but encode caution differently |
| `case_10/max_t0_task1` | Saltshaker acquired after ordered cabinet inspection | `UPDATE/SUPPORT_ONLY`, 0 | `NO_CHANGE/SUPPORT_ONLY`, 0 | Same general listed-order evidence; decision label differs while operation is support-only |
| `case_10/max_t1_task1` | Saltshaker acquired after a different cabinet traversal | `UPDATE/SUPPORT_ONLY`, 0 | `NO_CHANGE/SUPPORT_ONLY`, 0 | Same direction; different decision label on the paired source ref |
| `case_10/max_t0_task2` | Plate acquired from countertop after open-surface search | `UPDATE/SPECIALIZE`, 2 | `UPDATE/REFINE`, 0 | Both propose open-surface priority; only Flash explicitly marks the untested alternative/boundary |
| `case_10/max_t1_task2` | Plate acquired from cabinet; endpoint stops at acquisition | `NO_CHANGE/SUPPORT_ONLY`, 0 | `NO_CHANGE/2×SUPPORT_ONLY`, 0 | Both keep search guidance; Max also proposes support for the clean routine although cleaning is not in the observed endpoint |

The abbreviated `case_NN/...` names expand to the full case IDs in the frozen
registry. Raw and parsed outputs for every row remain at the runtime paths in
docs/133; case-specific Stage 1/A inputs and provenance are under the frozen
v2 review package. Pan/Max's Max A row points to the isolated recovery path,
not the preserved corrupt original response.

## 4. Historical A versus restored integration

The historical Phase 1F A emitted comparison status/evidence-role judgments
in addition to memory updates. Restored Phase 2A A instead receives a
Stage-1-produced Candidate + Support, bounded pre-task Text Memory, and compact
prior Support, and proposes a local memory mutation without comparison-status
output. Therefore historical `PARTIALLY_RESOLVED`, `REMAINS_OPEN`,
`IRRELEVANT`, and `INCONCLUSIVE` labels are not ground truth and are not
directly comparable output fields.

Qualitatively, restored integration often makes the evidence boundary more
visible than historical A did—for example, the restored Tomato and SoapBar
responses identify that a successful/attempted route does not prove faster
search. Some historical broad claims are narrowed. But this is not uniform:
preference-like guidance remains in several restored outputs, and new
Flash/Max responses diverge on identical source evidence. Because Phase 2A
jointly restores Stage 1, Candidate + Support, prior Support, and a different
Stage 2 contract, any before/after difference is evidence about restored
native integration as a package; it cannot be attributed to Stage 1 alone.

## 5. Matched new Flash-versus-Max review

The new cross-model comparison is stronger than the historical
`flash_t`/`max_t` comparison for input attribution: the same
`source_episode_ref` is replayed to both backbones, and its model-visible
Stage 1 input, pre-task memory, and prior Support view match. Stage 1 outputs
are not required to match word-for-word. The semantic patterns are mixed:

* Some pairs agree on the evidence direction but differ on epistemic
  expression: Pan `flash_t`, Lettuce `flash_t`, SoapBar, and parts of the
  topology chain.
* Some pairs differ on whether to propose a narrow heuristic or retain generic
  listed-order guidance: Tomato, Egg, Pan `flash_t`, Cloth, and topology task
  2.
* Flash emits 17 explicit `unresolved_boundary` items; Max emits none. Max
  sometimes places caveats in support notes/guidance, but not consistently.
  This is a notable model-dependent representation pattern, not by itself a
  correctness violation.

Same-input pairing is valid, but semantic agreement is not sufficiently
stable to say that restored integration removed the cross-model regime
difference exposed in Phase 1F. The key risk remains whether similar evidence
gets comparable mutation authority and explicit boundaries—not matching
wording or old comparison-status labels.

## 6. Input-support context and cost

For each model, 22 of 74 selected Existing Memory entries had prior Support
available; 52 explicitly reported unavailable. The same selected support
records were supplied for each same-source-ref Flash/Max pair. This does not
prove those records were sufficient or that either model used them correctly.
The corpus is reconstructed prior Support, not native Stage 1 output.

The completed primary calls used about 140k Flash input tokens and 147k Max
input tokens including the isolated A recovery. Frozen planning estimates are
about USD 0.080 per backbone; provider-reported charges are unavailable. There
was no observed context-limit failure or output truncation among accepted
responses. This is acceptable as a bounded diagnostic cost, not a scale-cost
projection.

## 7. Remaining failure modes

1. **Cross-model epistemic-boundary instability:** same frozen input does not
   consistently produce comparable scope, mutation strength, or explicit
   unresolved boundaries.
2. **Feasibility-to-preference risk:** some single realizations still support
   preference-like guidance without direct comparison. This appears in both
   backbones and is not solved by mechanical grounding.
3. **Stage 1 scope/generalization:** event-grounded facts can still be
   converted into broad Candidate language. Event membership alone does not
   validate the inference.
4. **Support availability is limited:** 52/74 per-run selected Existing
   Memory entries had no recovered prior Support. This limits the claim that
   support-aware reconciliation was exercised uniformly.
5. **Recovery provenance:** one original Max A output remains unreadable; the
   accepted isolated response is a separate, authorized additional request.
   One Max Stage 1 result-unknown request was explicitly reissued under
   docs/137. These do not invalidate the frozen input population but limit a
   claim of physically uninterrupted execution.

No mechanical grounding, schema, leakage, or pairing blocker was found in the
completed outputs. These are semantic stability/coverage limitations, not
evidence that the comparison ledger or Graph needs redesign.

## 8. Phase 2A interpretation and gate

**Gate: `CROSS_MODEL_REGIME_REMAINS`.**

The primary execution shows that the restored search-local Stage 1 →
Candidate + Support → A path can produce grounded, useful updates and can
make feasibility/comparison boundaries explicit. It does not satisfy the
cross-model semantic stability criterion: the same source evidence still
elicits materially different Candidate abstractions, update operations, and
boundary treatment; preference-like generalization remains possible in both
backbones. The accepted output count and cost do not outweigh this
interpretive blocker.

This is not a claim that Phase 2A failed mechanically, that Flash is correct,
that Max is wrong, or that exploratory memory lacks value. It is a decision
that this curated replay does not yet warrant Phase 2B native accumulation or
a Phase 2A pass claim. The analysis is small, selected, and search/acquisition
local.

No `docs/135` Phase 2B plan is created because its prerequisite Phase 2A pass
was not met. No secondary cases were run; they are not needed to establish
that the frozen primary set leaves cross-model semantic stability unresolved.
There is no automatic rerun, prompt modification, secondary execution,
Phase 2B/C/D, Method v1 freeze, or formal evaluation authorization. Researcher
review is the next action.
