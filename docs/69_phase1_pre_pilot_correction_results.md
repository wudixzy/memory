# 69. Phase 1 Pre-Pilot Correction Results

> 状态：协议修正与无模型 dry-run 完成；未执行 actor reliability screen，未执行任何付费模型调用。
> 分支：`exp/minimal-exploratory-memory-validation`
> 阶段：Phase 1A — Receptacle-Search Targeting Pilot readiness

## 1. 修正范围

本轮只修正 Phase 1 的可审计性，不改变 B/C/H/A、Functional Contract、action-index、
`probe_runtime_state`、H lifecycle、E1-only A 或 actual-execution pairing proof。主要结果是：

```text
pinned split
  -> public reset records
  -> complete eligible universe
  -> deterministic Source/in-domain Calibration/diagnostic Calibration/Target partition
  -> registry-bound target execution
```

C3 真实 H 仍然没有生成；默认 source-H manifest 是空的 schema-only manifest，科学 runner
在没有注册 H 时 fail closed。

## 2. Complete public universe and partitions

实现：

```text
experiments/exploratory_memory_mvp/phase1_population.py
experiments/exploratory_memory_mvp/build_phase1_registry.py
experiments/exploratory_memory_mvp/cases/phase1_source_tasks.json
experiments/exploratory_memory_mvp/cases/phase1_registered_targets.json
```

`build_public_eligible_universe()` 枚举 pinned ALFWorld `train` split 的 54 个
task/trial 目录，并对每个实例使用 requested seed 42 取得 actor-visible initial
observation 和 ordered admissible actions。eligible predicate 只检查公开 task family、
public instruction、public observation、public action set 和 public affordance structure；
没有读取 hidden placement、expert plan、condition outcome 或 evaluator label。

当前 frozen counts：

| partition | count | role |
|---|---:|---|
| Source | 5 | frozen source reservation |
| Hard calibration | 10 | in-domain C1 actor gate |
| Diagnostic calibration | 18 | out-of-domain stress only; never admission |
| Target | 20 | Phase 1A target pool |
| Residual excluded | 1 | public hash quota outside target/calibration partitions |
| eligible universe | 54 | complete public registry coverage |

五组 partition 两两不交并覆盖全部 54 条 eligible records。选择使用固定 salt
`phase1a-public-universe-partition-v1`，target reservation 保持原有 public-only hash
protocol；随后从剩余四个 Phase 1A task families 中抽取 hard calibration，并把剩余
out-of-domain candidates 作为 diagnostic calibration。没有根据任何运行结果重采样。

冻结 digests：

```text
candidate IDs:  6f12d1a1e26a9a5d5b95567a1b0900d08cce8b39d745939a8332b39b35cdb283
public records: f0c2157f2a78bccc2a36750b696866c6f87a2fb570a3a6bc89f7bb5cc438ecf3
partitions:     fc548e0f4f493074ed2bc20b05433b6d7a94602e8c77a694cc745030037b120f
registry:       0e43d9846ad96249ef1b421b02585a0fff1190e76eb6156b64e64da6c805588d
source set:     a6c9d990b60d8563ba83baadd7845e1a8df440c8c371a15aadb62253860bf55d
applicability contract: 71d982a25ab3d9b7da40b71e1f3900e39fcd0f59ddd40e551b040c38d4499d82
```

Target records all belong to the pre-registered public scope `h_family_receptacle_search`.
这只是一个 semantic comparison family，不是 5–8-family generality experiment。

## 3. Registry-bound execution invariant

`phase1_runner.run_phase1_paired_target()` 现在在创建 scientific episodes 前 fail closed：

1. load and validate the frozen registry;
2. recompute registry SHA-256 and compare the caller-provided frozen digest;
3. require the requested target to be in `partitions.target`;
4. require the requested seed to equal the registered seed;
5. instantiate the actual target episode;
6. recompute its actor-visible initial fingerprint;
7. compare it with the registered fingerprint;
8. verify the target against the public Phase 1A applicability contract;
9. load and verify the source-H manifest, source-set/K*/artifact provenance contract and
   resolve a same-family deterministic H assignment;
10. only then construct C1/C2/C3 and retain the existing actual pairing proof.

The root artifact keeps registry verification, H assignment and source-only H provenance. None
of these artifacts is passed into actor prompts. Tests cover wrong registry digest, unregistered
target, seed mismatch, public fingerprint mismatch, unregistered H, wrong H family and mutated
H content with a stale digest.

## 4. Source-H manifest

`experiments/exploratory_memory_mvp/h_manifest.py` validates the committed
`cases/phase1_source_h_manifest.json` schema. Each future live entry must carry:

```text
h_id
h_family_id
applicability_contract_id
source_task_id / source_task_seed
source_history_identity / source_history_sha256
k_star_sha256
b_artifact_sha256 / c_artifact_sha256
future_h_sha256 / future_h
offline_model_config
creation_version
```

The current manifest has zero entries and status `schema_only_no_live_b_c_artifacts`; this is
intentional because this correction cycle makes no B/C paid calls. `h_assignment.py` provides a
stable target-to-H assignment among registered same-family entries using a public target ID and
frozen salt only. It is tested with fake registered entries and does not inspect target outcomes.

`h_manifest.py` now provides `freeze_source_h_entry()` and
`validate_frozen_h_entry_artifacts()`. The freeze path computes file hashes itself, requires
the source history to identify the frozen source task/seed, projects `future_h` from the
validated C result, checks canonical K*, and rejects stale/mutated source/B/C artifacts. It
does not accept manually claimed SHA strings as evidence. B/C freeze envelopes must embed the
same normalized offline model configuration; a separate claimed configuration is not accepted
as provenance. The standalone Source reservation must exactly match the registry Source
partition. `future_h` is the only part eligible for actor context; source IDs, history hashes and
B/C artifact provenance remain model-invisible. The committed manifest remains empty in this
no-model cycle.

## 5. Actor manifest and probe budget

`cases/phase1_actor_manifest.json` replaces Qwen3.8-Flash as a code-level invariant with a
config-level frozen manifest. It currently records:

```text
provider: dashscope
model: qwen3.8-flash
thinking: false
temperature: 0
step_cap: 32
actor_prompt_version: actor_action_index_probe_runtime_v1
selection_status: candidate_pending_independent_reliability_gate
```

The model is therefore still the current planning candidate, not a passed actor gate. The
DashScope client now accepts the manifest's model/config values, and condition parity rejects
condition-specific drift.

C2/C3 share the frozen mechanical probe budget:

```text
max_probe_actions = 4
max_distinct_candidate_visits = 2
```

Probe-budget digest: `6513813712b26a474ebce8cbfcc49b8544d7681cc004cabfc3b0b24be034184e`.
It is stored and hashed in all condition configs. `max_probe_actions` is the only hard
termination cap. Distinct candidate visits are telemetry only, and cannot remove H. The
stepwise runner now records both `episode_visited_receptacles` and probe-local
`probe_visited_receptacles`; pre-H navigation cannot consume probe-local telemetry.

## 6. Context/token audit

`experiments/exploratory_memory_mvp/phase1_context_audit.py` reads saved actor inputs/prompts
without invoking an environment or model and reports per-condition H characters/tokens,
first-step context characters/tokens, prompt characters/tokens, and distributions. It can be
run as a no-model command with repeated `--artifact CONDITION=PATH` arguments. It reports exact
token counts only when the caller supplies a tokenizer; otherwise it explicitly declines an exact
parity claim. No C2/C3 text was changed from target outcomes in this cycle.

## 7. Reliability gate and scientific scope

The next paid gate is **Actor + K* = C1** on the disjoint 10-task hard-calibration partition.
C0 can be an auxiliary diagnostic, but is not sufficient as the main gate. The proposed
pre-run gate is:

```text
invalid action index = 0
at least 8/10 in-domain C1 tasks successful
at most 2/10 step-cap failures
at most 2/10 clear semantic-loop tasks
```

These thresholds were not tuned against target outcomes and were not executed here.

The next experiment is explicitly **Phase 1A — Receptacle-Search Targeting Pilot**. The allowed
claim is only whether history-derived targeting adds value over fair structured generic
exploration for this pre-registered receptacle-search family. It must not be reported as general
exploratory-memory superiority.

## 8. Verification status

No model/API call was made. ALFWorld public reset collection used the local pinned carrier only;
the fake runner used no-network transports. Focused tests cover registry/partition stability,
runner fail-closed checks, source-H provenance isolation, actor-manifest parity, shared probe
budget, assignment stability, context audit, action-index and existing pairing/lifecycle
invariants. The focused suites passed (9 final pre-actor tests, 12 pre-pilot tests, 14 Phase 1
readiness tests, and 21 existing MVP tests; 56 tests total).

The full repository suite completed 317 tests with 8 skips and 2 unrelated errors because this
checkout lacks the AppWorld playbook and target input-state fixtures
(`third_party/ace-appworld/...`). This correction does not claim that the paid Phase 1 pilot is
ready to run until the researcher reviews the registry, creates valid B/C-derived H entries,
audits C2/C3 context budgets, and runs the independent C1 actor gate. The current actor
manifest remains `candidate_pending_independent_reliability_gate`; the scientific runner now
fails closed on that status.
