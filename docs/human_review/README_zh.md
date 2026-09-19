# Exploratory Memory MVP：中文双语人工 Review 包

本目录用于研究者直接检查当前 ALFWorld TextWorld MVP 的真实输入、可见模型输出和执行轨迹。它不是自动评分器，也不是对模型隐藏推理的重建。

## 1. 当前方法简图

```text
B：识别值得打开的重要未决 incumbent comparison
    ↓
C：综合一个 grounded local probe policy
    ↓
H：一次性 exploratory memory / future-facing probe guidance
    ↓
Online：逐步读取最新 observation 与 admissible_actions，执行一次 action
    ↓
Evidence：产生或未产生 comparative evidence
    ↓
A：只根据实际 E1 episode evidence 保守 reconcile
```

本轮另有一个 harness 层变化：actor 返回 `action_index`，runner 按当前有序 `admissible_actions` 列表做精确索引，随后执行 resolved exact action。这个变化不改变 B/C/H/A 的科学职责。

## 2. 术语表

| English | 中文说明 |
|---|---|
| established memory | 已建立记忆：历史已确认、可在相应 scope 下复用的经验。 |
| exploratory memory / H | 探索性记忆 H：一次性的、用于测试一个局部替代方案的 future-facing guidance；不是已证实知识。 |
| Functional Contract | 功能契约：局部行为进入前可用的状态、局部功能、后续必须保留的状态和约束。 |
| probe policy | 探针策略：根据未来实际 observation 自适应选择局部动作，而不是预先写死完整 action sequence。 |
| source grounding | 源任务 grounding：C 生成 H 时用来证明入口动作在 source entry state 合法的证据。 |
| `probe_runtime_state` | 由已执行公共动作/观察机械汇总的探针进度，例如已访问 receptacle 和 probe action 数量；不选择下一动作。 |
| `EVIDENCE_OBTAINED` / `PROBE_EVIDENCE_READY` | 已有足够公共观察供 A 判断；不代表 hypothesis 为真或全局最优。 |
| A reconciliation | A 根据实际 target E1 轨迹、probe evidence 和环境结果，决定 `NO_CHANGE` 或 scope-limited `UPDATE`。 |
| action-index harness | actor 返回 zero-based `action_index`，代码只做 `admissible_actions[action_index]` 精确映射。 |

## 3. 样本索引

| 文件 | 样本 | 用途 | Artifact provenance |
|---|---|---|---|
| `01_b_open_and_controls_zh.md` | Sample A：P005 `OPEN`；Sample B：N1 `NONE` | 检查 B 的 comparison diagnosis 与正负控制差异 | 两者均为 `ORIGINAL SAVED ARTIFACT` |
| `02_c_and_h_zh.md` | Sample C：clean P005 C/H | 检查 fact-only local packet、C 是否独立合成 alternative、H 是否 future-facing | `ORIGINAL SAVED ARTIFACT` |
| `03_laptop_online_attribution_zh.md` | Sample D：Laptop 旧 loop 与 runtime-state 诊断 | 检查接口/状态表示归因 | 两个运行均为 `ORIGINAL SAVED ARTIFACT` |
| `04_cross_task_transfer_zh.md` | Sample E：SprayBottle transfer；Sample F：Apple action-index sanity | 检查跨任务 H、stepwise probe、action-index 与失败边界 | SprayBottle 为既有 `ORIGINAL SAVED ARTIFACT`；Apple 为本轮 `ORIGINAL SAVED ARTIFACT` |
| `05_a_reconciliation_zh.md` | Sample G：A 的 `NO_CHANGE` 与 `UPDATE / REFINE` | 检查 A 是否只绑定 E1 evidence、是否过度泛化 | `ORIGINAL SAVED ARTIFACT` |

本机所有上述 artifact 均已存在，因此本包没有 `RECONSTRUCTED REPRODUCTION` 样本，也没有为了挑选更好结果而重复重跑旧样本。新 action-index 运行的结果目录为：

```text
artifacts/exploratory_memory_mvp/action-index-sanity-20260916-v2/
```

运行 artifact 默认被 `.gitignore` 忽略；本文档只追踪经过压缩、去除运行噪声的 review excerpt。完整英文原始 JSON、每步 prompt、raw response、environment result 请按各文件末尾的 artifact path 查阅。

为便于远程协作，本轮还提交了一个小型但完整的 D0/D1/D2 逐轨迹子集：

```text
docs/human_review/trajectory_artifacts/phase1_actor_stack_core/
```

其中包含同四个 task（Laptop、Shelf cool、CoffeeMachine、SoapBar）在三个变体中的
12 条完整 task artifact，均为 `ORIGINAL SAVED ARTIFACT`。选择理由和每条轨迹的机械
结果见该目录下的 `README.md`；完整十任务运行根目录仍只保留在本地 ignored artifacts。

## 4. 阅读边界

- `case_type`、evaluator rationale、oracle alternative/location/outcome 和 `review_only` 内容只在文档中作为 reviewer-side 注释出现，绝不能误认为模型输入。
- 模型原文保留在 fenced code block 中；紧随其后的中文是翻译或字段解释，不是模型原话。
- 长 observation 只在正文保留与判断直接相关的句子；完整原文由 artifact path 指向。
- old transfer artifacts 使用的是本轮 action-index 改造之前的 exact-string actor interface；Apple Sample F 才是新的 `action_index` interface。这个版本差异在相应章节中明确标注。

## 5. 人工 Review checklist

### B

- B 打开的 comparison 是否真的值得打开？
- `NONE` 控制是否有真实的 comparative evidence，而不是仅仅因为没有 alternative？
- B 是否只诊断 incumbent comparison，没有越界替 C 设计 alternative？

### C / H

- C 的输入是否只有局部事实、Functional Contract 和真实 capability？
- C 是否自己提出 alternative，而不是从 researcher hint 中抄答案？
- H 是否太具体（source entity shortcut）或太抽象（`explore more`）？
- `source_grounding` 与 future-facing H 是否真正分离？

### Online

- H 是否实际影响了局部行为，还是 prompt 直接指定了动作？
- actor 是否每一步只选择当前 `admissible_actions` 中的一项？
- `action_index` 与 `resolved exact action` 是否一一对应？
- probe termination 是否合理？negative observation 后是否能自然 continuation？

### A

- A 是否只看到了真实 E1，而没有 E0/counterfactual？
- `UPDATE` 的 scope 和 guidance 是否超出实际 evidence？
- `NO_CHANGE` 是否保守但合理，还是过于拒绝更新？

### Overall

- 当前 controlled experiments 实际支持了 B/C/H/Online/A 中哪些机制层？
- 哪些仍然只是 qualitative evidence？
- action-index 消除的到底是 harness 噪声，还是仍有 model semantic execution failure？
