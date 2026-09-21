# 09. Project Master Handoff：背景、方法、实验路线与当前进展

> **2026-09-21 active cycle:** Phase 1B is frozen as `READY_FOR_SCALE_WITH_KNOWN_LIMITATIONS`. The active cycle is **Phase 1C — Flash Scale-Aware Hypothesis Pilot**. Read `docs/102_phase1c_flash_scale_hypothesis_pilot_plan.md`, `docs/38_exploratory_memory_lifecycle.md`, `docs/37_method_structural_initialization.md`, and current `AGENTS.md`. The pilot is 32 fresh tasks, G vs T, Flash-only; Max is deferred until researcher review.

> **2026-09-20 protocol reset:** the S1C development line ended with `STOP_CURRENT_MINIMALIST_ACTOR_FORMULATION`. For the active Phase 1A protocol, read `docs/83_phase1a_controlled_targeting_fast_track_plan.md` and current `AGENTS.md`. The historical Gate B1/B1-R autonomous-actor path below is retained as evidence but is no longer the prerequisite for the versioned controlled-targeting-v2 experiment.

> 状态：当前项目单一接手入口（2026-09-21，Phase 1C — Flash Scale-Aware Hypothesis Pilot）
> Branch：exp/minimal-exploratory-memory-validation
> Frozen Phase 1B baseline：c8daa67ba9d9d6257d65e446b437d362e60abc61
> 适用对象：新研究者、新 coding-agent、新 reviewer、组会参与者。
> 原则：本文只写当前共识与当前证据边界；历史设计演化请查顶层 docs/00–69。

---

## 0. 先读这一页能知道什么

读完本文，应能回答：

1. 我们到底在解决什么 scientific problem？
2. 为什么 Feasibility Evidence != Comparative Evidence 是核心？
3. Established Memory、Exploratory Memory、Graph、Stage1/A/B/C/H 各自是什么？
4. 方法原生 cold start 到底如何初始化？
5. 为什么当前 Phase 1 故意使用 warm-start K*，但它不是方法初始化？
6. 当前已经验证了什么、没有验证什么？
7. 为什么正式贡献比较是 C3 vs C2，而不是 C3 vs C0？
8. benchmark 在什么时候进入、完整系统什么时候才实现？
9. 当前 Phase 1A 到底测什么，claim 能有多大？
10. 下一轮参与者应该 review 什么，而不是重新打开什么？

快速接手：

    本文
    -> 10_current_review_protocol.md
    -> AGENTS.md

若要深入方法，再读 current_state/01–08。

---

# 1. 研究背景与问题定义

## 1.1 Persistent memory 的默认范式

Persistent agent memory 通常希望把历史经验压缩成未来可复用知识：

    Trajectory
      -> Extract / Summarize / Consolidate
      -> Persistent Memory
      -> Future Reuse

典型优化目标包括：

- 从成功历史提取 procedure / workflow / rule；
- 减少重复搜索、重复错误和重复推理；
- 在未来类似任务中直接复用已学经验；
- 让 memory 随 episode 逐步更新。

这个方向合理，但有一个容易被忽略的 epistemic gap：

\[
\boxed{\text{Feasibility Evidence} \neq \text{Comparative Evidence}}
\]

一条 trajectory 中策略 A 成功，只能证明：

    A works under the observed scope.

它不能自动证明：

    A > B
    A is necessary
    A should be the default
    A is near-optimal

如果 memory 系统把“成功过”不断压缩成“以后默认这么做”，就可能把一个从未真正比较过的 realization 过早固化。

## 1.2 我们真正关心的问题

本项目不只问：

> 什么历史经验值得保存？

还问：

> 哪些已经被历史采用、甚至已经写入 established memory 的行为，其 comparative status 其实仍然没有被 evidence 关闭？

给定 pre-update established memory K_pre 和 completed trajectory tau_t，我们希望发现一个 local incumbent realization r，使得：

1. r 有 feasibility support；
2. 相对 plausible alternatives 的 comparative support 不足；
3. 这个 comparison 对未来 policy 有实际意义；
4. 未来存在低风险、局部的 evidence-acquisition opportunity。

如果满足，就不应该直接把某个替代方案写成“真知识”，而应该形成一个 future-facing one-shot experiment。

---

# 2. 核心方法概念

## 2.1 两类 memory

\[
K_t = K_t^{established} \cup K_t^{exploratory}
\]

### Established Memory

表示当前 evidence 已支持、在相应 scope 中可以直接复用的 guidance。

它回答：

> What do we currently have reason to reuse?

### Exploratory Memory / H

不是 established knowledge，而是：

> What unresolved, policy-relevant question should be tested once in a future matching context?

H 的关键性质：

- history-derived；
- local；
- future-facing；
- capability-grounded；
- adaptive；
- one-shot；
- evidence-seeking；
- consumed 后不能继续当长期探索指令重复执行。

所以我们研究的不是 generic curiosity，而是：

\[
\boxed{\text{History-derived Targeted Exploration}}
\]

---

# 3. 方法原生结构初始化

正式 method-native cold start 当前定义为：

\[
\boxed{
\begin{aligned}
G_0 &= G_{\text{tool}} \\
K_0^{established} &= \varnothing \\
K_0^{exploratory} &= \\varnothing \\
\\mathcal E_0^{history} &= \\varnothing \\
\\mathcal T_0 &= \\varnothing
\end{aligned}}
\]

核心原则：

> Fix what the environment defines; learn what experience gives meaning to.

## 3.1 启动时允许存在什么

G_tool 只由环境显式 Tool/API schema 确定性构造，可包含：

- Tool identity；
- Operation/API identity；
- Tool→Operation containment；
- 显式 input / parameter；
- 显式 output / return；
- 稳定 description；
- stable ID；
- environment provenance。

它只回答：

> Agent objectively can call what?

## 3.2 启动时禁止预构造什么

不能预先枚举：

- Strategy / Procedure concepts；
- Semantic Concepts；
- Context families；
- subgoal taxonomy；
- 完整 action / strategy space；
- alternative_to / preferable_to / dominates；
- should_explore；
- 任何跨 trajectory 才有意义的 semantic relation。

Semantic Concept、Strategy meaning、Context abstraction 从第一条真实 trajectory 起，经 Stage1→A 逐渐长出来。

因此 Graph 的初始非空，只来自 stable tool/capability scaffold，不代表我们预设 task ontology。

---

# 4. 完整方法架构

总体设计：

\[
\boxed{
\text{Heavy Offline / Between-Episode Memory Evolution}
+
\text{Lightweight Online Memory Consumption}
}
\]

原则：

> Online writes facts; Offline writes knowledge.

完整 offline 不是简单串行：

    trajectory -> Stage1 -> A -> B -> C

因为 B/C 的 historical side 必须看 pre-update memory，不能让当前 trajectory 先经 A 写入，再伪装成“历史 evidence”。

正确逻辑：

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

最后统一 materialize：

\[
K_{t+1}
=
\mathrm{Apply}(A)
+
H_{\text{new}}
+
\text{consolidation/index refresh}
\]

---

# 5. 各模块职责

## 5.1 Stage 1 — Candidate Experience Extraction

目标：

    raw trajectory -> candidate experiences / evidence

负责：

- trajectory parsing；
- candidate experience extraction；
- provenance；
- 保留 observed behavior / outcome / cost / scope cues。

不负责：

- 判定 unresolved comparison；
- 生成 H；
- 替 A 决定 memory update；
- 用 evaluator/oracle 给 semantic label。

Stage1 不能把：

    A succeeded

自动压缩成：

    A is preferred

它应保留 comparative uncertainty。

## 5.2 A — Established Memory Reconciliation

核心问题：

> What does this new actual evidence change about what we already know?

可能输出：

- ADD；
- REFINE；
- SPECIALIZE；
- MERGE；
- NO_CHANGE。

A 必须 conservative、evidence-bound、scope-limited。

禁止输入：

- E0 reference；
- researcher counterfactual；
- evaluator label；
- oracle target location；
- expected conclusion。

A 当前只允许看真实发生的 E1 evidence。

## 5.3 B — Open Comparative Question Diagnosis

核心问题：

> Which incumbent comparison is worth opening?

B 负责：

- 找 local incumbent behavior；
- 判断 feasibility support；
- 判断 comparative support 是否不足；
- 判断 policy relevance；
- 输出 OPEN / NONE；
- 输出 Functional Contract。

B 不负责提出 concrete alternative。

这条边界已经经过早期失败实验验证：让 B 同时找问题和想替代方案，会导致职责漂移。

## 5.4 Functional Contract

B→C 的局部替换边界：

    available_state
    local_function
    required_downstream_state
    constraints

它描述：

> 哪个局部功能允许被换一种 realization，同时下游必须保留什么。

它不应该提前告诉 C：

> 去 surface first。

## 5.5 C — Exploratory Memory Synthesis

核心问题：

> What grounded local test should be tried once?

输入：

- B diagnosis；
- Functional Contract；
- local public facts；
- relevant established memory；
- capabilities/tools。

C 不应重新看到完整 completed source trajectory，更不能看到 source 最终 hidden answer。

原则：

> facts, not candidate solution

输出不是 future open-loop action list，而是 adaptive local probe policy。

## 5.6 H — Exploratory Memory

H 的 future-facing 内容通常包含：

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

另有 creation-time：

    source_grounding
    provenance

但 future target actor 不应该消费 exact source grounding。

---

# 6. Source Grounding 与 Future Grounding

C 创建 H 时，可以保存 source-specific grounding，例如：

    go to countertop_1

它的意义只是：

> 证明 proposal 在 source entry state 中不是凭空想象。

Future-facing H 应抽象成：

    try an available open surface before closed storage

未来 target 再根据真实 observation / admissible actions ground 成具体实体。

所以：

    source_grounding = creation-time provenance
    future_grounding = target-time actor responsibility

---

# 7. H Lifecycle

Persistent H：

    active
      -> first real activation
      -> consumed

同一个 episode 中保留 runtime copy：

    ACTIVE
      -> EVIDENCE_OBTAINED / ABORTED
      -> remove runtime H
      -> continue original task

注意：

\[
\text{EVIDENCE\_OBTAINED}
\neq
\text{hypothesis true}
\]

它更准确表示：

    PROBE_EVIDENCE_READY

Consumed 也不等于 hypothesis 被证实或证伪，只表示这条 one-shot instruction 不再进入未来 active pool。

### Exploration History / Archive

被实际激活的 H 同时进入离线 `\\mathcal E^{history}`。Archive 不进入在线 recall，只在未来 B=OPEN 后向 C 暴露少量相关、已测试 exploratory hypotheses，帮助避免重复实验。是否等价、是否值得 materially different retest 仍由 C 语义判断；B 当前不读取 archive。详见 `docs/38_exploratory_memory_lifecycle.md`。

---

# 8. Online 运行边界

Online 目标保持轻：

    task/current state
      -> retrieve
      -> activate
      -> target-time ground
      -> act
      -> observe/log
      -> repeat

Actor 每步输入：

- task；
- current public state；
- ordered admissible actions；
- relevant established memory；
- active H；
- executed history；
- mechanical probe runtime facts。

Actor 输出：

    action_index
    probe_status

代码只负责：

    resolved_action = admissible_actions[action_index]

不负责 semantic next-action selection。

---

# 9. Graph 的当前定位

Graph 不是完整 search-space planner。

当前职责：

- stable Tool / Capability grounding；
- Semantic Concept organization；
- memory–concept–trajectory provenance；
- hard relations；
- retrieval / local expansion support。

Exploration 主要依赖：

\[
\text{Semantic Memory}
+
\text{Local Comparative Diagnosis}
+
\text{Capability-grounded Counterfactual Generation}
\]

而不是预先构造完整 strategy graph。

---

# 10. 长期系统应如何演化

系统不是：

    A successful
    -> discover B
    -> permanently replace A with B

更准确是：

\[
K_t
\rightarrow
\text{current incumbent}
\rightarrow
\text{unresolved comparison}
\rightarrow
H
\rightarrow
\text{future evidence}
\rightarrow
K_{t+1}
\]

然后继续。

所以长期行为更像：

\[
\boxed{\text{memory-driven local policy refinement over episodes}}
\]

目标不是保证 global optimum，而是在 observed distribution / proposal space 中趋向 locally empirically stabilized memory。

---

# 11. 当前实验为什么不用完整系统起步

如果一开始就把 Stage1、A、B、C、H、retrieval、actor、longitudinal history 全部接上，那么 negative result 无法归因。

因此实验按照 scientific gate 逐步恢复复杂度。

---

# 12. 正式实验路线

## Phase 0 — Mechanism Sanity

状态：基本完成。

已经验证/审计：

- B/C 责任边界；
- B OPEN/NONE controlled cases；
- C fact-only local synthesis；
- source/future grounding separation；
- H target-time grounding；
- H behavioral authority；
- one-shot lifecycle；
- positive/negative observation logging；
- E1-only A；
- action-index；
- mechanical runtime state；
- actual execution pairing proof。

这不等于 C3 优于 baseline。

## Phase 1 — Targeting Value

核心问题：

\[
\boxed{C3\;vs.\;C2}
\]

C1：

    fixed established memory K* only

C2：

    K* + fair structured generic exploration

C3：

    K* + history-derived targeted exploratory H

C2 与 C3 必须尽量共享 H schema、one-shot authority、lifecycle、runtime bookkeeping、actor、step cap、context budget、probe budget。

唯一关键差异：

    history-derived targeting information

## Phase 1A — 当前真正准备运行的窄实验

当前 lead carrier：pinned ALFWorld TextWorld。

当前 experiment scope：

> Receptacle-Search Targeting Pilot

它只测试一个 semantic comparison family：

    h_family_receptacle_search

因此允许的 claim 是：

> Given a useful history-derived receptacle-search unresolved comparison, does targeted exploration outperform fair structured generic exploration on a pre-registered scope-matched target distribution?

它不能支持：

> exploratory memory generally outperforms generic exploration.

当前 public universe：

    eligible: 54
    source: 5
    hard calibration: 10
    diagnostic calibration: 18
    target: 20
    residual: 1

当前 target 共 20 个，来自 public-only outcome-blind partition。

## Phase 2 — Native Cold-Start Memory Formation

只有 Phase 1 出现值得继续的 signal 后，才从正式 native cold start 开始验证：

    raw trajectory
      -> Stage1
      -> A
      -> established memory / Semantic Concepts

重点不是普通摘要准确率，而是：

- 是否保留 evidence；
- 是否保留 scope；
- 是否保留 provenance；
- feasibility 是否被错误升级成 preference；
- comparative uncertainty 是否被压平。

Pilot 规模：约 30–50 trajectories，15–20 人工深审。

## Phase 3 — One-Step Memory Evolution Value

闭合：

\[
K_t
\rightarrow B
\rightarrow C/H
\rightarrow E
\rightarrow A
\rightarrow K_{t+1}
\]

然后比较 held-out tasks：

\[
Actor(K_t)
\quad vs.\quad
Actor(K_{t+1})
\]

真正回答 exploratory evidence 是否转化成 later-task memory benefit。

## Phase 4 — Automatic Retrieval

比较：

    C3_oracle-match
    vs.
    C3_auto-retrieval

并拆 retrieval miss、wrong H、wrong activation、grounding failure、actor failure。

## Phase 5 — Full Native Cold-Start Longitudinal System

最后才实现真正完整：

\[
K_0
\rightarrow
T_1
\rightarrow
K_1
\rightarrow
T_2
\rightarrow
\dots
\]

包含 Stage1、A、B、C/H、automatic retrieval、consolidation/index、online actor、longitudinal runner。

这才是 full-system benchmark。

---

# 13. Benchmark 什么时候进入

不要混淆三层：

### Phase 1

已经使用真实 benchmark task distribution，但属于 benchmark-backed controlled evaluation。

### Phase 3

开始形成更正式的 method-level benchmark claim。

### Phase 5

才是 full native cold-start longitudinal benchmark。

---

# 14. 数据量与模型策略

Phase 1A 计划：

    20 unique targets
    × C1/C2/C3
    × 2 repetitions
    = 120 actor episodes

统计单元仍然是：

    n = 20 target/source-target units

repetition 不是独立样本。

模型原则：

    1 main actor
    1 offline semantic backbone

只有主信号明确后才加第二 actor 做 robustness。

---

# 15. MVP Warm Start 与 Method-Native Cold Start 的区别

Phase 1 为隔离 targeting value，故意使用固定：

\[
K_{0,\mathrm{Phase1}}^{established}=K^*
\]

当前 K*：

- 手工 feasibility-only control fixture；
- 不是 Stage1/A 产物；
- 不是方法 native initialization；
- C1/C2/C3 完全共享；
- 不能用来证明 native memory formation 已成立。

因此 Phase 1 的 claim 是 conditional：

> given a reasonable established memory / incumbent, does targeted exploratory memory add value?

---

# 16. 当前主要 benchmark 判断

### ALFWorld TextWorld

当前唯一 Phase 1 lead carrier，因为已有真实执行 harness、actual pairing proof、action-index、低环境成本和明确 local search alternatives。

局限：optimization semantics 主要集中在 search order，不适合作为唯一最终 benchmark。

### AppWorld

历史审计没有找到足够好的自然 Problem-B cases，且执行/actor/pairing 成本高。当前 deferred。

### 其他 benchmark

ScienceWorld / WorkArena++ 等可以后续重新做 admission，但不应在 Phase 1A 前增加工程变量。

---

# 17. 当前进展时间线

## 17.1 问题定义阶段

已经完成：

- feasibility vs comparative evidence；
- evidential reachability framing；
- established vs exploratory memory；
- targeted exploration 定位。

## 17.2 初始 MVP

早期 B：

    P 0/5 OPEN

失败原因：

- current trajectory / historical memory 边界混淆；
- B 被迫同时提出 concrete alternative；
- B/C 责任漂移。

修正后：

    P 5/5 OPEN
    N1 0/3 OPEN
    N2 0/3 OPEN

这支持接口设计，但不是自然分布 discovery claim。

## 17.3 C 修正

早期 C 输出 fixed future action sequence。

已修成 adaptive probe policy，并去掉 source final-answer leakage，区分 source grounding 与 future H。

## 17.4 Online mechanism

跨 task H 可以激活、target-time ground、改变行为、evidence-ready、remove runtime H、continue original task。

SprayBottle transfer 支持 lifecycle/transfer 能工作，但没有 performance gain。

## 17.5 Runtime representation

Laptop case 中，原 actor desk/shelf 循环到 cap。

加入仅机械的 visited/count 后变成短成功轨迹。

这支持：

> representation/interface problem should be fixed before adding semantic controller.

## 17.6 Action-index / Pairing

已经解决 exact action string reproduction confound、invalid repair/clamp、discarded preflight pairing，并建立 actual E0/E1 replay-spec proof。

## 17.7 Phase 1 Readiness

commit 3d1a716...：

- fair C2；
- warm-start K*；
- target registry；
- benchmark admission；
- actor gate protocol；
- C1/C2/C3 runner scaffolding。

## 17.8 Pre-Pilot Correction

commit a738366...：

- full public eligible universe；
- Source/Calibration/Target deterministic partition；
- registry-bound execution；
- source-H manifest schema；
- deterministic H assignment；
- actor manifest；
- probe budget；
- context audit；
- fail-closed tests。

No paid model/API call。

## 17.9 Gate B1 Protocol Transition (historical)

This was the historical **Gate B1 — Independent C1 Actor Calibration** cycle.
The method,
K*, Source/Calibration/Target partitions, actor prompt, step cap and transport
configuration are frozen. The only permitted real model experiment is one C1
run on the ten hard-calibration tasks; the 18 diagnostic tasks, all targets,
live B/C H generation, B3 context audit and any second actor are prohibited.

The admission criteria are frozen before the calls:

- invalid action index = 0;
- at least 8/10 successful hard-calibration tasks;
- at most 2/10 step-cap failures;
- at most 2/10 manually reviewed semantic-loop tasks;
- at least one successful task in each of the four Phase 1A task families.

The committed Qwen3.8-Flash actor manifest remains
`candidate_pending_independent_reliability_gate`; calibration may use it, but
the scientific target runner remains fail closed until a separate researcher
review promotes a manifest. This gate tests only baseline C1 execution
reliability, not C3 targeting value or exploratory-memory effectiveness.

## 17.10 Gate B1 execution result

The single protocol-consistent 10-task C1 run was executed with the frozen
configuration and is recorded in [docs/71_phase1_gate_b1_actor_calibration_results.md](../71_phase1_gate_b1_actor_calibration_results.md).
The first base-Python invocation stopped before model calls because ALFWorld
text dependencies were unavailable; the preserved infrastructure artifact is
not an actor result. The subsequent run in the existing pinned
`memory-automanual` environment made 262 step-level actor calls across the
same ten tasks, with no task retry.

The candidate result is **FAIL** under the frozen gate: 4/10 successes, 6/10
step-cap failures, zero invalid action indices, and no success in the
`pick_cool_then_place_in_recep` family. Manual review found two clear loops and
four uncertain no-progress traces; the uncertainty cannot change the result
because the mechanical criteria already fail. The committed actor manifest
remains `candidate_pending_independent_reliability_gate`.

---

# 18. 当前证据支持等级

## 强/可信的 mechanism/harness evidence

- conceptual B/C boundary；
- fact-only C synthesis；
- source/future grounding separation；
- H behavioral authority；
- one-shot lifecycle；
- target-time grounding；
- E1-only A；
- action-index；
- pairing proof；
- public-only target registry；
- fail-closed scientific runner。

## 尚未支持

- C3 > fair C2；
- Qwen3.8-Flash 已通过 main actor gate；
- production Stage1；
- native cold-start memory formation；
- automatic H retrieval；
- K_t→K_{t+1} later-task benefit；
- multi-family generality；
- full longitudinal system；
- cross-benchmark generality。

---

# 19. 当前正式 review 结论

截至 `ef44ff2...`，上一轮 readiness blockers 已经 code-enforced，Gate B1
的 protocol transition 与唯一 10-task C1 run 均已完成。结果记录在
`docs/71_phase1_gate_b1_actor_calibration_results.md`：当前 Qwen3.8-Flash
candidate 未通过基础执行可靠性 gate。Gate B1 只审查共同 actor 在 Phase 1A
`Actor + K* = C1` 下的基础执行可靠性，不审查 C2/C3 的科学贡献。

### Gate B1 hard admission criteria

    invalid action index = 0
    success >= 8/10
    step-cap failures <= 2/10
    manually reviewed semantic loops <= 2/10
    each Phase 1A family has >= 1 success

Hard calibration is fixed at 10 in-domain tasks. The 18 out-of-domain
diagnostic tasks cannot affect admission and are not run in this cycle.

---

# 20. 当前下一步

Phase 1B Pre-Scale Closure 的唯一六-task closure run 已完成并记录在
`docs/98_phase1b_prescale_closure_results.md` 与
`docs/99_phase1b_prescale_closure_semantic_review_and_decision.md`。它证明了
Task 1→2 的完整 longitudinal loop，但发现一个局部 A interface blocker：合法的
`CONTRADICTING / PARTIALLY_RESOLVED` assessment 会被同一 response 中非法的
`REFINE` 空 target 绑定整体丢弃。

当前 active cycle 改为：

    Phase 1B Finalization — A Fault Isolation & Freeze

本 cycle 只做无模型代码/artifact regression：把 A 的 epistemic assessment 与
Established Memory updates 分层验证和物化，并使用保存的 Task 1/2/3/4 artifacts 回归。
不得重新运行六-task、十二-task或 fresh task，不得进行任何 model/API call。

如果回归通过，决策为：

    READY_FOR_SCALE_WITH_KNOWN_LIMITATIONS

然后停止 development/tuning，下一 cycle 直接设计 fresh 40–60 task longitudinal scale
experiment。已知限制为：unsafe B Functional Contract 会 fail-closed、comparison identity
可能产生 near-duplicate、retrieval quality 尚未规模验证、当前 controlled ALFWorld search
abstraction 不是完整 autonomous actor。

# 21. 当前不要重新打开的问题

除非有新 evidence，不要重新设计：

- B 是否提出 concrete alternative；
- C 是否看到完整 source trajectory；
- H 是否固定 future action list；
- H 是否跨 episode 自动重复；
- A 是否看 E0；
- online 是否做 semantic memory update；
- online B/C；
- graph search controller；
- VOI planner；
- rule-based fallback；
- 全局 trajectory planner。

当前重点是：

\[
\boxed{\text{evaluation quality > method complexity}}
\]

---

# 22. 新参与者接手时的工作纪律

任何建议/修改都先回答：

1. 这是 scientific method change，还是 harness/evaluation change？
2. 当前 evidence 真的要求改方法吗？
3. 会不会引入 evaluator/oracle leakage？
4. 会不会改变 C1/C2/C3 除 intervention 外的因素？
5. 这个结果支持 conditional claim 还是 full-system claim？
6. 是否把 repetition 错当 independent sample？
7. 是否把 warm-start K* 错当 native initialization？
8. 是否在少量漂亮 case 上过拟合方法？

如果说不清，先不要改代码。

---

# 23. 推荐阅读地图

快速加入讨论：

    09_project_master_handoff.md
    -> 10_current_review_protocol.md
    -> AGENTS.md

理解科学问题：

    01_problem_and_contribution.md
    -> 09_project_master_handoff.md

理解方法细节：

    02_method_architecture.md
    -> 03_component_contracts.md

理解实验路线：

    05_paper_level_evaluation_design.md
    -> 07_experiment_validation_roadmap.md
    -> 08_experiment_scale_and_model_budget.md

理解历史证据：

    04_validation_progress.md
    -> docs/45
    -> docs/51
    -> docs/57
    -> docs/60
    -> docs/63–69

当前实现者：

    10_current_review_protocol.md
    -> AGENTS.md
    -> experiments/exploratory_memory_mvp/

---

# 24. 一句话当前状态

> 核心方法机制已经足够清楚，当前研究风险不再是“idea 能否写出来”，而是 history-derived targeting 在公平 generic exploration baseline 上是否真的具有增量价值。当前正在完成 Phase 1A 首次付费实验前的最后科学约束审查。
