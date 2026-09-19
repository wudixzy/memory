# Exploratory Persistent Memory：当前状态总索引

> 更新时间：2026-09-20  
> 分支：exp/minimal-exploratory-memory-validation  
> 当前项目接手基线 commit：7e98ebaf550f4e57ea7a80c43e203f9b7cec4f13

这组文档不是历史讨论日志，而是对当前项目共识、已经完成的验证、仍未解决的问题和下一阶段实验设计的整理。后续新参与者、新 Agent 或组会讨论应优先从这里进入；顶层 docs/ 中更早的文档主要用于追溯设计演化和实验细节。

## 新参与者最快接手路径

如果目标是无缝加入当前讨论，不建议先从历史 docs 顺序读起。优先：

1. [09_project_master_handoff.md](./09_project_master_handoff.md)  
   单一 master handoff：背景、问题、方法、初始化、实验路线、证据等级、当前 Phase 1A 状态。

2. [10_current_review_protocol.md](./10_current_review_protocol.md)  
   当前 review contract：哪些已经接受、哪些是 blocker、怎样判断是否能进入 Actor Gate。

3. 根目录 AGENTS.md  
   当前 coding cycle 的实现边界和 stop rule。

然后再按需要深入下面的专题文档。

## 专题文档推荐阅读顺序

1. [01_problem_and_contribution.md](./01_problem_and_contribution.md)  
   先理解为什么要做 exploratory persistent memory、核心问题是什么、我们真正声称的 contribution 是什么。

2. [02_method_architecture.md](./02_method_architecture.md)  
   当前最终方法架构、offline / online 划分、Stage 1 / A / B / C / H 数据流、运行时生命周期。

3. [03_component_contracts.md](./03_component_contracts.md)  
   各模块的信息边界、职责、输入输出语义和明确禁止事项。适合实现者和 reviewer 使用。

4. [04_validation_progress.md](./04_validation_progress.md)  
   从早期失败到当前 MVP 的实验历程、关键修正、哪些结论已获得支持、哪些仍只是 qualitative evidence。

5. [05_paper_level_evaluation_design.md](./05_paper_level_evaluation_design.md)  
   当前正式评测设计草案：C0–C3、generic exploration baseline、公平控制、Frozen-history 与 Closed-loop、retrieval 分层、指标和成本。

6. [06_open_questions_and_handoff.md](./06_open_questions_and_handoff.md)  
   当前尚未解决的科学问题、接下来应该讨论什么、不应该重新打开什么，以及新人接手时的操作顺序。

7. [07_experiment_validation_roadmap.md](./07_experiment_validation_roadmap.md)  
   当前正式实验推进路线：Phase 0–5、每阶段科学问题与 stop rule、benchmark admission、native cold-start 与 full-system evaluation 的进入条件。

8. [08_experiment_scale_and_model_budget.md](./08_experiment_scale_and_model_budget.md)  
   各阶段 pilot / paper-scale 数据量、repetition、模型角色、actor episode 数量级、成本升级条件与下一实现周期规模。

## 当前一句话定位

现有 persistent memory 主要擅长复用已经成功的历史经验，但“历史上成功过”只提供 feasibility evidence，并不等价于“这个 realization 相比替代方案更好”。本工作希望 memory 不仅保存 established knowledge，还能从历史行为中识别重要但尚未解决的 comparative question，并把它转化成 future-facing、one-shot、grounded 的 exploratory memory，使未来匹配任务主动产生新的 comparative evidence。

核心链路：

    History
      -> Unresolved Comparison
      -> Targeted Future Probe
      -> Comparative Evidence
      -> Memory Evolution

## 当前方法状态

已经基本冻结：

- feasibility evidence != comparative evidence；
- established memory / exploratory memory 的区分；
- B 负责发现值得打开的 incumbent comparison；
- C 负责把问题变成 grounded local probe policy；
- H 是 one-shot exploratory memory，而不是 established knowledge；
- source grounding 与 future target grounding 分离；
- online 轻量、offline 较重；
- online 只记录事实，offline 才写 semantic knowledge；
- A 只能根据实际 E1 evidence 做 conservative reconciliation；
- action-index、probe_runtime_state、pairing proof 等属于实验/运行时 harness，而不是方法贡献本身。

尚未完成：

- automatic H retrieval；
- Stage 1 的 full-system 接入；
- C3 相对公平 generic exploration baseline 的正式优势；
- full closed-loop longitudinal memory evolution；
- 多 benchmark、多 actor 的 paper-level evaluation；
- 跨 carrier 的 generality。

## 当前实验基础设施状态

当前 pinned ALFWorld TextWorld 上：

- action-index 已移除 exact action-string reproduction 噪声；
- probe_runtime_state 只提供机械 public progress；
- actual E0/E1 episodes 使用 replayable episode specification 建立 pairing proof；
- Apple/Microwave 与 Pencil/Shelf 的 reset audit 支持当前 pinned carrier 的稳定 replay；
- pairing、action legality、H lifecycle 均已可审计；
- 当前主要剩余执行噪声来自 actor semantic reliability，而不是 action string 或 pairing interface。

详细证据见：

- docs/57_action_index_and_chinese_review_results.md
- docs/60_pairing_infrastructure_validation_results.md
- docs/human_review/
- docs/61_paper_level_evaluation_design.md

## 使用原则

这组文档描述“当前共识”，不是要求后续所有设计永远不变。但如果要重新打开一个已经冻结的问题，应明确指出：

1. 新发现了什么反例或证据；
2. 它破坏了当前哪个假设；
3. 为什么不能通过 evaluation 或局部实现修正来处理；
4. 为什么值得重新增加方法复杂度。

当前阶段默认优先级已经从“这个 idea 能不能跑”转向：

    这个 idea 相比合理 baseline 是否具有系统性、可重复、可归因的价值？


## 当前实验推进路线

后续默认按以下科学 gate 恢复系统复杂度：

    Phase 0  Mechanism sanity（基本完成）
      -> Phase 1  Targeting value：C3 vs fair C2
      -> Phase 2  Native cold-start memory formation：Stage1 + A
      -> Phase 3  One-step memory evolution：K_t vs K_{t+1}
      -> Phase 4  Automatic retrieval / activation
      -> Phase 5  Full native cold-start longitudinal system

从 Phase 1 开始使用真实 benchmark task distribution，但仍属于 controlled benchmark-backed evaluation；Phase 3 才开始形成较正式的 method-level benchmark claim；Phase 5 才是完整 cold-start system 的正式 longitudinal benchmark evaluation。详见 [07_experiment_validation_roadmap.md](./07_experiment_validation_roadmap.md)。


## 当前最重要入口

- **完整项目交接**：[09_project_master_handoff.md](./09_project_master_handoff.md)
- **当前 review 方法**：[10_current_review_protocol.md](./10_current_review_protocol.md)
- **新参与者提示词**：docs/70_project_onboarding_prompt.md
- **当前实现契约**：根目录 AGENTS.md

当前 active cycle 是 **Phase 1A Actor-Stack Development Diagnostic (D1/D2)**。
Gate B1 已 FAIL，且 docs/72 的逐轨迹诊断显示失败不能主要归因于模型；当前优先隔离
K*/carrier contract 与 raw-history representation 两个 confound。

原 10 个 hard-calibration tasks 已转为 development evidence。D1/D2 必须完整保留原始逐步
trajectory 供下一轮 review；不得在这些任务上调优后继续把它们当 independent Gate B1。
正式计划见 [docs/73_phase1_actor_stack_development_diagnostic_plan.md](../73_phase1_actor_stack_development_diagnostic_plan.md)。

原 20 个 Phase 1A targets 继续封存。若数据允许，应在 D1/D2 模型调用前从未使用的 pinned
ALFWorld split 以 public-only deterministic protocol 预注册 fresh Gate B1-R，但本 cycle 不执行它。
D2 后 STOP，等待 researcher review。
