# Phase 1 Gate B1 Failure Trajectory Diagnosis

更新时间：2026-09-20
分支：`exp/minimal-exploratory-memory-validation`
基线结果 commit：`4216a8b14762bc2c304992f797cb5d515545074a`

本轮只做人工、逐轨迹、逐步诊断，不调用模型/API，不重跑 Gate B1，不修改
actor prompt、K*、actor、step cap、task membership、gate threshold、B/C/H/A 或
Phase 1 registry。

## 1. Evidence scope and review method

主要证据是本地保存的唯一协议一致 scientific run：

```text
artifacts/exploratory_memory_mvp/gate-b1-qwen38-c1-20260919-ef44ff2-automanual
```

我直接读取了 10 个 task 的：

```text
initial_state.json
run_config.json
每一步的 actor_input.json / actor_prompt.json
actor_parsed.json / actor_raw_response.json
action_validation.json / step.json / environment_result.json
execution.json / episode_summary.json
```

第一轮 `CarrierUnavailable` artifact 没有模型调用，不作为 actor evidence，也没有
纳入本诊断。

### 1.1 实际 actor-visible representation

每一步的 `actor_input` 实际包含：

```text
current_task:
    instruction, task_id, seed
current_state:
    latest observation, ordered admissible_actions, done, won
executed_action_history:
    已执行的 action string 列表
pre_update_established_memories:
    四条 K* memory
probe_runtime_state:
    机械计数/visited telemetry；C1 中 H 未激活
```

其中 `executed_action_history` 只保存动作字符串，不保存逐步的历史 observation、
历史 action result、物品状态快照或显式的 `SEARCH / OBJECT_ACQUIRED / NEED_COOL`
等 phase。actor 每一步能看到最新 observation，但不能从一个结构化
`observation_history` 字段直接回看之前每个容器的内容。

冻结 prompt 中与本诊断最相关的原文是：

```text
Use the task instruction and established memory to finish the original task.
```

以及：

```text
Read current_state.admissible_actions in the exact order provided. Choose
exactly one entry by returning its zero-based action_index.
```

K* 的通用搜索 guidance 是：

```text
Search visible receptacles in the order presented in the room observation.
At each location, navigate to the receptacle, open it if closed, and inspect
for the requested object. Once the target object is located, take it and
carry it directly to the specified destination receptacle.
```

相关 clean/cool/heat guidance 也同时出现在每一步输入中。这里没有 hidden
reasoning 可供检查；模型输出是可见的 JSON `action_index` 和 `probe_status`。

## 2. Ten-task overview

| task | family | outcome | steps | first meaningful divergence / control note |
|---|---|---:|---:|---|
| `pick_and_place_simple-Laptop-None-Desk-306` | simple | success | 11 | control；先拿到 distractor cellphone 后恢复 |
| `pick_clean_then_place_in_recep-Knife-None-DiningTable-26` | clean | step cap | 32 | step 4 重访已空的 `cabinet_1`；step 7 在尚未拿到 knife 时进入 sink |
| `pick_cool_then_place_in_recep-Mug-None-Shelf-1` | cool | step cap | 32 | step 16 在 `cool mug_2 with fridge_1` 可用时选择 `put`；之后无法继续 cooling |
| `pick_heat_then_place_in_recep-Apple-None-Fridge-20` | heat | success | 25 | control；microwave 前连续 `look` 后仍恢复并完成 |
| `pick_heat_then_place_in_recep-Potato-None-CounterTop-15` | heat | step cap | 32 | step 5 拿错 `soapbottle_2`，且该远端 take action 在当前 action list 中合法 |
| `pick_cool_then_place_in_recep-Mug-None-CoffeeMachine-30` | cool | step cap | 32 | step 2 面对 closed `cabinet_1` 选择 `inventory`，随后未建立 search progress |
| `pick_clean_then_place_in_recep-SoapBar-None-Cabinet-428` | clean | success | 13 | control；search、clean、downstream placement 切换清楚 |
| `pick_clean_then_place_in_recep-DishSponge-None-Cart-430` | clean | success | 21 | control；先处理 cloth，之后仍能切换到 dishsponge 并完成 |
| `pick_clean_then_place_in_recep-Cup-None-Shelf-20` | clean | step cap | 32 | step 4 在 closed `cabinet_2` 选择 `look`；step 5–11 形成 cabinet loop |
| `pick_heat_then_place_in_recep-Potato-None-Fridge-27` | heat | step cap | 32 | step 5 重访已空 `cabinet_1`；step 9 后连续 `inventory` |

artifact 中每一步的 action index 均通过机械验证；本轮没有发现 action-index 映射或
执行层面的 invalid action。

## 3. Six failure deep reviews

### 3.1 Knife → DiningTable

Task：

```text
pick_clean_then_place_in_recep-Knife-None-DiningTable-26/
trial_T20190908_133611_882723
```

Family：`pick_clean_then_place_in_recep`
Outcome：step cap，未获取 knife，未 clean，未 placement。
Artifact：

```text
.../tasks/001_f5d0f35d6dfd/c1_rep00/
```

#### Trajectory summary

模型先执行：

```text
1 go to cabinet_1                 -> cabinet_1 empty
2 go to cabinet_10                -> cabinet_10 closed
3 open cabinet_10                 -> cabinet_10 empty
4 go to cabinet_1                 -> cabinet_1 empty again
5 examine garbagecan_1            -> tomato_1
6 go to diningtable_1             -> no knife
7 go to sinkbasin_1               -> no knife
8 go to diningtable_1             -> no knife
9 go to sinkbasin_1               -> no knife
```

之后又在 `cabinet_1`、`cabinet_10`、`diningtable_1`、`sinkbasin_1` 之间往返；
step 23 以后打开了没有目标的 fridge，最后 step 28–32 连续 `look`。

#### First meaningful divergence

* step：4
* public state：最新 observation 是 `You open cabinet_10. In cabinet_10, you see nothing.`；
  `current_state.admissible_actions` 中同时有 `go to cabinet_2`、其他未访问 cabinet、
  `go to sinkbasin_1` 等动作。
* model action：`action_index=2`，resolved action 为 `go to cabinet_1`。
* why problematic：`cabinet_1` 刚刚已经被观察为空；这使 search progress 从“检查下一个
  候选”变成了已知空容器重访。step 7 是更明确的 phase violation：history 中没有拿到
  knife，dining table 也没有 knife，但模型直接去 sink 执行 clean routine 的前置地点。

Could a reasonable actor infer the correct local direction from visible input? **YES，带有
representation caveat。** task instruction、最新 empty observation、action list 和 raw
action history 都支持继续 search；但 history 没有保存先前 observation 的结构化记录，
也没有 visited/empty-candidate summary。

#### Causal assessment

K* 的 search guidance 没有直接要求去 sink；clean guidance 也以“After acquiring the
target object”开头，因此没有证据表明 K* 明确诱导了 step 7。更像是模型没有维持
当前 `SEARCH` phase 和“尚未拿到 object”的事实。

模型选择的是合法 action，prompt 也明确要求读 task、memory 和 current state。因此
这是 model-side local decision failure 的证据，但不是纯模型能力证据：长 action list、
只有 action-string history、缺少结构化 search progress 都能解释相同偏离。

* Primary bottleneck hypothesis：search progress / current phase 没有被稳定保持，导致
  actor 反复选择可见但无进展的 receptacle。
* Alternative explanations：长上下文下的 qwen3.8-flash 搜索能力不足；模型把
  `go to sinkbasin_1` 错当成 clean routine 的合理下一步；ALFWorld 容器反馈与 raw
  action history 的组合不利于长期搜索。
* Evidence supporting：step 4 重访空 cabinet；step 7 在无 knife 时去 sink；step 19–22
  明确 `sinkbasin_1 ↔ diningtable_1` 往复；step 28–32 连续 `look`。
* Evidence against：没有 invalid action；并非所有任务都不能进行多阶段切换，SoapBar
  和 DishSponge 成功完成了 clean/placement。
* Model-only fix plausibility：**POSSIBLE**，但不能从此 trace 单独确认。
* Prompt/state representation fix plausibility：**LIKELY**，至少应是需要控制的混杂因素，
  但本轮不修改。
* Confidence：**MEDIUM**。

### 3.2 Mug → Shelf（cool）

Task：

```text
pick_cool_then_place_in_recep-Mug-None-Shelf-1/
trial_T20190908_073555_430020
```

Family：`pick_cool_then_place_in_recep`
Outcome：已找到 mug 并送到 fridge，之后未完成 cooling/retrieval/placement。
Artifact：

```text
.../tasks/002_a04b6f263f6d/c1_rep00/
```

#### Trajectory summary

search 阶段虽然有 cabinet 重访，但最终：

```text
10 go to cabinet_8
11 open cabinet_8             -> mug_2, soapbottle_2, vase_2
13 take mug_2 from cabinet_8
14 go to fridge_1
15 open fridge_1
16 put mug_2 in/on fridge_1
```

关键是 step 15 和 16 的 actor-visible action list：

```text
cool mug_2 with fridge_1
...
put mug_2 in/on fridge_1
```

模型选择了 `put mug_2 in/on fridge_1`。其后的 observation 仅为
`You put mug_2 in/on fridge_1.`；step 17 的 action list 已不再包含
`cool mug_2 with fridge_1`，只包含从 fridge 取出 mug 的 `take` action、导航、
`inventory` 和 `look`。模型随后执行 `inventory / look`，step 24 在没有携带 mug 的
情况下去 `shelf_2`，最后继续停滞。

#### First meaningful divergence

* step：16（step 17 是该偏离的显性后果）
* public state：目标 mug 已被获取，agent 在 open fridge 前；task 明确要求 cool，
  action list 同时提供了显式 `cool mug_2 with fridge_1` 和 `put mug_2 in/on fridge_1`。
* model action：选择 `put mug_2 in/on fridge_1`。
* why problematic：在 pinned ALFWorld 语义下，`put` 不是这个 episode 中可继续触发
  cooling 的 action；真正的 cooling action 在放入之前可用，放入后消失。

Could a reasonable actor infer the correct local direction? **UNCLEAR。** 仅看 task 和
action list，选择显式 `cool` 是合理的；但冻结 K* 的 guidance 是“navigate to a fridge,
open it if closed, place the object inside to cool it, then retrieve it”，没有明确要求
调用 `cool ... with fridge`。模型的 `put` 选择实际上是对 K* 字面 guidance 的合理执行，
而不是任意违反任务。

#### Causal assessment

这是本轮最强的 K*/environment/action-semantics confound：K* 的自然语言 realization
与 ALFWorld 的显式 action contract 不一致。它不能被写成“Qwen 不理解 cooling”而不
控制这个差异。

* Primary bottleneck hypothesis：frozen K* 的 cool routine 与载体 action semantics
  不一致，导致 actor 在正确目标已获取后选择了不可完成后续 cooling 的 realization。
* Alternative explanations：模型看到了 `cool` 仍没有选择；`put` 与 `cool` 的先后
 关系对模型不清楚；最新 observation 没有显式声明 object 的温度/冷却状态。
* Evidence supporting：step 15/16 的 exact action list；step 16 后 `cool` action 消失；
  actor 已在 step 13 正确获取目标，说明 failure 不是初始 search 全部失败。
* Evidence against：Apple 成功 case 也有类似的 heat action/state ambiguity，但模型最终
 选择了 `heat apple_3 with microwave_1` 并完成；因此该混杂因素不是每次必然失败。
* Model-only fix plausibility：**POSSIBLE**，但不能优先于修正/隔离这个 contract
  confound 来判断。
* Prompt/state representation fix plausibility：**LIKELY**。
* Confidence：**HIGH**（关于存在语义混杂）；**MEDIUM**（关于单独占失败主因的程度）。

### 3.3 Potato → CounterTop（heat）

Task：

```text
pick_heat_then_place_in_recep-Potato-None-CounterTop-15/
trial_T20190908_231700_114762
```

Family：`pick_heat_then_place_in_recep`
Outcome：未获取 potato；携带了错误的 `soapbottle_2`；step cap。
Artifact：

```text
.../tasks/004_6b27915dcc20/c1_rep00/
```

#### Trajectory summary

```text
1 go to cabinet_1              -> empty
2 go to cabinet_11             -> closed
3 open cabinet_11              -> empty
4 go to coffeemachine_1        -> empty
5 take soapbottle_2 from countertop_1
6 go to fridge_1               -> closed
7–10 look                      -> unchanged closed fridge
11 open fridge_1               -> bowl, plate; no potato
14 go to sinkbasin_1           -> potato_4, potato_2, tomato_1 visible
17 go to countertop_1          -> potato_1 visible
```

step 5 的 current observation 是 `You arrive at loc_24. On coffeemachine_1, you see
nothing.`，但 ordered action list 同时包含：

```text
take potato_1 from countertop_1
take soapbottle_2 from countertop_1
```

而且 `take soapbottle_2 from countertop_1` 在当前状态被 harness 判定为合法并执行，
尽管 actor 当时的局部 observation 是 coffeemachine。这是一个重要的 carrier action
affordance 特征：action list 不是只列当前 receptacle 的动作。

#### First meaningful divergence

* step：5
* public state：task 明确为 heat potato；当前 observation 没有 potato，也没有
  soapbottle；action list 有 `go to countertop_1`、`take potato_1 from countertop_1`
  和多个 distractor take actions。
* model action：选择错误对象 `soapbottle_2`。
* why problematic：从这里开始 inventory 与目标 task 不一致；后续到 countertop 时
  target potato 虽然公开出现，模型已经携带错误物品且没有恢复。

Could a reasonable actor infer the correct local direction? **YES，但有明显 carrier
ambiguity。** task/object identity 足够明确，`take potato_1` 也在 admissible list；但
`take` 远端对象在非当前 receptacle observation 下直接可执行，使错误 object 具有和
正确 object 一样的 mechanical legality。

#### Causal assessment

这是 model object-grounding failure 与 action affordance representation 混合的案例，
不是 action-index/harness execution error。模型选择的 action 合法、可执行，但 semantic
上与 task 冲突；同时环境把远端 take actions 暴露在当前 action list 中，增加了错误
选择空间。

step 7 还提供了第二个证据：fridge closed 且 `open fridge_1` 在 list 中，模型先连续四次
`look`，直到 step 11 才打开。step 17 已看到目标 `potato_1`，但仍然只 inventory、
回 fridge、examine；这说明错误对象提交后没有稳定的 task-phase recovery。

* Primary bottleneck hypothesis：object identity 与 current task phase 没有被可靠绑定；
  global admissible take actions 使这一缺陷显性化。
* Alternative explanations：模型在长 action list 上选择 token/index 近邻 distractor；
  qwen3.8-flash 对 ALFWorld 的 remote take semantics 不可靠；K* generic search 没有
  给出当前 object binding 的结构化支持。
* Evidence supporting：step 5 直接选错 object；step 7–10 对 closed fridge 重复 look；
  step 17 观察到 potato 后仍未获取它。
* Evidence against：Apple、SoapBar、DishSponge 都能从公开对象列表中选出正确目标，
  所以不是所有 object grounding 都失败。
* Model-only fix plausibility：**POSSIBLE**。
* Prompt/state representation fix plausibility：**LIKELY/POSSIBLE**，尤其是如果保留
  global action list，就需要更清晰的目标/位置/当前 task phase 表达；本轮不修改。
* Confidence：**MEDIUM**。

### 3.4 Mug → CoffeeMachine（cool）

Task：

```text
pick_cool_then_place_in_recep-Mug-None-CoffeeMachine-30/
trial_T20190907_153036_598316
```

Family：`pick_cool_then_place_in_recep`
Outcome：未获取 mug；step cap。
Artifact：

```text
.../tasks/005_6cf8b7e81791/c1_rep00/
```

#### Trajectory summary

该 task 的初始 admissible list 很长（包含 13 个 cabinet、27 个 drawer 以及多个
appliance）。trajectory 是：

```text
1 go to cabinet_1       -> cabinet_1 closed
2 inventory             -> empty
3 go to stoveburner_2   -> kettle_2
4 go to coffeemachine_1 -> mug_1
5 inventory             -> empty
6 go to fridge_1        -> fridge_1 closed
7–13 inventory          -> empty
14 go to stoveburner_2
15–16 inventory
17 go to fridge_1
18–32 inventory
```

#### First meaningful divergence

* step：2
* public state：observation 是 `cabinet_1 is closed`；admissible list 中有
  `open cabinet_1`，而 task 仍是寻找需要 cooling 的 mug。
* model action：`inventory`。
* why problematic：inventory 不能推进 search，随后模型去 stoveburner 和
  coffeemachine，但没有建立任何 candidate inspection；在 step 7 的 closed fridge
  处又选择 inventory 并进入长时间停滞。

Could a reasonable actor infer the correct local direction? **YES，带有长 action-list
和 history representation caveat。** 立即的 `open cabinet_1` 是清楚的，但 task 的
目标 mug 可能藏在大量 cabinet/drawer 中，current input 没有 candidate bookkeeping 或
phase summary。

#### Causal assessment

这里没有像 Cool/Shelf 那样直接观察到 K* realization 与 carrier command 的冲突；
K* 的 search guidance 与任务方向一致，但模型没有执行 open/search。故不能把 cool
family 的两次失败都归结为 cool semantics：本 case 在 cooling routine 之前就失败了。

* Primary bottleneck hypothesis：长候选空间下，actor 没有保持 SEARCH subgoal，
  `inventory` 成为低成本但无进展的默认动作。
* Alternative explanations：模型能力/上下文负担；没有历史 observation 或 visited
  summary；ALFWorld 把大量 drawer/cabinet 导航都暴露给 actor。
* Evidence supporting：step 2 在 closed cabinet 上选择 inventory；step 7–13 和
  step 18–32 连续 inventory；task instruction 没有被改变。
* Evidence against：当前 observation 和 action list 对打开 closed container 是清晰的；
  其他成功 case 能进行 search。
* Model-only fix plausibility：**POSSIBLE**。
* Prompt/state representation fix plausibility：**POSSIBLE/LIKELY**，但还没有一个
  isolated test 把两者分开。
* Confidence：**MEDIUM**。

### 3.5 Cup → Shelf（clean）

Task：

```text
pick_clean_then_place_in_recep-Cup-None-Shelf-20/
trial_T20190909_150437_976767
```

Family：`pick_clean_then_place_in_recep`
Outcome：未获取 cup；之后拿错 lettuce，step cap。
Artifact：

```text
.../tasks/008_622e1e897f57/c1_rep00/
```

#### Trajectory summary

```text
1 go to cabinet_1       -> closed
2 open cabinet_1        -> empty
3 go to cabinet_2       -> closed
4 look                  -> still closed
5 go to cabinet_1       -> empty
6 go to cabinet_2       -> closed
7 open cabinet_2        -> empty
8–11 cabinet_1/cabinet_2 ping-pong
12 go to countertop_1
13 go to diningtable_1
14 take lettuce_1 from diningtable_1  (wrong object)
15–18 sink/fridge navigation
19–24 shelf_1/shelf_3/shelf_2 loop
```

#### First meaningful divergence

* step：4
* public state：`cabinet_2 is closed`，admissible list 明确包含 `open cabinet_2`。
* model action：`look`。
* why problematic：look 没有改变 closed state；下一步模型离开到 cabinet_1，再回来，
  形成后续 loop。step 7 最终打开 cabinet_2，但两个 cabinet 都空后仍在 step 8–11
  重复它们，没有进入未访问候选。

Could a reasonable actor infer the correct local direction? **YES。** task、closed
observation、`open cabinet_2` action 和 K* search guidance 一致。长 action list 与缺少
历史 observation summary 仍是可能的 representation confound。

step 14 是第二个重要偏离：dining table observation 显示 `lettuce_1` 以及许多对象，
但 task 目标是 cup，模型选择了 `take lettuce_1`。从该点开始后续 clean routine 作用于
错误对象；actor 没有在后续 history/state 中恢复目标绑定。

* Primary bottleneck hypothesis：局部 closed-container decision 后，actor 没有维护
  candidate progress；随后在开放表面上又发生 object identity drift。
* Alternative explanations：动作列表过长；raw history 没有记录过去的容器内容；模型
  选择了当前可执行但与 task 无关的 object。
* Evidence supporting：step 4 的 clear open-vs-look choice；step 5–11 ping-pong；
  step 14 明确拿错 lettuce；step 20–24 shelf loop。
* Evidence against：没有 invalid action；后续 navigation action 都是当前 list 中合法
  action；成功 controls 显示 actor 有时能切换 subgoal。
* Model-only fix plausibility：**POSSIBLE**。
* Prompt/state representation fix plausibility：**LIKELY/POSSIBLE**。
* Confidence：**HIGH**（存在清晰局部错误）；**MEDIUM**（归因到 model-only）。

### 3.6 Potato → Fridge（heat）

Task：

```text
pick_heat_then_place_in_recep-Potato-None-Fridge-27/
trial_T20190908_143628_766051
```

Family：`pick_heat_then_place_in_recep`
Outcome：未获取 potato；step 9 后连续 inventory 至 step cap。
Artifact：

```text
.../tasks/009_b07fc9fbab42/c1_rep00/
```

#### Trajectory summary

```text
1 go to cabinet_1       -> empty
2 go to cabinet_2       -> empty
3 go to cabinet_10      -> closed
4 open cabinet_10       -> empty
5 go to cabinet_1       -> empty again
6 go to cabinet_2       -> empty again
7 go to cabinet_1       -> empty again
8 examine cabinet_7     -> bowl_1
9 inventory             -> not carrying anything
10–32 inventory         -> not carrying anything
```

#### First meaningful divergence

* step：5
* public state：刚刚打开的 `cabinet_10` 明确为空；action list 中有未访问的 cabinet、
  receptacle 和 appliance。
* model action：重访 `cabinet_1`，随后又重访 `cabinet_2`。
* why problematic：search path 不再累积有效 progress。step 8 虽然通过
  `examine cabinet_7` 找到 bowl，但这不是 task target；step 9 后在
  `not carrying anything` 且有大量未尝试 actions 时仍连续选择 inventory。

Could a reasonable actor infer the correct local direction? **YES，带有 history/state
caveat。** task 是 `put a hot potato in fridge`，没有 target acquisition；最新 state 和
admissible actions 支持继续 search。模型可见 raw action history，但看不到之前各 cabinet
observation 的独立历史记录，也没有 visited-candidate structure。

#### Causal assessment

K* heat routine 只有在“acquiring the target object”之后才 relevant，没有证据表明它
诱导了 step 5 或 step 9。这里的停滞更早发生在 search progress 维护阶段。

* Primary bottleneck hypothesis：模型在多候选 search 中无法从 action history 形成
  稳定的已检查集合，随后把 `inventory` 当成默认恢复动作。
* Alternative explanations：长 action list/context load；qwen3.8-flash 的空间搜索
  能力不足；最新 observation 对 remote candidate 状态不完整。
* Evidence supporting：step 5/6/7 重访；step 9–32 完全不改变 state；所有 index 合法。
* Evidence against：成功 Apple 能在多个容器之间继续 search 并完成；所以不是 carrier
  完全无法表达搜索。
* Model-only fix plausibility：**POSSIBLE**。
* Prompt/state representation fix plausibility：**LIKELY/POSSIBLE**。
* Confidence：**MEDIUM-HIGH**。

## 4. Four success controls

成功案例不是“漂亮结果”而是用于比较相同 C1 prompt/interface 下哪些 transition
能够完成。

### Laptop → Desk

Artifact：`tasks/000_db485ebd50e7/c1_rep00/`。

模型先执行 `go to desk_1 -> go to bed_1 -> take cellphone_1`，再把 cellphone 放回，
随后取得 `laptop_2` 并放到 desk，11 步完成。这个 control 说明：

* actor 可以在有 distractor object 时恢复目标；
* observation `On bed_1, you see ... laptop_2 ...` 对目标 acquisition 足够清楚；
* success 并不代表没有 semantic detour，且不是最短路径。

### Apple → Fridge（heat）

Artifact：`tasks/003_9fa5d3902fe0/c1_rep00/`。

模型找到并拿到 `apple_3`，导航到 microwave；在 closed microwave 前连续四次
`look`，但最终选择 `heat apple_3 with microwave_1`，再取/放回 fridge，25 步完成。
这说明：

* step-cap 不是所有冗余的直接终点；actor 有时能从重复 observation 恢复；
* heat command 的成功反馈 `You heat apple_3 using microwave_1.` 明确表达了 transformation；
* 同一 K* 中的 heat routine 虽然文字上提到 open/put/close，actor 仍能使用载体提供的
  direct heat action。

### SoapBar → Cabinet

Artifact：`tasks/006_4d0e4849f544/c1_rep00/`。

模型经过 cabinet search 找到 `soapbar_1`，执行 `clean soapbar_1 with sinkbasin_1`，
再到 cabinet placement，13 步完成。`You clean soapbar_1 using sinkbasin_1.` 是清晰的
transformation feedback；search → clean → placement 的 phase switch 可被维持。

### DishSponge → Cart

Artifact：`tasks/007_2d9170ac03a8/c1_rep00/`。

模型先拿到并清洗 `cloth_2`，之后把 cloth 放回 toilet，再取得目标 `dishsponge_4`，
清洗后放入 cart，21 步完成。这是重要 control：模型并非一旦处理 distractor 就必然
无法恢复；它能在 observation 明确显示新对象后重新绑定 task，并完成两次局部 routine。

### Controls 与 failures 的差异

成功 controls 中更常见：

* 目标对象在当前 observation 中明确出现；
* transformation 有直接、清楚的环境反馈；
* distractor 处理后有明显的新 observation 帮助重新绑定；
* action list 没有像 CoffeeMachine case 那样同时包含几十个 cabinet/drawer navigation
  候选。

失败 cases 则更常见：

* 空/closed receptacle 之后需要维护长期 search progress；
* target 未获取时就进入 downstream routine；
* action list 中存在当前 observation 之外的 remote `take` distractors；
* transformation 或物品状态没有结构化、明确地表达在当前 state 中。

这是一组 interface/instance 差异和 model decision 差异的混合证据，不足以做 model-only
因果归因。

## 5. Cross-case synthesis

### 5.1 Observed recurring bottlenecks

1. **Search progress 不稳定。** Knife、Cup、Potato/Fridge、Cool/Coffee 都在空或
   closed receptacle 后重访或选择 `inventory/look`，没有形成可审计的“已检查候选”状态。
2. **当前 phase 没有显式承载。** actor 必须从 task instruction、最新 observation、
   action-string history 和 K* 自己推断 `SEARCH`、`OBJECT_ACQUIRED`、`NEED_COOL` 等；
   失败轨迹中经常在未拿到 object 时使用 downstream routine，或拿错对象后继续执行。
3. **Action affordance 比局部 observation 更宽。** Potato/CounterTop 的 actor 在
   coffeemachine observation 下看到并执行 `take soapbottle_2 from countertop_1`；这让
   remote object identity 错误成为合法 action，而不是 invalid action。
4. **历史 observation 缺失。** raw `executed_action_history` 只说明“做过什么”，不说明
   每次做完看到了什么。因此 actor 能知道它曾去过 `cabinet_1`，却没有一个结构化字段
   保存该次 empty result 或目标物状态。
5. **载体 transformation semantics 与自然语言 routine 可能不一致。** Cool/Shelf 的
   `put` versus `cool` 是最直接的例子。
6. **长 action list 增加选择负担。** Cool/Coffee 的初始 list 约含几十个 drawer/cabinet；
   即使 action-index 消除了字符串复述错误，它没有消除 semantic candidate selection。

### 5.2 Evidence for a model capability bottleneck

有一些局部决策满足“公开信息已经相当清楚，但仍选择明显无进展 action”：

* Cup step 4：closed `cabinet_2`，`open cabinet_2` 可用，选择 `look`；
* Cool/Coffee step 2：closed `cabinet_1`，`open cabinet_1` 可用，选择 `inventory`；
* Potato/Fridge step 9：看到无关 `bowl_1` 且不携带物品，在大量未尝试 actions 存在时选择
  `inventory`，随后重复 24 次；
* Knife step 7：尚未拿到 knife，且当前 dining table 没有 knife，仍进入 sink；
* Potato/CounterTop step 5：task 明确要求 potato，action list 有 exact
  `take potato_1`，仍拿 `soapbottle_2`。

这些是 actor execution reliability 的真实负面证据，说明“只要提供 action-index 就能可靠
执行”是不成立的。但这些决策同时暴露在长 action list、无 observation history、global
take semantics 等条件下，所以它们不能被写成 Qwen 单独的能力测量。

### 5.3 Evidence for prompt / representation bottleneck

证据相对更强，且跨多个 case 重复：

* 输入没有显式 `current_phase`、目标 object status、carried-object status snapshot 或
  historical observation summary；
* prompt 要求“Use task instruction and established memory”，但没有显式要求每一步先
  从最新 observation 更新 subgoal、确认 target identity、再选择 action；
* 四条 K* 同时注入，相关 scope 依靠模型从自然语言中筛选；
* `probe_runtime_state` 是机械字段，C1 中没有 H；它不提供普通 search 的 visited
  candidate summary；
* failure 往往在动作本身合法但 semantic target 错误时发生，而不是 schema/interface
  invalid。

这不是说必须在本轮修 prompt 或 state representation；它说明这些因素是重要 confound，
下一次若修改它们，当前 10-task Gate B1 不能继续作为独立 pass evidence。

### 5.4 Evidence for K* interference

结论：**没有广泛的强证据，但有一个具体的强语义冲突。**

* Knife、Cool/Coffee、Cup、Potato/Fridge 中，K* 的 search guidance 总体上要求继续
  搜索，失败更像 actor 没有执行 guidance，而不是 guidance 明确把它引向错误容器。
* Cool/Shelf 中，K* 的“放入 fridge 以冷却”与载体实际需要的
  `cool mug_2 with fridge_1` 不一致；这是可复现的 scope/contract concern，应在未来
  development diagnostic 中单独隔离。
* 因此不能说 K* 完全无害，也不能把所有失败归因于 K*。

### 5.5 Evidence for environment / harness ambiguity

有两类明确证据：

1. 当前 observation 位于 `coffeemachine_1` 时，admissible list 可以暴露并执行从
   `countertop_1` 取物的 action。它是合法执行，不是 invalid index，但不等价于“当前
   局部可见 affordance”；这会放大 object-selection error。
2. Cool/Shelf 中，`cool mug_2 with fridge_1` 在放入前存在，`put mug_2 in/on fridge_1`
   后不再存在；而 observation `You put mug_2 in/on fridge_1.` 没有直接说明 cooling
   是否已经完成。这使自然语言 K* 与 environment action contract 难以对齐。

相反，action-index resolution、当前 index legality、环境 action execution 本身在 10
个 traces 中没有发现 mechanical failure：invalid action count 是 0。

### 5.6 Family-specific pattern: cool = 0/2

两个 cool failures 的 first divergence 不同：

* Cool/Shelf：目标 mug 成功获取，失败发生在 cooling realization；K*/environment
  semantics 是主要 confound。
* Cool/CoffeeMachine：在目标获取前就停滞，step 2 未打开 closed cabinet，之后反复
  inventory；它更像 search/context-load failure。

共同点只能谨慎表述为：两个 case 都没有完成“取得 mug → 执行 cooling → downstream
placement”的完整链路；不能从 2 个样本推出 cool operation 本身是唯一问题，也不能
推出 cool family 的 actor capability 普遍较差。

### 5.7 Step-cap interpretation

6 个 step-cap 不是同一种失败：

* Knife：step 7 后已经明显进入无进展 receptacle loop，后续不是“还差几步”；
* Cool/Shelf：到 step 16 已取得目标并到达 fridge，若 cooling contract 明确，可能只
  需要少量后续动作；这是最接近成功但也最受 K*/environment semantics 影响的 failure；
* Potato/CounterTop：step 5 拿错 object，step 17 虽看到 potato 仍未恢复，属于早期
 目标绑定失败后的长期漂移；
* Cool/CoffeeMachine：step 2 后没有形成 search，step 7–32 基本是 inventory 停滞；
* Cup：step 4 后的 cabinet loop、step 14 错拿 lettuce、step 20–24 shelf loop，
  是多个早期 semantic drift，不是接近完成；
* Potato/Fridge：step 5 的重访和 step 9–32 inventory 停滞，属于早期 search 失败。

Apple control 也有四次重复 `look`，但最终恢复并完成；因此单纯出现冗余 action 不等于
step-cap 根因，关键是之后是否能恢复到正确 phase。

## 6. Attribution table

| issue | implementation/interface evidence | model evidence | current judgment |
|---|---|---|---|
| action-index mapping | 10 traces 中 invalid index = 0，resolved action 与 ordered list 一致 | 无 | 不是当前主要 blocker |
| search progress | 无 observation history、无 structured visited/phase；长候选 list | 多次重访空容器、closed container 上选择 look/inventory | stack-level confound；不能 model-only 归因 |
| object grounding | remote take action 在当前 list 中机械合法 | Potato step 5 拿 soapbottle，Cup step 14 拿 lettuce | 混合原因，需 controlled test |
| transformation semantics | Cool/Shelf 的 `put`/`cool` action contract 与 K* wording 不一致 | 模型选择了 K* 字面上合理的 `put` | K*/carrier confound 很强 |
| downstream phase switch | 没有显式 phase/status history | 未拿到 object 时去 sink、拿错后继续 | stack-level failure，model contribution possible |
| step cap | cap 机械执行正常 | 大量早期 no-progress traces | 主要是上游决策/表示问题，不是 cap 本身 |
| K* broad interference | 四条 memory 同时可见 | 失败时没有普遍直接追随错误 K* | no strong broad evidence; one cool-specific conflict |

## 7. Answers to the research questions

### 1. 是否足以把 Gate B1 failure 主要归因于 model capability？

**不足。** 轨迹包含真实的 model-side bad choices，但当前 evidence 只能支持：

```text
Qwen3.8-Flash + frozen prompt + frozen K* + current ALFWorld state/history
representation + carrier action semantics + harness
```

这个完整 C1 stack 不可靠。它不能把失败主要、单独归因于模型能力。

### 2. 是否有足够 evidence 表明 prompt/state/K*/harness 至少一个是重要 confound？

**有。** 最强证据是：

* history 只有 action strings，没有 observation history 或 phase state；
* 多个 failure 在空/closed container 后重访或 inventory-loop；
* Potato case 暴露 remote take affordance；
* Cool/Shelf 的 K* realization 与实际 cooling command 不一致。

这不意味着当前 harness 必然“有 bug”；而是它目前没有把这些语义选择因素与模型能力
隔离开。

### 3. 下一轮应选 A、B、C 还是 D？

当前最合理的是 **C：先做一个极小 controlled test 区分模型问题和明确 interface/K*
问题**，而不是直接换更强模型。

建议的研究顺序是：

1. 先针对 Cool/Shelf 做一个不进入正式 gate 的 carrier-contract diagnostic，明确
   `cool mug with fridge` 与 `put mug in/on fridge` 的语义关系；
2. 再用极少量、与当前 gate 独立的 held-out tasks，对“当前输入”与一个事先冻结的
   最小 interface variant 做对照，例如仅明确 transformation command/phase evidence，
   不加入 oracle outcome、hidden placement 或 rule-based next action；
3. 只有在 interface contract 被验证且仍出现“公开信息足够、模型重复无进展”的失败时，
   才有充分理由优先评估更强 actor（A）。

本轮不实施上述改动，也不把它们写回正式 Gate B1。

### 4. 如果之后修改 prompt/K*/state representation

当前 10-task hard calibration 必须被标记为 **development/diagnostic evidence**，不能
在同一 10 tasks 上调参到 `>=8/10` 后宣称 independent Gate B1 pass。

后续必须由 researcher 重新冻结：

* 修改后的 prompt/K*/state representation；
* 新的 independent actor gate protocol；
* 与开发样本不重叠的 admission/calibration membership，或明确的预注册复测方案；
* unchanged threshold 与 failure review rule。

当前 actor manifest 不变，Gate B1 result 不变。

## 8. Final recommendation and stop rule

本轮诊断推荐保留以下结论：

```text
Do not equate this Gate B1 stack failure with model failure.
Do not claim C3/C2/H/persistent-memory effectiveness.
Treat current traces as negative stack-level reliability evidence.
Use a small controlled interface/K* diagnostic before selecting a stronger actor.
```

没有修改代码、prompt、K*、manifest、registry 或 Gate B1 result。runtime traces 继续
按 repository policy 保存在本地 ignored artifact directory；本报告只提交人工提炼的
可审计 evidence，避免把大体量运行数据纳入 Git。

完成本报告后停止，返回 researcher review；不得在本 cycle 运行 diagnostic 18、B2/B3、
target matrix 或 second actor。
