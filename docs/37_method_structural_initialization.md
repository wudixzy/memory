# Persistent Agent Memory：方法级结构初始化规范

> **状态**：当前方法基线补充（2026-09-18）  
> **用途**：明确 Persistent Agent Memory 在尚未观察任何历史 trajectory 时的结构初始化。  
> **范围**：本文只定义 **method-native cold start**。用于最小实验控制变量的 MVP warm-start memory snapshot 尚未定稿，后续单独设计。

---

## 1. 为什么需要单独定义初始化

当前方法同时包含：

- Raw Experience；
- Semantic Memory；
- Structural Graph；
- Established Memory；
- Exploratory Memory；
- Tool / Capability grounding。

如果不明确初始化，很容易把三类完全不同的“初始状态”混在一起：

1. baseline 自带的官方初始 playbook / rules；
2. 我们方法本身在没有经验时的 native cold start；
3. 为了最小实验隔离变量而人为准备的 warm-start memory snapshot。

本文只固定第 2 类。

---

## 2. Native Cold Start 的总体原则

系统在启动时尚未拥有任何经验驱动的长期知识，因此：

\[
\boxed{
K_0^{established}=\varnothing,
\qquad
K_0^{exploratory}=\varnothing
}
\]

但环境在运行前已经定义了一组稳定的 Tool / API capabilities，因此 Structural Graph 不必完全为空：

\[
\boxed{
G_0 = G_{tool}
}
\]

初始化遵守：

\[
\boxed{
\textbf{Fix what the environment defines; learn what experience gives meaning to.}
}
\]

也就是说：

- 环境客观定义的 Tool / API 结构在启动时确定；
- Strategy、Procedure、Semantic Concept 等经验语义不提前枚举，而是在后续 trajectory 中逐步形成。

---

## 3. 初始化时确定性构造的 Tool / Capability Scaffold

`G_tool` 由 Tool / API schema 直接构造，不依赖历史 trajectory，也不需要 LLM 进行跨经验语义判断。

第一版至少可以包含：

- Tool identity；
- Operation / API identity；
- `Tool has Operation` 等稳定 containment relation；
- schema 中明确声明的 input / parameter；
- schema 中明确声明的 output / return；
- Tool / Operation 的稳定自然语言 description；
- stable IDs 与 environment provenance。

这里的目标不是构造完整 solution graph，而只是提供一个长期稳定的 capability reference frame：

> Agent 客观上可以调用什么。

初始化阶段不从这些 capabilities 推导“应该怎样解决任务”。

---

## 4. 初始化时明确不创建的对象

以下结构不能因为“看起来以后可能有用”就在启动时预先构造：

- Strategy / Procedure concepts；
- Semantic Concepts；
- Context families；
- Subgoal taxonomy；
- 完整 action / strategy space；
- `alternative_to`；
- `preferable_to`；
- `requires`；
- `dominates`；
- `should_explore`；
- `over_explored / under_explored`；
- 任何依赖跨 trajectory evidence 才能成立的 semantic relation。

因此：

\[
\boxed{
\text{Tool / Capability vocabulary relatively fixed;}
\quad
\text{Strategy / Semantic Concept vocabulary experience-driven and open-ended.}
}
\]

---

## 5. 各长期层在 cold start 时的状态

### 5.1 Raw Experience

初始为空：

\[
\mathcal T_0 = \varnothing
\]

第一条真实 trajectory 完成后才开始保存 execution trace、observations、outcome、cost 和 provenance。

### 5.2 Established Semantic Memory

初始为空：

\[
K_0^{established}=\varnothing
\]

不预写“常识型策略”或人为 procedure。

第一条经验通过：

\[
\tau_1
\rightarrow
\text{Stage 1}
\rightarrow
A
\rightarrow
K_1^{established}
\]

后，才形成第一批 experience-derived long-term memories。

### 5.3 Exploratory Memory

初始为空：

\[
K_0^{exploratory}=\varnothing
\]

Exploratory Memory 只能由后续 B/C 在真实 established experience 基础上生成，不能在没有历史 evidence 时预置。

### 5.4 Semantic Concept / Experience Graph

经验语义部分初始为空。

第一批 Candidate Experience 出现后，A 才开始：

- 创建新的 Semantic Concept；
- 对齐已有 Concept；
- merge / dedup；
- refine / generalize / specialize；
- 建立 memory--concept--trajectory provenance grounding。

因此 Semantic Concept 是经验驱动的长期 abstraction，而不是初始化 ontology。

---

## 6. 第一条 trajectory 之后系统如何“长起来”

Cold start：

\[
(G_0^{tool}, K_0^{established}=\varnothing, K_0^{exploratory}=\varnothing)
\]

第一条 trajectory：

\[
\tau_1
\xrightarrow{Stage1}
M_1^{cand}
\]

随后 A 进行第一次 conservative reconciliation：

\[
(M_1^{cand}, K_0)
\xrightarrow{A}
K_1^{established}, G_1
\]

此后系统才进入正常的持续闭环：

\[
K_t
\rightarrow
\text{Online Acting}
\rightarrow
\tau_{t+1}
\rightarrow
Stage1/A/B/C
\rightarrow
K_{t+1}
\]

因此 native initialization 不需要额外的“预训练 memory formation stage”。

---

## 7. 初始化与当前 Graph 定位的关系

Tool scaffold 的存在不意味着 Graph 是 exploration 的主推理引擎。

当前 Graph 的主要职责仍然是：

- stable Tool / Capability grounding；
- Semantic Concept organization；
- cross-memory / cross-trajectory provenance；
- hard relations；
- retrieval / local expansion support。

当前 exploration 主要依赖：

\[
\boxed{
\text{Semantic Memory}
+
\text{local comparative diagnosis}
+
\text{capability-grounded counterfactual generation}
}
\]

而不是在初始化时构造完整 search-space graph。

---

## 8. 与 baseline initialization 的区别

某些 baseline 本身带有官方初始知识，例如：

- official initial playbook；
- built-in rules；
- static skills / manuals。

这些属于 baseline 的系统定义，不应该直接等同于我们方法的 experience-derived established memory。

因此实验文档中应明确区分：

### Baseline initialization

由 baseline 官方实现规定。

### Our method native cold start

\[
G_0=G_{tool},
\quad
K_0^{established}=\varnothing,
\quad
K_0^{exploratory}=\varnothing
\]

二者不能用同一个 `K0` 术语含混表示。

---

## 9. MVP Warm Start：当前明确后置

当前 MVP 尚未决定是否从 native cold start 完整构建 Memory。

为了控制 Stage 1 / A / B / C 同时变化带来的实验混淆，后续可能采用固定的 established-memory snapshot：

\[
K_{0,MVP}^{established}=\text{fixed prebuilt memory snapshot}
\]

同时：

\[
K_{0,MVP}^{exploratory}=\varnothing
\]

但以下问题当前**尚未定稿**：

- seed trajectories 如何选择；
- snapshot 是否由 Stage 1 + A 原生形成；
- 是否采用逐 trajectory incremental construction；
- 是否需要人工审查；
- seed 数量与停止条件；
- warm-start snapshot 与最终 native system 的关系。

这些属于**实验初始化协议**，不是方法结构初始化，不应在当前阶段为了“补完整”而提前设计。

---

## 10. 当前初始化规范的最简表述

方法级 cold start 可以压缩为：

\[
\boxed{
\begin{aligned}
G_0 &= G_{tool} \\
K_0^{established} &= \varnothing \\
K_0^{exploratory} &= \varnothing \\
\mathcal T_0 &= \varnothing
\end{aligned}
}
\]

其中：

- 环境定义的 capability 先存在；
- 经验语义不预定义；
- 第一条 trajectory 开始产生 Candidate Experience；
- A 从真实 evidence 中逐步形成 Semantic Memory / Semantic Concept；
- B/C 只能在已有经验基础上形成 exploratory memory。

这部分应视为当前方法定义的一部分，并在后续实现文档和主 method 文档中保持一致。
