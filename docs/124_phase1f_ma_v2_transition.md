# Phase 1F-MA-v2 — Immutable Transition

Date: 2026-09-22

Branch: `exp/minimal-exploratory-memory-validation`

Protocol: `phase1f-ma-v2`

Status: the no-model population, carrier, implementation, and analysis gates
passed. This transition authorizes exactly one 12-task development validation
after the commit containing this document is pushed. It does not authorize
formal evaluation or another development run.

## 1. Purpose and redesign record

Phase 1F-MA asks whether restoring a frozen Generic C2 opportunity on valid
T no-H episodes changes the cross-model attribution picture. The only policy
adaptation is T1's valid no-H route; this is not a search for a policy that
beats G.

The original 16-task proposal required four tasks per family. The audited
`valid_unseen` residual was simple/clean/cool/heat = `5/12/3/4`, so the cool
quota failed before any Phase 1F model call. That blocker remains recorded in
`docs/123_phase1f_population_gate_blocker.md`. The researcher then authorized a
new, separately preregistered 12-task development budget of three tasks per
family. No Phase 1F-MA model outcome existed when this redesign was selected.
The deterministic salt and population procedure were committed first in
`a2e212ff4795ad124cce53e2d92486b4ae75229b`; the final registry was then built
from the frozen public census. No outcome informed selection.

The local residual is not claimed to be a formal reserve. Phase 1F-MA-v2 tasks
are permanently `development-only / confirmatory-ineligible`. The current
pinned residual population is already insufficient to establish a future
multi-stream formal confirmatory study. Formal Population Admission is a
separate future blocker and must establish a new untouched population/split
before paper-level evaluation. No B1-R or other protected task is used.

## 2. Frozen population and identity

The population was deterministically rebuilt and validated from committed
public artifacts using the inherited public eligibility contract: valid
public reset; admitted family; parseable public target; no exact target `take`
action at entry; and at least two public candidate receptacles. Eligibility
and ordering do not use hidden placement, PDDL answers, oracle routes, task
outcomes, or expected arm winners.

The source residual counts are simple/clean/cool/heat = `5/12/3/4`. The frozen
selected order is the required `simple → clean → cool → heat`, repeated three
times; every requested seed is 42.

| Index | Family | Frozen public task ID |
|---:|---|---|
| 1 | simple | `pick_and_place_simple-SaltShaker-None-Drawer-10/trial_T20190909_021613_077537` |
| 2 | clean | `pick_clean_then_place_in_recep-Plate-None-CounterTop-10/trial_T20190908_213420_728917` |
| 3 | cool | `pick_cool_then_place_in_recep-Bread-None-CounterTop-10/trial_T20190908_091835_825830` |
| 4 | heat | `pick_heat_then_place_in_recep-Potato-None-GarbageCan-10/trial_T20190907_161853_945788` |
| 5 | simple | `pick_and_place_simple-SoapBottle-None-Toilet-424/trial_T20190907_004404_604165` |
| 6 | clean | `pick_clean_then_place_in_recep-Mug-None-CoffeeMachine-10/trial_T20190907_221208_560499` |
| 7 | cool | `pick_cool_then_place_in_recep-Pan-None-CounterTop-10/trial_T20190908_114545_244903` |
| 8 | heat | `pick_heat_then_place_in_recep-Tomato-None-GarbageCan-10/trial_T20190908_225453_272533` |
| 9 | simple | `pick_and_place_simple-PepperShaker-None-Drawer-10/trial_T20190918_154326_823501` |
| 10 | clean | `pick_clean_then_place_in_recep-SoapBar-None-Cabinet-424/trial_T20190908_214946_567644` |
| 11 | cool | `pick_cool_then_place_in_recep-Mug-None-Cabinet-10/trial_T20190909_121635_622676` |
| 12 | heat | `pick_heat_then_place_in_recep-Cup-None-Cabinet-10/trial_T20190907_083346_800823` |

Frozen artifacts:

| Artifact | Path | SHA-256 |
|---|---|---|
| Full public residual census | `experiments/exploratory_memory_mvp/cases/phase1f_ma_v2/public_residual_census.json` | `b650bc30d12ad1ef3fa54494d5438c12ff76adce271a4f90f8e47b0943ab39d0` |
| Historical/protected exclusions | `experiments/exploratory_memory_mvp/cases/phase1f_ma_v2/historical_exclusions.json` | `3e00dcd05770551183df56f75be2b73934771ffdbce8e55b6256b77201611b3a` |
| Selected registry | `experiments/exploratory_memory_mvp/cases/phase1f_ma_v2/registry.json` | `948d858ee6b02269b32894f0cca5598a9111ba3079886ea4859ce6d18f011333` |
| Selected task ID sequence digest | registry field `selected_task_ids_sha256` | `0c992f93c6b19dae08f5e99cec747a25a657326095ce89ff5853a838483c2ab3` |
| Post-selection carrier replay identity | `experiments/exploratory_memory_mvp/cases/phase1f_ma_v2/carrier_replay_manifest.json` | `a66308fed63aba7455f7e0628e92e1371611c3905b8a480afc4dc246b7a991b0` |

The population validator reports 98 historical/protected exclusions, 32
Phase 1D development exclusions, and the exact eligible residual counts above.
It validates disjointness from Phase 1A–1E, Phase 1B development, B1-R, and
other committed protected IDs. The population builder reads only committed
public census/registry fields and does not initialize the carrier.

The separate carrier manifest was produced only after population selection.
It verifies the pinned carrier's task/seed/split and public initial
fingerprint. Its identity hashes are execution-integrity metadata only; they
do not affect eligibility, selection, ranking, or ordering, and no hidden
placement/PDDL answer was interpreted. The no-model carrier preflight passed
12/12 tasks with zero task-solving actions, zero model calls, and zero model
transport initializations. Its runtime is
`artifacts/exploratory_memory_mvp/phase1f-ma-v2-carrier-preflight-20260922-automanual`.
An earlier environment-discovery attempt used a Python environment without
TextWorld and failed before carrier initialization; that fail-closed artifact
was retained separately and had no scientific effect.

## 3. Frozen arms and T1 routing

All six streams start as independent fresh states under the same Phase 1 warm
start. G starts with canonical K*. T0 and T1 each start with canonical K*,
empty active/consumed H, empty Exploration History, empty comparison ledger,
and empty evidence state. No Phase 1C/1D/1E evolved state is imported and no
state is shared between models or arms.

| Arm | Frozen route |
|---|---|
| G | Generic C2 on every task, then canonical continuation if needed, then the frozen offline pipeline. |
| T0 | Valid H activation uses the frozen targeted probe; valid no-H goes to canonical continuation. |
| T1 / T-Hybrid | Valid H activation uses exactly the T0 targeted probe; valid NONE or a mechanically empty active-H pool uses frozen Generic C2 with T1's own current Established Memory, then canonical continuation if needed. |

An H retrieval/model/schema error retains frozen fail-closed behavior and does
not trigger Generic C2 fallback. T1 Generic C2 is ordinary online
exploration, not an H: it does not create/activate/consume/archive H, bind
evidence to a comparison, or count as targeted-memory activation. Its actual
public actions and observations continue through the unchanged frozen A/B/C
pipeline. With no consumed H, A receives no synthetic comparative-H binding.

The only scientific intervention is T1's valid no-H composition relative to
T0. Prompts, schemas, memory lifecycle, retrieval, candidate budget, executor,
canonical continuation, endpoint, and failure semantics are unchanged.

## 4. Model and execution freeze

Every model-facing role in each stream uses that stream's single backbone:

| Stream group | Backbone | Temperature | Thinking |
|---|---|---:|---|
| Flash-G / Flash-T0 / Flash-T1 | `qwen3.8-flash` | 0 | false |
| Max-G / Max-T0 / Max-T1 | `qwen3.8-max` | 0 | false |

Roles are candidate selector, active-H retrieval, B, Exploration-History
retrieval, C, A, and H/comparison reconciliation. Mixed roles and
model-specific prompt tuning are prohibited. The frozen K* digest from the
prepare-only run is
`331728a3e001c8a3bc7e992d7605ee428501c34d0d5d8fed75a19abd98314447`; maximum
candidate probes remain 2.

The experiment is exactly 12 tasks × 3 arms × 2 models = 72 episodes, with no
repetitions, retries, replacements, or mid-run changes. Tasks within each
longitudinal stream execute in order. The runner will use a single execution
worker, processing independent stream states sequentially to avoid unnecessary
provider/host concurrency risk; this does not parallelize tasks within any
stream or share state.

The primary contrast is environment actions to exact target acquisition for
`T1 − T0`, separately for Flash and Max. Secondary contrasts are `T0 − G` and
`T1 − G`. The frozen analysis reports all 12 tasks, families, first/second
halves, per-task paired values, H-active/no-H groups, and T1 no-H generic-probe
direct acquisitions, candidate sequences, and action costs. Secondary
mechanism telemetry includes A roles/assessments, B/C statuses, H creation and
activation, archive/backlog, comparison status, and reconciliation operation.
No significance threshold or new primary metric is introduced.

## 5. No-model verification and execution authorization

No Phase 1F-MA model/API calls occurred before this transition. The separate
carrier preflight and six-stream prepare-only run report zero model calls and
zero transport initializations. Prepare-only initial-state digests are
recorded in:

`artifacts/exploratory_memory_mvp/phase1f-ma-v2-prepare-only-20260922-a2e212f/run_config.json`

Verification before transition:

* Phase 1F population/T-Hybrid/analyzer/Phase 1B regressions: **39 passed**.
* Phase 1C/Phase 1C H2/Phase 1D regressions: **19 passed**.
* Phase 1E cross-model/resume/prefix regressions: **22 passed**.
* MVP and controlled-targeting regressions: **29 passed**.
* Ruff on changed/new Phase 1F Python modules and tests: **passed**.
* Python compile checks on changed/new Phase 1F modules and tests: **passed**.
* `git diff --check`: **passed**.
* Registry and carrier replay manifest validation in the pinned Python 3.9
  `memory-automanual` environment: **passed**, 12/12.

The immutable transition commit containing this document, the selected
registry, carrier identity manifest, runner, analyzer, tests, and current-state
contract is the prerequisite for execution. Once that commit is pushed, it
authorizes only the six frozen streams (72 episodes) described here. Any
infrastructure failure must be preserved and handled under the explicit
stop/resume discipline; there are no silent retries or replacements. Formal
evaluation remains unauthorized.
