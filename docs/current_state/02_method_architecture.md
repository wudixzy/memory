# 02. 当前方法架构与 Offline / Online Dataflow

## 1. 总体设计原则

当前方法已经明确采用：

    Heavy Offline Memory Evolution
    +
    Lightweight Online Memory Consumption

核心工程原则：

    Online writes facts;
    Offline writes knowledge.

这里的 offline 更准确地说是 episode-between / 非 action-latency-critical path。它不要求真正的异步后台服务，只要求较重 semantic reasoning 不出现在每一步 tool-use critical path 中。

## 2. 总体数据流

当前建议的完整系统不是简单串行：

    trajectory -> Stage 1 -> A -> B -> C

因为 B/C 的 historical side 必须使用 pre-update established memory snapshot，不能让当前 trajectory 经 A 写入 memory 后又被当成历史 evidence。

正确的逻辑是：

                         +--> A --> established update
                         |
    trajectory -> Stage1
                         |
                         +--> B(K_pre)
                               |
                               v
                             C(K_pre, local context)
                               |
                               v
                               H

然后统一 materialize：

    K_{t+1}
      = Apply(A update)
      + newly created H
      + consolidation/index refresh

## 3. Memory State

概念上：

    K_t = K_t^established ∪ K_t^exploratory

### Established

持久的、已被 evidence 支持的 reusable guidance。

### Exploratory

尚未成立为知识的 one-shot future probe。

探索性 memory 不应该因为被创建就获得 established authority。

## 4. Offline / Between-Episode Pipeline

### 4.1 Stage 1

目标：

    raw trajectory -> candidate experiences / evidence

负责：

- trajectory parsing；
- candidate experience extraction；
- provenance；
- 为 A / B 提供较清晰的语义输入。

当前 MVP 大量实验有意 bypass Stage 1，以隔离 B/C/H 本身。

后续 full-loop 才接入最小 Stage 1。

### 4.2 A — Established Memory Reconciliation

问题：

    What does this new evidence change about what we already know?

可能输出：

- ADD；
- REFINE；
- SPECIALIZE；
- MERGE；
- NO_CHANGE。

A 必须 conservative、evidence-bound、scope-limited。

A 只允许看真实发生的 episode evidence，不允许看 researcher-side E0 counterfactual。

### 4.3 B — Open Comparative Question Diagnosis

问题：

    Which incumbent comparison is worth opening?

输入：

    current completed trajectory
    + K_pre^established

职责：

- 找 local incumbent behavior；
- 区分 feasibility support 与 comparative support；
- 判断 comparison 是否 unresolved；
- 判断解决它是否可能 materially change future policy；
- 输出 Functional Contract。

B 不负责提出具体 alternative。

### 4.4 C — Exploratory-Memory Synthesis

问题：

    What grounded local test should be tried once to answer B's question?

输入应局部化：

    B diagnosis / Functional Contract
    + local public state/evidence
    + relevant established memory
    + relevant capabilities/tools

C 不应该重新读取整条 completed source trajectory，也不应该把 source 最终答案缓存进 H。

输出是 adaptive probe policy，不是 future open-loop action sequence。

### 4.5 Consolidation / Index Refresh

在 established update 与新 H 产生之后：

- materialize persistent state；
- 去重/合并必要 metadata；
- 更新 embeddings / index；
- 为未来 retrieval 准备 searchable representation。

这部分允许比较重，因为不在 online critical path。

## 5. Online Pipeline

Online 尽量保持：

    task/current state
      -> retrieve
      -> activate
      -> ground
      -> act
      -> observe/log
      -> repeat

### 5.1 Retrieval

在线主要新增的是 memory retrieval：

- retrieve established memories；
- retrieve exploratory H；
- metadata / embedding recall；
- 可选小规模 rerank / semantic selection。

设计目标：

    cheap recall
      -> small top-k
      -> at most light selection

不要把 retrieval 本身重新做成重型 planning agent。

### 5.2 Scope Match / Activation

决定当前 context 是否适合某条 H。

正式系统需要 automatic retrieval；当前 MVP 的 cross-task transfer 仍主要使用 researcher-confirmed scope match。

后续 evaluation 应同时测试：

    C3_oracle-match
    C3_auto-retrieval

用于分离 retrieval error 与 H content/execution error。

### 5.3 Target-time Grounding

H 保存的是：

    realization pattern / capability requirement

不是：

    exact source action/entity ID

例如 H 表达：

    try an available open surface before closed storage

未来 target 中 actor 根据真实 observation/admissible actions 将其 ground 成：

    desk_2
    countertop_1
    shelf_3
    ...

这一步属于正常 online tool-use grounding，不需要重新调用重型 C。

### 5.4 Stepwise Actor

Actor 每次：

    latest state
    + task
    + relevant established memory
    + active H if any
    + runtime bookkeeping
    -> choose exactly one action

当前 harness 使用 zero-based action_index：

    resolved_action = admissible_actions[action_index]

模型仍然负责 semantic action selection；代码只负责 exact lookup。

### 5.5 probe_runtime_state

当前只包含机械事实，例如：

- visited_receptacles；
- probe_action_count；
- executed_action_history。

它不包含：

- best next action；
- evidence conclusion；
- fallback route；
- rule-selected plan。

因此它属于轻量 runtime bookkeeping，而不是一个新 controller。

### 5.6 H Lifecycle

Persistent H：

    active
      -> first activation
    consumed

一旦真正激活，H 不再回到未来 persistent active pool。

但当前 episode 中保留 runtime copy：

    ACTIVE
      -> EVIDENCE_OBTAINED / ABORTED
      -> remove runtime H
      -> continue original task

这里的 EVIDENCE_OBTAINED 更准确理解为：

    PROBE_EVIDENCE_READY

它不表示 hypothesis 为真，也不表示 alternative 更优。

### 5.7 Evidence Logging

在线只记录：

- actions；
- observations；
- cost；
- success/failure；
- H activation/status；
- probe progress；
- provenance。

真正的 semantic interpretation 和 persistent memory update在 episode 后由 A/B/C 完成。

## 6. Functional Contract

Functional Contract 是 B 与 C 之间的关键接口，描述：

    available_state
    local_function
    required_downstream_state
    constraints

它的目标是定义：

> 哪个局部功能允许被替换，以及替换后必须保留什么。

它不描述具体 alternative。

例如：

    local_function:
      locate requested hidden object

    required_downstream_state:
      requested object remains acquirable and
      can still be delivered to destination

这样 C 可以改变 local search realization，而不会重新规划整个 task。

## 7. Source Grounding 与 Future Grounding

C 创建 H 时需要 source grounding：

> 证明 proposed experiment 不是凭空想象出来的。

但 future actor 不应该看到 source exact grounding 作为执行命令。

因此：

    source_grounding
      = creation-time provenance

    future-facing H
      = scope + hypothesis + probe_policy

future target 中再做 current-state grounding。

## 8. 当前系统的轻重边界

### Offline 可以重

- Stage 1；
- A；
- B；
- C；
- semantic memory retrieval for synthesis；
- consolidation；
- index refresh；
- 更强模型；
- 多次 LLM call。

### Online 应保持轻

- retrieval；
- small rerank；
- H activation；
- target-time grounding；
- normal actor；
- action-index lookup；
- probe_runtime_state；
- lifecycle bookkeeping；
- evidence logging。

## 9. 当前明确不采用的设计

默认不重新引入：

- online B/C；
- 每一步 semantic memory update；
- graph search controller；
- VOI controller；
- global trajectory planner；
- rule-based fallback planner；
- future open-loop action synthesis；
- H 的多 episode 自动重复执行。

这些只有在新的 evidence 明确表明当前结构无法工作时才值得重新讨论。
