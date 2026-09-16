# Sample G：A reconciliation 的 evidence-bound review

## 0. 为什么这个样本重要

A 是 deployed online updater 的边界：它只能读取 pre-update established memory、已经 consumed 的 H、实际 E1 target episode 和公共环境结果。它不能看到 researcher 用来做 E0/E1 比较的 E0 outcome，也不能看到 target hidden location、transfer class 或 expected conclusion。

```text
Artifact provenance: ORIGINAL SAVED ARTIFACT
artifacts/exploratory_memory_mvp/clean-a-e1-only-20260916/
```

这里使用一个 `NO_CHANGE`（Laptop）和一个 `UPDATE / REFINE`（SprayBottle），方便人工检查“保守”与“可更新”两种边界。

## 1. A prompt-critical instructions

### Original English

```text
The input contains the pre-update established memory, one consumed exploratory
memory H, an actual E1 target public trajectory, an actual local probe trace,
the actual E1 execution outcome, and provenance. It does not contain E0 or any
other counterfactual baseline, evaluator labels, oracle answers, or a
researcher-written expected conclusion.

EVIDENCE_OBTAINED means only that the probe produced enough observations for you
to judge; it does not establish that H is true or globally superior.

Use NO_CHANGE with an empty updates list when one episode is insufficient to
change established memory. If you update, bind every claim to the target trace
and keep its scope explicit. One positive case must not become an always-
optimal or universal claim. One negative probe must not falsify an entire
hypothesis family.
```

### 中文翻译

输入包含 pre-update established memory、一个已 consumed 的 H、实际 E1 target public trajectory、实际 local probe trace、实际 E1 execution outcome 和 provenance；不包含 E0 或任何其他 counterfactual baseline、evaluator label、oracle answer、researcher expected conclusion。

`EVIDENCE_OBTAINED` 只表示 probe 已产生足够观察供判断，不表示 H 为真或全局更优。一个 episode 不足以改变 established memory 时应使用空 updates 的 `NO_CHANGE`；如果更新，所有 claim 都必须绑定 target trace 并保持 scope 明确。单个 positive case 不能变成 universal optimum，单个 negative probe 不能否定整个 hypothesis family。

## 2. NO_CHANGE example — Laptop

### What A actually saw — Original JSON excerpt

```json
{
  "target_task": {
    "task_id": "pick_and_place_simple-Laptop-None-Desk-306/trial_T20190909_075009_810389",
    "seed": 42,
    "instruction": "put some laptop on desk."
  },
  "probe_evidence": {
    "condition": "E1",
    "probe_status_history": [
      "ACTIVE", "ACTIVE", "ACTIVE", "ACTIVE", "ACTIVE", "ACTIVE",
      "ACTIVE", "ACTIVE", "ACTIVE", "ACTIVE", "ACTIVE", "ACTIVE",
      "ACTIVE", "ACTIVE", "ACTIVE", "ACTIVE", "ACTIVE", "ACTIVE",
      "ACTIVE", "ACTIVE", "ACTIVE", "ACTIVE", "ACTIVE", "ACTIVE"
    ],
    "probe_steps": "the actual E1 step records"
  },
  "environment_outcome": {
    "e1": {
      "executed_steps": 24,
      "executed_actions": [
        "go to desk_1", "go to shelf_1", "go to desk_1", "go to shelf_1",
        "go to desk_1", "go to shelf_1", "go to desk_1", "go to shelf_1",
        "go to desk_1", "go to shelf_1", "go to desk_1", "go to shelf_1",
        "go to desk_1", "go to shelf_1", "go to desk_1", "go to shelf_1",
        "go to desk_1", "go to shelf_1", "go to desk_1", "go to shelf_1",
        "go to desk_1", "go to shelf_1", "go to desk_1", "go to shelf_1"
      ],
      "completed_requested_sequence": false,
      "won": false,
      "reward": 0.0
    }
  },
  "provenance": [
    "source_c:alfworld-p-002-pencil",
    "target_task:pick_and_place_simple-Laptop-None-Desk-306/trial_T20190909_075009_810389",
    "target_pair:stepwise_e0_e1"
  ]
}
```

### 中文翻译与边界说明

A 看到的是 E1 中 24 步 desk/shelf 往返、没有完成 task 的事实。`environment_outcome` 顶层只有 `e1`；E0 成功的 16 steps 或 E0 failure 都没有进入此输入。A 也看到了 consumed H 的内容和 probe trace，但这些不是“再次激活 H”的命令。

### Exact A output — Original JSON

```json
{
  "decision": "NO_CHANGE",
  "still_unresolved": [
    "The 'Open Surfaces First' heuristic failed to locate the target (laptop) in this specific instance, but did not falsify the hypothesis for all object types or environments.",
    "Whether prioritizing open surfaces reduces step count compared to the established exhaustive search when the target is actually on an open surface.",
    "The impact of navigation loops (oscillating between desk and shelf) on overall efficiency versus a linear search strategy."
  ],
  "updates": []
}
```

### 中文翻译与人工判断

A 没有把一个失败的、带 loop 的 E1 episode 解释为 surface-first 在所有 object/environment 上都无效；它保留了 target-on-surface 时的比较未决，并指出 navigation loop 需要单独理解。这个 `NO_CHANGE` 是保守且 evidence-bound 的。需要人工判断的是：对于已经明确暴露 interface loop 的失败，A 是否应该额外记录“actor-control failure”而不是完全不更新；当前 schema 允许但没有要求这种元层记录。

## 3. UPDATE / REFINE example — SprayBottle

### What A actually saw — Original English evidence

```text
target task:
pick_and_place_simple-SprayBottle-None-Toilet-426/trial_T20190908_155225_439006

E1 trajectory:
1. go to countertop_1
   You arrive at loc_13. On countertop_1, you see cloth_2, soapbottle_3,
   soapbottle_2, soapbottle_1, spraybottle_1, and toiletpaper_3.
2. take spraybottle_1 from countertop_1
   You take spraybottle_1 from countertop_1.
3. go to toilet_1
4. put spraybottle_1 in/on toilet_1
   task won; 4 executed steps; reward 1.0

probe_status_history:
["ACTIVE", "EVIDENCE_OBTAINED", "NOT_ACTIVE", "NOT_ACTIVE"]
```

### 中文翻译

E1 在第一次导航到 `countertop_1` 后，公共 observation 直接显示 `spraybottle_1`；第二步拿到它，随后前往 `toilet_1` 并完成放置。轨迹是 4 steps、reward 1.0；`EVIDENCE_OBTAINED` 后 H runtime 结束。

### Exact A output — Original JSON

```json
{
  "decision": "UPDATE",
  "still_unresolved": [
    "Whether this strategy remains optimal when the target object is exclusively hidden inside closed containers.",
    "The comparative efficiency gain against the incumbent policy in scenarios requiring multiple container openings."
  ],
  "updates": [
    {
      "evidence_basis": "The target trajectory successfully located 'spraybottle_1' on 'countertop_1' after a single navigation step ('go to countertop_1'), allowing completion of the task in 4 steps without opening any closed containers.",
      "guidance": "Prioritize navigating to and inspecting open-access surfaces before searching closed containers. If the target object is found on an open surface, take it immediately; otherwise, proceed to search closed containers.",
      "operation": "REFINE",
      "provenance": [
        "target_task:pick_and_place_simple-SprayBottle-None-Toilet-426/trial_T20190908_155225_439006"
      ],
      "scope": "ALFWorld pick-and-place tasks where the target object is not visible in the initial room observation and open-access surfaces (e.g., countertops) are present."
    }
  ]
}
```

### 中文翻译与人工判断

这个 `REFINE` 只把 established guidance 限定为“初始不可见、存在 open-access surface 的 ALFWorld pick-and-place task”，并保留 closed-container-only 场景的未决问题。它没有声称 surface-first 全局最优，也没有把 E0 route 或 matched step difference 写进 evidence basis。

但它仍然是单个成功 E1 episode 产生的模型提议；人工 reviewer 应判断 `Prioritize` 是否比这一次证据稍强，以及 scope 是否仍需更窄。`E0` 只留在 researcher-side paired result 中，不在本 A input 或 A prompt 中。

## 4. E0 isolation check

对两个样本的 `a_input.json` 做的机械检查：

```text
set(environment_outcome) == {"e1"}
e0_reference absent
E0 actions absent
E0 step count absent
matched counterfactual fields absent
target evaluator/oracle/review_only fields absent
```

因此本节可直接审查 A 是否过度泛化，而不需要担心它偷偷读取了 counterfactual baseline。

## 5. Human-review questions

- Laptop 的 `NO_CHANGE` 是否充分保留了“目标也许仍在 open surface”的不确定性？
- SprayBottle 的 `UPDATE / REFINE` 是否完全由 4-step E1 evidence 支持？
- `scope` 是否仍比实际 evidence 更宽？`Prioritize` 是否应改成更弱的“try first”？
- A 是否需要将 interface loop/actor reliability 作为 unresolved evidence 单独保留？
- A 是否始终没有把 consumed H 重新写成 active exploratory memory？

## 6. Raw artifact references

```text
NO_CHANGE:
artifacts/exploratory_memory_mvp/clean-a-e1-only-20260916/transfer-p002-to-laptop-qwen38-20260916-v2/a_input.json
artifacts/exploratory_memory_mvp/clean-a-e1-only-20260916/transfer-p002-to-laptop-qwen38-20260916-v2/a_prompt.json
artifacts/exploratory_memory_mvp/clean-a-e1-only-20260916/transfer-p002-to-laptop-qwen38-20260916-v2/a_raw_response.json
artifacts/exploratory_memory_mvp/clean-a-e1-only-20260916/transfer-p002-to-laptop-qwen38-20260916-v2/a_parsed.json

UPDATE / REFINE:
artifacts/exploratory_memory_mvp/clean-a-e1-only-20260916/transfer-p005-to-spraybottle-qwen38-20260916/a_input.json
artifacts/exploratory_memory_mvp/clean-a-e1-only-20260916/transfer-p005-to-spraybottle-qwen38-20260916/a_prompt.json
artifacts/exploratory_memory_mvp/clean-a-e1-only-20260916/transfer-p005-to-spraybottle-qwen38-20260916/a_raw_response.json
artifacts/exploratory_memory_mvp/clean-a-e1-only-20260916/transfer-p005-to-spraybottle-qwen38-20260916/a_parsed.json
```
