# 07. 分阶段实验验证路线：从 Controlled Mechanism 到 Full Cold-Start System

> 状态：当前实验推进基线（2026-09-18）  
> 分支：`exp/minimal-exploratory-memory-validation`  
> 用途：规定后续实验按什么顺序增加真实系统复杂度、什么时候开始使用真实 benchmark distribution、什么时候才实现和评测完整 closed-loop system。

## 1. 总原则

当前核心方法已经完成受控 mechanism sanity，但尚未完成 paper-level contribution validation。

后续不采用：

    先实现全部 Stage1 / A / B / C / retrieval / closed-loop
    -> 再一次性跑 benchmark

而采用：

    isolate one scientific question
    -> run the smallest defensible experiment
    -> pass / stop
    -> only then restore the next source of system complexity

原因是最终 end-to-end effect 同时受：

- memory formation；
- B diagnosis；
- C/H quality；
- exploration targeting；
- actor reliability；
- retrieval / activation；
- A reconciliation；
- longitudinal history divergence；

影响。过早合并会使 negative result 无法归因。

## 2. 方法初始化与实验初始化必须分开

方法原生 cold start 定义为：

\[
\boxed{
\begin{aligned}
G_0 &= G_{tool} \\
K_0^{established} &= \varnothing \\
K_0^{exploratory} &= \varnothing \\
\mathcal T_0 &= \varnothing
\end{aligned}}
\]

其中：

- `G_tool` 只包含环境明确给出的 Tool / Operation / I/O / stable containment / description / provenance；
- 不预初始化 Strategy、Semantic Concept、Context family、subgoal taxonomy 或完整 action/strategy space；
- Semantic Concept 与 established memory 从第一条真实 trajectory 开始，经 Stage1 -> A 逐渐形成；
- exploratory memory 初始为空，只能由已有经验上的 B/C 生成。

但是，前几阶段实验允许使用固定 warm-start snapshot：

\[
K_{0,MVP}^{established}=K^*
\]

它只用于控制变量，不属于方法 native initialization，也不能被当作 full-system result。

## 3. Phase 0 — Mechanism Sanity

### 核心问题

    Can the intended one-iteration mechanism be implemented
    without obvious leakage or harness confounds?

### 当前状态

基本完成。

已经有 controlled qualitative support：

- B/C responsibility boundary；
- B OPEN/NONE 基本 discrimination；
- local fact-only C synthesis；
- source grounding / future grounding separation；
- H target-time grounding；
- H behavioral authority；
- one-shot persistent/runtime lifecycle；
- positive / negative evidence logging；
- E1-only A reconciliation；
- action-index interface；
- mechanical probe_runtime_state；
- actual E0/E1 pairing proof。

### 本阶段不支持

- C3 > C2；
- natural-distribution H usefulness；
- Stage1 / A native memory formation；
- automatic retrieval；
- long-term memory improvement；
- full closed-loop claim。

### Stop rule

除非新的人工 review 找到明确概念错误，不再通过 patch 少量 controlled case 修改 B/C/H/A。

---

## 4. Phase 1 — Targeting Value：Controlled Warm-Start Contribution Test

这是下一阶段最优先的实验。

### 4.1 科学问题

给定一个固定、合理的 established-memory snapshot：

> History-derived targeted exploration 是否比同等 authority 的 generic exploration 提供额外价值？

核心 comparison：

\[
\boxed{C3\;vs.\;C2}
\]

辅助条件：

### C1 — Established Only

    fixed established memory K*

### C2 — Established + Generic Structured Exploration

与 C3 尽量共享：

- H object/interface；
- one-shot authority；
- lifecycle；
- probe status；
- probe_runtime_state；
- actor；
- step cap；
- approximate context/token budget。

只移除：

    history-derived unresolved-comparison targeting information

### C3 — Established + History-derived Targeted Exploration

    K*
    + B/C-derived exploratory H

### 4.2 本阶段继续 bypass 什么

暂时 bypass：

- production Stage1；
- native cold-start memory construction；
- automatic H retrieval；
- full longitudinal A accumulation。

优先使用 oracle / structural scope match，隔离 H content + execution quality。

### 4.3 Benchmark 在这里扮演什么角色

从 Phase 1 开始，target 必须来自真实 benchmark task distribution，而不是只选择 researcher 已知 positive 的 target。

因此这是：

    benchmark-backed controlled evaluation

不是：

    full benchmark / full system evaluation

target pool 必须在看 target outcome 前按公开结构条件预注册。例如某条 H 的 scope 由 public context 定义后，满足 scope 的 target 全部进入 pool，包括：

- H helpful；
- H neutral；
- H harmful；
- base actor 本来就选择同路线；
- negative / ambiguous evidence。

禁止根据 hidden target location、oracle answer 或运行结果筛 target。

### 4.4 Actor reliability gate

正式 Phase 1 pilot 前，对候选 main actor 做 no-H base reliability screening。

如果 base actor 在 admitted target pool 上大量：

- step-cap；
- semantic loop；
- task failure；

则先更换/筛选 actor，而不是用 memory experiment 解释这些失败。

C1/C2/C3 必须共享同一个 actor。

### 4.5 主要指标

End-to-end：

- task success / reward；
- steps / tool calls；
- tokens / API cost；
- online latency。

Mechanism：

- H activation；
- incremental behavioral effect；
- productive-evidence rate；
- probe-induced failure；
- downstream completion；
- abort / recovery。

核心 paired/statistical quantity可以包括：

\[
\Delta cost = cost(C3)-cost(C2)
\]

以及 C3 相对 C1 的 incremental effect。

### 4.6 Phase 1 stop rule

如果在公平 C2 和自然 scope-matched target distribution 下：

    C3 ~= C2

且没有稳定 mechanism advantage，

则先停止向 full system 扩展，重新审查：

- history-derived targeting 是否真的提供额外信息；
- C2 是否已经能够独立恢复同样 alternative；
- benchmark 是否对 target information 不敏感；
- H representation 是否过泛。

不要用 Stage1、retrieval 或更复杂 controller 掩盖这一 negative result。

### 4.7 C2b 的位置

C2b：

    target-time on-demand local exploration synthesis

是重要 strong baseline，但不要求在第一次 Phase 1 pilot 同时实现。

推荐：

    C1 vs C2 vs C3
    -> 若 C3 有稳定信号
    -> 再加入 C2b

C2b 用来挑战：

> 为什么 unresolved comparison 必须持久化，而不是 target 到来时现场重新生成？

---

## 5. Benchmark Admission — 从现在开始，但不等于 Broad Run

Benchmark admission 与 Phase 1 准备并行进行。

目标是录取 2–3 个真正适合后续层级实验的 benchmark，而不是因为知名度直接使用。

每个候选先做 <=10 个 real-case audit，检查：

- repeated / same-family task structure；
- memory 对 future behavior 有真实 authority；
- multiple plausible local realizations；
- objective 能区分好坏，而不只是 researcher preference；
- trajectory / tool call 可观测；
- replayable 或有 defensible randomized protocol；
- actor base reliability；
- positive / negative / ambiguous evidence；
- online/offline cost；
- 是否支持后续 longitudinal sequence。

### Benchmark 使用层级

**Phase 1**

真实 benchmark distribution，用于 controlled warm-start C1/C2/C3。

**Phase 2**

真实 benchmark trajectories，用于 native memory formation audit。

**Phase 3**

开始形成 method-level benchmark claim：memory update 是否带来 held-out benefit。

**Phase 5**

才是 native cold-start full-system / publication-scale benchmark evaluation。

---

## 6. Phase 2 — Native Cold-Start Memory Formation

只有 Phase 1 证明 targeted exploration 本身有值得继续的信号后，才恢复 Stage1 + A 的上游复杂度。

### 6.1 科学问题

从方法原生 cold start：

\[
G_0=G_{tool},\quad
K_0^{est}=\varnothing,\quad
K_0^{exp}=\varnothing,\quad
\mathcal T_0=\varnothing
\]

出发：

> Raw trajectory 经 Stage1 + A 后，能否形成可信、可用、保留 uncertainty 的 established memory / semantic structure？

### 6.2 第一版不需要 full online loop

先用一小批真实 completed trajectories：

    raw trajectory
    -> Stage1
    -> Candidate Experience
    -> A
    -> K_established / Semantic Concepts

人工 audit 一个 labelled subset。

### 6.3 重点不是普通摘要准确率

必须检查：

- behavior / outcome / cost 是否保留；
- scope 是否合理；
- provenance 是否完整；
- Semantic Concept 是否从 evidence 中产生；
- merge/dedup 是否损失关键条件；
- feasibility 是否被错误升级成 preferred/default；
- comparative uncertainty 是否被过早压平。

一个关键 failure：

    A succeeded
    -> "A is the preferred strategy"

而 evidence 实际只支持：

    A is feasible under observed scope

### 6.4 Degradation experiment

比较：

    B/C on manually reviewed clean evidence
    vs.
    B/C on Stage1+A-produced memory/evidence

测：

- B OPEN agreement；
- incumbent segment quality；
- Functional Contract quality；
- C usable-probe rate；
- H content degradation。

这样能量化：

    idealized downstream quality
    -> native upstream quality loss

### 6.5 Phase 2 stop rule

如果 Stage1+A 大量：

- 丢失关键 experience；
- 过度 generalize；
- 把 feasibility 固化为 preference；
- 产生 unusable semantic concepts；

则先修 upstream memory formation，不进入 retrieval/full-loop。

---

## 7. Phase 3 — One-Step Memory Evolution Value

在 Phase 1 和 Phase 2 都通过后，第一次闭合：

\[
K_t
\rightarrow B
\rightarrow C/H
\rightarrow E
\rightarrow A
\rightarrow K_{t+1}
\]

### 7.1 科学问题

> Exploratory episode 获得的新 evidence，经过 A 吸收后，是否真的形成了更有用的 established memory？

### 7.2 关键实验

构造同一 pre-update memory：

    K_t

运行一次真实 exploratory episode，得到：

    K_{t+1}

然后在新的 held-out task pool 上比较：

\[
Actor(K_t)
\quad vs.\quad
Actor(K_{t+1})
\]

为了隔离 established-memory update 的价值，held-out evaluation 第一版可以不再提供 active H。

### 7.3 这里开始形成什么 claim

如果 K_{t+1} 在 held-out tasks 上稳定优于 K_t，才真正支持：

\[
\boxed{
Exploration
\rightarrow Evidence
\rightarrow Memory Evolution
\rightarrow Later-task Benefit
}
\]

而不只是：

    Exploration -> interesting trajectory

### 7.4 Phase 3 stop rule

如果 H 能产生 evidence，但 A update：

- 没有 behavioral effect；
- 过度泛化；
- 在 held-out tasks 上无收益或伤害；
- memory churn 大但 utility 不升；

则先修 A / memory materialization，不进入 full retrieval/longitudinal system。

---

## 8. Phase 4 — Automatic Retrieval / Activation

前面先用 oracle / structural match 隔离 H quality。

Phase 4 才加入：

    automatic retrieval
    + scope activation

### 8.1 核心比较

\[
C3_{oracle-match}
\quad vs.\quad
C3_{auto-retrieval}
\]

定义：

\[
Retrieval\ Gap
=
Performance(C3_{oracle})
-
Performance(C3_{auto})
\]

### 8.2 Failure attribution

至少区分：

- retrieval miss；
- wrong H retrieval；
- wrong activation；
- correct retrieval but bad target-time grounding；
- correct H but actor execution failure。

### 8.3 原则

retrieval 可以：

    cheap recall
    -> small top-k
    -> light rerank/selection

不要重新变成重型 online planning agent。

---

## 9. Phase 5 — Full Native Cold-Start Longitudinal System

这是最终完整方案和正式 full-system benchmark evaluation。

### 9.1 起点

必须从方法原生 cold start 开始：

\[
\boxed{
G_0=G_{tool},\quad
K_0^{est}=\varnothing,\quad
K_0^{exp}=\varnothing,\quad
\mathcal T_0=\varnothing
}
\]

不是人工 seed strategy memory。

### 9.2 完整 loop

\[
Task_t
\rightarrow Online\ Retrieval/Activation/Acting
\rightarrow \tau_t
\]

然后：

\[
\tau_t
\xrightarrow{Stage1}
M_t^{cand}
\]

并行：

\[
M_t^{cand}
\rightarrow A
\rightarrow established\ update
\]

以及：

\[
(M_t^{cand},K_{pre})
\rightarrow B
\rightarrow C
\rightarrow H
\]

统一 materialize：

\[
K_{t+1}
\]

继续：

\[
K_0\rightarrow K_1\rightarrow K_2\rightarrow\cdots
\]

### 9.3 主要纵向性质

周期性在 frozen held-out probe pool 上测：

\[
J(K_t)
\]

同时报告：

- held-out task performance；
- B OPEN rate；
- C CREATE / usable-probe rate；
- productive-H rate；
- A update rate；
- memory growth；
- memory churn；
- retrieval context cost；
- harmful exploration rate；
- later-task benefit。

理想性质不是每 episode 单调变好，而是分布意义上：

\[
Performance(t)\uparrow
\]

同时后期：

\[
B\text{-OPEN}(t)\downarrow
\]

\[
A\text{-Update}(t)\downarrow
\]

\[
Memory\ Churn(t)\downarrow
\]

最终形成在 observed task distribution / proposal space 下相对稳定的 memory。

不能把这表述成 guaranteed global optimum。

---

## 10. Frozen-History 与 Closed-Loop 的结论边界

### Frozen-history / Controlled intervention

主要承担 Phase 1–4 的局部因果与 attribution claim。

所有条件尽量共享：

- history；
- K_pre；
- actor；
- target；
- environment；
- step cap。

只改变 intervention。

### Full Closed-loop

Phase 5 承担长期 system claim。

不同 condition 的历史会逐渐分叉，因此：

> Phase 5 的差异不能被重新解释成单个 H 的局部 causal effect。

两者必须分开报告。

---

## 11. 当前实现优先级

下一实现周期建议只做支撑 Phase 1 的最小增量：

1. 定义公平 C2；
2. 做 benchmark admission audit；
3. 筛 main actor；
4. 固定 Phase 1 target-pool sampling protocol；
5. 实现 C1/C2/C3 Frozen-history pilot runner；
6. 保留完整 artifact / telemetry / failure attribution。

当前不应同时实现：

- production Stage1；
- automatic retrieval；
- longitudinal runner；
- broad multi-benchmark matrix；
- C2b；
- publication-scale statistics。

---

## 12. 阶段 Gate 总结

### Gate 0 — Mechanism

    Can B/C/H/Online/A operate cleanly?

状态：基本通过。

### Gate 1 — Targeting

    Does C3 outperform a fair C2 on natural scope-matched benchmark targets?

未验证；当前最高优先级。

### Gate 2 — Native Formation

    Can Stage1+A grow useful established memory from native cold start
    without destroying comparative uncertainty?

未验证。

### Gate 3 — Memory Evolution

    Does K_{t+1} improve later behavior relative to K_t?

未验证。

### Gate 4 — Retrieval

    How much value survives automatic retrieval/activation?

未验证。

### Gate 5 — Longitudinal Full System

    Does the complete cold-start system improve and stabilize over task streams?

未验证。

---

## 13. 一句话路线

后续默认顺序：

    Mechanism sanity
    -> Targeting value
    -> Native memory formation
    -> One-step memory-evolution value
    -> Automatic retrieval
    -> Full cold-start longitudinal benchmark

核心纪律：

> Do not restore a source of system complexity until the previous scientific gate has produced interpretable evidence.


## 14. 规模与模型预算

每个阶段的 pilot / paper-scale 数据量、repetition、模型角色和 actor-episode 数量级不在本文重复展开，统一见：

    docs/current_state/08_experiment_scale_and_model_budget.md

当前 Phase 1 readiness 不直接执行未来的 120–180 episode paid pilot；先冻结 fair C2、K* provenance、target-pool sampling、lead benchmark 与 main actor，再启动 paid matrix。
