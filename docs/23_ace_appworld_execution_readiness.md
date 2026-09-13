# ACE + AppWorld：review 修复、执行边界与完整批次

2026-09-12。**可以提交原定一次批次的付费批准；本轮未执行真实模型请求。**
这不是 ACE Phase 0/1 已通过，也没有产生新的 A/B 科学样本。首次真实来源任务仍兼作模型兼容性检查。
本报告接续 docs/21–22，不改变任务、原生记忆算法、干预或研究判据。

## 1. Review 修复及旧证据更正

旧 `artifacts/ace-appworld-offline-v2/observations.jsonl` 的最后一段实际为：

```text
apis.supervisor.complete_task()
io.UnsupportedOperation: not writable
```

完成状态先改变，日志写入随后失败，因此旧 manifest completed、四次合成调用及 ADD **不能证明正常
API 执行反馈已经接通**。旧文件保持原样；docs/22 的相关接线结论受此更正限制。

|问题|修复位置|直接证据|
|---|---|---|
|guard 内写日志干扰操作|`ace_execution.PublicExecution.dispatch` 只向内存事件列表追加；`ace_appworld.run_task/ObservedWorld.execute` 在可信侧落盘，generated code 不执行 sink|`ace-appworld-isolated-batch-v2/sources/00_60d0b5b_1/observations.jsonl`：complete_task **200**，原文 `Marked the active task complete.`；execution output 正确为 `TERMINAL_OUTPUT_ONLY\n`，无 not-writable|
|失败在 response_to_json 前抛出而漏记|在 native `Requester.raise_if_failure` 边界，先保存 API 名、实际参数、HTTP status 与 response.text，再调用原生异常处理；不关闭原生异常|`ace-boundary-v5/report.json` 的 apply_promo_code_to_cart **422**，见下方原文；生成程序静默捕获，execution output 仍是 `Execution successful.`|
|主机文件/内部对象可达|生成代码移入已有 bubblewrap/seccomp，加载原生 execute、IPython、SafetyGuard；只经受控公开 API capability 调用可信 remote-APIs|同一 report：sentinel_denied、management_denied、variable_persisted、fresh_variables、reset_public_equal、native_date_equal 均 true；可信 evaluator 执行，success=false|

失败 API 的实际公开响应：

> The minimum cart amount for this promo code is $644.0 but your cart has $634.0. Add more items to qualify for this promo code.

这来自 `432dc7a_2` 的原生公开购物 API，不是数据库判据替代响应。
诊断重用之前从公开邮件取得的调用序列，不执行参考答案、不下单，不向后续真实 actor/updater 提供诊断代码/结论。
原始 trace 中来源 S1 有两次 show_thread；诊断定位首个 apply 调用，不能误把第二封邮件当作失败调用。

必须区分：422 **由 API 返回** → 代码 `except Exception: pass` **捕获但不打印** →
原生执行输出 **不含该错误**。API 日志不会被拼接进 Generator 或 updater history。
此边界诊断没有模型/updater；原生 updater history 的实际捕获另见下面的合成全链路证据。
日志设施自身的 OSError 则直接停止 run，manifest failed，不回传成普通操作失败、不触发 Generator 重规划；
对应回归实际只发生一个合成模型调用，未进入 updater。

## 2. 最终边界与机制影响

```text
可信调度/provider/artifacts/evaluator
  ├─ 官方 AppWorld + Requester ── loopback ── 官方 remote-APIs（数据库/管理）
  └─ 受控管道 ── guest：官方 execute + IPython + SafetyGuard
                     只能发出当前 task 的公开 API capability 请求
```

- `scripts/smoke/ace_api_server.py` 使用固定 fork 的 `build_main_app()`，仅绑定 127.0.0.1；
  使用原生 `/dbs`、日期、seed、保存/清理控制，但**仅可信控制端**可调用它们。
  guest 不知道服务地址、不具备 socket 能力，不是直接开放整个 remote-APIs 服务。
- `ace_execution.py` 的白名单来自当前世界的原生公开 `ApiCollection`，**不是 required_apis**。
  拒绝 admin、私有方法、client/track 与内部参数；防止原生 URL path 参数插值绕到管理路由。
  公开 API 参数与返回仍由原生 Requester/服务处理；默认 dict/list/string，不做有损转换。
  普通 HTTP 失败保留原生 Exception 与公开文本，普通 Python 异常保留原生错误格式及变量状态。
- guest 只读挂载 Python 环境、系统库、独立 bootstrap、固定的 `environment.py` 和静态 common helpers。
  **不挂载项目目录、任务数据、数据库、evaluator、参考解答、研究报告、真实 .env。**
  不运行 AppWorld 包中导入 Task/evaluator 的 `__init__`；preamble 的 Requester/ApiCollection 名称只对应公开能力代理。
- `ace_guest.py` 从固定源 AST **直接加载未改写的 AppWorld.execute**，以及 preamble 到 run_cell 的原生部分；
  保留原生 IPython 输出、语法检查和 SafetyGuard。原生状态持久化移到可信端调用，非放开生成代码写磁盘。
  内部 `/dev/shm` 仅供可信 IPython bootstrap 初始化；生成执行仍受原生写入 guard 和文件大小资源限制。
- 每任务新 guest；同任务保留变量/helper。原生任务日期同步到 guest，API 服务器也使用原生日期/seed=123。
  guest 随机数 seed 固定；这不证明拆分进程后的随机流与旧单进程所有用法完全等价。
- 复用 `CodeSandbox` 的命名空间、清除环境、seccomp、进程组清理：禁网络/新进程/挂载/ptrace 等。
  每块 100 秒真实时钟期限，guest 累计 CPU 120 秒、地址空间 2 GiB、管道消息 1 MiB；
  保留原生每块 1000 API 请求限制，桥接另有 RPC 上限。超时、guest 退出、协议损坏视为设施终止，不重建。
  `sandbox.monotonic` 与 RoleModel 的延迟计时不受 AppWorld 冻结任务时钟影响。
- provider 仅在显式真实执行、首个已检查预算的 transport 调用中加载凭证；guest/server 环境按白名单建立。
  DeepSeek `ProxyHandler({})` 不变。原生 requests Session `trust_env=False`、timeout=30；httpx
  `trust_env=False`。guest 无网络；API server 禁止主动外连。loopback 使用原生 HTTP，外部模型 HTTPS 仍验证 TLS。

**机制差异须保留**：这是受限执行＋remote-APIs 接线，不是原单进程任意 Python 能力完全等价。
未开放读取内部对象、构造任意 Requester 或管理状态的能力；未重写 ACE、AppWorld API/数据或 ADD 算法。
不提供形式化安全证明，也不保证所有未来生成代码的库用法已经覆盖；真实运行遇到设施不兼容即停止，不能现场放宽边界。

原 001/002/003 patches 保留，没有新增上游源码 patch、没有重放/重置 checkout。
新增变化在 adapter/bootstrap；manifest 的 patches 列表另保存这些接线文件的路径、SHA256 与用途。
执行入口检查官方 origin、固定 commit `928e86877d34cd10eaba159606386f93a1765090`，
并检查实际加载的 environment.py 与 pin 一致。无依赖安装/升级，原环境 lock 仍适用。

## 3. 实际离线全链路与限制

最终合成调度产物：`artifacts/ace-appworld-isolated-batch-v2/`。
固定五任务 + I1→M1→M2→I2→I3→M3，**11 个真实任务世界/独立 guest，44 次注入式合成 transport**。
manifest.synthetic=true、scientific_evidence=false；这些并非自然 ACE 学习样本。
环境响应是真的，生成响应及 ADD 内容为 `SYNTHETIC_WIRING_ONLY` 接线 fixture。

|任务|next_global_id before→after|首个 Generator call_id|
|---|---|---|
|60d0b5b_1|9→10|`c246d9bd4c75452599630652abc1e0ff`|
|37a8675_1|10→11|`a4df693e713f4e1ba5701824e0351f96`|
|60d0b5b_2|11→12|`ddd011c50040498b8997fe04fb01debd`|
|432dc7a_2|12→13|`e16dc9f85a66423385f58980f9d3b945`|
|432dc7a_3|13→14|`a52d0d358b044f979a1ee8e64c404852`|
|I1 / M1 / M2 / I2 / I3 / M3|各自 14→15|见各 branches/*/model_calls.jsonl|

前一任务 memory_after 与下一任务 memory_before 的哈希逐项相等；六分支原 K 均为
`08ff5f92c34529e98787a3c2a250f12daddf3fad913b280527e59a6dfb5b7e6c`。
这是**合成** K，禁止用于真实批次初始化。

实际请求核对：I1 首请求 `047ba08994d5418f8b740fb699489180` 与 M1
`280dcc51ec6a4bc29eac8f25d1661b8d` 都有 75 条含原生静态 demonstrations 的 messages；
仅将 I1 一处完整 playbook 替换成 initial 后，messages 与 M1 **完全相等**。
三次 M 的最终 Generator 请求均无学习 fixture；所有分支 Reflector/Curator 请求均保留完整 K。

每任务原生 `update_000001` 保存完整 before/after、ADD 操作和输入/输出引用。
`updater_input.json` 保留真实 trimmed history：前段 `SYNTHETIC_PUBLIC_PREFIX` 在 Output 中；
终段 `TERMINAL_OUTPUT_ONLY` 不在 updater 的 Output 中（代码文字仍在）。未补入终段反馈。
自报 complete 不等于 evaluator success：本 fixture 没解决真实任务，评价失败保留，不拿它冒充成功能力。
max_steps 未完成时，继续维持原生无统一 curator 的边界并停止来源序列。

合成用量 4,400 input / 880 output tokens，估价算术总数 USD **0.002376**，不是收费；
provider_reported_cost_usd=null。真实 LLM/embedding 请求 **0**，真实费用 **0**。
旧 offline-v1/v2、旧诊断和本轮失败版本均不覆盖。边界 v1 为延迟导入错误格式化依赖问题；
v2 为诊断脚本误解 evaluator tuple；v3 为诊断定位第二封邮件而非 apply；v4 修复通过；
v5 另验证 guest 原生日期同步。最终依据 v5 与 isolated-batch-v2，不挑换任务/结果。
v5 evaluator 有原生 traceback 美化 warning，tracker 正常返回；不是评价通过或任务已解决。

## 4. 唯一真实批次及语义边界

`scripts/run/ace_appworld_ab.py`：默认只打印 plan；`--execute` 是真实五任务调度，
不是简单移除旧拒绝语句。每任务新 agent/world/guest，恢复完整官方 playbook+next_global_id；
只有原生持久 memory 顺序继承，角色/执行上下文不串任务。run ledger 全程共享。

五任务固定为上表顺序，seed=123，initial playbook 起步。第五任务后状态为
`awaiting_coding_agent_semantic_review`，不自动决定 B、不另发模型判断请求。
**这不是新一轮用户审批**：获得完整批次授权后，coding-agent 在同一次交付中阅读五任务原文，
尤其两条优惠来源的 API/代码/模型实际可见内容和更新，保存语义判断后继续同一批次或结束 B。
两个命令边界用于让当前 coding-agent 读原文，不是任务故障恢复或补跑入口。

判断文件须含：

- `source_hashes`、`checkpoint_sha256`（从 batch.json 取）；
- `outcome`：`run_branches` / `stop_no_commitment` / `stop_conditional_knowledge`；
- `source_behavior`、`memory_commitment`（具体条目原文/范围）、`behavior_prediction`、`counterevidence`；
- `evidence: [{"path": "sources/.../model_calls.jsonl", "quote": "文件中确实出现的短原文"}, ...]`。

引用必须涵盖实际来源行动/API结果、实际请求、新增记忆，不能仅引 evaluator 成功或预期任务条件。
代码只检查数据哈希/原文引用/配置/ledger一致，不自动评定语义是否正确。
完整条件化比较知识是反向证据，应停止 B；没有可检验承诺也停止。不补写 K、不追加来源或换目标。

满足条件时仅执行目标 `432dc7a_1` 六分支；每次恢复第五任务后的相同完整 K。
Intact 的 Generator 完整 K；`learned-playbook-removed` 仅呈现官方 initial。
Reflector/Curator 持有该分支完整 K，更新不流入其他分支。静态示例/工具/目标不变。
原 checkpoint 与 initial 哈希、来源文件、价格/预算及 ledger 在继续前校验；禁止 synthetic/真实模式混用。

未知费用、身份异常、设施错误、预算拒绝、更新未完整执行均停止，保存当前 task 引用、manifest 和部分 artifacts；
已启动目录拒绝覆盖，stopped/running/completed 批次不能进入语义继续入口。正常任务失败且原生更新完整则继续。

## 5. 预算与准确命令

沿用 docs/22 的 **待批准**峰值价表（官方来源及 2026-09-12 查询记录见 docs/22）：
每百万 hit/miss/output USD 0.006 / 0.30 / 1.20。执行授权时若价格已变化，须先核实，不绕过预留。
请求 `deepseek-v4-flash`；返回只接受 `deepseek-flash`，non-thinking、temperature=0；三角色一致。
无 embedding，CNY task/run 都为 0。未验证 ACE 真实模型兼容性，不单开 probe。

- 每任务 42 次 transport（40 G＋R＋C），run 462 次、最多 11 个任务，零自动网络重试/补跑。
- USD task **3**、run **6**；input task 4,194,304；output task 344,064、每调用 max_tokens=8192。
- 单次按完整 1,048,576 input＋8192 output 预留 **USD 0.3244032**，按可信实际 usage 释放。
  不静默截断 memory/history；余额不足预留则停止。provider 未报告金额保持 null，本地估价不冒充账单。
- 仍无真实 ACE 用量；docs/22 的 USD 0.55–4.10 仅是规划敏感性例子，不是本轮实测预测。

```bash
# 现在可运行；默认不加载世界/凭证、不调用模型
python scripts/direct.py conda run -n memory-ace-appworld python scripts/run/ace_appworld_ab.py

# 以下两步仅在后续一次完整批次付费授权内执行，本轮没有执行
python scripts/direct.py conda run -n memory-ace-appworld python scripts/run/ace_appworld_ab.py --execute --output artifacts/ace-appworld-ab-v1
# coding-agent 立即阅读原文并写 source_review.json；无需另向用户申请中间审批
python scripts/direct.py conda run -n memory-ace-appworld python scripts/run/ace_appworld_ab.py --execute --output artifacts/ace-appworld-ab-v1 --continue-branches artifacts/ace-appworld-ab-v1/source_review.json
```

若 judgment 选择停止，第二条继续入口仅登记停止结果，不请求模型。
批准的是同一上限内五任务＋**条件式**六分支，不是无条件必须跑满。

## 6. 验证与交付范围

全部通过 direct.py；未安装依赖，Python **3.11.16**（memory-ace-appworld），Ruff **0.12.0**（memory-infra）。

```bash
python scripts/direct.py conda run -n memory-ace-appworld env ACE_OFFLINE_TEST=1 PYTHONWARNINGS=ignore python -m unittest discover -s tests -p test_ace_appworld.py -v
python scripts/direct.py conda run -n memory-ace-appworld python scripts/smoke/ace_boundary.py --execute --output artifacts/ace-boundary-v5
python scripts/direct.py conda run -n memory-ace-appworld python scripts/run/ace_appworld_ab.py --offline --output artifacts/ace-appworld-isolated-batch-v2
```

- ACE 相关 **6 tests passed，约 22 秒**；正常返回/真实 output/API 事件、日志设施错误、no-GT 实际模板、
  干预/full K、max_steps、角色共享预算、来源失败停止/禁止重跑。
- 另只运行既有 sandbox 的变量/helper、普通异常恢复、超时清理三个相关测试：**3 passed，约 1 秒**。
- 11 个相关 Python 文件的 Ruff check / format --check、compileall、git diff --check 通过；
  默认 plan 通过。只读核对固定 origin/commit，没有做上游 patch 重放、ALFWorld 运行或全套安装验证。
- 对最终全链路 artifacts 逐项核对 memory 继承、分支源 K、最终角色请求、正常 API/output、终段 history
  及 provider 金额 null：断言全部通过。没有把静态示例/合成 ADD 分析成自然 A/B 证据。

推荐提交上述**一次有条件的 USD 6 批次授权**，不再增加准备轮或独立 probe。
真实首任务兼容性、来源是否形成合格承诺，以及完整任务能力仍待该批实测；隔离结论只覆盖上述实际边界，
不宣称形式化安全、原运行能力完全等价或 H1–H4 成立。
本轮真实模型/embedding 0 次、费用 0；未修改真实 .env/旧 artifacts，未创建 commit。

最终 `git status --short` 摘要：仍为 `M AGENTS.md / README.md / docs/01 / docs/02` 与此前
未跟踪的 configs/scripts/src/tests、docs/03–22 等；新增 docs/23。本轮未改 AGENTS/docs01/docs02，
其既有改动保留。artifacts、third_party、真实 .env 仍被 Git 忽略。
