# 70. Phase 1A Final Pre-Actor Patch Results

> 状态：无模型调用完成；未运行 actor calibration；未运行 Phase 1A paid pilot。
> 分支：`exp/minimal-exploratory-memory-validation`
> 阶段：Phase 1A — Receptacle-Search Targeting Pilot

本轮只修正实验不变量，没有改变 B/C/H/A、Functional Contract、action-index、pairing
proof 或 heavy-offline/light-online 方法边界。

## 1. Frozen public population and partitions

完整 pinned ALFWorld train split 的 public-only eligible universe 仍为 54 条记录。当前
冻结分区为：

| partition | count | scientific role |
|---|---:|---|
| Source | 5 | frozen source histories；不参与 actor gate |
| hard calibration | 10 | Phase 1A in-domain C1 admission gate |
| diagnostic calibration | 18 | out-of-domain stress/diagnostic only |
| Target | 20 | Phase 1A target pool |
| residual excluded | 1 | public hash quota residual |

hard calibration 的 10 个任务全部属于四个 Phase 1A task families；diagnostic calibration
不决定 admission。四个非 residual partition 两两不相交，五个 partition 覆盖完整 54
条 public universe。target reservation 保持原有 public-only stable-hash 结果，因此没有
通过 outcome 重选 target。

`build_phase1_registry.py` 现在在一次 public reset-only 构建中同时写出完整 target registry
和 calibration registry；不需要手工复制分区记录。

冻结 digest：

```text
candidate IDs:          6f12d1a1e26a9a5d5b95567a1b0900d08cce8b39d745939a8332b39b35cdb283
public records:         f0c2157f2a78bccc2a36750b696866c6f87a2fb570a3a6bc89f7bb5cc438ecf3
partitions:             fc548e0f4f493074ed2bc20b05433b6d7a94602e8c77a694cc745030037b120f
target registry:        0e43d9846ad96249ef1b421b02585a0fff1190e76eb6156b64e64da6c805588d
calibration registry:   87605dd5bd9810ee8c9e7867e8e176d60034c6969babff58fbb81b73e5a4e120
source reservation:     a6c9d990b60d8563ba83baadd7845e1a8df440c8c371a15aadb62253860bf55d
applicability contract: 71d982a25ab3d9b7da40b71e1f3900e39fcd0f59ddd40e551b040c38d4499d82
actor manifest:         00816f2eeb6626dfd68ec20943aef0f755e689fa657587a2f6af628aad8c3a94
probe budget:           6513813712b26a474ebce8cbfcc49b8544d7681cc004cabfc3b0b24be034184e
source-H manifest:      8ebee748294f3ed48559988b30c96cc10d4e538063302bf52c8cdc440691dc85
canonical K*:           331728a3e001c8a3bc7e992d7605ee428501c34d0d5d8fed75a19abd98314447
```

## 2. Probe-budget correction

`max_probe_actions = 4` remains the only hard mechanical H termination budget. The existing
`max_distinct_candidate_visits = 2` field remains in the symmetric C2/C3 contract as telemetry
only; it cannot remove H or terminate a probe. This avoids treating `go to cabinet` as a full
inspection when a later `open cabinet` is still required.

`probe_runtime_state` now exposes:

```text
episode_visited_receptacles   # all executed public navigation
probe_visited_receptacles     # only probe_action_history
visited_receptacles           # compatibility alias for probe-local visits
probe_action_count
```

No field chooses a next action or classifies semantic evidence. Tests cover pre-probe navigation,
multiple candidate visits beyond the telemetry threshold, and hard removal only at the action
budget.

## 3. Public H-family applicability contract

`h_family_receptacle_search` is bound to
`phase1a-receptacle-search-public-contract-v1`. Before target/H assignment, the runner checks
only public entry fields:

- one of the four frozen Phase 1A task families;
- no directly executable `take ...` action at entry;
- at least two public `go to <entity_id>` candidate affordances;
- a non-empty public instruction; the local search subproblem is supplied by the public task
  family, not by hidden placement.

There is deliberately no requirement that an open surface contain the target, and no outcome,
PDDL fact, oracle trajectory or semantic online judge is used. A future C result with a narrower
scope must either record this same mechanically testable public contract or be rejected during
source-H freeze.

## 4. Source-H referential integrity

The committed `phase1_source_h_manifest.json` is still empty (`manifest_status` is
`schema_only_no_live_b_c_artifacts`), because this cycle makes no B/C calls. The new
`freeze_source_h.py` command and `h_manifest.freeze_source_h_entry()` path are ready for the
next gate. They compute artifact hashes from bytes and require:

```text
source_task_id in phase1_source_tasks.json and registry.partitions.source
source_task_seed == frozen public source seed
k_star_sha256 == compute_k_star_digest(get_phase1_k_star())
source_history_sha256 == hash(actual source-history artifact)
b_artifact_sha256 == hash(actual B artifact)
c_artifact_sha256 == hash(actual C artifact)
future_h == future_exploratory_memory(validated C CREATE result)
future_h_sha256 == hash(future_h)
applicability_contract_id == frozen Phase 1A contract
offline_model_config == the same embedded B/C offline configuration
```

The B/C freeze artifacts must be JSON envelopes containing their validated result plus the
normalized `offline_model_config`; a separate claimed config or manually supplied SHA is not
accepted as provenance. The standalone `phase1_source_tasks.json` must exactly match the Source
partition in the frozen public registry.

`validate_frozen_h_entry_artifacts()` rechecks the source, K*, all file hashes and the C
projection, so stale source history, missing/mutated B/C artifacts and projection drift fail
closed. Actor inputs receive only `future_h`; source task IDs, hashes, B/C artifacts and offline
provenance remain model-invisible.

## 5. Actor-gate status and provider scope

The actor manifest has an explicit status vocabulary:

```text
candidate_pending_independent_reliability_gate
passed_independent_reliability_gate
rejected_independent_reliability_gate
```

The committed Qwen3.8-Flash manifest remains `candidate_pending_independent_reliability_gate`.
Pending is accepted by calibration-mode config validation, but the scientific C1/C2/C3 paired
runner fails closed unless the status is `passed_independent_reliability_gate`. No model was
selected or marked passed here.

The actor configuration is manifest-driven. The current transport is specifically
DashScope-compatible and direct/no-proxy. Switching to another DashScope-hosted model is
supported by the manifest/config structure; a non-DashScope provider would require a later
transport adaptation and is not claimed here.

## 6. Commands prepared for the next paid gate (not run)

The following files/commands are the next-cycle interfaces; none was executed in this cycle:

```bash
# B1: run the independent in-domain Actor + K* = C1 screen only.
# Use hard_records from this frozen registry; diagnostic_records are not admission data.
PYTHONPATH=src:experiments:. python -m exploratory_memory_mvp.run_phase1_calibration \
  --calibration-registry experiments/exploratory_memory_mvp/cases/phase1_calibration_registry.json \
  --partition hard_calibration \
  --actor-manifest experiments/exploratory_memory_mvp/cases/phase1_actor_manifest.json \
  --output <gate-b1-output> \
  --allow-network

# B2: after B/C calls, freeze one real source H from saved artifacts.
PYTHONPATH=src:experiments:. python -m exploratory_memory_mvp.freeze_source_h \
  --h-id <h-id> \
  --source-task-id <frozen-source-task-id> \
  --source-history <source-history.json> \
  --b-artifact <b-envelope-with-offline-config.json> \
  --c-artifact <c-envelope-with-offline-config.json> \
  --offline-config <normalized-offline-config.json> \
  --creation-version <freeze-version> \
  --manifest experiments/exploratory_memory_mvp/cases/phase1_source_h_manifest.json

# B3: audit assembled C2/C3 contexts after live Hs exist and before target outcomes.
PYTHONPATH=src:experiments:. python -m exploratory_memory_mvp.phase1_context_audit \
  --artifact C2=<saved-C2-actor-input.json> \
  --artifact C3=<saved-C3-actor-input.json>
```

`run_phase1_calibration` is a prepared next-cycle paid-run entrypoint and was not invoked by this
no-model patch. It accepts a pending candidate for calibration, preserves per-task artifacts,
requires the frozen public initial fingerprint, and leaves semantic-loop labeling for direct
review; it never writes an actor-passed status. B2 and B3 interfaces are also present and
mechanically auditable.

## 7. Verification and remaining blockers

No paid call, actor calibration, or Phase 1A C1/C2/C3 episode was run. Focused no-model tests
cover updated partitions, public applicability, probe-local bookkeeping, source-H freeze hashes
and projection, actor status fail-closed behavior, and the prior registry/pairing/action-index/
leakage invariants.

The focused no-model suites pass 56 tests. The full repository run executes 317 tests with 8
skips and retains 2 unrelated AppWorld fixture errors because this checkout lacks the pinned
playbook and target input-state files; these are not Phase 1 failures.

Exact blockers before Gate B1:

1. researcher review/acceptance of the 10-task in-domain hard-calibration denominator and fixed
   thresholds;
2. an independent paid C1 calibration run using the pending actor candidate;
3. if the candidate passes, freeze a new actor manifest with status `passed...`; otherwise select
   a replacement manifest without using Phase 1A target outcomes;
4. independently freeze the five real B/C-derived source H entries and their artifact provenance;
5. audit C2/C3 context/token distributions, then only consider the pre-registered pilot.

This document makes no claim that the actor is reliable, that real Hs exist, or that C3 improves
over C2.
