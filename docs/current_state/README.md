# Exploratory Persistent Memory：Current-State Index

> 更新时间：2026-09-23  
> 分支：exp/minimal-exploratory-memory-validation  
> Frozen Phase 2A preparation baseline：2dd673be18866fdc283f9fbc592433e32936e9b6  
> 当前阶段：Phase 2 — Core Method Integration Validation  
> 当前 decision：PREPARATION_ACCEPTED_WITH_PREEXECUTION_BLOCKERS  
> 当前禁止：Flash/Max/model API execution；Phase 2B/C/D；Graph/comparison-ledger redesign。

本目录用于告诉新参与者“当前共识是什么”，而不是记录全部历史过程。顶层 docs/ 的历史实验文档用于追溯 evidence / protocol evolution。

---

## 新参与者最短接手路径

### 必读 1：全局设计与当前任务

1. [11_phase2_core_method_handoff.md](./11_phase2_core_method_handoff.md)  
   当前最重要的 master handoff。包含 problem、完整方法、历史设计继承、Phase 1 evidence、Phase 2 规划、不要重新打开的问题和当前唯一执行任务。

2. [../131_phase2a_preexecution_review_and_corrections.md](../131_phase2a_preexecution_review_and_corrections.md)  
   对 commit 2dd673b 的 researcher review。明确哪些 preparation 已通过、哪些是 execution blocker，以及为什么。

3. [../128_phase2_core_method_integration_validation_plan.md](../128_phase2_core_method_integration_validation_plan.md)  
   Phase 2A–2D 总体实验路线和 gate。

4. [../130_phase2a_semantic_integration_transition.md](../130_phase2a_semantic_integration_transition.md)  
   Frozen Phase 2A v1 no-model preparation transition。注意：它现在是 historical preparation baseline，不是 READY_TO_RUN transition。

### 必读 2：方法 contract

5. [02_method_architecture.md](./02_method_architecture.md)
6. [03_component_contracts.md](./03_component_contracts.md)
7. [../37_method_structural_initialization.md](../37_method_structural_initialization.md)
8. [../38_exploratory_memory_lifecycle.md](../38_exploratory_memory_lifecycle.md)

### 必读 3：为什么从 Phase 1 转向 Phase 2

9. [../126_phase1f_ma_v2_semantic_review.md](../126_phase1f_ma_v2_semantic_review.md)
10. [../127_semantic_review_bundle_handoff.md](../127_semantic_review_bundle_handoff.md)
11. [04_validation_progress.md](./04_validation_progress.md)

---

## Coding / Research Agent 直接使用的 onboarding prompt

见：

[12_new_participant_onboarding_prompt.md](./12_new_participant_onboarding_prompt.md)

该 prompt 强制新参与者先做 Inheritance Check，再修改代码，以避免：

~~~text
当前没有实现某组件
-> 误认为以前没讨论过
-> 重复设计 Stage1 / A / Graph / comparison ledger
~~~

---

## 当前一句话研究定位

Persistent Memory 可以把历史成功经验固化成 future guidance，但：

~~~text
Feasibility Evidence != Comparative Evidence
~~~

因此系统既要复用 established experience，又要识别重要但未关闭的 comparative question，并用 future-facing one-shot exploratory memory 主动获取新的 evidence，再通过 native memory-evolution path 吸收。

---

## 当前方法核心

~~~text
Trajectory
-> Stage1: Candidate + Support
-> A/Stage2: support-aware Local Knowledge Reconciliation
-> Established Memory

Pre-update Established Memory + current trajectory
-> B: unresolved comparative diagnosis
-> C: grounded local experiment
-> H: one-shot Exploratory Memory

Future H test
-> actual trajectory
-> Stage1/A again
-> Memory evolution
~~~

Graph 保持 historical design，不是本轮 exploration controller。

---

## 当前 Phase 2A 状态

v1 no-model preparation 已冻结：

~~~text
commit 2dd673be18866fdc283f9fbc592433e32936e9b6
12 cases / 25 episode appearances
7 primary / 5 secondary
0 model/API calls
~~~

但 review 发现：

1. prior Support semantic content 不足；
2. Existing Memory selection 在 Stage1 Candidate 之前完成；
3. model-visible semantics 与 audit provenance 混在一起；
4. Stage1 grounding identity 没有机械 membership 校验；
5. evidence alignment / terminology / schema / executor 仍需 hardening。

因此当前唯一工作是：

> Phase 2A Pre-execution Hardening

详见 docs/131。

---

## 当前不要重新打开

除非有新 evidence：

- B/C responsibility boundary；
- C full-source leakage boundary；
- H one-shot/adaptive semantics；
- online/offline write boundary；
- Stage1 no-Existing-Memory；
- Candidate vs Current Text Memory 作为 Stage2 主 comparison；
- historical raw trajectory 只作为 fallback；
- Graph 不是 exploration search-space controller；
- no separate Policy Preference Memory；
- no rich comparative-strength taxonomy；
- comparison ledger 当前不升级为第二套 truth store；
- native cold-start definition。

重开必须指出：

1. 新 evidence；
2. 破坏了哪个 existing assumption；
3. 为什么局部实现/evaluation 修复不够；
4. 为什么值得增加 complexity。

---

## 其它专题文档

1. [01_problem_and_contribution.md](./01_problem_and_contribution.md) — problem / contribution framing
2. [02_method_architecture.md](./02_method_architecture.md) — method architecture
3. [03_component_contracts.md](./03_component_contracts.md) — component contracts
4. [04_validation_progress.md](./04_validation_progress.md) — validation history
5. [05_paper_level_evaluation_design.md](./05_paper_level_evaluation_design.md) — evaluation design
6. [06_open_questions_and_handoff.md](./06_open_questions_and_handoff.md) — older open questions / handoff
7. [07_experiment_validation_roadmap.md](./07_experiment_validation_roadmap.md) — staged roadmap with Phase 2 update
8. [08_experiment_scale_and_model_budget.md](./08_experiment_scale_and_model_budget.md) — scale/model budget
9. [09_project_master_handoff.md](./09_project_master_handoff.md) — long project master history
10. [10_current_review_protocol.md](./10_current_review_protocol.md) — active review boundary
11. [11_phase2_core_method_handoff.md](./11_phase2_core_method_handoff.md) — current master handoff
12. [12_new_participant_onboarding_prompt.md](./12_new_participant_onboarding_prompt.md) — copyable onboarding prompt

---

## 当前 stop rule

新的参与者完成 hardened Phase 2A executor/package + docs/132 后：

~~~text
STOP
-> researcher review
-> only then authorize Flash/Max
~~~

不要自动进入 model execution。
