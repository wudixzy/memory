# ACE + AppWorld：真实五任务与 A/B 语义结果

2026-09-13。执行本轮一次授权，固定 seed=123、官方 commit
`928e86877d34cd10eaba159606386f93a1765090`、原 patches、隔离、提示词和 ADD-only 更新均未改变。
**五任务全部完成原生更新并 evaluator success=true；B 登记为 `stop_conditional_knowledge`，六分支未启动。**
这不是 intact/masked 阴性实验，也不证明 B 普遍不存在。优惠样本是已经研究过的 test-challenge，
仅用于探索性机制研究；全部真实 manifest.synthetic=false、scientific_evidence=false，不报告未见测试成绩。

## 1. 执行、费用与终态

产物根目录：[ace-appworld-ab-v1](../artifacts/ace-appworld-ab-v1/)。
运行前目录不存在；默认 plan 与本轮登记完全一致。没有重跑、补跑、独立 probe、embedding 或分析模型。

|顺序 / task|终态 / evaluator|G/R/C 请求|执行块 / 公开 API / 失败 API|input / cached input / output tokens|保守估算 USD|
|---|---|---|---|---|---|
|00 / 60d0b5b_1|completed / true|9/1/1|9 / 14 / 0|117,454 / 77,312 / 13,388|0.028572072|
|01 / 37a8675_1|completed / true|21/1/1|21 / 21 / 5|281,348 / 232,832 / 68,136|0.097714992|
|02 / 60d0b5b_2|completed / true|10/1/1|10 / 17 / 0|133,570 / 92,416 / 21,590|0.038808696|
|03 / 432dc7a_2|completed / true|19/1/1|19 / 18 / 1|328,496 / 263,424 / 26,561|0.052975344|
|04 / 432dc7a_3|completed / true|25/1/1|25 / 24 / 0|436,445 / 365,568 / 60,336|0.095859708|

合计 **94 次真实 transport**（84 Generator、5 Reflector、5 Curator），input **1,297,313**，
其中 cached **1,031,552**、cache miss **265,761**；output **190,011**。
估算 **USD 0.313930812**，run 剩余 **USD 5.686069188**；embedding 0、CNY 0、自动重试 0。
provider 金额全部 **null**，不能将本地估算当作账单。公开 API 计数包含 API 文档和模拟登录，
不包含可信控制端管理请求/evaluator；它们不是收费模型 transport。

2026-09-13 经 direct.py＋urllib `ProxyHandler({})`、TLS 校验访问
[官方价格页](https://api-docs.deepseek.com/quick_start/pricing/)，峰值每百万 hit/miss/output
仍为 USD **0.006 / 0.30 / 1.20**；继续用该保守价表，未根据非高峰折扣扩大额度。
旧请求名仍被接受并由 **DeepSeek-V4.1-Flash** 服务，与 docs/23 的身份说明一致；
全部真实返回 `deepseek-flash`，请求仍为 `deepseek-v4-flash`、non-thinking、temperature=0。
返回别名一致不证明与历史 ALFWorld 请求使用相同权重。

执行命令（均退出 0）：

```bash
python scripts/direct.py conda run -n memory-ace-appworld python scripts/run/ace_appworld_ab.py
python scripts/direct.py conda run -n memory-ace-appworld python scripts/run/ace_appworld_ab.py --execute --output artifacts/ace-appworld-ab-v1
python scripts/direct.py conda run -n memory-ace-appworld python scripts/run/ace_appworld_ab.py --execute --output artifacts/ace-appworld-ab-v1 --continue-branches artifacts/ace-appworld-ab-v1/source_review.json
```

最后一条只登记停止，前后 ledger 均 94 次、USD 0.313930812。没有预算/身份/设施中止。
任务内 422 后继续属于官方纠错，不是网络重试或任务补跑。
预算保持 task USD 3/run USD 6、42/462 请求、8192 output/call、完整 input 预留 1,048,576，
每次预留 USD 0.3244032。余额不足预留即停止的机制没有放宽。

## 2. Memory 的真实集合演化

每任务均有 `updates.jsonl:update_000001` 的完整 begin/end；本文所有新增条目均以 **memory_after** 为准。
完整 K（playbook＋next_global_id）从官方 initial 一次初始化，逐任务前后哈希严格相等，
每任务首个实际 Generator 请求包含该完整 K；不是只根据调度参数推断继承。

|任务后|Curator 提出 / 原生接纳 ADD|实际新增条目|完整 snapshot bytes|
|---|---|---|---|
|initial|—|8 条官方 initial|1,536|
|00|2 / 1|vc-00009：付款后的金额/双方/描述核验|1,724|
|01|2 / 1|cms-00010：卡有效期预筛；有效卡资金不足时尝试其他卡|2,036|
|02|2 / 1|vc-00011：退款前确认原请求及检查已有退款|2,338|
|03|2 / 2|shr-00012：优惠量化比较及不可用条件；cms-00013：日期来源|3,061|
|04|1 / 1|cms-00014：无日期 API 时系统时间作为后备|3,475|

第五任务后完整 K：`47a674397a045e5f07739ff8054c999118102ba2b95a7878e61d3441269ef886`。
逐任务哈希、大小、用量见 [calibration.json](../artifacts/ace-appworld-ab-v1/calibration.json)；
源文件哈希及语义判断见 [source_review.json](../artifacts/ace-appworld-ab-v1/source_review.json)。
学习集合只有上述六条，没有写入“旧优惠总是更好”、具体任务账户、优惠码或支付金额作为策略。

### A1：首条退款——有效压缩与实际遗漏

目录 `sources/00_60d0b5b_1/`，Generator 实际 step 从 0 开始。

|实际证据|记忆主张 / 更新结果|判断|
|---|---|---|
|step 4 分页取回 25 条 approved sent requests，打印收款人、金额及 approved_at；Robert 对应最新匹配项 6097、74。step 6 转账，step 7 show_transaction 核验 74、双方及无卡支付|vc-00009 保存转账后核验；没有保存个人身份、74 或具体请求 ID|合理压缩：保留可迁移的验证操作，丢弃个体值并非问题。身份/金额信息由下次任务及 API 重新取得|
|Reflector 注意到“last sent”的 created_at / approved_at 区别|Curator 提出偏向 created_at 的条目，但 **未持久化**|原生校验导致决策相关知识遗漏；不等于模型没有提出，也不能宣称后续用了这条时间知识|
|API doc 说明省略 payment_card_id 使用余额；本次余额支付成功|未新增“余额永远足够”或默认强制某张卡|没有提取错误的全局资金承诺；没有必要规定一条轨迹必须产生若干特定条目|

原文与定位：转账 call `62e2c1deaf334d8392e3093b0134ae77`，真实反馈 `Sent money.`；
核验 call `2340bc631bfe427ba2cc67c882b53e06`。Reflector
`2360228aa041426b86b480d790d2f7d8` 区分两种日期，但其“list is sorted by created_at”
并未由当轮打印的创建时间序列直接证明——原始 API 返回含 created_at，实际程序只打印 approved_at，
不能把研究侧能读原始字段等同 updater 已看过所有字段。两个时间在本次选中项上相符，不构成实际选错。
Curator `4bdec058b5a24dd48fd98799f71950b5` 与 `updater_output.json`/memory_after 对照显示：
时间条目使用 `problem-solving_heuristics_and_workflows`，原生只接受
`problem_solving_heuristics_and_workflows`。固定源码
`experiments/code/ace/adaptation_react.py:324–352` 对未列 section 直接跳过；本轮未修补它。
task 01 的跨 app 身份条目、task 02 再次提出的时间条目也在同一边界被跳过。
这是原生已完成的过滤/更新结果，不是调度设施未运行完更新。

原始响应还有虚构的 15/75 美元、多个代码块及自编 Output，例如
`0399f5a9043c45e4bf083a35a6520680`、`aaf313ab6561401195cdba782c240854`。
**它们不是真实转账或观察**。原生首代码块解析/截取后，后续上下文接受实际 74 元反馈；
updater history 也不是未经处理的完整生成响应。不能将被裁掉的虚构续写直接归为进入记忆的事实污染。

### A2：余额变化与回到旧条件——集合互补，不是强制覆盖

|实际证据|记忆主张 / 更新结果|判断|
|---|---|---|
|task 01 step 8 从 Phone 联系人匹配号码，再找 Venmo；step 11 余额不足，step 12 明确余额 0|提出 Phone→邮箱的条件化身份解析，但 section 名不符被跳过|语义上合理的跨源知识，实际集合缺失；尚无后续同类号码任务证明损失造成错误|
|step 14 过期卡失败；15–17 三张卡资金不足；18 最后一张卡成功付 91、private=true；19 核验|cms-00010 保留有效期检查和有效卡之间尝试；vc-00009 保留且执行|新旧知识互补，明确区分有效期与资金。不是把“没过期”当作“必定有钱”|
|task 02 step 6 查余额 48；step 7 不指定卡付 48；step 8 核验|保留 cms-00010，但不机械换卡；继续核验|条件适配的反向证据。没有 intact/masked 对照，不能将新增查余额行为单独归因于 K|
|task 02 已用 status=approved 取回请求，但未检索重复退款|vc-00011 新增原批准状态及防重复退款检查；日期条目再被跳过|防重复退款是合理风险先验，并非观测到本次已有退款。按同金额/描述检索仅是线索，不能视为充分证明；当前条目也没有明确说匹配即禁止付款|

task 01 的余额反馈 call `082fd5a7951a47a3b705664dfd625375`：
`Your Venmo balance does not have $91.00 to make this transaction.`
过期卡 call `cd048be2b2af4ca9b1d6b0214f6717ea`：`The payment card has expired.`
其生成响应后段虽说改用有效卡，真正执行的首块仍用了过期卡；不能将“后来生成了正确代码”当作已经避开失败。
Reflector `b7910825ec3940c999db052ff9c38062` 的概述称 “skipped the expired” 不准确，
但同一回复 error_identification 承认已尝试过期卡；最终 cms-00010 没将错误行动伪记为成功。
Curator：`48260d8e6c704c35949508c362f92263`。

task 02 Reflector `27256dfe5e514af5a6b67a2e0b8662e9` 又要求核验是否“由收款人批准”、
检查其他 pending 请求及已有退款。这些不是本次发现的异常；不能用未额外检查证明原任务处理错误。
Curator `bf5c93b1362d41c4b6b187bb5bf6be98` 的 vc-00011 是前置防重复检查，与 vc-00009 的后置核验互补，
但来源/确定程度没有被结构化保留。这里只指出依据与措辞强度的差别，不规定正确记忆条数。

### A3：优惠经历及日期更新——合理保留与过度归责同时存在

|实际证据|记忆主张 / 更新结果|判断|
|---|---|---|
|task 03 新码不满足门槛；actor 已说明旧码是 `the only one that works`，且重读购物车确认有效|Reflector 仍批评没有明确区分不可用与折扣比较；shr-00012 要求量化，并保留不可用条件|“没有明确说明”被实际 history 反驳。固定购物车下不可用已足以排除新码，不需改购物车来算假想折扣。条目仍支持比较，不等于偏向旧码|
|task 03 筛卡日期来自当天邮件；task 04 先查 supervisor profile，无日期后将任务的 today 与新邮件日期对应，按 2023-05 筛卡|cms-00013→cms-00014 从建议可靠来源扩展成 API 优先/系统时间后备及 Never 使用邮件日期|系统时间后备合理且本隔离环境已同步原生日期；但任务明确说邮件“today”是额外证据，不能与任意旧邮件混同。将其一概定为不可靠丢失了来源条件|
|task 04 公开试用新码，比较 498.9 对 459.9，恢复旧码并核验成交|shr-00012 原样保留，没有 ADD“旧码总是更好”|健康条件化复用的反向证据。没有物理删除旧条目符合原生 ADD-only，不判为更新失败|
|task 04 Reflector 提到“previous task”的 Simple Note 解析为空|来源是 history[67–69] 的官方静态示例，不是本批实际任务；Curator 明确不相关，没有写入新条目|来源归属含混是 A 风险；不夸大为已经污染持久记忆。实际 task 04 API 只有 amazon/api_docs/gmail/supervisor|

task 03 R `365b21dd9a49449b96d440a606400702`、C `7072a53505a943b58b4224987397641b`；
task 04 R `21ee5bd1828c4adaa63ebfffab93300e`、C `00c337a15dc04cbc82fc74a430cc87e6`。
日期依据的实际 task 指令原文含 **“today I received a new promotional email”**；
task 04 `updater_input.json` 的实际末段 history 明确说 profile 无日期，随后利用该 today 约束。
因此 updater **收到**该依据；不是因日志缺失才不知道。

cms-00010→13→14 是前提与取值方法的补充，同时 13/14 有重复；没有证据显示系统把它们计为独立验证次数。
不能仅因重复、强措辞或后段成功就宣布自强化。当前没有保存置信度/逐条可验证 provenance，
其缺失使审阅更依赖全轨迹；这不等于要求 baseline 记住每一细节或本轮开发新机制。

## 3. B：实际来源证据与停止理由

|来源|新证据的实际获取与处理|选择、模拟成交及成本|判断|
|---|---|---|---|
|432dc7a_2|step 8 读新邮件 AZ950；10 实际 apply→422，634 < 644；11 读取旧码 AZ25c 仍 valid、总价 588.4|16 工作地址下单 588.4；17 show_order 核验。18 API，1 次失败是检验不适用所得反馈|源任务条件下保留旧码合理。没有取得不可用新码的假想成交价，不等于没有取得决策证据|
|432dc7a_3|11 读新邮件 AZc5b；13 apply成功；14 读取新总价498.9；与6旧总价459.9比较；15恢复AZ2a6；16确认459.9|22 家庭地址下单459.9；23核验。24 API，0失败；旧码比新码少39|实际比较并正确采用更优可行方案，不是根据“上次旧码赢了”跳过尝试|

task 03 的直接取证 call：`1827fc555e414b7da97e047cb8db8517`（apply新码）；
`ad22815f1c34452685b106af4bf804c6`（读反馈后复查）；
`d25506e31a58410da56aaf376269617f`（明确不可用/旧码唯一可行）。

task 04 call `12c9881600a94af69402417bdf7f4fab` 实际说：

> Following the playbook [shr-00012], I need to quantify the discount each would provide.

随后 `c7d59e33b2dc4a2c9086f1a7e22c5591` 的代码实际 apply 新码，
`9e2310dd03dc4342ab3f4e32927cad0f` 实际 show_cart；
`88437d877f6847279be240fb0d6caf2d` 正确比较已取得的两种总价并实际恢复旧码。
这些可见解释仅辅助；API 与执行代码才确定发生过何事。

两条来源的关键邮件、422、两种总价、恢复与订单核验输出均逐项核对存在于 updater 的实际 history。
API 日志不是额外注入的模型信息；本次相关代码确实打印这些反馈，才构成模型/updater 可见证据。
保留官方终段边界：最后 complete_task 的返回未补入 updater，但前一块订单/转账核验已经进入，
不把“省略终段输出”泛化成 updater 没收到所有结果。

**最终判定：`stop_conditional_knowledge`。** 源 K 的唯一优惠条目在当前两候选语境下有明确条件且鼓励比较，
第五任务提供实际调用与结果支持。其“existing code is the only choice”在更一般情境仍隐含
旧码有效/仅两个方案等条件，但本登记目标没有证据表明这会阻止尝试有效新码。
不能凭强措辞、两次都选旧码、K 更长或想观察组间差异，硬凑限制性行为预测。
剩余额度充足也不是运行无合格假设分支的理由。

六个 I1/M1/M2/I2/I3/M3 均 **not_started**，无中止样本、无 intact/masked 结果；
目标 432dc7a_1 未运行。没有修改 K、换目标、扩大 mask 或额外来源。
判断及原文引用由 coding-agent 阅读后写入，非自动标签/LLM judge。

## 4. 分开回答 A、B、A+B 与接入条件

- **A**：获得独立的集合层证据。有效核验/卡条件知识互补保留并复用；原生格式边界丢弃三项合理建议；
  Reflector 对已有证据有局部误述/过度归责，日期来源区别在 Never 规则中被压平。
  静态示例归属问题被 Curator 挡住，没有该项持久污染。不能以五次成功证明 K 整体可靠。
- **B 证据获取/方案比较**：来源实际获得并比较关键证据，新增知识未满足限制性候选条件。
  这是本来源序列的反向证据，不是目标分支因果结论，不证明记忆没有任何行为影响。
- **B 改进**：来源采用各自更便宜的可行选项；API 搜索、取文档与尝试有成本，未运行相同任务干预，
  不能证明 K 缩短/拖长探索，或“停留次优”发生。模拟成交款与模型费用分别核算。
- **A+B**：可以定位 cms-00010→实际筛卡→日期批评→13/14 的更新联系，以及 shr-00012→实际比较，
  但没有证据受限的对照，更没有由此造成的有害维持/长期锁定；不宣称 H2/H3/H4。

Phase 0 的真实模型调用、官方任务、evaluator、完整 memory/update 与已登记依赖条件均已落实。
Phase 1 的五任务顺序记忆、成本及原始轨迹已完成，结合 docs/22–23 已审阅的局部 reset 与
Generator 学习集合干预接线，**已满足记录范围内的工程接入条件**；不升级为全状态确定性或 H1–H4 准入证明。

实际兼容性限制：17 次 Generator 响应达到 8192 output cap，且有重复/虚构后续 Output；
官方首代码块提取保留正常反馈循环，所有五次原生更新完成。没有为成功修补提示词/解析器、放宽隔离或重试。
原生 section whitelist 的连字符差异已记录为内容落盘限制。当前 no-GT 核对：实际请求不含各自 evaluator report，
关键 adaptive 信息来自公开轨迹；执行侧边界仍按 docs/23，不将字符串检查宣称为完整隔离证明。

## 5. 交付与最小下一步

**建议停止该优惠候选的付费分支，保留条件化复用的反向证据；优先审阅本批 A 的来源/条件分析。**
当前不推荐追加优惠任务、扩大移除集合、换模型确认或开展 H4。
若未来另有研究授权，必须提出能补足具体证据缺口的新问题；本轮剩余额度不自动转授权。

本轮没有修改运行代码、模型配置、上游、依赖、真实 .env 或旧 artifacts，没有创建 commit。
仅新增本报告、当前批次产物、语义判断及 calibration 汇总，更新 README 状态索引。
没有以增加测试替代样本：只做默认 plan、实际运行、来源哈希/继承/最终请求/关键 history 的只读核对及
`python scripts/direct.py git diff --check`。这些核对均通过；未重跑旧 smoke、reset、安装或全套测试。
最终 git status 保留既有 `M AGENTS.md / README.md / docs/01 / docs/02` 和未跟踪的工程/doc目录，
新增 docs/24；artifacts、third_party、.env 继续被忽略。
