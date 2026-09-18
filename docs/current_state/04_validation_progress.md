# 04. MVP 验证实验历程与当前证据

本文只总结当前实验真正支持什么，不把设计意图当成实验结论。

## 1. 为什么做 Controlled MVP

早期尝试直接使用较重 benchmark / memory baseline 时，实验很难区分：

- memory 本身没有 authority；
- base actor 已经自己做了合理验证；
- benchmark 没有产生合适 unresolved comparison；
- 实现接口有问题；
- 方法本身失败。

因此后续定位改成：

> 使用真实 benchmark / 真实环境作为 case carrier，但先手工选择少量具有目标结构的真实 case，用来做 mechanism validation。

ALFWorld TextWorld 最终成为当前主要 carrier。

## 2. Case 类型

### P

存在 policy-relevant unresolved comparison。

预期：

    B = OPEN

### N1

已有真实 comparative evidence，comparison 已经关闭。

预期：

    B = NONE

### N2

技术上可能未完全证明，但 policy relevance 很低。

预期：

    B = NONE

当前 curated set：

    5 P
    3 N1
    3 N2

## 3. 第一次 B 失败

最早 B 实现出现：

    P: 0/5 OPEN
    N1: 0/3 OPEN
    N2: 0/3 OPEN

也就是 constant NONE。

主要原因不是简单“模型太弱”，而是接口和职责设计错误：

1. 当前 completed trajectory 没有被清楚作为 current trajectory 提供；
2. 历史 route 被混进 established memory；
3. prompt 隐式要求 B 知道一个 concrete alternative 存在；
4. B/C responsibility drift。

## 4. B/C Boundary 修正

最终明确：

    B:
      Which incumbent comparison is worth opening?

    C:
      What grounded local test should be tried once?

B 不需要证明 alternative 存在。

修正后 Qwen3.8-Flash：

    P: 5/5 OPEN
    N1: 0/3 OPEN
    N2: 0/3 OPEN

因此 controlled MVP 层面 B 基本通过。

局限：

- P cases 仍较同质；
- 大多围绕 search-order；
- 不能代表 broad generality。

## 5. C 的第一次问题：Open-loop Future Program

早期 C 尝试输出：

    [a1, a2, ..., an]

但 future observations 尚未发生，因此这种 action list 的 executability 无法保证。

典型失败：

- source-time 某些 action/entity 在历史中出现过；
- C 错误地把“历史见过”理解为“未来 sequence 现在可执行”。

## 6. C 改成 Probe Policy

最终 C 输出：

- local function；
- realization pattern；
- capability requirements；
- adaptive policy；
- evidence goal；
- stop conditions；
- required downstream state。

只要求 source entry grounding。

未来动作由 target actor 根据真实 observation/admissible actions stepwise grounding。

## 7. Same-task Online Sanity

### AlarmClock -> Desk

E0：

    20 steps, success

E1：

    4 steps, success

H 有明显行为影响。

### Pencil -> Shelf

E0：

    4

E1：

    4

H 被激活并执行，但 base actor 本来就走同样直接路线。

重要区分：

    behavioral authority = yes
    incremental behavioral effect = ~0

### SoapBottle -> Cabinet

E0：

    8

E1：

    5

H 有局部行为影响。

这些结果证明：

> H 可以成为 online actor 的 local behavioral authority。

但 same task / same seed replay 存在 source-answer-cache 风险，因此不能作为最终 transfer evidence。

## 8. Local C Boundary 修正

随后发现 C 如果看到完整 source trajectory，就可能知道最终 object location。

于是 C input 收缩为：

    Functional Contract
    + local public facts
    + relevant memory
    + relevant capability

不再默认提供完整 source trajectory。

并把 H 分成：

### Future-facing

    scope
    hypothesis
    guidance
    probe_policy

### Source-only

    source_grounding
    provenance

## 9. Clean C Experiment

最初人工 local packet 中 P005 曾直接暗示：

> open surface before closed storage

这等于 researcher 提前给了 candidate alternative。

随后删除这些 hint，只保留事实。

Clean P002 / P005 在 fact-only local packet 下仍然：

    C = CREATE

并生成 future-facing local alternatives，且 future H 不包含 source entity ID。

因此小样本上支持：

> C 不只是把 researcher-proposed alternative 包装成 H。

但仍未证明更广 task family generality。

## 10. Cross-task Transfer

### SprayBottle

Source：

    P005 H

Different target：

    SprayBottle -> Toilet

结果：

    E0 4 steps
    E1 4 steps

E1：

    H activated
    -> target-grounded
    -> object found
    -> evidence ready
    -> H removed
    -> original task completed

因为 E0 自己选择同路线，因此它是 mechanism evidence，不是 incremental performance evidence。

### Laptop

原 E1：

    desk <-> shelf loop
    24-step cap
    failure

最初容易被解释成 H / online control 问题。

但加入纯机械：

    visited_receptacles
    probe_action_count

保持同一个 H、同一个模型后：

    6 steps
    success

因此原 Laptop failure 主要定位为：

    state representation / actor interface problem

而不是必须重新设计 H。

## 11. Negative Evidence / Fallback

SoapBottle / Apple 等 case 表明：

- H 可以产生 negative local observation；
- H 可以 adaptive continuation；
- 可以到达 EVIDENCE_OBTAINED；
- runtime H 可被移除；
- downstream task 有时可以继续完成。

但 weak actor 的 long-horizon semantic drift 使 clean performance attribution 一度不稳定。

因此后续重点转向清理 harness confound。

## 12. A Reconciliation

早期 A 输入错误包含 E0 reference。

这不符合真实 deployed system，因为 A 不会知道：

> 如果当时没有 H，会发生什么。

修正后：

    A sees actual E1 evidence only

代表结果：

### Laptop

    NO_CHANGE

### SprayBottle

旧输入包含 E0 时：

    SPECIALIZE

E1-only 后：

    REFINE

更加保守。

### Negative case

常见：

    NO_CHANGE

因此当前 qualitative evidence 支持：

> A 可以做 scope-limited、evidence-bound reconciliation。

但尚未证明 long-term memory evolution quality。

## 13. Action-index Harness

weak actor 曾出现 exact action string 错误，例如错误 object suffix。

为避免把字符串复现能力当成 memory failure，actor 改为：

    action_index

runner：

    admissible_actions[action_index]

Sanity：

    E0 x3: 3/3 success
    invalid index: 0

说明 exact-string transport confound 被有效清理。

E1 仍有合法 index 下的重复动作/path drift，因此剩余噪声主要属于 semantic actor reliability。

## 14. Pairing Infrastructure

旧 runner：

    preflight E0 reset
    preflight E1 reset
    compare
    discard
    create new execution episodes

这无法证明真正执行的 E0/E1 是 paired state。

当前改成：

    create actual E0 episode
    create actual E1 episode from same replay spec
    build pairing proof
    verify
    run actor on these same episodes

### Reset audit

Apple/Microwave：

    10 resets
    unique public fingerprint = 1
    unique static PDDL = 1

Pencil/Shelf：

    10 resets
    unique public fingerprint = 1
    unique static PDDL = 1

因此当前 pinned TextWorld carrier 支持 replayable episode spec。

### Post-fix Apple sanity

    E0: 2/3 success
    E1: 2/3 success

3/3 E1：

    H activated
    evidence ready
    runtime H removed

139/139 action_index valid。

这个实验不说明 H 有性能优势，只说明：

> action interface、pairing 与 lifecycle 已经足够可审计，不再是主要 confound。

## 15. 当前真正支持的结论

### 已获得 controlled qualitative support

- B/C conceptual boundary；
- B 对 OPEN/NONE 的基本 controlled discrimination；
- C 从 local fact-only input 合成 local alternative；
- future-facing H 不依赖 source exact ID；
- target-time grounding；
- H behavioral authority；
- one-shot lifecycle；
- positive / negative evidence generation；
- E1-only A reconciliation；
- action-index interface；
- mechanical runtime progress state；
- actual E0/E1 pairing proof。

### 尚未支持

- C3 > C2；
- automatic H retrieval；
- full Stage1 pipeline；
- natural-distribution H usefulness；
- long-term A accumulation benefit；
- cross-benchmark generality；
- full closed-loop improvement；
- stable main-paper performance under a reliable actor。

## 16. 当前阶段判断

项目已经从：

    Can the mechanism work?

推进到：

    Does the mechanism provide systematic value
    over strong, fair alternatives?

因此继续围绕 controlled case 修方法的收益已经很低。

下一阶段应该正式进入 baseline/evaluation design。
