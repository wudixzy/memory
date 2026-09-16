# Sample A / B：B `OPEN` 与 `NONE` 控制

## 0. 为什么选择这些样本

Sample A 使用 P005 `alfworld-p-005-soapbottle-417`，其 incumbent route 成功，但 pre-update memory 没有 comparative evidence。它是一个典型的“可行性已知、偏好未决”的 `OPEN` case。

Sample B 使用 N1 `alfworld-n1-001-alarmclock-resolved`。pre-update memory 已保存 incumbent route 与更短 route 的 matched comparative evidence，因此它检验 B 能否关闭已经解决的问题。

两个样本都来自：

```text
Artifact provenance: ORIGINAL SAVED ARTIFACT
artifacts/exploratory_memory_mvp/experiment_a-qwen38-b-boundary-20260916/b/
```

`case_type`、`expected_b`、oracle actions 和 evaluator `why` 只在本文件的 reviewer-only 区域出现，不在 B 的 `b_input.json` 或 prompt 中。

## 1. Sample A — P005 `OPEN`

### Task / Context — Original English

```text
task_id: pick_and_place_simple-SoapBottle-None-Cabinet-417/trial_T20190910_084726_610116
seed: 42
instruction: put some soapbottle on cabinet.

initial observation:
-= Welcome to TextWorld, ALFRED! =-

You are in the middle of a room. Looking quickly around you, you see cabinet_4, cabinet_3, cabinet_2, cabinet_1, countertop_1, garbagecan_1, handtowelholder_1, sinkbasin_2, sinkbasin_1, toilet_1, toiletpaperhanger_1, and towelholder_1.

Your task is to: put some soapbottle on cabinet.
```

### 中文翻译

```text
任务是在当前房间中找到 soapbottle，并把它放到 cabinet 上。初始公共观察列出了多个 closed cabinet 和开放表面/设施，但 requested object 没有直接出现在初始观察中。
```

### Pre-update established memory — Original English

```json
{
  "memory_id": "established-search-listed-order-soapbottle-417",
  "scope": "Repeated ALFWorld pick-and-place tasks where the requested object is not visible in the initial room.",
  "guidance": "Search visible receptacles in the order presented by the room observation. At each location, open a closed receptacle before inspecting it; take the requested object and place it in the requested destination.",
  "prior_comparison_evidence": null
}
```

### 中文翻译与解释

这条 established memory 只确认一种按观察顺序搜索的可行 guidance；`prior_comparison_evidence` 为 `null`，没有确认 cabinet-first 相对于 surface-first 的优越性。

### Current completed trajectory — Original English

```json
{
  "executed_actions": [
    "look",
    "go to cabinet_1",
    "open cabinet_1",
    "go to cabinet_2",
    "open cabinet_2",
    "go to cabinet_3",
    "open cabinet_3",
    "go to countertop_1",
    "take soapbottle_1 from countertop_1",
    "go to cabinet_1",
    "put soapbottle_1 in/on cabinet_1"
  ],
  "completed_requested_sequence": true,
  "final": {"done": true, "won": true, "reward": 1.0}
}
```

### 中文翻译与解释

incumbent route 先打开三个 cabinet，之后才到 `countertop_1` 取到 `soapbottle_1`，最终成功。这个结果证明 feasibility，但单独不能证明搜索顺序是 preferred/default realization。

### B prompt-critical instructions — Original English

```text
Your role is comparative diagnosis only:

    B: decide which incumbent comparison is worth opening.
    C: later construct and ground one concrete local test.

Do not propose, name, ground, verify, or execute a concrete alternative. Do not
require evidence that a concrete alternative already exists. C will synthesize
and ground an alternative only after B returns OPEN.

A successful incumbent establishes feasibility under its observed scope, not
comparative superiority or default status.

An alternative being absent from memory is not evidence that the comparison is
resolved.
```

### 中文翻译

```text
B 只负责比较诊断：判断哪个 incumbent comparison 值得打开；具体 alternative 由 C 在 B 返回 OPEN 后构造和 grounding。

不要要求已经存在具体 alternative 的证据。成功的 incumbent 只证明在观察 scope 下可行，不证明 comparative superiority 或 default status。memory 中没有 alternative，也不能作为 comparison 已解决的证据。
```

### Exact visible B output — Original JSON

```json
{
  "decision": "OPEN",
  "evidence_status": {
    "comparative_support": "No evidence exists to show that searching cabinets first is superior to other strategies (e.g., checking countertops or sinks first). The success only confirms feasibility, not optimality or default status.",
    "feasibility_support": "The incumbent successfully located and retrieved the soapbottle from countertop_1 after searching three cabinets, proving the sequence is executable and effective in this instance.",
    "policy_relevance": "Determining whether a specific search order (cabinets vs. surfaces) is preferred materially affects efficiency and policy generalization for future pick-and-place tasks with hidden objects."
  },
  "functional_contract": {
    "available_state": "Agent at start location; target object (soapbottle) is not visible in initial room observation; multiple receptacles (cabinets, countertops, etc.) are present.",
    "constraints": [
      "Must respect physical adjacency or movement costs if applicable.",
      "Must not assume object location without verification.",
      "Search must terminate upon finding the object."
    ],
    "local_function": "Execute a search strategy to locate the target object among non-visible receptacles.",
    "required_downstream_state": "Target object identified and accessible for pickup."
  },
  "incumbent_segment": "Sequential search of cabinets (1, 2, 3) before checking countertop_1 for the target object.",
  "warrant": "The incumbent's choice to search cabinets sequentially before surfaces is an arbitrary heuristic validated only by success, not comparative superiority. Resolving whether surface-first or cabinet-first search is more efficient or robust is a meaningful open question for policy optimization."
}
```

### 中文翻译与字段说明

- `decision: OPEN`：B 判断存在一个值得交给 C 实例化的未决 comparison。
- `incumbent_segment`：定位到 cabinet-first 的局部搜索段，而不是重写整个任务。
- `comparative_support`：明确说没有证明 cabinet-first 优于其他搜索 realization。
- `policy_relevance`：搜索顺序可能改变未来 hidden-object task 的效率和 policy。
- `functional_contract`：保存入口状态、定位功能、取到目标后的 downstream state，以及“不凭假设定位、找到即停止”等约束。

### Evaluator-only expected rationale — 仅 evaluator 可见

```text
The established route completes in 11 steps. The source-directed local replacement completes in 6 steps and remains a local search-segment substitution.
```

上面这句话来自 case fixture 的 `evaluator_notes.why`，没有进入 B prompt；B 只看到了真实 current trajectory 和 pre-update memory。

## 2. Sample B — N1 `NONE`

### Task / Memory — Original English

```text
task_id: pick_and_place_simple-AlarmClock-None-Desk-314/trial_T20190908_185938_027368
seed: 42
instruction: put a alarmclock in desk.

initial observation:
-= Welcome to TextWorld, ALFRED! =-

You are in the middle of a room. Looking quickly around you, you see bed_1, desk_1, drawer_5, drawer_4, drawer_3, drawer_2, drawer_1, dresser_1, and garbagecan_1.

Your task is to: put a alarmclock in desk.

pre-update memory:
{
  "memory_id": "established-alarmclock-comparison-resolved",
  "scope": "This exact ALFWorld task state and its matching pick-and-place tasks.",
  "guidance": "A listed-order search route completes the task reliably.",
  "prior_comparison_evidence": "A matched replay completed with the listed-order route in 17 steps. A source-directed local route also completed in 5 steps. The two outcomes and step counts are already recorded for this scope; use the 5-step route when the same state is recognized."
}
```

### 中文翻译与解释

该 memory 已经包含同一 scope 内的 matched comparative evidence：listed-order route 为 17 steps，source-directed route 为 5 steps，并且已规定相应状态使用短 route。因此这里的问题不是“alternative 不在 memory”，而是 comparison 已有结果并已改变 default policy。

### Current trajectory — Original English

```json
{
  "executed_actions": [
    "look", "go to bed_1", "go to desk_1", "go to drawer_1", "open drawer_1",
    "go to drawer_2", "open drawer_2", "go to drawer_3", "open drawer_3",
    "go to drawer_4", "open drawer_4", "go to drawer_5", "open drawer_5",
    "go to dresser_1", "take alarmclock_2 from dresser_1", "go to desk_1",
    "put alarmclock_2 in/on desk_1"
  ],
  "completed_requested_sequence": true,
  "final": {"done": true, "won": true, "reward": 1.0}
}
```

### Exact visible B output — Original JSON

```json
{
  "decision": "NONE",
  "evidence_status": {
    "comparative_support": "Pre-existing memory explicitly records a comparison between this 17-step route and a more efficient 5-step source-directed route, resolving the status of the incumbent as non-preferred.",
    "feasibility_support": "The incumbent trajectory successfully completes the task in 17 steps.",
    "policy_relevance": "The policy is already established to use the 5-step route when the state is recognized; reopening the comparison would not change future behavior."
  },
  "functional_contract": null,
  "incumbent_segment": null,
  "warrant": "The comparative status of the incumbent search strategy is already closed by established memory which identifies a superior alternative and dictates its use. No new diagnostic value exists in re-evaluating the incumbent's efficiency."
}
```

### 中文翻译与人工判断

`NONE` 的理由是已有 comparative evidence 关闭了 incumbent status，并且已有 policy guidance；不是因为 B 需要先看到新的 alternative。与 Sample A 的真实区别在于 Sample A 的 `prior_comparison_evidence` 为空，而 Sample B 的 memory 已经记录 matched outcomes 和当前应采用的短 route。

### Reviewer-only isolation note

Sample B 的 `case_type: N1`、`expected_b: NONE`、oracle action list 和 evaluator `why` 都不属于模型可见输入。它们只用来帮助 review 对照 B 的人工标签。

## 3. Human-review questions

- Sample A 的 `OPEN` 是否确实只打开了“cabinet-first vs. another local search realization”的问题？
- Sample B 的 comparative evidence 是否足以关闭该问题，scope 是否过窄或过宽？
- B 的 `functional_contract` 是否描述了要保留的功能，而没有偷偷指定 C 应采用的 alternative？
- B 的 `warrant` 是否是可审计的可见判断，而不是隐藏推理的替代品？

## 4. Raw artifact references

```text
P005:
artifacts/exploratory_memory_mvp/experiment_a-qwen38-b-boundary-20260916/b/alfworld-p-005-soapbottle-417/b_input.json
artifacts/exploratory_memory_mvp/experiment_a-qwen38-b-boundary-20260916/b/alfworld-p-005-soapbottle-417/b_prompt.json
artifacts/exploratory_memory_mvp/experiment_a-qwen38-b-boundary-20260916/b/alfworld-p-005-soapbottle-417/b_raw_response.json
artifacts/exploratory_memory_mvp/experiment_a-qwen38-b-boundary-20260916/b/alfworld-p-005-soapbottle-417/b_parsed.json

N1:
artifacts/exploratory_memory_mvp/experiment_a-qwen38-b-boundary-20260916/b/alfworld-n1-001-alarmclock-resolved/b_input.json
artifacts/exploratory_memory_mvp/experiment_a-qwen38-b-boundary-20260916/b/alfworld-n1-001-alarmclock-resolved/b_prompt.json
artifacts/exploratory_memory_mvp/experiment_a-qwen38-b-boundary-20260916/b/alfworld-n1-001-alarmclock-resolved/b_raw_response.json
artifacts/exploratory_memory_mvp/experiment_a-qwen38-b-boundary-20260916/b/alfworld-n1-001-alarmclock-resolved/b_parsed.json
```
