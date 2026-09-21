# 10. Current Review Protocol — Phase 1C Flash Scale Pilot

> Status: active reviewer contract (2026-09-21)
> Frozen method baseline: `c8daa67ba9d9d6257d65e446b437d362e60abc61`
> Active plan: `docs/102_phase1c_flash_scale_hypothesis_pilot_plan.md`

## 1. Review purpose

The current cycle is no longer actor calibration or Phase 1B interface development.

The single review question is:

> Does a 32-task Flash longitudinal pilot show that history-derived exploratory memory
> begins to create scale-dependent mechanism or behavioral value relative to persistent
> generic C2 exploration?

This is hypothesis evidence, not a final paper experiment.

## 2. Before calls

Reviewer must verify:

- Phase 1B behavior is not silently retuned;
- docs/37–38 lifecycle/init definitions are present;
- exactly 32 fresh tasks are frozen before outcomes;
- 8 tasks per admitted family;
- deterministic interleaved order;
- previous used tasks and B1-R reserve excluded;
- no hidden placement/PDDL/outcome used;
- G/T share replay/public initial state;
- qwen3.8-flash is used for all model-facing roles;
- no Max calls;
- G has no access to H/comparison/archive;
- T archive is populated only after actual H activation;
- archive retrieval returns only existing archive IDs;
- C sees only compact selected archive summaries;
- probe budget and canonical continuation are shared;
- registry/transition commit precedes paid calls.

If these fail, block before paid execution.

## 3. During run

Do not tune.

Semantic/model failures are evidence and stay fail-closed.

Do not replace tasks or rerun calls for cleaner outputs.

Only infrastructure failures that prevent execution justify stopping.

## 4. After run

Review four things separately.

### Performance

Report cumulative environment actions for G/T at 8/16/24/32.

Do not over-interpret a single endpoint or require monotonicity.

### H1 — history changes exploration

Inspect H creation/retrieval/activation and whether T probe behavior increasingly differs from G.

### H2 — archive suppresses redundant exploration

Inspect C decisions where relevant archive history was retrieved. Distinguish reasonable
duplicate suppression, materially different proposals, justified retests, apparent redundant
retests and possible over-suppression.

### H3 — cumulative behavior

Judge whether the cumulative G/T cost trajectory gives an early scale-positive signal.

## 5. Decision boundary

Possible research conclusions:

- behavioral + mechanism signal -> worth freezing/replicating with Max and larger protocol;
- mechanism signal only -> likely worth extending horizon before rejection;
- no meaningful mechanism signal -> review hypothesis/system before spending on Max;
- infrastructure/scientific corruption -> result invalid, fix correctness only.

Do not automatically start Max.

## 6. Claims still forbidden

A single 32-task Flash stream does not establish:

- general memory superiority;
- paper-level statistical significance;
- cross-model robustness;
- native cold-start success;
- full autonomous-agent benefit;
- cross-benchmark generality.

The cycle exists only to decide whether the scale-aware hypothesis deserves the next level of
experimental investment.
