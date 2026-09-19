# 73. Phase 1A Actor-Stack Development Diagnostic Plan

> 状态：researcher-approved development plan（2026-09-20）
> Branch：`exp/minimal-exploratory-memory-validation`
> Baseline：`7e98ebaf550f4e57ea7a80c43e203f9b7cec4f13`
> 前置证据：Gate B1 FAIL + `docs/72_phase1_gate_b1_failure_trajectory_diagnosis.md`
> 核心纪律：diagnose before optimizing; preserve trajectories; do not reuse development tasks as independent admission evidence.

## 1. 为什么进入 development diagnostic

Gate B1 的 10-task C1 run 结果为 4/10 success、6/10 step-cap、0 invalid action index，
但逐轨迹诊断不足以把失败主要归因于 Qwen3.8-Flash 本身。当前可以确认的是：

```text
Qwen3.8-Flash
+ actor prompt
+ warm-start K*
+ online state/history representation
+ ALFWorld actor-facing action semantics
+ harness
= current C1 actor stack is not reliable enough
```

已有轨迹暴露两类优先处理的 confound：

1. **K* / carrier contract mismatch**
   - cool guidance 的“place object inside to cool”与实际 actor-facing `cool X with fridge` action contract 不一致；
   - generic search guidance 的“找到目标后直接去最终 destination”对 clean/heat/cool family 过宽，应把 search 与 downstream transformation 解耦。
2. **raw interaction evidence 缺失**
   - actor 只有 executed action strings，没有历史 observation；
   - 多个失败需要记住“某 receptacle 已经看过且为空”，但当前输入没有保留该原始事实。

这两个问题都应先于“换更强模型”做小规模隔离。

## 2. Scientific status of the old 10-task set

从本计划开始，原 Gate B1 的 10 个 hard-calibration tasks 明确降级为：

```text
actor-stack development / diagnostic set
```

它们可以用于 D1/D2 开发诊断，但不能再用于：

- 独立 actor admission；
- 调整后宣称 Gate B1 pass；
- 选择 target；
- 支持 C3 > C2 claim。

原 Gate B1 FAIL 结果永久保留为 negative evidence，不覆盖、不删除。

## 3. D0 / D1 / D2

### D0 — 已有 evidence，不重跑

```text
Qwen3.8-Flash
current actor prompt
K* v1
action-only executed history
10 development tasks
result = historical Gate B1: 4/10
```

D0 只作为 development reference，不再调用模型。

### D1 — Carrier-correct K* candidate

只改变 K*，其他 actor-visible factors 保持 D0：

```text
same model
same prompt
same 10 development tasks
same step cap
same action-index
same action-only history
K* candidate v2
```

K* v2 必须先做 no-model carrier-contract audit。原则：

- 保留 feasibility-only control fixture 定位；
- 不加入 hidden placement / target outcome / comparative winner；
- generic search memory 只负责“找到并取得目标”，找到后交给 task-required downstream routine，不再统一要求直接去 final destination；
- clean / heat / cool guidance 与真实 actor-visible carrier action contract 对齐；
- 不加入特定 development case 的 entity/action sequence；
- 不把 D0 失败轨迹直接编码成 if/then repair rules。

K* v2 在本轮只是 **candidate fixture**。D1/D2 review 通过前不要替换正式 canonical K*。

### D2 — K* candidate v2 + raw action-observation history

在 D1 基础上唯一增加：

```text
past executed action -> resulting public observation
```

允许保存/显示原始 public interaction facts，例如：

```text
action: go to cabinet_1
observation: cabinet_1 is empty
```

禁止增加：

- current_phase；
- SEARCH / NEED_COOL / OBJECT_ACQUIRED 等 hand-coded semantic phase；
- semantic visited/fully-inspected labels；
- rule-based next-action recommendation；
- oracle/hidden facts；
- model-generated trajectory summary。

D1 与 D2 必须使用相同 prompt、model、K* v2、task set、step cap 和 transport。
D1→D2 的 actor-visible主要差异应仅是 raw observation history。

## 4. Trajectory preservation contract

D1/D2 的完整 trajectory 是下一轮 researcher review 的主要证据，必须保留。

每个 run 使用新的、不可覆盖目录：

```text
artifacts/exploratory_memory_mvp/actor-stack-dev-d1-<date>-<commit>/
artifacts/exploratory_memory_mvp/actor-stack-dev-d2-<date>-<commit>/
```

禁止删除、覆盖或只保留 aggregate。

每 task 至少保留现有 step-level artifacts：

- initial state；
- run config；
- actor input；
- actor prompt；
- raw/parsed actor output；
- ordered admissible actions；
- action_index / resolved_action / validation；
- environment result / next observation；
- execution / episode summary；
- usage/error artifacts。

每个 D1/D2 root 额外保存一个轻量 `trajectory_manifest.json`，记录：

- development variant；
- git HEAD；
- task id / family / seed；
- artifact relative path；
- K* candidate identity/version；
- history mode；
- actor manifest/config identity；
- outcome；
- steps；
- infrastructure failure flag。

不要求为每个 step 重新计算或人工核对 SHA。已有文件身份/immutability机制够用。

Runtime raw artifacts继续按现有 repository policy 保留在本地 ignored artifact directory；
在 researcher review 完成前禁止清理。Result memo 必须记录精确 artifact paths，以便后续 coding-agent
直接读取原始 trajectory，而不是只看摘要。

## 5. Fresh independent Gate B1-R reservation

因为旧 10 tasks 已成为 development evidence，新的 actor stack 若要获得独立 admission，
必须使用从未用于 D0/D1/D2 tuning 的 fresh tasks。

**在 D1/D2 的任何模型调用之前**，先做 no-model public-only split census：

优先检查 pinned ALFWorld 的未使用 evaluation splits，例如 `valid_seen`，不足时再检查
`valid_unseen`。只允许读取：

- public task identity / family；
- public instruction；
- reset 后 public observation；
- ordered admissible actions；
- public affordance structure。

禁止读取：

- hidden placement；
- PDDL answer；
- expert/oracle path；
- task outcome；
- D1/D2 result。

如果存在足够样本，按固定 split priority + stable public hash 预注册 fresh Gate B1-R。
目标优先为每个 Phase 1A family 3 tasks（12 total）；若某 split 不足，可降到每 family 2
（8 total），但必须在 D1/D2 calls 前冻结并记录 denominator。

fresh Gate B1-R membership：

- 不得与 Source 5 / old development 10 / Phase 1A Target 20 重叠；
- 不得在 D1/D2 中运行；
- 不得根据 D1/D2 outcome 修改；
- 只为未来 independent actor admission 保留。

如果没有合格 fresh split，记录 census negative result；不要动原 20 targets 来凑 gate。

## 6. Execution order

严格顺序：

```text
A. no-model carrier/K* audit
B. implement K* candidate v2 + diagnostic-only raw-history mode
C. no-model fresh-split census and pre-register Gate B1-R if feasible
D. tests / diff / reviewable transition commit
E. run D1 once: 10 development tasks
F. run D2 once: 10 development tasks
G. preserve trajectories + result memo
H. STOP for researcher review
```

如果 D1/D2 某个 task发生 infrastructure/API failure，不静默 task-level retry。
保存 failure；只有明确的零/非科学基础设施失败才允许 protocol-consistent full-run replacement，
并必须在 memo 中说明。

## 7. What to report

D1/D2 都报告：

- success / 10；
- step-cap / 10；
- invalid action count；
- per-family success；
- per-task steps/outcome；
- model calls/tokens/cost；
- infrastructure failures。

这些指标是 development diagnostics，不是 formal gate。

不需要本轮自动做新的 failure classifier。保留完整 trajectories，下一轮 researcher review
会重点人工比较：

- D0 vs D1：carrier-correct K* 是否修复明确 contract failure / 是否产生 regression；
- D1 vs D2：raw observation history 是否减少空 receptacle 重访、inventory/look 停滞、
  object grounding drift；
- 哪些 failure 在 interface confound 降低后仍表现为信息充分条件下的明显错误。

## 8. Stop rule

D2 与 fresh-split reservation 完成后立即停止。

禁止：

- 执行 fresh Gate B1-R；
- 换第二模型；
- 修改 actor prompt；
- 加 semantic phase/controller；
- B2/B3；
- Phase 1A Target；
- Stage1/retrieval/longitudinal；
- 根据 D1/D2 result 修改 target membership。

下一轮 researcher review 才决定：

1. 是否接受 K* v2；
2. 是否接受 raw interaction history 作为最终 actor interface；
3. 是否还需要 prompt diagnostic；
4. 是否该换 stronger actor；
5. 何时执行 fresh independent Gate B1-R。
