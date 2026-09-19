# 67. Phase 1 No-H Main-Actor Reliability Screening Protocol

> 状态：Phase 1 基础执行器可靠性筛选协议（2026-09-18）
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

因此，**进入 Phase 1 付费对比矩阵之前，候选 Main Actor 必须独立通过一套严格的无记忆（No-H / C0）基准可靠性筛查**。

---

## 2. 筛查环境与测试样本定义

### 2.1 筛查环境配置
- **载体**：ALFWorld TextWorld（已录取的主载体）；
- **条件**：**纯 C0 条件（No-H, No Memory）**；
  - 仅向模型提供当前环境任务指令、当前公开观察与当前有序 `admissible_actions`；
  - **输入中绝不挂载任何既定记忆 $K^*$，绝不挂载任何探索性记忆 $H$**；
- **接口**：严格使用零基动作索引（Zero-based `action_index`）；
- **参数控制**：`temperature = 0`，`thinking = false`，`step_cap = 32`。

### 2.2 筛查样本池（15 个基准测试任务）
选取涵盖简单取放与多步复合任务的 15 个独立任务实例：
1. **简单取放（Pick & Place, 4 个）**：
   - `pick_and_place_simple-AlarmClock-None-Desk-314`
   - `pick_and_place_simple-Pencil-None-Shelf-310`
   - `pick_and_place_simple-Plate-None-Dresser-218`
   - `pick_and_place_simple-SoapBottle-None-Toilet-417`
2. **清洗后放置（Pick-Clean-Place, 4 个）**：
   - `pick_clean_then_place_in_recep-Apple-None-Microwave-14`
   - `pick_clean_then_place_in_recep-Knife-None-CounterTop-10`
   - `pick_clean_then_place_in_recep-Mug-None-CoffeeMachine-10`
   - `pick_clean_then_place_in_recep-SoapBar-None-Cabinet-424`
3. **加热后放置（Pick-Heat-Place, 4 个）**：
   - `pick_heat_then_place_in_recep-Apple-None-Fridge-10`
   - `pick_heat_then_place_in_recep-Potato-None-Microwave-10`
   - `pick_heat_then_place_in_recep-Mug-None-CoffeeMachine-10`
   - `pick_heat_then_place_in_recep-Bread-None-CounterTop-15`
4. **冷却后放置与照明检查（Pick-Cool & Look, 3 个）**：
   - `pick_cool_then_place_in_recep-Potato-None-Microwave-10`
   - `pick_cool_then_place_in_recep-Pan-None-CounterTop-10`
   - `look_at_obj_in_light-Book-None-DeskLamp-308`

---

## 3. 评测指标与准入硬性阈值（Hard Acceptance Gates）

| 指标名称 | 定义与统计方式 | 准入及格线（Pass Threshold） | 违规性质 |
|---|---|---|---|
| **非法索引率 (`invalid_action_index_rate`)** | 智能体输出的 `action_index` 超出范围或非整数的比例 | **严格 = 0.0%** (0 / 全部决策步) | 基础设施与交互契约致命违规 |
| **基础任务成功率 (`base_success_rate`)** | 15 个任务中成功达成目标（`won == True`）的比例 | **总体 $\ge 60\%$**<br/>(简单任务 $\ge 75\%$, 复杂任务 $\ge 50\%$) | 基础解题能力不足 |
| **步数上限耗尽率 (`step_cap_rate`)** | 达到最大步数 32 步仍未终止的任务比例 | **$\le 33.3\%$** (不多于 5 个任务) | 规划迟滞或探索过度冗余 |
| **语义死循环率 (`semantic_loop_rate`)** | 出现连续 4 步在两个容器之间往复 `go to A` $\leftrightarrow$ `go to B` 的任务比例 | **$\le 20.0\%$** (不多于 3 个任务) | 缺乏基础空间与记忆更新能力 |
| **平均完成步数 (`avg_steps_completed`)** | 成功完成任务的平均物理交互步数 | **$\le 22.0$ 步** | 正常交互效率基线 |
| **单任务平均 Token 开销** | 每次任务调用的平均 Input/Output Token 总数 | **作为基准记录**，供成本测算 | 预算基准 |

---

## 4. 候选模型梯队与评估定位

根据 `docs/current_state/08_experiment_scale_and_model_budget.md` 的模型政策，Phase 1 遵循**单主模型原则（1 Main Actor + 1 Offline Semantic Backbone）**，避免全笛卡尔积开销：

### 候选模型 A：Qwen3.8-Flash（当前 MVP 验证模型）
- **特点**：延迟极低、推理成本微小（约 0.12 CNY / Episode），已验证与 `action_index` 接口兼容良好；
- **已知风险**：在多步复合任务（如取物后前往水槽清洗再放置）中，偶发语义目标漂移（如取到苹果后错放进垃圾桶）；
- **定位**：低成本筛选候选与弱模型鲁棒性（Weak-model Robustness）验证锚点。

### 候选模型 B：Qwen-2.5-72B-Instruct / 商业高等级推理模型（如 Claude-3.5-Haiku / GPT-4o-mini 级别）
- **特点**：长程指令遵循与逻辑状态追踪能力显著强于轻量模型，语义循环率大幅降低；
- **定位**：若 Qwen3.8-Flash 在复合任务上的成功率未达 60% 阈值，则采用该梯队作为正式 Phase 1 的 Main Actor Backbone。

---

## 5. 跨条件冻结不变量（Cross-Condition Invariants）

一旦某模型通过本筛选协议并被确定为 Phase 1 的 Main Actor：

1. **绝对固定模型实例与配置**：
   - $C1$（纯既定）、$C2$（泛化探索）、$C3$（针对性探索）三组实验**必须且仅能使用完全相同的经过筛选的 Actor 模型版本与运行配置**；
   - **绝对禁止**在 $C3$ 中使用强模型、而在 $C1/C2$ 中偷偷换用弱模型；
2. **零修改基础提示词框架**：
   - 基础系统角色设定、动作索引格式说明、合法动作列表格式在 $C1/C2/C3$ 中保持一致，仅允许差异化呈现探索性记忆对象 $H$。
