# Phase 1C Flash Scale-Aware Hypothesis Pilot — Immutable Transition

Date: 2026-09-21
Branch: `exp/minimal-exploratory-memory-validation`
Protocol: `phase1c-scale-pilot-v1`

This document freezes the no-model transition for the first Phase 1C Flash
pilot. No model/API call has been made for this path before the transition
commit. The pilot remains development evidence for the scale-aware hypothesis;
it is not a paper-level superiority evaluation.

## Frozen population

The pinned repository does not contain the required untouched public `valid_seen`
split, and the usable `train` population is not large enough after prior-use
exclusions. The protocol therefore uses the explicit pinned `valid_unseen` split,
selected before any Phase 1C arm outcome exists. This is a carrier/population
fact, not an outcome-based choice.

The public-only census and deterministic registry are committed at:

`experiments/exploratory_memory_mvp/cases/phase1c_scale_pilot_registry.json`

Frozen census and selection:

| item | value |
|---|---:|
| public `valid_unseen` task/trial census | 135 |
| public eligible universe | 88 |
| eligible simple / clean / cool / heat | 21 / 28 / 19 / 20 |
| selected stream | 32 |
| selected per family | 8 |
| requested seed | 42 |
| registry SHA-256 | `0975718ce5de471e70bc29412291558ac50db5b2a40dfa958f6fe115184119f9` |
| selected-ID SHA-256 | `0cf944c9e2ebe229a95337f720fa88effff0ce94a2d9d146dff0a07022ab7672` |

The selected order is the frozen interleave: `simple → clean → cool → heat`,
repeated eight times. The public exclusion manifest records prior partitions, the
12 explicit B1-R reserved tasks, public instruction/entry-state exclusions, and
out-of-scope families. The B1-R public census is not treated as prior scientific
use; only its explicit reserved set is excluded.

Eligibility uses only task family, public instruction, public reset observation,
ordered public admissible actions, and public candidate structure. No PDDL
placement, hidden answer, oracle route, arm outcome, or expected winner is used.

## Frozen Phase 1C implementation

The new versioned path is implemented in:

* `experiments/exploratory_memory_mvp/phase1c_population.py`
* `experiments/exploratory_memory_mvp/phase1c_contract.py`
* `experiments/exploratory_memory_mvp/prompts_phase1c.py`
* `experiments/exploratory_memory_mvp/run_phase1c_scale_pilot.py`

The runner maintains independent G and T state. Both arms share the registry,
replay specification, public initial fingerprint, Flash model configuration,
candidate-index selector, two-candidate probe budget, controlled executor,
canonical continuation, acquisition endpoint, and factual/A validation
semantics. Each task is reset into both actual episodes and the pairing proof is
checked before the first model call for that pair.

G uses the Phase 1A generic C2 probe on every task and has no B/C, H,
comparison-ledger, or exploration-history input. T retrieves at most one active
H, consumes it after activation, and writes a compact exploration-history record
only for an actually activated H. History retrieval is called only after
`B=OPEN` and is restricted to at most three real archive IDs. C receives only
compact selected summaries; raw trajectories and the evidence archive remain
runner artifacts.

The two arms never share evolved memory. Checkpoint snapshots are written after
tasks 8, 16, 24, and 32. The primary metric is cumulative environment actions
to exact target acquisition, not the number of episodes (`scientific n = 32`).

All model-facing roles are frozen to:

```text
provider: DashScope-compatible direct transport
model: qwen3.8-flash
thinking: false
temperature: 0
```

The transport removes proxy variables through the existing model utility. The
Phase 1C runner does not use `qwen3.8-max` or a mixed configuration.

## No-model verification before execution

The transition verification consists of the Phase 1C focused tests, Ruff on all
new/changed Python files, Python compilation of those files, and `git diff --check`.
The committed registry was generated using the pinned ALFWorld carrier with
public resets only. No Phase 1C model transport was initialized.

The next authorized action after this immutable transition is exactly one
complete 32-task G/T Flash stream (`64` episodes), with no mid-run task
replacement, retry, prompt/model change, or Max invocation.
