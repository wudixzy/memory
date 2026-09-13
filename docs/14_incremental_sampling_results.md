# 有限增量采样：结果与候选判断（2026-09-11）

## 结论

固定的 9 个新任务全部完成官方任务及更新，均 won=true。没有中止、替换、补跑或扩大预算。
观察到了真实的错误恢复、规则形成、跨类型技能迁移和后续同类型复用；但本轮没有筛出
**信息替代较少、值得立即付费确认的单规则候选**。这不是“记忆没有作用”，也不是 H1–H4 的反证。
建议降低当前 AutoManual 简单任务上的单规则 mask 搜索优先级，不继续 rule_3/task_01，
也不立即对新 rule_8 做高度冗余的分支。没有自动执行下一批。

所有本轮运行 synthetic=false、scientific_evidence=false，用于自然候选发现，不是因果确认。
继续使用已批准的 `automanual-native-won-v1-2026-09-11`，官方 chat 路径、受限 Python、
DashScope embedding substitution；不宣称等同论文原配置。

## 固定来源、选择与执行

原始产物：[`automanual-incremental-19a209c33a5e`](../artifacts/automanual-incremental-19a209c33a5e/)。
运行前清单/数据校验和、逐任务状态和共享 ledger 保存在
[`sampling.json`](../artifacts/automanual-incremental-19a209c33a5e/sampling.json)。
离线抽取（包含逐动作原始 observation、规则变更及请求 call_id）：
[`analysis.json`](../artifacts/automanual-incremental-19a209c33a5e-analysis.json)。
旧的 lamp 指标仍是复用分析器的字段，本轮不把它们用于候选结论。

只恢复一次原校准 `artifacts/automanual-calibration-f13a39e724d0/task_04/memory_after.json`：

- 文件 SHA256：`677148c3d99829085e9e40f77f4ba4d9f35d8a973b8dd0d68b8952c851676f74`。
- 完整 snapshot SHA256：`7dae14fff93e04423e51e04a91b7e38a659947b2f276d86a51e6b4b7ddbec6db`。
- 运行后再次核对来源文件哈希未变；未使用任何反事实分支的后续 memory。
- 清单文件 `configs/automanual_alfworld/incremental_tasks.json` SHA256：
  `268637df7ad1c0a59ac3a74acbb3cdfeb31d2a0f7399204ce29fd6f2f19f8165`。

使用已 pin 的 AutoManual `aeb17e4a4fe8bb43b9eb390b7b0b94a3ca8b9324` 及其 bundled ALFWorld，
保留 001/002/003 patches。本轮不安装依赖、不重放 patches、不读取任务答案筛题。
按本地 train 路径字典序，排除既有 look 类型、已运行 task（包含环境 smoke）、
不受支持的 movable/Sliced 路径；取前三类、每类前三个并交错。
普通搬放的 AlarmClock 已用于旧环境 smoke，因此排除；可用数量足够，无需下载。
全部 seed=42，NoIntervention，native epoch=5–13，严格按下列顺序运行：

| 目录 / epoch | 完整任务 ID（train 相对路径） |
|---|---|
| task_00 / 5 | `pick_and_place_simple-Book-None-Sofa-229/trial_T20190907_042933_874605` |
| task_01 / 6 | `pick_clean_then_place_in_recep-Apple-None-Fridge-27/trial_T20190906_220808_492885` |
| task_02 / 7 | `pick_cool_then_place_in_recep-Bread-None-CounterTop-15/trial_T20190909_085448_256298` |
| task_03 / 8 | `pick_and_place_simple-Candle-None-Toilet-427/trial_T20190909_030439_155103` |
| task_04 / 9 | `pick_clean_then_place_in_recep-Apple-None-Microwave-14/trial_T20190909_120203_117379` |
| task_05 / 10 | `pick_cool_then_place_in_recep-Bread-None-CounterTop-7/trial_T20190909_021904_818116` |
| task_06 / 11 | `pick_and_place_simple-Laptop-None-Desk-306/trial_T20190909_075009_810389` |
| task_07 / 12 | `pick_clean_then_place_in_recep-Cup-None-Shelf-20/trial_T20190909_150437_976767` |
| task_08 / 13 | `pick_cool_then_place_in_recep-Cup-None-Microwave-30/trial_T20190909_073451_112369` |

## 实际执行、用量及 memory

费用均为按可信 usage 和公开价格计算的本地估算，不是 provider 账单。
每行终态均为 completed、won=true；动作数只计真实环境 step，不计生成代码或反思中的步骤。
生成输入包含缓存，表中另列缓存；embedding token 独立列出。

| task | 动作 | 生成 / embedding 请求 | 生成 input / output / cached tokens | embedding tokens | USD | CNY |
|---|---:|---:|---:|---:|---:|---:|
| 00 | 5 | 2 / 2 | 9087 / 1951 / 5632 | 11 | 0.003411492 | 0.0000055 |
| 01 | 11 | 5 / 2 | 33531 / 5363 / 26240 | 19 | 0.008780340 | 0.0000095 |
| 02 | 8 | 2 / 2 | 11560 / 2583 / 6400 | 28 | 0.004686000 | 0.0000140 |
| 03 | 5 | 2 / 2 | 11247 / 1770 / 6400 | 33 | 0.003616500 | 0.0000165 |
| 04 | 12 | 2 / 2 | 12155 / 2344 / 5376 | 36 | 0.004878756 | 0.0000180 |
| 05 | 9 | 2 / 2 | 12233 / 2019 / 6016 | 37 | 0.004323996 | 0.0000185 |
| 06 | 6 | 2 / 2 | 11355 / 1747 / 7808 | 33 | 0.003207348 | 0.0000165 |
| 07 | 21 | 2 / 2 | 12985 / 2794 / 5376 | 36 | 0.005667756 | 0.0000180 |
| 08 | 15 | 2 / 2 | 13318 / 2995 / 3712 | 37 | 0.006498072 | 0.0000185 |
| 合计 | 92 | 21 / 18 | 127471 / 23566 / 72960 | 270 | 0.045070260 | 0.0001350 |

task_01 的 5 次生成分别是两次行动代码、一次成功后整理代码、两次 Builder 调用。
整理代码不是第三次环境执行；普通生成代码异常后第二次行动保留了真实环境进度。
全批 39 次 transport、0 次自动重试；全部 accounting_trusted=true。
全部生成请求/返回身份为 `deepseek-v4-flash` / `deepseek-flash`，non-thinking、temperature=0；
embedding 为北京 `text-embedding-v4` 请求/返回同名，1024 维 float，身份一致。
provider 未报告费用，相关字段保持 null，不用估算冒充账单。

硬限额：12 请求/task、108/run；USD 6/task 和 6/run；CNY 0.05/task 和 0.20/run。
没有触发任何限额、费用不确定或执行设施故障。
运行前直连核对价格（2026-09-11）：
[DeepSeek 官方价格](https://api-docs.deepseek.com/quick_start/pricing/)
Flash 每百万 cached/miss/output tokens USD 0.006/0.30/1.20，使用峰值保守价；
[DashScope 官方同步 embedding 文档](https://help.aliyun.com/zh/model-studio/text-embedding-synchronous-api)
北京 v4 每百万 input tokens CNY 0.5。不抵扣免费额度，不混合币种。
生成每请求按 1048576 输入及 2000 输出上限预留 USD 0.3169728；embedding 每条输入预留 8192 tokens，
即 CNY 0.004096，批量按条数计算。记账及请求前预算未削弱。

逐任务核对完整 `memory_before.data == previous memory_after.data`：9/9 一致，第一项对来源 checkpoint。
每任务新环境、新 guest，native epoch 正确推进；每任务临时角色和记录器状态清理，原生 memory 不重置。
规则数 7→8→9，此后保持 9；技能 1→2→3→4，此后保持 4。
99 个 updater 区间全部结束且 completed（每任务 10/11/10/11/12/10/11/11/13），
没有 merge（规则未超过原生阈值）、没有规则删除/重编号；ID 仍仅按具体 checkpoint 解释。
最终 snapshot：`8599df8c9987f817026a629ed932d876110c5e1b71ee19afd36e8a94ee04ccb6`。

## 检索和自然复用的证据

每任务的 `memory_injections.jsonl` 保存 query、实际返回 skill ID、文本和 helper 源；
`model_calls.jsonl` 保存实际 Worker 请求。不是根据类型名推断检索结果。
全批使用同一 embedding identity、官方 FAISS，normalize_L2=false。

| 目标 task | 实际 query → 返回 skill | 来源和后续情况 |
|---|---|---|
| 00 | simple → look_at_obj_in_light | 原校准技能；Worker 改写成找书、拿书、放沙发 |
| 01 | clean → pick_and_place_simple | task_00 的书技能；之后形成 clean 整理技能，原生 success=0 |
| 02 | cool → pick_clean_then_place_in_recep | task_01 成功后的整理代码，**该整段未重新环境执行**；官方允许检索 success=0 |
| 03、06 | simple → pick_and_place_simple | 持续返回 task_00 书技能，分别实际改成蜡烛、笔记本任务 |
| 04 | clean → pick_clean_then_place_in_recep | task_01 技能；task_04 首次直接成功后替换为苹果进微波炉技能，success=1 |
| 07 | clean → pick_clean_then_place_in_recep | 返回 task_04 技能，真实搜索杯子、清洗并放到架子 |
| 05、08 | cool → pick_cool_then_place_in_recep | 返回 task_02 面包冷却技能，实际适配不同布局/物体/目标 |

下表的 call_id 都指本批对应 task 的 `model_calls.jsonl`；update_id 指 `updates.jsonl`。
Worker 的规则消息在 messages[5]。**输入出现、行为相容不等于该规则有独立因果作用。**

| 关系 | 形成/更新的原始证据 | 后续实际注入及行为 | 判读、替代来源 |
|---|---|---|---|
| rule_7：找→拿→放，扩展 clean/cool | task_00 `update_000005` / Builder `c39216e2eebb4e0dba93b2a7672d8528` 写入；真实步骤 1–5 成功。task_01 `update_000005` 加开门/清洗；task_02 同号区间加冷却，均有对应实际动作 | task_01 Worker `8169cab8484c4478bf344d4f5801da2c` 已注入旧版；task_04 `29bc9c2f29fb4344a54d98aede86846b` 注入扩展版，步骤 7/9/11/12 拿/洗/开/放成功 | 自然形成及相容复用成立；同一过程已在检索技能中，因果归属未分离。加入 heat/microwave/stoveburner 的泛化没有本批加热执行证据 |
| rule_8：目标关闭则先开再放 | task_01 步骤 8 原始 `fridge_1 is closed`，9 `Nothing happens`，10 `You open`，11 `You put`/won=true；Builder `ac3cdc0989734e739e46c4c78fa1891b`，`update_000006` 写入 | task_04 Worker 同上、task_08 Worker `fbc8dddca5464b22ba23ffc4e6720f2d` 均实际注入；task_04 步骤 10–12、task_08 步骤 13–15 在 closed 观察后开微波炉再成功放置 | 合理纠错的直接证据；rule_7、技能、公开 `go_to_put_object` 都提供开门逻辑。不宜再次做高度冗余的单规则 mask |
| rule_6：go_to 无效时跳过 | 来源校准 rule_6 原已存在；本批 task_04 `update_000005` / `71d74c5d18224232a590ef4cca85523e` 强化；task_08 `update_000008` 再强化 | task_04 Worker `29bc…` 步骤 3、task_08 Worker `fbc8…` 步骤 5 到初始列表中不存在的 diningtable 均 `Nothing happens` 后继续 | 本批缺失桌子的解释受初始观察支持；不是“所有 Nothing happens 都不可达”的验证。helper 的普通搜索循环本来就继续，规则的额外作用不可识别 |
| rule_1：三返回值 helper 的记录 | task_07 `update_000005` / `7662984473dd4efaa8b6361ac25181c4` 加入 `find_object_with_obs` 示例 | task_08 请求 `fbc8…` 已收到新例子；但真实 Worker 代码仍自己定义/调用名为 `find_object` 的三返回值版本。Builder `dfec87b7feec4de383b7660be9fc7bf6` / `update_000005` 却记录为使用了 `find_object_with_obs` | 是具体命名归因不准确，不是该新增函数实际执行的证据；三返回值在旧技能已存在，不是独占新信息 |

补充人工核对：

- task_01 Worker 第二次回复把尚未更新的 rule_7 解释成“closed 先 open”，但当时 rule_7 不含此条；
  Builder 第一阶段 `b86b819863814af6a4c0e65c41b72a29` 也输出更新代码，真正执行的更新却来自随后
  `ac3cdc…`，不能把两段模型代码都计成 memory 写入。
- task_07 文字计划先列 cabinet 再 shelf，实际代码及步骤 3–5 先查看 shelf，再依次打开 cabinet_1–5；
  第 15 步才观察到 cup_1。后续 shelf_2/3 放置备选没有执行，不能算探索。
- task_08 Builder 总结说冷却时开过关闭冰箱；实际第 7 步在搜索阶段开冰箱，第 11 步返回时已打开，
  第 12 步直接冷却。不能把成功总结当作精确时序。
- 本批多次原始 `Nothing happens` 是重复 go_to 当前地点，随后照常拿物成功。
  官方 `env_history.py:141–145` 会把这类观察替换为当前位置缓存，不能将原始环境字符串
  等同 Python/Worker 看到的反馈。rule_6 的“不可达”解释不能套到这些动作。
- task_07 真实打开五个柜子并获得逐次内容信息，表明没有普遍停止证据获取。
  9 次成功与较短轨迹也不能证明规则有益/无害；没有执行反事实。

## 候选筛选与下一步

**本轮推荐的新付费分支候选：0 个。** 有两个可描述但不优先执行的线索：

1. rule_8 → task_04：可从 task_03/memory_after 恢复，预测 mask 后增加“closed 目标上首次放置失败”或推迟 open。
   形成与注入证据完整，但 rule_7 与实际 clean 技能已有同样操作。若 mask 后开/放顺序不变，
   只能否定该渠道在该配置的边际预测；并不能否定知识作用。信息替代问题与旧候选相似，故不立项。
2. rule_6 → task_08：可从 task_07/memory_after 恢复，预测 mask 后更可能再次尝试无效 diningtable
   或增加位置核查。然而实际 helper 无须该规则也会继续搜索；原生当前地点观察缓存又限制了
   “失败即跳过”触发条件。即使计划中提及规则，也不足以预计可区分的行动改变，故不立项。

rule_1 新 helper 是命名归因线索，不补成第三个候选。rule_7 的 heat 扩展是未经本批验证的范围扩大，
不是已经观测的有害泛化；没有加热后续轨迹，不能据此提交规则—行为因果候选。
恢复给任何未来分支的 memory 必须来自目标之前，不包含这里的分析结论或后续任务更新。

明确建议：**降低当前简单 ALFWorld 任务上的单规则注入屏蔽路线优先级**，保留本批作为
自然纠错/重复信息来源的负筛选结果。若后续仍希望投入此 baseline，优先考虑尚未覆盖的
`pick_heat_then_place_in_recep` / `pick_two_obj_and_place` 的小型、另行授权采样，
而不是继续重复此处三类或追加冗余 mask。这里没有为其创建执行批次或消耗预算。

## 最小接线、验证及工作树

- `scripts/smoke/automanual_adapter.py`：复用原顺序 worker，支持来源恢复一次、之后只推进 epoch，
  共享 ledger；不修改官方提示词或更新算法。
- `scripts/run/automanual_incremental.py`：固定清单、默认计划、显式执行；启动前拒绝已运行任务，
  校验来源/任务文件哈希；不是 checkpoint/调度/恢复框架。
- `tests/test_rule_screening.py`：仅新增一项 restore-once 连续状态/epoch/原件不变的离线回归。

实际命令（全部经 direct.py，进程代理清除，真实 transport 显式 ProxyHandler({})，TLS 开启）：

```bash
python scripts/direct.py conda run -n memory-infra env PYTHONPATH=src python -m unittest discover -s tests -p test_rule_screening.py -v
python scripts/direct.py conda run -n memory-infra ruff check scripts/run/automanual_incremental.py scripts/smoke/automanual_adapter.py tests/test_rule_screening.py
python scripts/direct.py conda run -n memory-infra ruff format --check scripts/run/automanual_incremental.py scripts/smoke/automanual_adapter.py tests/test_rule_screening.py
python scripts/direct.py conda run -n memory-infra python -m compileall -q scripts/run/automanual_incremental.py scripts/smoke/automanual_adapter.py tests/test_rule_screening.py
python scripts/direct.py git diff --check
python scripts/direct.py conda run -n memory-automanual python scripts/run/automanual_incremental.py
python scripts/direct.py conda run -n memory-automanual python scripts/run/automanual_incremental.py --execute
python scripts/direct.py conda run -n memory-infra python scripts/analysis/automanual_evidence.py --source artifacts/automanual-incremental-19a209c33a5e --output artifacts/automanual-incremental-19a209c33a5e-analysis.json
```

以上均 exit 0；6 项针对性测试通过（含新增 1 项），Ruff/格式/compileall/diff 通过。
不重复完整测试矩阵、reset、校准、独立 API probe、安装或上游重放。
真实执行命令只运行一次；不要重跑已完成批次。环境未变：memory-infra Python 3.10.20 / Ruff 0.12.0，
memory-automanual Python 3.9.16。凭证只由真实 transport 加载，未打印/修改 `.env`。

保留原有工作树修改，没有 commit。最终 status 的目录级摘要仍为：
修改 AGENTS.md、README.md、docs/01、docs/02；未跟踪 .env.example、.gitignore、configs/、docs/03–14、
pyproject.toml、scripts/、src/、tests/。运行 artifacts、third_party、真实 .env 继续 gitignored。
