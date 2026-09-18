# 03. 组件职责、信息边界与实现契约

本文面向实现者和 reviewer，重点不是介绍故事，而是回答：

> 每个模块到底能看什么、必须输出什么、不能做什么？

## 1. Stage 1

### 职责

    completed trajectory -> candidate experiences / evidence

### 应做

- 提取候选 experience；
- 保留 provenance；
- 把 raw trace 转成后续模块可读的 evidence 单元。

### 不应做

- 直接决定 unresolved comparison；
- 生成 H；
- 替 A 决定 memory update；
- 用 evaluator oracle 做 semantic labeling。

### 当前状态

尚未正式接入 full pipeline。MVP 中大量实验有意绕过。

## 2. A — Memory Reconciler

### 核心问题

    What does this new evidence change about what we already know?

### 输入

- pre-update established memories；
- consumed H（如果该 episode 使用了 H）；
- actual target task；
- actual E1 public trajectory；
- actual probe trace；
- actual outcome/cost；
- provenance。

### 明确禁止输入

- E0 reference；
- researcher counterfactual；
- oracle target location；
- positive/negative evaluator label；
- expected conclusion；
- hidden benchmark answer。

### 输出语义

    decision: NO_CHANGE | UPDATE

update operation 可以包括：

- ADD；
- REFINE；
- SPECIALIZE；
- MERGE。

### 约束

一次 positive episode 不得升级成 universal optimum。

一次 negative probe 不得自动否定整个 hypothesis family。

EVIDENCE_OBTAINED 不等于 hypothesis validated。

## 3. B — Comparative Diagnosis

### 核心问题

    Which incumbent comparison is worth opening?

### 输入

- current completed trajectory；
- pre-update established memory snapshot K_pre；
- current task/public state。

### 可以判断

- incumbent local segment；
- feasibility support；
- comparative support；
- policy relevance；
- Functional Contract；
- OPEN / NONE。

### 不负责

- 具体 alternative；
- tool substitution；
- future action sequence；
- alternative execution proof；
- exploration score。

### 当前推荐输出结构

    decision: OPEN | NONE
    incumbent_segment
    evidence_status:
      feasibility_support
      comparative_support
      policy_relevance
    functional_contract:
      available_state
      local_function
      required_downstream_state
      constraints
    warrant

### 关键原则

    successful incumbent
    -> feasibility evidence

不能推出：

    comparative superiority

## 4. Functional Contract

### 目的

定义 local replacement boundary，而不是给 C 答案。

### 字段语义

**available_state**

局部行为发生前 agent 可以依赖什么状态。

**local_function**

该 segment 真正在完成什么功能。

**required_downstream_state**

替代行为结束后，后续 task 仍需要什么状态。

**constraints**

不能破坏的局部限制。

### 为什么重要

它让 C 可以只替换局部 realization，而不需要重新规划整个 task。

## 5. C — Exploratory Memory Synthesizer

### 核心问题

    What grounded local test should be tried once
    to answer B's open comparison?

### 输入

- B OPEN diagnosis；
- Functional Contract；
- local public facts；
- relevant established memories；
- relevant capabilities/tools。

### Local packet 原则

只能告诉 C：

- 当前有哪些 public affordances；
- object 是否 visible；
- local function；
- downstream contract。

不能提前告诉：

- try open surface first；
- prefer cabinet first；
- check X before Y。

也就是：

    facts, not candidate solution

### 输出

H 的 future-facing 部分：

    scope
    hypothesis
    guidance
    probe_policy

probe_policy 至少包含：

    local_function
    realization_pattern
    capability_requirements
    adaptive_policy
    evidence_goal
    stop_conditions
    required_downstream_state

另保留：

    source_grounding
    provenance

### 不允许

- 输出完整 future action list；
- 把 source entity ID 写进 future policy；
- 用 source 最终 object location 当未来答案；
- 重规划整条 task；
- 强制 CREATE。

C 可以返回 NONE。

## 6. H — Exploratory Memory

### 本质

H 不是 knowledge claim，而是：

    one-shot grounded future experiment

### 应足够具体

不能只是：

    explore more

### 又不能太具体

不能是：

    go to dresser_1 next time

### 理想抽象层级

    local policy guidance

例如：

> 在 hidden-object search 的匹配 context 中，先测试当前可用的 open surface，再根据 observation adaptive continuation。

## 7. Source Grounding

### 用途

证明 C 的 proposal 在 source 创建时是 capability-grounded 的。

### 可以包含

- exact source entry action；
- source entity ID；
- current admissibility；
- creation-time capability evidence。

### 不能成为

future actor 的固定 action command。

## 8. Future Actor View

Future target actor 主要消费：

    scope
    hypothesis
    guidance
    probe_policy

而不是：

    source_grounding

## 9. Online Actor

### 输入

- task；
- current public state；
- ordered admissible actions；
- established memory；
- active H；
- executed action history；
- mechanical probe_runtime_state。

### 输出

当前推荐：

    action_index
    probe_status

probe_status：

    NOT_ACTIVE
    ACTIVE
    EVIDENCE_OBTAINED
    ABORTED

### action_index

zero-based。

runner 只做：

    resolved_action = admissible_actions[action_index]

### 语义责任

actor 负责：

- semantic action choice；
- target-time grounding；
- H adaptive execution；
- evidence-ready / abort decision；
- task continuation。

代码不应该替它做：

- best-next-action selection；
- semantic evidence judgment；
- fallback strategy planning。

## 10. probe_runtime_state

只允许 mechanically derived facts：

- visited_receptacles；
- probe_action_count；
- executed_action_history；
- current H status。

不允许：

- “next best candidate”；
- “comparison resolved”；
- “fallback should be cabinet_3”。

## 11. H Lifecycle

### Persistent

    active -> consumed

第一次真正激活即 consumed。

### Runtime

同 episode 内：

    ACTIVE
      -> terminal probe status
      -> remove runtime H
      -> continue ordinary task

### 注意

Consumed 不等于 hypothesis true/false。

它只意味着这条 one-shot exploration instruction 不再进入未来 episode active pool。

## 12. Retrieval

当前正式系统尚未完成 automatic retrieval。

未来应分：

### Oracle / Researcher Match

用于隔离 H content/execution quality。

### Automatic Retrieval

用于 full system。

二者必须分别报告。

## 13. Mechanical Code vs Semantic LLM

### 适合 deterministic code

- schema validation；
- provenance；
- leakage checks；
- action-index resolution；
- current admissibility；
- pairing proof；
- replay spec；
- runtime counts/visited IDs；
- telemetry；
- lifecycle state；
- artifact persistence。

### 适合 LLM semantic judgment

- experience meaning；
- A reconciliation；
- B comparison diagnosis；
- Functional Contract；
- C alternative synthesis；
- scope/generalization；
- evidence interpretation。

总原则：

    Rules validate mechanics/provenance;
    LLMs interpret semantics.
