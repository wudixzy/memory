# Native feedback boundary — approved AutoManual exception, NOT blanket admission

Date: 2026-09-11. The user approved the precisely scoped AutoManual native
won-derived feedback exception and table/cadence below. Effective version:
**automanual-native-won-v1-2026-09-11**. AGENTS.md §10 and docs/01 §6.1 now reflect
this exception only. No generic approval framework or new Phase 0 conditions
are introduced. The broader original proposed wording below is historical, not
automatically adopted. Restricted Python/chat/embedding differences remain
explicit; old synthetic artifacts are unchanged. The authorized real single-task
connection smoke is `synthetic=false, scientific_evidence=false`.

## Source basis and interpretation

Official AutoManual `aeb17e4a4fe8bb43b9eb390b7b0b94a3ca8b9324`, bundled ALFWorld
tree `cc528106f15eaaef06f4900e78c649f9f99a5d06`. Paths/lines below refer to the
**original pin**, not shifted patched lines. `A/` = `automanual_alfworld/`,
`F/` = `alfworld/alfworld/`; TextWorld is pinned in docs/05.
See [the original data-flow audit](04_automanual_source_audit.md).

The proposed distinction is between **native interaction feedback actually
consumed by the baseline** and **additional evaluator-only evidence**. Being in
an `info` dictionary is insufficient authorization. Conversely, deriving a
limited native observation from simulator state does not by itself make that
observation forbidden ground truth. The contract, actual consumer, timing and
granularity must all be audited; labels alone do not establish isolation.

Current error-channel implementation: ordinary built-in guest Python exceptions
retain a bounded public type/message without a traceback. Worker guest state is
preserved for official replanning. Facility failures still terminate; see docs/09.
The earlier generic-only error description in the historical table is superseded.

## Field-level boundary table

Actor/updater columns describe the selected official `autobuild_case` path, not
every theoretically possible arbitrary-Python access. Unrestricted exec at the
original pin can reach much more; its containment is a separate requirement.

| Field | Actual source and official consumption | Actor input | Updater input | Capture / proposed decision and basis |
|---|---|---|---|---|
| Public task description | `F/agents/utils/misc.py:78–116` templates from task parameters; raw reset → `A/main_build.py:108–111` text transformation → `InteractEnv.init_info:107–112` | Initial Worker prompt, `autobuild_trail.py:51–56` | Trajectory/skill `init_obs`, task text | Raw initial `observations.jsonl`, actual prompt in `model_calls.jsonl`. Allow the public rendered instruction, not the task source/PDDL that generated it. |
| Ordinary action observation | `InteractEnv.step:128–148` raw text → `process_ob`, location/holding suffix → history; `Agent.observation:17–24`, `report:53–62` | Direct helper return and subsequent Worker report | Native interaction/environment history, `add_epoch_history` | Raw observations plus exact prompt reports; allow native text/transformation. No hidden object expansion. |
| Tool/action error | `script_transform:159–188`, `InteractEnv.step:123–127`; Worker try/except `autobuild_trail.py:62–80` | Native unsupported-action text and code failure report | Same recorded interaction in Builder/history | Visible messages/history; allow ordinary native errors. Containment failures expose only safe categories, a separately disclosed behavior change requiring review, not equivalent error semantics. |
| Raw numeric TextWorld reward | TextWorld `PddlEnv.step:180–219`; `InteractEnv.step:128` **discards** numeric score via `_` | Not directly consumed | Not directly consumed | `evaluator.json` / diagnostic raw step record only. Do not inject numeric score merely because raw step exposes it. Sentinel test uses 987654 to distinguish it from `won`. |
| Native `won` → `env.reward` boolean | TextWorld `_gather_infos:59–70` checks goal; `InteractEnv.step:129` copies **won**, not numeric reward | No arbitrary polling in selected call graph. `Succeed: ...` enters Agent history/report only at termination/action cap (`:149–153`); affects error handling if env.done and reward (`autobuild_trail:65`) | After planning loop, boolean selects success/failure skill branch `:84–104`, epoch history, Builder success/classifier prompts `autobuild_case_trail:20–27,39–75` | Evaluator raw booleans segregated; exact native reports/updates retained. Proposal: permit precisely these existing boolean pathways; no added intermediate success prompts, progress scores or explanations. |
| Native `done` / local action cap | Raw done at `InteractEnv.step:129`; cap sets done at `:149–153`; `Agent.observation:18–19` returns `Done.` after termination | Stops further environment interaction; report terminal marker; Worker breaks after current code block (`autobuild_trail:82–83`) | Indirectly determines trajectory length and update timing, not a new Builder `done` prompt | Preserve original timing. Distinguish engine done from wrapper cap and three-response failure. Our real diagnostic has raw done=false throughout; task failure is not fabricated environment termination. |
| Admissible commands | Requested by train/dagger `F/agents/environment/alfred_tw_env.py:219–225`; supplied by TextWorld | No explicit consumer in Worker/Agent selected path | No explicit consumer | Prior no-actor env smoke saves them as diagnostic. New adapter never returns them over RPC or puts them into prompts. **Not permitted as additional hints** under this proposal. |
| Expert plan, walkthrough, reference answer | Train config requests expert plan; TextWorld `_gather_infos:132–148` consults expert/full state. Walkthrough may be generated if requested. Task trajectory JSON contains planning/annotation material | No explicit prompt edge; original unrestricted Python can access it | No explicit prompt edge; original exec scope is unsafe | Remains trusted environment internals, unavailable to adaptive channel; do not export plan/answers. Synthetic sentinels test rejection, not real secret reads. Any separate inspection is diagnostic-only and cannot seed memory or fixtures. |
| Full hidden state / PDDL facts / task files | Loader `alfred_tw_env.py:72–180`, TextWorld engine state; raw env object, internal files | Unrestricted `agent.env._env`/filesystem was reachable, not a legitimate helper contract | Original Builder scope/process similarly unsafe | Forbidden additional evidence. Environment stays trusted; no host project/data mounts in generated-code guest; no env object RPC. Full state is not serialized into adaptive artifacts. |
| Extra evaluator diagnostics / human analysis | Separate post-hoc evaluation or analyst conclusions, not selected baseline inputs | None | None | Separate diagnostic report only, never added to model prompt, skill or rule state. Cannot use analysis to manufacture fixture successes. |
| Official static demonstrations / initial rules | `prompts/autobuild_simple_examples.py:1–...`, passed by official factory as examples; initial two rules | Public author-supplied prior examples and rules | Builder's static worked example | Preserve and identify as official prior demonstrations, **not** the current task expert trajectory. Do not load published learned manual/skill checkpoints. |

### Exact feedback cadence to preserve

1. Each native action updates internal wrapper reward from `won`, and done from
   raw done or the 50-action cap. The direct observation return contains the
   native action text/location/holding, not an added reward dictionary.
2. `Succeed` is appended to **history** at native termination/cap. `Agent.report`
   exposes newly recorded history after the emitted Python block; it does not
   repeatedly append the terminal marker when called again without new actions.
3. After at most three Worker generations, the loop can fail while raw env is
   still not done. The official final-replan notice says unsuccessful. We must
   not change the engine reward to make this fixture successful or terminal.
4. Skill/failure selection and epoch history consume the same resulting boolean.
   Builder classifies failure or indirect success, then updates; direct success
   skips the classifier. No added evaluator query is permitted before each rule
   mutation or during merge. Our diagnostic exercises **failure only**.

`scripts/smoke/feedback_contract.py --execute` runs the official `Agent` and
`InteractEnv` against a clearly synthetic raw environment, with distinct numeric
reward, won and hidden/admissible sentinels. It verifies items 1–2 and excluded
fields without consulting real hidden files. This is contract wiring evidence,
not proof of a successful ALFWorld task or universal leakage freedom.

## Original proposed wording (historical; only the scoped exception above is effective)

Review these three changes as a unit; **do not apply automatically**:

1. **AGENTS.md §10, after the existing prohibition**, and **docs/01 §1 item 6**:

   > “Evaluator-only ground truth” excludes a finite native environment feedback
   > channel only when that channel is part of the baseline's documented and
   > source-audited interaction contract and is actually consumed by its official
   > adaptive loop. Such an exception must list fields, transformations, consumers,
   > timing and granularity in an approved per-pair boundary table. It does not
   > authorize additional answers, expert plans, hidden state, progress diagnostics
   > or evaluator queries. Mere presence in an API response is not authorization.

2. **docs/01 §6.1, new AutoManual feedback boundary**:

   > For the pinned AutoManual building path, preserve native public task/action
   > text, ordinary execution feedback, and existing won-derived boolean success
   > used at native stopping, skill/history and Builder case-selection boundaries.
   > Preserve the original feedback frequency and contents. Do not expose raw
   > numeric score, admissible-command lists, expert plans, walkthroughs, hidden
   > PDDL state or extra evaluator analysis to actor/updater if the selected
   > original path does not consume them. Generated Python must be confined to
   > approved action and native rule-operation capabilities. Each run records the
   > approved boundary version and all enforcement deviations.

3. **docs/01 §4 Phase 0 and §7 manifest requirements**:

   > Admission additionally requires an approved feedback-boundary version and
   > reviewed containment evidence for generated code. Diagnostic wiring using
   > synthetic responses remains scientific_evidence=false. Passing an environment
   > or embedding smoke is insufficient. Containment-induced capability/error
   > changes and embedding substitution must be reviewed separately before a
   > mechanism-faithful/common-backbone label is assigned.

The native-boolean exception and exact cadence are now approved for this audited
path. Restricted-Python/error behavior and provider/embedding substitutions still
need mechanism-impact assessment before a faithful main-experiment claim. The
bounded real connection entry is documented in docs/09; it is not main-run admission.
