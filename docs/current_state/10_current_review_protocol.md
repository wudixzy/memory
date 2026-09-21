# 10. Current Review Protocol：这一轮如何审查与决定是否进入 Actor Gate

> 状态：当前 reviewer contract（2026-09-21，Phase 1B Finalization — A Fault Isolation & Freeze）
> Baseline commit：f6bc77207557af68e913e5c037d5371651274dfb
> 当前目标：仅用保存的 closure artifacts 回归 A fault isolation；禁止模型/API调用和任何 task rerun。

---

## 1. Review 的目的

> **Current cycle override:** the actor-stack and Interface-Hardening reviews
> below are historical. The active review is `Phase 1B Finalization — A Fault
> Isolation & Freeze` (docs/100–101): verify that a valid A epistemic
> assessment survives an invalid Established Memory update, while preserving
> all existing leakage, evidence, temporal and fact-commit invariants.
> Do not reopen actor tuning or run fresh evaluation.

这一轮 review 不是：

- 重新设计 B/C/H/A；
- 找更多漂亮 ALFWorld case；
- 优化 H 让结果更好；
- 提前讨论 full Stage1/retrieval/longitudinal。

这一轮只回答：

> 当前 actor 在冻结的 Phase 1A `Actor + K* = C1` 条件下是否达到预注册的基础可靠性门槛？

Gate B1 不回答 C3 是否优于 C2，也不回答 exploratory memory 或 targeting 是否有效。

review 优先级：

    scientific validity
    > leakage / attribution
    > execution invariants
    > reproducibility
    > code style

---

# 2. Review 前先确认仓库状态

检查：

    branch = exp/minimal-exploratory-memory-validation
    baseline >= 56dcb311...

确认最新提交没有偷偷：

- 调模型/API；
- 跑 target outcomes；
- 改 B/C/H/A semantics；
- 改 source/target membership based on results；
- 把隐藏 PDDL/placement 加入 registry。

如果发生，先停止 review，明确污染范围。

---

# 3. 当前已经接受的基础设施

除非新 patch 破坏，不要重新争论：

- public-only universe；
- deterministic partition；
- target registry digest；
- actual public fingerprint；
- replay-spec pairing proof；
- action-index；
- model-invisible pairing metadata；
- warm-start K* 是 control fixture；
- C2 structured generic baseline；
- C3 future-facing H；
- source-only provenance 不进 actor；
- one-shot H lifecycle；
- E1-only A；
- Phase 1A 单 family claim。

Reviewer 应主要做 regression 检查，不应重新设计。

---

# 4. 当前必须解决的五个 blocker

## R1. Calibration 必须匹配正式 target domain

当前问题：

    15 calibration
    = 6 look_at_obj_in_light
    + 5 pick_two_obj_and_place
    + only 4 in-domain

这是不合格的 hard actor gate。

### Pass 条件

Final patch 后必须明确拆：

    in-domain calibration -> admission gate
    out-of-domain calibration -> diagnostics only

in-domain 指 Phase 1A target 的四类：

- pick_and_place_simple；
- pick_clean_then_place_in_recep；
- pick_cool_then_place_in_recep；
- pick_heat_then_place_in_recep。

Source / hard calibration / diagnostic / Target 必须 disjoint。

推荐 gate：

    invalid index = 0
    in-domain C1 success >= 80%
    step-cap <= 20%
    semantic loop <= 20%

实际 denominator 由 outcome-blind frozen partition 决定，必须在任何模型调用前写死。

### Fail 条件

- 为凑数据使用 target tasks；
- 看 actor outcome 后重新换 calibration；
- out-of-domain 任务影响 hard admission；
- calibration 与 source/target 重叠。

---

## R2. Probe budget 不能系统性偏向 C3

当前问题：

- visited_receptacles 来自 entire history；
- pre-probe visit 可能消耗 probe budget；
- closed cabinet 常需要 go+open；
- open surface 常 go 后即可观察；
- hard max_distinct_candidate_visits=2 会造成 realization-dependent unfairness。

### 推荐 pass 方案

Hard termination 只使用：

    max_probe_actions

Candidate visit 只记录 telemetry：

    episode_visited_receptacles
    probe_visited_receptacles

其中 probe-local 只能由 probe_action_history 派生。

不要引入：

- “fully inspected” semantic rule；
- code-selected candidate；
- rule-based next action。

### Reviewer 必测

构造：

    pre-probe go to X
    activate H
    probe go to Y

确认：

- X 不计入 probe-local visit；
- telemetry 可以看到 Y；
- candidate-count 不会提前 remove H；
- C2/C3 使用相同 action cap。

---

## R3. Live Source-H 必须有 referential integrity

当前 H manifest schema 还不足以证明来源真实。

### Pass 条件

Live H freeze 必须由工具从真实 artifact 计算，而不是手填 hash。

必须验证：

    source_task_id ∈ frozen source set
    source seed matches frozen protocol
    K* digest == canonical K*
    source history artifact exists
    B artifact exists
    C artifact exists
    source/B/C hashes match files
    C decision == CREATE
    future_H == projection(C result)
    future_H hash matches
    offline model config matches actual run

### Fail 条件

- 允许手填 arbitrary SHA；
- H 来源 source 不在 frozen source set；
- C output 修改后 manifest 仍合法；
- manifest future H 不是 stored C result 的 deterministic projection；
- source provenance 进入 target actor prompt。

---

## R4. H-family applicability 必须 public-only 且可执行检查

现在仅检查：

    target.matched_h_family == h_entry.h_family_id

过粗。

### Pass 条件

为 h_family_receptacle_search 定义 frozen public applicability contract。

只能使用：

- task family；
- public instruction；
- initial public observation；
- admissible actions；
- public affordance structure。

不能使用：

- hidden object placement；
- PDDL；
- outcome；
- oracle actions。

如果 live C 生成更窄 H scope，必须：

1. 在 target outcome 前把 public scope 加进 contract；或
2. 判定该 H 不适合作为 canonical Phase 1A H。

不能 target-by-target 人工看 hidden state 决定。

---

## R5. Scientific runner 必须拒绝 pending/rejected actor

Actor manifest 当前是：

    candidate_pending_independent_reliability_gate

### Pass 条件

状态 vocabulary 至少：

    candidate_pending_independent_reliability_gate
    passed_independent_reliability_gate
    rejected_independent_reliability_gate

Calibration mode：

    pending allowed

Scientific Phase 1A runner：

    only passed allowed

### Fail 条件

- pending actor 可以运行 target matrix；
- actor gate 失败后仍运行 Phase 1A；
- 根据 target outcome 改 actor；
- C1/C2/C3 actor config 不同。

---

# 5. Provider 支持的 review 口径

不要要求本轮做通用 provider abstraction。

当前真实实现仍走 DashScope client。

所以正确表述：

> model/config manifest-driven; current executable transport is DashScope-compatible.

如果 Qwen3.8-Flash 不通过，优先选 DashScope-compatible stronger candidate，除非研究者明确决定增加新 provider adapter。

不要把“provider 字段可配置”写成“任意 provider 已支持”。

---

# 6. C2 / C3 Fairness Review

付费 pilot 前检查：

### Same

- K*；
- actor；
- actor prompt base；
- action-index；
- lifecycle；
- runtime bookkeeping；
- step cap；
- probe action cap；
- target state；
- pairing；
- failure handling。

### Different

C2：

    generic structured exploration content

C3：

    history-derived targeted content

### 额外检查

实际 assembled first-step prompt 做 token/context audit。

不要求精确相等，但如果 C2/C3 差距异常大，应在看到 target outcome 前处理。

禁止：

- 结果出来后删长 prompt；
- 根据 target success 调 H 文本；
- C2 给更少 authority；
- C3 给更多 runtime facts。

---

# 7. 数据与统计 Review

Phase 1A：

    20 unique target tasks
    × 3 conditions
    × 2 reps
    = 120 actor episodes

但：

    n != 120

Primary scientific unit：

    n = 20 target/source-target units

2 reps 属于 nested repetitions。

建议 target-level 聚合后报告：

- C3 vs C2 win / tie / loss；
- success；
- shared-success step delta；
- probe activation；
- evidence-ready；
- abort；
- downstream completion；
- harmful probe；
- token/cost。

不要给 failure 随便赋一个巨大 synthetic step penalty 然后只报平均数。

---

# 8. 当前 claim boundary

Phase 1A 如果成功，只支持：

> Receptacle-search family 中，history-derived targeted exploration 相比 fair generic structured exploration 有增量价值。

不支持：

- general exploratory-memory superiority；
- natural B discovery rate；
- native cold-start success；
- Stage1 quality；
- retrieval quality；
- long-term memory improvement；
- cross-benchmark generality。

Reviewer 发现文档/结果越界时，应要求降 claim，而不是增加实验复杂度来“补”。

---

# 9. 当前 evidence hierarchy

从强到弱：

1. actual environment execution + immutable artifact；
2. deterministic paired execution proof；
3. committed public registry/hash；
4. model-visible prompt/input artifact；
5. code-level invariant + focused test；
6. human review；
7. design intention / prose。

遇到冲突时，优先相信更高层 evidence。

---

# 10. Review 输出格式

每轮 reviewer 最好按以下结构写：

## A. Verdict

    PASS
    PASS_WITH_MINOR_FIXES
    BLOCKED

## B. Must-fix blockers

只列会破坏 scientific interpretation / leakage / reproducibility 的问题。

## C. Non-blocking issues

文档、命名、未来 generality 等。

## D. Evidence checked

列出 commit、files、tests、relevant artifacts/digests。

## E. Claims allowed after this round

明确什么可以说。

## F. Claims still forbidden

明确什么还不能说。

## G. Next gate

只给一个下一 gate，不要同时开始多个阶段。

---

# 11. 历史 review verdict 与 development transition

The following actor-stack development transition is historical. The active
finalization contract is in `AGENTS.md` and docs/100–101.

当前：

    GATE_B1_FAIL_ACCEPTED
    -> ACTOR_STACK_DEVELOPMENT_DIAGNOSTIC

Gate B1 的 4/10、6/10 step-cap 与 cool 0/2 是有效 negative evidence，但人工逐轨迹诊断表明：
当前只能归因到完整 C1 actor stack，不足以主要归因到模型。

当前 review 接受两个优先 development intervention：

1. carrier-correct K* candidate v2；
2. raw public action->observation history。

不接受在本 cycle 中加入 semantic phase/controller、prompt tuning、第二模型或 target experiment。

原 10 hard-calibration tasks 从现在起是 development evidence，不再具有 independent admission
地位。完整计划见 docs/73_phase1_actor_stack_development_diagnostic_plan.md。

# 12. 历史 researcher review 重点

D1/D2 完成后，review 重点不是“是否达到 8/10”，而是逐轨迹比较：

- D0 vs D1：明确 K*/carrier contract failure 是否修复，是否出现新 regression；
- D1 vs D2：raw observation history 是否减少已知空 receptacle 重访、inventory/look 停滞、
  object grounding drift；
- 哪些错误在这些 confound 降低后仍然发生于信息充分的公开状态；
- K* v2 与 raw-history interface 是否值得冻结为后续正式 actor stack。

D1/D2 的 raw trajectories 必须可直接访问，summary 不能替代 trajectory evidence。

如果 fresh independent Gate B1-R 已在 D1/D2 前 public-only 预注册，review 只确认其 independence
和 membership freeze；不要在同一 review 中直接执行它。

下一 gate 仍需 researcher 明确授权。

# 13. Reviewer 不应做什么

不要：

- 因为某个 case 看起来不漂亮就改方法；
- 使用 hidden placement “验证” target 是否适合；
- target outcome 后改 sample；
- 在 Actor Gate 前看 target performance；
- 把 source positive curation 当 natural-distribution discovery；
- 把 H evidence-ready 当 hypothesis confirmed；
- 把 one successful alternative 当 global comparative proof；
- 为了公平性加 semantic controller；
- 为了 generality 提前接第二 benchmark。

---

# 14. 当前 review 的一句话纪律

> Before the first paid target pilot, every factor that can change the interpretation of C3 vs C2 should be frozen, public, auditable, and fail-closed.
