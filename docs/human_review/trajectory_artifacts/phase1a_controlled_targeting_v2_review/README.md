# Phase 1A controlled-targeting v2 forensic evidence packet

All JSON files in this packet copied from the listed runtime paths are marked:

```text
ORIGINAL SAVED ARTIFACT
```

They are byte-for-byte copies of the existing runtime/committed artifacts. No
model call or episode rerun was used to produce this packet. The packet is a
review convenience; the complete runtime remains under `artifacts/` and is
still the source of truth.

## Frozen artifacts

| packet file | provenance | original path |
|---|---|---|
| `frozen/source_h_manifest.json` | ORIGINAL SAVED ARTIFACT | `artifacts/exploratory_memory_mvp/phase1a-controlled-targeting-v2-source-20260920-8103a79/source_h_manifest.json` |
| `frozen/target_eligible_h_manifest.json` | ORIGINAL SAVED ARTIFACT | `artifacts/exploratory_memory_mvp/phase1a-controlled-targeting-v2-targets-20260920-4f01e89/target_eligible_h_manifest.json` |
| `frozen/target_h_assignments.json` | ORIGINAL SAVED ARTIFACT | `artifacts/exploratory_memory_mvp/phase1a-controlled-targeting-v2-targets-20260920-4f01e89/target_h_assignments.json` |
| `frozen/source_scope_review.json` | ORIGINAL SAVED ARTIFACT | `experiments/exploratory_memory_mvp/cases/phase1a_h_scope_review.json` |

The source-H manifest digest is `3298cddbba85d80e55d1d42c22dcf10e1563af734f821303fcd0628a9e9b3849`.
The target-eligible manifest digest is
`69742e9e733fcbe509954c5431dd2e4c5a78e06f30577ee3504ac12f9a7a97e4`.
The assignment digest is
`c2717b28bab8a9c816ff99411e3af210bdf7b1f47f874d32896c60e256daf43f`.

## Selected target slices

Each directory below contains the original `target_summary.json`, pairing and
assignment/provenance files, and only the saved C2/C3 selector-step artifacts
needed for the forensic comparison. These are not complete episode copies.

| artifact directory | target represented | why selected |
|---|---|---|
| `selected_targets/fe5a5bac7cf1` | SprayBottle -> Toilet-426 | C2 and C3 both acquire; C2 lower-probe contrast |
| `selected_targets/f13421bdbb8a` | clean Apple -> Fridge-27 | both-fail budget-censoring example |
| `selected_targets/6ce98e7a5d4c` | heat Egg -> GarbageCan-2 | C2-only acquisition |
| `selected_targets/32c555941b2f` | heat Apple -> GarbageCan-12 | C3-only acquisition |
| `selected_targets/31fc27164084` | cool Mug -> CoffeeMachine-30 | C3-only acquisition and cost contrast |
| `selected_targets/99916f3dc764` | cool Bread -> CounterTop-15 | both-fail public remote-take action anomaly |
| `selected_targets/0ff999aff7a8` | cool Cup -> Microwave-30 | both-fail case where exhaustive public scan did not expose an exact target take action |

For every copied selected-step file, the original runtime prefix is:

```text
artifacts/exploratory_memory_mvp/phase1a-controlled-targeting-v2-targets-20260920-4f01e89/targets/<artifact-directory>/
```

The complete original paired runtime is:

```text
artifacts/exploratory_memory_mvp/phase1a-controlled-targeting-v2-targets-20260920-4f01e89
```

The forensic report's H labels and per-target tables use
`frozen/target_h_assignments.json`, not the earlier memo transcription.

`derived_public_both_fail_scan.json` is not an original runtime artifact. It is
marked `DERIVED OFFLINE PUBLIC-ONLY DIAGNOSTIC` and records the post-hoc scan
described in the forensic report; it contains no hidden placement or evaluator
answer.
