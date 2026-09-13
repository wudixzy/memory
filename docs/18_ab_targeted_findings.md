# A 的集合更新证据与 B 的前置条件迁移筛选

后续状态：本页保留第一轮离线分析/准备的历史范围；授权六分支已执行，结果见 [docs/19](19_transform_precondition_results.md)。下文“本轮零调用”和待审批建议指准备轮，不指后续执行轮。§7–8 的解释判据已在执行前按 review 修订。

2026-09-12；docs/17 第一轮集中交付。**本轮真实 LLM/embedding 调用 0，USD 0 / CNY 0。**
没有启动付费任务、重做校准或旧 rule_3/Book 分支。只新增一个任务的无模型环境诊断。

**建议只审批 `transform-precondition-screen-v1` 六分支。** 已有自然 checkpoint 足够，
来源形成名额使用 0，A 额外补任务名额使用 0，B 使用 6/6；总计 6，不凑满 11。
新候选是“把容器放置的开门条件迁移为变换操作的必要条件”，不是再确认旧顺序词效应。
已证明目标环境存在公开动作可获得的反证/改进机会；**尚未证明 memory 限制其发现**。

## 1. 证据范围与本轮新增判断

沿用 [docs/15](15_memory_set_and_opportunities.md)、[docs/16](16_book_procedure_results.md) 的原始定位，
不重写旧结论。下文简称：

- C：`artifacts/automanual-calibration-f13a39e724d0`。
- P：`artifacts/book-procedure-opportunity-v1`，P/task_00=I1、P/task_01=M1。
- N：`artifacts/automanual-incremental-19a209c33a5e`，task_00–08 对应 native epoch 5–13。

call_id 在各任务 `model_calls.jsonl`，update_id 在 `updates.jsonl`，动作位置从 1 开始。
读取的是实际请求、返回代码、`actions/observations.jsonl` 和 `memory_before/after.json`；
更新按完成区间的 before/after 比较，不将 Builder 分类回复里未执行的代码算作更新。
完整 raw 包含 rule_manager 全字段、skill_bank、历史、控制字段和原生文件，而非注入文本。
八个相邻 N 边界的 **前任务 memory_after JSON = 后任务 memory_before JSON**；没有跨任务断链。

本轮新增的主要区分：

1. 正确知识和错误主张可以在**同一个不断增长、任务继续成功的集合**里同时保留；
   不能用集合大小/成功率判可靠，也不能因一处错误否定全部压缩。
2. N/task_01 的“put 前开门”修补保留到 task_08，没有被中间任务覆盖；
   **另一条更强的“transform 前必须开门”在 N/task_02 新加入，之后没有修订**。
   后者不是 task_04 清洗迁移才形成的，更不是所有开门规则的共同语义。
3. N/task_02/05 的成功没有比较不开门；将它提升为必要条件，是从充分流程到必要条件的越界。
   本轮官方环境诊断进一步验证其 heat 子情形确实不成立。A 的这一判断不依赖付费 B 分支。
4. 未观察到“不可靠集合必然导致纠错锁定”：N/task_01 正常纠错、N/task_03/06 保留简单放置、
   N/task_07 保留旧 helper 接口、P/I1 主动提出待验证优化，都是反向证据。

## 2. A 案例一：校准首次灯任务的多记忆形成

原件：[C/task_00 模型事件](../artifacts/automanual-calibration-f13a39e724d0/task_00/model_calls.jsonl)、
[原始观察](../artifacts/automanual-calibration-f13a39e724d0/task_00/observations.jsonl)、
[更新](../artifacts/automanual-calibration-f13a39e724d0/task_00/updates.jsonl)。
起点 rule_0/1、空技能；终点保留这两条并新增 rule_2–5、look 技能。

|实际证据|记忆主张|执行更新/集合关系|判断|
|---|---|---|---|
|第一轮找到两物；18 拿灯失败，随后异位置 put/use 也失败|某些对象不可拿；拿取失败时反转搬运方向|rule_2 / `update_000005` 与 rule_4 / `000007`，均来自同次拿灯失败|属性说明与补救流程互补，不是两份独立检验。rule_4 没保留空手、所在位置等其他失败前置条件；应定为过强诊断概括，不是已证明所有物体拿取错误|
|第二轮 23 拿闹钟、25 放下、26 用灯；26 尚未成功|只放在灯旁并用灯不足|rule_3 / `000006`、rule_5 / `000008` 共同记录失败区别|这个否定由观察支持，具有决策价值，不是需要保存所有细节|
|第三轮生成 take→use，但实际只执行 27 take 就 won/done=true|总结称“took … and then used the desklamp”而成功|总结 `114e76fe0f47476e83ff31e67093030d` → 技能 `000001`；执行 Builder `6d373bdc37c742dda2a80d5becf05b57` → rule_3/5|明确时序/来源错误：将未执行 use 计入成功经历；“已有开灯状态”区别丢失。不是说拿→用这个充分策略本身无效|
|官方搜索规则返回两项；执行 helper 返回三项|保留基础 helper；技能携带三返回值版本|rule_1 未改，技能/规则同时有同名变体|有意保留旧知识合理；接口选择负担仍在，但没有已观测冲突错误|

第三轮 Worker call `7524536048f94e8685b6afb563232023` 的计划不是执行记录。
**最终 Builder 实际请求 messages[9] 已收到**：

> `obs_27: Act: agent.take_from('alarmclock_1', 'desk_1') ... This epoch is done. Succeed: True`

其后没有 use 观察。故这不是“updater 没收到终态”；它同时收到生成代码、真实反馈和错误总结，
仍把代码/总结当成执行事实。第一次 Builder 分类 call `ba4b01f8c7954dd5a18601a8f8f9c61d`
也误述时序，但该回复附的写规则代码未执行，不能计两套规则写入。

集合层面：rule_2/4 是属性—纠错，rule_3/5 是成功流程—纠错，技能是程序实例；
这种拆分可以互补，**不要求改成一条**。问题是共同来源与确定程度没有随拆分得到区分。
Builder 称四条 “do not overlap”，比实际关系更强。validation 的同源拼接重复由
`autobuild_utils.py` 的 `update_rule` 累加导致；不能声称模型真的把重复计成多票。
Worker 的 `rule_string` 不显示 validation，Builder 的 all_rules 显示，两者影响渠道不同。

后续 C/task_01 真正拿→用成功，look 技能从 success=0 整理稿变为 success=1 实际程序；
C/task_02–04 的成功支持充分流程，却不回头检验原 epoch_0 的时序。旧规则的错误 provenance
与后来有效知识可以并存。无需再补两个灯任务来重复证明这件事。

## 3. A 案例二：Book 的来源混淆及反向证据

原件：[P/M1 模型事件](../artifacts/book-procedure-opportunity-v1/task_01/model_calls.jsonl)、
[M1 后态](../artifacts/book-procedure-opportunity-v1/task_01/memory_after.json)、
[I1 模型事件](../artifacts/book-procedure-opportunity-v1/task_00/model_calls.jsonl)。

|实际证据|记忆主张|真正更新|判断|
|---|---|---|---|
|M1 初始列表没有 desk_1；Worker 自写 desk_1 搜索，step 1 Nothing happens|“desk_1 was listed”；初始列出的容器也可能不可达|Builder `8bbfacde626f4809a89d00b0f41de604`；`000005` 改 rule_0，`000008` 新 rule_6|明确来源事实错误，扩散到两条规则。不是发现列表不可靠，也不是两次独立验证|
|M1 仍实际拿书→用灯成功；helper 真返回三项|rule_3 成功验证、rule_1 可选三返回值|`000006/000007`；其余规则保留|这一部分可合理压缩，不能因同次 Builder 有错误就全部判错|
|I1 实际 sidetable→dresser→bed→sidetable→bed→take→sidetable→use|分别搜索造成冗余，建议单次记录多物体|Builder `aa53c2f08ffa4b38a0892b7bc06a3a99`；`000007` 新 rule_6|建议明确标 `planning-efficiency rule, not a correctness rule`、`needing further verification`；不是虚构已执行优化，是反向证据|
|六分支原生 look.add_skill 都 no-op|规则能变化，旧技能不替换|已有 success=1；官方 add_skill 门槛|不同通道更新不同步是事实；不能仅据固定门槛宣布长期锁定|

M1 Builder 请求 messages[6] 是当前列表、messages[7] 是实际执行；两者均已收到。
错误原文：`some receptacles listed in the initial observation may not be valid targets for go_to`。
旧技能初始观察/其他规则示例有 desk_1，是可能替代来源；**没有证据定位哪段造成混淆**。
错误影响的是对当前可用行动列表的信任，具有潜在决策意义；本轮没有其后续有害影响证据。

I1 建议与旧技能双搜索形成效率张力，不是逻辑冲突：旧法能成功，新法可能更省。
它的访问次数表述仍有精度问题（sidetable 实际三次，不是两次）。
I1/M1 不是“同一证据、只变 updater 输入”的对照；不能用二者差别归因单个上游因素。
旧六分支结果及暂停建议不变，不为这些 A 判断再执行 Book。

## 4. A 案例三：逐任务维护，而不是跨快照归因

原件：[N](../artifacts/automanual-incremental-19a209c33a5e/)，各 task 的 model_calls、updates、完整快照。
表中只列实质记忆字段变化；epoch/history/check_rule/save 等控制写入仍完整保存在区间中。
全序列未删除旧规则或技能。task_01 后 9 条规则，task_02 后 4 类型技能，之后数量不变。

|任务/epoch；实际证据|实际记忆变化（update_id）|Builder call_id|集合判断|
|---|---|---|---|
|00/5 Book→Sofa，公开表面放置成功|`000001` plain-put success=1；`000005` 新 rule_7|c39216e2eebb4e0dba93b2a7672d8528|简单 search→take→put 压缩合理；只验证开放目标，未证明所有容器无需开门|
|01/6 Apple clean→Fridge：8 closed，9 put 失败，10 open，11 put 成功|`000001` clean success=0；`000005` rule_7 加 put-open 与条件 clean；`000006` 新 rule_8|ac3cdc0989734e739e46c4c78fa1891b|正常纠错；流程与局部前置条件同源互补。保留简单放置，不把 clean 强加全部任务|
|02/7 Bread cool→CounterTop：5 open、6 cool、8 put 成功|`000001` cool success=1；`000005` rule_7 正文/示例扩成 clean/cool/heat，加入 transform must-open|f02faf09c8a34144a525efd64222a919|结构类比合理部分与未经验证的必要条件混在同条规则；不是 task_04 的改动|
|03/8 Candle→Toilet：开放目标，5 步成功，没有 clean/cool|`000005` rule_7 validation；`000006` rule_1 validation；技能全不变|54ec5c262b534e77a4cb147cc18077c8|保留简单任务分支；明确 rule_8 未触发，不伪造关闭目标验证|
|04/9 Apple clean→Microwave：10 closed、11 open、12 put 成功；3 访问未列出的 diningtable 失败|`000001` clean 0→1（替换代码）；`000005` rule_6 正文/验证；`000006/7` rule_7/8 仅验证|71d74c5d18224232a590ef4cca85523e|跨关闭容器的成功复用；rule_8 仍保留 cabinet/drawer 待验证；准确区分没列出的 diningtable，与 Book M1 错归因相反|
|05/10 Bread cool→CounterTop：6 open、7 cool、9 put 成功|`000005` rule_7 仅 validation；四技能均不变|25d8ace73d92497ea5e9b31504cd31fd|第二次冷却足以支持流程可用，仍不验证开门必要性；不能把 task_02→08 的所有变化归给此任务|
|06/11 Laptop→Desk：6 步成功，未调用变换|`000005/6` rule_1/7 仅 validation|71da514816fe4778892010a907e7722f|再次保留简单放置；见两个 laptop 选一成功是当前任务证据，不证明任意数量任务只需一个|
|07/12 Cup clean→Shelf：15 开 cabinet 见杯、19 clean、21 put；备选 shelf 未执行|`000005` rule_1 example 加具不同名字的三返回值版本；`000006` rule_7 validation；clean 技能不变|7662984473dd4efaa8b6361ac25181c4|旧两项接口保留，新增变体合理；开放 shelf 不触发目标开门；不能把未走 fallback 当新经验|
|08/13 Cup cool→Microwave：搜索时已经开 fridge；13 closed microwave、14 open、15 put|`000005–8` rule_1/7/8/6 仅 validation；所有正文和技能保持|dfec87b7feec4de383b7660be9fc7bf6|继续确认 put-open；没有新增“关闭 fridge 直接 cool”的证据，不能指控 updater 忽视了它没收到的反证|

本轮逐一比较确认：**rule_7 正文/example 最后一次变化是 task_02；rule_8 正文/example 在 task_01
形成后一直不变。** task_04、08 的验证扩展不等于正文再扩展。rule_7 的滚动 validation 到 task_08
主要保留 epoch_11–13，早期失败因果细节仍在 rule_8 example 和全局历史中；
这是不同层次的取舍，而非全部证据被删除。旧 plain-put 技能没更新开门，并不等于整体仍不会开门：
后续规则提供该条件，Worker 也实际按不同目标条件适配。

### 最重要的新增 A 区分：put 和 transform 的条件不同

N/task_01 第二个 Worker `1a0be18b4a4b439eb51b86c94c57f7a5` 把新补救说成旧 rule_7 已含
`If Y is closed, open it first`；实际旧正文不含。Builder 分类 `b86b819863814af6a4c0e65c41b72a29`
却指出旧规则缺口，最终正确补入。**它没有机械接受 Worker 的错误来源归因。**
成功总结 `ac103a7a506349a6b24d260701b4d283` 整理的 clean 代码未从初态重跑，
但确为已经成功执行片段的组合，原生 success=0 保留这个区别。

到了 task_02，Builder 请求已含实际先 open 再 cool 的反馈，响应写：

> `The transformation receptacle may be closed and must be opened first.`

并说 `rule_8 ... is validated again ... for cooling not putting; still consistent`。
最后实际只更新 rule_7，**没有把这次误称验证写入 rule_8**。task_05 有类似解释，仍只改 rule_7 验证。
这不是已经比较两种条件的结果，而是把“做过而且成功”提升为“必须做”。

官方实际 game 的 `HeatObject/CoolObject` 要求持物、位置和器具类型，但没有 opened 前置条件；
`PutObject/PickupObject` 则有 `(or (not (openable ?r)) (opened ?r))`。
不能只读同名参考文件认定一致：本轮检查了所选 `game.tw-pddl` 内实际嵌入的 domain。
它与 downloaded/logic 文本并非字节相等，但上述动作条件在实际 game 中确实如此。
本轮环境诊断也验证了 heat 区分，见 §6。

因此应把 rule_7 拆开判断：clean/cool 流程共同结构是合理压缩；“变换器具必须开门”过强，
“microwave/stoveburner for heat_with”也超出了所读 API 示例（microwave）及实际 domain（仅 MicrowaveType）。
本轮未单独执行 stoveburner 失败诊断，不以其虚构后续轨迹；干预也不删该词以免扩大问题。
task_01 的 put 条件正确，task_04/08 保留它正确；**不能把整个 rule_7 或所有开门知识称为错误**。

实际检索的完整技能（由请求中 skill_code 精确匹配）：N/00 look；01 plain-put；02 clean；
03 plain-put；04 clean；05 cool；06 plain-put；07 clean；08 cool。
所以首次冷却确实复用的是 clean 示例，而后两次可复用已自然形成的 cool 示例。
cool success=1 程序保留 task_02 的 open-before-cool；clean 仅 task_04 从 0→1 替换。
这不是九次独立的策略学习，也不是所有新经验都会更新所有表示。

**A 是否需要两条补充任务？不需要。** 现有 task_04/08 已覆盖同条件关闭目标复用，
task_03/06/07 覆盖开放目标、简单/复合任务切换。新的 heat 分支同时提供尚缺的“操作类型改变后，
是否区分不同前置条件”的更新证据，不额外占两个名额。若没有分支获得相关反证，
不能称 updater 忽略反证；届时分别记录未取得与取得后处理失败。

## 5. B：10 个新增配置的有界选样

仅扫描本地 54 个路径名称以确定可用类型；详细读 **10 个**配置，不下载、不读专家执行计划选路线。
固定顺序：clean 尚未运行的前三个、heat 字典序前三个、two 字典序前四个。
读取字段为 pddl_params、任务文本、game 的目标/初始条件与动作语义；这些是**研究侧**资料，
不进入 actor/updater。人工 annotation 与真实 grammar 任务文本可能不同，不拿 annotation 当实际请求。
十个 game 均为官方预生成 solvable=true；这不是实跑成功证明。

所有 ID 均相对 `third_party/automanual/alfworld/downloaded/json_2.1.1/train/`：

|编号/完整任务 ID|核实的条件差异|纳入/排除理由|
|---|---|---|
|1 `pick_clean_then_place_in_recep-DishSponge-None-Cabinet-414/trial_T20190909_061502_436342`|关闭 cabinet 目标；海绵在 toilet；目标要求 clean+in|可检验已注明待验证的 cabinet 泛化，但旧 put-open 策略仍合适，没有相反前置条件；A 已有充足同类更新证据，不另付费|
|2 `pick_clean_then_place_in_recep-DishSponge-None-Cart-430/trial_T20190906_233458_108018`|开放 cart；海绵分布 drawer/shelf/toilet|与现有 clean→shelf 同类开放目标；条件式 open 已允许不打开，无明确受压制的替代策略|
|3 `pick_clean_then_place_in_recep-DishSponge-None-Toilet-427/trial_T20190908_234203_467365`|部分海绵已在目标 toilet，但没有 isClean；另在 bathtubbasin|仍必须拿→clean→返回目标；“已在目标”不等于目标满足，未找到可省掉变换的公开证据|
|4 `pick_heat_then_place_in_recep-Apple-None-Fridge-20/trial_T20190910_105931_762443`|microwave 从过去的 put 目标变为 heat 器具；关闭 fridge 为最终 put 目标|**唯一保留/推荐**。同任务可以区分 heat 不需 open 与 put 需 open；已有自然 K；诊断实证见下|
|5 `pick_heat_then_place_in_recep-Apple-None-GarbageCan-12/trial_T20190908_172429_549227`|开放 garbagecan 目标；没有现成 hot apple|同一 heat-precondition 候选的另一实例，无需再保留第二候选/再诊断；字典序优先 #4|
|6 `pick_heat_then_place_in_recep-Egg-None-GarbageCan-2/trial_T20190909_101128_479012`|部分 egg 初始 cool，但目标 hot；其余在 countertop|不能把换 egg 当独立机制；温度变化需主动 heat，不存在已热跳过的证据；不纳入|
|7 `pick_two_obj_and_place-CD-None-SideTable-321/trial_T20190912_055724_501328`|两枚不同 CD 必须在同一个 sidetable；两枚在 diningtable，另一枚在 armchair；目标无现成 CD|确有数量区别，但不能同时携两物；旧单物 search helper 可逐次使用，尚无自然“第二件无需再找/任意一个就够”的记忆承诺；目前更像任务适配测试|
|8 `pick_two_obj_and_place-CellPhone-None-Bed-314/trial_T20190909_013435_646326`|三个 phone 同在 dresser；需两枚到 bed，初始 bed 无 phone|可记住两个已见 ID，但不能靠同时拿两枚省往返；没有证据确认旧 K 限制第二 ID 记录，不先花来源名额诱导它|
|9 `pick_two_obj_and_place-CellPhone-None-Dresser-229/trial_T20190911_131442_170447`|两个 phone 在 coffeetable，另一枚在 sidetable；目标无 phone|同样有多目标适配空间，但未经观察的搜索排序优劣不能从隐藏位置直接塞进方案；比 #4 缺少已确认承诺—反证关系|
|10 `pick_two_obj_and_place-CreditCard-None-ArmChair-227/trial_T20190907_075635_674582`|两个 card 同在 coffeetable，另一枚在 drawer；目标无 card|没有“目标已有一件但旧策略搬两件”的预期边界；不据任务名宣称存在该机会。保留为未成熟方向，不推荐付费|

two 类型不是被判定永远不适合 B；仅当前四个配置与现有 K 不如 #4 明确。
不用 source 采样制造“只搬一个”的错误记忆；也不植入错误、换题或改环境。

## 6. 唯一候选的机制与可发现性

**来源**：N/task_01 的关闭 fridge 放置确实需补 open；N/task_04/08 的关闭 microwave 放置
按同规则成功，是旧条件的自然复用参照。N/task_02 将其扩展为变换前必须开门，
N/task_05/08 保留/复用冷却流程；checkpoint 为 **N/task_08/memory_after.json**。
K 不需要另形成，且绝不来自 P 的分支后态或本轮诊断。

**新条件**：仍有关闭 microwave，但目标要求是 `heat X with microwave`，不是 `put X in microwave`。
最终 `put X in fridge` 仍需开 fridge。故区别是**同类器具在不同原生动作中的角色/前置条件**，
不是换 apple 名字或提高难度。旧先开门法在新任务也能成功，但多一步且得不到“关门也可 heat”的反证。

**E***：公开观察明确 microwave closed，未在其后 open，就有实际 `You heat ... using microwave`。
这是对 must-open 主张的反证；后续相同 hot+in-fridge 目标成功，支持省掉该步骤的改进价值。
仅省动作、未成功加热或未完成任务，不满足此解释。

**如何从当时公开信息合理发现？** Worker API 将 heat 定义成一个完整操作，给出
`heat_with('tomato_1', 'microwave_1')` 示例，没有声明先 open；已拿到 apple 且到达列出的 microwave
时，直接调用该 API 是合理的可测试选择。`closed` 对 put 有意义，未必对不同 API 同样有意义。
Agent 不知道 domain，也不应得到“正确做法是直接 heat”的提示；该省略究竟会自主出现，留给分支。
现实生活常识可能反而支持先开门，是未移除的替代来源。一次调用生成整段 Python，
E* 发生在代码执行中，不假装每个动作都有一次新决策调用。

### 无模型诊断的实际证据

[report.json](../artifacts/automanual-transform-opportunity-v1/report.json)，3 个独立环境、seed 42：
open→heat 路径及其一次重复均 8 步，所有初始/逐步 observation、reward、won、done 相等；
第三次只移除 `open microwave_1`，7 步且 won=true，没有失败动作。

1. `go to countertop_1`：公开见 apple_4；2. `take apple_4` 成功；
3. `go to microwave_1`：`microwave_1 is closed.`；
4. 对照 open 得到 `In microwave_1, you see nothing.`，随后 heat；
   替代路径直接得到 `You heat apple_4 using microwave_1.`；
随后两条路径均 go fridge（closed）→open→put，最后 won=true。

搜索规则在执行前固定：仅从初始公开列表取 countertop 优先、diningtable 次之、其余字典序，
拿第一个**公开看见**的 apple；不按 PDDL 位置跳到答案，不读 expert plan。
第三条路径由第一条公开轨迹仅删一个步骤生成。这是研究者诊断，不是 Agent 自发探索。
保留 game/initial_state/traj SHA，官方环境和 `AutoManualAdapter.reset_task` 与分支同路径；
只证明这个任务/路径，不证明全部隐藏状态确定性。没有改上游数据。

**可能的信息替代来源**：rule_8/公共 helper/静态 put 示例仍讲开容器；clean 技能包含
去 microwave 放置前开门；模型先验也可能泛化。保留它们，因为其正确作用是搜索/放置，
不是直接表达 transform 必要条件。否则将删除任务相关正确知识，改变目标问题。
本轮不声称所有 opening 相关知识被移除，也不把阴性解释为全部 memory 无作用。

## 7. 干预：一次固定的承诺呈现组，不是改正确答案

`actor_transform_opening_mask`，任务开始到本任务所有 Worker 调用，固定三处关联呈现：

|成员|为何关联|准确移除/保留|
|---|---|---|
|rule_7 正文末句|唯一直接说变换器具必须先 open 的学习主张|只删 `The transformation receptacle may be closed and must be opened first.`；保留 heat/clean/cool API、器具例子、持物、put 条件|
|rule_7 的 cool 示例|同一次 task_02 更新将承诺程序化|只删 cool 前的 if-closed/open/assert 三行；后面目标放置前相同结构保留|
|已检索 cool 技能的 Step 3|同条真实 task_02 程序携带同一承诺|若官方检索选到该技能，删变换前开门三行及标题中 `open it if closed`；全部 helper、搜索/拿取/冷却/放置、原任务/初始观察保留；若未检索到，不强制换技能|

这是一个记忆组的 **Worker 注入视图**，不是全局删知识、物理删 rule_7 或编辑技能存储。
不改 rule ID、整个 checkpoint、Builder、历史、技能索引/向量、其他规则、公共 helper、静态 prompt；
不另加策略提示，但这是**必要条件及关联程序呈现的编辑**：删除开门代码后，示例呈现
go_to→cool_with。无法区分撤除旧约束与编辑后范例的引导作用，不能称为无引导的独立探索。
目标中“加热前开门”和“放置前开门”要分别判读，不能都算被干预行为。
没有中途强制暂停、额外模型调用、上下文重建。此前生成代码/重规划上下文若再表述该承诺，
不会被清除；这是起始呈现干预留下的内生影响，不声称 complete amnesia。

选择这种窄集合而非清空全部 K 的理由：已有具体必要条件错误，能只移除其直接语义和程序例子，
保留完成任务所需的正确流程。因果结论最多针对**这组三处呈现**，不能归因于单句/单规则。
技能是否被检索、提示长度、保留的搜索/put 先验、旧模板替代和远程随机性仍须分析。

实际已保存请求的离线验证：
[automanual-transform-offline-v1.json](../artifacts/automanual-transform-offline-v1.json)，
源 N/task_08 Worker call `fbc8dddca5464b22ba23ffc4e6720f2d`；其 rule_7 与 cool 程序
和当前 checkpoint 相同。保存完整 intact/masked 请求、精确 diff、source SHA，源 checkpoint 不变。
**这不是新的 heat 请求/响应**，不冒充已验证 heat query 的 DashScope 排序。
真实 heat embedding 未调用；native top-1 可能是四技能中任一种。执行时按真实返回保存并过滤
实际出现的 cool 程序，不能为了符合预期强制选择它。回归覆盖 cool 出现/未出现。
该离线 artifact 的 plan 是初次捕获版本；后续仅补充价格/身份说明及代码排版，当前可执行清单以 configs 为准。

## 8. 唯一待审批批次：六次，完整官方更新

机器清单：[transform_branches.json](../configs/automanual_alfworld/transform_branches.json)。

- checkpoint：N/task_08/memory_after.json；文件 SHA256
  `7de38c3fcd0714584351a36b6ca2e0500e572ebd938b79892b31127b9e99f2c7`；snapshot SHA256
  `8599df8c9987f817026a629ed932d876110c5e1b71ee19afd36e8a94ee04ccb6`。
- 目标：上表 #4；seed=42，native epoch=14。
- 顺序 I1→M1→M2→I2→I3→M3；各次独立恢复同一 checkpoint、新环境/guest；
  不继承分支更新，完整原生成功/失败总结、Builder、必要 merge。不会删诊断动作来强迫模型走 7 步。
- synthetic=false、scientific_evidence=false，用途筛选；反馈仍 `automanual-native-won-v1-2026-09-11`。
- 请求 deepseek-v4-flash，返回限定 deepseek-flash，non-thinking/temp 0；
  北京 DashScope text-embedding-v4/1024/float；零自动网络重试。

### 预定判据：A、H1、B、闭环分别回答

主指标 E* 是否出现及次数。辅助记录：首次 heat 前公开器具状态、是否已因搜索而开门、
opening 的实际目的、成功 heat/put、won、总动作/失败动作、请求/token/费用。
没有走到加热决策或此前搜索已经打开 microwave，机会为 **未暴露**，不能填作“拒绝直接 heat”；
设施中止的缺失指标 null，保留观察前缀，不计正常任务失败。
每组全部三次均进入整体结果表，同时单列机会暴露及未暴露原因，不剔除未暴露样本后比较。
搜索路径也可能受记忆影响；未发生 E* 不等于拒绝探索。
B 取证判断不以 Builder 正确吸收或最终任务成功为必要条件：后续其他失败不能抹去有效反证。
B 策略改进另看相同成功约束下的实际成本；A 看收到证据后的更新；A+B 看二者的可解释联系。

|结果|结论边界|
|---|---|
|masked 更常取得 closed→heat 成功|可支持 B 取证差异线索；不要求 Builder 正确吸收，最终其他失败不抹去反证；单次事件不足以证明稳定因果效应|
|同等成功要求下减少非必要操作和实际成本|另行判断 B 改进，核对搜索/试错成本；不能只看省去一条代码|
|仅动作不同，或成本降低来自更幸运搜索|最多 H1/不确定；热了但最终失败可有取证价值，不据此称整体策略更优|
|两组都直接 heat，或两组同样先 open|前者反对该承诺抑制当前机会；后者不支持干预预测，可能有保留渠道/先验替代，不扩大 mask 追阳性|
|masked 反而更差，或 intact 自己发现并限定旧规则|保留反向结果；不能因方向不符排除|
|已经取得 E*，Builder 却称必须 open，或仅添成功记录|A 收到反证仍处理错误；需逐字核对输入与真更新。若差异路径维持不同承诺才有 H3 线索|
|未取得 E*，仍保留旧必要条件|不能判定 updater 忽略未收到的证据；结合组间取证差异才讨论 A→B→A|

逐分支读 Builder 请求/代码/完成区间：rule_7 正文、example、validation 分别是否限定；
rule_8 正确 put 条件是否保留；新 heat 技能实际写了什么。heat 在该 checkpoint 尚无技能，
因此本次 add_skill **可以新写**（成功/失败按原门槛），不能预设像 Book 那样必然 no-op。
旧 cool success=1 仍可能保持，规则与新 heat 技能若区分操作条件，是正常集合维护，不必全同步改写。
没有各分支后续复用，不宣称长期自强化或 H4。

### 预算和现行公开来源

2026-09-12 经 direct.py + urllib ProxyHandler({})、正常 TLS 直连读取：
[DeepSeek 官方价格](https://api-docs.deepseek.com/quick_start/pricing/)，Flash 峰值每百万
input-hit/miss/output 为 USD 0.006/0.30/1.20；
[DashScope 同步 embedding 官方表](https://help.aliyun.com/zh/model-studio/text-embedding-synchronous-api)，
**北京 text-embedding-v4** 为 CNY 0.0005/千输入，单行 8192，最多 10 行。不用免费额度。

重要身份边界：当前 DeepSeek 页面明确说旧 deepseek-v4-flash 请求由 **DeepSeek-V4.1-Flash** 服务，
按 Flash 计价。仍保持项目指定 request ID，不静默换模型；实际 response ID 必须逐次保存。
**同一个 deepseek-flash 返回名不能证明与历史采样是相同权重版本**。
本轮仅文档核实，未重新做模型兼容调用；新批六分支内部保持同配置，不拿历史成功率做跨版本因果对照。
review 应知晓这个限制，执行前再次确认价格/身份说明，无适用价格或身份不符即停止。

|项目|预定上限/估算|
|---|---|
|启动|6；不换题、不补跑；来源 0、A 附加 0|
|transport|12/task、72/run，生成+embedding 合计|
|USD 硬上限|6/task、6/run|
|CNY 硬上限|0.05/task、0.20/run；不与 USD 相加或换汇|
|相似任务实测推算|N/task_08 ×6：24 请求、输入 80130（含 embedding）、输出 17970；USD 0.038988432 / CNY 0.000111；不是账单或保证|
|每次生成保守预留|输入 1,048,576 + native max_tokens=2000：USD 0.3169728；实际可信 usage 后释放未花预留|
|embedding 预留|每文本 8192 tokens / CNY 0.004096；四文档请求预留 0.016384，query 0.004096；原机制执行，无免费额度|

六次满上下文并非能靠小估算无限发请求；后续任一请求不能在余额内预留即停止。
参考 N/task_02/05/08 均 2 generation+2 embedding，USD 0.004686/0.004324/0.006498，
输出 2583/2019/2995；新类型可能重规划、总结和 merge，故保持 12 的请求限而非固定 4 次。
provider 未报告费用仍 null，本地估算单列。费用/usage 未知、模型身份变化、设施故障、预算中止、
原生更新不完整、checkpoint/注入匹配失败时整批停止；正常完成更新的任务失败继续固定顺序。

默认不付费计划入口（已在 memory-automanual 执行，exit 0）：

```bash
python scripts/direct.py conda run -n memory-automanual python scripts/run/automanual_transform_branches.py
```

**仅待这份具体清单获得新授权后执行；本轮没有执行：**

```bash
python scripts/direct.py conda run -n memory-automanual python scripts/run/automanual_transform_branches.py --execute --output artifacts/transform-precondition-screen-v1
```

输出目录已存在即拒绝；复用既有 restore/guest/ledger/完整更新流程，不新增 checkpoint 框架。
新 runner 仅临时绑定已有呈现干预 callback；在 manifest 追加本轮入口 SHA。
模型请求中没有诊断轨迹/研究表/PDDL/专家信息。执行后人工读六份原始材料按上述预定判据报告，
不以通用旧 Book 指标替代本批语义指标。

## 9. 验证、改动和剩余边界

本轮新增本报告、固定 config、特定呈现入口、一个无模型诊断入口、3 个小回归；
共享 adapter 仅多记录这一入口的 patch SHA。未改上游代码、prompt、memory 算法、数据、schema、
依赖、凭证或旧 artifacts。现有未提交改动全部保留。

实际命令均经 scripts/direct.py；环境诊断额外禁止网络连接与 `.env` 读取：

```bash
python scripts/direct.py conda run -n memory-automanual python scripts/smoke/automanual_transform_opportunity.py --execute
python scripts/direct.py conda run -n memory-infra python scripts/run/automanual_transform_branches.py --offline
python scripts/direct.py conda run -n memory-infra env PYTHONPATH=src python -m unittest discover -s tests -p test_transform_screen.py -v
```

诊断 exit 0（8/8/7 步均成功）；保存请求双视图 exit 0；新增 3 tests / 0.004s 全通过。
回归确认：目标集合片段移除、put 开门和 helper 保留、源 checkpoint 不变、未检索 cool 时不强塞技能、
Builder 不变、下一 intact 不继承 mask、默认计划不启动 worker。使用合成小 fixture，不加载密钥或联网。
没有跑全套测试、安装、API probe、旧 reset 或上游 patch 重放。
相关 Ruff/format/compileall 与 diff 检查收尾见下；初次 Ruff 四个长字符串行已拆行修复。

最终相关验证：新增 3 项 + 复用呈现生命周期既有 5 项，**8 项通过**；
4 个相关 Python 文件 Ruff / format --check 通过，memory-automanual Python 3.9 编译通过。
未运行其余无关测试。默认计划及 git diff --check 通过。
命令补充（前三个脚本及新 test 为本轮检查范围）：

```bash
python scripts/direct.py conda run -n memory-infra env PYTHONPATH=src python -m unittest discover -s tests -p test_procedure_screen.py -v
python scripts/direct.py conda run -n memory-infra ruff check scripts/run/automanual_transform_branches.py scripts/smoke/automanual_transform_opportunity.py scripts/smoke/automanual_adapter.py tests/test_transform_screen.py
python scripts/direct.py conda run -n memory-infra ruff format --check scripts/run/automanual_transform_branches.py scripts/smoke/automanual_transform_opportunity.py scripts/smoke/automanual_adapter.py tests/test_transform_screen.py
python scripts/direct.py conda run -n memory-automanual python -m compileall -q scripts/run/automanual_transform_branches.py scripts/smoke/automanual_transform_opportunity.py scripts/smoke/automanual_adapter.py
python scripts/direct.py git diff --check
python scripts/direct.py git status --short
```

最终 status 保留原有 tracked 修改 AGENTS、README、docs/01、docs/02，及原有未跟踪
configs/scripts/src/tests 等实现和 docs/03–17。本轮新增 docs/18、transform config/两个入口/测试，
更新 README 索引和 adapter 的入口 SHA 记录；`.env`、artifacts、third_party 仍忽略。
无 commit，无安装/升级，无全局代理配置改动。

**剩余边界**：热任务尚无真实 Worker 输入/输出；热 query 排序未验证；有限呈现删除不消除全部先验；
诊断只覆盖该可见路径；三次重复不证明统计效应；远程模型别名不保证历史权重相同。
这不妨碍 A 的直接语义证据成立，但 B/H3 仍要等授权后的自然模型经历与原生更新。

**明确推荐：仅做上述一个六分支筛选；不补 A 灯/清洗任务、不继续旧候选、不额外采样或启动 H4。**
若没有相关证据差异，就保留 A 的前置条件过概括事实，结束该候选，而不是继续增加工程和重复次数。
