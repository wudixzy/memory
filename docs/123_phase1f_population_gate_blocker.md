# Phase 1F-MA Population Gate — Blocked Before Execution

Date: 2026-09-22

Branch: `exp/minimal-exploratory-memory-validation`

Audit type: no-model, public-only population/protection audit

Decision: **STOP BEFORE MODEL CALLS**

## 1. Result

The authorized Phase 1F-MA run requires exactly 16 fresh development tasks,
four in each frozen family, plus a defensible development/formal population
boundary. The audited local pinned/public pools do not satisfy these
conditions:

| Public split / stage | Simple | Clean | Cool | Heat | Notes |
|---|---:|---:|---:|---:|---|
| `train`, Phase 1A public eligible universe | 9 | 9 | 9 | 9 | All 36 in-scope candidate entries are already included in the Phase 1A Source/Calibration/Target/residual-excluded partitions. |
| `valid_unseen`, Phase 1C public eligible universe | 21 | 28 | 19 | 20 | 88 eligible public-reset records in the frozen Phase 1C registry. |
| `valid_unseen`, Phase 1D frozen eligible universe | 13 | 20 | 11 | 12 | 56 total after the frozen historical/protected exclusions. |
| `valid_unseen`, Phase 1C/1D selected development tasks | 8 | 8 | 8 | 8 | Phase 1E reused these same 64 task identities; they are not fresh Phase 1F tasks. |
| `valid_unseen`, eligible remainder after the 32 Phase 1D selections | 5 | 12 | 3 | 4 | 24 total; the frozen quota fails because `cool=3 < 4`. |

The 12-task B1-R reservation remains protected (three per family). It is an
actor-gate reserve, not a Phase 1F development pool or a formal reserve, and
is not borrowed to fill the deficit. No task was selected, replaced, or
reset for this Phase 1F cycle.

## 2. Formal-reserve boundary

The local pinned ALFWorld data root contains only `train` and `valid_unseen`.
The `valid_seen` evaluation split referenced by the ALFWorld configuration,
and public `test_normal` / `test_challenge` splits, are absent locally. No
committed formal-reserve manifest or task registry was found. Therefore the
repository cannot presently prove a distinct, untouched formal population
boundary for this proposed development block.

The unused remainder of `valid_unseen` is not silently relabeled as a formal
reserve: that split already contains the Phase 1C/1D development stream and
the protected B1-R tasks. B1-R is not repurposed as a confirmatory reserve.
Availability of `valid_seen` elsewhere is unknown and must not be treated as
either available or empty without a new, documented census.

## 3. Sources and public-only method

The audit used the repository's frozen public artifacts and split inventory:

* `experiments/exploratory_memory_mvp/cases/phase1_registered_targets.json`
  — Phase 1A public candidate universe and actual partitions;
* `experiments/exploratory_memory_mvp/cases/phase1_b1r_reservation.json` —
  protected B1-R task IDs;
* `experiments/exploratory_memory_mvp/cases/phase1c_scale_pilot_registry.json`
  — frozen Phase 1C population;
* `experiments/exploratory_memory_mvp/cases/phase1d_long_horizon_registry.json`
  — 135 public reset records, 56 eligible records, selected 32 and the
  exclusion provenance;
* `experiments/exploratory_memory_mvp/cases/phase1e_cross_model_registry.json`
  — Phase 1E reuse of the frozen Phase 1C/1D task population;
* `configs/automanual_alfworld/upstream.json` and the local split directory
  names.

The inherited eligibility contract uses only public task family/instruction,
reset observation, ordered admissible actions, and public candidate
affordances. The source census records split/task directories and public
reset states; it does not inspect PDDL contents, hidden placements, oracle
routes, task outcomes, or expected arm winners. No model/API call was made.

The pinned execution source recorded in `upstream.json` is
`aeb17e4a4fe8bb43b9eb390b7b0b94a3ca8b9324`. Its data checksum manifest does
not cover the complete ALFWorld data tree; the vendored checkout also has
pre-existing local modifications in four upstream files. Those files were
left untouched. Thus this audit relies on the committed public registry
digests for the already frozen populations and does not claim a full raw data
tree checksum.

## 4. Stop decision and next required researcher input

The failed cool-family count alone blocks the 16-task design. Independently,
the formal-reserve boundary is not established. In accordance with the
pre-registered rule:

* no Phase 1F task registry or selection salt was frozen;
* no experiment transition document or transition commit was created;
* no model/API call, actor episode, or T-Hybrid run was made;
* no B1-R task was borrowed;
* the 12-task or any relaxed-eligibility design was not substituted.

The independent code-only T-Hybrid workstream produced:

* `experiments/exploratory_memory_mvp/run_phase1f_matched_adaptation.py`;
* `experiments/exploratory_memory_mvp/analyze_phase1f_matched_adaptation.py`;
* `tests/test_phase1f_matched_adaptation.py`.

Its route/lifecycle tests use fake episodes and fake transport only. The
runner carries a closed population gate and no task registry was constructed.
No model/API/network call occurred. The scaffold is not an experiment
transition and does not authorize execution. Resumption requires researcher
direction establishing an eligible development-only pool of at least four
tasks per family and an explicit untouched formal-reserve boundary, or
authorizing a newly specified population/design. No experiment should run
until that population is frozen and a real immutable transition exists.

Verification actually run in this cycle:

* Phase 1F-MA focused tests: 9 passed;
* Phase 1C scale tests: 13 passed;
* Phase 1C H2 audit tests: 1 passed;
* Phase 1D tests: 5 passed;
* Phase 1E cross-model tests: 6 passed;
* Phase 1E resume tests: 11 passed;
* Ruff check on all three added Python files: passed;
* `compileall` on all three added Python files: passed;
* `git diff --check`: passed after removing Markdown trailing whitespace.
