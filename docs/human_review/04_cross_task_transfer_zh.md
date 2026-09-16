# Sample E / F：跨任务 transfer 与 Apple action-index sanity

本文件并列两个不同用途的 transfer 样本：SprayBottle 说明 source H 可以在不同 task 上触发一个局部 probe 并继续完成；Apple 是本轮 action-index harness 的固定 3×E0 / 3×E1 sanity check，主要判断 exact action-string transport noise 是否被移除。

## 1. Sample E — P005 → SprayBottle

### Provenance

```text
Artifact provenance: ORIGINAL SAVED ARTIFACT
artifacts/exploratory_memory_mvp/transfer-p005-to-spraybottle-qwen38-20260916/
actor interface: previous exact-string interface (本轮 action-index 改造前)
```

### Source-generated H — Original English

```json
{
  "type": "exploratory",
  "scope": "Future ALFWorld pick-and-place tasks where the target object is not visible in the initial room observation and both closed containers (e.g., cabinets) and open surfaces (e.g., countertops, sinks) are present.",
  "hypothesis": "Prioritizing inspection of open-access surfaces before searching closed containers may reduce the number of 'open' actions required to locate the target object, potentially improving efficiency compared to a cabinet-first heuristic.",
  "guidance": "Upon entering the room, navigate directly to an available open surface (such as a countertop or sink basin) instead of a closed container. Inspect the surface for the target object. If found, take it; if not, proceed to search closed containers.",
  "probe_policy": {
    "local_function": "Initial search strategy selection for hidden objects",
    "realization_pattern": "Surface-first search: Navigate to and inspect open receptacles before attempting to open closed receptacles.",
    "adaptive_policy": "1. Identify all open-access surfaces (countertops, sinks, etc.) from the initial observation. 2. Select one such surface and navigate to it. 3. Check if the target object is visible on this surface. 4. If yes, take the object. 5. If no, revert to the incumbent strategy of searching closed containers sequentially.",
    "evidence_goal": "Determine if the target object is located on an open surface, thereby avoiding the cost of opening multiple closed containers.",
    "stop_conditions": [
      "Target object found on the inspected surface",
      "All open surfaces have been checked without finding the object",
      "Agent reaches a state where only closed containers remain unchecked"
    ]
  }
}
```

### 中文翻译

H 的未来 guidance 是先尝试当前可用的 open surface；如果没有目标，再转向 closed container。它没有把 source 的 `countertop_1` 作为 target 的固定动作，也没有泄漏 target hidden location。该 H 仍是 hypothesis/probe policy，不是 established memory。

### Different target — Original English

```text
task_id: pick_and_place_simple-SprayBottle-None-Toilet-426/trial_T20190908_155225_439006
seed: 42
instruction: put some spraybottle on toilet.

initial observation:
-= Welcome to TextWorld, ALFRED! =-

You are in the middle of a room. Looking quickly around you, you see bathtubbasin_1, countertop_1, drawer_8, drawer_7, drawer_6, drawer_5, drawer_4, drawer_3, drawer_2, drawer_1, garbagecan_1, handtowelholder_1, sinkbasin_1, toilet_1, toiletpaperhanger_1, towelholder_2, and towelholder_1.

Your task is to: put some spraybottle on toilet.
```

Target actor 的公开 entry list 中包含 `go to countertop_1`；source/target scope-match 与 evaluator classification 位于 `transfer_pairs.json` 的 `review_only`，没有进入 actor prompt。

### E0 / E1 compact trace — Actual English actions and statuses

| step | E0 action | E0 status | E1 action | E1 status | 中文说明 |
|---:|---|---|---|---|---|
| 1 | `go to countertop_1` | `NOT_ACTIVE` | `go to countertop_1` | `ACTIVE` | 两个条件都由当前 target observation grounding 到 `countertop_1`。 |
| 2 | `take spraybottle_1 from countertop_1` | `NOT_ACTIVE` | `take spraybottle_1 from countertop_1` | `EVIDENCE_OBTAINED` | E1 在 open surface 找到并拿到目标，公共 evidence 已足以供 A 判断。 |
| 3 | `go to toilet_1` | `NOT_ACTIVE` | `go to toilet_1` | `NOT_ACTIVE` | E1 H runtime 已移除，开始 ordinary continuation。 |
| 4 | `put spraybottle_1 in/on toilet_1` | `NOT_ACTIVE` | `put spraybottle_1 in/on toilet_1` | `NOT_ACTIVE` | 两个任务都完成，`won: true`。 |

### Outcome / interpretation

E0 和 E1 都是 4 steps、都成功；E1 发生了 `ACTIVE → EVIDENCE_OBTAINED → runtime guidance removed → continuation`。由于 E0 自己也选择了完全相同的路线，这支持的是“E1 中 H 可以被激活、产生证据并结束”的 mechanism evidence，不是 H 带来的 incremental performance improvement。

## 2. Sample F — Apple/Microwave action-index sanity

### Fixed setup

```text
source: P005 SoapBottle-417
target: pick_clean_then_place_in_recep-Apple-None-Microwave-14/trial_T20190909_120203_117379
model: qwen3.8-flash
thinking: false
temperature: 0
seed: 42
step cap: 32
H: existing cleaned P005 future H, unchanged across all six runs
```

```text
Artifact provenance: ORIGINAL SAVED ARTIFACT
artifacts/exploratory_memory_mvp/action-index-sanity-20260916-v2/
```

### New actor contract — Original English

```text
Read current_state.admissible_actions in the exact order provided. Choose
exactly one entry by returning its zero-based action_index. Do not rewrite,
paraphrase, or reconstruct the action string. The harness resolves the index
to the exact current environment action and executes only that one action.
```

### 中文翻译

严格按照 `current_state.admissible_actions` 的原有顺序读取，返回某一项的 zero-based `action_index`。不要重写、改述或重构 action string；harness 负责把 index 映射到 exact action 并执行一个动作。

### Entry ordered list — Run 1 Original English

Run 1 的 initial ordered list（index 从 0 开始）是：

```text
0  go to cabinet_1
1  go to cabinet_2
2  go to cabinet_3
3  go to cabinet_4
4  go to cabinet_5
5  go to cabinet_6
6  go to cabinet_7
7  go to cabinet_8
8  go to coffeemachine_1
9  go to countertop_1
10 go to countertop_2
11 go to fridge_1
12 go to garbagecan_1
13 go to microwave_1
14 go to sinkbasin_1
15 go to stoveburner_1
16 go to stoveburner_2
17 go to stoveburner_3
18 go to stoveburner_4
19 go to toaster_1
20 inventory
21 look
```

每一步的完整 ordered list 都被保存；下面同时展示模型返回的 `action_index` 和 harness 的 `resolved exact action`。表中 observation 是 artifact 中实际 environment result 的 task-relevant 英文句子；重复 boilerplate 的完整内容请查 raw step artifact。

### One clean E1 trace — Run 1 actual evidence

| step | `action_index` | resolved exact action | observation / result — Original English | `probe_status` | 中文说明 |
|---:|---:|---|---|---|---|
| 1 | 10 | `go to countertop_2` | `You arrive at loc_21. On countertop_2, you see dishsponge_3, knife_1, mug_3, mug_1, potato_3, saltshaker_1, and spoon_2.` | `ACTIVE` | 第一个 open surface candidate 未发现目标。 |
| 2 | 10 | `go to countertop_1` | `You arrive at loc_15. On countertop_1, you see bowl_1, butterknife_1, cup_2, fork_2, fork_1, knife_2, ladle_2, lettuce_2, lettuce_1, mug_2, pan_1, peppershaker_1, ...` | `ACTIVE` | 另一个 open surface 仍没有 apple。长 observation 见 artifact。 |
| 3 | 14 | `go to sinkbasin_1` | `You arrive at loc_8. On sinkbasin_1, you see nothing.` | `ACTIVE` | 当前 observation 没有目标，actor 继续局部搜索。 |
| 4 | 12 | `go to fridge_1` | `You arrive at loc_2. fridge_1 is closed.` | `ACTIVE` | 从 open-surface 试探转向 closed storage。 |
| 5 | 20 | `inventory` | `You are not carrying anything.` | `ACTIVE` | 这是合法但没有推进的 semantic action。 |
| 6 | 20 | `inventory` | `You are not carrying anything.` | `ACTIVE` | 继续暴露 actor 的语义执行不稳定，但 index 合法。 |
| 20 | 1 | `go to cabinet_1` | `You arrive at loc_4. On cabinet_1, you see nothing.` | `ACTIVE` | 中间步骤 7–19 的完整记录在 step artifacts；这里保留一段实际轨迹。 |
| 21 | 1 | `go to cabinet_2` | `You arrive at loc_14. On cabinet_2, you see dishsponge_1, and peppershaker_1.` | `ACTIVE` | 仍在合法地探索当前 affordance。 |
| 22 | 13 | `go to microwave_1` | `You arrive at loc_10. microwave_1 is closed.` | `ACTIVE` | 再次到达 closed appliance。 |
| 23 | 21 | `look` | `You are facing microwave_1 (is closed). Next to it, you see nothing.` | `ACTIVE` | observation 没有改变，仍是语义控制问题而非字符串复制问题。 |
| 24 | 12 | `go to fridge_1` | `You arrive at loc_2. fridge_1 is closed.` | `ACTIVE` | 返回 closed storage。 |
| 25 | 22 | `open fridge_1` | `You open fridge_1. In fridge_1, you see apple_4, apple_3, bread_1, cup_3, and egg_1.` | `ACTIVE` | 公开观察现在给出可验证的 candidate。 |
| 26 | 23 | `take apple_3 from fridge_1` | `You take apple_3 from fridge_1.` | `EVIDENCE_OBTAINED` | acquisition 产生 probe evidence-ready；H runtime 随后移除。 |
| 27 | 17 | `go to sinkbasin_1` | `You arrive at loc_8. On sinkbasin_1, you see nothing.` | `NOT_ACTIVE` | H 已不再出现在 actor input，开始 downstream cleaning。 |
| 28 | 0 | `clean apple_3 with sinkbasin_1` | `You clean apple_3 using sinkbasin_1.` | `NOT_ACTIVE` | 正常 task continuation。 |
| 29 | 16 | `go to microwave_1` | `You arrive at loc_10. microwave_1 is closed.` | `NOT_ACTIVE` | 继续原 task。 |
| 30 | 24 | `open microwave_1` | `You open microwave_1. In microwave_1, you see apple_1, and potato_2.` | `NOT_ACTIVE` | 当前目标 apple 已在手中，打开 destination。 |
| 31 | 25 | `put apple_3 in/on microwave_1` | `You put apple_3 in/on microwave_1.` | `NOT_ACTIVE` | 任务完成，`won: true`。 |

省略的 7–19 步没有被删除：它们逐步保存在 `run-01/e1_established_plus_source_h/steps/`，其中所有 step 都有 ordered action list、index、resolved action、validation、prompt 和 environment result。

### E0 × 3 / E1 × 3 result table

| run | condition | all indices valid? | won? | steps | H activated? | evidence ready? | H removed? |
|---:|---|---|---|---:|---|---|---|
| 1 | E0 | yes | yes | 15 | n/a | n/a | n/a |
| 2 | E0 | yes | yes | 17 | n/a | n/a | n/a |
| 3 | E0 | yes | yes | 13 | n/a | n/a | n/a |
| 1 | E1 | yes | yes | 31 | yes | yes | yes |
| 2 | E1 | yes | no, step cap | 32 | yes | yes | yes |
| 3 | E1 | yes | no, step cap | 32 | yes | yes | yes |

机械汇总：6 条 runs 共 140 个已执行 action decisions，invalid index 数量为 **0**。每一步的 `resolved_action` 都严格等于该步保存的 `current_admissible_actions[action_index]`。没有发生 exact-string actor output，因此此前 E0 中因错误 object suffix 造成的 exact-action validation failure 在这 3 个 E0 run 中没有再出现。

### Cross-run caveat

虽然每个 run 内 E0/E1 initial public state 都 matched，但同一 nominal `seed: 42` 的不同 run 出现了不同的 ALFWorld layout/object instance：例如 E0 run 1 在 `garbagecan_1` 看到 `apple_2`，E0 run 2/3 在 `microwave_1` 看到 `apple_1`；E1 run 1 在 `fridge_1` 取得 `apple_3`。因此这 6 次不是严格的跨 run deterministic replay。

### Attribution

- action-index harness：在本固定 sanity 中，index transport 完全合法，E0 3/3 完成；这支持 exact-string reproduction 是此前 E0 failure 的一个真实干扰源。
- actor semantic reliability：E1 的 2/3 step-cap failure 发生在所有 index 都合法的情况下，trace 包含重复 `inventory`、跨 receptacle 往返和不稳定的 object choice；不能归因于 index harness。
- H lifecycle：3 个 E1 都曾激活 H、到达 `EVIDENCE_OBTAINED`、移除 runtime guidance；但 E1 任务只有 1/3 完成，所以不能把“产生 evidence-ready status”当作完整 task success。
- method：本 sanity 没有证明 H 相比 E0 更高效，也没有证明整个 persistent-memory method；它只清理了 action-string transport confound，并暴露了剩余 semantic actor control variability。

## 3. Human-review questions

- 当前每个 `action_index` 是否确实按当步 ordered list 解释，而不是跨步复用 index 含义？
- E1 run 1 的 surface → closed storage 转换是否是 H 的合理 adaptive probe，还是模型在长轨迹中自行漂移？
- `EVIDENCE_OBTAINED` 后 H 移除、clean/place continuation 是否符合 one-shot semantics？
- E1 run 2/3 的 failure 是否应当在 broader evaluation 中作为 actor reliability failure 单独统计？
- 同一 nominal seed 产生不同 layout 的问题，是否需要在 paper-level evaluation 中固定可复现 episode state 或记录 reset variance？

## 4. Raw artifact references

```text
artifacts/exploratory_memory_mvp/action-index-sanity-20260916-v2/run-01/
artifacts/exploratory_memory_mvp/action-index-sanity-20260916-v2/run-02/
artifacts/exploratory_memory_mvp/action-index-sanity-20260916-v2/run-03/
```
