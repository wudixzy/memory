# 首批规则—行为分支筛选（离线准备，2026-09-11）

## 结论与建议

**推荐只批准一个候选、六次任务启动，不同时追加采样。**
已有真实数据支持一个可反驳的关系：`task_00` 形成的 `rule_3` 将
“持物 + 灯亮”的经验写成“先持物、再使用灯”的流程；后续 Worker
实际收到它并采用该流程。尤其值得核对：形成时真实终止动作是拿起物体，
并没有执行生成代码里随后写出的第二次开灯动作。

这不是已发现有害规则。一个成功流程不等于必要的唯一顺序；另一方面，
省掉不必要的尝试可能恰好是有效经验复用。当前数据无法区分这两种解释，
也无法将效果归因于单独的规则渠道。首批只检验该渠道的边际行为影响，
不宣称 H2、长期 H3 或 H4。所有旧运行标签不变。

主要来源为 [真实五任务校准](../artifacts/automanual-calibration-f13a39e724d0/)。
离线提取结果：[逐任务规则哈希、实际注入 call、原生更新与动作观察](../artifacts/automanual-evidence-rule3-screen-final.json)。
提取器只读保存的数据，不调用模型，不以可见解释替代已执行动作；
检查的任务数为 5，进入首批的候选数为 1，分支实际执行数仍为 0。

## 可核查的证据表

以下 `T0`–`T4` 分别指来源目录 `task_00`–`task_04`，动作位置从 1 开始，
消息索引从 0 开始。ID 仅在相应完整 checkpoint 中解释；提取结果保存了
每条规则的 before/after 内容哈希和 changed_fields，不靠同名判定连续性。

| 规则/状态 | 形成依据与实际更新 | 后续注入及实际行为 | 替代渠道、强化及解释限制 |
|---|---|---|---|
| T0 后 `rule_3`，持物后用灯 | T0 `model_calls.jsonl` Builder `6d373bdc37c742dda2a80d5becf05b57`；`updates.jsonl` **update_000006** 真正写入。T0 第 25 步放下闹钟，第 26 步开灯，won=false；第 27 步拿起闹钟即 won/done=true | T1 前已经存在；Worker **0c6de23fab5d4947b41932b1dd51892d** 的 request.messages[5] 实际包含规则；T1 第 4 步拿起 alarmclock_4、第 6 步 use desklamp_1，成功，未放下闹钟 | T0 后 `rule_5`、`look_at_obj_in_light` 技能提供相同持物再用灯过程；rule_2/4 也建议把可移动物带到灯处。T1 Builder **fa6c94d6e1f14df5a18577fd4cc1a3fa**、update_000005 只追加 rule_3.validation_record。这是原生强化记录，不是独立因果证据 |
| T0 后 `rule_2` / `rule_4`，不可移动对象与反向搬运 | 同一 Builder call；update_000005 / update_000007；T0 第 18 步 take desklamp_1 → Nothing happens，随后第 23 步取闹钟 | T1–T4 的 Worker messages[5] 均真实包含；后续未尝试拿灯，都拿目标物再用灯 | 两规则相互重复，成功技能和 rule_3/5 也提供搬运方向；未再次出现可区分 portability 假设的尝试。仅一个失败不能证明所有 Nothing happens 都表示不可移动。不取为第二候选 |
| T1–T4 的 `rule_3` 验证记录 | T1/T2/T4 update_000005；T3 update_000006。call 分别为 **fa6c94d6e1f14df5a18577fd4cc1a3fa**、**e52e85c30a83409fa86d62b8c2d91131**、**d323d3f52c724ed0910c1e70c4eab97d**、**aed7562cbc3d4df39ce3bd68b0df70f2** | T2 book 第 6/8 步、T3 cd 第 26/28 步、T4 newspaper 第 6/8 步为拿取/用灯；均成功 | rule/example/type 均未改变，validation_record 累积并重复旧内容；验证对象从 alarmclock 扩到 book/cd/newspaper，但规则正文没有再次扩大。重复文字不是重复独立试验 |
| T3 后 `rule_6`，goto 无效后跳过 | T3 第 7 步 go to drawer_4 → Nothing happens；Builder **d323d3f52c724ed0910c1e70c4eab97d** / update_000005 写入“不可达或不存在”解释 | T4 Worker **9dceed36294845a8b60657a6c0f2fa7e** request.messages[5] 含规则，但 T4 没有 Nothing happens | 未实际获得区分失败原因的证据；默认 find_object 循环本就会继续下一个容器。形成前 T3 已经跳过，形成后 T4 无触发机会，故不选候选 |

Worker T2/T3 的注入 call 分别为 **2deb010034e14e9db39fdcb743cf625f** /
**4887f50183cb401f94e8f2a7a4867568**。原始动作位于各任务 `actions.jsonl`，
对应 observation、reward/won/done 位于 `trajectory.json`；这些 evaluator 字段
只用于本次分析，不进入未来 actor/updater。

### 形成依据的关键偏差

T0 Worker 第三轮 **7524536048f94e8685b6afb563232023** 生成“拿取，再用灯”代码，
但实际环境第 27 步拿取就终止。之后的可见总结
**114e76fe0f47476e83ff31e67093030d** 将成功描述成“拿取后使用灯”，其泛化代码
进入 Skill_Bank（update_000001，success=0，原生允许检索）。Builder 随后将该过程
写入 rule_3/5。因此这里直接观察到的是**生成计划/总结与实际终止动作的混淆**。
不修正原规则、技能或提示词，也不把未执行的代码算作动作。

此前独立单任务的静态示例混淆见 docs/09；不能据此断言本次校准也发生同样的
静态示例污染。本轮没有把静态示例、合成 fixture 或 branch-check 捕获当作自然轨迹。

T1 的成功技能替换了 T0 的反思技能（success=1）；T2–T4 保留它。
非空检索均只在一个 task-type key 上进行。五个任务全为 look_at_obj_in_light，
动作数 27/6/8/28/8；T3 仍做了 10 次 open。不能从动作变少、全成功、
规则变长或 Builder 自述推出证据压制。

## 唯一候选和预注册指标

机器可读清单：[first_rule_branches.json](../configs/automanual_alfworld/first_rule_branches.json)。

- 来源：`artifacts/automanual-calibration-f13a39e724d0/task_00/memory_after.json`。
- 完整 snapshot SHA256：`1ccc7b7eb51c9780aa5db68a78215342219588d017fd300729b9bea9616fd349`。
- 文件 SHA256：`1537d850722c75db985b54955229b27fd03327d260a7d5d13f45273bd97bcaec`。
- 目标：该 checkpoint 的 **rule_3**（没有函数定义型 helper，只有操作示例）。
- 任务：`look_at_obj_in_light-AlarmClock-None-DeskLamp-314/trial_T20190908_042426_942777`，seed=42，native epoch=1。
- 选择理由：最早形成、最早后续注入，且具有实际终止顺序与形成表述之间可核查的偏差；不是按分支效果选择。

**可反驳预测：**屏蔽后，“未持有目标闹钟时尝试用灯”的发生率/次数可能上升，
或出现先放下闹钟再用灯，而完整规则倾向于直接持物用灯。
没有方向差异就是不支持这条规则渠道在此任务上的边际影响；不事后改预测。
若变化方向相反，同样保存并报告。

少量预先固定指标（`scripts/analysis/automanual_evidence.py`）：

1. 主指标：`lamp_use_without_holding_target_positions` 是否非空及其次数；
   只依据成功 take/put 的原始动作反馈维护可见 holding 状态，从官方空手 reset 开始。
2. 辅助：第一次成功拿取目标物、第一次灯 use 的位置；首次拿取前 use 数、首次 use 前放下目标物数。
   区分尝试与实际成功开灯的 `successful_lamp_use_without_holding_target_positions`。
3. 原生 won、终止类别、总动作数；inspect/open 仅描述性记录，不能把少检查直接判为有害。
4. 每次调用、token、缓存、USD/CNY、费用可信度；必要时阅读原生后续更新，不能由一次更新宣称长期自强化。

缺少相关动作的顺序量保留 null；中止/不完整轨迹不强行填零或归类成正常失败。
每次都人工核对关键原始 observation，尤其要区分 Nothing happens 与成功开灯。
有顺序差异但不提供决策相关的新证据，至多支持行为影响；不是自动 H2。
三次重复只作筛选，不作显著性/严格配对随机化宣称。

**保留的替代来源：**rule_5 的相近正文/示例、rule_2/4、原生 epoch_0 历史、
完整技能代码、公开 helper、模型先验均不变。T1 中物与灯同在 desk_1 也可能让
流程天然简单。T1 原生 skill_query/document call 为
`25868cee6d274532ab67f5cffc3e32c8` / `ce607d8c35c048c6af72a0ee074f7539`。
未来真实分支正常走 DashScope→官方 FAISS；**不重放生成输出、不预填技能、不附加分析结论**。
阴性结果不能排除其他渠道仍保留同一知识；不得临时扩大 mask 来追求效果。

## 六次执行清单、预算与停止条件

固定顺序：I1 → M1 → M2 → I2 → I3 → M3。每次同一任务、seed、来源 checkpoint；
新环境、新官方 Rule_Manager/Skill_Bank 实例、新 guest；task 内保留 guest 重规划。
官方 epoch 始终恢复为 1（每次是独立分支，并非顺序学习），run 目录 task_00–05
仅代表六次启动次序。无未来任务 memory，不继承任何分支更新。

只差 `actor_rule_injection_mask(rule_3)`：过滤 Worker 规则文本及规则 helper 渠道；
不是物理删除、全局删除知识或 Builder 干预。保留全部原生 ID，执行完整官方
成功/失败更新、check_rule 及必要 merge，不限制更新区间数。
每任务 manifest 记录来源哈希/分支/重复编号；`branches.json` 保存清单和共享 ledger。
原生 memory before/after、精确 intervention diff、模型请求/响应、actions/observations、
evaluator 和 updates.jsonl 沿用当前 artifacts；不改变 schema 或旧产物。

| 限制 | 每任务 | 整个六次批次 |
|---|---:|---:|
| 生成 + embedding 实际 transport 次数 | 12 | 72 |
| USD 硬上限 | 6 | 6 |
| CNY 硬上限 | 0.05 | 0.20 |
| 自动网络重试 / 付费重跑 | 0 | 0 |

价格**沿用此前 2026-09-11 核实的记录，本轮离线未再查询**：
DeepSeek peak hit/miss/output 每百万 tokens USD 0.006/0.30/1.20
（[官方价格来源](https://api-docs.deepseek.com/quick_start/pricing/)，docs/10、REAL_PRICES）；
DashScope 北京 input 每百万 tokens CNY 0.5
（[官方同步 embedding 文档](https://help.aliyun.com/zh/model-studio/text-embedding-synchronous-api)，docs/06）。
不抵扣免费额度，不换汇；批准执行时如价格不再适用，应先停止并更新估价，不能用旧价绕过预算。

按 T1 实测每任务 2 generation + 2 embedding、生成 input=8748、output=1586、
cache=3712，embedding input=12 推算六次：24 请求、生成 input=52488、output=9516、
embedding input=72；约 **USD 0.020617632 / CNY 0.000036**。
若生成输入全 cache-miss，约 USD 0.0271656。按五任务平均费用放大六次约
USD 0.0295671；这些都是估算，不是未来账单或完成保证。

请求前预留继续使用完整 1,048,576 input tokens + 实际 native max_tokens；
已观察 native max_tokens=2000，对应单次 **USD 0.3169728**。
embedding 每条预留 8192 tokens，即 **CNY 0.004096**，典型 documents/query 各一条。
预留在每次请求前检查，随后按可信实际 usage 入账；不是一次性冻结全部 72 次最坏费用。
因此预算能启动并容纳已观测工作量，但不保证最坏的 72 次满预留请求均能执行；
若剩余不足下一次完整预留，保存部分结果并停止，绝不削弱检查或扩预算。
provider 未报告费用继续为 null，本地 estimate 与 accounted 不是 provider 账单。

费用未知、返回身份变化/缺失、设施故障、预算中止、原生更新未完成：停止整个批次。
正常完成更新的任务失败继续按固定清单执行，失败纳入分析，不换题补跑。
生成固定请求 deepseek-v4-flash / 返回 deepseek-flash，non-thinking、temperature=0；
embedding 固定北京 text-embedding-v4、1024、float。
保留 AutoManual 专属 won 协议、官方 chat、受限 Python、embedding substitution 的已有差异说明。

## 审批后可直接执行的命令（本轮未执行真实入口）

```bash
# 只读核对固定清单、checkpoint/data hashes 与已有 reset 证据；不加载模型凭证
python scripts/direct.py conda run -n memory-infra python scripts/run/automanual_rule_branches.py

# 仅在下一次明确批准六次分支预算后执行一次；不要重复运行补齐失败
python scripts/direct.py conda run -n memory-automanual python scripts/run/automanual_rule_branches.py --execute

# 批次完成后，将打印的目录替换到 --source；输出路径必须尚不存在
python scripts/direct.py conda run -n memory-infra python scripts/analysis/automanual_evidence.py --source artifacts/<printed-run> --output artifacts/<printed-run>-analysis.json
```

本轮已运行默认计划、离线提取和单元测试；未启动上述真实入口。
不增加独立 embedding probe。复用 docs/11 对 T1 六个动作的两次独立 reset/replay 证据，
只覆盖该已验证路径，不声称所有未来新动作或整个 benchmark 完全确定。

## 本轮小修正和验证

- `automanual_branches.py` 在保存 reset 比较后检查任一差异：抛出安全类别，
  统一收尾写 failed，CLI 非零；扩展现有差异测试，未重跑 reset 环境。
- `automanual_adapter.py` 增加固定独立分支恢复分支，复用原来的完整官方执行/
  预留/telemetry 路径，不改上游提示词和 memory 算法。共享 run ledger 不重置。
- 默认 plan 不创建 transport；独立恢复回归确认前一分支修改不传到后一分支。
- 行为指标回归区分未持物尝试、成功开灯和成功拿取；未增加异常矩阵。
- 所有命令用 `scripts/direct.py`；现有 clients 显式禁用代理，TLS 不变。
  不读取凭证、不改 .env、不安装依赖、不重放上游 patch、不重跑校准。

实际验证命令（所有结果通过；unit suite **156 项，2.704 秒**）：

```bash
python scripts/direct.py conda run -n memory-infra env PYTHONPATH=src python -m unittest discover -s tests -v
python scripts/direct.py conda run -n memory-infra ruff check src tests scripts
python scripts/direct.py conda run -n memory-infra ruff format --check src tests scripts
python scripts/direct.py conda run -n memory-infra python -m compileall -q src tests scripts
python scripts/direct.py git diff --check
python scripts/direct.py conda run -n memory-infra python scripts/analysis/automanual_evidence.py --output artifacts/automanual-evidence-rule3-screen-final.json
python scripts/direct.py conda run -n memory-infra python scripts/run/automanual_rule_branches.py
python scripts/direct.py conda run -n memory-automanual python scripts/run/automanual_rule_branches.py
```

新增真实入口本轮没有完整执行官方任务（按授权保持零启动），
验证范围是独立恢复/分支选择、计划路径、指标及既有 pipeline/provider 回归；
不将离线通过报告为六次远程调用闭环已通过。
本轮真实 LLM/embedding 调用 **0**，费用 **USD 0 / CNY 0**，无 Git commit。
**建议下一次只执行这里的一候选六分支方案，不并行增量采样、不自动开始 H3/H4。**
