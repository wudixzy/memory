# B 的实验载体重评：条件变化、探索机会与实施成本

具体 AppWorld 任务数据已经在后续研究中核对，见 [docs/21](21_appworld_ab_execution_plan.md)。
下一步按该文的集中接入计划执行，不再重复本文件的 benchmark 广泛比较。

2026-09-12。资料与源码研究；未安装环境、未运行新任务、未调用模型。

**建议：暂停在当前 ALFWorld 候选上继续付费搜索；下一优先核验 AppWorld 的具体任务组与 ACE 官方在线实现。
WorkArena++ 提供更明确的策略适用条件变化，但平台准入及 memory baseline 接线成本更高，作为备选。
不是因为任何一个 benchmark 保证出现 B。**

## 1. 当前结果究竟排除了什么

docs/13、16、19 检验的是三个限定的呈现干预，没有证明完整学习记忆对策略无作用。
其中最近六分支虽实际输入不同，动作/观察仍完全相同；全部检索的是保留的 clean 技能。
我们尚未区分学习记忆其他渠道、固定示例和模型先验各自的贡献。

当前样本的弱点：

- Book 的机会主要是少往返，加热的机会主要是少开一次门；旧流程都可成功。
- 加热案例确认了错误条件的推广，但不是一个特别强的“来源条件下最合适、目标条件下策略明显失效”的迁移实例。
- 发现一条更短的人工诊断路径，不等于证明 actor 面临清晰的探索选择，或有足够理由自行尝试它。
- 去掉部分呈现后的阴性不能推出 DS 太强；两组都走次优流程也与稳定先验、模板替代相容。

须纠正此前过于简单的解释：AutoManual **并非完全没有效率要求**。
当前 pinned [Worker prompt](https://github.com/minghchen/automanual/blob/aeb17e4a4fe8bb43b9eb390b7b0b94a3ca8b9324/automanual_alfworld/prompts/worker_prompt.txt)
要求在步数限制内优化代码、遵循规则范例，没有更好修改时复制代码；Builder 侧强调减少代码尝试/错误。
这些不等于以最少环境动作作为原生成功判据，也不能据此要求 agent 每次都主动证明其路径最短。

本地 [run_trail](../third_party/automanual/automanual_alfworld/autobuild_trail.py) 每轮先生成整段代码再执行，
在代码结束/异常且任务未结束时再获得下一轮模型决策。程序仍能按观察做条件分支，不能说它不适应观察；
但环境动作之间通常没有重新调用模型。这使“某一步去掉 K 后重新考虑”不一定能原样实施。

因此问题是 **benchmark × baseline × 目标与干预** 的匹配，而非已证明 ALFWorld 整体无效。
A 的已有语义证据保留；B 不再默认靠增加同类样本解决。

## 2. 下一样本需要满足的条件

选样先问五个问题，不做复杂评分系统：

1. 来源任务中的策略 P 为何合理，相关 K 能否由 baseline 自然形成？
2. 目标任务改变了什么条件，使 P 的适用范围或收益发生变化？
3. 哪个公开观察/文档/API 响应能区分 P 与 Q，agent 如何有机会取得它？
4. 代价是否具有任务意义：漏项、违反约束、错选方案、显著冗余，而不只是研究者偏好？
5. 记忆干预能否改变相关决策渠道，且能与基础工具能力、固定示例影响区分？

纠错与改进分开选样。改进实验优先使用任务本来就要求比较/优化的情形，避免额外奖励塑形。
原生任务中的最优性要求若以二元成功评测，也仍可研究次优选择；任务失败本身不构成 B。
程序在已得到全部数据后算错，更接近推理错误；还须证明记忆影响了数据取得、候选考虑或策略选择。

## 3. 候选比较

|载体|已确认的结构|对 B 的价值（研究判断）|成本/限制|建议|
|---|---|---|---|---|
|当前 AutoManual + ALFWorld|原生规则/技能、低成本 reset、已完成接入|适合 A 和局部机制检查；当前 B 样本区分力有限|固定程序先验、有限决策轮、成功流程冗余不一定受到反馈惩罚|保存证据，暂停旧候选|
|ACE + AppWorld|同场景变体、数据干扰、分段执行、官方在线 playbook|最值得先找状态/数据条件变化，兼顾 A 的集合维护与 B|未完成本地安装/真实任务核验；官方实现比论文概括更窄|下一优先做具体任务组核验|
|WorkArena++|原生单项/组合预算分配等任务模式、显式目标比较、逐步 UI|本轮找到最明确的策略适用条件变化之一|平台权限、浏览器、尚未核实原生持续 memory baseline 配对|强备选，不立即安装|
|AWM + WebArena|购物比较任务、官方 workflow 接入、可观察 UI 行动|可研究先入策略是否跳过单位价格/约束比较|老入口已弃用警告、网站部署/reset 成本、页面噪声|保留，不同时接入|

表中不是性能排名，也没有用历史模型成功率推断当前 DS 表现。

## 4. AppWorld：优先候选，但还不是已选好的实验

作者的[论文 §3 与附录 H](https://arxiv.org/html/2407.18901v1#S3)明确包含同场景的状态变体和干扰信息。
两个值得优先核验的原生场景如下；这是论文确认的场景，不是本轮已取得的具体任务/checkpoint：

- **支付资金来源变化**：Venmo 余额与卡余额配置变化，可能需要不同资金操作。适合核验旧支付流程是否跳过余额/卡状态检查。
- **优惠码比较**：请求明确要求最好折扣，邮件包含不同折扣和过期码。适合核验已成功使用的渠道/流程是否限制其他候选的检查和比较。

任务状态变化确实存在；但是否自然产生 P、是否有可区分的来源—目标组合，必须读取具体数据确认。
不能直接把“第一张卡”“第一个可用码”写成来源记忆来制造问题。
优惠码涉及 Amazon/Gmail；官方[任务浏览器](https://appworld.dev/appworld/task-explorer)指出这些应用位于 test-challenge，
不能假定该场景在 train/dev 可直接找到。若选择测试场景做机制发现，明确 exploratory 用途，
不再把这些样本当作未见的泛化测试。

[官方环境](https://github.com/StonyBrookNLP/appworld)提供应用模拟及状态评估，支持多种完成方式；
它不保证基于过去经验的锁定自然发生，也不是开箱即用的长期记忆 benchmark。
长期记忆来自 ACE 在不同任务之间保留的 playbook。任务世界与 memory 的重置/继承必须分别记录。

### ACE 官方实现的源码核验

读取 `ace-agent/ace-appworld` commit `928e86877d34cd10eaba159606386f93a1765090`，
未安装或执行该仓库。以下是当前版本静态结论，不代表全面隔离审计：

1. [ACE_online_no_GT.jsonnet](https://github.com/ace-agent/ace-appworld/blob/928e86877d34cd10eaba159606386f93a1765090/experiments/configs/ACE_online_no_GT.jsonnet)
   使用 adaptation 路径和 no-GT reflector 模板。
2. [adaptation_agent.py](https://github.com/ace-agent/ace-appworld/blob/928e86877d34cd10eaba159606386f93a1765090/experiments/code/ace/adaptation_agent.py)
   的无 GT 路径交替生成/执行代码。任务完成后调用 evaluator，再调用 curator；
   **仅见 evaluate_task 不能判定信息泄漏**，还需检查模板和真实消息。
3. [adaptation_react.py](https://github.com/ace-agent/ace-appworld/blob/928e86877d34cd10eaba159606386f93a1765090/experiments/code/ace/adaptation_react.py)
   将 required_apis 放入渲染参数，但当前 generator 模板没有使用该变量。
   no-GT reflector 模板将 GT/test report 写为不适用，没有对应替换占位符；
   curator 模板也未使用传入的 gt。所查路径**尚未发现这些值实际进入提示**；
   不据变量名误报，也不能据此宣称所有隐藏状态访问均已隔离。
4. 同文件 curator 只接受 **ADD**；更新库输出不保留 helpful/harmful 计数。
   可通过追加限定来修正集合，但不能称为已经支持直接修改、删除、计数驱动维护。
   测 A 应考察追加的限定/冲突及其使用，不为匹配论文印象重写官方算法。
5. 原生初始 playbook 和静态例子已经强调读 API 文档、分页和验证。
   “漏查分页”未必是好候选；干预学习条目也不能消除静态示例中的相同指导。
6. 默认配置启用**响应结果缓存**和较多网络重试；不是 DeepSeek 的前缀 token 缓存。
   后续因果重复必须关闭跨分支响应复用、按项目要求限制重试，并把 reflector/curator 纳入共享计费。
   所查 solve 路径的显式 cost_tracker.add 主要针对 generator，不能直接沿用为全角色硬预算。
7. 单纯达到 max_steps 而未触发完成/费用条件时，所查循环没有统一的末尾 curator 调用。
   失败任务是否更新有原生边界，必须记录；不能擅自补 updater 改机制。

此外，模板仍有“反思依据 ground truth”的泛化措辞，不能当成真实 GT 输入；
也要关注它是否让无 GT 的 updater 对不确定结论表述过强，这本身是 A 的潜在研究点。
以上边界可在一次小接入中核验，不需要先做完整通用 harness。

## 5. WorkArena++：更清晰的原生策略切换

已读[官方任务类](https://github.com/ServiceNow/WorkArena/blob/a772230a94cf1caf4166b8ead3983f3b3786455b/src/browsergym/workarena/tasks/compositional/maximize_investment_return.py)
和[实例生成器](https://github.com/ServiceNow/WorkArena/blob/a772230a94cf1caf4166b8ead3983f3b3786455b/src/browsergym/workarena/tasks/compositional/utils/knapsack.py)。
它们原本就定义了 `single_item`、`random`、`trivial`、`n_items` 等模式。

具体可考察：

- `FilterSingleItemExpensesAndSelectInvestmentsSmallTask`：项目成本均大于总预算一半，最多选一个；挑最高收益单项合理。
- `FilterRandomExpensesAndSelectInvestmentsSmallTask`：多个项目可组合，需要比较组合收益；不能照搬只选一个。

两类 Small 任务均使用预算 150000、项目数量参数范围 `[3, 5]`，不是研究者改代码制造的新规则。
目标都要求在预算内选投资，变化在可通过界面读到的成本/收益条件。
**这是静态源码确认的候选关系，尚未生成实际 seed 实例、运行浏览器或形成任何学习记忆。**

适合 B 的假设是：来源经历自然形成单项选择捷径后，目标中是否忽视组合的可行性/比较，
记忆干预是否恢复相关候选考虑。即使目标选错，也须区分算错、读漏、UI 操作失败和 memory 影响。
若所有成本/收益已被完整读取，仍选错，不能直接宣布“反证获取被抑制”；可能是策略比较部分的问题。

实施限制：当前[官方 README](https://github.com/ServiceNow/WorkArena/blob/a772230a94cf1caf4166b8ead3983f3b3786455b/README.md)
要求申请 gated ServiceNow 实例资源并通过 Hugging Face 认证。
不是仅提供 DeepSeek/DashScope key 就可运行。我们还没有核实一个现成、机制合适的原生持续记忆实现与该任务配对。
**不应为了试这组任务，先花很多轮搭浏览器平台或把 ACE 自行改造成新 baseline。**

## 6. WebArena / AWM：已有具体 ID，但不优先

读取[官方任务配置](https://github.com/web-arena-x/webarena/blob/dce04686a56253aefba7b18a4fa0937cf1dc987b/config_files/test.raw.json)：

- task 431–435，同一 template 145：从已打开商品标签中选择单位价格最低者加入购物车。
- task 506，template 172：在指定预算范围内选最高评分商品。

这比“任务名看起来复杂”更具体。包装数量、总价与单位价可能构成决策区别；
但本轮没有部署页面，未确认某一对商品的总价与单位价排序确实相反，不能声称已找到完整来源—目标案例。

[AWM 的官方流程](https://github.com/zorazrw/agent-workflow-memory/blob/8c0ff8cd11d648c8fceb99e4e42f37e3b75381b1/webarena/README.md)
包含运行、模型评估、workflow 归纳；[run.py](https://github.com/zorazrw/agent-workflow-memory/blob/8c0ff8cd11d648c8fceb99e4e42f37e3b75381b1/webarena/run.py)
仍明确提示弃用。服务部署和依赖兼容尚未验证。换到浏览器会引入定位/页面噪声，
更难并不自动带来更好的 B 因果样本；本阶段不与 AppWorld 同时接入。

## 7. 建议下一步，只推进一个交付

**优先做 AppWorld 的任务数据核验 + ACE 最小接入可行性检查，合在一个 coding-agent 交付中。**

- 先查上述两个场景的实际任务 ID、变体和公开证据路径，允许使用官方数据获取方式，
  不依据模型阳性结果选样；研究侧数据/评测与 actor/updater 输入分开。
- 每组必须写清 P 在来源为何合理、目标条件如何改变、哪个动作/观察能区分。
  若只发现换名字、普通难题或没有学习记忆的潜在作用，停止该组。
- 只有至少一组值得执行，才在独立 Python 3.11 conda 环境做官方最小安装与无模型接入检查。
  不先铺满 AppWorld 通用遥测、自动评分或所有干预方式；复用现有 artifact/费用边界。
- 固定官方 fork 与数据版本，先检查 no-GT 实际消息、响应缓存、全角色预算、任务 reset 和原生更新边界。
  产出一个小批次的任务/来源/干预/费用方案；不把旧实验额度沿用到新环境。
- 如果 AppWorld 没有合适条件差异，或接入需要重大机制改写，报告具体失败原因，再决定 WorkArena++ 的访问投入。

不再把 ALFWorld 的整体 K 消融作为转向前的必经关卡。
它可作为另行提出的、用于区分完整学习记忆与先验的诊断，但不能自动证明 B，也不在本轮启动。
不改变 backbone 来主动制造失败；新环境同时产生的 A/正常更新证据继续保留。

## 8. 研究记录与边界

本轮核对的远端 HEAD commit（研究定位，不是已安装环境）：

|仓库|commit|
|---|---|
|ace-agent/ace-appworld|928e86877d34cd10eaba159606386f93a1765090|
|StonyBrookNLP/appworld|42b5bcf3cd334fee33f0c37c02070a9f5807add5|
|ServiceNow/WorkArena|a772230a94cf1caf4166b8ead3983f3b3786455b|
|zorazrw/agent-workflow-memory|8c0ff8cd11d648c8fceb99e4e42f37e3b75381b1|
|web-arena-x/webarena|dce04686a56253aefba7b18a4fa0937cf1dc987b|

联网阅读了官方论文、仓库和任务配置；选取的公开源码临时缓存于 `/tmp/memory-b-source-research-20260912`，
不是新安装的 baseline。命令行下载通过 scripts/direct.py + ProxyHandler({})，TLS 保持开启；
raw 下载部分超时后使用 GitHub 官方 API 读取公开 blob，未启用代理。
只新增研究文档和索引，不改实现或既有实验状态，不重跑测试、不读取项目真实 .env、不创建 commit。
模型请求 0，模型 API 费用 0。

结论是基于源码和任务结构的优先级判断，尚没有新的 B 阳性证据。
