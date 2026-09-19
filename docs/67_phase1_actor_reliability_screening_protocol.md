# 67. Phase 1 Main-Actor Reliability Screening Protocol

> 状态：Phase 1 基础执行器可靠性筛选协议（2026-09-19，pre-pilot correction）
> 分支：`exp/minimal-exploratory-memory-validation`
> 对应任务：Phase 1 Targeting-Value Readiness — Deliverable E

---

## 1. 为什么在评测记忆前必须先筛选基础 Actor？

在以往智能体记忆评测中，最普遍的实验失真之一是：
> **用记忆干预去代偿、掩盖一个本就不合格的基础智能体（Using Memory as a Crutch for an Unreliable Actor）。**

如果基础 Actor（Main Actor Backbone）本身在无任何记忆的情况下：
- 经常输出非法的动作格式；
- 在房间内无休止地在两个容器之间来回走动（语义死循环）；
- 或者即使找到了目标物品也忘记捡起、无法执行基础的下游动作；

那么在 $C1 / C2 / C3$ 实验中所观测到的步数变化与成败结果，将被**基础模型的随机行为方差完全主导**，根本无法分辨探索性记忆是否产生了真正的因果收益。

因此，**进入 Phase 1 付费对比矩阵之前，候选 Main Actor 必须独立通过以 C1 为主条件的
可靠性筛查**。C0 可以作为辅助诊断，但不能代替 `Actor + K* = C1` 主 gate；否则筛查
没有覆盖 Phase 1 实际 baseline 的 memory-context 负载。

---

## 2. 筛查环境与测试样本定义

### 2.1 筛查环境配置
- **载体**：ALFWorld TextWorld（已录取的主载体）；
- **主条件**：**C1（Established-only）**；
  - 向模型提供当前环境任务指令、当前公开观察、有序 `admissible_actions` 和固定 `K*`；
  - **绝不挂载探索性记忆 $H$**；
- **辅助条件**：C0（No-H, No Memory），只用于区分 K* context 负载与基础执行能力；
- **接口**：严格使用零基动作索引（Zero-based `action_index`）；
- **参数控制**：`temperature = 0`，`thinking = false`，`step_cap = 32`。

### 2.2 筛查样本池（冻结的 15 个 Calibration tasks）

Calibration 不再手写一组可能与 target 重叠的 task。它是
`cases/phase1_calibration_registry.json` 中由完整 public universe 通过固定 hash
partition 生成的 15 个 task，parent registry digest 为：

```text
fdd5b37024b71c2369ede7c56f37e8be87dfde4db851ece7a51fb4555da64dcd
```

该 registry 的 digest 为：

```text
fa76c5048384f8899e3563166f1db33ce10d1f322a74705056c597fe3a97ae52
```

它与 Source（5）和 Phase 1A Target（20）通过 validator 强制不相交；执行前应加载该
registry，而不是临时补 task。它覆盖当前 pinned split 的六个公开 task families，且
selection 不读取任何 task outcome。

---

## 3. 评测指标与准入硬性阈值（Hard Acceptance Gates）

| 指标名称 | 定义与统计方式 | 准入及格线（Pass Threshold） | 违规性质 |
|---|---|---|---|
| **非法索引率 (`invalid_action_index_rate`)** | 智能体输出的 `action_index` 超出范围或非整数的比例 | **严格 = 0.0%** (0 / 全部决策步) | 基础设施与交互契约致命违规 |
| **基础任务成功率 (`base_success_rate`)** | 15 个 C1 任务中成功达成目标（`won == True`）的比例 | **至少 12/15**（80%） | 基础解题能力不足 |
| **步数上限耗尽率 (`step_cap_rate`)** | 达到最大步数 32 步仍未终止的任务比例 | **至多 2/15** | 规划迟滞或探索过度冗余 |
| **语义死循环率 (`semantic_loop_rate`)** | 出现连续 4 步在两个容器之间往复 `go to A` $\leftrightarrow$ `go to B` 的任务比例 | **至多 2/15** | 缺乏基础空间与记忆更新能力 |
| **平均完成步数 (`avg_steps_completed`)** | 成功完成任务的平均物理交互步数 | **仅记录，不作为本轮硬 gate** | 正常交互效率基线 |
| **单任务平均 Token 开销** | 每次任务调用的平均 Input/Output Token 总数 | **作为基准记录**，供成本测算 | 预算基准 |

---

## 4. 候选模型梯队与评估定位

根据 `docs/current_state/08_experiment_scale_and_model_budget.md` 的模型政策，Phase 1 遵循**单主模型原则（1 Main Actor + 1 Offline Semantic Backbone）**，避免全笛卡尔积开销。模型不再由代码常量决定，而由
`experiments/exploratory_memory_mvp/cases/phase1_actor_manifest.json` 冻结；当前 manifest 只是
Qwen3.8-Flash candidate，`selection_status` 明确标为 pending gate。

### 候选模型 A：Qwen3.8-Flash（当前 MVP 验证模型）
- **特点**：延迟极低、推理成本微小（约 0.12 CNY / Episode），已验证与 `action_index` 接口兼容良好；
- **已知风险**：在多步复合任务（如取物后前往水槽清洗再放置）中，偶发语义目标漂移（如取到苹果后错放进垃圾桶）；
- **定位**：低成本筛选候选与弱模型鲁棒性（Weak-model Robustness）验证锚点。

### 后续候选模型处理

本轮不选择、切换或调用其他模型。如果当前 candidate 未通过独立 C1 gate，研究者应
重新选择一个候选并生成新的 actor manifest；不得依据 Phase 1 target outcome 临时替换
模型，也不存在由某个 target 成功率触发的自动换模规则。通过 gate 后的唯一正式配置仍由
一个冻结的 actor manifest 同时约束 C1/C2/C3。

---

## 5. 跨条件冻结不变量（Cross-Condition Invariants）

一旦某模型通过本筛选协议并被确定为 Phase 1 的 Main Actor：

1. **绝对固定模型实例与配置**：
   - $C1$（纯既定）、$C2$（泛化探索）、$C3$（针对性探索）三组实验**必须且仅能使用完全相同的经过筛选的 Actor 模型版本与运行配置**；
   - **绝对禁止**在 $C3$ 中使用强模型、而在 $C1/C2$ 中偷偷换用弱模型；
2. **零修改基础提示词框架**：
   - 基础系统角色设定、动作索引格式说明、合法动作列表格式在 $C1/C2/C3$ 中保持一致，仅允许差异化呈现探索性记忆对象 $H$。
