# 08. 分阶段实验规模、模型角色与预算计划

> 状态：当前实验规模基线（2026-09-18）  
> 用途：把 07 中的 Phase 0–5 路线落实为可执行的数据规模、重复次数、模型角色和升级条件。  
> 原则：先用最小规模判断科学信号，再决定是否扩大；unique task / source-target sequence 是主要统计单元，重复运行属于 nested repetitions。

## 1. 总体原则

不要把：

    20 unique tasks × 3 conditions × 2 repetitions = 120 actor episodes

写成：

    n = 120 independent samples

统计单元优先是：

- unique task；
- source-target sequence；
- memory-update event；
- longitudinal task stream。

repetition 用来估计 actor/environment variance，不增加独立任务数。

模型同样按角色控制，而不是做大矩阵：

### Online Actor

负责真实 target-time acting、H grounding、probe execution 和 task continuation。

### Offline Semantic Backbone

负责 Stage1 / A / B / C 等非 action-latency-critical semantic reasoning。

### Retrieval Model

仅 Phase 4 以后加入 embedding / lightweight rerank。

Pilot 默认：

    1 main actor
    + 1 offline semantic backbone

二者可以是同一个模型，也可以不同，但角色和调用成本必须分开记录。

只有前一 scientific gate 有稳定信号后，才加入：

    1 secondary actor backbone

做 robustness。不要把 actor × offline model 做全笛卡尔积。

---

## 2. Phase 0 — Mechanism Sanity

状态：基本完成，不再扩样本。

当前已有：

- 11 curated B cases；
- 少量 C/H synthesis；
- same-task / cross-task online sanity；
- action-index / pairing / lifecycle checks。

后续仅在新的 conceptual bug 出现时补 targeted regression case。

### 模型

保持已有 MVP 记录即可，不新增 multi-model matrix。

---

## 3. Benchmark Admission

从现在开始，但不属于正式 broad run。

### 候选数量

    2–3 benchmark candidates

### 每个 benchmark

先做：

    <= 10 real-case admission audit

检查：

- same-family / repeated-task structure；
- plausible local alternatives；
- native objective；
- memory authority；
- observability；
- pairing/randomization；
- base actor reliability；
- cost；
- longitudinal feasibility。

如果需要 actor screening，优先只跑：

    10–20 no-H base tasks / candidate

不做 C1/C2/C3。

### 进入 Phase 1 的最低要求

至少：

- 1 个 lead benchmark/carrier 通过 admission；
- 另外 1–2 个候选有明确 memo；
- lead benchmark 的 target-pool predicate 可以在不看 hidden outcome 的情况下定义。

---

## 4. Phase 1 — Targeting Value

核心问题：

    C3 history-derived targeted exploration
    vs.
    C2 fair structured generic exploration

### 4.1 Pilot 规模

第一轮只用一个 lead benchmark。

建议：

    5–8 source/H families
    20–30 unique scope-matched target tasks
    C1 / C2 / C3
    2 repetitions / condition

actor episode 数约：

\[
20\text{–}30
\times 3
\times 2
=
120\text{–}180
\]

unique scientific units 仍然只有：

    20–30 targets

不是 120–180。

### 4.2 Source/H family 要求

不要让 20–30 个 target 全来自一个 surface-first H。

pilot 应尽量覆盖：

    5–8 distinct unresolved-comparison families

如果 lead benchmark 实际只能自然支持 1–2 类 comparison，应如实记录，不人为制造 family。

### 4.3 Offline calls

B/C 不需要随每个 target 重跑。

对于固定 source history / K*：

- B diagnosis 通常每 source family 一次；
- C3 H synthesis 通常每 OPEN source 一次；
- C2 generic H 的生成方式必须在 pilot 前冻结；
- target actor 才是主要调用量。

### 4.4 Main actor

Pilot：

    1 main actor backbone

进入 pilot 前先做 base reliability screen。

不要求第一轮同时跑 weak actor。

如果 Phase 1 主结果有稳定信号，再加入：

    1 secondary actor

验证 effect 是否依赖单一 backbone。

### 4.5 Offline semantic model

Pilot：

    1 offline semantic backbone

B/C 必须固定。

如果 C2/C3 差异只在某个 offline model 上出现，再考虑第二个 offline backbone；不要预先扩矩阵。

### 4.6 Phase 1 expansion

若 20–30 target pilot 有清晰信号，再扩到：

    40–60 unique targets

仍先保持一个 benchmark 和一个 main actor，确认 effect size / variance。

### 4.7 Paper-scale 预估

只有 Phase 1 pilot + expansion 都支持继续时，才考虑：

    50–100 unique targets / benchmark
    2–3 benchmarks
    2–3 repetitions based on pilot variance

这可能对应每 benchmark 约：

\[
50\text{–}100
\times 3
\times 2\text{–}3
=
300\text{–}900
\]

actor episodes。

因此 publication-scale 不能作为第一轮预算。

---

## 5. Phase 2 — Native Cold-Start Memory Formation

核心问题：

    raw trajectory
    -> Stage1
    -> A
    -> established memory / Semantic Concepts

是否能够保留 evidence 和 comparative uncertainty。

### 5.1 Pilot 数据

建议：

    30–50 raw trajectories

其中人工深度 audit：

    15–20 trajectories

人工标签重点不是“写一份完美 memory”，而是：

- important experience；
- observed behavior；
- outcome / cost；
- justified scope；
- provenance；
- what is feasible；
- what is NOT comparatively established。

### 5.2 Degradation subset

对：

    15–20 audited trajectories

比较：

    manually reviewed clean evidence
    vs.
    Stage1+A-produced evidence/memory

再送入 B/C，检查 downstream degradation。

### 5.3 模型

主要：

    1 offline semantic backbone

这一阶段可以不增加新的 actor model。

如果 Stage1/A 质量明显不足，可以用：

    1 stronger diagnostic offline model

做 attribution；该模型不是自动加入 paper matrix。

### 5.4 Paper-scale 预估

若 pilot 通过：

    100–200 trajectories
    30–50 human-audited subset
    2–3 benchmark families / carriers

但不要求所有 trajectory 人工逐条 gold 标注。

---

## 6. Phase 3 — One-Step Memory Evolution Value

统计单元改为：

    memory-update event

而不是单条 actor step。

### 6.1 Pilot

建议：

    10–15 valid update events

每个 update：

    3–5 held-out scope-matched targets

held-out 比较：

    K_t
    vs.
    K_{t+1}

第一版建议：

    2 repetitions / memory condition

actor evaluation episode 数大约：

\[
10\text{–}15
\times 3\text{–}5
\times 2
\times 2
=
120\text{–}300
\]

另加 10–15 个产生 update 的 exploratory episodes。

### 6.2 模型

    1 main actor
    + 1 offline semantic backbone

与 Phase 1/2 尽量保持一致。

### 6.3 Paper-scale 预估

若 pilot 通过：

    30–50 update events
    × 3–5 held-out targets

实际 actor episodes可能进入：

    360–1000+

因此 Phase 3 之前必须已有明确 effect signal。

---

## 7. Phase 4 — Automatic Retrieval / Activation

retrieval 数据可以比在线环境任务大，因为大部分是离线 query。

### 7.1 Retrieval pilot

建议：

    100–200 retrieval queries

每个 query 尽量包含：

- relevant H；
- hard negative H；
- unrelated H。

测：

- Recall@k；
- precision；
- false activation；
- miss；
- context cost。

### 7.2 End-to-end retrieval pilot

建议：

    30–50 unique targets

比较：

    C3_oracle-match
    vs.
    C3_auto-retrieval

每 condition：

    2 repetitions

约：

    120–200 actor episodes

### 7.3 模型

此时增加：

    1 embedding / lightweight retrieval model

总角色：

    main actor
    offline semantic backbone
    retrieval model

reranker 若需要，优先轻量，不加入新的重型 planner。

### 7.4 Paper-scale 预估

    500+ retrieval queries
    100+ end-to-end targets

只有 oracle H value 已经明确后才值得投入。

---

## 8. Phase 5 — Full Native Cold-Start Longitudinal System

这是最昂贵阶段。

### 8.1 Longitudinal pilot

先做：

    3 task-order seeds / streams
    15–20 training episodes / stream

即：

    45–60 sequential learning episodes / system condition

evaluation checkpoints 例如：

    t = 0, 5, 10, 20

每个 checkpoint：

    10–15 frozen held-out probe tasks

如果先比较两个 full-system conditions，例如：

    baseline
    ours

一个中等 pilot：

    3 streams
    × 4 checkpoints
    × 15 held-out tasks
    × 2 conditions
    = 360 held-out evaluation episodes

再加约：

    90–120 longitudinal training episodes

总量已约：

    450–480 actor episodes

所以 Phase 5 不适合用于“碰运气找信号”。

### 8.2 Paper-scale

只有 Phase 1–4 均有清楚结果后再考虑：

    >= 5 task-order seeds
    30–50 training episodes / stream
    2–3 benchmarks
    2–3 system conditions

加 checkpoint evaluation 后很容易进入：

    1000–3000+ actor episodes

量级。

最终样本仍应由 pilot effect size / variance 决定，不把这里写成固定统计承诺。

---

## 9. 模型策略汇总

### Phase 1

    main actor: 1
    offline semantic model: 1

### Phase 2

    offline semantic model: 1
    optional diagnostic stronger model: at most 1

### Phase 3

    main actor: 1
    offline semantic model: 1

### Phase 4

    main actor: 1
    offline semantic model: 1
    retrieval/embedding model: 1

### Phase 5 主实验

    main actor: 1
    offline semantic model: 1
    retrieval model: 1

### Robustness

主结果明确后再加入：

    secondary actor: 1

原则上最终 paper 不需要：

    4 actors × 3 offline models × 3 retrievers

推荐最终最多形成：

    2 actor backbones
    + 1 main offline semantic backbone
    + 1 retrieval model

必要时第二 offline backbone只做 targeted sensitivity analysis。

---

## 10. API / 本地模型策略

模型供应方式不是科学变量。

同一个 comparison 中：

- C1/C2/C3 actor 必须同一 backbone/config；
- B/C offline model 必须同一 backbone/config；
- temperature / thinking / max tokens 应固定；
- API 与 local 不应因 condition 不同而改变。

Pilot 优先：

- 可靠、低成本 API actor；
- offline semantic model可以更强，因为不在 online latency critical path；
- local model只有在可靠性和复现实验成本更合适时使用。

最终具体模型在 Phase 1 actor-screening 后冻结。

---

## 11. 成本控制与 Stop Rule

每阶段只预算到下一 gate。

### Phase 1 readiness

不启动完整 120–180 episode paid matrix，直到：

- fair C2 定义冻结；
- K* 来源冻结；
- target-pool predicate 冻结；
- lead benchmark admitted；
- main actor 通过 base reliability；
- artifacts / telemetry dry-run 通过。

### Phase 1 pilot

最多先做：

    20–30 unique targets
    × C1/C2/C3
    × 2 reps

如果没有 targeting signal，停止。

### Phase 2 / 3

只有 Phase 1 有值得继续的信号才投入。

### Phase 5

不使用上千 episode 去“寻找”一个前面没有出现过的 effect。

---

## 12. 当前下一实现周期的规模

coding-agent 下一轮不直接执行 full Phase 1 paid pilot。

当前 readiness cycle 只需要准备：

1. fair C2 candidate specification；
2. fixed warm-start K* provenance/specification；
3. public-only target-pool registry / sampling protocol；
4. 2–3 benchmark admission memos；
5. main-actor base reliability screening plan；
6. C1/C2/C3 runner/config scaffolding；
7. dry-run / fake-transport tests；
8. token/cost projection；
9. STOP，返回 researcher review。

研究者确认后，下一 cycle 才运行：

    20–30 unique targets
    × 3 conditions
    × 2 reps
