# Paper-level Evaluation Design（草案）

日期：2026-09-17
状态：设计稿；本轮不启动 broad evaluation
方法状态：B/C/H/A core design frozen

本文把当前 MVP 的受控观察转换成可复查的论文级评估设计。它不是结果报告，也不把 ALFWorld 的 3 组 paired sanity 当作 method effect。

## 1. Scientific questions

正式评估应分别回答：

1. history-derived targeted exploratory memory 是否改善未来 scope-matched task 的行为？
2. 它在什么 context 下帮助，什么 context 下会伤害？
3. 它是否优于 generic exploration，而不是只优于 no exploration？
4. 探索带来的 task quality、步骤数、token/API cost trade-off 是什么？
5. probe evidence 是否能被 A conservatively 吸收到 persistent established memory，并在后续任务中产生可重复 benefit？

核心方法比较是 C3 vs C2。C3 的 B/C-generated targeted hypothesis 不能进入 C2；否则无法区分 targeted exploration 与 generic exploration。

## 2. Frozen method boundary

```text
offline / between episodes:
trajectory/evidence -> A -> B -> C -> consolidation/index refresh

online / task time:
retrieval/activation -> target-time grounding -> stepwise actor
                   -> mechanical state -> environment execution -> facts/evidence
```

保持：

- B 只诊断“哪个 incumbent comparison 值得打开”；
- C 只合成一个 grounded local probe policy；
- H 是 one-shot exploratory memory，在当前 episode 可保留 runtime guidance 到 probe stop；
- actor 每次只选择一个当前 admissible action，使用 action-index 或同等结构化接口；
- online 只写可观察事实；A 在 episode 之后做知识更新；
- 每个条件内 actor/model/backbone、temperature、thinking、step cap 和 carrier protocol 固定。

## 3. Core conditions

| 条件 | 输入 | 目的 |
|---|---|---|
| C0: no memory | task/state + normal actor context | 测量没有历史记忆的基础执行能力。 |
| C1: retrospective established memory only | C0 + established memories | 测量已有知识的直接作用。 |
| C2: retrospective + generic exploration | C1 + generic exploration instruction/controller interface | 测量“允许探索”本身的收益和代价；不能注入 B/C 的 targeted hypothesis。 |
| C3: retrospective + targeted exploratory memory（ours） | C1 + retrieval/activation of history-derived H | 测量 history-derived local hypothesis 的增量作用。 |

C3 的主效应不是 C3 vs C0；主效应是匹配 task/state 下的 C3 vs C2，同时报告 C0/C1 以解释 memory 与 exploration 的各自贡献。对于 source→target transfer，要在 source H 生成完成后封存 H，再暴露 target；target 的 hidden answer/outcome 只能留在 evaluator-side protocol。

## 4. Metrics

### 4.1 End-to-end

按 task 和 matched repetition 报告：

- task success / reward；
- solution quality 或目标完成质量；
- steps / tool calls；
- input/output tokens、API cost；
- latency（如果 provider telemetry 可靠）。

success 不能单独作为 exploratory memory 的判据：一个 probe 即使发现 alternative 更差，也可能提供有价值的 comparative evidence。

### 4.2 Mechanism

离线与在线分开统计：

- B `OPEN` rate；在人工标注 subset 上的 B precision/recall；
- C `CREATE` rate；usable-probe rate；
- H retrieval/activation rate；target-time grounding success；
- incremental behavioral effect（C3 相对 C2 的局部动作/探测变化）；
- productive-evidence rate；positive / negative evidence frequency；
- probe termination、abort/recovery、downstream completion；
- actor 是否实际执行了 H，而不是只把 H 看见；
- probe evidence 是否改变该 comparison 的 epistemic status。

`EVIDENCE_OBTAINED` 在 runtime 中只表示 `PROBE_EVIDENCE_READY`：有足够局部观测供 A 事后处理，不表示 hypothesis 为真、alternative 更优或全局问题已解决。

### 4.3 Memory evolution

对每个 A update 保存 evidence basis 与 provenance，并由人工 review subset 检查：

- A update rate；
- evidence-supported update rate；
- over-generalization；
- under-update / 过度 `NO_CHANGE`；
- resolved-question reopening；
- memory growth、检索上下文成本；
- later-task benefit。

A 的更新必须只使用 deployed actor 实际能看到的 E1 轨迹、probe trace 和环境结果；E0 是 researcher-side counterfactual，不能进入 A prompt。

## 5. Actor reliability and failure attribution

主评估 backbone 必须先通过 base-execution reliability screening。当前 Qwen3.8-Flash 的 action-index 接口已经能清除 exact-string transport failure，但 Apple sanity 仍出现合法 index 下的 semantic path drift 和 step-cap failure。因此 paper 主结论不能建立在一个不稳定的 base actor 上。

建议保留 `qwen3.8-flash` 作为弱模型 robustness condition；另选一个通过相同 task completion/replay screening 的 stronger actor 作为主 backbone。C0–C3 比较中 actor/backbone 必须固定，不能只在 C3 使用更强模型。

每个失败 trace 都按以下主类归因，必要时附次类：

```text
transport/interface failure
semantic actor failure
memory retrieval/activation failure
H grounding/authority failure
probe-control failure
task continuation failure
A/update failure
```

`action_index` invalid、当前 admissibility mismatch、pairing proof invalid 等是可审计的 mechanical/interface failure；它们不能混入 semantic method failure。反过来，合法 index 也不能掩盖模型错误选择、重复动作或错误目标对象。

## 6. Benchmark admission criteria

benchmark 不是按流行度录取，而是按以下条件逐项检查：

- 有 sequential/repeated tasks，使 established memory 和后续 transfer 有意义；
- 至少存在多个 plausible local realization，而不只是唯一 oracle path；
- 有 success/quality/cost signal；
- trajectory/tool calls 和 public observations 可记录；
- 有 replayability，或有明确 randomized pairing protocol；
- base actor 足够可靠，避免执行失败完全吞没 memory effect；
- 实验成本可控，能够保存完整 prompts、responses、telemetry 和 failure artifacts。

项目已有经验给出几个实际门槛：

- ALFWorld TextWorld 对当前 pinned task 可以通过缓存 game/PDDL replay 建立 pair，但不能把 nominal seed 自身当作通用 proof；换 carrier 必须重做 reset audit。
- ALFWorld 的对象同类实例和 actor 的 object choice 会造成表面上不同的 `object_n`，因此 evaluator 必须区分 public initial state、underlying specification 和 actor 后续选择。
- AppWorld 的上一轮最终 sanity 已显示环境/任务状态或工具链问题可以先于 method 暴露；这类 carrier blocker 应记录并停止，而不是用 prompt/rule workaround 伪装成 memory result。
- WebShop/ScienceWorld 或其他候选 carrier 只有在小规模真实样本同时满足可执行局部替代、可观察比较证据和可 defensibly pair/replay 时才进入正式评估；不能因为 adapter 已存在就自动录取。

每个 benchmark admission memo 至少应给出：10 个以内的真实样本、base success rate、失败 taxonomy、reset/replay 证据、一个 positive 和一个 negative/ambiguous local comparison，以及预计在线/离线成本。

## 7. Online/offline cost accounting

### Online task-time cost

单独报告 retrieval 与小 rerank、memory/H context 增加的 input tokens、normal actor one-action calls、probe runtime bookkeeping 和 environment/tool latency。

### Offline maintenance cost

单独报告 Stage 1（完整系统启用后）、A reconciliation、B diagnosis、C synthesis、consolidation/index refresh，以及各阶段的 prompts、responses、tokens、API cost 和 latency。

当前 MVP telemetry 可作量级估计：一次 B/C case 通常各是 1 个 model call；一次 A 是 1 个 call；stepwise actor 按实际执行 step 逐 call。新的 Apple paired sanity 的 6 个条件共产生 139 个 actor calls，平均每 condition 约 23.2 calls、191,001 input tokens 和 2,096 output tokens；逐 call 本地 estimated cost 合计约 0.1255 CNY，但 provider-accounted cost 未返回。Qwen3.8 的 cached-input cost 受 DashScope console 计价方式影响，不能仅用本地 token 数推断最终账单；正式报告应同时给 provider telemetry 和 accounted/estimated cost，并标明未知项。

## 8. Preliminary experiment matrix（只设计，不运行）

下面是可按预算缩放的第一版矩阵。`20 tasks × 3 repetitions` 是设计假设，不是已执行结果；每个 task 必须先通过 benchmark admission 和 pairing validation。

| 层级 | benchmark | conditions | actor | tasks/reps | episode count | 目的 |
|---|---:|---|---|---:|---:|---|
| screening | 2 admitted candidates | C0–C3 | 1 main backbone | 20 × 3 | 480 | 初步估计 C3 vs C2 与机制失败率。 |
| reliability | same 2 candidates | C0–C3 | main + Qwen robustness | 20 × 3 | 960 | 判断主结论是否依赖弱模型执行噪声。 |
| memory evolution | 1 candidate first | C1/C2/C3 with multi-episode histories | main backbone | 20 source/target sequences × 3 | 180 target episodes plus source/offline calls | 测量 A update、later benefit、memory growth。 |

在 `15` actor decisions/episode 的保守假设下，screening 约 `7,200` actor calls，reliability 约 `14,400` actor calls，memory-evolution 的 180 个 target episodes 约 `2,700` actor calls，再加 source episodes。

这些数字只包含 actor call 粗估，不包含 B/C/A、retrieval、失败重试或额外 target grounding calls。按当前 MVP 的 call shape，offline rough categories 可以写成：每个 targeted source 是 1 B + up to 1 C；每个 E1 target episode 是 1 A；每个 actor step 是 1 normal actor call。正式预算应分别列出 actor online cost、retrieval/H context overhead、offline B/C/A cost、consolidation/index cost，以及 environment/latency cost。

未知项包括各 benchmark 的实际平均 step、H activation rate、C `NONE` rate、provider cached-token price、stronger backbone price，以及 paired replay 是否需要额外 environment startup。正式执行前可用小 pilot 更新这些估计，但不能通过 rejection sampling 挑选 outcome。

## 9. Protocol requirements before broad runs

1. 每个 C3 target pair 保存 `pairing_proof`，并证明实际执行 episode 与 proof 对应；无法证明时阻止 causal comparison。
2. C2 不得收到 C3 的 targeted hypothesis、scope-specific H 或 evaluator oracle。
3. source H 在 target hidden state/outcome 暴露前封存；target actor 只获得 public observation、当前 admissible actions、established memory 和被激活的 future-facing H。
4. E0/E1 初始状态、task/seed、actor config、step cap 和 established memory 完全匹配；只允许 H intervention 不同。
5. 保存每一步 prompt/input/visible response/current action list/action index/resolved action/environment result/runtime H status。
6. evaluator label、oracle location、researcher rationale 只在 researcher-side result table 出现，不进入 model-visible payload。
7. 失败 artifact 必须保留，failure attribution 先于任何 prompt 或 implementation change。
8. A 只能使用实际 E1 evidence；不得读取 E0 reference 或 counterfactual summary。

## 10. What this design does not claim

当前实验只支持：在一个 pinned ALFWorld TextWorld 子集上，实际执行 E0/E1 可以用 cached static episode specification 建立可审计配对；action-index 和 stepwise runtime bookkeeping 能把部分接口错误变成机械可检查事件；小样本中可以观察 B/C/H/Online/A 的信息边界和 evidence lifecycle。

当前仍未支持：C3 普遍优于 C2；targeted H 的总体 success/quality/cost improvement；A 的长期知识积累收益；跨 carrier 的 replayability；或 full persistent-memory closed loop。

因此建议先由研究者 review 本设计和 benchmark admission criteria，再决定主 backbone、正式样本规模及预算；本 cycle 不启动 C0–C3 broad runs。
