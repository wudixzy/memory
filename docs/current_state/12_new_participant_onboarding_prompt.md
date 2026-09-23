# 12. New Participant Onboarding Prompt — Phase 2 Core Method Integration

下面是一份可以直接交给新的 research / coding participant 的接手提示词。

---

你现在接手仓库：

~~~text
wudixzy/memory
~~~

工作分支：

~~~text
exp/minimal-exploratory-memory-validation
~~~

当前 frozen baseline：

~~~text
2dd673be18866fdc283f9fbc592433e32936e9b6
~~~

当前阶段：

~~~text
Phase 2 — Core Method Integration Validation
Phase 2A preparation completed
Researcher review decision:
PREPARATION_ACCEPTED_WITH_PREEXECUTION_BLOCKERS
~~~

你的当前任务不是重新讨论 Persistent Memory 架构，也不是直接跑模型，而是完成：

> Phase 2A Pre-execution Hardening

## 非常重要：先继承设计，再工作

本项目已经进行了多轮方法设计和实验验证。当前最容易浪费时间的问题是：

> 看到代码里某组件没有完整实现，就误以为此前没有讨论过，于是重新设计 Stage1 / A / Graph / comparison ledger。

禁止这样做。

在提出任何 architecture change 之前，先阅读并理解以下文档。

### 第一组：当前全局状态

1. docs/current_state/11_phase2_core_method_handoff.md
2. docs/131_phase2a_preexecution_review_and_corrections.md
3. docs/128_phase2_core_method_integration_validation_plan.md
4. docs/130_phase2a_semantic_integration_transition.md

### 第二组：方法定义

5. docs/current_state/02_method_architecture.md
6. docs/current_state/03_component_contracts.md
7. docs/37_method_structural_initialization.md
8. docs/38_exploratory_memory_lifecycle.md

### 第三组：为什么现在进入 Phase 2

9. docs/126_phase1f_ma_v2_semantic_review.md
10. docs/127_semantic_review_bundle_handoff.md
11. docs/current_state/04_validation_progress.md

### 第四组：当前实现

12. experiments/exploratory_memory_mvp/phase2a_integration.py
13. tests/test_phase2a_integration.py
14. docs/review_samples/phase2a_semantic_integration/

读完以后，在开始修改代码之前，先输出一份短的 Inheritance Check：

~~~text
A. 我确认哪些设计已经 frozen / closed
B. Phase 1F / semantic review 真正新增了什么 evidence
C. 当前仍然 open 的问题是什么
D. 我本轮将修改哪些文件 / interfaces
E. 为什么这些修改是实现既有设计，而不是重新发明方法
~~~

如果这五点说不清楚，不要直接改 architecture。

---

# 项目核心问题

Persistent Memory 会影响未来 policy，而未来 policy 又决定以后能获取什么 evidence。

核心区分：

~~~text
Feasibility Evidence != Comparative Evidence
~~~

一次 historical success 说明某 realization 可行，不自动说明它应该成为 default 或优于 alternative。

当前方法希望形成：

~~~text
Established Memory
-> detect meaningful unresolved comparison
-> Exploratory Memory H
-> future one-shot local probe
-> actual evidence
-> native memory evolution
~~~

---

# 已经确定的方法结构

长期信息结构：

~~~text
Raw Experience
+ Semantic Memory
+ Structural Graph
+ Support/provenance
~~~

Semantic Memory：

~~~text
Established Memory
+ Exploratory Memory
~~~

不要新增单独 Policy Preference Memory。

## Stage1

~~~text
one trajectory
no Existing Memory
-> Candidate + Support
~~~

Stage1 不做 historical comparison、不决定 superiority、不生成 H。

## A / Stage2

~~~text
Candidate
<-> Current Text Memory
+ small diagnostic Support
+ bounded Graph context when useful
-> minimal necessary mutation
~~~

历史 raw trajectories 是 fallback，不是每次默认输入。

## B

发现一个值得 future exploration 的 unresolved incumbent comparison。

B 不生成具体 alternative。

## C

基于 Functional Contract + Semantic Memory + real capabilities 合成 grounded local experiment。

## H

future-facing、adaptive、one-shot exploration。

Consumed != falsified。

## Graph

Graph 负责 Semantic Concept / relation / grounding / navigation / cross-trajectory organization。

Graph 不是：

~~~text
global planner
exploration controller
comparison truth engine
full action-space graph
~~~

当前任务禁止重新设计 Graph。

## Comparison ledger

当前先理解为：

~~~text
exploration identity / provenance / telemetry
~~~

Established Memory + Support 才是 epistemic source of truth。

当前不要强化 OPEN/PARTIAL/RESOLVED，也不要增加 confidence/evidence-strength taxonomy。

---

# 最近 semantic review 得到的关键结论

Phase 1F 中：

- Flash / Max 会对相似 evidence 给出不同 comparison status；
- one-sided success 有时被写成 stronger policy guidance；
- Max 即使说 comparison remains open，也可能显著改 Established Memory；
- evidence direction 与 comparison resolution 是不同问题；
- Lettuce/Tomato 还有 H retrieval/scope mismatch；
- early schema/interface difference 会在 persistent memory 中被后续放大。

当前 working hypothesis：

> 一部分 instability 可能来自 Phase 1 exploratory MVP bypass / compression 了历史 Stage1 + support-aware Stage2，使 A 职责过载。

所以当前要恢复完整 core，而不是继续补 comparison ledger。

---

# 当前 Phase 2A preparation 已完成什么

Commit：

~~~text
2dd673be18866fdc283f9fbc592433e32936e9b6
~~~

已有：

- 12 cases / 25 episode appearances；
- 7 primary / 5 secondary；
- frozen registry / digests；
- Stage1/A preparation code；
- no-model package；
- transition docs/130；
- tests；
- 0 model/API calls。

但是 researcher review 发现执行前 blocker。

---

# 你必须修的四个核心问题

## 1. prior Support 必须真正包含 semantic evidence

当前 compact prior Support 主要是 IDs / operation metadata。

需要从 frozen artifacts 机械恢复：

~~~text
representative positive
boundary / counter-support
observed context
provenance
availability
~~~

不要用 LLM重新总结历史 Support。

不要默认加载全部 historical raw trajectories。

## 2. memory selection 必须发生在 Stage1 之后

正确顺序：

~~~text
trajectory
-> Stage1 Candidate+Support
-> Candidate/problem-side memory selection
-> A
~~~

不要再用 source H / comparison ID 的巨大权重决定 semantic neighborhood。

## 3. model-visible input 与 audit provenance 分离

模型不需要看：

~~~text
artifact paths
SHA
runtime identity
source file paths
audit-only evidence IDs
~~~

拆成：

~~~text
model_visible_*.json
audit_metadata_*.json
~~~

只有 model_visible 输入进入 LLM payload。

## 4. Grounding / provenance 必须 runner-owned / mechanically valid

Stage1 event ref 必须属于 actual model-visible trajectory event set。

unknown event -> fail closed。

trajectory_id / source_h_id / source_comparison_id 由 runner bind，不让模型重新生成。

---

# 同时需要一起修的协议问题

## Evidence alignment

不要因为 task_id 一样就叫 exact matched evidence。

至少区分：

~~~text
EXACT_PUBLIC_TRAJECTORY
SAME_TASK_DIFFERENT_TRAJECTORY
~~~

必要时才加：

~~~text
SEMANTICALLY_SAME_TRAJECTORY_METADATA_DIFF
~~~

只有真正 matched evidence 才用于 Flash/Max semantic agreement。

## Claim scope

Phase 2A 的 frozen trajectory 多数只到 target acquisition。

所以 Phase 2A 当前验证：

~~~text
search-local Stage1 -> A integration
~~~

不是完整 benchmark task trajectory 的 native memory formation。

完整 completed-task Stage1 留给 Phase 2B。

## Schema

修：

~~~text
UPDATE -> updates non-empty
SUPPORT_ONLY -> must target existing memory
~~~

Phase 2B 前再恢复完整 RETIRE 等 historical primitive。

---

# 你需要实现的 executor

当前 docs/130 记录了未来 run command，但 runner 尚不存在。

请实现 versioned：

~~~text
run_phase2a_semantic_integration
~~~

逻辑：

~~~text
verify frozen inputs
-> model-visible Stage1 call
-> persist raw/usage
-> strict validation
-> runner bind provenance
-> Candidate-based memory selection
-> diagnostic prior Support
-> model-visible A call
-> persist raw/usage
-> strict validation
-> proposed mutation + audit artifacts
~~~

必须：

- 默认禁止模型调用；
- 只有显式 --allow-model-calls 才能启用；
- 当前任务中不要传该 flag；
- output path refusal-on-overwrite；
- schema/semantic invalid fail closed；
- 不 silent retry “不漂亮”的语义输出；
- Flash / Max 输出独立。

---

# Versioning

不要覆盖：

~~~text
docs/review_samples/phase2a_semantic_integration/
docs/130_phase2a_semantic_integration_transition.md
~~~

它们是 frozen v1 preparation。

新建 hardened v2 package / registry / schemas。

新建：

~~~text
docs/132_phase2a_execution_transition.md
~~~

docs/132 必须冻结：

- parent commit；
- hardened registry digest；
- package digest；
- model-visible schemas/prompts；
- audit schemas；
- prior Support extraction policy；
- Candidate-based memory selection policy；
- evidence alignment；
- executor path；
- exact future Flash/Max commands；
- tests；
- model/API calls = 0；
- stop rule。

同时更新 AGENTS / current_state status。

---

# 当前禁止事项

本轮不要：

- 调用 Flash / Max；
- 调用任何模型/API；
- 跑 Phase 2A replay；
- 跑 Phase 2B/C/D；
- 新跑 ALFWorld；
- 改 B/C/H；
- 重构 comparison ledger；
- 改 Graph；
- 加 confidence；
- 加 NONE/INDIRECT/MATCHED/DIRECT；
- 用 LLM总结历史 Support；
- 更换 case；
- 根据期望结果调 prompt；
- 覆盖历史 Phase 1 artifacts；
- 覆盖 Phase 2A v1 package。

---

# Tests

至少新增/验证：

1. model-visible Stage1 不含 audit path/hash；
2. model-visible A 不含 audit path/hash；
3. Stage1 不含 Existing Memory；
4. event_ref 必须 belong to visible event IDs；
5. fake event ref fail closed；
6. provenance runner-owned；
7. memory selection only after Stage1；
8. H/comparison IDs 不主导 semantic selection；
9. frozen semantic Support 可用时必须真实进入 diagnostic view；
10. missing Support explicit unavailable；
11. exact evidence-alignment normalized input equal；
12. different trajectory classification correct；
13. UPDATE + [] rejected；
14. SUPPORT_ONLY without target rejected；
15. executor model call disabled by default；
16. explicit allow flag required；
17. executor refuses overwrite；
18. Phase 1 / Phase2A-v1 artifacts unchanged。

运行 focused tests + relevant regression + ruff/format + compileall + git diff --check。

---

# Stop condition

完成：

~~~text
hardened v2 preparation
+ executor
+ tests
+ docs/132 immutable execution transition
+ push
~~~

然后立即停止。

报告：

- commit SHA；
- changed files；
- registry/package digests；
- evidence-alignment counts；
- Support extraction coverage；
- model-visible/audit separation；
- grounding validation；
- executor commands；
- tests；
- remaining blockers；
- explicit model/API calls = 0。

不要自动开始模型执行。

Researcher 会做最后一次 pre-execution review。

如果没有新的 blocker，下一步应该是直接执行 Phase 2A，而不是继续设计第四版 architecture。
