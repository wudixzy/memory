# 10. Current Review Protocol — Phase 1E Max M61 Resume

> Status: Phase 1C and Phase 1D completed. The original Phase 1E Max attempt
> stopped before task 62 episode creation because `/tmp` had no space. The
> researcher has authorized a no-model audit and, after an immutable resume
> transition is committed/pushed, continuation from Max M61 for only registered
> tasks 62–64. No model/API call is authorized before that transition.
> Frozen method baseline: `c8daa67ba9d9d6257d65e446b437d362e60abc61`
> Authoritative result docs: `docs/104_phase1c_flash_scale_pilot_results.md`,
> `docs/105_phase1c_flash_scale_pilot_semantic_review.md`
> Current audit/plan: `docs/107_phase1c_h2_exploration_history_audit.md`,
> `docs/108_phase1d_flash_long_horizon_validation_plan.md`

## 1. Active authorization boundary

The active cycle is the infrastructure-only `phase1e-max-resume-v1`
continuation. It must use the exact original Phase 1E registry and Max G/T M61
states; run only tasks 62→63→64; use `qwen3.8-max` for every model-facing role;
and preserve segmented execution provenance. Tasks 1–61 must never be rerun.
No retries, replacements, Flash fallback, method changes, or formal evaluation
are authorized. The no-model prefix and resume records are in docs/116–117.

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

The project has not established general memory superiority, cross-model
robustness, native cold-start performance, full autonomous-agent benefit, or
cross-benchmark generality. Phase 1D supported a development-scale Flash
signal, after which the authorized Phase 1E Max validation was attempted but
stopped as infrastructure-invalid. The next stages remain researcher review
of that failure, a protocol-consistent replacement only if authorized,
cross-model validation, Method/Evaluation v1 freezing, and only then fresh
formal controlled evaluation.

Phase 1E transition `0ada221` preceded all recorded Max calls, but the original
run is invalid/incomplete because the carrier stopped before task 62 episode
creation with `OSError: [Errno 28] No space left on device` while writing a
temporary `libdownward.so`. The researcher has explicitly authorized only the
segmented M61 continuation for tasks 62–64 after docs/117 is committed/pushed;
no replacement of tasks 1–61, formal evaluation, or other model call is
authorized.
