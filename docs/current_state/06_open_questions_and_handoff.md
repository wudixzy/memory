# 06. 当前未决问题、接手指南与下一阶段决策

> **2026-09-19 更新**：本文保留未决问题清单，但新参与者应优先阅读
> [09_project_master_handoff.md](./09_project_master_handoff.md) 和
> [10_current_review_protocol.md](./10_current_review_protocol.md)。
> 当前 active cycle 已推进到 Phase 1A Final Pre-Actor Patch；本文部分早期 readiness 表述仅作演化记录。

## 1. 当前阶段判断

项目已经从：

    Can the mechanism work?

推进到：

    Does the mechanism provide systematic value
    over fair and strong baselines?

因此当前默认策略是：

> Freeze core MVP method; shift effort to staged contribution validation.

如果没有新的反例，不再围绕少量 controlled case 持续修改 B/C/H/A。

当前正式实验路线已收束到 [07_experiment_validation_roadmap.md](./07_experiment_validation_roadmap.md)：

    Phase 0  Mechanism sanity（基本完成）
      -> Phase 1  Targeting value：C3 vs fair C2
      -> Phase 2  Native cold-start memory formation：Stage1 + A
      -> Phase 3  One-step memory evolution：K_t vs K_{t+1}
      -> Phase 4  Automatic retrieval
      -> Phase 5  Full native cold-start longitudinal system

## 2. 最优先未决问题

## Q1. C2 Generic Exploration Baseline 到底怎么定义？

这是当前最重要的实验控制问题。

需要保证 C2 与 C3：

- online interface 一致；
- one-shot authority 一致；
- lifecycle 一致；
- runtime state 一致；
- 大致 token/context budget 一致。

只拿掉：

    history-derived targeted content

否则 C3 > C2 无法解释。

## Q2. 什么时候加入 On-demand Target-time Exploration Baseline？

候选：

    C2b

它不保存 source H，而在 target 到来时现场生成 local alternative。

当前默认顺序：

    先 C1 / fair C2 / C3
    -> 若 C3 相对 C2 有稳定信号
    -> 再加入 C2b

这样先回答 history-derived targeting 是否有额外信息，再回答这种信息是否值得持久化而不是 target-time 重建。

仍需讨论：

- online cost 是否过大；
- 是否能公平控制 model capability；
- 是否应作为主表还是 appendix/ablation。

## Q3. Frozen-history 与 Closed-loop 各自承担什么结论？

必须提前写清：

### Frozen-history

支持 causal intervention claim。

### Closed-loop

支持 long-term system claim。

不能混用。

## Q4. Automatic H Retrieval 什么时候、怎么测？

当前不作为 Phase 1 的首要变量。

先用：

    oracle / structural scope match

隔离 H content + execution；在 targeted exploration、native memory formation 和至少一次 memory-evolution value 已获得可解释信号后，再进入：

    C3_oracle-match
    vs.
    C3_auto-retrieval

否则 retrieval miss 会污染 H quality 判断。

## Q5. Stage1 在什么时候接入？

当前顺序已经明确：

1. Phase 1 先 bypass Stage1，验证 C3 vs fair C2 的 targeting value；
2. 若有稳定信号，Phase 2 立即回到 method-native cold start，接入最小 Stage1 + A；
3. Stage1/A 应在 automatic retrieval 与 full longitudinal system 之前完成 upstream realizability audit。

Stage1 不是最终才补的工程模块，而是决定方法能否从空 experience memory 自然长出可信 established memory 的关键科学 gate。

## Q6. 选哪 2–3 个 Benchmark？

下一阶段需要真正筛选。

候选不能只看名气，应根据：

- repeated tasks；
- memory authority；
- plausible local alternatives；
- observability；
- replay/randomization；
- actor reliability；
- cost；

打 admission memo。

## Q7. Main Actor Backbone 是什么？

当前 Qwen3.8-Flash：

- 成本低；
- 足够做 MVP；
- semantic execution stability 不足以支撑所有 main conclusions。

需要筛更可靠 backbone。

但所有 C0–C3 条件必须共享同一个 actor。

## Q8. Evaluation Sample Size

当前不要预设最终规模。

先 pilot，估计：

- base success；
- task variance；
- H activation；
- effect size；
- failure rates。

然后再确定 repetitions / sample count。

## 3. 当前建议不要重新打开的问题

除非出现新的强证据，不要重新讨论：

- B 是否应该提出 concrete alternative；
- C 是否应该看到完整 source trajectory；
- H 是否应该保存 fixed future action sequence；
- H 是否应该跨多个 episode 自动重复执行；
- A 是否可以看到 E0；
- online 是否应该做 semantic memory update；
- 是否需要复杂 search controller；
- 是否需要 rule-based fallback planner；
- 是否应该把 B/C 放进 online critical path。

当前默认答案都是：

    No.

## 4. 当前基础设施可直接复用的部分

- ALFWorld TextWorld carrier；
- action-index actor interface；
- current admissibility validation；
- probe_runtime_state；
- H persistent/runtime lifecycle；
- E1-only A input boundary；
- evaluator leakage checks；
- replayable episode spec；
- actual execution pairing proof；
- artifact persistence；
- token/cost telemetry；
- 中文 human review package。

## 5. 当前还没有的 Full-System 部分

- production Stage1；
- automatic H retrieval；
- mature established-memory consolidation；
- broad multi-benchmark adapters；
- fair C2 baseline implementation；
- C2b on-demand baseline；
- longitudinal sequence runner；
- paper-level statistics pipeline。

## 6. 推荐给新参与者的阅读顺序

如果只想理解研究问题：

    README
    -> 01_problem_and_contribution

如果要实现方法：

    02_method_architecture
    -> 03_component_contracts
    -> AGENTS.md

如果要理解目前证据：

    04_validation_progress
    -> docs/human_review/
    -> docs/60_pairing_infrastructure_validation_results.md

如果要设计下一阶段实验：

    05_paper_level_evaluation_design
    -> docs/61_paper_level_evaluation_design.md
    -> 本文

## 7. 新 Agent / 新成员开始工作前应该回答的五个问题

1. 我现在是在验证 method mechanism，还是在验证 paper-level contribution？
2. 我修改的是科学方法，还是实验 harness？
3. 我的信息是否会造成 evaluator/oracle leakage？
4. 这个 failure 应该归因于 actor、retrieval、memory、pairing，还是方法本身？
5. 我是否正在为了少量 case 的漂亮结果增加不必要复杂度？

如果这五个问题答不清楚，不建议直接改代码。

## 8. 下一轮讨论的推荐议程

### 第一部分：Phase 1 Baseline Fairness

- C2 的 structured generic H 怎么定义；
- C1/C2/C3 如何共享 authority / lifecycle / actor / budget；
- target-pool scope 如何在看 outcome 前预注册；
- C2b 暂不要求同时实现。

### 第二部分：Benchmark Admission

重新筛 2–3 个候选 benchmark。

每个 benchmark 都明确：

- Phase 1 可以观察哪一层；
- 是否支持后续 Phase 2 native formation 与 Phase 5 longitudinal sequence；
- base actor 是否可靠；
- pairing/randomization 是否成立；
- objective 是否原生区分 behavior quality；
- 成本；
- failure taxonomy。

### 第三部分：Actor / Pilot Protocol

- main actor；
- weak-model robustness actor；
- base reliability threshold；
- pilot run count；
- token/cost budget；
- statistical unit。

### 第四部分：Phase 1 Frozen-History Protocol

- 固定 warm-start K*；
- oracle / structural H match；
- C1/C2/C3；
- artifact / telemetry；
- stop rule。

Auto retrieval、production Stage1、longitudinal runner 暂不进入下一实现周期。

## 9. 下一阶段完成标准

在启动 Phase 1 pilot 前，至少应该确定：

- 公平 C2；
- 固定 warm-start K* 的实验边界；
- scope-matched target-pool sampling protocol；
- Frozen-history protocol；
- 至少 1 个先行 admitted benchmark / carrier，另有 1–2 个候选 admission memo；
- main actor 与 base reliability screen；
- metric table；
- statistical unit；
- pilot budget；
- failure attribution schema；
- Phase 1 stop rule。

当前不要求先完成：

- C2b；
- automatic retrieval protocol；
- production Stage1；
- full longitudinal runner。

这些由 Phase 1–3 的科学 gate 决定是否值得继续投入。

## 10. 当前仓库状态

Repository：

    https://github.com/wudixzy/memory.git

Branch：

    exp/minimal-exploratory-memory-validation

当前 Phase 1A pre-pilot baseline commit：

    a738366b5d8e1905a430f2403bf85c1813cbfffd

当前最重要历史文档：

- docs/54_cleanup_attribution_validation_results.md
- docs/57_action_index_and_chinese_review_results.md
- docs/human_review/
- docs/60_pairing_infrastructure_validation_results.md
- docs/61_paper_level_evaluation_design.md

## 11. 最后一条项目纪律

当前阶段最需要避免的是：

> 在 evaluation 还没有定义清楚之前，继续通过 patch controlled case 来“改善方法”。

新的方法复杂度必须回答一个明确问题，并由新的 evidence 驱动。

否则优先：

    improve evaluation,
    not architecture.
