# 10. Current Review Protocol — Phase 1F-MA-v2 Matched Adaptation

> Status: Phase 1C/1D and segmented Phase 1E are complete; Phase 1F
> attribution/provenance review is complete. The original 16-task proposal
> remains historically blocked (docs/123). The researcher separately
> authorized Phase 1F-MA-v2 with 12 development-only tasks, three per family.
> No model/API call occurred before the immutable transition. After its commit
> is pushed, only the six frozen streams (72 episodes) are authorized. Formal
> evaluation remains unauthorized, and this residual is not a formal reserve.
> Frozen method baseline: `c8daa67ba9d9d6257d65e446b437d362e60abc61`
> Authoritative result docs: `docs/104_phase1c_flash_scale_pilot_results.md`,
> `docs/105_phase1c_flash_scale_pilot_semantic_review.md`
> Current audit/plan: `docs/120_phase1f_cross_model_attribution_and_tuning_provenance.md`,
> `docs/121_phase1f_matched_adaptation_validation_plan.md`,
> `docs/122_phase1f_matched_adaptation_execution_plan.md`, historical blocker
> `docs/123_phase1f_population_gate_blocker.md`, and active transition
> `docs/124_phase1f_ma_v2_transition.md`.

## 1. Active authorization boundary

The Phase 1E resume is complete. The original 1–61 prefix and resumed 62–64
segment were mechanically reconstructed and validated as one registered
1–64 stream, while retaining segmented provenance. Do not rerun or replace any
task. Phase 1F-MA-v2 is the active bounded development cycle. Before the
immutable transition commit is pushed, no model/API calls are authorized.
After it is pushed, the only authorized calls are the 12 frozen tasks across
G/T0/T1 and Flash/Max (72 episodes). No retries, replacements, tuning,
additional stream, Method/Evaluation v1 freeze, or formal evaluation are
authorized by this transition.

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
docs/118–121. These historical Phase 1E/attribution results authorize no
reruns. The separate current Phase 1F-MA-v2 scope is defined only by docs/124;
formal experiments remain unauthorized.

## 6. Phase 1F status and active v2 boundary

The deterministic aligned-artifact analysis is implemented at
`experiments/exploratory_memory_mvp/analyze_cross_model_attribution.py`.
Findings and protocol-development provenance are in
`docs/120_phase1f_cross_model_attribution_and_tuning_provenance.md`. The
active one-dimension, symmetric T-no-H-to-generic-C2 validation is the new
12-task Phase 1F-MA-v2 transition in
`docs/124_phase1f_ma_v2_transition.md`; docs/121 remains its earlier proposal.

Current boundary:

* Phase 1E completed; no Phase 1E result/runtime is to be rewritten.
* The original Phase 1F-MA 16-task gate failure remains historical; no result
  from it exists.
* Phase 1F-MA-v2 population and code are frozen in docs/124 after a fresh
  researcher authorization. The selected 12 tasks are development-only and
  confirmatory-ineligible; no formal reserve is claimed.
* No model/API call occurred before the immutable transition. Once that commit
  is pushed, exactly the six frozen 12-task streams are authorized.
* Do not tune, retry, replace tasks, create another development run, freeze
  Method v1, or begin formal evaluation. Future formal evaluation requires a
  separately admitted untouched population/split.
