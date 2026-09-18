# 06. 当前未决问题、接手指南与下一阶段决策

## 1. 当前阶段判断

项目已经从：

    Can the mechanism work?

推进到：

    Does the mechanism provide systematic value
    over fair and strong baselines?

因此当前默认策略是：

> Freeze core MVP method; shift effort to evaluation design.

如果没有新的反例，不再围绕少量 controlled case 持续修改 B/C/H/A。

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

## Q2. 是否加入 On-demand Target-time Exploration Baseline？

候选：

    C2b

它不保存 source H，而在 target 到来时现场生成 local alternative。

需要讨论：

- 是否是 reviewer 很可能要求的强 baseline；
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

## Q4. Automatic H Retrieval 怎么测？

需要至少拆：

    oracle/researcher match
    vs.
    automatic retrieval

否则 retrieval miss 会污染 H quality 判断。

## Q5. Stage1 在什么时候接入？

建议不要立即接。

先完成 B/C/H 的正式 intervention evaluation，再加入 Stage1。

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

### 第一部分：Baseline Fairness

- C2 的结构化 generic H 怎么定义；
- 是否加入 C2b；
- C1/C2/C3 的 A update 是否统一。

### 第二部分：Evaluation Regimes

- Frozen-history；
- Oracle H match；
- Auto retrieval；
- Full closed-loop。

### 第三部分：Benchmark Audit

重新筛 2–3 个候选 benchmark。

每个 benchmark 都明确：

- 可以观察哪一层；
- base actor 是否可靠；
- pairing/randomization 是否成立；
- 成本；
- failure taxonomy。

### 第四部分：Actor / Budget

- main actor；
- weak-model robustness actor；
- API vs local；
- pilot run count；
- token/cost budget。

## 9. 下一阶段完成标准

在启动 broad run 前，至少应该确定：

- 公平 C2；
- 是否有 C2b；
- Frozen-history protocol；
- retrieval protocol；
- 2–3 admitted benchmark；
- main actor；
- metric table；
- statistical unit；
- pilot budget；
- failure attribution schema。

如果这些没定清楚，不建议直接启动大规模实验。

## 10. 当前仓库状态

Repository：

    https://github.com/wudixzy/memory.git

Branch：

    exp/minimal-exploratory-memory-validation

当前 evaluation-transition baseline commit：

    36d29c440906eaf0c8060f7c2c00174f9bdc00a8

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
