# Coding-Agent Handoff: Action Index + Chinese Human Review

> Date: 2026-09-16
> Branch: `exp/minimal-exploratory-memory-validation`
> Primary plan: `docs/55_action_index_and_chinese_human_review_plan.md`

Copy the prompt below directly into the coding agent.

---

```text
You are starting without assuming a local repository checkout.

Repository:
https://github.com/wudixzy/memory.git

Target branch:
exp/minimal-exploratory-memory-validation

Do NOT work on main.

Bootstrap:

git clone https://github.com/wudixzy/memory.git
cd memory
git fetch origin
git switch exp/minimal-exploratory-memory-validation

If needed:

git switch -c exp/minimal-exploratory-memory-validation \
  --track origin/exp/minimal-exploratory-memory-validation

Verify:

git status
git branch --show-current
git log -5 --oneline

The active branch must be:

exp/minimal-exploratory-memory-validation

If clone/fetch/push authentication fails, report the exact error. Do not create an unrelated replacement project.

READ FIRST, IN THIS ORDER:

1. AGENTS.md
2. docs/55_action_index_and_chinese_human_review_plan.md
3. docs/54_cleanup_attribution_validation_results.md
4. docs/52_cleanup_attribution_validation_plan.md
5. current code under experiments/exploratory_memory_mvp/

This cycle has exactly two goals:

A. perform the final harness sanity check by replacing free-form exact action strings with action-index selection over current admissible actions;
B. produce a Chinese human-review package from representative real experiment artifacts.

Do NOT redesign the scientific method.

============================================================
PART A — ACTION-INDEX ACTOR INTERFACE
============================================================

The scientific action decision is:

    choose one action from current_state.admissible_actions

The model should no longer be required to reproduce the exact environment action string.

CHANGE THE ACTOR OUTPUT CONTRACT FROM SOMETHING LIKE:

{
  "action": "take apple_3 from fridge_1",
  "probe_status": "ACTIVE"
}

TO:

{
  "action_index": 7,
  "probe_status": "ACTIVE"
}

Use ZERO-BASED indexing.

The current_state.admissible_actions list order shown to the model is authoritative and must remain stable within that decision call.

The harness resolves:

    resolved_action = current_state.admissible_actions[action_index]

and executes resolved_action exactly.

The model still makes the semantic action choice. Deterministic code only performs exact lookup.

DO NOT silently clamp, correct, or reinterpret invalid indices.

Reject:

- bool values (Python bool is an int subclass; reject explicitly);
- non-integer values;
- negative indices;
- out-of-range indices.

For every actor step save:

- ordered current admissible action list;
- returned action_index;
- resolved exact action string;
- index-validation result;
- probe_status;
- environment result / observation.

The actor prompt should explicitly say, in substance:

    Read current_state.admissible_actions in the exact order provided.
    Choose exactly one entry by returning its zero-based action_index.
    Do not rewrite, paraphrase, or reconstruct the action string.

Keep all existing scientific semantics unchanged:

- stepwise execution;
- latest observation/current admissible actions;
- established memory;
- exploratory H;
- probe_runtime_state;
- visited-candidate factual bookkeeping;
- probe_status semantics;
- H active -> consumed lifecycle;
- runtime H retention until evidence/abort;
- continuation of the original task.

Do not change H/C/A to make the action-index test easier.

------------------------------------------------------------
ACTION-INDEX SANITY RUN
------------------------------------------------------------

Use the existing Apple/Microwave negative-target case from the cleanup cycle:

source:
P005 SoapBottle-417

target:
pick_clean_then_place_in_recep-Apple-None-Microwave-14/
trial_T20190909_120203_117379

Keep fixed:

- qwen3.8-flash
- thinking=false
- temperature=0
- same target seed
- same established memory
- same cleaned source-generated H
- same probe_runtime_state semantics
- same step cap

Run a small repetition check only:

E0: 3 runs
E1: 3 runs

Do not optimize prompt/case selection inside these repetitions.

Report:

run | condition | all indices valid? | task won? | steps | H activated? | evidence ready? | H removed?

Interpretation:

1. If exact-action failures disappear and E0 becomes substantially more stable:
   => prior E0 failures were dominated by actor action-string transport noise.

2. If every action index is mechanically valid but E0 still often fails semantically:
   => base actor reasoning/execution reliability remains a confound.

Do not add a planner or more rules after this result.

============================================================
PART B — CHINESE HUMAN-REVIEW PACKAGE
============================================================

The researcher wants to manually inspect representative REAL samples.

Do not create only a high-level Chinese summary.

The review package must expose the actual model-facing/model-generated content in a readable bilingual form.

------------------------------------------------------------
SOURCE OF TRUTH
------------------------------------------------------------

Prefer original runtime artifacts whenever available:

b_input.json
b_prompt.json
b_raw_response.json / b_parsed.json
c_input.json
c_prompt.json
c_raw_response.json / c_parsed.json
target_h_actor_view.json
actor step actor_input/prompt/raw/parsed/environment_result files
a_input.json
a_prompt.json
a_raw_response.json / a_parsed.json

Runtime artifacts are gitignored.

Therefore:

1. check whether the current environment already contains the referenced artifact directories from docs/45, 48, 51, and 54;
2. if present, use those original files;
3. if absent in a fresh clone, regenerate ONLY the minimal representative samples under the frozen existing configuration;
4. do NOT rerun the entire experiment suite just to prepare documentation.

For every review sample mark:

    Artifact provenance: ORIGINAL SAVED ARTIFACT

or:

    Artifact provenance: RECONSTRUCTED REPRODUCTION

Do not hide this distinction.

------------------------------------------------------------
TRANSLATION RULES
------------------------------------------------------------

For important English text:

- preserve the original English;
- provide a faithful Chinese translation;
- do not silently simplify technical meaning;
- keep exact action strings, IDs, JSON keys, model names, file paths, and code unchanged in code formatting;
- translate surrounding natural language;
- do not invent hidden reasoning;
- do not present your interpretation as if it were the model's output.

For long repetitive ALFWorld observations:

- retain the full raw original in a details block / appendix or artifact reference;
- provide a Chinese task-relevant rendering in the main view;
- do not omit evidence relevant to the research interpretation.

------------------------------------------------------------
REVIEW PACKAGE LOCATION
------------------------------------------------------------

Create a directory like:

docs/human_review/

Recommended structure:

README_zh.md
01_b_open_and_controls_zh.md
02_c_and_h_zh.md
03_laptop_online_attribution_zh.md
04_cross_task_transfer_zh.md
05_a_reconciliation_zh.md

You may combine files if that materially improves readability, but keep the review package easy to navigate.

------------------------------------------------------------
REPRESENTATIVE SAMPLES
------------------------------------------------------------

Do not translate everything. Use a compact but scientifically representative set.

SAMPLE A — B POSITIVE OPEN

Use a clean positive case such as P002 or P005.

Show:

- task / context;
- pre-update established memory;
- compact current trajectory;
- B-critical prompt instructions;
- exact B visible output;
- Functional Contract;
- evaluator-side expected OPEN rationale, clearly marked as evaluator-only and never shown to B.

SAMPLE B — B NEGATIVE CONTROL

Include at least one N1 or N2.

Show:

- what B saw;
- exact NONE output / evidence fields;
- why this control differs from the OPEN case.

SAMPLE C — CLEAN C / H SYNTHESIS

Use cleaned P002 or P005 from the latest cycle.

Show:

- fact-only local C packet;
- relevant capabilities;
- C-critical prompt instructions;
- exact C output;
- source_grounding;
- future_exploratory_memory / target actor H after source grounding/provenance has been stripped.

This sample is important for judging whether C independently synthesized the alternative.

SAMPLE D — LAPTOP ATTRIBUTION

Show the SAME original H across:

1. original online trace that loops;
2. mechanical probe_runtime_state added;
3. corrected successful trace.

Show explicitly:

- what information changed;
- what did NOT change;
- compact step-by-step tables;
- Chinese explanation of why this is an interface/state-representation attribution test.

SAMPLE E — POSITIVE / NEUTRAL CROSS-TASK TRANSFER

Use SprayBottle or another clean completed transfer.

Show:

- source H;
- different target task;
- E0 compact trace;
- E1 compact trace;
- H activation;
- target-time grounding;
- evidence-ready status;
- H removal;
- downstream completion;
- E1-only A output.

Make clear when E0 independently chose the same route, so this is mechanism evidence rather than an incremental cost effect.

SAMPLE F — NEGATIVE-EVIDENCE TRANSFER

Use the Apple/Microwave case AFTER action-index sanity runs.

Show at least one clean E1 trajectory including:

- open-surface attempts;
- negative local observations;
- adaptive move into closed storage;
- target acquisition;
- evidence-ready status;
- H runtime removal;
- downstream clean/place continuation.

Also summarize the E0/E1 action-index repetition results.

Do not claim a clean causal advantage if E0 remains unstable.

SAMPLE G — A CONSERVATISM

Include at least:

- one NO_CHANGE output;
- one UPDATE / REFINE output.

Show:

- actual E1 evidence package visible to A;
- exact A prompt-critical instructions;
- exact A output;
- Chinese review notes asking whether scope/guidance is justified or too strong.

This may be combined with Samples E/F.

------------------------------------------------------------
PER-SAMPLE FORMAT
------------------------------------------------------------

Use a consistent format close to:

# Sample ...

## 0. 为什么选择这个样本

## 1. Task / Context
### Original English
...
### 中文翻译
...

## 2. Memory / Evidence shown to model
### Original English / JSON
...
### 中文翻译与字段说明
...

## 3. Prompt-critical instructions
### Original English
...
### 中文翻译
...

## 4. Model output
### Original English / JSON
...
### 中文翻译与字段说明
...

## 5. Execution trace
| step | observation summary | admissible/action decision | probe status | 中文说明 |

For the action-index implementation include BOTH:

- action_index
- resolved exact action

## 6. Outcome / A update
...

## 7. 人工 Review 问题
- ...

Do not replace exact model outputs with only your own prose summary.

------------------------------------------------------------
README_ZH
------------------------------------------------------------

README_zh.md should contain:

1. one-page Chinese overview of the current method:

   B -> C -> H -> Online Probe -> Evidence -> A

2. glossary:

   established memory
   exploratory memory / H
   Functional Contract
   probe policy
   source grounding
   probe_runtime_state
   EVIDENCE_OBTAINED / PROBE_EVIDENCE_READY
   A reconciliation

3. sample index;
4. provenance/reconstruction status for each sample;
5. reviewer checklist.

Reviewer checklist should cover:

B:
- comparison 是否真的值得打开？
- NONE 是否合理？

C:
- 输入是否只有局部事实？
- C 是否自己提出了 alternative？
- H 是否过具体或过抽象？

Online:
- H 是否真正改变/约束了局部行为？
- 是否只是 prompt 直接指定动作？
- probe termination 是否合理？
- negative evidence 后 continuation 是否自然？

A:
- 是否只依据 E1 真实 evidence？
- UPDATE 是否过度泛化？
- NO_CHANGE 是否过于保守？

Overall:
- controlled experiments 真正支持了哪几层机制？
- 哪些结论仍只是 qualitative evidence？

------------------------------------------------------------
NO CHERRY PICKING / NO METHOD PATCHING
------------------------------------------------------------

When preparing the human-review package:

- do not modify B/C/H/A prompts to make examples cleaner;
- do not repeatedly rerun a sample just to select the most favorable output;
- do not omit inconvenient failures;
- do not add semantic grading rules;
- do not translate your interpretation as model output.

If reconstruction is necessary, use the first valid reproduction under the frozen configuration and mark it as reconstructed.

============================================================
TESTS
============================================================

Add focused tests for action-index behavior:

1. actor schema uses action_index rather than free-form action;
2. zero-based indexing is explicit;
3. bool is rejected;
4. negative index is rejected;
5. out-of-range index is rejected;
6. resolved action equals admissible_actions[action_index];
7. step artifacts store both index and resolved action;
8. E0 and E1 use the same index interface;
9. H lifecycle is unchanged;
10. probe_runtime_state is unchanged;
11. evaluator isolation is unchanged;
12. failure artifacts remain preserved.

Do not make phrase checks the scientific semantic evaluator.

============================================================
RESULT REPORT
============================================================

Add a concise tracked result report under docs/, separate from the human-review package.

It should report:

ACTION INDEX:
- implementation change;
- Apple E0 3-run result;
- Apple E1 3-run result;
- whether invalid exact-action-string failures disappeared;
- whether remaining failures are semantic actor failures.

HUMAN REVIEW PACKAGE:
- files created;
- samples included;
- which samples used original artifacts vs reconstructed reproductions;
- any artifact that could not be faithfully recovered.

FINAL RECOMMENDATION:
- whether mechanism debugging should stop;
- whether the next work should be paper-level evaluation design.

============================================================
GIT / SUBMISSION
============================================================

Before commit:

git status
git diff
git diff --check

Run focused tests, Ruff, and compile checks.

Do not commit:

- .env
- API keys
- cookies
- credentials
- downloaded benchmark runtime data
- large raw runtime artifacts unless they are deliberately reduced/sanitized review excerpts

The human-review Markdown files ARE intended to be tracked.

Commit and push to the existing branch:

git add <relevant files>
git commit -m "exp: add action-index actor and Chinese review package"
git push origin exp/minimal-exploratory-memory-validation

Do not force-push.

At completion report:

- final commit SHA;
- changed files;
- tests/checks run;
- Apple action-index E0/E1 results;
- review-package files;
- original vs reconstructed provenance;
- any remaining implementation/model/method uncertainty.
```
