# 05. Paper-level Evaluation Design：当前方案与待收束控制变量

## 1. Evaluation 的核心目标

正式评测不再只问：

> 某个 H 能不能在某个 case 上 work？

而要回答：

1. history-derived targeted exploratory memory 是否改善未来行为？
2. 它在什么情况下帮助、什么情况下伤害？
3. 它是否优于 generic exploration？
4. 它相比 target-time on-demand exploration 是否有额外价值？
5. 性能收益与 online/offline cost trade-off 如何？
6. 探索产生的 evidence 是否能被 A 稳定吸收并在后续任务产生 benefit？

## 2. Core Conditions

当前基础条件：

### C0 — No Memory

只有普通 actor / task context。

### C1 — Retrospective Established Memory

C0 + established memory。

测量：

> retrospective memory 本身的作用。

### C2 — Retrospective + Generic Exploration

C1 + generic exploratory mechanism。

### C3 — Retrospective + History-derived Targeted Exploratory Memory

C1 + B/C 生成并持久化的 H。

当前工作的主 contribution comparison：

    C3 vs C2

而不是 C3 vs C0。

## 3. C2 必须避免 Strawman

C2 不能只是：

    "Please explore alternatives."

而 C3 却拥有：

- structured probe policy；
- one-shot authority；
- stop condition；
- runtime lifecycle；
- probe_runtime_state。

否则 C3 赢可能只是因为接口更强。

公平 C2 应尽量匹配：

- same online memory object/interface；
- same authority；
- same lifecycle；
- same action/probe status interface；
- similar context/token budget。

区别只在：

### C2

generic exploratory content，不来自历史 unresolved comparison。

### C3

history-derived targeted content。

只有这样：

    C3 > C2

才真正说明 targeted historical information 本身有价值。

## 4. 值得考虑的 Strong Baseline：On-demand Exploration

潜在 baseline：

    C2b = target-time on-demand local exploration synthesis

它不持久化 source-derived H。

在 target task 到来后，根据当前 context 临时生成 local alternative。

它回答：

> 为什么一定要把 unresolved comparison 持久化？未来 task 到来后现场想一个 alternative 不行吗？

同时它能形成成本对比：

### C3

    heavier offline
    lighter online

### C2b

    lighter history maintenance
    heavier online synthesis

C2b 是否进入最终 core table 还需结合成本与 benchmark 可行性决定，但值得优先审查。

## 5. 两套必须分开的 Evaluation Regime

## 5.1 Frozen-history Intervention Evaluation

所有条件共享相同：

    source history
    K_pre
    target task/state
    actor
    environment
    step cap

只改变 intervention：

    C0 / C1 / C2 / C3

回答：

> 当前 memory/exploration intervention 的 causal effect 是什么？

这是最干净的机制/贡献评测。

## 5.2 Full Closed-loop Evolution

各条件独立经历：

    episode_1
      -> memory update
    episode_2
      -> memory update
    ...

回答：

> 长期运行后整个 memory system 是否变得更好？

这里不同 condition 的历史会逐渐分叉，因此不能再把单个 future episode 的差异简单解释为局部 H causal effect。

论文中应把两者明确分开。

## 6. Conditional Effect 与 Full-System Effect

不能只选择：

    B = OPEN
    C = CREATE
    researcher confirms scope match

的 target 来报告主结果。

否则产生 selection bias。

需要同时报告：

### Conditional Mechanism Effect

在正确 H 存在并匹配时：

    C3 vs C2

回答：

> H 本身有没有用？

### End-to-End System Effect

自然 sequence 中全部包含：

- B NONE；
- C NONE；
- retrieval miss；
- wrong activation；
- helpful H；
- harmful H；
- actor failure。

回答：

> 完整方法整体有没有用？

## 7. Retrieval 分层

当前 MVP 主要采用 researcher-confirmed scope match。

正式系统应拆成：

### C3_oracle-match

gold/researcher confirmed H match。

用于隔离：

    H content + execution quality

### C3_auto-retrieval

真实 retrieval + activation。

用于测试：

    full system

这样可以把失败区分为：

- retrieval failure；
- H content failure；
- target-time grounding failure；
- actor execution failure。

## 8. A 的 Baseline 公平性

Full-loop 中 C1/C2/C3 应尽量共享同一个 A reconciliation mechanism。

区别在 evidence source：

### C1

normal trajectory evidence。

### C2

normal + generic exploratory evidence。

### C3

normal + targeted exploratory evidence。

否则 C3 的长期收益可能只是因为它拥有额外 update channel。

## 9. Stage 1 Evaluation Staging

### Phase I

继续 bypass Stage1。

目标：

> 隔离 B/C/H contribution。

### Phase II

接入最小 Stage1。

目标：

> 测 full system extraction + memory evolution。

如果 Phase II performance 下降，就能判断：

- Stage1 extraction；
- B；
- C/H；
- retrieval；
- actor；

分别在哪里失败。

## 10. Metrics

## 10.1 End-to-End

- task success；
- reward / quality；
- steps / tool calls；
- input/output tokens；
- API cost；
- online latency。

## 10.2 Mechanism

- B OPEN rate；
- B precision / recall（人工标注 subset）；
- C CREATE rate；
- usable-probe rate；
- H retrieval rate；
- activation rate；
- target-time grounding success；
- incremental behavioral effect；
- productive-evidence rate；
- positive / negative evidence frequency；
- probe termination；
- abort / recovery；
- downstream completion；
- probe-induced failure。

## 10.3 Memory Evolution

- A update rate；
- evidence-supported update；
- over-generalization；
- under-update；
- resolved-question reopening；
- memory growth；
- retrieval context cost；
- later-task benefit。

## 11. Failure Attribution

建议统一分类：

    transport/interface failure
    semantic actor failure
    retrieval/activation failure
    H grounding/authority failure
    probe-control failure
    task continuation failure
    A/update failure
    carrier/pairing failure

不要把所有失败都算成 method failure。

## 12. Actor Backbone

Qwen3.8-Flash 已经证明：

- 足够做很多 MVP mechanism validation；
- 但 long-horizon semantic reliability 有明显噪声。

因此正式主结果应先做：

    base actor reliability screening

选择可靠 enough 的 main backbone。

Qwen3.8-Flash 可以保留：

    weak-model robustness condition

C0–C3 内 actor 必须完全一致。

## 13. Benchmark Admission Criteria

候选 benchmark 必须逐项检查：

- sequential / repeated task structure；
- history 对 future task 有意义；
- multiple plausible local realizations；
- memory 有 incremental authority；
- success/quality/cost signal；
- full trajectory/tool call 可观测；
- replayable 或有 defensible randomized protocol；
- base actor 足够可靠；
- 支持 positive / negative / ambiguous evidence；
- 成本可控。

不要因为 benchmark 知名就直接录取。

建议每个候选 benchmark 先做 <=10 个 real-case admission audit：

- base success；
- failure taxonomy；
- reset/replay；
- unresolved comparison 是否真实存在；
- one positive example；
- one negative/ambiguous example；
- online/offline rough cost。

## 14. Pairing / Randomization

如果 benchmark 支持 deterministic replay：

- 保存 actual pairing proof；
- E0/E1 必须对应真正执行的 episode；
- 禁止 discarded preflight reset 作为 proof。

如果 carrier 无法 deterministic replay：

- 设计明确 randomized repeated protocol；
- 不能伪装成 matched causal comparison。

## 15. Statistical Unit

统计单元应是：

    task
    或 source-target sequence

不是 actor step / LLM call。

Repeated runs 属于 nested repetitions。

当前类似：

    20 tasks x 3 reps

只能作为 pilot assumption。

最终样本规模应根据 pilot 的：

- base rate；
- task variance；
- effect size；
- H activation rate；

决定。

## 16. Cost Accounting

必须分开：

### Online

- retrieval；
- rerank；
- memory/H context tokens；
- actor calls；
- tool/environment latency；
- runtime bookkeeping。

### Offline

- Stage1；
- A；
- B；
- C；
- consolidation；
- embedding/index refresh。

这种拆分也是方法的重要工程属性。

## 17. 当前推荐的评测推进顺序

### Step 1

把 C2 定义成真正公平 baseline。

### Step 2

决定是否加入 C2b on-demand exploration。

### Step 3

筛选 2–3 个 benchmark candidate。

### Step 4

做 base actor reliability + benchmark admission audit。

### Step 5

先做 Frozen-history pilot。

### Step 6

加入 auto retrieval。

### Step 7

最后接 Stage1 + full closed-loop longitudinal evaluation。

不要一次性把所有模块和 benchmark 都接上。
