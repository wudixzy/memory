# A：记忆集合的证据校准；B：纠错与改进机会

2026-09-11。本轮真实 LLM/embedding 调用 **0**，费用 **USD 0 / CNY 0**。
这是对既有真实闭环的人工语义分析，以及一个新假设的离线准备；不是 H2–H4 确认。
旧 artifacts、旧 rule_3/task_01 阴性结果和反馈协议均不改写。

## 阶段性结论与建议

**A 已有独立、具体的证据**：成功总结把“计划但未执行的最后一步”写成成功经历，
进入两条相关规则及技能；条件性的动作失败被概括成对象属性判断；validation 文本存在同源重复。
与此同时，清洗任务提供了很清楚的正常纠错、条件保留和跨任务有效复用的反向证据。
不能将整个更新器概括成“不可靠”，更不能由这些 A 问题推出 B。

**B 推荐一个改进机会筛选，而不是再找一条错误规则**：
校准 task_02 的“先分别找齐两物体，再回头拿目标”流程存在可验证的两步往返开销。
本轮无模型诊断验证：同样前三步搜索、找到书立即拿取，**6 步与原 8 步均官方成功**。
要检验的是两个流程示例共同提供的顺序承诺，是否降低采用该机会的概率；
不是质疑“持物用灯”本身，也不是扩大旧 mask 追求旧指标阳性。

建议下一轮只审批 **book-procedure-opportunity-v1，6 次独立任务启动**。
不同时追加样本、不启动第二案例或 H4。纠错 lock-in 本轮尚无足够明确的候选。

## 证据范围与阅读方法

以下简称对应真实原始目录，不是自动分类结果：

- **C**：[五任务校准](../artifacts/automanual-calibration-f13a39e724d0/)，native epoch 0–4。
- **R**：[六个 rule_3 分支](../artifacts/automanual-rule-branches-26a1a1925404/)，同一 C/task_01。
- **N**：[九任务增量](../artifacts/automanual-incremental-19a209c33a5e/)，epoch 5–13。

下面 call_id 位于相应 task 的 `model_calls.jsonl`；update_id 位于 `updates.jsonl`，
动作序号对应 `actions.jsonl` / `observations.jsonl`（初始观察单列）及 `trajectory.json`。
完整集合位于 `memory_before.json` / `memory_after.json` 的 `data.raw`，包括所有规则字段、
skill_bank、历史、控制状态和原生文件。ID 只在相应 checkpoint 内解释。

逐个核对了三个案例中的实际 Worker 规则/技能请求、可见反馈、生成代码、实际动作、
成功总结（存在时）、Builder 输入/响应、真正完成的 updater 区间和集合前后变化。
辅助精确字符串检查确认：所引用各 Builder 请求含相应 native epoch 全部已保存 interact_history 内容；
这仅证明输入可见性，**不证明 Builder 正确理解了它们**。静态 spraybottle 示例始终作为提示词示例，
不计自然样本。原始 reward/won/done 用于独立判读；adaptive loop 仍只有获准的 won-derived 反馈。

## 案例一：灯任务从一条轨迹形成四条规则和一个技能

主要原文：[C/task_00/model_calls.jsonl](../artifacts/automanual-calibration-f13a39e724d0/task_00/model_calls.jsonl)、
[动作观察](../artifacts/automanual-calibration-f13a39e724d0/task_00/observations.jsonl)、
[完整后态](../artifacts/automanual-calibration-f13a39e724d0/task_00/memory_after.json)。
起点只有官方 rule_0/1、空技能；终点 rule_0–5、一个 look 技能。

| 轨迹中的证据 | 实际提取的记忆 | 集合中的关系与条件 | 后续更新 |
|---|---|---|---|
| 步 18 在 desk_1 空手拿 desklamp 失败；步 23 拿 alarmclock 成功 | rule_2 非便携机制，rule_4 拿取失败后反转搬运方向；分别 `update_000005/000007` | 属性解释与纠错策略互补，但来自同一次失败，不是两份独立验证。rule_2 保留需跨物体验证；rule_4 的“take 失败→视为不可移动”遗漏其他拿取前置条件 | 后续 lamp 任务未再尝试拿灯；没有新增便携性反证/独立检验。不能把后续成功视为普遍验证这种诊断规则 |
| 步 25 放闹钟成功；26 开灯成功但未完成；27 拿闹钟即 won=true/done=true | rule_3 成功流程、rule_5 纠错流程，`update_000006/000008`；另存完整整理技能 `update_000001` | “放在灯旁不够”和“持物相关”有证据；“本次先拿再用灯而成功”不是实际时序。rule_3/5 与技能共享总结来源 | C/task_01 真正执行拿→开灯成功，rule_3 validation 更新；技能从 success=0 整理稿换为 success=1 的实际代码。C/task_02–04 继续更新 rule_3 validation，技能不再替换 |
| 搜索 helper 在实际代码中返回三项；官方 rule_1 返回两项 | rule_1 保留不变，技能携带三返回值 helper | 可合理保留基础接口，但集合同时提供两种同名接口，调用者必须适配；不能说二者逐字/接口完全相同 | 后续 Worker 通常显式重定义三返回值版本；本批未观测由此导致执行错误 |

**最关键的原始片段**：

Worker `7524536048f94e8685b6afb563232023` 生成“take，然后 use”；但下一请求
`114e76fe0f47476e83ff31e67093030d` 收到：

> obs_27: Act: agent.take_from('alarmclock_1', 'desk_1'). … This epoch is done. Succeed: True

该调用的成功总结却说：

> The successful completion occurred when the agent took the alarmclock and then used the desklamp while holding it.

真正执行的 Builder `6d373bdc37c742dda2a80d5becf05b57` 把相同描述写进 rule_3/5，
并认为四条规则 “do not overlap”。前一 Builder `ba4b…` 的分类回复虽也带代码，
不是实际写入来源；不能多计一轮更新。

这里丢失的不是无关动作细节，而是**灯的已有状态与成功触发时机**：
已开灯时拿起目标即完成，区别于必须在持物后另执行 use。这影响纠错时是否多做一步，
也影响如何解释完成条件。原轨迹已经支持这个区别，不需要读隐藏 evaluator 逻辑。
准确结论是“早期成功归因不忠实、充分流程被叙述成必要顺序”；
不能据此否认后来拿→用确实成功，也不声称穷尽了任务所有成功条件。

rule_4 的条件问题同样具体：Worker 工具说明已写 take 需要空手，
而 rule_4 没有限定空手、位置正确等条件就把 Nothing happens 诊断为不可移动。
这是**缺少关键前置条件的概括**；本批没有携物后拿可移动物体的自然失败，所以尚无其有害后果。
rule_2 的正向“某些不可移动物体拿取会失败”不能与 rule_4 的逆向诊断混为一谈。

**证据权重与集合更新**：C/task_01 Builder `fa6c94d6e1f14df5a18577fd4cc1a3fa`、
C/task_02 Builder `e52e85c30a83409fa86d62b8c2d91131`，均在 `update_000005`
传回含早期历史的完整 validation 文本。官方
[autobuild_utils.py:80](../third_party/automanual/automanual_alfworld/autobuild_utils.py#L80)
又将旧值与新值用 ` | ` 相接，仅保留最后三个分段，造成早期 epoch 重复出现。
**重复来源事实可直接确认；模型把它数成多份独立证据尚未确认。** Worker 的 rule_string
不显示 validation_record，但 Builder 显示完整 all_rules，故它主要影响更新端的依据，
不能直接说重复 validation 给 Worker 增加了同等数量的“票”。

集合中同时存在机制、纠错提示、流程示例和技能并不本身错误：不同角色/呈现渠道可互补。
问题是共同保留了同源的时序归因，没有把“事后整理、局部执行、另一次直接成功”明确拆开。
后续 C/task_01–04 的成功支持流程可用，却不检验其必要性或效率。

### 旧六分支应如何用于此问题

R/task_00 Worker `11ea2c34612a402b8ba52cc37ca2d656` 与 R/task_01
Worker `fb57b4fc73244b6899beeb22fce7c344` 是首对，其余四次见 R/branches.json。
六次均为同样 6 个动作，规则单渠道 mask 的旧主指标两组都是 0/3。
这否定该任务/该渠道的边际预测；rule_5、技能仍给出持物用灯流程，
因此不能据此判 A 不存在，也不能宣称整个流程记忆集合无行为影响。
本报告不重算旧预测、不把阴性更名为阳性。

## 案例二：清洗后关闭冰箱放置失败，如何修订整个集合

原文：[N/task_01 请求与响应](../artifacts/automanual-incremental-19a209c33a5e/task_01/model_calls.jsonl)、
[更新区间](../artifacts/automanual-incremental-19a209c33a5e/task_01/updates.jsonl)、
[后续 task_04](../artifacts/automanual-incremental-19a209c33a5e/task_04/model_calls.jsonl)。
前态 rule_0–7、look/plain-put 两技能；后态 rule_0–8，新增 clean 技能。

| 证据 → | 记忆 → | 与其他记忆关系 → | 后续更新 |
|---|---|---|---|
| N/task_00 真正找书→拿→放沙发成功 | Builder `c39216e2eebb4e0dba93b2a7672d8528` / `update_000005` 新 rule_7；`update_000001` plain-put 技能 | rule_7 依赖 rule_1 搜索；技能是实例实现。开放沙发不检验关闭目标的前置条件 | N/task_01 初次 Worker `8169cab8484c4478bf344d4f5801da2c` 实际收到两者；照搬骨架但补上 clean，未补开目标 |
| task_01 步 5 拿 apple_3，7 清洗；8 fridge closed；9 put Nothing happens；10 open；11 put 成功 | Builder `ac3cdc0989734e739e46c4c78fa1891b` / `update_000005` 修订 rule_7；`000006` 新 rule_8 | rule_7 补条件并仅在 compound task 插入 clean，保留简单放置知识；rule_8 独立描述动作前置条件，和规则/技能是同源互补，不是额外独立验证 | task_04 10 closed→11 open→12 put 成功；`71d74c5d18224232a590ef4cca85523e` / `000007` 更新 rule_8，仍注明 cabinet/drawer 待验证 |
| task_01 成功后 Worker `ac103a7a506349a6b24d260701b4d283` 重组完整代码 | `update_000001` 保存 clean success=0 技能 | 整段没有从初态重执行，但原生标签区分非直接成功；新代码是已执行片段的合理组合，不能直接指为假技能 | task_04 直接成功代码将其替换为 success=1。task_07 使用该技能，清洗杯子并放 shelf 成功；旧规则/其他技能保留 |
| task_02 实际 cool bread 后 put countertop | `f02faf09c8a34144a525efd64222a919` / `000005` 扩展 rule_7 的 transformation 分支 | clean/cool 的共同结构压缩合理；新增 heat_with 与 microwave/stoveburner 属未在该轨迹验证的概括；工具说明已提供 heat/microwave，并非所有词都凭空生成 | 后续 clean/cool 成功验证各自条件，不会自动验证 heat/stoveburner。没有自然加热反例，不定性为已证实有害规则 |

原始 Worker 第二次回复 `1a0be18b4a4b439eb51b86c94c57f7a5` 说：

> rule_7: … If Y is closed, open it first.

但它收到的旧 rule_7 不含这一句。这是对旧知识的错误归因，不是纠错失败。
Builder 分类 `b86b819863814af6a4c0e65c41b72a29` 正确指出：

> This covers go_to failures, not put_in_or_on failures on closed receptacles.

随后真正执行的更新同时补流程与前置条件。它没有机械接受 Worker 的“原规则早已教过”说法，
也没有把缺陷一概归咎执行者。**这是 A 的正常纠错证据，也是不能笼统宣称 correction lock-in 的反证。**

被保留的关键区别包括：找东西时开容器≠放东西时开目标；clean 不是所有 put 任务必需；
开放表面与关闭容器不同。rule_7/8 重复开门提示不构成错误，因为两者承载完整流程与局部前置条件。
尚未解决的是泛化验证标记没有按 rule_7 的每个 transformation 分支细分，后续“再次成功”
可能使整条复合规则显得都被验证；当前只有文本结构风险，没有独立权重测量。

## 案例三：helper 的接口变化、保留旧知识和技能更新选择

原文：[N/task_07/model_calls.jsonl](../artifacts/automanual-incremental-19a209c33a5e/task_07/model_calls.jsonl)、
[N/task_08/model_calls.jsonl](../artifacts/automanual-incremental-19a209c33a5e/task_08/model_calls.jsonl)、
[task_07 完整后态](../artifacts/automanual-incremental-19a209c33a5e/task_07/memory_after.json)。
前后都是 9 条规则、4 个技能，变化主要在 rule_1 示例和 validation，不是新增一种算法。

| 证据 | 提取/更新 | 集合关系 | 后续 |
|---|---|---|---|
| task_07 Worker `b38c625f152a455196edb71401001008` 实际定义三返回值 find_object，先查 shelf、再开 cabinet_1–5，第 15 步见 cup | Builder `7662984473dd4efaa8b6361ac25181c4` / `000005` 保留旧两返回值 find_object，新增具不同名字的三返回值 find_object_with_obs | **合理的接口区分**：不是仅因改名就虚构经验。避免覆盖旧调用约定，有助保留有效知识；技能仍有三返回值同名函数，调用端仍需适配 | task_08 Worker `fbc8dddca5464b22ba23ffc4e6720f2d` 收到新规则和 cool 技能，继续显式定义三返回值 find_object |
| task_08 真实三返回值实现找杯成功 | Builder `dfec87b7feec4de383b7660be9fc7bf6` / `000005` 写 find_object_with_obs 被使用成功 | 按字面是命名/来源不精确；按功能属于等价变体的验证，不应升级成“虚构成功” | 没有由此造成接口错误或任务失败；缺少两种 helper 权威冲突的行为证据 |
| task_07 代码有 shelf_1/2/3 备选，实际首个放置即成功 | `000006` 更新 rule_7 清洗及开放 shelf 的验证；技能未替换 | 合理记录成功的 shelf_1，而不能声称备选都验证；新 fallback 并未进入长期技能 | 第一份 success=1 clean 技能仍是 task_04 苹果进 microwave 的代码，不是最后一次代码 |
| Builder task_07 注意到重复 go_to；task_08 注意到 fridge-before-sink 的搜索顺序 | 明确判断不足以新立规则，实际只更新已有规则的验证 | 没有采用“每个步骤都必须存入 memory”。这种选择可能是合理压缩；task_08 关于杯子通常位置只是推断，不能据此断定最优排序 | 改进没进入技能不完全是模型忽略，见下方官方写入门槛 |

两个原始片段支持“有审慎压缩，而非全然不反思”：

> task_07 Builder: “This is harmless but wasteful. … Not worth a standalone rule”

> task_08 Builder: “not a robust enough phenomenon to warrant a new rule — it's a heuristic, not a mechanism.”

后一条不是对当前搜索顺序优劣的实验验证；本报告不把它当杯子分布事实。
公开 helper 的 `go_to` 和 wrapper 当前地点缓存会造成冗余，需要与真正跨位置往返区别。

**重要的集合更新机制事实**：官方
[Skill_Bank.add_skill:176–178](../third_party/automanual/automanual_alfworld/autobuild_utils.py#L176)
只有类型未存在或旧 `success != 1` 时才替换技能。故第一份直接成功的类型技能被保留，
不是每个新成功都选更优技能。N/task_04 clean 从 0→1 能替换，task_07 后不再替换；
C/task_01 look 从 0→1 后，task_02–04 也不再替换。
这给 improvement lock-in 一个**结构上的可能机制**，但不能单凭固定门槛证明行为锁定。
规则仍能修订，Worker 也确实会适配技能。即使下一轮出现更好代码而 skill 不变，
也须先归因这个确定性写入门槛，不能自动称为“模型忽视反证”的 H3。

## A 的总体判断：强度分层

| 强度 | 本批可以说什么 | 不能说什么 |
|---|---|---|
| 直接提取/更新问题 | 灯任务成功时序错记；rule_4 缺拿取失败的诊断前置条件；同源 validation 重复 | 已造成可复现任务伤害、全部规则错误 |
| 合理但未充分验证 | portable 跨类型推论；rule_7 的 heat/stoveburner 扩展；关闭容器泛化中尚未覆盖的类型 | 后续任意成功足以验证整个范围 |
| 正常纠错/有效压缩 | open-target 修补；clean/cool 条件化插入且保留 plain put；helper 双接口保留；不把未发生 fallback 当验证 | 任务成功能证明全部抽象和更新正确 |
| 证据不足 | 重复文本是否被当独立票数；不更新技能是否抑制改进；A 问题的实际因果后果 | 从“长、重复、稳定”直接推出 lock-in |

多记忆集合的关键不是条数，而是**同源证据在多个表示间传播、哪些条件和验证层级随之消失**。
当前 A 阶段结论值得保留，不因没有独占信息的单规则而否定研究问题。

## B：纠错与改进分别判断

### 纠错：暂不推荐付费案例

1. rule_4 的“失败→不可移动”有条件缺失，但现有后续任务没有明确的携物拿取失败、随后可恢复成功事件。
   尚缺同一决策点上可获得的区分证据，不能只 mask 后等待偶然错误。
2. rule_7/8 的开门知识有替代来源，这不是排除它的唯一理由；更关键的是**开门获得的是正确补救**，
   目前没有需要反驳的承诺及被压低概率的纠错事件。把两条规则和 clean 技能都删掉、制造一次放置失败，
   主要验证知识作用/再学习，不直接验证 correction lock-in。
3. 灯任务的“已开灯再拿即可”由原轨迹支持，但旧分支本来就拿后用，
   没有明确收益足以支付重做顺序必要性实验。本轮不恢复旧预测。

### 推荐案例：book 的流程示例是否妨碍机会性拿取

真实前态：**C/task_01/memory_after.json**，native epoch 2 前。
文件 SHA256 `e4ec1a9e226372fc1e729c337a8232360e850dda212f2bc5af6c3d1da91ba60e`；
snapshot SHA256 `85e5dd4a3875b38a09b563248b6f7bb6df8f95a99d0ffeef9c4a227665d5000c`。
目标 C/task_02：
`look_at_obj_in_light-Book-None-DeskLamp-317/trial_T20190909_201143_217673`，seed=42。

Worker `2deb010034e14e9db39fdcb743cf625f` 的实际 messages[5] 同时包含：

> rule_3 example: “Find X and Y using find_object.”，然后 “Go to X's location and take X.”

> look skill: Step 1 search alarmclock → Step 2 search desklamp → Step 3 go back and take alarmclock

这两个表示共享“完整搜索阶段先于拿取阶段”的流程承诺；不是要求全局删除持物知识。
生成代码也按书搜索→灯搜索→回头拿书组装。真正轨迹：

| 原步 | 实际动作与可见证据 | 机会意义 |
|---|---|---|
| 1 | go sidetable_1，看见 desklamp_1 | 已获灯 ID 和位置，之后没有物体移动/关灯事件 |
| 2 | go dresser_1，无书 | 保持同样的搜索成本，不靠隐藏位置捷径 |
| 3 | go bed_1，看见 book_1 | 当前就能尝试拿取；不需先空手回灯旁 |
| 4、5 | 回 sidetable_1，再回 bed_1；各自内容与此前相同 | 真正跨地点往返，不是 go_to 当前地点的 wrapper no-op |
| 6–8 | take book_1、go sidetable_1、use desklamp_1，won=true | 已选流程有效，但存在可比较的更低动作成本路径 |

**E***：在第一次观察到目标书的访问中，离开该容器前成功拿取；随后仍成功完成同一任务。
对已观察到灯的路径，进一步核查是否复用原观察，不再先空手返回确认。
更优标准：同一任务/seed/初始状态及成功约束下，实际环境动作更少、无新增失败；
不声称全局最优，不用只改生成文字或漏做任务要求当改进。

官方一次生成整段 Python，并非每步观察都新调用 Worker。中途观察由执行中的 Python 获得；
替代方案需要代码把拿取放在第二次搜索之前，或保存/复用已经观察的位置。
保留的 find_object 不缓存搜索中所有非目标物体，**但仍可在找书返回后立即拿，再调用找灯**，
无需新 helper 或修改环境 wrapper。本案例不把整段代码结束后才到达模型的反馈假装成逐步重规划。

本轮诊断：[report.json](../artifacts/automanual-book-opportunity-v1/report.json)。
两次新官方环境/reset 的原 8 步重放与原始初始观察、逐步 observation/reward/won/done 全部相同。
第三个独立环境保持前三步，接原步骤 6–8，**6 步 won=true**。
动作由上述公开轨迹重组；不读专家计划选路线，不输入到任何正式分支。
这是人工诊断证明“存在机会”，不是 Agent 自主发现，也不是 H1/H2；只覆盖这个任务及这些路径。

**行为预测**：减少两处完整流程示例后，首次见书即拿取的比例上升，
在已获灯位置时空手返灯→回书的事件减少；若确实采用更短成功流程，观察 Builder 如何记录。
支持链目前是“记忆已注入→生成/执行相容流程→Builder 再次验证 rule_3”，
最后由 C/task_02 `e52e…` / `update_000005` 支持。尚缺干预导致行为变化的因果环。

**反驳与混杂**：

- 两组行为不变：不支持该呈现渠道的边际预测，不扩大屏蔽、不追加重复。
- 仅改变搜索顺序、运气更早看到书：H1 线索，不自动算机会性拿取或 B。
- 拿取更早但失败/动作不减少：没有证实相同约束下改进。
- 更短路径可因基础模型本来的规划习惯、prompt 长度、示例减少而产生；两项联合移除不识别单项效应。
- rule_3 正文、rule_5、公共工具、静态示例、helper、历史和 Builder 均保留；它们仍可提供相同部分信息。
- 输入已经包含灯的位置；这里关注**比较/采用机会的受限**，不是最初灯位置观察被遮断。
  若只是机械减少调用、模型/updater 不理解更好条件，最多 H1/效率变化，不直接 H2。

## 下一批固定设计：一个案例、六次启动

机器清单：[procedure_branches.json](../configs/automanual_alfworld/procedure_branches.json)。
顺序 **I1 → M1 → M2 → I2 → I3 → M3**；每次独立恢复上述 checkpoint，新官方环境和 guest，
epoch=2，完整任务及原生更新，共享 run ledger。不继承任何分支更新。
相同 seed 不等于远程 API 严格配对随机实验；3 次/分支仅筛选，不作显著性宣称。

干预名称 **actor_procedure_example_mask**，预先固定两项：

1. 仅删 Worker 请求内 rule_3 的 `example` 呈现及相应 “For example” 引导，**保留 rule_3 正文**。
2. 仅删已检索 look skill 的顶层任务步骤（`# [Step 1]` 起至末尾），
   保留原文 helper 定义、原技能任务描述和初始观察。FAISS 仍检索同一真实技能，函数照原样注入。

没有改 persistent rule/skill、rule ID、validation/history、Builder 的旧集合，也没有新写策略提示。
其余 Worker 消息、公共 API、静态示例和所有 helper 不变。删除的示例还包含具体物体位置列表、
assert 和用灯步骤，**因此效应解释是“这一组流程示例的总体呈现作用”，不是某一句顺序词的纯效应**。
这些信息与流程承诺相关；机制要求仍由保留正文/纠错规则提供。若需要单项归因，须另行设计，不能事后扩大本批。

这是新假设：旧实验删除 rule_3 全条、保留完整技能，在同位置闹钟任务上测“放下后用灯”；
本实验保留持物规则正文，去两个程序模板，在异位置书任务上测**早取物与免往返**。
旧阴性不重标，旧指标不改写。

### 记录与判读

- 主指标：首次看到书的访问期间、离开前是否有原始 `You take book_…` 成功反馈。
  尝试失败不计拿取；未完成 artifacts 主指标 null，已有观察单列。
- 次指标：首次成功拿取前返回已知灯位置的实际跨位置动作；首见/首取序号；到 won 的总动作与失败动作。
  人工核对重复观察内容和已有证据；不能将未执行的代码分支计为路径探索。
- 官方 won/终态、调用/token/独立币种费用、全部 updater 区间。
- 对得到 E* 的分支：查看 Builder 是否认识首次见物时可拿、是否改 rule_3 example/条件，
  是否只追加成功记录，是否错误声称仍走旧流程；对未得 E* 的分支查看如何维护原承诺。
- 特别检查原生 Skill_Bank.add_skill no-op：已 success=1 的旧技能不替换是官方门槛，
  不能单独计作 H3；规则端对新证据的吸收才需要进一步语义判读。

证据强度：A 可独立判断提取忠实度；H1 需组间真实行为变化；B/H2 还需有价值的替代路径
在 intact 更少被发现/采用，排除只缩短文字等解释；H3 需轨迹差异进入 updater 并差异性维持承诺。
没有这条闭环前不安排 H4。正常任务失败纳入分析，不换题；设施中止不是普通任务失败。

### 模型、预算、停止与命令

生成 DeepSeek 官方 request `deepseek-v4-flash` / required return `deepseek-flash`，
thinking=false、temperature=0；embedding DashScope 北京 `text-embedding-v4`、1024、float。
反馈仍 `automanual-native-won-v1-2026-09-11`；沿用官方 chat、受限 Python 和 embedding substitution 的非等价边界。

上限：12 transport/task，72/run，零自动网络重试、零补跑；
USD 6/task、6/run；CNY 0.05/task、0.20/run，独立核算。
基于 C/task_02 原用量 2 generation + 2 embedding 的六倍：预期约 24 请求、
USD **0.020118312** / CNY **0.000036**。这是原轨迹推算，不是分支测量/账单；
示例减少、重规划和更新都可能改变用量。

采用已归档 2026-09-11 保守峰值价格：USD 每百万 hit/miss/output=0.006/0.30/1.20；
北京 embedding CNY 0.5/百万输入（来源及当时核实见 docs/14，不假设免费额度）。
本轮未查询新价格、未访问模型；下一次实际执行若价格依据失效须先核实。
请求前仍按生成输入 1,048,576 + 输出 2,000 预留 USD 0.3169728/请求；
embedding 每条预留 8,192 tokens，即 CNY 0.004096/条。
这是逐请求保守预留、取得可信实际 usage 后释放未花部分；**并非承诺能以 6 美元发送 72 个满上下文请求**。
当前清单与该机制相容；若实际长用量令下一请求无法预留就整批停止，不放宽检查。
provider 未报告费用保持 null，本地估算另列。

未知费用/用量、模型身份变化、设施故障、预算中止或原生更新未完整完成：保存部分 artifacts，停止整批。
两组均完整原生更新的正常任务失败继续固定清单，不补跑。

默认计划（本轮已执行，零调用）：

```bash
python scripts/direct.py conda run -n memory-automanual python scripts/run/automanual_procedure_branches.py
```

**以下仅供下一轮审批后执行，本轮未执行**：

```bash
python scripts/direct.py conda run -n memory-automanual python scripts/run/automanual_procedure_branches.py --execute --output artifacts/book-procedure-opportunity-v1
python scripts/direct.py conda run -n memory-infra python scripts/analysis/automanual_evidence.py --source artifacts/book-procedure-opportunity-v1 --output artifacts/book-procedure-opportunity-v1-analysis.json
```

目录已存在会拒绝覆盖。汇总 `branches.json` 固定顺序和来源；每任务实际发送请求由现有 provider 写
`model_calls.jsonl`，而非只记原生组装前文本。`intervention_diff.json` / `actor_request_example_view`
保存消息视图精确 diff，`task_call_ordinal` 对应任务 usage.calls 的一基次序；
生成请求/响应/usage 仍由 provider 的同一 call_id 关联。
`memory_injections` 的旧 rule/skill/helper 事件是**干预前的原生组装来源**，
最终模型可见文本以 model_calls 为准。总体 memory diff 和原生更新区间不混入该输入视图差异。

## 最小接线与本轮验证

未修改 upstream 文件/patch、提示词文件、memory 算法、schema 或计费实现。
复用现有六分支 runner，只增加可选 plan factory 与 manifest 干预说明；
新入口以局部 callback 修改 Worker messages[5] 的两段确切原文，Builder 调用不经过变换。
任何预期段缺失即停止，不模糊匹配或扩大 mask。正常重规划仍保留当任务 guest，
不同分支恢复新副本；新干预类型在 manifest 独立标记，不伪装 NoIntervention。

离线请求证据：[automanual-procedure-offline-v1.json](../artifacts/automanual-procedure-offline-v1.json)，
对真实 C/task_02 call `2deb…` 的保存请求作双视图验证，保留 source SHA 与完整前后文本。
**这是保存请求的离线变换，不是新模型响应，也没有重做官方环境完整 actor/updater 执行**。
独立小型回归确认执行 callback 只改 Worker、Builder 不变、下一 intact 不继承 mask。
FAISS/helper 原路径未改，因此不重新安装/重测整套检索设施。

实际执行均通过 `scripts/direct.py`；无模型诊断另拒绝网络及 `.env` 读取，
真实 transport 原有 ProxyHandler({})/TLS/零重试不变。
memory-infra Python 3.10.20、Ruff 0.12.0；memory-automanual Python 3.9.16；未安装/升级依赖。

```bash
python scripts/direct.py conda run -n memory-automanual python scripts/smoke/automanual_book_opportunity.py --execute
python scripts/direct.py conda run -n memory-infra python scripts/run/automanual_procedure_branches.py --offline
python scripts/direct.py conda run -n memory-infra env PYTHONPATH=src python -m unittest discover -s tests -v
```

前两命令通过：3 次有界官方环境 reset（8/8/6 动作），没有模型；一次保存请求双视图验证。
另运行新入口默认计划、相关 Ruff/format/compileall 和 git diff --check。
测试与最终检查结果见本报告收尾记录。没有重跑校准、六付费分支、独立 API probe、全 upstream 重放。

最终收尾：**164 项测试全部通过（2.566 秒，含本轮 5 项小型回归）**。
相关 6 个 Python 文件的 Ruff、format --check、compileall，以及 git diff --check 全部通过。
初次 lint 的 import/长行问题已在最终检查前修正。默认计划在两个既有 conda 环境均通过。
新增分析字段已离线核对 C/task_02：首见书=3、首次成功拿取=6、首次访问拿取=false、
空手返回已知灯位置=[4]；提取结果保存
[automanual-ab-calibration-analysis-v1.json](../artifacts/automanual-ab-calibration-analysis-v1.json)，
不覆盖旧分析。中止产物新增指标同样 null，并保留已观察前缀；旧 lamp 主指标不变。

对应最终命令（`FILES` 仅为下列六个任务文件，不涉及凭证/环境变量）：

```bash
FILES="scripts/run/automanual_procedure_branches.py scripts/run/automanual_rule_branches.py scripts/smoke/automanual_adapter.py scripts/smoke/automanual_book_opportunity.py scripts/analysis/automanual_evidence.py tests/test_procedure_screen.py"
python scripts/direct.py conda run -n memory-infra ruff check $FILES
python scripts/direct.py conda run -n memory-infra ruff format --check $FILES
python scripts/direct.py conda run -n memory-infra python -m compileall -q $FILES
python scripts/direct.py git diff --check
python scripts/direct.py conda run -n memory-infra python scripts/analysis/automanual_evidence.py --source artifacts/automanual-calibration-f13a39e724d0 --output artifacts/automanual-ab-calibration-analysis-v1.json
```

保留原有 dirty worktree，无 commit。最终 `git status --short` 目录级摘要：
修改 AGENTS.md、README.md、docs/01、docs/02（除 README 新链接外均为原有改动）；
未跟踪 .env.example、.gitignore、configs/、docs/03–15、pyproject.toml、scripts/、src/、tests/。
本轮仅改动 README、docs/15、新固定清单/入口/诊断脚本/5 项测试，以及原 runner 的复用点和分析指标。
真实 .env、运行 artifacts、third_party 仍忽略；未读取/改动凭证、未安装依赖。

## 完整 A→B→A 还缺什么

已取得：有条件缺失/归因问题也有正常纠错的 A 实例；自然流程承诺、实际复用、后续验证记录；
一个有同任务官方执行支持的改进机会。
缺：该记忆呈现组导致机会采用率变化；变化确有改进价值；原生更新针对不同经历出现可解释差异。
不能把 skill 写入门槛、wrapper 缓存、重复 validation 或一次成功分别当作完整闭环。

**明确建议：继续 A 的集合/时间分析，并仅执行上述一个改进机会筛选，暂不付费测试纠错 lock-in。**
如果筛选没有可解释差异，保留 A 结论，不追加 mask；届时再判断是否有明确的信息缺口值得采样。
目前不自动采加热/双物体，不切 baseline，不降低整个 A+B 研究问题的优先级。
