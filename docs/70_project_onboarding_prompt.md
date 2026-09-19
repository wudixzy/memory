# Project Onboarding Prompt：给新研究者 / 新 Agent 的接手提示词

你正在接手一个 Persistent Agent Memory 研究项目。请不要从零重新构思，也不要先写代码。你的第一任务是准确理解当前问题、方法、证据边界和实验 gate，然后作为研究合作者继续推进。

Repository：

    https://github.com/wudixzy/memory.git

Branch：

    exp/minimal-exploratory-memory-validation

当前基线应至少包含：

    a738366b5d8e1905a430f2403bf85c1813cbfffd

或其后继 commit。

## 第一步：确认仓库状态

先检查：

- 当前 branch；
- HEAD commit；
- workspace 是否 clean；
- 最近 3–5 个 commit；
- 不要切到旧 branch 后误读历史状态。

如果 HEAD 已经比上述 commit 更新，优先 review 最新 diff，但必须先理解当前 master handoff。

## 第二步：按顺序阅读

必须先读：

1. docs/current_state/09_project_master_handoff.md
2. docs/current_state/10_current_review_protocol.md
3. AGENTS.md

然后根据任务补读：

### 科学问题

- docs/current_state/01_problem_and_contribution.md

### 方法

- docs/current_state/02_method_architecture.md
- docs/current_state/03_component_contracts.md

### 当前证据

- docs/current_state/04_validation_progress.md
- docs/45_b_c_boundary_corrected_retest_results.md
- docs/51_local_c_a_closure_validation_results.md
- docs/57_action_index_and_chinese_review_results.md
- docs/60_pairing_infrastructure_validation_results.md

### 正式实验路线

- docs/current_state/05_paper_level_evaluation_design.md
- docs/current_state/07_experiment_validation_roadmap.md
- docs/current_state/08_experiment_scale_and_model_budget.md

### 当前 Phase 1

- docs/63_phase1_fair_c2_specification.md
- docs/64_phase1_warm_start_k_star_provenance.md
- docs/65_phase1_target_pool_sampling_protocol.md
- docs/67_phase1_actor_reliability_screening_protocol.md
- docs/68_phase1_targeting_value_readiness.md
- docs/69_phase1_pre_pilot_correction_results.md

## 第三步：先用自己的话复述项目

在建议任何方案前，请先给出一个简洁但具体的理解，至少包含：

1. 为什么 feasibility evidence 不等于 comparative evidence；
2. Established Memory 与 Exploratory Memory 的区别；
3. Stage1 / A / B / C / H 的职责；
4. 为什么 B 不提出 concrete alternative，C 才 synthesis probe；
5. 为什么 C 不看完整 source trajectory；
6. source grounding 与 future target grounding 的区别；
7. H 为什么 one-shot；
8. heavy-offline / light-online 原则；
9. method-native cold start：G0 = G_tool，experience memory 为空；
10. 为什么 Phase 1 仍使用 warm-start K*；
11. 为什么主 comparison 是 C3 vs C2；
12. 当前 Phase 1A 的 claim 为什么只能局限于 receptacle-search family。

如果无法准确复述这些，不要进入实现。

## 第四步：理解当前研究阶段

当前项目不是在问：

    Can the mechanism run at all?

这个阶段基本过去了。

现在最重要的是：

    Does history-derived targeting provide incremental value
    over a fair structured generic exploration baseline?

当前实验顺序：

    Phase 0  Mechanism sanity
    -> Phase 1 Targeting value
    -> Phase 2 Native cold-start memory formation
    -> Phase 3 One-step memory evolution
    -> Phase 4 Automatic retrieval
    -> Phase 5 Full longitudinal system

不要把 Phase 5 的完整系统提前实现。

## 第五步：理解当前真实证据

当前已有较强支持的是：

- B/C responsibility boundary；
- local fact-only C synthesis；
- future-facing adaptive H；
- H behavioral authority；
- one-shot lifecycle；
- target-time grounding；
- E1-only A；
- action-index；
- mechanical runtime bookkeeping；
- replayable pairing proof；
- public-only target registry；
- fail-closed Phase 1 runner scaffolding。

当前没有支持的是：

- C3 > fair C2；
- main actor 已通过 reliability gate；
- production Stage1；
- native cold-start memory formation；
- automatic retrieval；
- later-task K_t+1 benefit；
- multi-family generality；
- full closed-loop value。

不要把“机制能跑”写成“方法有效”。

## 第六步：当前 review 重点

如果当前 HEAD 仍处在 a738366 附近，请重点 review：

1. calibration 是否真正 in-domain；
2. probe budget 是否公平；
3. source-H manifest 是否有 referential integrity；
4. H-family applicability 是否 public-only；
5. scientific runner 是否拒绝 pending/rejected actor；
6. C2/C3 context 是否对称；
7. 所有选择是否 outcome-blind；
8. source/target/calibration 是否 disjoint；
9. source provenance 是否始终 model-invisible；
10. claim 是否越界。

请按 10_current_review_protocol.md 输出：

- Verdict；
- Must-fix blockers；
- Non-blocking issues；
- Evidence checked；
- Allowed claims；
- Forbidden claims；
- Next gate。

## 第七步：方法冻结纪律

没有新 evidence 时，不要重新打开：

- B 是否生成 alternative；
- C 是否看 source full trace；
- H 是否 fixed action sequence；
- H 是否重复多个 episode；
- A 是否看 E0；
- online semantic updater；
- online B/C；
- graph planner；
- VOI controller；
- rule-based fallback；
- global trajectory planning。

如果你确实认为这些需要改，必须明确：

1. 哪个新 observation 破坏了当前设计；
2. 为什么不是 evaluation/harness 问题；
3. 最小修改是什么；
4. 新修改如何实验验证。

## 第八步：实验纪律

任何正式实验都必须区分：

### Scientific unit

task / source-target sequence / memory-update event / longitudinal stream

### Repetition

nested execution repetition

不要把：

    20 targets × 3 arms × 2 reps = 120 episodes

写成：

    n = 120

当前 Phase 1A 的 scientific n 是 20 target units。

## 第九步：禁止信息泄漏

任何 sample selection、C2、C3、runner 都不能使用：

- hidden placement；
- PDDL answer；
- oracle route；
- evaluator expected winner；
- future target outcome；
- researcher knowledge that H will help。

Target-time actor 只能看到它合法应该看到的 public state、memory 和 runtime facts。

## 第十步：工作方式

如果任务是 review：

- 先读 diff；
- 再查关键 implementation；
- 再查 focused tests；
- 区分 design intention 与 enforced invariant；
- 不只相信 README。

如果任务是 coding：

- 严格跟 AGENTS.md；
- 只实现当前 gate；
- 不扩大 scope；
- 不执行未经授权的 paid/broad run；
- commit + push；
- 返回 exact tests/results/blockers。

如果任务是研究讨论：

- 优先攻击当前核心假设；
- 不迎合已有设计；
- 但不要在无证据时增加方法复杂度。

## 第十一步：当前最终目标

论文故事最终希望证明：

> Persistent memory should not only reuse what worked; it should also preserve and act on decision-relevant comparative uncertainty. History-derived exploratory memory can turn unresolved comparisons into targeted future probes, acquire evidence that ordinary reuse would suppress, and feed that evidence back into memory evolution.

但目前只完成到进入首次严肃 targeting-value experiment 的前夜。

你的工作是：

> 在不破坏 attribution 的前提下，把项目推进到下一 scientific gate，并诚实报告 negative evidence。
