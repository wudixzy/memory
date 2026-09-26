# CURRENT HANDOFF UPDATE — 2026-09-27: Round1-v2 transition frozen

The Phase 2B Round1-v1 saved-output audit and A contract repair are complete.
`STAGE1_V1_KEEP` applies to mechanically revalidated Stage1 outputs 1–8 only.
The new Round1-v2 transition is frozen in
`docs/146_phase2b_round1v2_contract_transition.md`; audit details are in
`docs/145_phase2b_round1_saved_output_audit.md`.

Round1-v2 uses clean native cold start, reuses only Stage1 1–8, runs fresh
Stage1 9–12, and obtains fresh A outputs for every Stage1-accepted task (up
to 12). Round1-v1 remains immutable and classified
`ROUND1_V1_CONTRACT_SHAKEDOWN_INCOMPLETE`. Preparation used zero model/API
calls. No model/API call or environment episode is currently authorized;
await a separate researcher decision before execution. Do not enter Round
2/3, holdout, Max sanity, Phase 2A-X, Phase 2C, or formal evaluation.

---

# Superseded handoff update — 2026-09-27: Round1 contract repair in progress

The active task is no longer infrastructure resume. Round1-v1 is frozen as
contract-shakedown evidence. Review found a model-facing A contract mismatch:
schema cardinality and Support-binding affordances were looser/different from
the post-validator, producing six rejections among seven visible A outputs.

Current sequence:

```text
saved-output 0-call audit
-> A contract repair
-> tests / Stage1-cache plan
-> immutable Round1-v2 transition
-> researcher review
-> future clean-cold-start Round1-v2
```

No model/API call is currently authorized. See docs/143–144.

---

# Current update — 2026-09-25: Phase 2A-X preparation frozen

The no-model Phase 2A-X Stage1/A cross-feed package is prepared and frozen in
`docs/139_phase2ax_crossfeed_attribution_plan_and_transition.md`. It binds all
15 Phase 2A primary `source_episode_ref` appearances, the existing FF/MM
outputs (including the separately authorized Pan/Max A recovery while
preserving its original corrupt response), and future FM/MF placeholders.
Preparation made zero model/API calls and started zero environment episodes.

Current gate remains `CROSS_MODEL_REGIME_REMAINS`. The only prepared future
execution is 30 off-diagonal A calls; it is not authorized until a separate
researcher decision. No Stage1 rerun, diagonal rerun, secondary case,
Phase 2B/C/D, or formal evaluation is authorized.

---

# CURRENT HANDOFF UPDATE — 2026-09-25: Phase 2B Native Core

The researcher has explicitly shifted the active line to **Phase 2B — Native
Persistent Memory Core Implementation & Bounded Tuning**. Phase 2A-X remains
`FROZEN_OPTIONAL_DIAGNOSTIC`; preserve its preparation and do not execute it.
The inherited method design remains unchanged: native `G_tool` cold start,
complete real trajectory → Stage1 Open Mining → Candidate + native Support →
Stage2/A local reconciliation → Text Memory ∥ Semantic Graph ∥ Support.
Exploratory B/C/H are deferred and are not part of Phase 2B.

The frozen implementation plan is `docs/140_phase2b_native_memory_core_plan.md`;
the no-model preparation/transition is recorded in
`docs/141_phase2b_initialization_and_implementation_transition.md`. The fixed
corpus has 24 development-only trajectories (12 calibration, 12 holdout),
disjoint from the 13 task identities with already-saved terminal full-task
traces. Formal Population Admission remains separate and unresolved. No
model/API call or environment action is allowed before the immutable
transition is committed and pushed; after it, only the bounded Phase 2B runs
authorized there may proceed.

---

# 11. Phase 2 Core Method Handoff — 全局设计、证据边界与当前接手任务

> 当前更新：2026-09-25 — Phase 2B Round 1 interrupted at calibration task 8.
> The 24-task corpus completed; six A responses failed frozen validation and
> task 8 A ended with a privacy-safe `DashScopeError` transport artifact. The
> run is incomplete, no retry/resume was attempted, and no further model/API
> calls are authorized pending researcher direction. See docs/142. Phase 2C,
> Phase 2A-X execution, formal evaluation, and Method v1 freeze remain
> unauthorized/incomplete.
>
> 历史更新时间：2026-09-23
> Active branch：exp/minimal-exploratory-memory-validation
> Frozen Phase 2A v1 preparation baseline：2dd673be18866fdc283f9fbc592433e32936e9b6
> 当前状态：Phase 2B full-trajectory corpus complete; Flash Round 1 incomplete after task 8 transport failure (docs/142).
> 当前授权：Phase 2B calibration authorization paused at the recorded interruption; no automatic retry, resume, or further model/API calls are authorized pending researcher direction.

> **Historical Phase 2A status note (superseded by the current update above):** v1 preparation and v2 hardening remain immutable. Primary runs completed on frozen inputs; Max provenance is segmented, with one disclosed unknown-result Stage 1 reissue and one separately authorized isolated A recovery. The semantic review found useful grounded learning but persistent same-input cross-model divergence in mutation authority and boundary treatment. At that point, no secondary cases or Phase 2B runs had occurred. The subsequent Phase 2B corpus and interrupted Round 1 are recorded in docs/142.

本文是当前项目的主接手文档。它的目的不是再次从头设计方法，而是让新的研究者 / coding-agent 在进入代码前先继承已经完成的概念设计、历史实验和证据边界。

如果本文与更早的历史实验文档冲突，优先按当前 Phase 2 plan、当前 review/transition、frozen historical result docs 的时间顺序解释，不回写历史结果。

---

# 0. 新参与者先记住的三件事

第一，本项目当前已经不再处于“idea 能不能跑”的 MVP 阶段。

Phase 1 已经验证了 B/C/H、one-shot exploration、跨 task transfer、long-horizon accumulation、Flash/Max cross-model behavior 等多个机制。当前进入的是：

~~~text
Core Method Integration Validation
~~~

也就是开始恢复并测试原来完整方法中的 Stage1 -> support-aware A/Stage2，而不是继续给 Phase 1F 的 A / comparison ledger 打补丁。

第二，最近 review 暴露出的核心问题不是“Graph 还没设计好”，也不是已经证明“comparison ledger 必须更复杂”。

更合理的当前 attribution hypothesis 是：

~~~text
Phase 1F 为了隔离 B/C/H 而压缩了原始 Stage1 + Stage2/A，
可能导致 A 职责过载和 epistemic state 跨模型不稳定。
~~~

这是待验证 hypothesis，不是结论。

第三，很多问题已经在 8–9 月完整讨论过。后续参与者不能因为当前代码没有实现，就把这些问题重新当成 conceptual open question。

原则：

> 先确认这是“历史设计已定但尚未实现”，还是“真实新 evidence 迫使我们重开设计”。

---

# 1. 研究问题：我们到底在解决什么

Persistent agent memory 的标准目标是：

~~~text
historical trajectory
-> compress / consolidate
-> reusable persistent memory
-> future behavior
~~~

但 Memory 不只是被动存储。它会改变未来 Agent 的行为，而未来行为又决定系统之后会看到什么 evidence：

~~~text
K_t
-> future policy
-> observed evidence
-> future trajectory
-> memory update
-> K_{t+1}
~~~

因此一个核心风险是：

~~~text
Feasibility Evidence != Comparative Evidence
~~~

历史中策略 A 成功，只能直接说明：

~~~text
A worked under the observed scope
~~~

不能自动说明：

~~~text
A > B
A is necessary
A should become the default
A is near-optimal
~~~

如果 Memory 不断把“成功过”压缩成“以后优先这样做”，可能造成 improvement lock-in：系统以后越来越少获得能够比较其它 realization 的 evidence。

当前方法的核心闭环因此是：

~~~text
Established Experience
-> Unresolved Comparative Question
-> Targeted Future Exploration
-> New Evidence
-> Memory Evolution
~~~

---

# 2. 当前方法不是单独一套 Exploratory Memory，而是 Persistent Memory 的完整演化框架

当前长期信息结构继承历史方案：

~~~text
Raw Experience
+ Semantic Memory
+ Structural Graph
+ Support / provenance substrate
~~~

同时 Semantic Memory 中区分不同 epistemic status：

~~~text
K = Established Memory + Exploratory Memory
~~~

## 2.1 Raw Experience

回答：

> What actually happened?

保存真实 trajectory / actions / observations / outcomes / costs / provenance。

它是最终 evidence source，但不是每次 Stage2 默认重新读取的历史 reasoning context。

## 2.2 Established Memory

回答：

> What do we currently have reason to reuse?

它是 future Agent 正常 exploitation/reuse 的主要长期语义。

最近 review 使用了一个有帮助的 semantic audit lens：

~~~text
Established Memory
= Claim
+ Evidence Basis
+ Unresolved Boundary
~~~

但必须注意：

**这不是已经冻结的新物理 schema。**

它是检查一条 Memory 是否 epistemically calibrated 的语义视角：

- Claim：当前可以复用地说什么；
- Evidence Basis：为什么有理由说；
- Unresolved Boundary：当前 Claim 到哪里为止、什么还没有被 evidence 支持。

Unresolved Boundary 是当前 Claim 的局部 epistemic limitation，不是 exploration TODO list。

~~~text
Unresolved Boundary != Exploratory Memory
~~~

场景中“下一步值得探索什么”仍由 B/C/H 负责。

## 2.3 Exploratory Memory / H

回答：

> Which grounded local hypothesis should be tested once in a future matching context?

H 是：

- history-derived；
- local；
- future-facing；
- grounded；
- adaptive；
- one-shot；
- evidence-seeking。

H 不是事实，也不是一个新的 policy preference memory。

~~~text
H = future experiment
Established Memory = reusable conclusion
~~~

不存在单独的 Policy Preference Memory。

## 2.4 Support

Support 是 historical observation 对长期 Claim 提供的可追溯依据。

历史设计已经区分：

~~~text
Historical Support Log
= complete / auditable

Current LLM-facing Support View
= small / diagnostic / deduplicated
~~~

优先级：

~~~text
boundary / counter-support
>
provenance-diverse representative positive
>
large amounts of duplicate positive support
~~~

Support observation 尽量 immutable；变化的是 Support 与当前 semantic claim 的 binding。

## 2.5 Structural Graph

Graph 不是本项目当前待重新设计的问题。

既有定位：

- Tool / Capability anchors；
- Semantic Concept organization；
- cross-memory / cross-trajectory grounding；
- stable semantic relations；
- retrieval / bounded local expansion；
- cross-trajectory aggregation / abstraction / navigation。

Graph 明确不是：

- global planner；
- exploration search-space controller；
- ANN/retrieval graph 的复杂包装；
- full action transition graph；
- comparison truth engine。

Semantic Concept 是：

> 有稳定独立语义、能被多个 persistent objects 共享引用、且显式 identity 具有 relational reuse value 的 abstraction anchor。

Phase 2 当前只要求和既有 Graph 设计兼容，不测试 Graph contribution。

---

# 3. Native cold start 已经定义，不要重新讨论

正式方法初始化：

~~~text
G_0 = G_tool
Established Memory = empty
Exploratory Memory = empty
Exploration History = empty
Raw Trajectory Store = empty
~~~

原则：

> Fix what the environment defines; learn what experience gives meaning to.

启动时允许：

- Tool identity；
- Operation/API identity；
- stable I/O / containment；
- environment-defined capability metadata。

启动时不预构造：

- Strategy / Procedure concepts；
- Semantic Concepts；
- Context taxonomy；
- subgoal taxonomy；
- complete action/strategy space；
- preferable_to / alternative_to / should_explore 等经验关系。

Phase 1 的 warm-start K* 是实验控制，不是 method-native initialization。

---

# 4. Offline method 主链：Stage1 与 A/Stage2 是历史设计，不是 Phase 2 新发明

完整方法的 offline core 是：

~~~text
completed trajectory
-> Stage1 Open Mining
-> Candidate + Support
-> A / Stage2 Local Knowledge Reconciliation
-> Established Memory / Support / optional Graph mutation
~~~

同时 B/C 的历史侧必须读取 pre-update Established Memory，防止当前 trajectory 经 A 写入后又被当成自己的历史 evidence。

逻辑上：

~~~text
Stage1(current trajectory)
  -> A(Candidate, pre-update Established Memory)

current trajectory + pre-update Established Memory
  -> B
  -> C
  -> future H
~~~

最后统一 materialize state。

---

# 5. Stage1：Single-Trajectory Open Mining

Stage1 输入：

~~~text
one completed trajectory
no Existing Memory
~~~

输出：

~~~text
Candidate
├── Content
└── Support
    ├── Direct Grounding
    ├── Minimal Global Context
    └── provenance / optional bounded verification grounding
~~~

Stage1 回答：

> What is potentially reusable from this trajectory, and what evidence/context is required not to misread it?

Stage1 不负责：

- historical comparison；
- comparative superiority；
- B OPEN/NONE；
- exploration judgment；
- comparison ledger update；
- H synthesis；
- Graph planning；
- unnecessary generalization。

Stage1 是第一处显式有损 semantic transformation。

---

# 6. A / Stage2：Local Knowledge Reconciliation

A 回答：

> What does this Candidate change about what we already know?

历史设计里最重要的 comparison object 已经明确：

~~~text
Candidate
<-> Current Text Memory
~~~

不是：

~~~text
Candidate + all historical raw trajectories
~~~

Bounded local context 可以包含：

~~~text
Current Text Memory
+ bounded Semantic Graph context
+ small diagnostic Support view
~~~

核心 reasoning contract：

~~~text
Existing coverage
-> Candidate semantic delta
-> decision relevance
-> evidence sufficiency
-> minimal necessary mutation
~~~

A 可以进行：

- new / CREATE；
- merge / dedup；
- refine；
- generalize；
- specialize；
- contradiction reconciliation；
- scope revision；
- provenance accumulation；
- concept alignment。

A 可以修改 Claim、Evidence Basis、Unresolved Boundary 对应的语义部分。

真正需要保护的是：

~~~text
Claim authority cannot exceed evidence.
~~~

以及：

~~~text
one-sided success
!=
comparative/default superiority
~~~

不能因为这一点就把 A 拆成大量规则模块。

原则仍然是：

> LLM interprets semantics; code protects identity, provenance and epistemic invariants.

---

# 7. B / Functional Contract / C / H 的边界已经验证过，不要重开

## B — Local Comparative Diagnosis

B 回答：

> Which incumbent comparison is worth opening?

B 判断：

- 当前 behavior 有 feasibility support；
- comparative support 不足；
- 这个 unresolved comparison 对 future policy 有意义。

B 不生成 concrete alternative。

## Functional Contract

描述当前局部 realization 必须完成什么功能：

~~~text
available input/state
+ local function
+ required downstream state
+ necessary constraints
~~~

它是 transient context-conditioned working representation。

不要和 Semantic Concept 混淆：

~~~text
Semantic Concept = long-term semantic organization
Functional Contract = local substitutability boundary
~~~

## C — Counterfactual Synthesis

C 回答：

> What grounded local test should be tried once?

C 根据：

- B diagnosis；
- Functional Contract；
- relevant Semantic Memory；
- real Tool/Capability；

生成 grounded adaptive H。

C 不默认看到完整 source trajectory，避免 source answer leakage。

## H lifecycle

Persistent：

~~~text
active
-> activated
-> consumed
~~~

Consumed != falsified。

实际被激活的 H 进入 offline Exploration History，以防 C 以后不断重复同一个 exploratory hypothesis。

B 当前不读 Exploration History；C 在 B=OPEN 后读取少量相关历史。

---

# 8. Comparison ledger 当前应该怎样理解

Comparison ledger 是 exploratory branch 后来引入的对象。

当前不应把它视为 Established Memory 之外的第二套 epistemic truth store。

Phase 2 当前策略：

~~~text
Established Memory + Support
= epistemic source of truth

Comparison record
= exploration identity / provenance / bookkeeping / telemetry
~~~

在 native Stage1/A 恢复之前，不继续强化：

- OPEN / PARTIALLY_RESOLVED / RESOLVED；
- confidence；
- comparative strength；
- evidence accumulator taxonomy。

是否 KEEP / LIGHTEN / REMOVE AS INDEPENDENT SUBSYSTEM，要等 Phase 2C/2D 看到真实 evidence 后决定。

---

# 9. 已经讨论完、默认不要重新打开的问题

后续参与者在提出 architecture change 前必须先检查本节。

## 已关闭 / 冻结方向

1. B 不提出 concrete alternative；C 才提出。
2. C 不默认读取完整 source trajectory。
3. H 不是 fixed future action list，而是 adaptive local probe policy。
4. H 是 one-shot；consumed 不代表 falsified。
5. Online 不做 semantic memory update；Online writes facts, Offline writes knowledge。
6. Historical reasoning 默认基于 compressed Persistent Memory，不每次读取全部 raw trajectories。
7. Stage1 不看 Existing Memory。
8. A/Stage2 主要比较 Candidate 与 Current Text Memory。
9. Graph 不承担 exploration search-space controller。
10. 不建立复杂 ContextFamily / StrategyFamily taxonomy。
11. 不额外建立 Policy Preference Memory。
12. 不提前设计 NONE/INDIRECT/MATCHED/DIRECT 等 evidence strength hierarchy。
13. 不提前引入 confidence score / repeated-test threshold / statistical confidence online。
14. 不因为 Max 与 Flash 不一致就把 Flash 的 PARTIALLY_RESOLVED 当 ground truth。
15. 不把 Graph 的具体 relation list、Graph DB、hop 数等当当前顶层科学问题。
16. 不在 formal evaluation 前用 current development residual 假装 untouched reserve。

如果要重开，必须明确提供：

- 新 evidence；
- 被破坏的既有 assumption；
- 为什么不能通过局部 implementation/evaluation 修正；
- 为什么值得增加方法复杂度。

---

# 10. Phase 1 已经告诉我们的东西

## Phase 1B

冻结 baseline：

~~~text
c8daa67ba9d9d6257d65e446b437d362e60abc61
~~~

结论：

~~~text
READY_FOR_SCALE_WITH_KNOWN_LIMITATIONS
~~~

B/C/H mechanism、transfer、actual evidence、A update 等基本链路可工作。

## Phase 1C — Flash N=32

Generic G vs history-conditioned T：

~~~text
N32:
G = 446
T = 405
Delta(T-G) = -41
~~~

H-active benefit 明显；no-H 基本中性。

## Phase 1D — Flash N=64

~~~text
N64:
G = 797
T = 705
Delta = -92
~~~

suffix 仍有新增收益，说明不是只有早期 lucky prefix。

## Phase 1E — Max N=64

~~~text
G = 638
T = 685
Delta = +47

H-active = -7
no-H = +54
~~~

即 mechanism 能形成，但整体 behavior negative，主要问题不在 H-active subset。

Max 的 Established Memory / comparison evolution 与 Flash 显著不同。

## Phase 1F attribution

leading attribution：

~~~text
MIXED
~~~

包括：

- Max generic exploration 本身更强；
- old T no-H asymmetry；
- model-dependent A/H/comparison evolution；
- protocol + prompt + trajectory divergence。

## Phase 1F-MA-v2

12 development-only tasks × G/T0/T1 × Flash/Max = 72 episodes。

Hybrid T1 将 no-H 恢复为 generic C2：

~~~text
Flash:
T1 - T0 = -11
T1 - G  = -21

Max:
T1 - T0 = -4
T1 - G  = +33
~~~

generic fallback 有帮助，但没有解释 Max residual。

最终解释：

~~~text
MEMORY_EVOLUTION_REGIME_REMAINS
~~~

---

# 11. Phase 1F semantic review 的真正新增信息

对 frozen 12-case bundle 的人工 review 发现：

1. Pan / Egg 等 matched factual cases 中，Flash/Max 对 evidence direction 接近，但 comparison threshold 不同。
2. Flash 多次从 one-sided H success 给出 SUPPORTING + PARTIALLY_RESOLVED，即使自己承认没有 baseline comparison。
3. Max 有时 REMAINS_OPEN / INCONCLUSIVE，却仍显著把 Established Memory 写成 policy-like guidance。
4. Cloth / SoapBar 显示 evidence direction 与 comparison resolution 必须分开。
5. Lettuce / Tomato 暴露 H scope/retrieval mismatch，不能全部归因于 A。
6. topology chain 显示早期 schema/interface difference 会被 persistent memory 放大成后续 memory topology divergence。

最重要的结构问题：

> Phase 1F A 同时承担 trajectory interpretation、evidence direction、comparison assessment、Established Memory mutation，可能绕过原方法中的 Stage1 + support-aware reconciliation。

因此当前不是继续调 ledger，而是恢复历史完整 core。

---

# 12. Phase 2 总路线

Governing plan：

~~~text
docs/128_phase2_core_method_integration_validation_plan.md
~~~

## Phase 2A — Frozen semantic integration replay

目标：

> 在 frozen Phase 1F trajectory 上恢复 Stage1 -> Candidate+Support -> A，验证 semantic integration。

它是 integration gate，不是最终 full-system result。

## Phase 2B — Native memory formation / accumulation

从 empty experience memory 出发，用 frozen real completed trajectories：

~~~text
tau_1 -> Stage1/A -> K_1
tau_2 -> Stage1/A -> K_2
...
~~~

验证 native memory formation，而不是 performance。

## Phase 2C — One-step exploratory closed loop

闭合：

~~~text
K_t
-> B/C/H
-> H-test trajectory
-> Stage1/A
-> K_{t+1}
~~~

验证 exploratory evidence 能否通过同一 native memory path 被吸收。

## Phase 2D — Short full-core longitudinal validation

比较：

~~~text
E-only:
native Stage1/A
+ Established Memory reuse
+ same generic exploration

Full:
native Stage1/A
+ Established Memory reuse
+ B/C/H
+ H-active targeted exploration
+ same generic exploration when no H
~~~

stream 内严格 sequential；model/arm stream 可并行。

---

# 13. 历史 Phase 2A preparation snapshot（execution 已在后续完成）

Frozen preparation commit：

~~~text
2dd673be18866fdc283f9fbc592433e32936e9b6
~~~

已完成：

- 12 cases / 25 episode appearances；
- 7 primary / 5 secondary；
- deterministic registry/package；
- source digests；
- Stage1/A prompts/schemas；
- no-model placeholders；
- 50 relevant tests PASS；
- package verification 25/25；
- 0 model/API calls。

Transition：

~~~text
docs/130_phase2a_semantic_integration_transition.md
~~~

在该 preparation commit 当时，researcher review 结论是：

~~~text
PREPARATION_ACCEPTED_WITH_PREEXECUTION_BLOCKERS (historical v1 review decision)
~~~

因此 docs/130 本身不是 READY_TO_RUN transition。其后 v2 pre-execution
hardening 与授权执行由 docs/131–138 记录；当前运行结果与 gate 以
docs/133–134 和本文顶部的 active status 为准。

---

# 14. 历史 v1 pre-execution review findings（已由 v2 处理）

以下记录的是 v1 review 时提出的问题；其 v2 disposition/verification 见 docs/131 与 docs/132。它们不再是当前 coding task。

详细 review 见：

~~~text
docs/131_phase2a_preexecution_review_and_corrections.md
~~~

以下问题是在 v1 review 时提出并作为历史证据保留；v2 disposition 与验证见 docs/131、docs/132。它们不是当前未完成的 coding task。

## Blocker A — prior Support 还不是 semantic Support

当前 A 主要看到：

- Existing Guidance；
- comparison/evidence IDs；
- operation metadata。

真正 representative support / boundary / counter-support 没有进入 compact prior Support View。

这会继续造成：

~~~text
strong claim
+ weak evidence context
~~~

必须优先从 frozen artifacts 机械恢复 small diagnostic Support。

禁止用新的 LLM call 重写历史 support。

## Blocker B — memory neighborhood 在 Stage1 Candidate 之前就被选了

当前 selection 由 task + H + comparison/H provenance anchor 主导。

应改为：

~~~text
trajectory
-> Stage1 Candidate+Support
-> Candidate/problem-side memory selection
-> A
~~~

H/comparison IDs 是 provenance，不应以极大权重决定 semantic neighborhood。

## Blocker C — model-visible semantics 和 audit provenance 混在一起

artifact path / SHA / runtime path / evidence ID 等应该留在 audit sidecar。

模型 payload 只保留 semantic reasoning 需要的内容。

## Correctness blocker — grounding identity 没有强校验

Stage1 的 event_id 当前只检查 non-empty。

必须检查：

~~~text
event_ref belongs to actual visible trajectory events
~~~

trajectory/H/comparison provenance 应由 runner bind，而不是让模型生成。

---

# 15. 其它需要在执行前一起修的小问题

1. evidence alignment 不能只看 task identity。
   - EXACT_PUBLIC_TRAJECTORY；
   - SAME_TASK_DIFFERENT_TRAJECTORY；
   - 必要时 SEMANTICALLY_SAME_TRAJECTORY_METADATA_DIFF。

2. Phase 2A 的 source trajectory 实际主要是 search/acquisition endpoint，不应称 full completed benchmark trajectory。

   当前 claim 应收紧为：

~~~text
search-local Stage1 -> A integration
~~~

真正 full completed-task Stage1 在 Phase 2B 验证。

3. A schema：
   - UPDATE 不能 updates=[]；
   - SUPPORT_ONLY 必须 target existing memory。

4. docs/130 中预留的 execution command 对应 runner 当前不存在。
   必须先实现真正 executor，再冻结 executable transition。

5. Phase 2A 暂时不要求 RETIRE，但 Phase 2B 前必须恢复完整 historical Stage2 primitive。

---

# 16. 当前新参与者的唯一执行任务

任务名称：

> Phase 2A Pre-execution Hardening

只做：

1. 构造真正 diagnostic prior Support View；
2. Stage1 后再做 Candidate-based memory neighborhood；
3. model-visible input / audit metadata 分离；
4. runner-owned provenance + event grounding validation；
5. evidence-alignment classification；
6. terminology/schema hardening；
7. 实现真正 Phase 2A executor，但默认禁止模型调用；
8. 新建 versioned hardened package；
9. 新建 docs/132_phase2a_execution_transition.md；
10. 运行 no-model tests；
11. push 后停止。

不得：

- 调 Flash / Max；
- 跑 Phase 2A semantic replay；
- 跑 Phase 2B/C/D；
- 改 B/C/H；
- 改 Graph；
- 重构 comparison ledger；
- 用 LLM总结历史 Support；
- 重新选 case；
- 根据预期结果调 prompt。

---

# 17. 历史 stop rule（Phase 2A primary 已按授权执行并完成）

本节记录当时的 preparation-to-review boundary；其后的授权执行与当前
decision 见本文顶部及 docs/133–134。不要把下方 pre-execution 状态当作
当前状态。

完成 hardened package + executor + immutable execution transition 后：

~~~text
STOP
-> researcher pre-execution review
~~~

如果没有新 blocker，再授权 Flash/Max。

不要因为“还可以再优化一下”继续做第三轮 architecture tweaking。

从这一点开始，优先：

> test the frozen method, not perfect the method before evidence.

---

# 18. 后续 formal evaluation 仍然没有授权

当前仍不能声称：

- general memory superiority；
- native cold-start performance；
- broad cross-benchmark generality；
- final paper-level superiority。

Formal evaluation 仍需要：

- Method freeze；
- Evaluation freeze；
- separately admitted untouched confirmatory population；
- 不能继续消费 current development residual 当 reserve。

---

# 19. 新参与者阅读顺序

## 最短路径

1. 本文：current_state/11_phase2_core_method_handoff.md
2. docs/131_phase2a_preexecution_review_and_corrections.md
3. docs/128_phase2_core_method_integration_validation_plan.md
4. docs/130_phase2a_semantic_integration_transition.md
5. current_state/02_method_architecture.md
6. current_state/03_component_contracts.md
7. docs/37_method_structural_initialization.md
8. docs/38_exploratory_memory_lifecycle.md
9. docs/126_phase1f_ma_v2_semantic_review.md
10. docs/127_semantic_review_bundle_handoff.md

然后再看：

- docs/current_state/04_validation_progress.md
- docs/104–126 对应的具体实验历史。

## 实现者

再读：

~~~text
experiments/exploratory_memory_mvp/phase2a_integration.py
tests/test_phase2a_integration.py
docs/review_samples/phase2a_semantic_integration/
~~~

---

# 20. 防止重复讨论的工作纪律

新的参与者开始任何设计讨论前，先输出一份短的 Inheritance Check：

~~~text
A. 已继承的 frozen decisions
B. 当前 evidence 真正支持什么
C. 当前仍 open 的问题
D. 本轮准备修改什么
E. 为什么这不是重新打开一个已经解决的问题
~~~

如果无法完成这五点，不应直接提 architecture change。

特别禁止这种推进方式：

~~~text
看到当前代码没有 X
-> 假设以前没讨论过 X
-> 重新设计 X
~~~

正确方式：

~~~text
看到当前代码没有 X
-> 查 current_state + historical design
-> 判断 X 是 deferred implementation 还是 conceptual gap
-> 只有真实新 evidence 才重开 conceptual design
~~~

这条纪律适用于 Stage1、A、Support、Graph、comparison ledger、cold start、H lifecycle、retrieval 等所有核心组件。
