# 10. Current Review Protocol — Phase 1C H2 Audit / Phase 1D Pending

> Status: Phase 1C completed; H2 audit completed; Phase 1D protocol prepared
> and pending researcher authorization (2026-09-21).
> Frozen method baseline: `c8daa67ba9d9d6257d65e446b437d362e60abc61`
> Authoritative result docs: `docs/104_phase1c_flash_scale_pilot_results.md`,
> `docs/105_phase1c_flash_scale_pilot_semantic_review.md`
> Current audit/plan: `docs/107_phase1c_h2_exploration_history_audit.md`,
> `docs/108_phase1d_flash_long_horizon_validation_plan.md`

## 1. Active authorization boundary

Phase 1C was one 32-task Flash development stream comparing persistent generic
exploration (G) with history-conditioned exploration (T). It produced
mechanism and descriptive behavioral evidence, not a paper-level superiority
claim.

The current cycle is a no-model post-hoc H2 audit plus preparation of a
possible Phase 1D continuation. **No model/API calls are currently
authorized.** Do not run Flash, Max, Phase 1D, a new task stream, or any
additional development experiment until the researcher explicitly authorizes
the prepared protocol.

Do not modify the immutable Phase 1C runtime, its task population, model
configuration, prompts, retrieval, lifecycle, comparison identity, or H2
interpretation after the fact.

## 2. H2 audit boundary

The deterministic extraction utility is:

```text
experiments/exploratory_memory_mvp/analyze_phase1c_h2_audit.py
```

It reads only:

```text
artifacts/exploratory_memory_mvp/phase1c-scale-pilot-v1-20260921-60c2474
```

The extraction uses the archive actually supplied to C, selected real history
IDs, visible C outputs, B→C projection, and mechanical reconciliation/task
artifacts. It does not inspect PDDL, hidden placement, oracle routes, target
outcomes, or call a model. The resulting local artifact is:

```text
artifacts/exploratory_memory_mvp/phase1c-scale-pilot-v1-20260921-60c2474-h2-audit-v1/extracted_cases.json
```

The audited population is 30 history-available C cases: 20 CREATE and 10
NONE. Task 1 is excluded because no prior archive was available; task 23 is
excluded because the existing B→C firewall correctly prevented C. See
`docs/107_phase1c_h2_exploration_history_audit.md` for the complete manual
labels and root-cause discussion.

## 3. Current H2 conclusion

The audit found:

* 14 `MATERIALLY_DIFFERENT` CREATE cases;
* 5 `JUSTIFIED_RETEST` CREATE cases;
* 1 confirmed `REDUNDANT_NEAR_DUPLICATE` CREATE case;
* 6 `REASONABLE_SUPPRESSION`, 2 `POSSIBLE_OVER_SUPPRESSION`, and 2
  `UNCLEAR` NONE cases.

No correctness blocker was found. The decision is
`PROCEED_TO_LONG_HORIZON_VALIDATION`, not “H2 passed”. Occasional semantic
near-duplication and backlog growth remain development risks to measure in a
future frozen continuation; they must not be patched silently from this
stream.

## 4. Prepared Phase 1D (not authorized)

`docs/108_phase1d_flash_long_horizon_validation_plan.md` proposes continuing
from the immutable G/T state at task 32 and adding a fresh public-only suffix
of 32 tasks (8 per admitted family), with checkpoints at N=40/48/56/64.
It keeps qwen3.8-flash, the Phase 1C behavior, and the same G/T mechanical
controls. It is a plan only: no suffix registry, transport, paid run, or
transition commit is created by the current cycle.

The eventual review must distinguish scale-positive, saturation, scale
degradation, mechanism overproduction, and mechanism-positive/behavior-
negative outcomes without converting development evidence into a formal
superiority claim.

## 5. Claims and next-stage boundary

The project has not established general memory superiority, cross-model
robustness, native cold-start performance, full autonomous-agent benefit, or
cross-benchmark generality. If Phase 1D is later authorized and supports the
mechanism, the next stages are cross-model validation, Method/Evaluation v1
freezing, and only then fresh formal controlled evaluation.

No Max call is authorized in the current state.
