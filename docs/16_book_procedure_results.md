# Book 流程呈现六分支：结果与 A/B 分析

2026-09-12。批次 `book-procedure-opportunity-v1` 已完成；真实运行
`synthetic=false, scientific_evidence=false`。本报告是三次/组的筛选判断，
不是显著性、等价性或 H2/H3/H4 确认。**建议保留为有限证据，不继续确认此候选。**

## 固定条件与核验

产物根目录 `artifacts/book-procedure-opportunity-v1/`，汇总 `branches.json`；
逐任务目录依次为 task_00=I1、task_01=M1、task_02=M2、task_03=I2、
task_04=I3、task_05=M3。指标定位文件为
`artifacts/book-procedure-opportunity-v1-analysis.json`，以下判断同时人工阅读
`model_calls.jsonl` 的请求/响应、`actions.jsonl`、`observations.jsonl`、
`updates.jsonl` 和完整 memory 前后状态，不以自动指标代替语义分析。

任务为 `look_at_obj_in_light-Book-None-DeskLamp-317/trial_T20190909_201143_217673`，
seed 42、native epoch 2。来源是校准 C/task_01 的 `memory_after.json`：

- 文件 SHA256：`e4ec1a9e226372fc1e729c337a8232360e850dda212f2bc5af6c3d1da91ba60e`。
- snapshot SHA256：`85e5dd4a3875b38a09b563248b6f7bb6df8f95a99d0ffeef9c4a227665d5000c`。
- 六份 memory_before 与来源 JSON 完全相等；执行后来源文件哈希不变。
- 六份实际 Worker 请求经结构比较：三个 intact 完全相等，三个 masked
  都恰好等于对 intact 应用登记的 `reduce_examples`；配置和其他消息相同。
  删除仅为 rule_3 example 与检索技能的顶层 procedure，保留 helper 定义、
  规则正文、技能旧任务/初始观察、其他规则及静态提示。
- 完整持久 memory 没有预先删除；每次独立恢复、新环境和 guest。Builder
  未经过此过滤；其消息 5 是完整规则集合，消息 6/7 是本次任务与执行轨迹。
  后续更新不传给下一分支。精确呈现 diff 在各目录 `intervention_diff.json`。
- 每任务均完整执行原生更新；没有中止、重规划、网络重试或补跑。

## 行为结果：早拿不是改善的充分条件

动作位置从 1 开始；“首次拿取”指首次看到书的这次位置访问结束前成功拿取，
不是必须紧接下一条动作。失败/无效动作同时列出原始 `Nothing happens`，
区分非法目标与已经在原地的 no-op，不把它们叫基础设施失败。

|分支|首次见书→成功拿取→用灯|首次访问拿取|总动作|失败/无效动作|已知灯处空手返回次数|won/终态|
|---|---|---|---:|---|---:|---|
|I1|3→6→8，book_1|否|8|0|1|true/completed|
|M1|9→11→13，book_2|是，但中间原地 go_to|13|2：非法 desk_1；原地 drawer_3|0|true/completed|
|M2|3→7→9，book_1|否|9|0|1|true/completed|
|I2|6→10→12，book_2|否|12|0|0|true/completed|
|I3|3→6→8，book_1|否|8|0|1|true/completed|
|M3|3→6→8，book_1|否|8|0|1|true/completed|

intact 完整 3、中止 0；masked 完整 3、中止 0；正常任务失败各 0。
主指标 I=0/3、M=1/3；总动作 I=28、M=30（均值 9.33/10）。
两组已知灯处空手返回都合计 2 次。I2 的 0 不代表没有折返：它是在发现书后
**首次**寻找灯，然后回去拿书，不满足“返回已知灯处”这个更窄指标。
不能事后换指标把这算成 positive。

### 逐分支代码与原始观察

- **I1**：`34e53ebb3fae489b8743b4289b01f357`，完整沿用“搜书→搜灯→回书处拿→用灯”。
  sidetable→dresser→bed，step 3 `On bed_1, you see book_1...`；
  step 4 回 sidetable，step 5 回 bed，两个位置内容与此前相同；step 6
  `You take book_1 from bed_1.`，8 `You turn on desklamp_1.` 且 won=true。
  这是真实重复跨位置行走，没有新证据，不是未执行的代码。
- **M1**：`0edcaa2e6030462db5b6ed8ae970d509`，仍“找齐两物→拿→用”，但先搜灯。
  desk_1 不存在，step 1 `Nothing happens.`；dresser→sidetable 后逐个开
  drawer_1/2/3，step 9 `In drawer_3, you see book_2, and creditcard_2.`；
  step 10 原地 go_to 的 raw observation 是 `Nothing happens.`，11 拿书成功。
  因已先找到灯，第一次见书后不需要再离开找灯，主指标成立；这不是证据支持的
  “发现 book_1 时立即拿、消除已知冗余”改进。它拿的是另一合法实例 book_2，
  同一任务成功约束满足，但搜索路径更贵。三个开抽屉确实增加了新观察；没有
  证据表明这些观察帮助改善本任务成本或纠正旧承诺。
- **M2**：`c7b23ececf9c49dc9b1f5043e326535b`，先 dresser→sidetable→bed，
  见书后再次 dresser→sidetable，再回 bed 拿书：与 I1 相同的延迟拿取，
  多了一次 dresser 复查。代码有复杂 non-portable fallback，但没有执行，
  不把它计作试验或新证据。
- **I2**：`d2107a92bf48492cb1af2c27c9a02eb4`，先开三个抽屉找到 book_2，
  再 dresser→sidetable 找灯，回 drawer_3 拿，再回灯。仍完整原流程；
  12 步主要来自搜索顺序/开抽屉，不能全部归因于流程示例。
- **I3**：`d53dc8f9b80a4f6b808fdb0c58cb55f1`，与 I1 的 8 条实际动作、
  原始观察和成功结果相同，仍延迟拿取。
- **M3**：`3900dd346bd944f4aad1fddf0252f6c7`，与 I1/I3 同样 8 步。
  代码包含 take 失败后的备用策略，但 book_1 实际拿取成功，备用分支没有执行。

因此本批**没有观察到 masked 获得更低成功动作成本**。它有一次顺序变化，
但并未采取此前诊断验证的六步机会。删除的是两个示例整体，包含位置列表、
assert 和代码组织，不是单个顺序词的纯效应；搜索先验、其余规则/helper、
保留的技能任务描述以及远程模型变动都是解释边界。温度 0 下 intact 自身
也在 bed/book_1 与 drawer/book_2 路径之间变化。

## A：本次真正写入了什么

以下 update_id 均在对应 task 的 `updates.jsonl`，规则 ID 仅在该分支解释。
每次 `update_000001 skill_bank.add_skill` 的前后 skill_bank 相等：已有
`look_at_obj_in_light.success=1`，官方写入门槛不替换它。六次最后的 skill_bank
也与来源相等。没有额外成功总结调用；本次每任务只有 Worker/Builder 两次生成，
不能编造一个独立 reflector 总结。

|分支/Builder call_id|实际证据→执行更新|A 判断|
|---|---|---|
|I1 / aa53c2f08ffa4b38a0892b7bc06a3a99|000005 更新 rule_3 验证；000006 更新 rule_1 正文/验证（三返回值变体）；000007 新 rule_6 单次搜索同时记录两物|有价值地识别重复行走，并把优化标成待验证，不是所有成功都阻止改进提取|
|M1 / 8bbfacde626f4809a89d00b0f41de604|000005 错扩 rule_0；000006 改 rule_1 正文/示例/验证；000007 rule_3 验证；000008 写 rule_6“列表中的 receptacle 可能不可达”|直接可核查的错误归因，且重复进入两条记忆；没有提取一个经成本证明的改善|
|M2 / d37393c62e904a7a841877c54d990f42|000005 仅 rule_3 验证|正确记录 holding/use 成功，未测试 portability 的 fallback 不等于经验；没有吸收效率机会|
|I2 / 7cdf5820222c4577af71aa814fd2e022|000005 仅 rule_3 验证|压缩了有效过程，但“efficiently searched”只是解释，12 步本身没有优越性证据|
|I3 / 8d017cd436354fdd828840414521aab7|000005 rule_3 验证；000006 rule_1 示例/验证（三返回值注释）|合理小变体记录；与 I1 同动作却没有提取优化建议，体现更新选择不稳定|
|M3 / b4502539f1114f54b74f862edf8cb368|000005 仅 rule_3 验证|成功过程记录有效；解释先称 confirms rule_2/4，后又承认未直接测试；没有把 portability 新验证写入这两条规则|

**I1 的支持与限制。** 新 rule_6 明写 `planning-efficiency rule, not a correctness rule`
及 `needing further verification`。它从实际重复观察提出单次多目标扫描，属于
合理但未执行的优化假设，而不是成功优化的既成事实。其验证称 sidetable 与 bed
各访问两次不精确：实际 sidetable 三次、bed 两次。不能把建议中的伪代码算作
Agent 已探索了替代方案。这个 intact 反例尤其不支持“保留示例就无法发现改进”。

**M1 的直接 A 问题。** Builder 输入消息 6 的真实初始观察列有 dresser_1、
sidetable_1，但没有 desk_1；消息 7 清楚记录自己生成的 `go_to('desk_1')` 失败。
然而实际 rule_0/6 都写 `some receptacles listed in the initial observation may not
be valid targets for go_to`；rule_0 验证进一步写 `desk_1 was listed`。
这是把模型自行加入的搜索目标误归因给环境列表，丢失“当前任务列表”和
“旧示例/先验”的关键区别。旧技能的保留初始观察、其他规则示例确实有 desk_1，
是可能的混淆来源，但无法仅凭这一条证明具体来源。该错误进入两个规则，
不代表有两份独立证据；可能让未来忽略环境列表可靠性，但尚未运行其后续影响。

**集合一致性。** 六次 rule_3 正文和 example 都不变，只有 validation_record
增加此次成功；旧验证被返回的累计文字与 native append 再次重复，不能视为
独立验证次数。rule_1 的三返回值是实际执行过的 helper 变体，不能因变体就称
虚构成功。I1 新规则建议单次多对象扫描，技能仍保留分别搜索的旧流程，形成
效率建议与执行范例间的张力，但不是逻辑上无法同时成立；它明确允许旧方法成功。
M1 技能不吸收新搜索顺序由 success=1 门槛解释，rule_3 验证却写入新顺序。
固定门槛和这种不一致是研究对象，不单独证明长期闭环失败。

## 分开的结论与建议

1. **A 提取/更新**：存在直接错误（M1 环境列表归因）及验证精度问题；也有
   正常压缩、有效变体记录和主动提出待验证优化（I1）。不能全称记忆更新失效。
2. **行为变化**：M1 出现先灯后书和首次访问拿取；其余 masked 仍沿用双搜索。
   三次重复只能描述，不能把一次变动精确归因为删除某句词，也不能证明无效等价。
3. **B 改进机会**：已知存在的更短成功路径本轮未被采用；masked 没有更低成本，
   主指标的一次阳性由搜索顺序/书实例选择解释，缺少“呈现限制采用改善”的支持。
   新抽屉观察是真证据，但不是纠错或降低成本所需证据；不自动升级 H2。
4. **A+B**：成功经历继续进入规则验证、技能保留旧范例，是事实；尚无证据链
   证明其导致不能纠错/改善并经后续经验强化。I1 主动建议改进是反向线索。
   M1 错误记忆尚无后续复用，本轮不启动纵向恢复/H4。

**推荐保留为有限证据，暂停这个候选，不追加确认或扩大 mask。** 保留 A 的
具体 provenance 错误作为后续研究素材；不把一次成功但较贵的顺序变化包装为
改进受限。下一步如另获授权，应围绕能区分经验来源与更新可靠性的明确问题
设计，而不是继续用此 Book 主指标追求正结果。

## 调用、价格与执行记录

2026-09-12 执行前通过 direct.py + `urllib.request.ProxyHandler({})` 直连核对：
[DeepSeek 官方价格](https://api-docs.deepseek.com/quick_start/pricing/) 的 Flash
峰时上界仍为每百万 cache hit/miss/output USD 0.006/0.30/1.20；
[DashScope 官方 embedding 表](https://help.aliyun.com/zh/model-studio/text-embedding-synchronous-api)
北京 v4 仍为 CNY 0.0005/千输入 tokens。未用免费额度。原价格表版本仍保留
2026-09-11 标签，本报告记录本日适用性复核，未改旧 artifacts。

|分支|输入 tokens（含 embedding 12）|输出|缓存命中|生成/embedding 请求|估算 USD|估算 CNY|
|---|---:|---:|---:|---|---:|---:|
|I1|9005|2765|5632|2/2|0.004360092|0.000006|
|M1|8451|2538|5120|2/2|0.004072020|0.000006|
|M2|8940|2634|5888|2/2|0.004108128|0.000006|
|I2|9281|2016|6272|2/2|0.003355932|0.000006|
|I3|8867|2063|6400|2/2|0.003250500|0.000006|
|M3|8507|2008|5888|2/2|0.003227028|0.000006|
|总计|53051|14024|35200|12/12|0.022373700|0.000036|

generation 输入 52979，embedding 输入 72。所有 usage 可信、retry_count=0，
请求/返回分别为 deepseek-v4-flash/deepseek-flash 与 text-embedding-v4/
text-embedding-v4；既定 non-thinking、temperature 0、北京 1024 float。
provider 未报告金额，保持 null/unavailable；表中是本地上界价格估算，不是账单。
上限 task/run=12/72 requests、USD 6/6、CNY .05/.20；未触发。

实际命令（全部通过无代理入口）：

```bash
python scripts/direct.py conda run -n memory-infra env PYTHONPATH=src python -m unittest discover -s tests -q
python scripts/direct.py conda run -n memory-infra ruff check scripts/run/automanual_procedure_branches.py tests/test_procedure_screen.py scripts/analysis/automanual_evidence.py
python scripts/direct.py conda run -n memory-automanual python scripts/run/automanual_procedure_branches.py --execute --output artifacts/book-procedure-opportunity-v1
python scripts/direct.py conda run -n memory-infra python scripts/analysis/automanual_evidence.py --source artifacts/book-procedure-opportunity-v1 --output artifacts/book-procedure-opportunity-v1-analysis.json
```

164 tests / 2.686s 通过、Ruff 通过、唯一真实批次 exit 0、提取六任务完成。
首次测试命令遗漏 PYTHONPATH 导致 import error，修正后通过，未安装依赖；
一次只读比较把 dict 误传给需要 `.raw` 的函数，修正后六份比较通过，未触发模型。
本轮无执行逻辑改动，仅新增本报告和索引；无安装、.env 改动、commit、额外 probe、
重置诊断或付费补跑。原始标签及所有阴性/反向结果保留。

另运行上述三个相关文件的 `ruff format --check`（3 files already formatted）
及 `python scripts/direct.py git diff --check`，均通过。最终 `git status --short`
保留原有 4 个 tracked 修改（AGENTS、README、协议、预算）和既有 untracked
实现/文档；本轮新增 `docs/16_book_procedure_results.md`、更新 README 索引。
artifacts 仍被忽略，没有凭证或上游目录进入新增 tracked 变更；未创建 commit。
