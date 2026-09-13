# transform-precondition-screen-v1：六分支结果与 A/B 分析

2026-09-12。唯一授权批次已完成，停止继续执行。建议**停止该 B 候选的付费确认**，保留其 A 更新证据。不是 H2/H4 阳性，也不是记忆无作用的等价性证明。

## 1. 判据修订与实际执行边界

执行前已在 docs/18 §7–8 和 `configs/automanual_alfworld/transform_branches.json` 分开 B 取证、B 成功成本、A 更新与 A+B 反馈链；明确程序编辑的引导混杂；规定所有三次/组均保留，并单列机会暴露及中止缺失语义。任务、干预、主指标不变。

本干预是“必要条件及关联程序呈现的编辑”：删除 rule_7 的 must-open 句和冷却示例中的变换前开门代码，留下 go_to→cool_with。若原生检索 cool 技能，还编辑其对应呈现。本设计不能区分撤除约束与编辑后示例引导，不能声称无引导独立探索。本次实际均检索 clean，未触发 cool 技能呈现编辑。

原始证据根目录 [R](../artifacts/transform-precondition-screen-v1/branches.json)；下文 task_XX 均相对此目录。每任务 `model_calls.jsonl` 保存真实请求/响应，`trajectory.json` 保存原始环境逐步结果，`updates.jsonl` 保存完整更新边界，`memory_after.json` 保存最终原生集合。

- checkpoint：`artifacts/automanual-incremental-19a209c33a5e/task_08/memory_after.json`；执行后文件 SHA256 仍为 `7de38c3fcd0714584351a36b6ca2e0500e572ebd938b79892b31127b9e99f2c7`。
- 六份 memory_before 与来源完整快照相等，snapshot SHA256 均为 `8599df8c9987f817026a629ed932d876110c5e1b71ee19afd36e8a94ee04ccb6`。不是继承前一分支更新。
- 任务 `pick_heat_then_place_in_recep-Apple-None-Fridge-20/trial_T20190910_105931_762443`，seed 42，epoch 14；顺序 I1→M1→M2→I2→I3→M3。固定源码、数据 SHA、配置 SHA 见 branches.json。
- synthetic=false，scientific_evidence=false；沿用已审计反馈例外、官方 chat 和受限 Python、DashScope substitution。没有输入诊断路径、PDDL 或研究结论。

## 2. 全部六分支结果

“暴露”指实际持有苹果、观察到关闭微波炉、存在直接 heat 的动作机会；不表示此时另有一次模型决策调用。六次均由一次 Worker 代码执行完成，没有重规划。

| 分支/目录 | closed 机会暴露 | E* 次数 | won / 终态 | 动作数 | 无效/no-op | 生成/embedding 请求 | 输入/输出 tokens | USD 估算 | CNY 估算 |
|---|---|---:|---|---:|---:|---|---|---:|---:|
| I1/task_00 | 是，obs_4 | 0 | true/completed | 9 | 1 | 2/2 | 12747/2233 | .004837092 | .000018 |
| M1/task_01 | 是，obs_4 | 0 | true/completed | 9 | 1 | 2/2 | 12741/2343 | .004139388 | .000018 |
| M2/task_02 | 是，obs_4 | 0 | true/completed | 9 | 1 | 2/2 | 12696/2212 | .003479472 | .000018 |
| I2/task_03 | 是，obs_4 | 0 | true/completed | 9 | 1 | 2/2 | 12775/2302 | .003648804 | .000018 |
| I3/task_04 | 是，obs_4 | 0 | true/completed | 9 | 1 | 2/2 | 12838/2585 | .003969672 | .000018 |
| M3/task_05 | 是，obs_4 | 0 | true/completed | 9 | 1 | 2/2 | 12731/2549 | .003856740 | .000018 |

输入列包括每任务 36 embedding tokens。intact 和 masked 各完整 3、正常失败 0、中止 0、暴露 3、E* 0、won 3。无样本剔除、补零或补跑。三次重复仅筛选，不作显著性/等价性声明。

逐个核对六份原始轨迹，其 observation/reward/won/done 序列完全相同：

1. go countertop_1，看见 apple_4；
2. 再 go countertop_1，原始观察 `Nothing happens.`（同位置 no-op）；
3. `You take apple_4 from countertop_1.`；
4. go microwave_1：`microwave_1 is closed.`，仍持有 apple_4；
5. `You open microwave_1. In microwave_1, you see nothing.`；
6. `You heat apple_4 using microwave_1.`；
7. go fridge_1：`fridge_1 is closed.`；
8. 成功 open fridge_1；
9. `You put apple_4 in/on fridge_1.`，won/done=true。

微波炉第一次被近距离观察在变换阶段，不是搜索时提前打开；开门确实执行，不是未执行代码。所有搜索在第一个 countertop 便找到同一 apple_4，后续长搜索列表、其他热源设想均未执行。无搜索顺序/物体实例/试错成本的实际分组差异。第 2 步无效移动源于搜索后再 go 的代码模式，不能算为 mask 导致的变化；没有失败的 take/heat/put 或异常重规划。

此前诊断已证明此任务直接 closed→heat 的合法成功路径可行（docs/18 引用的 `automanual-transform-opportunity-v1`），本轮未重跑。这里的 9 步不能全部归给 must-open：至少另含一个重复 go no-op。诊断的短路径不是模型自发发现或本批因果对照。

## 3. 实际输入与逐样本语义证据

六次 `memory_injections.jsonl` 的 `skill_retrieval` 均返回 `pick_clean_then_place_in_recep`，query 为 heat 类型，FAISS 原生排序、normalize_L2=false。该技能“put a cleaned apple in microwave”的目的地开门代码全部保留，是可能发生动作角色混淆的替代来源；不能证明模型确实由此开门。rule_1 的搜索开门、rule_8 的 put-open、模型先验也保留。

直接比较最终 Worker request：三份 intact 完全相同，三份 masked 完全相同；跨组仅 messages[5] 不同，精确差异是 rule_7 must-open 句和 cool 示例的三行开门代码。其他消息、公共/学习 helper 定义、clean 技能、解码配置不变。Builder 的 messages[5] 完整规则输入六次相同，仍包含未经 mask 的 rule_7；并没有全局删除 memory。

以下 call ID 直接定位各目录 `model_calls.jsonl`；update ID 定位同目录 `updates.jsonl` 的 completed 区间。

| 样本 | Worker call / 实际行为 | Builder call / 真正写入与判断 |
|---|---|---|
| I1 | `28566079b77f4bbfbab6ce057c7e2a4c`；计划及执行均先开微波炉再 heat | `4dc7f175b87046bfa158573604104d2c`；update_000005 写 rule_1 validation，000006 写 rule_7 validation。准确记录 apple_4、opened→heat→put；可见解释把两种开门统称 rule_8 验证，但没有实际修改 rule_8。 |
| M1 | `f39bb4d822414e4d88d847f4c0c1f668`；rule_7 呈现已编辑，仍自行生成并执行条件 open | `ec327307b46e49ab8644b18033d1df6c`；000005 rule_7、000006 rule_8 validation。rule_8 明确写 fridge 的 obs_7/8/9，对 put 条件的复用合理；没有取得“不必开门也能 heat”的证据。 |
| M2 | `69190c7b90614d3c91291f0aff707725`；高层计划不强调开门，实际代码与动作仍 open→heat | `35ff8fa3b4e34e5791e3156c9e356491`；仅 000005 写 rule_7 validation。解释识别重复 go 为“harmless redundancy”，未据此改变代码/规则。不能把计划省略或效率建议算实际改进。 |
| I2 | `8da78b8ea0e74f09ab667a9c84b872fe`；同样打开后 heat | `7188635f50b24c75ba6c440a272f7241`；000005 rule_1、000006 rule_7 validation。解释泛称两处开门符合 rule_8，真正 rule_7 新记录明确 fridge 是 put 目标；rule_8 原件保留。 |
| I3 | `20648a0b9a5341bfb07d2ca91866c614`；提出其他热源 fallback，但未执行；仍相同九步 | `677cf67e6eae44f1b1f8f27f7a412bfc`；000005 rule_7、000006 rule_8、000007 rule_1 validation。实际 rule_8 更新限定 fridge put，合理；可见分析误称 epoch_9 已验证 heating（当时是 clean+put），但该说法未写入此次规则字段。 |
| M3 | `cdd3d0f5edfa40f8833901dc46f950c3`；文字明确 put 开门，代码还在 heat 前开门；相同九步 | `8c6c90a8da1e4e4792b3c0ca0e016bd7`；000005 rule_7、000006 rule_1、000007 rule_8 validation。后者真正写入“confirms the rule applies to transformation receptacles (heat source) as well as target receptacles.” 把成功伴随的 open 推成条件规则的扩展验证，证据不足。 |

六个 Builder request 的 messages[7] 都实际包含 obs_4 closed、obs_5 open、obs_6 heat，以及 fridge 的 obs_7–9 和 won-derived success。足以知道执行了什么，却没有 E*：不能评价为“收到反证后忽视反证”。此外官方 Agent wrapper 将同位置 go 的原始 Nothing happens 替换为缓存位置观察，Builder obs_2 看见的是 countertop 内容；I3 称无 Nothing happens 不能归为收到原始错误后故意忽略。M2 可从重复动作本身发现冗余。

## 4. 完整集合与 A 判断

六次均从 9 规则/4 技能开始，最终 9 规则/5 技能。逐字段比对：所有规则正文、example、type 均不变，rule_7 仅 validation_record 更新；正确的 destination put-open 条件与示例保留；旧四种技能逐字段不变。没有 merge 或规则重编号，因为本次 check_rule 未触发这些操作；不能虚构额外更新。

每次 update_000001 原生 add_skill 写入新 heat 类型，success=1，保存该 Worker 实际执行代码（含未走到的搜索备选列表，但并未声称遍历过）。000002 save，000003 epoch history，000004 save；之后为上表 Builder 操作、stop/report/check_rule/save，完整结束区间数依次 11/11/10/11/12/12。没有用最终快照猜测中间状态。

合理部分：新 heat 技能是在该类型此前缺失、真实成功后写入，记录了有效程序；rule_7 加入 microwave 可作 heat source 的实例，维护旧 clean/cool/put 历史，没有覆盖有效 put 条件。它与 cool 技能在操作类型上正确区分，但都使用先开门的成功程序，不足以验证该步骤必要性。旧 cool success=1 且不同类型，不因本任务改写正常；不是门槛阻止了本次 heat 写入。

A 的局部问题：M3 的 rule_8 validation 从 put 的条件规则扩展到 heat source，观察只证明 open→heat 成功，未比较 closed→heat。这是**收到执行证据后过度解读验证范围**，不是经验造假，也不是必要条件获得证明。正文仍只讲 put，因而 validation 与正文适用范围出现不一致。I1/I2 仅可见解释出现类似混用，不能当成相同持久化错误。I3 的历史类型误读也只限其可见分析。其余准确的轨迹记录和限定于 put 的更新是反向证据，不能把六次统称错误更新。

集合层面 rule_7 validation 与新 heat 技能来自同一成功轨迹，是不同表达层面的互补，不能当独立复验；本批没有测得模型给它们额外证据权重。保留 must-open 旧句本身也不等于本轮忽视反证，因为没有反证被取得。规则/技能重复一个有效但非最小程序，尚不足以证明长期固化。

## 5. 分开的结论与建议

- **B 取证**：两组都暴露机会、都未取得 E*；本任务未观察到登记呈现组的边际作用。不存在未暴露样本的选择偏差，但仍有保留 clean 开门程序、公共模式、先验等替代来源；不是记忆不影响取证的证明。
- **B 改进**：两组都是同一成功九步轨迹，没有省开门、减少搜索或减少无效动作；费用差主要为 token/cache 差，不能替代行动改进。没有支持本干预促进更优路径采用。
- **A**：得到合理成功程序记录与局部验证范围扩大并存的证据，特别是 M3 的实际 rule_8 validation；没有测试 Builder 吸收 E* 的能力。
- **A+B**：看到“同一 open 程序成功后被保留/记入技能”，但缺少干预导致的经历变化，不能识别 memory→经历→承诺维持的因果反馈链。未运行后续任务，不作 H3 强结论或 H4。

建议停止此候选的付费确认，不扩大 mask，不补跑。保留 M3 作为 A 的来源/适用范围分析样本。只有未来独立自然数据出现实际 E*、明确不同的更新处理或更少替代来源的决策关系，才值得重新提出不同的已登记假设；本报告不授权该后续运行。

## 6. 用量、价格和检查

实际 24 transports：12 generation（6 Worker+6 Builder），12 embedding（各任务 4 文档+1 query 分两次请求）。零重试、零额外 probe、零中止。输入共 76,528（生成 76,312，embedding 216）；生成输出 14,224；缓存输入 54,528。

本地保守估算 USD **0.023931168**，CNY **0.000108**，独立核算；provider 未报告账单金额，USD provider_reported=null，CNY provider 金额 unavailable，不能把估算称实际账单。ledger uncertain=false。24/72 requests，费用远低于 USD6/CNY.20；每任务 4/12，最高 USD .004837092/CNY .000018，未触发预留/停止条件。

生成全部 request=`deepseek-v4-flash`、response=`deepseek-flash`、thinking=false、temperature=0；embedding 全部 request/response=`text-embedding-v4`、北京、1024/float。2026-09-12 通过 direct.py + urllib ProxyHandler({}) 直连重新查阅 [DeepSeek 官方价格](https://api-docs.deepseek.com/quick_start/pricing/) 与 [DashScope 同步 embedding](https://help.aliyun.com/zh/model-studio/text-embedding-synchronous-api)：沿用峰值 USD .006/.30/1.20 每百万 hit/miss/output，CNY .5 每百万 embedding input，不扣免费额度。DeepSeek 文档说明旧请求 ID 现由 V4.1-Flash 服务；同一 deepseek-flash 别名不证明历史权重相同，历史表现不是本批因果对照。公开文档核价未调用模型。

执行前默认计划 exit 0；输出目录不存在才启动以下命令一次，exit 0：

```bash
python scripts/direct.py conda run -n memory-automanual python scripts/run/automanual_transform_branches.py --execute --output artifacts/transform-precondition-screen-v1
```

本轮只改解释文档/config，无运行代码变更；按要求未新增测试、未跑全套/lint/reset/安装/上游重放。使用 direct.py 的只读原始 JSON 核对：来源完整一致、组内请求一致、跨组仅指定字段差异、全部原始轨迹一致、规则字段差异及旧技能不变、完整 updater 终态、用量可信。git diff --check 通过。transport 保持显式禁代理、TLS 校验和零自动重试。没有改动 .env、全局代理或旧 artifacts，没有 Git commit。
