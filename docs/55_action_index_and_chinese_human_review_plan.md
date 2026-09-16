# Action-Index Sanity Check and Chinese Human-Review Plan

> Date: 2026-09-16
> Branch: `exp/minimal-exploratory-memory-validation`
> Previous result: `docs/54_cleanup_attribution_validation_results.md`

## 1. Purpose

The exploratory-memory MVP has reached a point where further core-method patching is not justified by the current evidence.

This cycle has only two goals:

1. remove one remaining harness-level failure surface by replacing free-form exact action-string generation with **action-index selection** over the environment's current admissible actions;
2. produce a **Chinese human-review package** from representative real experiment artifacts so the research design, prompts, model judgments, online traces, and A updates can be inspected directly by a human researcher.

This cycle is not a new method experiment and must not introduce new B/C/H/A modules.

---

## 2. Frozen scientific design

Keep the current conceptual structure unchanged:

```text
B: identify a policy-relevant unresolved comparison in the incumbent behavior

C: synthesize one grounded local probe policy

H: one-shot exploratory memory / future-facing experimental guidance

Online: stepwise execution from current observations and current affordances

A: conservatively absorb only the evidence actually observed in the executed episode
```

Freeze:

- B prompt/schema/responsibility;
- Functional Contract semantics;
- C local-input boundary;
- source grounding vs. future-facing H separation;
- probe-policy H representation;
- `active -> consumed` persistent H lifecycle plus same-episode runtime guidance;
- mechanical `probe_runtime_state` as factual progress state;
- E1-only A information boundary;
- Stage 1 bypass for the current mechanism-validation work.

Do not add retrieval, graph memory, semantic search controllers, VOI scores, strategy taxonomies, or rule-based fallback planners.

---

# Part A — Action-index actor interface

## 3. Motivation

The latest negative-target experiment showed that the Qwen actor can occasionally produce an inadmissible exact action string even though the authoritative current `admissible_actions` list is present.

For example, the actor may semantically intend to select a currently available take action but reproduce the wrong object suffix in text.

That failure is not part of the research question.

The relevant semantic decision is:

```text
Which currently admissible action should the actor choose?
```

not:

```text
Can the model perfectly reproduce the environment's exact action string?
```

Therefore change only the actor-output transport contract.

---

## 4. New actor output contract

At every step the actor still receives the full current state and ordered list:

```json
{
  "current_state": {
    "observation": "...",
    "admissible_actions": [
      "look",
      "go to countertop_1",
      "open fridge_1"
    ]
  }
}
```

The actor should return:

```json
{
  "action_index": 2,
  "probe_status": "NOT_ACTIVE | ACTIVE | EVIDENCE_OBTAINED | ABORTED"
}
```

Use **zero-based indexing**:

```text
0 <= action_index < len(current_state.admissible_actions)
```

The harness resolves:

```python
action = current_state["admissible_actions"][action_index]
```

and executes that exact string.

The model still chooses the action. Deterministic code only performs exact string lookup.

---

## 5. Mechanical validation and audit artifacts

For each actor step save at least:

```text
current admissible action list with stable order
action_index returned by model
resolved exact action string
index validation result
probe_status
environment observation/result
```

Validation should reject:

- non-integer indices;
- booleans masquerading as integers;
- negative indices;
- out-of-range indices;
- malformed probe status.

Do not silently clamp or reinterpret an invalid index.

The existing exact-current-action validator may remain useful after resolution, but an in-range index into the exact current list should mechanically imply membership.

---

## 6. Prompt semantics

Change only the action-selection format.

The actor prompt should explicitly say:

```text
Read current_state.admissible_actions in the exact order provided.
Choose exactly one entry by returning its zero-based action_index.
Do not rewrite, paraphrase, or reconstruct the action string.
```

Keep existing semantics for:

- current observation;
- established memory;
- exploratory memory;
- `probe_runtime_state`;
- avoiding unnecessary revisits;
- probe-status meanings;
- one-shot lifecycle;
- continuation of the original task.

Do not change H to improve this test.

---

## 7. Minimal sanity experiment

Use the existing Apple/Microwave target from the cleanup cycle:

```text
source: P005 SoapBottle-417
target: pick_clean_then_place_in_recep-Apple-None-Microwave-14/
        trial_T20190909_120203_117379
```

Keep fixed:

```text
qwen3.8-flash
thinking=false
temperature=0
same target seed
same established memory
same source-generated H
same step cap
same probe_runtime_state semantics
```

Run a small number of repetitions sufficient to check the harness failure mode, e.g.:

```text
E0: 3 runs
E1: 3 runs
```

Do not search over prompts or cases inside this check.

Record:

```text
run
condition
all action indices valid?
task completed?
steps
H activated?       # E1
probe evidence ready?  # E1
H removed?         # E1
```

Interpretation:

```text
E0 becomes mechanically stable and task failures substantially disappear
=> prior failures were dominated by exact-action output interface noise.

All indices are valid but E0 still frequently fails semantically
=> base actor reasoning/execution capability is the remaining confound.
```

Do not respond to semantic E0 failures by adding a planner or semantic rules.

This is the final harness sanity check before planning broader evaluation.

---

# Part B — Chinese human-review package

## 8. Purpose of the review package

The researcher needs to inspect representative real samples directly rather than relying on aggregate reports.

The package should make it easy to answer:

- Did B identify the right question?
- Did C receive only appropriate local information?
- Did C independently synthesize a sensible probe?
- Is H appropriately scoped and future-facing?
- Does the online actor follow H without being over-controlled?
- Is probe termination sensible?
- Does A update only what the actual evidence supports?
- Are there hidden prompt/data artifacts that make a result easier than it appears?

The package is for **manual scientific review**, not presentation polish.

---

## 9. Source-of-truth policy

Whenever available, build the review package from original runtime artifacts:

```text
b_input.json
b_prompt.json
b_raw_response.json / b_parsed.json
c_input.json
c_prompt.json
c_raw_response.json / c_parsed.json
target_h_actor_view.json
actor step inputs/prompts/responses/environment results
a_input.json
a_prompt.json
a_raw_response.json / a_parsed.json
```

Do not reconstruct model outputs from the prose reports if raw artifacts exist.

Runtime artifacts are gitignored. Therefore:

1. first check whether the current working environment already contains the referenced artifact directories;
2. if they exist, use them directly;
3. if a fresh checkout lacks them, regenerate only the minimal representative cases using the frozen existing code/configuration;
4. do not rerun the entire experimental suite merely to produce the review package.

Clearly mark whether each reviewed artifact is:

```text
original saved artifact
or
reconstructed reproduction
```

---

## 10. Translation policy

For every important English model-facing/model-generated text:

- preserve the original English;
- provide a faithful Chinese translation immediately below or beside it;
- do not silently simplify technical meaning;
- keep exact action strings, entity IDs, JSON field names, model names, and file paths unchanged in code formatting;
- translate explanatory natural language around them.

For long observations containing repetitive environment boilerplate, it is acceptable to:

```text
preserve the complete original in a collapsible/details block or appendix
+
provide a concise Chinese rendering highlighting task-relevant content
```

but do not omit evidence that matters to the scientific interpretation.

Do not invent reasoning that is not present in the visible model output.

---

## 11. Recommended representative sample set

Create a compact set rather than translating everything.

### Sample A — B positive OPEN

Prefer one of the clean search cases, e.g. P002 or P005.

Show:

```text
current task
current trajectory summary
pre-update memory
B prompt instructions
B visible output
Functional Contract
why the evaluator expected OPEN
```

### Sample B — B negative control

Include at least one N1 or N2 case.

Show why B returned `NONE` and whether the distinction from Sample A is convincing.

### Sample C — clean C/H synthesis

Use cleaned P002 or P005.

Show:

```text
fact-only local C packet
relevant capability packet
C prompt
C output
source_grounding
future-facing H after source grounding is stripped
```

This is important for checking whether C independently proposed the alternative.

### Sample D — Laptop interface attribution

Show side-by-side:

```text
original H
old online trace that loops
new mechanical probe_runtime_state
corrected trace that succeeds
```

Make explicit what information changed and what did not.

### Sample E — positive/neutral cross-task transfer

Use SprayBottle or another clean completed transfer.

Show:

```text
source H
target task
E0 compact trace
E1 compact trace
probe activation/evidence/termination
task continuation
A E1-only output
```

### Sample F — negative-evidence transfer

Use the Apple/Microwave case after action-index sanity runs.

Show at least one clean E1 trace where:

```text
surface probe is negative
search adapts to closed storage
probe reaches evidence-ready status
H runtime guidance ends
downstream clean/place task completes
```

Also summarize the E0 reliability result from the action-index runs.

### Sample G — A conservatism comparison

Include representative:

```text
NO_CHANGE
and
UPDATE / REFINE
```

Show the actual E1 evidence and A's exact output so a human can judge whether the scope/guidance is too strong.

These may be combined with Samples E/F if duplication would be excessive.

---

## 12. Review-document organization

Prefer a dedicated directory such as:

```text
docs/human_review/
  README_zh.md
  01_b_open_and_controls_zh.md
  02_c_and_h_zh.md
  03_laptop_online_attribution_zh.md
  04_cross_task_transfer_zh.md
  05_a_reconciliation_zh.md
```

Exact file split may change if a simpler organization is clearer.

`README_zh.md` should provide:

- a one-page overview of the current method;
- sample index;
- artifact provenance / reconstruction status;
- a short checklist for the human reviewer.

---

## 13. Per-sample formatting

For each sample use a consistent structure:

```markdown
# Sample ...

## 0. Why this sample matters

## 1. Task / context
### Original English
### 中文翻译

## 2. Memory shown to the model
### Original English
### 中文翻译

## 3. Prompt-critical instructions
### Original English
### 中文翻译

## 4. Model output
### Original English / JSON
### 中文翻译与字段解释

## 5. Execution trace
| step | current observation summary | admissible/action choice | probe status | 中文说明 |

## 6. Outcome / A update

## 7. Human-review questions
- ...
```

Do not replace the real model text with only a narrative summary.

---

## 14. Trace presentation

For long actor traces, provide both:

### Compact table

Example:

| Step | State summary | Chosen action | Probe status | 中文解释 |
|---|---|---|---|---|

### Raw evidence reference

Point to the artifact path or include the relevant raw JSON in a collapsible block.

For the action-index version, show both:

```text
action_index
resolved exact action
```

so human reviewers can verify the new harness does not alter the semantic action choice.

---

## 15. Reviewer checklist

End the review index with questions such as:

### B
- B 打开的 comparison 是否确实值得探索？
- N1/N2 被关闭是否合理？

### C
- 输入是否只包含局部相关事实？
- C 是否真的提出了新 realization，而不是从输入里抄答案？
- H 是否过度具体或过度抽象？

### Online
- H 是否改变了行为？
- actor 是否只是被 prompt 强行指定了动作？
- probe 的 evidence goal / stop timing 是否合理？
- negative evidence 后的 continuation 是否自然？

### A
- A 是否只根据真正观察到的 E1 evidence 更新？
- 是否存在过度泛化？
- `NO_CHANGE` 是否过于保守？

### Overall
- 当前 controlled validation 是否真实支持核心机制？
- 哪些结论仍然只能算 qualitative evidence？

---

## 16. No new scientific mechanism during review preparation

While preparing the Chinese review package do not:

- alter B/C/H/A prompts to make examples cleaner;
- cherry-pick a different output by repeatedly rerunning the same sample unless reconstruction is required;
- remove inconvenient failures from the review package;
- add a semantic grader;
- turn Chinese translation into an interpretation presented as model output.

The purpose is auditability.

---

## 17. Required tests for action-index implementation

Add focused tests covering:

1. actor accepts `action_index`, not a free-form action string;
2. zero-based indexing is explicit;
3. booleans are rejected as indices;
4. negative/out-of-range indices are rejected;
5. exact resolved action equals `admissible_actions[action_index]`;
6. step artifacts persist both index and resolved action;
7. E0/E1 both use the same action-index interface;
8. H lifecycle and `probe_runtime_state` remain unchanged;
9. evaluator isolation remains unchanged;
10. failure artifacts remain preserved.

Do not alter the scientific semantics while implementing these tests.

---

## 18. Deliverables

This cycle should produce:

1. action-index actor interface;
2. Apple E0/E1 sanity repetitions and a concise result memo;
3. Chinese human-review package built from representative real artifacts;
4. provenance/reconstruction notes for every reviewed sample;
5. no new method module.

After this, stop mechanism patching and use the human review to decide whether the project is ready to move into paper-level evaluation design.
