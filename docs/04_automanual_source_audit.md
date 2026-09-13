# AutoManual + ALFWorld: fixed-source integration audit

Subsequent authorized embedding substitution and actual offline Skill_Bank wiring
are recorded in [the next audit](06_embedding_wiring.md). Original-source line
references and unresolved evaluator/containment/multi-updater gates below remain
applicable; earlier statements about uninstalled dependencies or embedding policy
describe the prior preparation state.

Audit date: 2026-09-11. This is preparation, **not Phase 0 completion**.
No LLM or embedding endpoint was called. This document concerns the official
`autobuild_case` ALFWorld building path, not MiniWoB/WebArena or a rewritten method.

## Source identity and citation convention

AutoManual: https://github.com/minghchen/automanual,
commit `aeb17e4a4fe8bb43b9eb390b7b0b94a3ca8b9324`.
Bundled `alfworld/` tree: `cc528106f15eaaef06f4900e78c649f9f99a5d06`.
All AutoManual line references below refer to that **original commit**, before the
declared lazy-import patch. `A/` means `automanual_alfworld/`; `F/` means
`alfworld/alfworld/`. They can be inspected with `git show COMMIT:path` and `nl -ba`.
The independent ALFWorld reference HEAD is not the execution source.

TextWorld: https://github.com/MarcCote/TextWorld,
commit `634f9f91fec732a79dd9e7623675301a53f06623`.
downward: https://github.com/MarcCote/downward,
commit `84769171b9d965bf5739eaa7cf6604b0d9697534`.

## 1. Task, environment, evaluator and reset

| Stage | Fixed-source entry | Actual behavior |
| --- | --- | --- |
| Runner selection | `A/main_build.py:55`, `:100–125` | Loads base_config, creates AlfredTWEnv(train), initializes batch 1, loops 135 resets and filters task types/counts; dispatches `autobuild_case_trail.run`. |
| Unsafe runner side effects | `A/main_build.py:16–18`, `:84–87` | Reads OpenAI environment credentials at import and deletes an existing run directory. Never imported or executed by this smoke. |
| File discovery | `F/agents/environment/alfred_tw_env.py:72–180` | Walks configured task directories; reads trajectory task type/goal; accepts cached `solvable` game files or generates/rechecks using expert. Unsorted filesystem order is not a stable task ID. |
| Initial text | `F/agents/utils/misc.py:78–90`, `:107–116` | Uses PDDL task parameters and templates (or human annotations if configured); this is the public task description, not an expert plan. |
| Environment | `F/agents/environment/alfred_tw_env.py:215–240` | Registers TextWorld games, author demangler and AlfredInfos wrappers, batch 1, async Gym, max 50 steps. Train/dagger requests won, admissible commands, expert plan, gamefile. |
| Task wrapper | `A/env_history.py:102–153` | `InteractEnv` keeps location/holding/history; transforms Python-style action strings, calls raw step, copies `info['won'][0]` into `reward`. |
| Official evaluation | TextWorld `textworld/envs/pddl.py:59–70`, `PddlEnv._gather_infos`; `:180–219`, `PddlEnv.step` | `state.check_goal()` evaluates hidden PDDL goal; step returns score 1 iff won, done iff won/lost. There is no separate AutoManual evaluator model. |
| Original reset | `A/main_build.py:108–111` | Raw reset advances through registered games. It does not establish same-task reset reproducibility or explicitly seed all RNGs. |

The diagnostic pins a single official task directory, calls the unmodified
AlfredTWEnv loader/init_env, seeds Python/NumPy/Gym, and creates two fresh batch
environments. It compares initial text, four action results, reward/done/won and
admissible lists. This tests an observed trajectory prefix, not hidden simulator
state equality, success-state resets, all actions, arbitrary tasks, or remote APIs.

## 2. Roles, LLM entrances and retries

The main call graph is:

```text
autobuild_case_trail.run
  -> autobuild_trail.run_trail
       -> Worker.generate (up to 3 planning/replanning calls)
       -> optional success-code conclusion OR failure reflection (up to 1 call)
       -> Skill_Bank.add_skill/add_failure + save
       -> Rule_Manager.add_epoch_history + save
  -> run_autobuild_case
       -> optional case classifier (0 or 1 Builder call)
       -> Builder.generate + exec(rule operations) (1 call)
       -> check_rule + save
  -> run_merge
       -> while rules > 12: fresh Builder_merge.generate + exec + arrange_rules
       -> save
```

- `A/autobuild_case_trail.py:13–14` creates Worker and Builder with the same
  `args.model_name`; prompt files and demonstrations differ by role.
- `A/autobuild_trail.py:56–104` implements planning, conclusion/reflection and skill
  persistence. Replanning is a behavioral loop, not an HTTP retry.
- `A/autobuild_case_trail.py:39–76` selects Builder prompt based on success and
  replan count, optionally asks it to classify imperfect rules vs imperfect agent,
  then executes emitted code. One generated block can perform many rule mutations.
- `A/autobuild_trail.py:119–132` merges repeatedly with **no iteration bound** if
  rules remain above 12. Every merge must be separately observed; no last-only diff.
- Formulator is a separate stage, not part of this one-task building call:
  `A/main_test.py:81–83` -> `A/formulate_manual.py:5–43`, one generate, Markdown
  extraction, rule reordering, manual assignment and save.

API factory: `A/OpenAI_Agent_API/__init__.py:13–21`. Default helper output cap is
2000; temperature 0. `process_respond:5–11` splits **visible returned text** into
rationale and Python. Its variable name `respond_thought` does not imply access
to hidden chain-of-thought. No hidden reasoning should be recovered or stored.

Chat path: `ChatGPT_API.py:69–126`, `get_prompt:58–67`, actual chat call `:97–105`.
Uses local prompt/history lists, cl100k_base length gate (15000 for unfamiliar
model IDs), max_tokens=2000, tools normally None. The factory does not supply
function tools for this path; generated Python calls local helpers. The alternate
legacy instruct completion is at `:86–95`, not relevant to the required model.

Assistants path: `Assistant_API.py:51–59` creates assistant/thread immediately;
`:64–70` adds prompt messages; `:83–132` creates/submits runs, polls every second
without timeout, lists latest messages. Its output cap is used in a local length
check but not sent to `runs.create`. Its consumed_tokens is a prompt estimate,
not invoice usage. The official README chooses this path; DeepSeek chat support
does not establish Assistants support. Prefer the already-official chat path for
future common-backbone work, recording the interface/config difference.

Both wrappers construct `openai.OpenAI()` with no explicit retry/timeout override.
No wrapper-level HTTP retry loop exists, but SDK retries must be included in a
future adapter budget and verified against the installed SDK version. The pinned
`openai==1.35.3` is in the full upstream requirements; **not installed or exercised
in the text-only environment**. Do not assert an exact effective retry count from
this audit alone. Disable hidden SDK retries or instrument each transport attempt
before any paid run. Poll requests are not equivalent to generation calls.

Additional paid entrance: `A/autobuild_utils.py:164,190–192` constructs
OpenAIEmbeddings, embeds successful skill task types into FAISS and embeds the
query. It is not a chat call and cannot be silently replaced with DeepSeek chat,
string matching or a local embedding model. Initial empty skill storage avoids
retrieval calls (`:186–188`), but the constructor still requires its dependency
and credential configuration. Later nonempty-memory operation is blocked pending
an explicitly approved faithful embedding/provider policy.

## 3. Native memory and update boundaries

`A/autobuild_utils.py`:

- `Rule_Manager:29–69`: `rule_manager.json` contains the entire global_history,
  `all_rules`, `cur_epoch`, optional `manual`, per-epoch interactions, environment
  history, success, error_step and check_rule. Keep the original JSON text too.
- `:71–94`: write/update/delete. Rules have `rule`, `type`, `example`,
  `validation_record`; updates retain up to 3 validation records; deletion first
  sets a tombstone. `write_rule:72` compares the saved success value with `>=0`;
  since the runner supplies booleans this check is not a reliable failure guard.
  This existing behavior is recorded, **not fixed** as an infrastructure change.
- `:119–138`: merge cleanup renumbers rule IDs and rewrites references. IDs are
  checkpoint-local; targeted interventions require explicit lineage, not assuming
  `rule_3` means the same rule forever.
- `:140–157`: injection is manual text or rule/type/example text, plus executable
  helper functions parsed from examples. Raw memory cannot be reduced to this text.
- `Skill_Bank:160–203`: `skill_bank.json` maps task type to task_name/init_obs/
  skill_code/success. Success can be direct/indirect; failures store reflection.
  FAISS/embeddings are derived retrieval state. Retrieved success code is also
  defined as executable helpers; failure records can be injected by task type.

Actual full memory is **both stores**, history/control metadata, and any derived
retrieval configuration/state necessary for replay. One task mutates memory in
multiple intervals: skill addition/failure recording; epoch history; each Builder
operation; check_rule flag; each merge/renumbering. The shared single updater
interval schema cannot represent these faithfully. Required future extension:
ordered update events with update_id/phase/call_id, full before/after snapshots,
per-operation diffs and availability, including partial failed intervals. Keep
overall checkpoint diff and intervention diff distinct. This extension is not
implemented as a placeholder real adapter in this deliverable.

## 4. Ground-truth data flow: gate not passed

This conclusion follows code paths, not Evidence labels:

1. Task PDDL and full facts enter the TextWorld engine. `_gather_infos` computes
   `won` by checking the hidden goal. `step` exposes it as score/done/info.
2. `InteractEnv.step:123–152` reads won, stores reward, and appends
   `Succeed: ...` to environment history at terminal/max-action conditions.
   `Agent.report:53–62` returns this history to Worker.
3. `run_trail:65–103` uses reward to handle errors, choose success conclusion vs
   failure reflection, write skill/failure memory and save success in epoch history.
4. `autobuild_case_trail:20–27,39–75` reads that same success and selects different
   Builder prompts. `prompts/builder_case_prompt.py:42–83` explicitly changes what
   kinds of rules should be written for success/failure. Removing success input
   would change memory formation, not just provider compatibility.
5. Train/dagger requests an expert plan (`alfred_tw_env.py:222–225`). TextWorld
   `PddlEnv._gather_infos:132–148` consults `HandCodedTWAgent`, full state and admissible
   actions; `reset` can also produce an explicit walkthrough if requested. The
   official runner only reads gamefile at reset and InteractEnv only reads won at
   step; no explicit expert-plan-to-prompt edge was found in this selected path.
6. However, generated Python runs via unrestricted `exec` with an Agent object
   (`run_trail:46,63`), reaching `agent.env._env` and process builtins. Builder exec
   runs in function scope. Hidden state/files/credentials are not capability-
   isolated. Absence of a prompt edge is **not** proof generated code cannot access
   evaluator/experts. This needs a real containment boundary, not a textual tag.

The public task goal itself is legitimate input; hidden state, expert plans and
goal-derived evaluation feedback need separate treatment. The native loop
intentionally makes terminal evaluation feedback adaptive. Under this project's
strict evaluator-isolation contract, this is **not approved for main H1–H4**.
If the project intends to permit native terminal success as ordinary environment
feedback, that requires an explicit protocol decision plus containment audit;
we do not silently reclassify it as safe. Otherwise only a separately approved
diagnostic native-feedback run is possible. No hidden-success input was removed,
and no claim of a faithful no-GT AutoManual variant is made.

The environment smoke has no actor/updater and uses only visible text to choose
navigation. Original train-config expert computation is diagnostic, not consumed
or exported as a plan. Published upstream memory files used for JSON transport
testing are quarantined diagnostic data; they must never initialize experiments.

## 5. Artifact capture map for a future reviewed adapter

| Artifact | Capture point / current availability |
| --- | --- |
| manifest | Fixed source/patch/environment/data/task + requested/resolved backbone; real provider still unverified. |
| memory before/after | Full native rule_manager + skill_bank checkpoints, raw bytes and normalized metadata; loop not run in smoke, unavailable there. |
| memory injected | `run_trail:47–49`: rule_string, skill_string and defined helper source; also record retrieval provenance. |
| request/visible response | Chat `get_prompt`/transport boundary and returned message before parser; preserve actual prompt/config and role/call IDs. |
| actions/observations | Before/after raw `step` plus InteractEnv transformations/history; smoke captures real raw text/actions. |
| evaluator | Raw official TextWorld reward/done/won; segregate diagnostic output from adaptive channel. |
| updater inputs | Trajectory/success/case prompt, all_rules, skill data; current isolation gate conflicts. |
| updater outputs/diffs | Every skill/rule/control/merge mutation, not only final save; requires multi-interval schema. |
| telemetry | Chat + embeddings + retries + latency, full memory growth; smoke has actual zero LLM usage and unavailable memory growth. |

## 6. Cross-version boundary

Use a narrow UTF-8 JSON subprocess boundary: Python 3.10 parent owns artifacts,
Python 3.9.16 worker imports bundled ALFWorld from its explicit source path.
No shared Python imports or pickle objects cross the boundary. Environment events
and **complete raw published memory files** are round-tripped alongside a separately
labelled Chinese/multiline/nested JSON probe; exact structural and raw-string
equality is checked. This validates serialization, not an integrated memory loop.
Hidden engine state serialization is not claimed. See the preparation report for
actual execution evidence and remaining gates.
