# Phase 1E Max Resume Transition

Date: 2026-09-22
Protocol: `phase1e-max-resume-v1`
Branch: `exp/minimal-exploratory-memory-validation`

## Authorization and scope

This is an infrastructure-only continuation of the original, preregistered
Phase 1E Max stream. The original execution stopped at global task 62 before
either scientific arm was created because the carrier could not copy
`libdownward.so` into `/tmp` (`OSError: [Errno 28] No space left on device`).
The researcher explicitly authorized a no-model prefix audit, resume-integrity
checks, a carrier-only preflight, and—only after this immutable transition is
committed and pushed—continuation from the original M61 state for tasks 62–64.

**The resume is not a replacement run and does not rerun tasks 1–61. It
continues the same longitudinal state after an external host interruption.**
No method, prompt, population, task order, replay specification, model setting,
or scientific behavior changes. No model/API call occurred while preparing
this transition.

The original Phase 1E attempt remains recorded as infrastructure-invalid in
`docs/114_phase1e_max_validation_results.md` and
`docs/115_phase1e_max_validation_semantic_review.md`; this document does not
rewrite those historical results.

## Frozen source identity

| Item | Frozen identity |
|---|---|
| Original Phase 1E transition/execution commit | `0ada22175818aa8aa6de6f152d91cb9e0ed0032d` |
| Original runtime | `artifacts/exploratory_memory_mvp/phase1e-cross-model-max-v1-20260922-0ada221` |
| Original combined registry | `experiments/exploratory_memory_mvp/cases/phase1e_cross_model_registry.json` |
| Registry SHA-256 | `a46ecec068060ccc264dcc994b74e088776b98e3b9f2c31982bfb83a3e5b1a7f` |
| Selected task-ID SHA-256 | `69cf0bc660df2283aa55b668aece2cecca39da73d76e31e886968da003bc3fe7` |
| Original task-62 carrier failure SHA-256 | `f58ea0918bedfd717ef1fb0ef0bfdeec9ff3d353f4092c9f8e211b0b1d92095a` |

The original runtime contains completed paired artifacts for exactly indices
1–61. Each has G/T completed summaries and a valid pairing proof. The original
task-62 directory contains only the recorded carrier `failure.json`; it has no
G/T episode or model-call artifacts. Tasks 63–64 were not attempted. The
read-only validator additionally checks the saved request/usage model identity,
zero recorded retries, unique call IDs, pairing/replay metadata, and registry
order.

### M61 state endpoint

The M61 snapshots match the task-61 materialized states and recomputed frozen
state digests:

```text
G M61:
aded8deab94573908b26d5d0359890702a5575619e4ea7bcf570d5dadffbcfcd:
4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945

T M61:
ab8f31135e15a3df85336cc7da35a873a439725b4fdd7296396ad543f7aec4c3:
ea68b1fb8453b313a3f0a492dd04615147baccdbdfe61dd6f0521705500c159a
```

The resume copies these exact states into its own continuation endpoint. G and
T remain independent. The runner does not reinitialize either arm from K* and
does not load any Flash-evolved state.

## No-model prefix diagnostic

The separately versioned prefix analysis is documented in
`docs/116_phase1e_max_prefix_diagnostic.md` and, when generated, stored outside
the immutable runtime under a Phase 1E prefix-diagnostic artifact path. It
reads only the saved 1–61 task artifacts and frozen registry. It is explicitly
an incomplete-prefix diagnostic, not the final cross-model result.

## Remaining frozen suffix

Exactly these registered tasks remain, in their original order and with their
original seed, replay specification, and public initial fingerprint:

| Global index | Family | Task |
|---:|---|---|
| 62 | `pick_clean_then_place_in_recep` | `pick_clean_then_place_in_recep-Cloth-None-Cabinet-424/trial_T20190908_022321_380927` |
| 63 | `pick_cool_then_place_in_recep` | `pick_cool_then_place_in_recep-Tomato-None-Microwave-10/trial_T20190909_102710_795182` |
| 64 | `pick_heat_then_place_in_recep` | `pick_heat_then_place_in_recep-Cup-None-Cabinet-10/trial_T20190907_083429_887065` |

The preflight reproduced all three registered public initial fingerprints and
replay-spec identities. It executed zero environment actions and made zero
model calls. Its artifact is:

```text
artifacts/exploratory_memory_mvp/
phase1e-max-resume-preflight-v1-20260922-a4cd7ec/carrier_preflight.json
```

## Temporary-storage correction

The issue was host temporary-storage placement, not the pinned carrier or
scientific environment. The resume process binds `TMPDIR`, `TMP`, `TEMP`, and
Python's `tempfile` directory to:

```text
/home/coolboy/phase1e-max-resume-tmp.AnGISV
```

This directory is on filesystem device `2096`, distinct from `/tmp` device
`127`. The preflight recorded approximately 1.08 TB total and 962 GB free at
the time of the check. The temporary-library copy and carrier initialization
succeeded for each of tasks 62–64. No ALFWorld/TextWorld behavior or replay
semantics were changed.

## Resume execution contract

After the immutable transition commit is pushed, the only authorized model
calls are the frozen Phase 1E Max calls for tasks 62, 63, and 64, sequentially:

```text
provider: DashScope-compatible direct transport
model: qwen3.8-max for every model-facing role
thinking: false
temperature: 0
arms: G then T for each registered task
retries: none
replacements: none
```

Each task's actual G/T episodes must pass pairing before either arm executes.
The resume writes before/after state snapshots so final reconstruction can
prove `M61 → M62 → M63 → M64` independently for G and T. If another carrier or
episode infrastructure failure prevents protocol execution, its artifact is
preserved and execution stops; no task-level retry is permitted.

The final deterministic merger will combine original indices 1–61 with resume
indices 62–64 without modifying either source runtime. It must verify all 64
pairs, exact registry order, Max-only calls, zero retries, unique call IDs,
pairing/replay identity, and continuous state lineage. The final report will
describe the run as segmented, not uninterrupted.

## No-model verification record

Completed before this transition commit, without model/API calls:

* Real-source `validate_resume_source()` passed: exactly 61 completed G/T
  pairs; 500 Max request/usage call records with unique call IDs and no retry
  records; task 62 contains only the registered failure artifact with the
  frozen SHA-256 above; tasks 63–64 are absent; M61 snapshots match the
  materialized task-61 states and frozen state digests.
* Real carrier-only preflight validation passed for exactly tasks 62–64, with
  registered seed/replay/public fingerprints, 0 environment actions, and 0
  model calls. The ignored preflight artifact remains at the path above.
* The deterministic prefix artifact was reproduced at
  `artifacts/exploratory_memory_mvp/phase1e-max-prefix-diagnostic-v1-20260922/diagnostic-final.json`
  (SHA-256 `b1ab60c6d237eb0c115339bdea2b98a81de3db1707c54d2b6fcb075b0d1bcdf7`)
  and reports 61 valid paired tasks / 122 episodes.
* Focused resume, prefix, Phase 1E, Phase 1D, Phase 1C, Phase 1B, and MVP
  regression command completed after adding a task-62 failure-artifact
  mutation check: **81 tests passed**.
* Ruff passed on all five changed Python files. Python `compileall` passed on
  those same files. `git diff --check` passed.

No scientific episode, model call, task retry, or task replacement occurred
during this preparation. These are pre-transition checks; the paid resume
runner additionally requires this transition to be committed and the
worktree clean before `--run` is accepted.

The transition runner fails closed unless the branch is the authorized
experiment branch, the resume transition is committed and the worktree is
clean, the registered source/runtime hashes match, the exact M61 state and
preflight are validated, and `--allow-network` is supplied. Therefore no
resume model call can occur before the immutable transition commit exists.
