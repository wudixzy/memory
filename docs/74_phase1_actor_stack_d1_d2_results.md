# Phase 1A Actor-Stack Development Diagnostic: D1/D2 Results

更新时间：2026-09-20
分支：`exp/minimal-exploratory-memory-validation`
本轮性质：development diagnostic，非 independent actor admission

本轮在 no-model transition commit `bd72f86944a21f951f0f9a2173a6f8225e7cf5b8` 后，按
`docs/73_phase1_actor_stack_development_diagnostic_plan.md` 运行了两次完整的开发诊断：

```text
D1 = Qwen3.8-Flash + current actor prompt + K* candidate v2 + actions_only history
D2 = 同一配置 + raw action -> resulting public observation history
```

两次都使用原 Gate B1 的 10 个 task，各执行一次；没有 task-level retry。原 Gate B1 的
`4/10` FAIL 结果和 D0 artifacts 未被覆盖。D1/D2 的结果不能用于宣称 Gate B1 通过，也
不能用于选择 Phase 1A target。

## 1. Transition and frozen inputs

| 项目 | 值 |
|---|---|
| transition commit | `bd72f86944a21f951f0f9a2173a6f8225e7cf5b8` |
| D1/D2 execution HEAD | `bd72f86944a21f951f0f9a2173a6f8225e7cf5b8` |
| actor | DashScope-compatible `qwen3.8-flash` |
| thinking / temperature | `false / 0.0` |
| step cap | `32` |
| action interface | zero-based `action_index` |
| actor selection status | `candidate_pending_independent_reliability_gate` |
| D1/D2 task partition | existing `hard_calibration`, 10 tasks, now development-only |
| calibration registry SHA | `87605dd5bd9810ee8c9e7867e8e176d60034c6969babff58fbb81b73e5a4e120` |
| canonical actor prompt | unchanged |
| canonical K* | unchanged and not promoted |
| transport | direct DashScope path; no proxy transport |

The committed development candidate is:

```text
experiments/exploratory_memory_mvp/cases/phase1_k_star_candidate_v2.json
candidate_version = phase1-k-star-candidate-v2
status = development_candidate
entries digest = e248e8a8604d8f64bde8f849986c08660d019281e35c9f6399d2d36ec529f80f
file SHA-256 = 49646f1e20212bfd0bdfbc6a6a2b6dda8181a9421d5e224d78c0448a00bbab7c
```

它仍是手工的 feasibility-only warm-start control fixture。generic search 只负责找到
并取得 requested object，取得后交给 task-required downstream routine；clean/heat/cool
分别使用 carrier 暴露的直接操作形式，例如 `clean <object> with <sinkbasin>`、
`heat <object> with <microwave>`、`cool <object> with <fridge>`。没有加入 development
case 的 entity ID、hidden placement、oracle outcome、比较优胜标签或 case-specific
if/then rule。它没有替换 `k_star.py` 中的 canonical K*。

## 2. Fresh Gate B1-R public-only reservation

这一步在 D1/D2 model calls 之前完成，且没有创建 model client。

本地 pinned data 没有 `valid_seen` 目录，因此按预先声明的 split priority 使用
`valid_unseen`：

```text
split: valid_unseen
full public-eligible universe: 135 task/trial records
Phase 1A in-domain public records: 100
reservation: 12 tasks = 3 per family
reservation digest: 0b8874ae03912bd7190e634dd6d54fccb2bc9a19eb26d0b9b7bad51c05885cfe
```

完整 public census、每条入口 observation、ordered initial admissible actions、public
affordance structure、selection protocol 和 digest 保存在：

```text
experiments/exploratory_memory_mvp/cases/phase1_b1r_reservation.json
```

预留 family 数量为：

| family | public eligible | reserved |
|---|---:|---:|
| `pick_and_place_simple` | 24 | 3 |
| `pick_clean_then_place_in_recep` | 31 | 3 |
| `pick_cool_then_place_in_recep` | 22 | 3 |
| `pick_heat_then_place_in_recep` | 23 | 3 |

选择算法是固定 salt 下的 stable public hash。代码显式拒绝与 frozen Source、旧
10-task development partition 或 Phase 1A Target partition 的重叠；本次选择来自
`valid_unseen`，因此也没有借用原 train target 20。没有读取 PDDL placement、expert
route、outcome 或 D1/D2 result。B1-R 只完成了 reservation，**本轮没有执行它**。

## 3. Diagnostic history interface

D1 actor input 在每一步继续包含：

```text
current_task
current_state
pre_update_established_memories
executed_action_history
probe_runtime_state
```

D2 在相同字段之外只增加：

```json
"action_observation_history": [
  {"action": "...", "observation": "..."}
]
```

每一项是环境刚刚返回的 raw public observation；没有加入 `current_phase`、
`SEARCH`、`OBJECT_ACQUIRED`、visited-empty summary、next-action recommendation、
planner state 或 heuristic action filtering。`executed_action_history`、
`probe_runtime_state`、action-index validation、H lifecycle 和 actor prompt system text
保持不变。D1 input 中没有 `action_observation_history`；D2 的 step 2 起该字段与已执行
action 一一对应。

## 4. Exact trajectory artifacts and retention

完整 ignored runtime artifacts 仍保留在本地，没有提交 Git，也没有删除或用 aggregate
替换：

```text
D1 root:
artifacts/exploratory_memory_mvp/actor-stack-dev-d1-20260920-bd72f86/
D1 manifest:
artifacts/exploratory_memory_mvp/actor-stack-dev-d1-20260920-bd72f86/trajectory_manifest.json

D2 root:
artifacts/exploratory_memory_mvp/actor-stack-dev-d2-20260920-bd72f86/
D2 manifest:
artifacts/exploratory_memory_mvp/actor-stack-dev-d2-20260920-bd72f86/trajectory_manifest.json
```

每个 root 都有 10 个 task artifact。D1 保存 240 个 step 目录，D2 保存 255 个 step
目录；每个 step 均保留 actor input/prompt/raw response/parsed result、ordered
admissible actions、index/resolved action/validation、environment result、step record
和 usage。每个 task 还保留 initial state、run config、execution、episode summary、
model events 和 failure/error artifact（若有）。D2 的 CoffeeMachine task 的 invalid
index failure 也保留了完整的失败 step artifact。

为方便协作者直接在 GitHub 上检查关键逐步证据，本次另外提交了四个 task 在 D0/D1/D2
中的完整 task artifact（共 12 条完整轨迹），而不是提交所有 30 个 task：

```text
docs/human_review/trajectory_artifacts/phase1_actor_stack_core/
```

该 tracked subset 选择了 Laptop 的跨变体成功控制、Shelf cool 的持续失败、
CoffeeMachine 的 D1 成功/D2 invalid-index 对照，以及 SoapBar 的 D0 成功到 D1/D2
回归。每个选中 task 目录完整保留 initial state、每一步 actor input/prompt/response、
admissible actions、action index/resolved action、环境结果、execution、usage 和失败
artifact；目录内的 variant metadata/manifest 也一并保留。它们均标记为
`ORIGINAL SAVED ARTIFACT`，不是重建或重跑结果。完整 10-task roots 仍按 artifact policy
保留在本地 ignored 路径中。

## 5. Per-task mechanical results

下表的 D0 是原 Gate B1 结果，仅作为历史 control；D1/D2 是本轮同一 10-task development
set 的新运行。`cap` 表示达到 32-step cap，`invalid` 是机械 action-index validation
失败。

| task | family | D0 | D1 | D2 |
|---|---|---|---|---|
| `Laptop-None-Desk-306` | simple | win, 11 | win, 6 | win, 5 |
| `Knife-None-DiningTable-26` | clean | cap, 32 | cap, 32 | cap, 32 |
| `Mug-None-Shelf-1` | cool | cap, 32 | cap, 32 | cap, 32 |
| `Apple-None-Fridge-20` | heat | win, 25 | win, 23 | win, 24 |
| `Potato-None-CounterTop-15` | heat | cap, 32 | cap, 32 | cap, 32 |
| `Mug-None-CoffeeMachine-30` | cool | cap, 32 | **win, 9** | invalid, 17 |
| `SoapBar-None-Cabinet-428` | clean | win, 13 | cap, 32 | cap, 32 |
| `DishSponge-None-Cart-430` | clean | win, 21 | win, 10 | win, 16 |
| `Cup-None-Shelf-20` | clean | cap, 32 | cap, 32 | cap, 32 |
| `Potato-None-Fridge-27` | heat | cap, 32 | cap, 32 | cap, 32 |

完整 task IDs、seed、fingerprint 和 relative artifact paths 在两个
`trajectory_manifest.json` 中，避免在此表中截断 trial identity。

## 6. D1/D2 aggregate telemetry

| metric | D0 historical | D1 | D2 |
|---|---:|---:|---:|
| successful tasks | 4 / 10 | 4 / 10 | 3 / 10 |
| step-cap tasks | 6 / 10 | 6 / 10 | 6 / 10 |
| invalid action-index steps | 0 | 0 | 1 |
| infrastructure failures | 0 | 0 | 0 |
| actor model calls | 262 | 240 | 255 |
| input tokens | 414,651 | 373,768 | 555,470 |
| output tokens | 4,060 | 3,719 | 4,024 |
| cached input tokens | 80,896 | 72,704 | 130,688 |
| known estimated cost | 0.2312272 CNY* | 0.2118731 CNY* | 0.2000140 CNY* |

\* Cached-input pricing is not fully available in the saved DashScope telemetry. D1 has
169 cost-known generation records and D2 has 135; the displayed values are known uncached
estimates, not complete provider billing. No exact total cost is claimed.

Family-level successes：

| family | D0 | D1 | D2 |
|---|---:|---:|---:|
| simple | 1 / 1 | 1 / 1 | 1 / 1 |
| clean | 2 / 4 | 1 / 4 | 1 / 4 |
| cool | 0 / 2 | 1 / 2 | 0 / 2 |
| heat | 1 / 3 | 1 / 3 | 1 / 3 |

这些只是 development mechanics，不是 reliability admission。D1 恢复了
`Mug-None-CoffeeMachine-30` 的一次成功，但同时 `SoapBar-None-Cabinet-428` 从 D0
成功变为 cap；D2 在相同 K* v2 上没有保留该 CoffeeMachine 成功，并出现一个
out-of-range `action_index`。这些差异需要逐轨迹人工 review，不能仅从 aggregate 归因
为 observation history 的因果效果。

## 7. Negative evidence and review boundary

本轮保留的负面证据包括：

* D1 仍有 6 个 step-cap，D2 仍有 6 个 step-cap；
* D2 有一个明确的 invalid action-index artifact；
* D1/D2 都没有解决 Shelf cool case；
* D1/D2 都没有使旧 10-task set 达到独立 actor gate 的意义；
* raw observation history 增加了 D2 context，且 D2 token input 高于 D1；这不是自动的
  “更好”或“更坏”结论。

本轮没有生成 failure classifier，也没有把 failure 自动标成 model failure、interface
failure 或 method failure。研究者下一步应直接比较 D0→D1 的 K*/carrier contract 变化，
以及 D1→D2 的 raw public interaction evidence 是否实际减少空 receptacle 重访、
`inventory`/`look` 停滞和 object grounding drift。

## 8. Explicit scope and stop condition

以下结论仍然禁止：

```text
D1/D2 pass independent Gate B1
Qwen3.8-Flash is intrinsically incapable
C3 > C2
H or persistent memory is effective
native cold-start initialization is validated
Phase 1A target matrix is ready to run
```

本轮没有运行：

```text
fresh Gate B1-R execution
diagnostic calibration partition
B2 live B/C or source-H freeze
B3 C2/C3 context audit
Phase 1A Target 20
second actor
Stage 1, retrieval, or longitudinal memory
```

当前 actor manifest 仍为：

```text
selection_status = candidate_pending_independent_reliability_gate
```

当前 K* v2 仍为 development candidate，没有 promote 为 canonical。下一步必须先由
researcher review D0/D1/D2 raw trajectories，再决定是否接受 K* v2/raw history interface、
是否需要另一个小型 controlled test，以及何时执行 fresh independent Gate B1-R。
