# ACE online/no-GT + AppWorld：集中接入结果与明确阻塞

后续 review 修复与当前状态见 [docs/23](23_ace_appworld_execution_readiness.md)。
**更正**：本文 offline-v2 的 complete_task 已改变状态，但 API 日志在 SafetyGuard 内写盘失败，
实际执行输出为 `io.UnsupportedOperation: not writable`。因此 completed/ADD 不能证明正常反馈接通；
旧 artifacts 保留不改。docs/23 提供修复后的返回/失败反馈、隔离及完整合成调度证据。

2026-09-12；落实 docs/21，未启动付费批次。**环境、公开 API 比较、官方三角色合成接线已验证；真实执行尚未准入。**
阻塞不是任务不适合或没有官方记忆代码，而是固定 fork 的代码执行限制允许读取主机文件。
遵照 AGENTS §10/19，本轮没有靠删几个属性名掩盖它，也没有另建沙箱平台。

## 1. 固定源码、安装与复现

- 官方仓库：<https://github.com/ace-agent/ace-appworld>，commit
  `928e86877d34cd10eaba159606386f93a1765090`；本地 `third_party/ace-appworld`，detached HEAD。
  使用 fork 自带 AppWorld，不是独立 AppWorld HEAD。
- 新环境 `memory-ace-appworld`：Python **3.11.16**、pip **26.2.1**；AppWorld **0.1.4.dev0**、
  experiments **0.1.0.dev0**。既有 base、memory-infra、memory-automanual 未安装/升级项目依赖。
- 官方 source install 与 `experiments[simplified]` 成功，`pip check`：`No broken requirements found.`
  `configs/ace_appworld/environment.yml`、`environment-lock.json`、`requirements-lock.txt`
  记录环境与全部解析版本，无凭证、私有地址或 editable 绝对路径。
  SDK 等依赖来自官方声明；实际三角色不使用这些 SDK 后端，不新增 embedding。
- 复用 `artifacts/appworld-feasibility-20260912/data-0.1.0.bundle`，34,280,074 bytes，
  SHA256 `fd9f9608c2ec71ed0ac25c3633a738b9129a318a129e31230425b9188e508250`。
  使用官方 `unpack_bundle`，解包至忽略目录；未再次下载数据、改任务或执行参考解答。
- 系统 `git lfs version/pull` 报 Git LFS 无法执行。没有修改全局 Git 配置或安装 LFS；
  从固定 commit 的 `media.githubusercontent.com` 获取四个公开 source bundle，逐一核对
  committed LFS pointer 中的长度、SHA256。Git 因没有 LFS clean filter 显示这四个文件为修改；
  它们是已校验的原始 LFS 对象，不是源码变更。

|原始 source bundle|bytes|SHA256|
|---|---:|---|
|apps|179048|`ed68e817a989a6dc23d9c010f21d874b8cd0420aa9321d9f18a6252da0a7d388`|
|tests|171579|`f851d247dc5a3401e48a74ef29e72376c4d139a13672962e84c192d8aa377620`|
|tasks|160921|`293f514642e9d43297a0a592c4dd16647c889917e1252ea6046ef3ceb31a773d`|
|data-generation|1507078|`eb49a92af1500732afa32767328ac7f5c0ad4ee312c265fc21268a5541ad8eb8`|

### 必要 patches

均在 `configs/ace_appworld/patches/`，未修改原生提示词、ADD 算法、任务数据。

1. **001_explicit_provider_and_generator_view**：取消 AppWorld 两处 import-time dotenv；
   StarAgent 可接受外部三角色实例；Generator 模板从独立呈现属性读取 playbook。
   完整 `self.playbook` 不被清空或临时替换。后一点是登记的实验干预接口，而非记忆算法升级。
2. **002_disk_path_memory_substring**：上游用 `"memory" in path` 识别内存数据库，
   导致本仓库真实磁盘路径 `/…/memory/memory/…` 被误识别，首次世界创建失败。
   在 `apps/model_lib.py`、`collections/models.py` 改为原生 `:memory:` 前缀或 SQLite
   `mode=memory` URL 判断。仅修复存储类型识别，未改变数据库内容或 API 语义。
3. **003_no_implicit_legacy_sdk_import**：ACE 包 `__init__` 会导入未使用的 legacy agent，
   进而导入 LiteLLM。`ACE_EXPLICIT_MODELS_ONLY=1` 时只导入本轮 adaptation 路径，避免
   未用 SDK 的隐式 dotenv、网络价格表和缓存初始化。原 legacy 默认路径不变。

注意：初次合成测试与 offline-v1 先于 patch 003，曾走到 LiteLLM 的隐式 `load_dotenv()`；
后续禁止 dotenv 调用的回归揭示了这个遗漏。没有构造真实模型客户端或使用凭证请求，
没有输出/修改本地凭证；但不能将初次检查描述成已证明“无隐式加载”。最终回归及 offline-v2
直接禁止 `dotenv.load_dotenv`、项目 key loader 与 socket connect，并成功通过。
旧产物保留，不重标记。

实际安装命令（全部经 direct.py；首次 pip 未使用尚不存在的 lock）：

```bash
python scripts/direct.py git clone https://github.com/ace-agent/ace-appworld.git third_party/ace-appworld
python scripts/direct.py git -C third_party/ace-appworld checkout --detach 928e86877d34cd10eaba159606386f93a1765090
python scripts/direct.py conda create -n memory-ace-appworld python=3.11 pip -y
python scripts/direct.py conda run -n memory-ace-appworld python -m pip install --index-url https://pypi.org/simple --retries 0 -e ./third_party/ace-appworld -e './third_party/ace-appworld/experiments[simplified]'
python scripts/direct.py python scripts/setup/ace_appworld.py --fetch-source-bundles
python scripts/direct.py conda run -n memory-ace-appworld python scripts/setup/ace_appworld.py --unpack
python scripts/direct.py conda run -n memory-ace-appworld python scripts/setup/ace_appworld.py --record-environment
python scripts/direct.py conda run -n memory-ace-appworld python scripts/setup/ace_appworld.py --verify-patches
```

重建时按 environment.yml 创建环境，pip 添加 `-c configs/ace_appworld/requirements-lock.txt`；
在任何 AppWorld import 前应用 001，安装/解包后应用 002，ACE 导入前应用 003。
用 `git -C third_party/ace-appworld apply <patch绝对路径>` 重放；不要覆盖已有 checkout。
`--verify-patches` 在临时目录从原 commit 恢复相关文件并依次重放三个 patch，
与当前文件逐字节一致；不 reset/clean 现有上游。`--unpack` 拒绝替换已有数据目录。

## 2. 真实零模型环境与公开证据

最终产物：`artifacts/ace-appworld-diagnostic-v3/`。所有请求为原生本地 ASGI API，socket connect 被阻止。
httpx 明确 `trust_env=False`、requests Session 明确 `trust_env=False`；无代理、无 TLS 绕过。
诊断不是自然 Agent 轨迹，不向之后的 Generator/Reflector/Curator 提供诊断代码或结论。

简单真实任务 `60d0b5b_1` 执行 `show_active_task` 和自报 `complete_task`，evaluator 执行成功：
**agent_completed=true，evaluator.success=false（7 项中 1 pass、6 fail）**。
这是特意未执行退款的最小接口诊断，验证“自报完成≠任务成功”，不是声称解题成功。
没有读取/运行参考解答来制造通过。

优惠证据路径：公开 supervisor profile/password API 登录模拟账户 → Gmail
`show_inbox_threads(query='Amazon', sort_by='-created_at')` → 从公开 subject 筛选促销邮件并
`show_thread` → 从最新邮件正文取候选码 → Amazon `show_cart` → apply 新码 → show_cart →
恢复旧码 → show_cart。未从研究侧 DB 提供优惠码。
模拟账户凭据仅存在被忽略的本地原生日志，不能公开分发解密数据/轨迹。

|任务|旧方案总价|尝试新码后的公开结果|恢复语义|
|---|---:|---|---|
|S1 `432dc7a_2`|588.40|422：最低购物车金额 644，当前 634；仍为旧方案 588.40|旧码没有被替换；再 apply 旧码返回 already applied，购物车完全一致|
|S2 `432dc7a_3`|459.90|新码有效，替换后 498.90|可重新应用旧码，恢复 459.90|
|T `432dc7a_1`|345.00|新码有效，替换后 315.00|可重新应用旧码，恢复 345.00|

金额单位是模拟购物 API 的美元，不是模型 API 费用。包括 API 返回的配送费与税，不只比较面额。
S1 的 after_apply.promo_valid=true 指**仍然保留的旧码**，不能当作新码有效。
三个 `comparison.json` 及 `public_trace.json` 保存了完整响应；诊断未下单，不声称配送/支付全链路已验。
S1 的 workplace 与 S2/T 的 home 指令差异仍保留。

目标创建独立世界、seed=123，重复上述公开路径：两份 `public_trace.json` 的 **9 个执行块代码与
输出逐项相同**，购物车/候选/错误或成功响应/恢复比较也相同；首次分歧无。
只证明该目标、该 API 路径的 reset，不证明所有状态或整个 AppWorld 确定性。

失败记录未删：diagnostic-v1 在世界创建时触发磁盘路径误判；v2 环境已运行，但最初的候选码正则
错误假设全大写长码，未能解析公开邮件。v3 改为公开 `Promo Code =>` 字段并按日期选择最新邮件。
没有换任务、改数据或凭试跑效果挑优惠；这些均为零模型接线修复。

## 3. no-GT 实际数据流与执行隔离是两个结论

以下位置为固定 commit 加声明 patches 后的文件/函数；核心 no-GT 控制流未修改。

|数据/控制流|实际消费与证据|
|---|---|
|任务描述、supervisor、app descriptions|`adaptation_react.py:48 initialize` 渲染官方 Generator 模板；静态 demonstrations 原样保留|
|required_apis|在 initialize 的模板参数中读取，但模板不引用；最终消息 sentinel 检查不出现。不是因为变量叫 no-GT 就放行|
|参考解答|`solve_task_wo_gt` 传 gt_code=None；没有走 `solve_task_with_gt`。模板注入 synthetic solution sentinel 后仍不进入实际 Reflector/Curator 请求|
|评价报告|`adaptation_agent.py:158 solve_task_wo_gt` 在自报结束后 evaluate，再 curator；报告确实在对象中，但 no-GT reflector 和 curator 模板没有对应插槽。最终请求 evaluator sentinel 不出现|
|完成判定|`environment.py:756 task_completed` 查询 supervisor active-task 状态，是程序自报；不等于隐藏 evaluator 的 success|
|执行 history|`adaptation_react.py:67` 只在下一次 Generator 决策加入上一轮 output；`trimmed_messages` 保留原生截断方式|
|终段输出|最后代码执行后若自报完成，直接 evaluate/curator，**没有追加最后 output**。不补写；updater_input 标记 terminal_output_supplemented=false|
|max_steps|原生最多 40 Generator 轮；未自报完成且到达上限，不统一 curator/evaluate。记录 max_steps_without_update；不是正常完整更新任务失败，不应继续来源序列|
|原生维护|`curator_call:269` 校验 ADD-only，`playbook.py apply_curator_operations` 原样执行，保存文本与 next_global_id；不擅自实现 UPDATE/MERGE/DELETE|

静态 Curator 提示仍说 reflection 使用了 ground truth；这是原生文字与 no-GT 实际路径不一致，
**不等于实际 GT 泄漏**，也不能假定模型不会受这句文字影响。本轮未改提示词。

### 已证实的执行阻塞

`SafetyGuard.is_syntax_safe` 允许 pathlib/appworld 等模块；`SafetyGuard.enable` 的文件保护主要禁止写入，
`Path.read_text` 未被禁止。真实 `world.execute` 执行以下代码读到了临时 sentinel：

```python
from pathlib import Path
print(Path("<temporary-sentinel-directory>/hidden.txt").read_text())
# 实际返回 SYNTHETIC_HIDDEN_SENTINEL
```

只探测自建临时文件，没有试读真实 .env、真实凭证、任务答案或隐藏数据库。
这已足以否定“上游 guard 能阻止任意主机文件读取”；不能因为普通 socket 在诊断中被 mock 禁止，
就声称远程模型代码已完成 OS 隔离。AppWorld/Requester/任务元数据与生成代码同进程，
更深内部对象路径也没有得到隔离证明。本轮 **不准入真实模型代码执行**。

最小后续选择是评审并接通**上游现有 remote-APIs 边界**：可信进程持有数据库/evaluator；
代码进程不挂载任务/项目/凭证，限制联网仅到可信公开 API 代理，复用已有 OS 级限制。
需要验证正常公开 API、生成代码变量持久化和最终评价，不能只在环境变量中去掉 key。
本轮没有实现这层，也不声称几个名字过滤就能替代它；如果不接受此执行边界改动，则停在诊断载体。

## 4. 三角色接线、干预与 artifacts

实现 `src/memory_validation/adapters/ace_appworld.py`，调用官方类与原生 `solve_task`；
仅替换模型入口与观测回调。没有同名重写 Generator/Reflector/Curator 的记忆算法。

- `RoleModel` → 现有 DeepSeekProvider/UsageTracker/RunLedger；逐次 request/response/usage 同一 call_id、role phase。
  不走上游 LiteLLM/Sambanova 的硬编码示例凭证、结果缓存或 SDK 重试；真实 HTTP 类继续 ProxyHandler({})。
- snapshot 为官方完整 playbook 文本＋next_global_id。restore 验证 next ID，不重新编号。
- `learned-playbook-removed`：Generator 只呈现官方 initial playbook；Reflector/Curator 持有完整原 K。
  分支之间独立对象/副本；不修改 checkpoint，静态示例/工具/任务一致。不是完全无记忆，也不是单条优惠记忆净效应。
- 每任务 sink 保存实际 code/output、公开 API 转换响应、模型请求/返回、独立 evaluator、updater 请求引用、
  原生 ADD 操作、完整 before/after/diff。API 返回过但未打印的内容单独标为不一定 model-visible。
  原生失败在 response_to_json 前抛出时以执行错误 output 保存，不能声称每次失败都有结构化 API response。
- 一个原生 reflector/curator 区间对应 `update_000001`；max_steps 路径无区间，evaluator 保持 unavailable。
  不将最后任务 memory 猜作未执行更新，不增加摘要/额外角色请求。

最终离线产物 `artifacts/ace-appworld-offline-v2/`：

|角色|call_id|性质|
|---|---|---|
|Generator 1|`bcc42f36128e4bd596c49b6aedab18ed`|合成可见前缀|
|Generator 2|`73dec0eb2ef544f4ba85a338e3ef7517`|合成终段代码，自报完成|
|Reflector|`b779a57ca63c4ed6a021e3fe57ec0345`|真实原生请求＋合成响应|
|Curator|`11aa8fb8bd104fc0bd562bd679791c56`|原生 ADD synthetic fixture，非自然学习记忆|

4 次**注入式合成 transport**，400/80 synthetic input/output tokens；算术估计 USD 0.000216
只是合成记账回归，**真实模型请求 0、费用 0**。provider 金额 null，不是实际账单。
memory 中 SYNTHETIC_WIRING_ONLY 不得用于任何实验初始化。
terminal output 在 observations 可见，但不在 updater 的 Output 消息中；生成代码文字中仍有对应 print，
不能把“看到代码”误报为“看到了执行结果”。

## 5. 唯一后续批次（待执行隔离与新授权）

默认计划入口已可运行；`--offline` 可运行上述固定合成接线；**`--execute` 明确退出 2，且在创建
任何真实 transport/key loader 之前阻止。它目前不是已完成的付费批次执行器。**
来源顺序与条件式六分支的完整付费调度尚未开放，不把 plan 输出称为已验证的十一任务闭环。

固定方案不变：

1. `60d0b5b_1 → 37a8675_1 → 60d0b5b_2 → 432dc7a_2 → 432dc7a_3`，seed=123。
   官方 initial playbook 开始，真实顺序继承；新任务独立世界，A 与 B 来源共用，不另跑校准。
2. 五任务后人工逐条读实际消息/API/新增条目，保存 semantic decision：是否自然形成具有可检验
   行为预测的承诺。没有则结束；清楚条件化的完整比较知识是反向证据，不硬凑 B。
3. 条件成立且额度足够时，目标 `432dc7a_1`，I1→M1→M2→I2→I3→M3。
   每次独立恢复第五任务后的同一 K；Generator 呈现干预，updater 仍完整原 K；更新不串分支。
4. 不追加来源、补记忆、换目标或付费重跑。test-challenge 任务标为探索性机制研究，非未见测试。

判据：A 分析资金/身份/金额/条件知识的事实与集合协调；B 分别记录新促销是否从邮件发现、
是否取得旧/新有效性及总价、程序是否比较、模型是否看见结果、是否选用适当方案、实际成交/配送结果。
最终评价与 API 探索成本分开，拿到信息但未比较不能叫“无法取得证据”；最终正确也不单独证明集合可靠。
updater 实际 history 中没有的终段信息不得用于指控其忽略证据。只有干预影响行为/证据且对应更新有联系，
才进一步讨论 A+B，不提前铺开 H4。

### 本次重新核价与预算建议（未获付费授权）

2026-09-12 通过 direct.py + ProxyHandler({}) 读取
[DeepSeek 官方价格页](https://api-docs.deepseek.com/quick_start/pricing/)：
峰值每百万 cache-hit/cache-miss/output **USD 0.006/0.30/1.20**；保守使用峰值，不扣免费额度。
官方说明旧 request 名 `deepseek-v4-flash` 仍接受，但实际由 **DeepSeek-V4.1-Flash** 服务。
请求仍固定旧登记名，返回只接受 `deepseek-flash`；non-thinking、temperature=0。
这是公开文档核实，不是 ACE 实际 API 兼容性验证；首次真实来源任务应兼做兼容性检查，无额外 probe。

|限制|task|整个登记批次|
|---|---:|---:|
|transport（全部角色）|42（40 Generator＋1 Reflector＋1 Curator）|462，最多 11 次任务|
|输入 tokens|4,194,304|由 11 个 task cap 给出结构上限 46,137,344；同时受 USD 上限阻断|
|输出 tokens|344,064；每调用 max_tokens=8192|结构上限 3,784,704；同受 USD 限制|
|USD 硬上限|3|6|
|CNY/embedding|0；本路径不需要 embedding|0|
|自动网络重试、补跑|0|0|

每次预留整个 1,048,576 input＋8,192 output，按峰值全 miss 为 **USD 0.3244032**；
不是字节/token 猜测。预留按请求逐次释放为可信 usage，不将 462 份预留同时锁死；
剩余额度不足单次保守预留则干净停止，不能强行花到 USD 6。输入 task cap 同样要容纳当前整次预留，
因此可能提前停止，不静默截断实际 memory/history。
8192 output cap 是新增预算限制，不保证所有 Curator 输出不会截断；正式执行需明确记录这一限制。

无 ACE 实测模型用量，不能照搬 ALFWorld 费用。仅用于规划的敏感性例子：
每任务 12–27 次全角色请求、平均输入 10k–30k/output 1k–4k，11 任务峰值全 miss 估计
**USD 0.55–4.10**；不是置信区间或已测预测。实际原生上下文可能超出这些假设，硬上限优先。
所有角色统一 ledger，逐任务 tracker 重新计数；未知 usage/费用、模型身份缺失或变化、设施异常、
预算中止、原生更新无效/未执行均停止后续调用。正常自报结束且原生更新完整、但 evaluator 失败的任务保留并继续。

命令：

```bash
# 可运行，不加载凭证/世界：
python scripts/direct.py conda run -n memory-ace-appworld python scripts/run/ace_appworld_ab.py
# 可运行，固定合成接线；新目录，不能复用旧输出：
python scripts/direct.py conda run -n memory-ace-appworld python scripts/run/ace_appworld_ab.py --offline --output artifacts/ace-appworld-offline-NEW
# 当前故意返回 2；不是本轮授权的付费执行：
python scripts/direct.py conda run -n memory-ace-appworld python scripts/run/ace_appworld_ab.py --execute
```

## 6. 验证、遗留边界与推荐

相关检查实际完成：

- `ACE_OFFLINE_TEST=1 PYTHONWARNINGS=ignore python -m unittest discover -s tests -p test_ace_appworld.py -v`
  （经 direct.py、conda memory-ace-appworld）：**4 tests passed，约 5 秒**。
  覆盖最终 no-GT/干预消息、source 不变、原生终段 history/ADD/evaluator 区分、max_steps 无更新、
  全角色共享 ledger 的发送前阻断。测试禁止 socket、dotenv 与项目 key loader；未跑无关全套。
- offline-v2：原生三角色＋真实世界的合成接线完成；公开 API diagnostic-v3 完成；没有模型调用。
- 原 pin＋全部 patches 临时重放与逐字节校验通过；不是拿修改后的 checkout 冒充原 pin。
- 五个新 Python 文件的 Ruff check、format --check、compileall 通过；`git diff --check` 通过。
- memory-ace-appworld `pip check` 通过；只读核对目标两次完整公开 trace，9 块相同。
- 默认 plan、显式 execute 的拒绝路径分别 exit 0、exit 2；拒绝发生在凭证加载之前。

没有验证真实 DeepSeek 在 ACE 长消息/长代码下的效果；没有自然 ACE 学习 K；没有实跑五任务/六分支；
没有验证最终下单/配送成功；没有证明原生执行安全隔离。本轮真实 LLM/embedding 调用均 **0**、费用 **0**。

**推荐：保留已核实的 AppWorld A/B 任务组，不再选 benchmark；先评审一个具体的公开 API 执行进程边界，
再接通付费序列。** 这不是改变 no-GT 协议或放宽读取权限的请求。当前不能推荐直接授权付费批次：
明确的文件读取通路尚未隔离。若继续，第一任务兼容性＋五任务 A/来源＋条件式六分支仍应合并为原计划，
不另开一轮探针或扩大采样。

本轮改动：上述 adapter、setup/smoke/run 三个入口、一个测试文件、ACE configs/locks/三 patches、
本文和 README/docs21 索引状态。原有大量未提交改动保留；未修改旧 artifacts/.env，未创建 commit。
最终 Git 摘要仍为原先 4 个 tracked 文件修改（AGENTS、README、docs01、docs02）与既有 untracked
目录/文档，新增 `docs/22_ace_appworld_preparation.md`；本轮新增 ACE 文件均在原已 untracked 的 configs/src/scripts/tests 内。
artifacts、third_party、真实 .env 保持被忽略。
