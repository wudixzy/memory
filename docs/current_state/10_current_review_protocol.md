# 10. Current Review Protocol — Phase 1F Attribution Review

> Status: Phase 1C, Phase 1D, and segmented Phase 1E are complete. Phase 1F
> attribution/provenance analysis is complete and a bounded matched-adaptation
> plan is prepared. Phase 1E remains development evidence classified
> `MECHANISM_REPLICATED_BEHAVIOR_NEGATIVE`, not a confirmatory or paper-level
> result. No model/API calls are currently authorized.
> Frozen method baseline: `c8daa67ba9d9d6257d65e446b437d362e60abc61`
> Authoritative result docs: `docs/104_phase1c_flash_scale_pilot_results.md`,
> `docs/105_phase1c_flash_scale_pilot_semantic_review.md`
> Current audit/plan: `docs/107_phase1c_h2_exploration_history_audit.md`,
> `docs/108_phase1d_flash_long_horizon_validation_plan.md`; Phase 1E review:
> `docs/116_phase1e_max_prefix_diagnostic.md`, `docs/117–119`, and current
> Phase 1F docs `docs/120–121`.

## 1. Active authorization boundary

The Phase 1E resume is complete. The original 1–61 prefix and resumed 62–64
segment were mechanically reconstructed and validated as one registered
1–64 stream, while retaining segmented provenance. Do not rerun or replace any
task. Phase 1F audit/plan is complete. No further model/API calls, method
changes, matched-adaptation runs, or formal evaluation are currently
authorized; await researcher review of docs/120–121. The matched-adaptation
plan is a proposal only, not execution authorization.

Phase 1C was one 32-task Flash development stream comparing persistent generic
exploration (G) with history-conditioned exploration (T). It produced
mechanism and descriptive behavioral evidence, not a paper-level superiority
claim.

The completed Phase 1D cycle was the researcher-authorized continuation from
the exact Phase 1C M32 endpoint. It ran one 32-task G/T Flash suffix (64
episodes) after immutable transition commit `ac0bb2b`. No Max call, retry,
task replacement, or additional stream was run. The result is development
evidence only; see docs/110 and docs/111.

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

## 4. Phase 1D continuation

`docs/108_phase1d_flash_long_horizon_validation_plan.md` and
`docs/109_phase1d_flash_long_horizon_transition.md` froze continuation from
the immutable G/T state at task 32, with a public-only suffix of 32 tasks
(8 per admitted family), checkpoints at N=40/48/56/64. It kept
qwen3.8-flash, the Phase 1C behavior and the same G/T mechanical controls.
The completed result and semantic review are in docs/110 and docs/111.

The eventual review must distinguish scale-positive, saturation, scale
degradation, mechanism overproduction, and mechanism-positive/behavior-
negative outcomes without converting development evidence into a formal
superiority claim.

## 5. Claims and next-stage boundary

The project has not established general memory superiority, native cold-start
performance, full autonomous-agent benefit, or cross-benchmark generality.
Phase 1E completed as a segmented Max stream and was classified
`MECHANISM_REPLICATED_BEHAVIOR_NEGATIVE`: the mechanism formed, but cumulative
Max T used 47 more acquisition actions than G, concentrated in no-H tasks;
Max's H-active subset was near-neutral. Flash showed the opposite aggregate
direction. Phase 1F's leading attribution is `MIXED`: stronger observed
Max-G generic probing, intentional T no-H asymmetry, and model-dependent
memory evolution all remain plausible contributors. This is one reused
development population per model, not a causal or formal estimate. See
docs/118–121. No model/API calls or formal experiments are currently
authorized.

## 6. Phase 1F current status

The deterministic aligned-artifact analysis is implemented at
`experiments/exploratory_memory_mvp/analyze_cross_model_attribution.py`.
Findings and protocol-development provenance are in
`docs/120_phase1f_cross_model_attribution_and_tuning_provenance.md`.
The only proposed next validation is a one-dimension, symmetric
T-no-H-to-generic-C2 matched-adaptation design in
`docs/121_phase1f_matched_adaptation_validation_plan.md`.

Current boundary:

* Phase 1E completed; no Phase 1E result/runtime is to be rewritten.
* Phase 1F attribution/provenance audit completed with no model/API calls.
* Matched-adaptation protocol prepared, pending explicit researcher
  authorization; it has not been run or transitioned.
* Formal evaluation and Method/Evaluation v1 freeze are not authorized.
* No Flash/Max calls, method tuning, or new development stream may start under
  this handoff alone.
