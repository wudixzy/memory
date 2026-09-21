# Persistent Agent Memory：Exploratory Memory 生命周期与历史归档

> **状态**：当前方法基线补充（2026-09-21）  
> **用途**：定义 exploratory memory 的在线使用、一次性消费、离线历史保留，以及 C 阶段如何避免重复提出已经测试过的探索假设。  
> **范围**：本文只定义最小 lifecycle。是否需要更复杂的 test-validity 判断、重复测试或 A-side hypothesis verification，留给后续实验决定。

---

## 1. 核心修正

Exploratory Memory 仍然采用 one-shot online use：

\[
\boxed{
H^{active}
\xrightarrow{\text{online activation}}
\text{consumed}
}
\]

但：

\[
\boxed{
\text{从 online active pool 删除}
\neq
\text{从系统历史彻底遗忘}
}
\]

否则同一个探索方向在后续 B/C 中可能被重新提出，造成重复实验。

因此系统区分：

\[
\boxed{
K^{exploratory}_{active}
}
\]

与：

\[
\boxed{
\mathcal E^{history}
}
\]

前者是在线可召回的一次性探索 Memory；后者是离线不可召回的 exploration history / archive。

---

## 2. 两个对象的职责

### 2.1 Active Exploratory Memory

用于未来在线任务中的一次性 exploration intervention。

典型字段：

```text
type: exploratory
scope: ...
hypothesis: ...
guidance: ...
grounded_realization: ...
reason: ...
provenance: ...
```

Online retrieval 可以召回它。

一旦被正式激活用于一次匹配情境：

\[
\boxed{
active \rightarrow consumed
}
\]

之后不再进入在线 recall。

### 2.2 Exploration History / Archive

只用于离线更新与实验审计。

它不是普通 Memory，也不向在线 Agent 提供 guidance。

最小记录：

```text
exploration_id
scope
hypothesis
grounded_realization
reason

source_memory_ids
source_trajectory_id

activated_on_trajectory
activation_step
related_post_test_memory_ids   # optional
```

Archive 的目标不是重新保存整条 raw trajectory，而是保留：

> 系统曾经提出并尝试过什么探索问题。

---

## 3. 为什么需要 Archive

理想闭环是：

\[
H
\rightarrow
\text{test}
\rightarrow
\tau
\rightarrow
A
\rightarrow
K^{established}
\]

理论上，如果 A 总能把测试结果完整吸收到 Established Memory，那么未来 C 可以通过普通 Memory 判断：

> 这个方向已经被测试过。

但 Persistent Memory 是有损压缩：

- A 可能以不同粒度总结测试结果；
- scope 可能被重新表述；
- 一次失败可能只产生局部 failure lesson；
- C 不一定能稳定从 Established Memory 反推出“同一探索假设已经测试过”。

因此完全依赖 A 做隐式去重不够稳。

Archive 只解决一个非常具体的问题：

\[
\boxed{
\text{Avoid repeatedly proposing the same already-tested exploration.}
}
\]

---

## 4. Online 仍保持 one-shot consume

当前在线流程不改变：

\[
\text{problem state}
\rightarrow
\text{scope-based exploratory retrieval}
\rightarrow
\text{activate at most one exploratory memory}
\rightarrow
\text{local test}
\]

一旦正式激活：

1. 从 (K^{exploratory}_{active}) 移除；
2. 在 (mathcal E^{history}) 中记录该 exploratory memory 及 activation provenance；
3. 正常完成 trajectory；
4. 新 trajectory 进入 Stage 1 → A。

因此：

\[
\boxed{
\text{online simplicity is preserved;}
\quad
\text{historical awareness is retained offline.}
}
\]

---

## 5. “Consumed” 不等于“Falsified”

必须区分：

\[
\boxed{
\text{one-shot consumption}
\neq
\text{epistemic falsification}
}
\]

一次 alternative execution 失败，可能来自：

- hypothesis 本身不成立；
- scope 不适用；
- 参数选择错误；
- transient environment error；
- realization 中某一步失败。

因此 archive 不应机械记录：

```text
hypothesis = false
```

Online 层只记录：

> 该 exploratory memory 已被激活并产生了一次测试 trajectory。

测试结果意味着什么，仍由：

\[
\boxed{
Stage1 \rightarrow A
}
\]

基于真实 trajectory 做 semantic reconciliation。

---

## 6. C 如何使用 Exploration History

C 的默认输入从：

\[
\text{Functional Contract}
+
\text{Established Memory}
+
\text{Tool Capabilities}
\]

扩展为：

\[
\boxed{
\text{Functional Contract}
+
\text{Established Memory}
+
\text{Tool Capabilities}
+
\text{Relevant Exploration History}
}
\]

其中 exploration history 只通过 semantic retrieval 返回少量相关记录，不把整个 archive 塞进 prompt。

可按：

- scope；
- hypothesis；
- grounded realization；

检索相关历史。

C 需要判断：

> 当前准备提出的 exploratory memory 是否只是一个已经在可比 scope 下被测试过的等价 hypothesis。

---

## 7. 不使用硬规则永久禁止“相似假设”

不写：

```python
if similar_hypothesis_exists:
    reject()
```

因为同一高层 strategy 在不同 scope 下可能值得重新测试。

例如：

- fuzzy-name query 下 direct search 失败；
- exact-email query 下 direct search 仍可能值得测试。

因此：

\[
\boxed{
\text{retrieval exposes prior exploration;}
\quad
C\text{ judges semantic equivalence and material novelty.}
}
\]

C 可以重新提出一个历史上类似的方向，但需要存在 material difference，例如：

- scope 明显变化；
- candidate realization 实质变化；
- 新 Tool capability 出现；
- 新 Established Memory 改变了原 comparison；
- 原 test 没有真正覆盖当前 unresolved question。

---

## 8. B 当前不读取 Exploration History

MVP 中：

\[
\boxed{
B\text{ does not need exploration history.}
}
\]

B 仍然只负责：

> 当前 trajectory + historical Established Memory 是否暴露出一个 meaningful open comparative question。

如果 B 再次提出类似 comparative question，C 可以通过 exploration history：

- 输出 NONE；
- 提出 materially different alternative；
- 缩窄 / 改变 scope。

这样虽然可能多一次 B call，但职责清晰、容易调试。

只有当实验显示大量：

\[
B
\rightarrow
\text{same question}
\rightarrow
C
\rightarrow
NONE
\]

造成明显浪费时，再考虑把 archive 摘要提前提供给 B。

当前不增加这一优化。

---

## 9. A 与 Archive 的关系

A 不负责维护复杂 exploration lifecycle。

测试 trajectory 正常进入 A：

\[
\tau_{test}
\rightarrow
Stage1
\rightarrow
A
\]

A 只做原本的：

- new / merge / refine；
- scope revision；
- contradiction reconciliation；
- failure lesson；
- provenance accumulation。

如果 A 产生了与某个 tested exploration 直接相关的 Established Memory，可以把其 ID 回写到 archive 的：

```text
related_post_test_memory_ids
```

这只是 provenance/bookkeeping，不要求 A 输出“hypothesis true/false”。

如果后续实验发现一次 activation 经常没有构成有效 test，再考虑让 A 增加轻量的 test-validity semantic judgment。

MVP 不提前加入。

---

## 10. 初始化

Method-native cold start 时：

\[
\boxed{
K_0^{exploratory}=\varnothing,
\qquad
\mathcal E_0^{history}=\varnothing
}
\]

只有 C 首次产生 exploratory memory 后，active exploratory pool 才非空。

只有某条 exploratory memory 被实际激活后，exploration history 才开始积累。

---

## 11. 完整生命周期

\[
\boxed{
\begin{aligned}
B &: \text{find an open comparative question} \\
C &: \text{create } H^{active} \\
Online &: H^{active} \rightarrow \text{one-shot local test} \\
Archive &: H \rightarrow \mathcal E^{history} \\
Trajectory &: \text{test produces } \tau_{test} \\
A &: \tau_{test} \rightarrow K^{established} \\
Future\ C &: \text{retrieve } \mathcal E^{history} \text{ to avoid redundant exploration}
\end{aligned}
}
\]

核心职责可以压缩成：

\[
\boxed{
\text{Active exploratory memory tells the agent what to test once;}
}
\]

\[
\boxed{
\text{Exploration history tells future C what has already been tried.}
}
\]

---

## 12. 当前明确不增加的机制

MVP 不实现：

- complex hypothesis state machine；
- semantic success/failure labels in the archive；
- repeated-test counters / confidence scores；
- archive-driven B gate；
- rule-based semantic dedup；
- mandatory multiple confirmations；
- online recall of archived hypotheses。

这些只有在实验暴露具体失败模式后再决定。

---

## 13. 当前方法更新后的最简状态

长期系统现在包含：

\[
\boxed{
K^{established}
+
K^{exploratory}_{active}
+
\mathcal E^{history}
+
G
+
\mathcal T
}
\]

其中：

- (K^{established})：已建立的长期经验；
- (K^{exploratory}_{active})：待一次性测试的探索性 Memory；
- (mathcal E^{history})：已经提出 / 激活过的探索历史，仅供离线 C 和审计；
- (G)：Tool/Concept/provenance grounding；
- (mathcal T)：raw trajectory evidence。

新增的 (mathcal E^{history}) 是一个轻量 archive，而不是新的在线 Memory subsystem。
