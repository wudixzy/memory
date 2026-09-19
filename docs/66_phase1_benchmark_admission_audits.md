# 66. Phase 1 Benchmark Admission Audits: Candidate Carrier Evaluations

> 状态：Phase 1 评测载体准入审计（2026-09-18）
> 分支：`exp/minimal-exploratory-memory-validation`
> 对应任务：Phase 1 Targeting-Value Readiness — Deliverable D

---

## 1. 准入审计原则与评估维度

在选择探索性持久记忆（Exploratory Persistent Memory）的实验载体时，**严禁仅仅因为某个 Benchmark 知名度高或手头已有代码就直接作为主实验载体**。

每个候选载体必须针对其**机制拟合度（Mechanism Fit）**、**因果可配对性（Causal Pairability）**、**模型执行可靠性（Base Actor Reliability）**与**运行成本（Execution Cost）**进行严格的真实样本准入审计（初始每个候选不多于 10 个真实样本）。

### 审计的核心 10 个维度：
1. **任务族同构性（Repeated / Same-family Structure）**：是否存在可复用 established memory 的系列任务；
2. **局部备选空间（Plausible Local Alternatives）**：智能体在决策点是否存在多个物理/逻辑合理的替代路径（而非仅唯一最优解）；
3. **原生目标明确性（Native Objective）**：是否有客观、非塑形的环境成功判据与步数/代价信号；
4. **记忆决策权威（Memory Authority）**：记忆中的探索指引能否真正改变智能体的局部行为，而不是被模型先验完全覆盖；
5. **轨迹全息可测性（Full Observability）**：所有动作、观察、合法候选与中间状态是否完全可记录；
6. **确定性重放与配对能力（Deterministic Replay / Pairing）**：能否在底层世界状态层面提供确凿的因果配对证明（Pairing Proof）；
7. **基础模型可靠性风险（Base Actor Reliability Risk）**：不带记忆的基础模型在该载体上的语法/语义完成率是否足够支撑评估；
8. **比较证据生产潜力（Comparative Evidence Potential）**：探索行为是否能自然产生正向（发现更优）、负向（证明劣势）与中性证据；
9. **环境与运行成本（Environment & Compute Cost）**：执行单个 Episode 的延迟、Docker 依赖与 API 成本；
10. **纵向演化延展性（Longitudinal Suitability）**：是否支持未来 Phase 3–5 的多轮历史闭环记忆累积。

---

## 2. 候选 1：ALFWorld TextWorld（Pinned Local Carrier）

### 2.1 审查样本与真实数据（10 个真实 Case，零模型）
审计覆盖训练集与验证集中的 5 个核心任务类型：
1. `pick_and_place_simple-AlarmClock-None-Desk-314/trial_T20190908_185938_027368` (Bedroom)
2. `pick_and_place_simple-Pencil-None-Shelf-310/trial_T20190908_023553_529151` (Office)
3. `pick_and_place_simple-Plate-None-Dresser-218/trial_T20190907_013555_841038` (Living room)
4. `pick_and_place_simple-SoapBottle-None-Toilet-414/trial_T20190908_110224_056978` (Bathroom)
5. `pick_and_place_simple-SoapBottle-None-Toilet-417/trial_T20190908_091807_840742` (Bathroom)
6. `pick_clean_then_place_in_recep-Apple-None-Microwave-14/trial_T20190909_120203_117379` (Kitchen)
7. `pick_clean_then_place_in_recep-Knife-None-CounterTop-10/trial_T20190909_110347_624008` (Kitchen)
8. `pick_heat_then_place_in_recep-Apple-None-Fridge-10/trial_T20190906_182435_622538` (Kitchen)
9. `pick_cool_then_place_in_recep-Potato-None-Microwave-10/trial_T20190907_033306_962974` (Kitchen)
10. `look_at_obj_in_light-Book-None-DeskLamp-308/trial_T20190908_020029_636862` (Living room)

### 2.2 审计结论与指标画像

| 评估维度 | 审计评级 | 具体证据与实测支撑 |
|---|---|---|
| **任务族同构性** | **优秀 (A)** | 任务天然按 Pick/Clean/Heat/Cool 聚类，且在不同房间布局下呈现相同的阶段性需求。 |
| **局部备选空间** | **良好 (B+)** | 搜索阶段存在多种合法的探查顺序（开敞表面 vs. 闭合橱柜/抽屉）；取放路线存在替代容器选择。 |
| **原生目标明确性** | **优秀 (A)** | 环境提供原生目标达成标志（`won: True/False`），并以纯物理交互动作数作为显式成本指标。 |
| **记忆决策权威** | **良好 (B+)** | 既有 action-index / stepwise artifact 显示 H 能改变首步行为；这不是对未来 C3 效应大小的保证。 |
| **轨迹全息可测性** | **优秀 (A)** | 文本环境交互步步透明；每步返回确定性的当前合法动作列表 `admissible_actions`。 |
| **确定性重放与配对** | **优秀 (A)** | `docs/60` 的 10 次零模型调用审计与 PDDL 二进制校验已证明：通过 `replayable_episode_spec` 可实现 100% 字节级确定性配对。 |
| **基础模型可靠性风险** | **中等 (B)** | `action_index` 完全清除了语法拼写错误；但在 Qwen3.8-Flash 上多步清洗/加热仍有语义循环或超时风险（需通过 Actor 筛选控制）。 |
| **比较证据生产潜力** | **优秀 (A)** | 探测成功则立即获得正向步数优势证据（Positive）；未果则自然触发 `ABORTED` 记录负向证据（Negative）。 |
| **环境与运行成本** | **极佳 (A+)** | 纯 Python 本地进程运行，单个 Episode 耗时 < 2秒（无模型网络时），无 Docker 或外部守护进程依赖。 |
| **纵向演化延展性** | **良好 (B+)** | 适合后续 Phase 3（单步演化更新）与 Phase 5（多任务序列长程演化）。 |

### 2.3 准入决策：【录取为 Phase 1 主载体（Lead Carrier）】
**裁决理由**：唯一已经具备完整确定性重放配对证明（Pairing Proof）、结构化动作索引（Action Index）、零成本环境执行并完成真实环境端到端打通的载体。选定为 Phase 1 实现脚手架的单一主载体。

---

## 3. 候选 2：AppWorld（ACE Python API Environment）

### 3.1 审查样本与真实数据（6 个历史真实 Case，<=10）
这里不把 research-side family census 冒充成环境轨迹。可核对的真实执行记录来自：

- `docs/24_ace_appworld_real_batch_results.md` 的 5 个 task（`60d0b5b_1`、`37a8675_1`、`60d0b5b_2`、`432dc7a_2`、`432dc7a_3`）；
- `docs/36_appworld_final_sanity_probe_results.md` 的 1 个 registered task `8f79e35_1`，其中 K0/KC 是匹配条件而不是新的 task family。

这些是历史真实运行的 admission evidence，不在本轮重新付费复现；相关 ignored artifacts 在 fresh
checkout 中不可用，因此以下结论严格标记为“历史记录审计”，不写成当前 runner 已通过的 real-case run。

### 3.2 审计结论与指标画像

| 评估维度 | 审计评级 | 具体证据与实测支撑 |
|---|---|---|
| **任务族同构性** | **优秀 (A)** | 244 个 Scenario Families，天然支持同场景下的参数变化与多任务序列。 |
| **局部备选空间** | **极佳 (A+)** | 存在丰富的 API 组合方式（如客户端过滤 vs. 服务端查询参数；单条查询 vs. 批量接口）。 |
| **原生目标明确性** | **优秀 (A)** | 具备完备的测试断言集（Unit Tests & State Evaluation），评分严格客观。 |
| **记忆决策权威** | **良好 (B+)** | Code Agent 能够读取 Playbook / Memory 并调用指定 API 模式。 |
| **轨迹全息可测性** | **良好 (B+)** | 支持代码执行日志与交互记录，但需拦截多层 HTTP/DB 交互。 |
| **确定性重放与配对** | **较差 (C)** | 历史记录说明可以新建相同输入世界，但没有 ALFWorld 那样的 actual E0/E1 underlying-state pairing proof。 |
| **基础模型可靠性风险** | **极高 (D)** | 要求复杂多行 Python 代码编写与 API 参数对齐；中轻量模型（如 Qwen3.8-Flash）在无庞大框架支撑时基础成功率 < 30%，大量因语法/变量名报错崩溃。 |
| **比较证据生产潜力** | **良好 (B+)** | 能够清晰对比 API 调用次数与执行延迟。 |
| **环境与运行成本** | **较重 (D)** | 需要常驻 Docker 守护进程；单个 Episode 执行通常需 1-3 分钟；多轮代码交互 Token 量极大（单个任务常超 $1.00 USD）。 |
| **纵向演化延展性** | **极佳 (A+)** | 极度适合 Phase 5 真实软件助手场景的纵向记忆演化。 |

### 3.3 准入决策：【暂时搁置（Deferred as Secondary Candidate）】
**裁决理由**：环境状态回滚与因果重放配对门槛过高；基础 Actor 在代码级环境下的严重可靠性噪声将彻底吞没探索记忆的微小因果信号；执行成本与调试摩擦力过大。不进入 Phase 1 主矩阵，保留为 Phase 3/5 的高价值演进候选。

---

## 4. 候选 3：MiniWoB++ / WebArena（Web Agent & Browser UI）

### 4.1 样本状态：静态 admission screen（0 个真实执行 Case）
本轮只读取了 `third_party/automanual/automanual_miniwob`、`automanual_webarena`
和已有公开任务配置；没有启动浏览器、没有执行下面的 10 个任务，也没有把它们
计作“10 个真实 case”。下面的判断是 carrier-risk screen，不是已完成 admission。
1. `click-test-2` (基础按钮响应)
2. `choose-list` (下拉列表选中特定项)
3. `login-user` (多输入框表单填充)
4. `book-flight` (多步行程表单预订)
5. `search-engine` (搜索引擎输入与点击首结果)
6. `shopping-cart-add` (商品详情页加购)
7. `drag-shapes` (画布拖拽交互)
8. `email-inbox-forward` (邮件客户端查看与转发)
9. `calendar-picker` (日期选择弹窗交互)
10. `social-media-post` (动态发布与标签选择)

### 4.2 审计结论与指标画像

| 评估维度 | 审计评级 | 具体证据与实测支撑 |
|---|---|---|
| **任务族同构性** | **中等 (B)** | MiniWoB 单项任务过于微观；WebArena 任务异构度较高。 |
| **局部备选空间** | **较差 (C-)** | 网页交互往往具有强制性的固定交互链路（必须先聚焦才能输入，必须先点击才能弹窗），局部自由替代空间极为狭窄。 |
| **原生目标明确性** | **良好 (B)** | 页面提供完成反馈，但存在部分环境渲染判定迟滞。 |
| **记忆决策权威** | **弱 (D)** | 网页智能体高度依赖当前可见 DOM 树驱动动作，记忆往往退化为无意义的泛化提示，难以实现精准的单次探测生命周期挂载。 |
| **轨迹全息可测性** | **中等 (B)** | DOM 树庞大冗长（常超数万字符），包含大量无关噪声，Token 开销极度浪费。 |
| **确定性重放与配对** | **较差 (C)** | 浏览器渲染时钟、动画过渡与无头浏览器（Headless Chrome）异步网络通信造成严重的非因果抖动。 |
| **基础模型可靠性风险** | **高 (C-)** | 极易发生 DOM XPath 定位失败、视口滚动偏移或坐标点击偏差。 |
| **比较证据生产潜力** | **弱 (D)** | 极难产生有意义的“策略对比”，绝大多数失败是感知或定位错误。 |
| **环境与运行成本** | **昂贵 (D)** | 必须启动无头浏览器实例与本地 Web 服务器，资源开销与并发限制大。 |
| **纵向演化延展性** | **较差 (C)** | 任务粒度不适合知识提取与假设沉淀。 |

### 4.3 准入决策：【不进入 Phase 1；真实 case admission 未完成】
**裁决理由**：网页交互的反应式（Reactive）特征与冗长 DOM 噪声极度不匹配“离线发现未决比较、在线探索假设验证”的核心方法论；配对噪声大且记忆权威弱，不具备作为探索性记忆科研载体的合格条件。

---

## 5. 准入审计总结与 Lead Carrier 确认

本轮能支撑的真实-case admission dossier 是两个：ALFWorld 的 10 个零模型真实
task/reset inspection，以及 AppWorld 历史记录中的 6 个真实 task/case（不在本轮
重新执行）。MiniWoB++/WebArena 只有静态风险筛查，明确不计作真实 case admission。
因此本轮只录取 ALFWorld 一个 lead carrier，不把未完成的浏览器筛查包装成第三个
已录取 benchmark。

| 候选载体 | 配对确定性 | 记忆拟合度 | Actor 可靠性 | 运行成本 | 准入结论 |
|---|---|---|---|---|---|
| **ALFWorld TextWorld** | **100% 验证** | **极高** | **可控 (通过 Action-Index 保护)** | **极低** | **【唯一入选 Lead Carrier】** |
| **AppWorld (ACE)** | 待工程化加固 | 极高 | 差 (小模型崩溃率高) | 昂贵 | **【阶段性搁置 (Phase 3/5 备选)】** |
| **MiniWoB++ / WebArena** | 未完成真实 case admission | 未确认 | 未确认 | 较重 | **【不进入 Phase 1；仅保留风险记录】** |

**最终结论**：Phase 1 脚手架与 Pilot 实验**聚焦且仅聚焦于 ALFWorld TextWorld 这一经过严格因果审计的单一 Lead Carrier**。绝不在 Phase 1 同时横跳多个环境增加工程不可控性。
