# AGENTS.md

This file defines the implementation contract for coding agents on branch:

```text
exp/minimal-exploratory-memory-validation
```

This branch is finishing the controlled mechanism-validation stage for exploratory persistent memory.

Older H1-H4 / AppWorld priorities and previous cleanup-cycle instructions do not override this file.

## 1. Current objective

The core B/C/H/Online/A method is frozen for this cycle.

Perform only two tasks:

1. replace free-form exact actor action-string generation with a deterministic **action-index harness** over the authoritative current `admissible_actions` list;
2. create a **Chinese bilingual human-review package** from representative real experiment artifacts.

The purpose is to remove one irrelevant action-string reproduction failure mode and then enable direct manual scientific review before broader evaluation design.

Do not add a new method module.

---

## 2. Required read order

Before coding, read:

1. `docs/55_action_index_and_chinese_human_review_plan.md`
2. `docs/56_coding_agent_prompt_action_index_and_chinese_review.md`
3. `docs/54_cleanup_attribution_validation_results.md`
4. current code under `experiments/exploratory_memory_mvp/`
5. this file

Docs 55–56 define the current cycle.

---

## 3. Freeze the scientific design

Do not redesign:

```text
B: identify a policy-relevant unresolved incumbent comparison

C: synthesize one grounded local probe policy

H: one-shot exploratory memory / future-facing experimental guidance

Online: stepwise execution from current observations and affordances

A: conservatively absorb only actually observed episode evidence
```

Keep frozen:

- B prompt/schema/responsibility;
- Functional Contract semantics;
- C local-input boundary;
- fact-only local C packets;
- source grounding vs. future-facing H separation;
- H probe-policy representation;
- `probe_runtime_state` as mechanical public progress state;
- persistent `active -> consumed` H lifecycle plus same-episode runtime guidance;
- E1-only A boundary;
- Stage 1 bypass for this validation work.

Do not add retrieval, graph memory, search controllers, semantic planners, VOI scores, strategy/context taxonomies, or rule-based fallbacks.

---

# Part A — Action-index actor interface

## 4. Scientific semantics

The actor's semantic decision is:

```text
choose one member of current_state.admissible_actions
```

It is not scientifically relevant whether the model can perfectly reproduce an environment-specific exact action string.

Therefore the model selects an index and deterministic code resolves it to the exact environment string.

This is a harness/interface change, not a method change.

---

## 5. Actor output contract

At every decision call, preserve the exact ordered list:

```text
current_state.admissible_actions
```

The actor returns exactly one zero-based integer index plus probe status, conceptually:

```json
{
  "action_index": 3,
  "probe_status": "NOT_ACTIVE | ACTIVE | EVIDENCE_OBTAINED | ABORTED"
}
```

Resolve mechanically:

```python
resolved_action = current_state["admissible_actions"][action_index]
```

Use zero-based indexing.

Do not let the actor return/reconstruct a free-form action string in the new main interface.

---

## 6. Index validation

Reject mechanically:

- booleans;
- non-integer indices;
- negative indices;
- indices outside the current action-list range.

Do not clamp or repair invalid indices.

For each step persist:

- ordered admissible-action list;
- returned `action_index`;
- resolved exact action;
- validation result;
- probe status;
- environment result.

The model chooses the semantic action. Code only performs exact lookup.

---

## 7. Actor prompt

Tell the actor explicitly:

```text
Read current_state.admissible_actions in the exact order provided.
Return the zero-based action_index of exactly one entry.
Do not rewrite, paraphrase, or reconstruct the action string.
```

Keep all existing semantics unchanged:

- current observation;
- current admissible actions;
- established memory;
- exploratory H;
- `probe_runtime_state`;
- executed action history;
- avoiding unnecessary revisits;
- probe status semantics;
- task continuation after H ends.

Do not change C/H/A to improve action-index results.

---

## 8. Action-index sanity experiment

Use only the existing Apple/Microwave target from the latest cleanup report:

```text
source: P005 SoapBottle-417

target:
pick_clean_then_place_in_recep-Apple-None-Microwave-14/
trial_T20190909_120203_117379
```

Keep fixed:

```text
qwen3.8-flash
thinking=false
temperature=0
same target seed
same established memory
same cleaned source-generated H
same step cap
same probe_runtime_state semantics
```

Run a small repetition check only:

```text
E0: 3 runs
E1: 3 runs
```

Do not search over prompts/cases during these repetitions.

This check asks only whether exact-action-string errors disappear and whether the remaining actor failures are semantic rather than transport noise.

After this check, stop harness patching.

---

# Part B — Chinese human-review package

## 9. Purpose

The researcher needs to inspect representative real samples directly.

Create a tracked bilingual review package under a directory such as:

```text
docs/human_review/
```

The package must expose actual model-facing/model-generated material, not only high-level summaries.

---

## 10. Source-of-truth rule

Prefer original runtime artifacts when they exist locally.

Relevant sources include:

```text
b_input / prompt / raw / parsed
c_input / prompt / raw / parsed
future target H
stepwise actor inputs / prompts / outputs / environment results
a_input / prompt / raw / parsed
```

Runtime artifacts are normally gitignored.

Therefore:

1. first inspect whether prior artifact directories are present in the current working environment;
2. use them directly when available;
3. on a fresh clone, regenerate only the minimal representative cases under the frozen configuration;
4. never rerun the full experimental suite solely to create documentation.

For every sample clearly state:

```text
ORIGINAL SAVED ARTIFACT
```

or:

```text
RECONSTRUCTED REPRODUCTION
```

Do not hide provenance.

---

## 11. Translation rule

For important natural-language material:

- preserve original English;
- provide faithful Chinese translation;
- keep exact JSON keys, IDs, action strings, model names, file paths, and code unchanged in code formatting;
- do not invent hidden reasoning;
- do not present reviewer interpretation as model output.

Long repetitive environment observations may be compacted in the main view only if the full original is preserved in a details block, appendix, or explicit artifact reference.

---

## 12. Required representative samples

Create a compact set covering at least:

### A. B positive OPEN

Use P002 or P005.

Show task, memory, current trajectory summary, B-critical instructions, exact visible B output, Functional Contract, and evaluator-only expected rationale clearly separated.

### B. B negative control

Include at least one N1 or N2.

Show why B returned NONE and whether the contrast with the OPEN case is convincing.

### C. Clean C/H synthesis

Use the latest fact-only P002 or P005 run.

Show local C packet, relevant capabilities, prompt-critical instructions, exact C output, source grounding, and the future-facing H after source grounding is stripped.

### D. Laptop attribution

Show the same old H across:

```text
old looping trace
vs.
mechanical probe_runtime_state
vs.
new successful trace
```

Make explicit what changed and what remained fixed.

### E. Positive/neutral cross-task transfer

Use SprayBottle or another clean completed transfer.

Show E0/E1 compact traces, H activation, target grounding, evidence-ready status, H removal, continuation, and E1-only A output.

### F. Negative-evidence Apple transfer

Use the Apple/Microwave case after the action-index sanity runs.

Show a clean E1 trajectory and summarize the E0/E1 repetition results without overstating causal benefit.

### G. A conservatism

Include at least one `NO_CHANGE` and one `UPDATE / REFINE` example with the actual E1 evidence visible to A.

Samples may be combined to avoid duplication.

---

## 13. Review-document structure

Prefer files similar to:

```text
docs/human_review/
  README_zh.md
  01_b_open_and_controls_zh.md
  02_c_and_h_zh.md
  03_laptop_online_attribution_zh.md
  04_cross_task_transfer_zh.md
  05_a_reconciliation_zh.md
```

`README_zh.md` should contain:

- concise Chinese method overview;
- glossary;
- sample index;
- original-vs-reconstructed provenance;
- reviewer checklist.

Each sample should include, as applicable:

```text
why the sample matters
original English
Chinese translation
model-visible memory/evidence
prompt-critical instructions
exact visible model output
compact execution table
raw artifact reference
outcome / A update
human-review questions
```

For the action-index interface show both:

```text
action_index
resolved exact action
```

---

## 14. Review integrity

Do not:

- alter B/C/H/A prompts to create cleaner examples;
- repeatedly rerun cases to cherry-pick a favorable output;
- hide inconvenient failures;
- add semantic graders;
- translate your interpretation as though it were model text.

If reconstruction is required, use the first valid reproduction under the frozen setup and label it reconstructed.

---

## 15. Tests

Add focused tests for action-index mechanics:

1. actor accepts `action_index` instead of free-form action;
2. zero-based indexing is explicit;
3. bool is rejected;
4. negative index is rejected;
5. out-of-range index is rejected;
6. resolved exact action equals `admissible_actions[action_index]`;
7. artifacts preserve both index and resolved action;
8. E0/E1 use the same interface;
9. H lifecycle remains unchanged;
10. probe runtime state remains mechanical;
11. evaluator isolation remains intact;
12. failure artifacts remain auditable.

Do not confuse fixture sanity checks with semantic scientific evaluation.

---

## 16. Required result memo

Add one concise tracked result report outside the human-review directory containing:

### Action index

- implementation change;
- Apple E0 ×3 results;
- Apple E1 ×3 results;
- invalid-index count;
- task success/steps;
- whether prior exact-action-string failures disappeared;
- whether any remaining failures are semantic actor failures.

### Human review

- files produced;
- samples covered;
- original-vs-reconstructed provenance;
- any artifact that could not be faithfully recovered.

### Recommendation

State whether mechanism debugging should stop and the project should move to paper-level evaluation design.

---

## 17. Explicit non-goals

Do not add:

- B redesign;
- C/H redesign;
- A redesign;
- new benchmark integration;
- retrieval;
- Stage 1;
- graph memory;
- search controllers;
- rule-based planning;
- generic-exploration baseline;
- publication-scale evaluation.

This is a final harness sanity + human audit cycle.

---

## 18. Git discipline

Never commit secrets or large raw runtime directories.

The reduced/sanitized bilingual Markdown review package is intended to be tracked.

Before commit:

```bash
git status
git diff
git diff --check
```

Run focused tests, Ruff, and compile checks.

Commit/push to:

```text
exp/minimal-exploratory-memory-validation
```

Do not force-push.

After this cycle, stop mechanism patching unless human review reveals a concrete scientific flaw.
