# Action-index harness 与中文人工 Review 结果

> Date: 2026-09-16
> Branch: `exp/minimal-exploratory-memory-validation`
> Carrier: ALFWorld TextWorld
> Model: `qwen3.8-flash`, `thinking=false`, `temperature=0`
> Transport: DashScope direct/no-proxy

本轮只做两个事情：把 actor 的 exact action-string 输出替换为当前有序
`admissible_actions` 的 zero-based `action_index`，以及从已有真实 artifacts 生成中文双语人工 review 包。B/C/H/A 的科学语义没有重新设计。

## 1. Action-index 实现

actor 现在每次返回：

```json
{
  "action_index": 7,
  "probe_status": "ACTIVE"
}
```

runner 保存当步完整有序 `current_state.admissible_actions`，并机械执行：

```python
resolved_action = current_state["admissible_actions"][action_index]
```

`action_index` 必须是严格的 Python `int`；`bool`、其他类型、负数和越界值都会被拒绝，不会自动修复。每个 step artifact 现在同时保存：

```text
current_admissible_actions
action_index
resolved_action
action_validation
probe_status
environment_result
```

新增的 `validate_action_index` 只负责索引解析和审计，不决定语义上的“最佳动作”。invalid index 的 `step.json`、`action_validation.json` 与 `error.json` 仍会保存。

## 2. Apple sanity run

固定 setup：

```text
source: P005 SoapBottle-417
target: pick_clean_then_place_in_recep-Apple-None-Microwave-14/
        trial_T20190909_120203_117379
seed: 42
step cap: 32
H: unchanged cleaned P005 H
```

本轮完成 `E0 × 3` 和 `E1 × 3`，没有在六次运行之间修改 prompt、case、H 或 step cap。

| run | condition | indices all valid? | won? | steps | H activated? | evidence ready? | H removed? |
|---:|---|---|---|---:|---|---|---|
| 1 | E0 | yes | yes | 15 | n/a | n/a | n/a |
| 2 | E0 | yes | yes | 17 | n/a | n/a | n/a |
| 3 | E0 | yes | yes | 13 | n/a | n/a | n/a |
| 1 | E1 | yes | yes | 31 | yes | yes | yes |
| 2 | E1 | yes | no, step cap | 32 | yes | yes | yes |
| 3 | E1 | yes | no, step cap | 32 | yes | yes | yes |

6 条 run 合计 140 个已执行 actor decision，invalid index 数量为 **0**；每个合法 step 的 `resolved_action` 都等于同一步的 `current_admissible_actions[action_index]`。因此本 sanity 中 exact-string action validation failure 没有再出现，E0 为 3/3 完成。

但这不是 H 的性能胜出结果：E1 只有 1/3 完成，另外两次在所有 index 合法的情况下到达 step cap。失败 trace 中仍有重复 `inventory`、跨 receptacle 往返和语义上的不稳定选择。因此，action-index 清除了 exact-string transport confound，但没有消除 actor 的 semantic/reasoning reliability 问题，也不能据此声称 H 或完整 persistent-memory method 有效。

每个 run 内 E0/E1 初始公共状态均 matched；不过不同 run 的同一 nominal seed 出现了不同 ALFWorld layout/object instance。因此这 6 次适合作为 harness sanity，而不是严格 deterministic replay 或性能比较。完整逐步 index/action 对照见：

```text
artifacts/exploratory_memory_mvp/action-index-sanity-20260916-v2/
```

## 3. 中文人工 Review 包

新增目录：

```text
docs/human_review/
├── README_zh.md
├── 01_b_open_and_controls_zh.md
├── 02_c_and_h_zh.md
├── 03_laptop_online_attribution_zh.md
├── 04_cross_task_transfer_zh.md
└── 05_a_reconciliation_zh.md
```

包含的代表性样本：

| Sample | 内容 | provenance |
|---|---|---|
| A/B | P005 B=`OPEN`、N1 B=`NONE` 控制 | `ORIGINAL SAVED ARTIFACT` |
| C | fact-only local C packet、capability、C 输出与 future H | `ORIGINAL SAVED ARTIFACT` |
| D | Laptop 旧 24-step loop 与同 H 的机械 `probe_runtime_state` 诊断 | `ORIGINAL SAVED ARTIFACT` |
| E | P005 → SprayBottle 不同任务 transfer、E0/E1、E1-only A | `ORIGINAL SAVED ARTIFACT` |
| F | Apple action-index 的 E0×3/E1×3 与代表性 E1 trace | `ORIGINAL SAVED ARTIFACT` |
| G | Laptop `NO_CHANGE` 与 SprayBottle `UPDATE / REFINE` 的 E1-only A | `ORIGINAL SAVED ARTIFACT` |

所有样本均直接引用当前机器已有 runtime artifact，没有为了挑选漂亮结果而重跑旧样本；本轮没有 `RECONSTRUCTED REPRODUCTION`。文档保留重要英文 prompt/model output，并紧跟中文翻译；action string、entity ID、JSON key、model name 和 artifact path 保持原样。长 observation 的完整版本仍由对应 artifact path 查阅。

## 4. 归因结论

| issue | implementation/interface evidence | model evidence | method evidence | current judgment |
|---|---|---|---|---|
| exact action-string failure | 新 harness 在 140/140 个 decision 上合法解析并精确映射；invalid artifacts 有保存测试 | 不适用 | action selection 语义未改变 | 原 exact-string failure 已被接口层清除 |
| E0 基础执行 | E0 3/3 完成，且没有 invalid index | 同一模型仍有 13/15/17 steps 的路径差异 | 不说明 H | actor 能在这些 episode 完成，但存在执行方差 |
| E1 长轨迹失败 | index、resolved action、当前 admissibility 均合法 | E1 2/3 在 step cap 前未完成，trace 有重复/漂移 | 不能归因于 B 或 action transport；H 的长程 authority/actor control 仍未充分证明 | 当前主要是 model semantic execution / online control reliability，method attribution 仍不确定 |
| Laptop 旧 loop | 加入机械 visited/count 后同 H 从 24-step loop 变为 6-step completion | Qwen 在更清楚的事实状态下成功选择未访问 candidate | 支持 probe runtime-state 表示对局部控制有帮助 | 旧 Laptop failure 更像 interface/state representation bottleneck |
| H/A 科学机制 | SprayBottle 中 H activation、evidence-ready、移除和 continuation 可观察；A 只收到 E1 | A 的 `NO_CHANGE` 与 `REFINE` 均保留部分 unresolved | 仍只有少量 qualitative mechanism evidence，不能推出总体效果 | 可进入 paper-level evaluation design；不要继续用 ad-hoc planner 修补 MVP |

## 5. Recommendation

action-index sanity 已达到本轮目的：exact action-string harness 不再是主要失败面。建议结束这条 mechanism debugging 支线，转入 paper-level evaluation design 讨论，并在正式评估中单独记录：

- actor 的 semantic execution reliability 与 step-cap failure；
- H 是否真正改变局部行为，而非只报告 H 被看见；
- probe evidence-ready、runtime H removal 和 downstream continuation；
- 固定可复现 episode state，或明确报告 ALFWorld reset variance；
- A 是否仅用实际 E1 evidence、是否过度泛化。

当前结果支持的是“action-index 能机械地移除 exact-string reproduction confound”和“在少量受控样本中可以审查 B/C/H/Online/A 的信息边界与生命周期”。它不支持“探索性记忆整体提升任务成功率”，也不支持完整 persistent-memory closed loop 已经成立。
