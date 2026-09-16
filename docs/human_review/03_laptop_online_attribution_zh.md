# Sample D：Laptop online attribution

## 0. 为什么这个样本重要

P002 → Laptop 是上一轮最清楚的 online failure attribution：同一个 source-generated H、同一个 target、同一个 Qwen actor，在没有机械进度状态时出现 desk/shelf 往返；只加入由真实执行历史机械汇总的 `probe_runtime_state` 后，actor 在 6 步内拿到 Laptop 并完成 placement。

```text
Artifact provenance: ORIGINAL SAVED ARTIFACT
old loop:
artifacts/exploratory_memory_mvp/transfer-p002-to-laptop-qwen38-20260916-v2/
3A corrected diagnostic:
artifacts/exploratory_memory_mvp/laptop-e1-qwen38-runtime-state-original-h-20260916/
```

本样本是上一轮 exact-string actor interface 下保存的 attribution artifact；本轮 action-index 只改变 transport contract，未改变 H 或 `probe_runtime_state` 语义。

## 1. Fixed task / H

### Task — Original English

```text
task_id: pick_and_place_simple-Laptop-None-Desk-306/trial_T20190909_075009_810389
seed: 42
instruction: put some laptop on desk.

initial observation:
-= Welcome to TextWorld, ALFRED! =-

You are in the middle of a room. Looking quickly around you, you see bed_1, desk_1, drawer_5, drawer_4, drawer_3, drawer_2, drawer_1, garbagecan_1, laundryhamper_1, shelf_1, and sidetable_1.

Your task is to: put some laptop on desk.
```

### H — Original JSON excerpt

```json
{
  "type": "exploratory",
  "scope": "Future ALFWorld pick-and-place tasks where the target object is not visible in the initial room observation and multiple receptacles (open surfaces and closed containers) are present.",
  "hypothesis": "Prioritizing inspection of open surfaces (like desks or shelves) before systematically opening closed containers reduces step count without increasing failure rate for common objects like pencils.",
  "guidance": "Navigate to an available open surface first. If the target is not found, proceed to inspect other open surfaces before moving to closed containers.",
  "probe_policy": {
    "local_function": "Search order heuristic: Open Surfaces First vs. Observation Order/Exhaustive Container Search.",
    "realization_pattern": "Identify all visible open surfaces in the current location. Navigate to one such surface. Inspect it. If target absent, repeat for other open surfaces. Only after exhausting open surfaces, begin navigating to and opening closed containers.",
    "adaptive_policy": "At the start state, parse the room description to distinguish between open surfaces (e.g., desk, shelf, bed) and closed containers (e.g., cabinet, drawer). Select an open surface as the first navigation target. Upon arrival, check if the target object is visible. If yes, take it. If no, select another unvisited open surface. If all open surfaces are exhausted without finding the target, switch to the incumbent strategy of visiting and opening closed containers.",
    "stop_conditions": [
      "Target object is located on an open surface.",
      "All open surfaces are inspected and target is not found (fallback to closed containers).",
      "Task completion (object placed on destination)."
    ]
  }
}
```

### 中文翻译

H 要测试的是：先检查当前可见的 open surface，再在没有找到目标时转向 closed containers；它不是“永远去 `desk_1` 或 `shelf_1`”。`desk_1` 等 exact source entity 只属于 source grounding/旧 artifact 的创建证据，不是 future target 的固定指令。

## 2. Old 24-step loop

### Actual executed actions — Original English

```text
1  go to desk_1
2  go to shelf_1
3  go to desk_1
4  go to shelf_1
5  go to desk_1
6  go to shelf_1
7  go to desk_1
8  go to shelf_1
9  go to desk_1
10 go to shelf_1
11 go to desk_1
12 go to shelf_1
13 go to desk_1
14 go to shelf_1
15 go to desk_1
16 go to shelf_1
17 go to desk_1
18 go to shelf_1
19 go to desk_1
20 go to shelf_1
21 go to desk_1
22 go to shelf_1
23 go to desk_1
24 go to shelf_1
```

### Actual observations — Original English excerpts

```text
After go to desk_1:
You arrive at loc_1. On desk_1, you see cellphone_3, desklamp_1, and keychain_1.

After go to shelf_1:
You arrive at loc_11. On shelf_1, you see alarmclock_1, cellphone_2, and creditcard_2.
```

这两条 observation 在 24 步中周期性重复。每一步旧 actor 都返回 `probe_status: ACTIVE`，没有 `probe_runtime_state`；最终 `won: false`、`done: false`，step cap 到达。

### 中文解释

模型确实执行了 H 所说的两个 open-surface candidate，但无法从已发生事实中记录“这两个 candidate 已经测试过”，因而重复同一对位置。这是 actor/interface state representation failure 的可观察表现，不是 evaluator hidden answer。

## 3. Corrected 3A run

### What changed and what stayed fixed

| 项目 | old loop | 3A corrected diagnostic |
|---|---|---|
| H | 相同 original H | 相同 original H |
| target / seed | Laptop target / 42 | Laptop target / 42 |
| model | `qwen3.8-flash`, `thinking=false`, temperature 0 | 相同 |
| step cap | 32 | 32 |
| 新增信息 | 无 `probe_runtime_state` | 只新增执行历史机械汇总：visited receptacle IDs、probe action count |
| prompt change | 旧 actor prompt | 仅提醒使用 factual progress state，避免无环境变化时重复已测试 candidate |
| H lifecycle | 旧 trace 未到 evidence | `active -> consumed`，evidence 后 runtime H 移除 |

### Mechanical state — Original JSON

在第 3 次 action call 前，artifact 中的 `probe_runtime_state` 为：

```json
{
  "visited_receptacles": ["desk_1", "shelf_1"],
  "probe_action_count": 2
}
```

这两个字段来自已经执行的 `go to desk_1`、`go to shelf_1`，没有告诉模型“下一个最佳地点”、没有 oracle location，也没有 semantic evidence conclusion。

### Prompt-critical instruction — Original English

```text
When exploratory_memory distinguishes visited from unvisited candidates, use
probe_runtime_state and executed_action_history as the authoritative factual
record of probe progress. Do not revisit an already-tested candidate unless the
environment has changed in a way that makes revisiting necessary. These fields
record what has happened; they do not choose the next action for you.
```

### 中文翻译

当 exploratory memory 区分已访问和未访问 candidate 时，使用 `probe_runtime_state` 与 `executed_action_history` 作为探针进度的事实记录。除非环境发生使重访必要的变化，否则不要重访已测试 candidate。它们只记录已发生的事实，不替你决定下一步动作。

### Corrected trace — Original English evidence

| step | observation summary | action | `probe_status` | `probe_runtime_state` before call |
|---:|---|---|---|---|
| 1 | `You arrive at loc_1. On desk_1, you see cellphone_3, desklamp_1, and keychain_1.` | `go to desk_1` | `ACTIVE` | `visited_receptacles=[]`, `probe_action_count=0` |
| 2 | `You arrive at loc_11. On shelf_1, you see alarmclock_1, cellphone_2, and creditcard_2.` | `go to shelf_1` | `ACTIVE` | `visited_receptacles=["desk_1"]`, `probe_action_count=1` |
| 3 | `You arrive at loc_10. On bed_1, you see cellphone_1, laptop_2, laptop_1, pillow_1, and teddybear_1.` | `go to bed_1` | `ACTIVE` | `visited_receptacles=["desk_1","shelf_1"]`, `probe_action_count=2` |
| 4 | `You take laptop_1 from bed_1.` | `take laptop_1 from bed_1` | `EVIDENCE_OBTAINED` | `visited_receptacles=["desk_1","shelf_1","bed_1"]`, `probe_action_count=3` |
| 5 | `You arrive at loc_1. On desk_1, you see cellphone_3, desklamp_1, and keychain_1.` | `go to desk_1` | `NOT_ACTIVE` | `visited_receptacles=["desk_1","shelf_1","bed_1"]`, `probe_action_count=4` |
| 6 | `You put laptop_1 in/on desk_1.` | `put laptop_1 in/on desk_1` | `NOT_ACTIVE` | `visited_receptacles=["desk_1","shelf_1","bed_1"]`, `probe_action_count=4` |

### 中文解释

第 3 步选择新的 `bed_1`，第 4 步获得 Laptop 的公共证据；之后 `EVIDENCE_OBTAINED` 被解释为 `PROBE_EVIDENCE_READY`，runtime H 消失，actor 继续原任务并在第 6 步完成 placement。最终 `won: true`，`actor_steps: 6`。

## 4. Attribution judgment

这是一项“同 H、只加机械进度事实”的诊断。loop 消失而不需要 3B stronger actor，因此当前最强解释是旧接口无法让 Qwen 看到已测试 candidate 的公共进度，而不是 H 必然无法执行，也不是 B 问题。它并不证明 H 在语义上最优，也不证明 Qwen 在所有 target 上可靠。

## 5. Human-review questions

- `visited_receptacles` 是否确实只是执行历史的机械摘要？
- 第 3 步从 desk/shelf 转到 bed 是否是 H 的合理 adaptive realization，而非 prompt 直接指定？
- `EVIDENCE_OBTAINED` 的时机是否有足够公共证据？
- H 移除后第 5–6 步是否是自然 downstream continuation？
- 这个 attribution 是否需要控制 ALFWorld reset 的跨运行随机变化？

## 6. Raw artifact references

```text
old loop:
artifacts/exploratory_memory_mvp/transfer-p002-to-laptop-qwen38-20260916-v2/e1_established_plus_source_h/execution.json
artifacts/exploratory_memory_mvp/transfer-p002-to-laptop-qwen38-20260916-v2/e1_established_plus_source_h/steps/
artifacts/exploratory_memory_mvp/transfer-p002-to-laptop-qwen38-20260916-v2/target_h_actor_view.json

corrected 3A:
artifacts/exploratory_memory_mvp/laptop-e1-qwen38-runtime-state-original-h-20260916/diagnostic_metadata.json
artifacts/exploratory_memory_mvp/laptop-e1-qwen38-runtime-state-original-h-20260916/diagnostic_result.json
artifacts/exploratory_memory_mvp/laptop-e1-qwen38-runtime-state-original-h-20260916/e1_established_plus_original_h/execution.json
artifacts/exploratory_memory_mvp/laptop-e1-qwen38-runtime-state-original-h-20260916/e1_established_plus_original_h/steps/
```
