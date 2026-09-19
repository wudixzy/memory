# 64. Phase 1 Warm-Start K* Provenance & Specification

> 状态：Phase 1 既定记忆对照规范（2026-09-18）
> 分支：`exp/minimal-exploratory-memory-validation`
> 对应任务：Phase 1 Targeting-Value Readiness — Deliverable B

---

## 1. 科学初始化边界：方法原生冷启动 vs. Phase 1 实验热启动

在论文写作与实验报告中，**必须严格区分两套完全不同的系统初始化概念**：

### 1.1 方法原生冷启动（Method-Native Cold Start）

本方法在理论与完整系统设定下，其原生初始状态定义为：

$$
\boxed{
\begin{aligned}
G_0 &= G_{tool} \\
K_0^{established} &= \varnothing \\
K_0^{exploratory} &= \varnothing \\
\mathcal{T}_0 &= \varnothing
\end{aligned}
}
$$

- $G_{tool}$：仅包含宿主环境原生声明的工具集、操作接口、基础说明与动作语法（例如 ALFWorld 的 12 个基本交互谓词及当前环境合法动作列表）；
- 不预置任何人工设计的先验策略（Strategy Taxonomy）、语义概念层次（Concept Hierarchy）或子目标规约；
- 所有 $K^{established}$ 知识与语义概念，必须在未来的完整系统中由原始任务轨迹经过 Stage 1 抽取并由模块 A 逐步闭环吸收沉淀而成；
- 所有 $K^{exploratory}$（探索性假设 $H$）初始为空，只能基于累积经验中的未决比较（Unresolved Incumbent Comparison）由模块 B 和 C 衍生。

### 1.2 Phase 1 实验受控热启动（Controlled Warm-Start $K^*$）

在 Phase 1 中，本研究的核心目标是**验证探索假设的针对性价值（Targeting Value: C3 vs. C2）**，而不是评测端到端长周期记忆沉淀。

若在此阶段直接从原生空记忆冷启动，实验结果将被以下上游混杂因素严重污染：
1. Stage 1 在极早期缺乏轨迹时的抽取噪声；
2. 模块 A 在仅有 1-2 条早期轨迹时的合并/泛化误差；
3. 智能体因完全没有基础操作常识而导致的严重随机试错，掩盖探索假设的因果效应。

因此，Phase 1 采取**实验隔离策略（Experimental Isolation Strategy）**：

$$
K_{0, \text{Phase 1}}^{established} \equiv K^*
$$

引入一份**固定、可复查、结构严格的基准既定记忆快照 $K^*$**。

> [!IMPORTANT]
> **红线原则**：严禁在任何报告、论文或元数据中将 $K^*$ 描述为“本方法的原生初始化”。$K^*$ 纯粹是用于控制变量的**实验基线控制夹具（Experimental Control Fixture）**。

---

## 2. $K^*$ 的出处来源与构建流程（Provenance）

本轮代码中的 `K_STAR_ENTRIES` 是**手工编写的、可行性-only 的控制 fixture**，不是由
Stage 1/A 自动生成，也不是从完整 ALFWorld train split 自动汇总出来的最终 memory。
这个限制必须明确写入 provenance，而不能把设计意图写成已经完成的轨迹生成事实。

当前 manifest 位于
`experiments/exploratory_memory_mvp/k_star.py::K_STAR_PROVENANCE`，其中：

- `source_histories_used = []`：本 fixture 没有把任何具体 source trajectory 当作生成器输入；
- `source_evidence_documents` 只记录此前 carrier / B-C / actor-harness review 文档；
- `stage1_generated = false`、`a_reconciled = false`；
- 当前 canonical K* digest 为
  `331728a3e001c8a3bc7e992d7605ee428501c34d0d5d8fed75a19abd98314447`。

因此，Phase 1 的结论只能解释为：在这份预先冻结的 feasibility-only K* 控制夹具下，
C3 相对 C2 是否有 targeting value；不能解释为 native cold-start memory 已经形成。

### 2.1 当前 fixture 的来源边界

四条 entry 的内容来自此前人工 review 过的 ALFWorld carrier procedure 讨论，覆盖
search/place、clean/place、heat/place、cool/place 四种**任务族抽象**。它们不是
某一批带有隐藏 placement 的 train trajectory 的自动摘要；也不携带具体 task ID、
具体 object ID 或目标位置。若未来要声称“trajectory-derived K*”，必须新建版本，
保存 source history manifest、原始 artifact hash 和生成过程，不能复用本版本的描述。

### 2.2 构建准则（Inclusion Criteria）

每一条进入 $K^*$ 的既定记忆条目，必须严格满足以下准则：
1. **纯可行性经验，非优越性断言（Feasibility, NOT Optimality）**：
   - 记忆仅陈述：*“在匹配场景下，按照当前房间观察所列顺序逐一探查可见容器，并在发现目标后进行抓取和后续搬运，该流程在物理上是可行的（Feasible）”*；
   - **严禁陈述比较性优越断言**（例如严禁包含：*“柜子比台面好”* 或 *“按列表顺序是最优解”*）。
2. **规范动作接口与 Functional Contract 完整性**：
   - 包含清晰的上下文范围（`scope`）；
   - 包含明确的前置条件识别与下游状态保护（保持手持物体、确保容器打开后再取物等）。
3. **完全剔除评估者信息与目标隐藏变量**：
   - 严禁包含任何未来测试任务的具体 ID、具体目标物品随机摆放位置（如 `fridge_1`）、或任何评估者标签。

---

## 3. $K^*$ 的标准条目规范与 Schema

$K^*$ 存储为一个有序的 JSON 列表，每个记忆对象包含以下规范字段：

```json
{
  "memory_id": "string",
  "scope": "string",
  "guidance": "string",
  "prior_comparison_evidence": null
}
```

### 3.1 核心基准条目集合

在 Phase 1 评测中，基准快照包含以下 4 条标准既定记忆：

#### 条目 1：通用物体搜索与摆放惯性规程（Search & Place Routine）
- `memory_id`: `"established-search-listed-order-general"`
- `scope`: `"ALFWorld pick-and-place tasks where the target object is not immediately visible in the entry observation."`
- `guidance`: `"Search visible receptacles in the order presented in the room observation. At each location, navigate to the receptacle, open it if closed, and inspect for the requested object. Once the target object is located, take it and carry it directly to the specified destination receptacle."`
- `prior_comparison_evidence`: `null`

#### 条目 2：清洗后摆放操作规程（Clean & Place Routine）
- `memory_id`: `"established-clean-then-place-routine"`
- `scope`: `"ALFWorld tasks requiring cleaning an object before final placement."`
- `guidance`: `"After acquiring the target object, locate an available sinkbasin, navigate to it, and clean the carried object. Then carry the clean object to the requested destination and place it."`
- `prior_comparison_evidence`: `null`

#### 条目 3：加热后摆放操作规程（Heat & Place Routine）
- `memory_id`: `"established-heat-then-place-routine"`
- `scope`: `"ALFWorld tasks requiring heating an object before final placement."`
- `guidance`: `"After acquiring the target object, navigate to a microwave, open it if closed, put the object inside, close it, and execute heating. Then retrieve the heated object and place it on the final receptacle."`
- `prior_comparison_evidence`: `null`

#### 条目 4：冷却后摆放操作规程（Cool & Place Routine）
- `memory_id`: `"established-cool-then-place-routine"`
- `scope`: `"ALFWorld tasks requiring cooling an object before final placement."`
- `guidance`: `"After acquiring the target object, navigate to a fridge, open it if closed, place the object inside to cool it, then retrieve it and transport it to the destination."`
- `prior_comparison_evidence`: `null`

---

## 4. 严格实验不变量：跨条件完全等同性

在 Phase 1 的 Frozen-history 实验中，$K^*$ 承担至关重要的**控制基准（Control Constant）**角色：

```text
       ┌────────────────────────────────────────────────────────┐
       │             Frozen Baseline Snapshot K*                │
       │           (SHA-256 Digest: Canonical JSON)             │
       └───────────────────────────┬────────────────────────────┘
                                   │
            ┌──────────────────────┼──────────────────────┐
            ▼                      ▼                      ▼
      Condition C1           Condition C2           Condition C3
  (Established Only)      (Fair Generic H)      (Targeted H from B/C)
   Input = K* only         Input = K* + H_gen     Input = K* + H_tgt
```

### 必须满足的硬性检验：
1. **字节级一致性（Byte-for-byte Parity）**：
   - 在传入 Actor 之前，序列化后的 $K^*$ 字符串及其 SHA-256 哈希值在 $C1$、$C2$、$C3$ 三组条件中必须完全相等；
   - 严禁在 $C3$ 条件中悄悄向 $K^*$ 注入更多便利信息，或在 $C1/C2$ 中删减条目；
2. **提示词挂载位置与格式完全相同**：
   - 在 Actor 提示词构造函数 `actor_context()` 中，`established_memories` 字段在三组条件下均以完全相同的 JSON 列表形式呈现于初始系统/任务上下文中。

---

## 5. 校验与防作弊清单（Anti-Leakage Audit Checklist）

- [x] **无隐蔽真值**：$K^*$ 内不包含任何测试集具体的 `trial_T*` ID、具体 object placement 或特定实体编号；
- [x] **无非对称优化**：$K^*$ 对开敞台面（CounterTop）与闭合橱柜（Cabinet）不表达任何偏好倾向；
- [x] **哈希锁定**：运行时必须通过 `compute_k_star_digest(k_star)` 记录并在 `run_summary.json` 中持久化记录其 SHA-256 哈希值；
- [x] **冷热分离说明**：报告与文档中必须附带说明——$K^*$ 为实验受控夹具，非系统原生初始化。
