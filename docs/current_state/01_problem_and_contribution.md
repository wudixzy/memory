# 01. Problem Definition 与预期 Contribution

## 1. 研究背景

Persistent memory 的典型目标是把历史 trajectory 转化为未来可复用的知识：

    trajectories -> memory -> better future behavior

大多数 memory 方法关注的问题包括：

- 历史经验如何抽取、压缩、去重和合并；
- 如何检索与当前任务相关的 memory；
- 如何把成功经验重新注入 agent；
- 如何降低重复错误和重复搜索。

这种范式的隐含目标是：

> 从历史中学会“以后应该怎么做”。

这本身合理，但存在一个容易被忽略的问题：历史 trajectory 中观察到的成功通常只说明某种行为是可行的，并不能说明它在其他 plausible realizations 中更优。

## 2. 核心区分：Feasibility != Comparative Evidence

这是当前工作的最核心 conceptual distinction：

    Feasibility Evidence != Comparative Evidence

例如，一个 agent 多次使用策略 A 成功完成任务，可以支持：

    A works under the observed scope.

但不能直接支持：

    A is better than B.
    A is necessary.
    A should be the default realization.
    A is close to optimal.

如果 persistent memory 把 repeated success 直接 consolidate 成默认 guidance，就可能把一个从未真正比较过的 realization 过早固化。

典型例子：

- 历史任务中 agent 按 observation 给出的 receptacle 顺序逐个搜索；
- 最终找到了目标 object，因此 trajectory 成功；
- memory 学到“按 listed order 搜索”；
- 但历史从未比较过 open-surface-first、targeted-source-first 或其他局部搜索方式。

这里的历史证据证明了搜索策略 A 的可行性，却没有解决 A 相对于替代方式的 comparative status。

## 3. 我们关注的问题

因此，我们不只问：

> 历史中有什么成功经验值得复用？

还问：

> 历史中有哪些已经被反复执行、甚至已经被 consolidate 的行为，其 comparative status 实际仍然 unresolved？

更正式地：

给定 pre-update established memory K_pre 和当前完成 trajectory τ，寻找一个局部 incumbent realization r，使得：

1. r 在历史上有 feasibility support；
2. 历史 evidence 尚不足以关闭 r 与 plausible alternative realizations 的比较；
3. 这个 comparison 对未来 policy 有实际影响；
4. 存在机会在未来匹配 context 中以较低风险获得 discriminative evidence。

如果满足这些条件，则不应该立刻把一个替代方案写成 established knowledge，而应该创建一个 future-facing exploratory memory。

## 4. Exploratory Persistent Memory

当前 memory 被概念上分成两类：

    K = K_established ∪ K_exploratory

### 4.1 Established Memory

已经有足够 evidence 支持、可以在适用 scope 中直接复用的经验。

它回答：

> 我们目前有理由相信什么？

### 4.2 Exploratory Memory / H

尚未被验证成知识，而是一个未来值得执行一次的 hypothesis / local probe policy。

它回答：

> 我们目前有哪些重要问题值得在未来匹配 context 中主动获得一次 evidence？

H 的关键性质：

- 来自历史 unresolved comparison，而不是 generic curiosity；
- future-facing；
- grounded；
- local；
- one-shot；
- evidence-seeking；
- 被消费后不会永久作为 exploration instruction 重复执行。

因此本工作的目标不是“让 agent 更爱探索”，而是：

    History-derived Targeted Exploration

## 5. 为什么不是 Generic Exploration

Generic exploration 可以告诉 agent：

> 尝试不同方案。
> 不要总使用默认策略。
> 在有机会时探索 alternative。

但这没有回答：

- 哪个 comparison 值得探索？
- 为什么是现在这个 comparison？
- 它与历史 memory 有什么关系？
- 应该在什么 scope 下激活？
- 什么 evidence 足以更新 memory？

我们的核心信息来源是历史中尚未被关闭的 comparative structure：

    successful history
      -> unresolved comparison
      -> targeted hypothesis
      -> future local experiment

因此正式论文中最关键的 baseline 不是 no-memory，而是：

    targeted history-derived exploration
    vs.
    generic exploration

即后续评测里的 C3 vs C2。

## 6. 预期 Contribution

当前预期 contribution 应分成三层，而不是夸大为一个已经验证完整的 full system。

### 6.1 Conceptual Contribution

指出 persistent memory 中一个常被混淆的问题：

> repeated feasibility evidence 不能自动关闭 comparative uncertainty。

Memory 不应只累计“什么成功过”，也应该显式保留“什么重要 comparison 仍未被回答”。

### 6.2 Method Contribution

提出一种 exploratory persistent memory 机制：

1. 从 completed trajectory 与 pre-update memory 中识别 policy-relevant unresolved comparison；
2. 将其转化为 grounded、future-facing、one-shot local probe policy；
3. 在未来 scope-matched task 中轻量检索、ground、执行；
4. 产生 comparative evidence；
5. 在 episode 后由 conservative reconciler 将真正成立的 evidence 吸收回 established memory。

### 6.3 System / Engineering Contribution

采用：

    heavy offline memory evolution
    +
    lightweight online memory consumption

避免为了 memory 在每个 action step 额外运行复杂 semantic updater / planner。

在线只做：

- retrieval；
- activation；
- grounding；
- acting；
- mechanical runtime bookkeeping；
- evidence logging。

较重的 semantic reasoning 保留在 episode-between offline path。

## 7. 我们目前不应该声称什么

当前 controlled MVP 尚不能支持：

- targeted H 普遍提高 task success；
- C3 已经显著优于 generic exploration；
- automatic retrieval 已经可靠；
- long-term A accumulation 一定提高 future performance；
- full persistent-memory closed loop 已经成立；
- 方法已跨 carrier 泛化。

当前实验真正支持的是：

> 核心机制在受控真实环境中可以被实现、审计和局部验证，已经具备进入 paper-level evaluation 的基础。

## 8. 论文故事的最简表达

可以将整个故事压缩为：

> Existing persistent memory systems mainly reuse what has worked before. However, repeated success provides feasibility evidence, not necessarily comparative evidence that the observed realization is preferable to alternatives.

> We therefore augment established memory with history-derived exploratory memory. After an episode, the system identifies policy-relevant unresolved comparisons in historical behavior and turns them into grounded one-shot local probe policies.

> At future task time, the online system remains lightweight: retrieve a relevant exploratory memory, ground it in the current state, execute the probe, record evidence, consume the hypothesis, and continue the original task. The resulting evidence is reconciled offline into established memory.

最终链路：

    History
      -> Unresolved Comparison
      -> Targeted Future Probe
      -> Comparative Evidence
      -> Memory Evolution
