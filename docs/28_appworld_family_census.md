# AppWorld family census — Stage A review

2026-09-13. This is the tracked reviewer summary for the offline census in
`docs/26_strategy_lockin_experiment_plan.md`. It supersedes the first-pass
ranking that treated a lower sibling reference call count as evidence for a
better strategy. The implementation is in
`scripts/analysis/appworld_family_census.py` and `src/memory_census/`; rerun it
against the pinned local checkout to regenerate the full machine-readable
records and candidate cards under the ignored `artifacts/` directory.

## Scope and non-claims

The census scans 732 AppWorld task directories grouped into 244 upstream
scenario families. It uses task instructions, seeded state summaries,
research-side evaluator/reference material and public API documentation only
for candidate selection. It performs no model call, network request or
benchmark execution, and its inputs never enter Generator, Reflector, Curator
or another adaptive-loop consumer.

This stage does not establish:

- K₀ / DS-V4-Flash discoverability of B; it is unmeasured everywhere;
- success of B on any target; it is unknown everywhere;
- cost(B); it is unknown everywhere;
- that C is better than alternatives, or that any agent follows the reference
  procedure;
- memory authority, policy concentration or a causal B effect.

Evidence that the reference procedure C runs successfully is not evidence that
C is better than alternatives. A sibling call-count difference is retained as
`reference_cost_gap` diagnostic only: siblings share the same parameterized
reference program, so a gap can be caused by workload/entity volume.

## Reprovenance

- benchmark: ACE AppWorld 0.1.0, pinned checkout SHA recorded by the existing
  ACE adapter;
- dataset content digest (task IDs plus per-task evidence digests):
  `57d8657e0e81749bb41c792e455773dbc723a6b5eff3fb75e115de32b7361567`;
- K₀ playbook digest:
  `3c4f46888c9159088c3eb8f70e879d4d28a5704ab9f15d132563ba0ee2730b7b`;
- family rule: AppWorld scenario generator ID, i.e. the prefix of
  `<generator_id>_<number>`, with contiguous sibling checks;
- generated full report: `artifacts/appworld_family_census/REPORT.md`;
- generated records: `census.json`, `census.csv`, `top10.json` and
  `boundary.json` in that same ignored directory.

The census package has no imports of the AppWorld runtime, ACE runtime,
network clients or model SDKs. Its boundary scan is recorded in
`boundary.json`; the generated artifacts are research-side evidence only and
must not be injected into the ACE loop.

## Result

| Category | Families | Interpretation |
|---|---:|---|
| Shortlist survivors | 0 | No family is worth an explorability probe after conservative offline review |
| Reserve | 26 | Some structural signal, but no admissible B route/cost evidence |
| Rejected | 218 | Failed comparison, reference, strategy-shift, cost or route-scope gates |
| Data-volume-only / no-strategy-shift flags | 3 / 18 | Same C over different workload or no route-relevant change |

No family is selected for the next stage. This is a failed candidate gate, not
evidence that success-induced strategy lock-in is absent from AppWorld. Per
`docs/26`, the next decision should be made after this review rather than by
lowering the gates or starting another benchmark.

## Top-10 reviewed candidates

This is a review list, not ten admissible candidates. It is ordered by
conservative admission/rubric evidence; it is not ordered by the sibling call
gap. Every row has a complete candidate record in the generated JSON, including
source/target IDs, concrete state/instruction differences, C/B evidence status,
reference gap, route provenance, K₀ overlap, comparison gate, rubric and
admission reason.

| Rank | Family | Status | State class | Source → target | cost(C) | cost(B) | Reason |
|---:|---|---|---|---|---:|---|---|
| 1 | `50e1ac9` | reserve | instruction semantic change | `50e1ac9_1` → `50e1ac9_2` | 133 | unknown | B structural saving below registered band |
| 2 | `ce359b5` | reserve | branch parameter change | `ce359b5_2` → `ce359b5_3` | 124 | unknown | no fully supported B route |
| 3 | `b7a9ee9` | reserve | branch parameter change | `b7a9ee9_1` → `b7a9ee9_2` | 95 | unknown | no fully supported B route |
| 4 | `37a8675` | reserve | branch parameter change | `37a8675_1` → `37a8675_2` | 9 | unknown | B structural saving below registered band |
| 5 | `692c77d` | reserve | branch parameter change | `692c77d_1` → `692c77d_2` | 101 | unknown | no reference-supported B route |
| 6 | `3ab5b8b` | reserve | branch parameter change | `3ab5b8b_1` → `3ab5b8b_3` | 33 | unknown | no reference-supported B route |
| 7 | `2a163ab` | reserve | branch parameter change | `2a163ab_3` → `2a163ab_1` | 29 | unknown | no reference-supported B route |
| 8 | `4fab96f` | reserve | branch parameter change | `4fab96f_2` → `4fab96f_1` | 32 | unknown | no reference-supported B route |
| 9 | `aa8502b` | reserve | branch parameter change | `aa8502b_1` → `aa8502b_2` | 29 | unknown | no reference-supported B route |
| 10 | `6171bbc` | reserve | branch parameter change | `6171bbc_1` → `6171bbc_2` | 64 | unknown | no reference-supported B route |

The earlier high-gap families are explicitly rejected as controls against a
common census error: `57c3486` is `data_volume_only`; `d4e9306` is
`data_volume_only`; and `df61dc5`, `afc0fce`, `68ee2c9`, `6c2c621` and
others are `no_strategy_shift` despite large same-C reference gaps. The coupon
family `432dc7a` remains rejected because its instruction explicitly requires
comparison/cheapest-choice reasoning. `27e1026` is rejected on review because
its proposed global Spotify catalogue search is not shown to substitute for
the user-scoped song/album/playlist libraries; equal response fields are not
enough to establish B success or cost.

## Verification boundary

The census tests are synthetic/offline and cover deterministic family grouping,
comparison gating, state-difference classification, reference-only cost and
strategy evidence, report schema, and adaptive-loop isolation. The available
direct test wrapper in this environment resolves `pytest` to an unavailable
`/snap/bin/pytest`; the equivalent unittest suite is the executed test gate.

Reproduction command:

```bash
python scripts/analysis/appworld_family_census.py
```

This work package stops here. No paid experiment, K₀ explorability probe,
source-memory formation run or branch experiment was started.
