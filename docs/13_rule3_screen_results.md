# rule3-order-screen-v1：六分支执行与分析

2026-09-11；一次授权启动，六个分支全部完成。**建议转向有限增量采样，
暂不继续付费确认当前规则渠道/任务组合。** 本任务上没有观察到 rule_3
通过 Worker 规则渠道的边际动作、证据获取或任务结果影响。
这不排除其知识被其他渠道替代，也不否定其他任务中的影响。

## 实验和实际结果

严格执行 [预先固定方案](12_first_rule_branch_screen.md)：I1 → M1 → M2 → I2 → I3 → M3。
来源仍为校准 `task_00/memory_after.json`，snapshot SHA256
`1ccc7b7eb51c9780aa5db68a78215342219588d017fd300729b9bea9616fd349`。
目标 `rule_3`；任务 `look_at_obj_in_light-AlarmClock-None-DeskLamp-314/trial_T20190908_042426_942777`，
seed 42、native epoch 1。新环境和 guest、每次从独立副本恢复；不继承分支更新。
保持 actor_rule_injection_mask 的范围、原有预测及主指标，未扩 mask 或重试补跑。

产物：[完整批次](../artifacts/automanual-rule-branches-26a1a1925404/)、
[提取分析](../artifacts/automanual-rule-branches-26a1a1925404-analysis.json)、
[事后只读核验记录](../artifacts/automanual-rule-branches-26a1a1925404-review.json)。
`synthetic=false`，`scientific_evidence=false`；用途为预注册规则渠道筛选，非 H2–H4 确认。

主指标为“未持有目标闹钟时使用灯”的实际动作位置列表及发生/次数。
下表拿取/用灯的位置均为原始观察确认成功的动作；所有分支没有 put 尝试，成功放置也是 0。

| 目录 / 分支 | 主指标发生 / 次数 | 成功放置数；拿取→用灯位置 | won / 终态 | 生成 input / output / cache tokens | 本地 USD 估算 | 本地 CNY 估算 |
|---|---|---|---|---|---:|---:|
| task_00 / I1 | 否 / 0 | 0；4→6 | true / completed | 8795 / 2016 / 5120 | 0.003552420 | 0.000006 |
| task_01 / M1 | 否 / 0 | 0；4→6 | true / completed | 8475 / 2037 / 4864 | 0.003556884 | 0.000006 |
| task_02 / M2 | 否 / 0 | 0；4→6 | true / completed | 8459 / 2002 / 6272 | 0.003096132 | 0.000006 |
| task_03 / I2 | 否 / 0 | 0；4→6 | true / completed | 8742 / 1516 / 6400 | 0.002560200 | 0.000006 |
| task_04 / I3 | 否 / 0 | 0；4→6 | true / completed | 8946 / 2445 / 6528 | 0.003698568 | 0.000006 |
| task_05 / M3 | 否 / 0 | 0；4→6 | true / completed | 8490 / 1791 / 6144 | 0.002889864 | 0.000006 |

每分支 2 次生成 + 2 次 embedding，embedding input 均为 12 tokens。
intact 完整运行 3、中止 0、正常任务失败 0、主指标 0/3；masked 相同。
六条 **完整 actions 与 observation/reward/won/done 序列逐项相同**，不仅是主指标相同。

### 原始观察人工核对

每个任务目录的 `actions.jsonl` 与 `trajectory.json` 都是以下六步：

1. go to desk_1：看见 alarmclock_4/3/2/1、desklamp_1 等物体。
2. go to desk_1：`Nothing happens.`
3. go to desk_1：`Nothing happens.`
4. take alarmclock_4 from desk_1：`You take alarmclock_4 from desk_1.`，won=false。
5. go to desk_1：`Nothing happens.`
6. use desklamp_1：`You turn on desklamp_1.`，won/done=true。

第 2、3、5 步是重复 goto 的无效响应，不是失败放置；没有把它们算作放下物体。
没有未持物开灯、先放下再用灯、额外 inspect/open，也没有为求解成功手写策略。
计数基于实际执行及反馈，未把可见生成代码中的未执行片段计为动作。
没有行为差异可据以主张“新增决策相关证据”；远程输出文字与 token 量变化本身不算 H2。

## 确认干预确实生效

六份 `memory_before.json` 与来源完整 JSON（含 raw native files、规则、技能、历史、控制字段及 metadata）
完全相同。`branches.json` 的 restored_source_exact 六项均 true；原校准 105 个文件哈希复查均未改变。

实际 Worker request call_id：

| 分支 | call_id |
|---|---|
| I1 | 11ea2c34612a402b8ba52cc37ca2d656 |
| M1 | fb57b4fc73244b6899beeb22fce7c344 |
| M2 | f25cdddbc4bd453199dc2c4c14fd6ca4 |
| I2 | cc2f764726484f259272956353661ca7 |
| I3 | 17a0505050174520b0a51cfe592b8419 |
| M3 | 0513aa4002d44897b8fee56eb820ab80 |

读取各 `model_calls.jsonl` 的真实 request：intact 的 messages[5] 含 rule_3 段，
masked 不含。仅从 intact 删除该段（到 rule_4 起始前）后，六份完整 Worker
请求 payload **完全一致**，包括其他消息及模型/解码参数。
`memory_injections.jsonl` 的 actor_rule_helper_sources 也只有该条 example 的差别；
真实 rule_3 没有函数定义，因此未移除额外可调用 helper。
六份 skill_return 事件相同，官方 Skill_Bank/FAISS 均检索同一原生技能。
Builder 请求仍包含完整原始 all_rules，包括 rule_3；它的实际轨迹输入随模型输出变化，未被人为统一。
这不是全局删除知识，也不是 Builder 屏蔽。

### 原生更新的附带观察

完成区间数依次为 10/13/12/10/12/11，共 68 个，全部 completed；原生最终 memory 仍分别保存。
所有分支都更新 rule_3，masked 的 Builder 也可以正常强化它，这是本干预的预定范围而非泄漏。

M1 的 Builder `2d4ef208e4034871a70bcb8c05d4d338` / update_000005，
M2 的 `f3edbe7209d143388fb27efecd11abc9` / update_000007 分别新增本地 rule_6，
将“选择 alarmclock_4 成功”概括为“任一同类实例都可用于任务”。两条文本不同，
不能因为同名就等同，更不能与旧校准 task_03 的 rule_6 混同。
这提示可见证据与概括范围仍值得在未来采样中观察，但其他实例未被试验，
此次也没有对应行为差异；**不据此追加候选、宣称 H3 或启动长期确认**。

## 模型、费用和预算

12 次真实生成均请求 `deepseek-v4-flash`，返回 `deepseek-flash`；non-thinking、temperature=0。
12 次真实 embedding 均请求/返回 `text-embedding-v4`，北京 endpoint、1024 维、float。
总计 **24 次 transport、0 自动重试、0 补跑**；不存在独立 probe。
生成 input=51907、output=11807、cached input=35328；embedding input=72。
每次 accounting_trusted=true，run ledger uncertain=false。

本地 estimated/accounted 总计 **USD 0.019354068 / CNY 0.000036**。
provider 未报告费用，两币种 provider cost 均保持 unavailable/null；这些估算不是实际账单。
每任务最多 12/run 72 请求、USD task/run 6、CNY task 0.05/run 0.20 的硬限制原样生效；
没有触发预留不足、费用不确定、身份变化或执行设施中止。

执行前通过 `scripts/direct.py` + `urllib.request.ProxyHandler({})` 直连公开文档，
TLS 校验开启、30 秒超时，不使用凭证：
[DeepSeek 价格页](https://api-docs.deepseek.com/quick_start/pricing/) 仍列
Flash peak hit/miss/output USD 0.006/0.30/1.20 每百万 tokens；
[DashScope 同步 embedding 文档](https://help.aliyun.com/zh/model-studio/text-embedding-synchronous-api)
北京 text-embedding-v4 仍为 CNY 0.0005/千 input tokens。
因此沿用原估价及完整 context/embedding 输入预留，不使用免费额度放宽预算。
模型 transport 保持 ProxyHandler({})、TLS 校验与零自动重试。

## 小修正与实际验证

`scripts/analysis/automanual_evidence.py`：

- put_before_first_lamp_use 仅计 target put 且原始 observation 确认 `You put` 的成功动作；
  失败 put 不改变 holding，主指标和预测不变。
- unavailable/缺失 memory、trajectory、usage 不阻断其余任务提取；中止状态保留，
  已取得的 observations、已配对动作及待返回动作保留。
- 中止或轨迹不完整的主 metrics 全部 null，观察到的前缀单独放 observed_prefix_metrics；
  不计入完整组、不当成正常任务失败。normal_task_failures 仅计完整运行且 won=false。

`tests/test_rule_screening.py` 新增两项小回归：失败/成功 put 对比、
完整任务与 unavailable/中止任务混合提取。无异常矩阵、无新通用框架。

实际命令（均禁用代理）：

```bash
python scripts/direct.py conda run -n memory-infra env PYTHONPATH=src python -m unittest discover -s tests -v
python scripts/direct.py conda run -n memory-infra ruff check src tests scripts
python scripts/direct.py conda run -n memory-infra ruff format --check src tests scripts
python scripts/direct.py conda run -n memory-infra python -m compileall -q src tests scripts
python scripts/direct.py git diff --check
# 以下真实命令只执行了一次，退出码 0
python scripts/direct.py conda run -n memory-automanual python scripts/run/automanual_rule_branches.py --execute
python scripts/direct.py conda run -n memory-infra python scripts/analysis/automanual_evidence.py --source artifacts/automanual-rule-branches-26a1a1925404 --output artifacts/automanual-rule-branches-26a1a1925404-analysis.json
```

**158 项测试通过，2.562 秒**；Ruff/format（41 files）/compileall/diff 均通过。
另以只读 JSON 检查逐一断言 checkpoint、Worker 输入差异、helper/skill 一致性、
Builder 完整规则、所有更新终态以及六条实际轨迹相同，结果均通过。
未安装依赖、未改 .env 或上游代码、未重跑校准/reset，未创建 Git commit。

## 判断与下一步

这是 **intact 0/3 对 masked 0/3** 的主指标筛选阴性结果，而非显著性或等价性证明。
保留的 rule_5、成功技能、历史和模型先验都可能提供替代知识；当前单一灯下观察任务也较简单。
不改预测、不扩大屏蔽来追求正结果。

**明确建议：转向有限增量采样。** 暂停当前候选的付费确认；以后若另行授权，
优先在少量不同训练任务类型中观察自然规则形成和复用，而不是继续重复同一个简单任务。
本轮不制定或启动新的付费批次；所有六个结果（包括阴性结果及不同原生更新）均保留。
