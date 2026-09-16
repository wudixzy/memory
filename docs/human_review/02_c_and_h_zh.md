# Sample C：Clean C / H synthesis

## 0. 为什么这个样本重要

这个样本检查上一轮 cleanup 后的 fact-only local packet 是否仍能让 C 独立提出一个 local alternative。研究问题不是 C 能否复述 researcher suggestion，而是：在没有完成 source trajectory、没有 later source observations 的情况下，C 是否能根据 B 的 Functional Contract、入口事实和真实 capability 形成可执行的 probe policy。

```text
Artifact provenance: ORIGINAL SAVED ARTIFACT
artifacts/exploratory_memory_mvp/experiment_c-qwen38-clean-20260916/alfworld-p-005-soapbottle-417/
model: qwen3.8-flash
thinking: false
temperature: 0
```

## 1. Task / context

### Original English

```text
task_id: pick_and_place_simple-SoapBottle-None-Cabinet-417/trial_T20190910_084726_610116
seed: 42
instruction: put some soapbottle on cabinet.

The entry observation names cabinet_4, cabinet_3, cabinet_2, cabinet_1,
countertop_1, garbagecan_1, handtowelholder_1, sinkbasin_2, sinkbasin_1,
toilet_1, toiletpaperhanger_1, and towelholder_1. The requested object is not
visible in the entry observation.
```

### 中文翻译

目标是找到 soapbottle 并把它放到 cabinet。entry observation 公开了多个 cabinet、`countertop_1`、sink 等 receptacle；requested object 在 entry observation 中不可见。

## 2. Fact-only local packet

### Original JSON

```json
{
  "entry_state": {
    "admissible_actions": [
      "go to cabinet_1",
      "go to cabinet_2",
      "go to cabinet_3",
      "go to cabinet_4",
      "go to countertop_1",
      "go to garbagecan_1",
      "go to handtowelholder_1",
      "go to sinkbasin_1",
      "go to sinkbasin_2",
      "go to toilet_1",
      "go to toiletpaperhanger_1",
      "go to towelholder_1",
      "inventory",
      "look"
    ],
    "observation": "-= Welcome to TextWorld, ALFRED! =-\n\nYou are in the middle of a room. Looking quickly around you, you see cabinet_4, cabinet_3, cabinet_2, cabinet_1, countertop_1, garbagecan_1, handtowelholder_1, sinkbasin_2, sinkbasin_1, toilet_1, toiletpaperhanger_1, and towelholder_1.\n\nYour task is to: put some soapbottle on cabinet.",
    "won": false
  },
  "public_evidence": [
    "The entry observation names closed cabinets and accessible surfaces such as a countertop and sinks. The requested object is not visible in the entry observation.",
    "The local function under comparison is selecting a search realization before acquiring the requested object while preserving the downstream placement contract."
  ]
}
```

### 中文翻译与边界说明

```text
入口 observation 中有 closed cabinets 和 countertop、sinks 等 accessible surfaces；requested object 不可见。
当前比较的 local function 是：在获取 requested object 前选择一种 search realization，同时保留 downstream placement contract。
```

这里没有 `try open surfaces first`、`prefer cabinets first`、`check X before Y` 等推荐性 wording。`local_c_packet.json` 也没有 completed source trajectory 或 later source observation。C 的 `b_diagnosis` 仍然包含 B 对 incumbent segment 的诊断；这属于 B 的输出，而不是 researcher 在 local packet 中塞入的 candidate realization。

## 3. Capability representation

### Entry-state capability — Original JSON excerpt

```json
{
  "entry_state_capabilities": {
    "currently_admissible_actions": [
      "go to cabinet_1", "go to cabinet_2", "go to cabinet_3", "go to cabinet_4",
      "go to countertop_1", "go to garbagecan_1", "go to handtowelholder_1",
      "go to sinkbasin_1", "go to sinkbasin_2", "go to toilet_1",
      "go to toiletpaperhanger_1", "go to towelholder_1", "inventory", "look"
    ],
    "currently_visible_or_referenced_entities": [
      "cabinet_1", "cabinet_2", "cabinet_3", "cabinet_4", "countertop_1",
      "garbagecan_1", "handtowelholder_1", "sinkbasin_1", "sinkbasin_2",
      "toilet_1", "toiletpaperhanger_1", "towelholder_1"
    ]
  },
  "historical_capability_vocabulary": {
    "action_names": [
      "look", "inventory", "go to", "open", "close", "examine", "take",
      "put", "use", "clean", "heat", "cool"
    ]
  }
}
```

### 中文翻译与解释

`entry_state_capabilities` 是 source entry state 当下实际 admissible 的动作和可见 entity。`historical_capability_vocabulary` 只提供真实 carrier 的 action schema/vocabulary；它不证明从未来任意 state 可以直接执行一整段序列。完整 `c_input.json` 和 `capabilities.json` 在 artifact path 中。

## 4. C prompt-critical instructions

### Original English

```text
Use only the public input fields: B's diagnosis, the visible task/instruction,
the manually curated local state/evidence packet, pre-update established
memory, and the real ALFWorld capability evidence. The local packet is
deliberately not the completed source trajectory.

The source_grounding.entry_action must be copied exactly from the source
entry-state admissible actions. It is provenance for C's creation, not the
future target instruction.

Do not put that source action or source entity IDs into scope, hypothesis,
guidance, local_function, realization_pattern, capability_requirements,
adaptive_policy, evidence_goal, stop_conditions, or required_downstream_state.

Do not emit an action list or pre-plan later actions whose legality depends on
future observations. The adaptive_policy must describe a local substitution,
react to the next real observation, and preserve B's Functional Contract.
```

### 中文翻译

```text
C 只能使用 B diagnosis、可见 task/instruction、手工整理的 local state/evidence、established memory 和真实 ALFWorld capability。local packet 刻意不包含完整 source trajectory。

source_grounding.entry_action 必须原样复制自 source entry-state admissible actions，但它只是 C 创建时的 provenance，不是 future target instruction。

source action 或 source entity IDs 不得进入 future-facing scope、hypothesis、guidance、probe policy 等字段。不得输出依赖未来 observation 的完整 action list；adaptive_policy 必须响应下一次真实 observation，并保持 Functional Contract。
```

## 5. Exact C output

### Original JSON

```json
{
  "decision": "CREATE",
  "type": "exploratory",
  "scope": "Future ALFWorld pick-and-place tasks where the target object is hidden and both closed storage receptacles (cabinets) and open surfaces (countertops/sinks) are visible in the initial observation.",
  "hypothesis": "Prioritizing inspection of open surfaces before opening closed storage receptacles reduces the average number of actions required to locate the target object compared to a cabinet-first search strategy.",
  "guidance": "Upon entering the room, navigate to an available open surface (e.g., countertop or sink) first. Inspect it for the target object. If not found, proceed to other open surfaces. Only after exhausting open surfaces should you begin navigating to and opening closed storage receptacles.",
  "probe_spec": {
    "local_function": "Selecting the next location to inspect during the search phase for a hidden object.",
    "realization_pattern": "Surface-First Search: Iterate through all visible open surfaces (countertops, sinks, etc.) before iterating through closed storage units (cabinets).",
    "capability_requirements": [
      "Navigation to visible entities",
      "Inspection of open surfaces (implicit via 'go to' and 'look' or direct visibility)",
      "Opening closed receptacles (if fallback needed)"
    ],
    "adaptive_policy": "1. Identify all open surfaces in the current observation. 2. Navigate to the nearest unvisited open surface. 3. Check if the target object is present. 4. If yes, take it. 5. If no, repeat step 2 for remaining open surfaces. 6. If all open surfaces are exhausted without finding the object, switch to the incumbent cabinet-first strategy (navigate to cabinet, open, check).",
    "evidence_goal": "Record the total number of actions taken from the start state until the target object is acquired. Compare this count against the baseline cabinet-first action count.",
    "stop_conditions": [
      "Target object is found and taken.",
      "All open surfaces have been inspected without success (triggering fallback to cabinets).",
      "Maximum exploration steps reached."
    ],
    "required_downstream_state": "Agent holding the target object, ready to place it on the destination."
  },
  "source_grounding": {
    "entry_action": "go to countertop_1",
    "why_grounded": "The entry observation lists 'countertop_1' as a visible entity, and 'go to countertop_1' is explicitly listed in the admissible actions for the source probe-entry state.",
    "public_capability_evidence": [
      "entry_state_capabilities.currently_admissible_actions includes 'go to countertop_1'",
      "historical_capability_vocabulary.action_schema defines 'go to <receptacle_id>' as a valid navigation action"
    ]
  },
  "provenance": [
    "B's diagnosis of OPEN status regarding search order efficiency",
    "Local state evidence showing mixed presence of cabinets and countertops",
    "Real capabilities confirming navigability to both types of receptacles at entry"
  ],
  "reason": "The incumbent memory assumes a sequential search of cabinets first. B identifies this as arbitrary. This probe tests the alternative 'surface-first' heuristic by grounding the initial move to a countertop, which is legally accessible at the start state, allowing a direct comparison of action costs between the two strategies."
}
```

### 中文翻译与字段解释

- `decision: CREATE`：C 认为可以创建一个一次性的 exploratory memory。
- `scope`：限定为初始 observation 中同时有 closed storage 和 open surfaces 的 hidden-object pick-and-place context。
- `hypothesis`：测试 surface-first 是否能减少获取目标所需的动作数；不是宣称已经成立。
- `adaptive_policy`：未来根据当前 observation 选择未访问的 open surface，失败后再转向 incumbent closed-container search；它没有列出未来固定 entity ID 的完整 action sequence。
- `evidence_goal`：记录到 acquisition 的 action count，并与 baseline 比较。
- `required_downstream_state`：必须仍持有目标、能够继续 placement。

这里 C 用了 `countertop_1` 作为 `source_grounding.entry_action`，但 future-facing 字段只使用 open surface / closed storage 等 role/type 描述。这是 source grounding 与未来 H 的分离点。

## 6. Source grounding 与 future-facing H

### Source grounding — Original JSON

```json
{
  "entry_action": "go to countertop_1",
  "why_grounded": "The entry observation lists 'countertop_1' as a visible entity, and 'go to countertop_1' is explicitly listed in the admissible actions for the source probe-entry state.",
  "public_capability_evidence": [
    "entry_state_capabilities.currently_admissible_actions includes 'go to countertop_1'",
    "historical_capability_vocabulary.action_schema defines 'go to <receptacle_id>' as a valid navigation action"
  ]
}
```

### Future H shown to target actor — Original JSON

```json
{
  "type": "exploratory",
  "scope": "Future ALFWorld pick-and-place tasks where the target object is hidden and both closed containers (e.g., cabinets) and open surfaces (e.g., countertops, sinks) are present in the initial observation.",
  "hypothesis": "Prioritizing inspection of open surfaces before opening closed storage receptacles reduces the average number of actions required to locate the target object compared to a cabinet-first search strategy.",
  "guidance": "Upon entering the room, navigate to an available open surface (e.g., countertop or sink) first. Inspect it for the target object. If not found, proceed to other open surfaces. Only after exhausting open surfaces should you begin navigating to and opening closed storage receptacles.",
  "probe_policy": {
    "local_function": "Selecting the next location to inspect during the search phase for a hidden object.",
    "realization_pattern": "Surface-First Search: Iterate through all visible open surfaces (countertops, sinks, etc.) before iterating through closed storage units (cabinets).",
    "capability_requirements": [
      "Navigation to visible entities",
      "Inspection of open surfaces (implicit via 'go to' and 'look' or direct visibility)",
      "Opening closed receptacles (if fallback needed)"
    ],
    "adaptive_policy": "1. Identify all open surfaces in the current observation. 2. Navigate to the nearest unvisited open surface. 3. Check if the target object is present. 4. If yes, take it. 5. If no, repeat step 2 for remaining open surfaces. 6. If all open surfaces are exhausted without finding the object, switch to the incumbent cabinet-first strategy (navigate to cabinet, open, check).",
    "evidence_goal": "Record the total number of actions taken from the start state until the target object is acquired. Compare this count against the baseline cabinet-first action count.",
    "stop_conditions": [
      "Target object is found and taken.",
      "All open surfaces have been inspected without success (triggering fallback to cabinets).",
      "Maximum exploration steps reached."
    ],
    "required_downstream_state": "Agent holding the target object, ready to place it on the destination."
  }
}
```

### 中文 Review

H 没有 source `countertop_1` 作为 future action，也没有 source object location 或 source outcome。它是一个可迁移的“先尝试当前可见 open surface，再依据 observation 自适应”的模式。不过 `hypothesis` 和 `evidence_goal` 仍然相对强，人工 review 时应判断一个单次 source C 输出是否足以支持这种 scope，而不能把 C 的 wording 当作已验证结论。

## 7. Human-review questions

- 删除 researcher hint 后，C 的 `Surface-First Search` 是否仍可视为独立提出？
- C 是否把“visible open surface”误当成在所有未来 state 都已知、可直接访问？
- `adaptive_policy` 是否足够 local，还是仍接近 whole-task plan？
- H 的 scope 是否比 source evidence 更宽？`future H` 是否应进一步缩小 scope？
- `source_grounding` 只证明入口动作合法，是否被误读成证明整个 future sequence 合法？

## 8. Raw artifact references

```text
artifacts/exploratory_memory_mvp/experiment_c-qwen38-clean-20260916/alfworld-p-005-soapbottle-417/local_c_packet.json
artifacts/exploratory_memory_mvp/experiment_c-qwen38-clean-20260916/alfworld-p-005-soapbottle-417/c_input.json
artifacts/exploratory_memory_mvp/experiment_c-qwen38-clean-20260916/alfworld-p-005-soapbottle-417/c_prompt.json
artifacts/exploratory_memory_mvp/experiment_c-qwen38-clean-20260916/alfworld-p-005-soapbottle-417/c_raw_response.json
artifacts/exploratory_memory_mvp/experiment_c-qwen38-clean-20260916/alfworld-p-005-soapbottle-417/c_parsed.json
artifacts/exploratory_memory_mvp/experiment_c-qwen38-clean-20260916/alfworld-p-005-soapbottle-417/capabilities.json
artifacts/exploratory_memory_mvp/experiment_c-qwen38-clean-20260916/alfworld-p-005-soapbottle-417/mechanical_grounding.json
```
