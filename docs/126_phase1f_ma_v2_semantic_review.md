# Phase 1F-MA-v2 — Semantic Review and Research Decision

Date: 2026-09-22
Evidence: frozen 12-task Phase 1F-MA-v2 registry and complete six-stream
runtime at
`artifacts/exploratory_memory_mvp/phase1f-ma-v2-20260922-4f78093/`
Scope: development attribution only; no post-run changes or additional calls

## 1. Main finding

The T1 no-H route produced a small favorable total-action difference relative
to T0 for both backbones:

* Flash: `T1−T0 = −11` actions (`103` versus `114`);
* Max: `T1−T0 = −4` actions (`120` versus `124`).

This is a local signal that generic exploration can be useful when the T
retrieval route validly finds no H. It is not a clean, large, Max-specific
transfer correction: the Max reduction is small in aggregate, six Max tasks
were higher in T1 than T0, and the corresponding Flash reduction was larger.
T1 no-H generic probing directly acquired 4/9 Flash targets and 3/6 Max
targets.

The adaptation did not remove the cross-model comparison gap:

| Backbone | T0−G | T1−G |
|---|---:|---:|
| Flash | −10 | −21 |
| Max | +37 | +33 |

Thus T1 remained 33 acquisition actions above Max-G, while Flash-T1 remained
21 below Flash-G. These totals are descriptive; Max's +33 is heavily
influenced by the cool-Pan task (+27 T1−G), rather than being a uniform
per-task penalty.

## 2. What the no-H intervention did—and did not—show

The policy difference was implemented as frozen: valid T1 no-H episodes used
T1's own Established Memory with Generic C2, while valid H activation kept
the targeted path. The generic fallback did not itself create or consume H,
write an archive record, or bind evidence to a comparison. Actual observations
continued into the unchanged offline pipeline. No T1 retrieval-error fallback
was observed; Max-T0 had one failed H-retrieval call and retained the
fail-closed route.

Direct probe acquisitions show an immediately useful opportunity in a subset
of no-H episodes. They do not by themselves establish the full longitudinal
effect. T1 and T0 no-H membership differed by model and task because their
independent memory states evolved differently. Moreover, the fallback can
change later evidence, B/C outputs, H creation, and future retrieval. The
contrast `T1−T0` therefore measures the resulting 12-task longitudinal policy
streams, not an isolated per-episode direct effect.

The paired task pattern was mixed. Flash T1 beat T0 on three tasks, tied six,
and used more actions on three. Max T1 beat T0 on four, tied two, and used
more on six. The Max improvement is concentrated in a few tasks (including
SoapBottle and the cooling Mug no-H cases), while regressions and ties offset
it. No significance test or post hoc success threshold is applied.

## 3. The major unresolved difference is memory evolution

The short run already shows that the two backbones' offline memory evolution
did not converge under the same contracts:

* B returned OPEN on all 12 T0 and T1 tasks for both models.
* Flash A accepted some actual H-probe evidence as
  `PARTIALLY_RESOLVED` (T0: 5 accepted; another 2 such raw assessments were
  rejected under the no-consumed-H rule; T1: 3 accepted); Max A left every comparison
  `REMAINS_OPEN` (12/12 in both arms).
* At N=12, Max-T0 had 7 H but only 1 comparison, with six
  `REFINE_EXISTING` reconciliations and four superseded H entries. Max-T1
  had 10 H and 9 OPEN comparisons, primarily through 9 ADD operations.
* Flash ended with 8 H / 5 comparisons in T0 and 7 H / 7 comparisons in T1.

The earliest visible divergence is already in task 1's post-episode
offline path: T1 took the new generic no-H probe while T0 continued from the
same warm-start state without it, so A/B/C received different actual public
evidence. For Max, the task-1 T1 C response was malformed JSON while T0
materialized an H; at task 2 the streams consequently differed in H
availability and route. This is the intended longitudinal consequence of the
intervention, not evidence of a runner integrity defect. Subsequent
reconciliation then followed sharply different identities: Max-T0 repeatedly
refined one comparison; Max-T1 mostly added comparisons. The 12-task result
cannot determine how much is attributable to C/reconciliation semantic
choices versus changed evidence and future routing.

Flash also changed between T0 and T1: the final counts moved from 5 to 7
comparisons, and the number of partial assessments fell from 7 to 3. The
offline-state divergence is therefore not exclusive to Max, although its
comparison status and consolidation pattern is more pronounced.

No comparison was RESOLVED. The report does not label the differing A
assessments as correctness failures: the small local evidence may reasonably
support conservative OPEN status, and the experiment provides no oracle for
the semantic judgment.

## 4. Fail-closed and model-output observations

All 72 scientific episodes completed and acquired their exact target. The
following stage-level outcomes remain part of the result, not reasons to
rerun:

* Flash-T0: two A epistemic assessments rejected because a no-consumed-H
  episode did not return `IRRELEVANT`.
* Flash-T1: one C future-facing entity leakage rejection and three
  source-entity B→C handoff rejections.
* Max-T0: one malformed C JSON response, one source-entity B→C handoff
  rejection, three fail-closed reconciliation outputs (`ADD` targeted an
  existing comparison), and one H retrieval call recorded as
  `failed_usage_unavailable`.
* Max-T1: one malformed C JSON response and one source-entity B→C handoff
  rejection.

The source-entity firewall rejections were expected safety behavior. Invalid
semantic outputs were retained and did not erase factual episodes. No call
was retried. These observations add uncertainty to short-horizon memory
comparison, but there was no pairing, registry, hidden-state, or state-sharing
failure.

## 5. Primary interpretation

**Primary category: `MEMORY_EVOLUTION_REGIME_REMAINS`.**

The no-H composition change modestly reduced T1−T0 action totals for both
models and produced several direct generic-probe acquisitions. It did not
explain the large residual Max T1−G difference, and it coincided with
substantial differences in A comparison assessment and H/comparison
materialization. In particular, Max-T1's 9 OPEN comparisons versus Max-T0's
single OPEN comparison is too important to describe the result only as an
immediate generic-probe opportunity effect.

This is a localization of remaining uncertainty, not a diagnosis that the
method is invalid or that either model is intrinsically incapable. The run is
small, development-only, and its arms are dependent longitudinal trajectories.

Secondary observation: **some general no-H composition value is plausible**,
because both backbones had lower total actions in T1 than T0 and generic C2
directly acquired a nontrivial subset of no-H targets. However, the Max
reduction was only four total actions, its task signs were mixed, and Flash's
reduction was larger. This does not support a Max-specific transfer-mismatch
conclusion. The broader `COMPOSITION_MISMATCH_GENERAL` and
`TRANSFER_MISMATCH_SUPPORTED` claims are therefore not established.

## 6. Research decision and stop boundary

Recommend **researcher review before any Method-v1 composition freeze or
formal evaluation**. This is the final default small attribution experiment;
do not automatically create Phase 1G, enlarge N, alter A/B/C, change H
reconciliation, or rerun any task.

The result supports a narrower conclusion: T1's valid no-H generic
opportunity has direct local value in several cases, but the change does not
remove the Flash/Max behavioral contrast or the model/trajectory-dependent
memory-state pattern in this block. A researcher should decide whether the
scientific framing should explicitly incorporate capability- and
trajectory-dependent memory evolution before freezing Method v1.

Formal evaluation remains separately blocked. The current pinned residual
population was insufficient for the prior fresh balanced block and is not a
formal reserve. Before paper-level evaluation, Formal Population Admission
must establish and freeze a new untouched confirmatory population/split.

No further model/API call is authorized automatically. This review makes no
claim that exploratory memory generally improves search, that T1 is the
preferred method, or that the full system is superior.
