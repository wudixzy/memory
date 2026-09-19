# 68. Phase 1 Targeting-Value Readiness Memo

> 状态：readiness scaffolding complete；等待 researcher review，未启动 paid pilot。
> Branch: `exp/minimal-exploratory-memory-validation`
> Carrier selected for scaffolding: pinned ALFWorld TextWorld only.

## 1. Readiness decision

本轮没有运行完整的 `20–30 targets × C1/C2/C3 × 2 repetitions` 矩阵，也没有为
产生漂亮结果而重选 target、调 B/C/H/A 或运行多模型矩阵。

当前判断是：**实现和审计脚手架可以交给研究者 review，但 paid Phase 1 尚未获准启动。**
启动前至少还应由研究者冻结：

1. C2 generic policy 的最终文字和 token/context budget 检查；
2. 手工控制夹具 K* 是否足以作为 Phase 1 的 warm-start；
3. ALFWorld lead pool 与 source/H family 的不重叠规则；
4. 主 actor 的 no-H reliability screen 结果。

## 2. Fair C2

`docs/63_phase1_fair_c2_specification.md` 与
`experiments/exploratory_memory_mvp/c2_generic.py` 定义 C2a：一次冻结的、任务族级
结构化 generic H。它与 C3 共享：

- `exploratory` object schema；
- actor prompt surface、zero-based `action_index` 和 step cap；
- one-shot active → consumed lifecycle；
- runtime H 保留到 `EVIDENCE_OBTAINED` / `ABORTED`；
- mechanical `probe_runtime_state`、admissible-action validation 和 artifact format。

C2 不接收 B/C 输出、source trajectory、source grounding、target hidden state、oracle
answer 或 target outcome。C2 的科学差异只有：它给出 generic candidate probing pattern，
不提供 history-derived unresolved-comparison targeting。C2b target-time synthesis 仍是
未来 baseline，不是本轮必需条件。

实现边界：当前 runner 保存 C2/C3 的 H 结构和每步运行事实，但没有假装已经证明 C2/C3
token 长度相等。paid pilot 前必须从实际 actor inputs 做 token 分布审计。

## 3. Warm-start K*

`docs/64_phase1_warm_start_k_star_provenance.md` 和
`experiments/exploratory_memory_mvp/k_star.py` 明确区分：

```text
method-native: G0 = G_tool, K0_established = empty, K0_exploratory = empty
Phase 1:       K0_established = fixed K*
```

当前 K* 是四条手工编写的 feasibility-only control entries。它不是 Stage 1/A 输出，
`source_histories_used = []`，也不是完整 train split 的自动摘要。canonical digest 是：

```text
331728a3e001c8a3bc7e992d7605ee428501c34d0d5d8fed75a19abd98314447
```

C1/C2/C3 通过 `k_star_sha256` 固定同一快照；K* 不包含 target ID、hidden placement、
oracle action/outcome 或 comparative winner claim。

## 4. Public-only target registry

`experiments/exploratory_memory_mvp/cases/phase1_registered_targets.json` 当前从 25 个
ALFWorld train candidate IDs 中注册 20 个 target task IDs；另外 5 个已冻结 source task
以公开、事前的 source-reservation 原因写入 `exclusion_reasons`。每条 target 记录只保存
public task identity、public instruction、reset 后 actor-visible initial fingerprint、task family 和预先声明的 H-family key。
registry 还保存：

- candidate universe 及其 candidate-ID digest；
- inclusion predicate；
- 5 个 source-reservation `exclusion_reasons`，用于保证 source/target 不重叠；
- `human_review.performed = false` 的 provenance 声明；
- registry digest：
  `41bb0b42cb4dcdf4249027f36e9208d65ec85ccb5aabae791380aa71d9b3dd6f`。

`validate_target_registry()` 拒绝 evaluator/oracle fields、重复 ID、universe 外 target、
错误 fingerprint 和不一致的 candidate-universe hash。target inclusion 不读取 static
PDDL placement 或任何 C3/E1 outcome。当前 registry 已把现有 source task IDs 从 target
列表中显式排除；如果 source/H family 再扩展，必须先更新 exclusion 记录和 registry digest，
再运行 pilot。当前 20 个 target 的 `h_family_receptacle_search` 是 lead-carrier 的机械
pool fixture，并不声称已经覆盖最终 pilot 所需的 5–8 个 source/H families；family 分层和
source-target disjointness 仍须在 pilot freeze 前由研究者审定。它不是 automatic H retrieval。

## 5. Carrier admission

`docs/66_phase1_benchmark_admission_audits.md` 的证据层级如下：

| candidate | evidence budget/status | decision |
|---|---|---|
| ALFWorld TextWorld | 10 个真实 task/reset inspection，零模型；另有实际 pairing proof 基础设施 | Phase 1 lead carrier |
| AppWorld/ACE | 历史文档中的 6 个真实 task/case，<=10；本轮不重新付费复现，fresh checkout 无 raw artifact | secondary/deferred |
| MiniWoB++/WebArena | 仅静态 source/risk screen，0 个真实执行 case | 不进入 Phase 1 |

因此没有把浏览器静态任务列表冒充成第三个已录取 benchmark。Phase 1 scaffolding 只接
ALFWorld，AppWorld 的状态回滚/actor/cost 风险保留为后续候选。

## 6. Main actor reliability gate

`docs/67_phase1_actor_reliability_screening_protocol.md` 规定先做约 10–20 个 C0/no-H
base tasks，记录：success、step-cap、semantic loop/drift、invalid index、steps/tool
calls、tokens/cost。C1/C2/C3 必须共享通过筛选的同一 actor/config；memory intervention
不能补偿不可靠的基础执行器。

本轮**没有**执行这个 paid screen，因此 Qwen3.8-Flash 仍只是当前 MVP 的 planning
backbone，不应被写成已经通过 Phase 1 main-actor gate。文档中的阈值是待 researcher
确认的 admission protocol，不是本轮观测结果。

## 7. Runner and dry-run boundary

`phase1_config.py`、`phase1_runner.py` 和 `phase1_budget.py` 提供 config-driven C1/C2/C3
Frozen-history scaffolding：

- unique target 是 scientific unit，repetition 是 nested metadata；
- 每个 arm 保存 immutable run config、K* digest、condition、repetition 和 model config；
- C1/C2/C3 actual episodes 从同一个 replayable episode specification 初始化；
- C1↔C2、C1↔C3 各自保存 pairing proof，不能用 discarded preflight reset 代替；
- fake transport 能在没有网络的情况下检查 H isolation、index legality、runtime lifecycle、
  failure artifacts 和 per-step action resolution；
- C3 config 只接受 future-facing H，不接受 `source_grounding` / `provenance` 等 source-only
  fields。

runner 默认 `allow_network=False`，没有启动 paid pilot。它仍然不会决定 semantic next
action、evidence truth、fallback route 或 H usefulness。

## 8. Token/call/cost projection

`phase1_budget.py` 的默认 planning anchor 来自已保存的 Apple action-index sanity：139
actor calls / 6 episodes，平均约 1,374 input tokens、15 output tokens、199 cached-input
tokens per call。它只是容量估计，不是 Phase 1 结果。

假设：`5–8` source/H families 取上界 8；C2a 是冻结 generic artifact（0 次 paid C2
generation）；C3/B 各按每个 source family 一次 offline call；Stage1/A/longitudinal
evolution 均 bypass。actor 成本按 DashScope Qwen3.8-Flash 当前代码中的 published
uncached planning rates `0.8 CNY/M input + 2.7 CNY/M output` 计算；cached-input rate、
free allowance、retry 和 provider-accounted bill 不纳入，因此这是上界式 planning estimate。

| unique targets | actor episodes | actor calls | input tokens | output tokens | offline B/C calls | uncached planning estimate |
|---:|---:|---:|---:|---:|---:|---:|
| 20 | 120 | 2,780 | 3,820,020 | 41,920 | B 8 + C3 8 = 16 | 约 3.1692 CNY |
| 30 | 180 | 4,170 | 5,730,030 | 62,880 | B 8 + C3 8 = 16 | 约 4.7538 CNY |

对应总 model-call planning estimates 分别为 2,796 和 4,186；不含环境 reset、磁盘、
网络延迟和失败重试。若改为模型生成 C2，另加最多 8 次 offline C2 calls；这不是当前
canonical C2a protocol。

## 9. Recommendation and non-claims

建议先由研究者 review docs/63–68，再决定是否运行 no-H actor screen；只有 actor gate、
C2 token audit、source/target disjointness 和 target registry freeze 都通过后，才启动
20-target pilot，再按 stop rule 决定是否扩到 30 targets。

本轮不支持以下结论：C3 已优于 C2、H 在自然任务分布上普遍有用、Qwen3.8-Flash 已是可靠
main actor、K* 已由 native cold start 形成、或 full persistent-memory loop 已经成立。
