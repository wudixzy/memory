# ALFWorld 配对基础设施验证结果

日期：2026-09-17
分支：`exp/minimal-exploratory-memory-validation`
载体：ALFWorld TextWorld（`third_party/automanual`）
模型：`qwen3.8-flash`，`thinking=false`，`temperature=0`
传输：DashScope direct/no-proxy

本轮只验证 E0/E1 配对基础设施，没有把 Apple sanity 当作方法效果实验。

## 结论摘要

- Apple/Microwave 与 Pencil/Shelf 各进行 10 次同 task、同 requested seed 的无模型 reset audit；两者的公开初始 fingerprint 均各只有 1 个，缓存的静态 PDDL 也各只有 1 个。
- 采用 `replayable_episode_spec`。当前 pinned TextWorld 中，`game.tw-pddl` 内的 `pddl_problem` 与 `initial_state.pddl` 字节完全一致，E0/E1 可以从同一个缓存 game specification 重放。
- paired runner 不再先 reset、比较、丢弃，再另建实际 episode。现在创建的两个 `StepwiseTask` 就是随后传给 actor loop 的两个 episode，`pairing_proof.json` 记录了它们的 replay identity 与初始 public fingerprint。
- 指定 Apple target 的 3 组实际配对 sanity 中，3/3 pairing proof 有效，139/139 个 actor decision 的 `action_index` 合法；E0 完成 2/3，E1 完成 2/3。E1 三次都激活 H、达到 `EVIDENCE_OBTAINED` 并移除 runtime H；这仍不是 H 的因果效果结论。

## 1. Reset audit（零模型调用）

执行命令（credential 未读取，网络未启用）：

```bash
env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY \
  -u http_proxy -u https_proxy -u all_proxy \
  PYTHONPATH=src:. conda run --no-capture-output -n memory-automanual \
  python experiments/exploratory_memory_mvp/run_reset_audit.py \
  --output artifacts/exploratory_memory_mvp/reset-audit-20260917-v2 \
  --repeats 10
```

artifact：`artifacts/exploratory_memory_mvp/reset-audit-20260917-v2/reset_audit.json`。该目录被 `.gitignore` 忽略；每次 reset 保存 exact initial observation、完整有序 `admissible_actions`、`extra.gamefile`、`won`、canonical public fingerprint 和 infrastructure-only static PDDL hash；`model_calls` 为 0。

| task | seed | repeats | unique public fingerprints | unique static PDDL | observation/actions |
|---|---:|---:|---:|---:|---:|
| `pick_clean_then_place_in_recep-Apple-None-Microwave-14/trial_T20190909_120203_117379` | 42 | 10 | 1 | 1 | 413 chars / 22 |
| `pick_and_place_simple-Pencil-None-Shelf-310/trial_T20190908_023553_529151` | 42 | 10 | 1 | 1 | 268 chars / 13 |

Apple public fingerprint：`60064b175a17a77e4c02b79a2bebc2b8070af7401969d6c816448961032fc8c0`。Pencil public fingerprint：`68a19c46faef81cf468af4e2c65ac5bf476c3a4325b50bdb5d187ddd8a4d6824`。

Apple 静态 PDDL 本身包含多个 `Apple` 实体，初始 `inReceptacle` facts 将它们放在 `GarbageCan`、`Microwave` 和 `Fridge` 等 receptacle 中。因此不同轨迹出现 `apple_1`、`apple_2`、`apple_3`，可以是同一个公开世界内 actor 选择了不同的合法对象，不应直接解释为 reset 生成了不同 object instance。这一判断由 PDDL facts 和本次 exact public reset audit 支持，同时保留了 actor 后续选择与 reset determinism 的区别。

## 2. Pinned carrier 检查

检查结果：

| 组件 | 观察 |
|---|---|
| `alfworld/agents/environment/alfred_tw_env.py` | `regen_game_files=False` 时使用已有 `game.tw-pddl`；runner 将 data path 限定到一个 task，并确认 `loader.game_files == [expected]`。 |
| `AlfredDemangler` / `Demangler` | `domain_randomization=False` 时 `shuffle=False`；entity IDs 来自排序后的 game infos。 |
| `textworld.envs.pddl.PddlEnv.load` | 从缓存 JSON 的 `pddl_problem` 创建 `State` / `Game`，不重新生成 ALFRED object placement。 |
| `textworld.envs.pddl.PddlEnv.reset` | 从已加载的静态 `Game` 创建 `GameProgression`，再生成 public observation 与 valid commands。 |
| `TextworldBatchGymEnv.seed` / `SyncBatchEnv.seed` | 控制 game-file iterator 和 leaf seed；batch size 为 1 且只有一个明确 game file 时不改变 task 选择。 |
| 环境配置 | `regen_game_files=False`、`domain_randomization=False`、`num_train_games=1`。 |

运行时版本为 TextWorld 1.3.2、Gym 0.15.4、NumPy 1.23.5；automanual upstream HEAD 为 `aeb17e4a4fe8bb43b9eb390b7b0b94a3ca8b9324`。

Apple 的 `game.tw-pddl` hash 为 `096ab254cc438cb948121084b0ead12ea428267832606a54e9cc49c788f4e9b5`；`initial_state.pddl` 和其中的 `pddl_problem` hash 都为 `8ac2d1d19fa35a477a1757f21f0c05a1f9afd8d498d519da08550a9e5aadc093`。这证明当前 TextWorld adapter 的缓存 episode specification 可 replay，不是对一般 ALFRED/AI2-THOR clone 的保证。

## 3. 选定的配对机制

没有采用 pinned `PddlEnv.copy`：该路径是 soft copy，并引用当前 wrapper 不适用的 `_inform7` 状态，不能作为已验证的完整 snapshot。也没有把“same task + same nominal seed”单独当作 underlying-state proof。

`episode_replay_spec(task_id, seed)` 保存并校验 `task_id`、`requested_seed`、`game_identity`、`game_file_sha256`、`initial_state_identity`、`initial_state_sha256`、`pddl_problem_sha256`、`trajectory_identity`、`trajectory_sha256`、`domain_sha256` 和 `pddl_problem_matches_initial_state`。

实际 pair 流程为：

```text
e0_episode = StepwiseTask(task_id, seed)
e1_episode = StepwiseTask(task_id, seed, replay_spec=e0_episode.replay_spec)
pairing_proof = build_pairing_proof(e0_episode, e1_episode)
assert pairing_proof.pairing_valid
run actor on e0_episode and e1_episode
```

`assert_pairing_proof_matches_episode` 在 actor loop 开始前检查 role fingerprint、task/replay metadata 和 proof 中的 actual episode metadata。pairing proof、game hash、initial fingerprint 及其解释不会进入 B/C/H/actor/A prompt。

## 4. Runner 改动

`run_online_pair.py` 与 `run_transfer_pair.py` 删除了原来的“preflight reset E0、preflight reset E1、compare/discard、再创建新的 E0/E1 execution episodes”。

现在 `paired_initial_states.json` 明确标记 `actual_execution: true`，其中的 fingerprint 来自后续真正执行的两个 `StepwiseTask`。无法证明 replay specification 或初始 public state 匹配时，runner 保存失败 artifact 并阻止 paired path。`action_index`、`probe_runtime_state`、H lifecycle 和 actor prompt semantics 没有为 pairing audit 改变。

## 5. Post-fix Apple sanity

固定设置：P005 SoapBottle-417 的已有 cleaned H；target 为 `pick_clean_then_place_in_recep-Apple-None-Microwave-14/trial_T20190909_120203_117379`；seed 42；step cap 32；qwen3.8-flash；无 thinking、temperature 0。artifact：`artifacts/exploratory_memory_mvp/pairing-apple-action-index-20260917-v1/`。

| run | pairing | condition | indices valid | won | steps | H activated | evidence ready | H removed |
|---:|---|---|---|---|---:|---|---|---|
| 1 | yes | E0 | yes | no, cap | 32 | n/a | n/a | n/a |
| 1 | yes | E1 | yes | no, cap | 32 | yes | yes | yes |
| 2 | yes | E0 | yes | yes | 18 | n/a | n/a | n/a |
| 2 | yes | E1 | yes | yes | 25 | yes | yes | yes |
| 3 | yes | E0 | yes | yes | 11 | n/a | n/a | n/a |
| 3 | yes | E1 | yes | yes | 21 | yes | yes | yes |

139/139 个 step 的 `resolved_action` 都等于同一步有序 `current_state.admissible_actions[action_index]`。E1 三次都从 `go to countertop_1` 进入 surface-first probe，在找到 Apple 时报告 `EVIDENCE_OBTAINED`，随后 runtime H 被移除。run 2/3 完成 clean/place；run 1 找到 Apple 后错误地将它放到 `sinkbasin_1`，在 step cap 前没有完成 microwave 目标。

配对基础设施因此通过了这次 sanity；actor 仍有语义执行方差（E0 2/3、E1 2/3）。不能用这 3 组运行声称 H 提升性能，也不能把 `EVIDENCE_OBTAINED` 解释为 hypothesis 已被证明。

这 139 个 completed model calls 共记录 191,001 input tokens、2,096 output tokens 和 27,648 cached input tokens；逐 call 本地 estimated cost 合计约 0.1255 CNY，provider-accounted cost 未返回。该数值仅用于成本量级记录，不作为跨模型价格比较。

### 非结果运行记录

曾误调用 `run_online_pair` 的 source case `alfworld-p-005-soapbottle-417`，实际执行的是 SoapBottle 而不是 Apple target；目录 `artifacts/exploratory_memory_mvp/pairing-apple-qwen38-20260917-v2/` 不用于本节结果。该目录的 proof 对实际 SoapBottle episode 有效，但 task 入口错误；报告保留它以避免静默删除失败记录。更早的相对 `.env` 路径错误目录 `...pairing-apple-qwen38-20260917-v1/` 在模型调用前失败，`usage.status` 为 `not_started`。

## 6. Remaining uncertainty

| 项目 | 当前判断 |
|---|---|
| reset/public pairing | 对当前两个 TextWorld task，10 次 audit 与 3 个实际 pair 支持稳定 replay；不是所有 carrier 的一般保证。 |
| hidden state | 由同一缓存 game/PDDL bytes 与 pinned `PddlEnv` construction 支持；没有通用 snapshot/clone。 |
| actor reliability | 仍是显著 confound；合法 index 不等于语义动作正确，Apple 仍有 step-cap failure。 |
| H/method effectiveness | 本 sanity 不支持性能或因果方法效果；只支持 H lifecycle 与配对/接口可审计。 |
| 旧 reset-variance 解释 | 当前证据更支持“单一静态世界中的多合法同类对象与 actor choice”，而非这两个 task 的 reset placement variance。 |

下一步应进入 paper-level evaluation design，而不是继续添加 semantic planner 或 ad-hoc fallback。
