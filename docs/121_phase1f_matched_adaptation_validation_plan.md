# Phase 1F — Matched-Adaptation Validation Plan

Status: prepared for researcher review; **not authorized to execute**
Models: `qwen3.8-flash`, `qwen3.8-max` only
Purpose: discriminate the leading Phase 1E attribution hypotheses, not optimize
T until it beats G

## 1. Question and rationale

Phase 1E compared a Flash-developed frozen protocol across two model
backbones. Max-G was substantially more efficient than Flash-G, while Max-T
was more costly than Max-G. The clearest protocol asymmetry is that G gets a
generic C2 opportunity on every task, but T receives a probe only when an H is
activated; with no activated H, T proceeds directly to canonical continuation.
In no-H Max episodes, G's generic probe acquired 15/42 targets and the aggregate
T−G delta was +54, though the subgroup delta, evolved Established Memory, and
post-hoc selection prevent causal attribution.

The smallest directly implicated, recognizable policy adaptation is therefore
one shared composition change:

> **T-Hybrid:** if T activates an H, keep the unchanged targeted probe. If no
> H is activated, give T the same generic C2 opportunity used by G, with the
> same maximum of two candidates, then use the same canonical continuation if
> acquisition has not occurred.

G remains unchanged. The candidate adjustment applies identically to Flash
and Max. This tests the no-H composition hypothesis; it is not a prompt tune,
and it is not by itself a claim about the best eventual method.

## 2. Fixed adaptation budget

| Budget item | Frozen proposal |
|---|---|
| Adjustable dimensions | Exactly one: T's no-activated-H branch (`canonical continuation` → `generic C2 then canonical continuation`). |
| Shared semantics that cannot change | H-active targeted probe, H lifecycle, G C2, A/B/C/H prompts and schemas, retrieval, history archive, comparison identity, candidate cap=2, executor, continuation, endpoint, fact commit. |
| Model-specific changes | None. Same policy adaptation, prompts, temperature, thinking, and model-role mapping for both models. |
| Calibration population | Exactly 4 fresh, non-protected calibration tasks, one per family, selected from a separately frozen development-only public universe. No Phase 1A–1E outcome-exposed task may be reused. Membership is not yet frozen because the inspected Phase 1D residual census is insufficient (see §2). |
| Calibration repetitions / iterations | One pass only; once four eligible IDs are registered, 4 tasks × 3 arms × 2 models = 24 episodes. No retry. No result-driven task replacement. |
| Adaptation iterations | One pre-registered batch (the single T-Hybrid definition above); zero post-calibration edits. No alternative fallback or threshold sweep. |
| Held-out evaluation population | Exactly 16 fresh development tasks, 4 per family, selected outcome-blind from an eligible development-only public pool; disjoint from calibration, all historical task IDs, protected reserves, and any formally reserved population. Membership is not yet frozen. |
| Held-out repetitions | One pass: once 16 eligible IDs are registered, 16 tasks × 3 arms × 2 models = 96 episodes. |
| Total if the population gate is met | 20 unique fresh tasks across calibration and held-out; 120 actor episodes. Calibration and held-out results are reported separately. |

### Population availability is a blocking precondition

The committed Phase 1D public eligible universe contains 56 records. After
its 32 selected tasks are removed, its residual family counts are only:

| Family | Residual unselected records |
|---|---:|
| `pick_and_place_simple` | 5 |
| `pick_clean_then_place_in_recep` | 12 |
| `pick_cool_then_place_in_recep` | 3 |
| `pick_heat_then_place_in_recep` | 4 |

That residual cannot supply the proposed five tasks per family (one
calibration plus four held-out). This is a shortage in the inspected Phase 1D
registry, **not evidence that no clean tasks exist in any public split**. The
Phase 1D selection protocol also excluded the protected B1-R reserve. Do not
borrow B1-R tasks or silently consume a future formal population.

Before this protocol can be frozen for execution, a no-model census must
identify a development-only public population with at least five eligible
tasks in each family, after excluding all Phase 1A–1E used IDs, B1-R and other
protected reserves, and any separately designated formal holdout. If such a
pool cannot be demonstrated, stop and ask the researcher to authorize a
different split or smaller design; do not relax eligibility or disjointness
rules after seeing outcomes. Exact calibration/held-out IDs, salts, registry
digests, seeds, replay specs, and fingerprints must be frozen before any
model call.

Once a clean population is established, select one calibration and four
held-out tasks per family deterministically without replacement, using
separate precommitted salts. Selection may use public family/instruction,
reset observation, ordered admissible actions, affordance structure, replay
availability, and public initial fingerprint only. No hidden placement,
PDDL, oracle, expert route, prior outcome, or expected winner may be used.

The calibration pass checks protocol compatibility and exposes the paired
behavior under the one preselected candidate. It does not select among
candidate policies. Calibration outcomes must never be merged into the
held-out estimate. If there is a mechanical incompatibility, stop before
held-out execution and report it; do not repair and rerun under the same
budget.

## 3. Arms and fresh state

Each model runs three independent longitudinal streams on the exact same
task/replay order:

| Stream | Per-task policy | Initial memory |
|---|---|---|
| G | Generic C2 opportunity on every task → canonical continuation | `K*` only; independently evolves G Established Memory |
| T0 | Frozen Phase 1E T: activate at most one H and targeted probe; if no H is activated, canonical continuation | `K*`; empty active/consumed H, comparison ledger, and archive |
| T1 | T-Hybrid: H-active path unchanged; if no H is activated, generic C2 then canonical continuation | Same fresh independent T state as T0 |

Flash and Max each start independently from canonical K*. No Flash memory,
H, archive, comparison ledger, prompts, or semantic outputs enter Max; no
cross-arm state sharing is allowed. T0 and T1 each have their own evolving
memory state. The only intended T0/T1 difference is the no-H opportunity.

Within each model, G/T0/T1 use exact same task registry, public replay spec,
seed, and public initial fingerprint. All arms retain the fixed two-candidate
budget and target-acquisition endpoint. A task with acquisition during the
probe ends that episode's search normally; otherwise the common deterministic
continuation proceeds.

## 4. Primary observations and interpretation

Primary descriptive quantity on the held-out tasks is environment actions to
exact target acquisition. Report paired:

```text
T0 − G
T1 − G
T1 − T0
```

for each model, plus paired per-task deltas and family/half summaries. The
main discriminator is whether the same T-Hybrid change selectively removes
the no-H cost while preserving the H-active path, and whether that occurs
similarly for both models. This is not a causal H-only estimate: H activation
and the longitudinal memory states remain endogenous.

Mechanism review is limited to:

* no-H generic candidate/acquisition sequences;
* H activation, H-directed sequence and actual public probe evidence;
* A evidence role/comparison assessment;
* B/C CREATE/NONE, handoff rejects, and comparison identity operations;
* active-H backlog and archive/comparison growth;
* protocol/schema failures and context sizes.

No semantic suppression or lifecycle fix may be applied during the run.

## 5. Pre-registered stop and handling rules

* Freeze code, prompts, actor configs, calibration/evaluation registries, and
  salts before calibration.
* Calibration is exactly one pass over four fresh, frozen tasks, all six
  model/arm streams; no task-level retries.
* If calibration reveals only an ordinary scientific/model failure, preserve
  it and proceed to held-out tasks under the frozen protocol.
* If calibration reveals a mechanical protocol/pairing/transport defect that
  prevents valid execution, stop; do not patch and repeat calibration.
* Once held-out execution starts, complete all 16 registered tasks for all
  six streams unless a genuine infrastructure failure prevents continuation.
  No result-driven stopping, replacement, retry, or model switch.
* The one allowed adaptation is the already-specified no-H C2 opportunity.
  No second iteration is permitted after either calibration or held-out
  results.
* Any future prompt, A/B/C, retrieval, comparison, H, or lifecycle change
  requires separate researcher authorization and a new design; do not bundle
  it with this test.

## 6. Dependency graph and parallelization

```text
freeze public calibration/evaluation registries + code/config
                         │
            one 4-task calibration block
                         │
          mechanical review only; no tuning
                         │
         16-task held-out registry execution
                         │
              paired artifact review
```

Each of the six streams (Flash-G/T0/T1 and Max-G/T0/T1) is longitudinal and
must execute its own tasks sequentially in the frozen order. Independent
streams may run in parallel if the provider/runtime permits and artifacts
remain isolated. Within a task, G/T0/T1 arms are separate state machines and
can be scheduled independently after their replay proofs are frozen. The
held-out phase is blocked on calibration completion only for protocol
integrity review; no performance-based retuning is allowed between phases.

## 7. How outcomes change the research interpretation

* **Transfer/composition mismatch supported:** T1 reduces the Max no-H
  disadvantage relative to T0, and the same direction is observed for Flash,
  while H-active behavior remains on its frozen targeted path. This supports
  a composition mismatch explanation; it does not prove general superiority.
* **Capability-dependent value remains plausible:** T1 still shows materially
  less incremental value for Max than Flash, while Max-G retains much lower
  cost. Keep this as a conditional scientific hypothesis, not “memory fails
  on strong models.”
* **Memory-evolution regime shift remains primary:** the same no-H change does
  not account for model-specific A assessments, handoff failures, CREATE/NONE
  imbalance, or comparison-state divergence. Stop; review the framing. This
  plan does not authorize a second calibration dimension.
* **Insufficient evidence:** the held-out stream is mechanically valid but
  mixed, with no clear interpretation. Return to the researcher; do not
  extend the horizon or add arms automatically.

No numeric “beat G” threshold selects a policy. T1 is not tuned to maximize
performance; the question is whether a small predeclared symmetric adaptation
changes the attribution picture.

## 8. Validation-to-formal boundary

This matched-adaptation study remains development evidence. Formal evaluation
is still unauthorized. If the result supports a stable model-aware protocol,
the next researcher-reviewed steps are to freeze Method v1 and Evaluation
Protocol v1, then design a fresh confirmatory study with multiple independent
streams and stream-level analysis. Do not reuse calibration or held-out
development cases as confirmatory evidence. No second benchmark, native cold
start, full autonomous actor, or formal run is included here.

**Execution status:** plan only. No model/API calls, registry creation,
transition commit, or experiment run is authorized by this document.
