# Coding-Agent Handoff: C Probe-Policy + Stepwise Online Retest

> Date: 2026-09-16  
> Repository: `https://github.com/wudixzy/memory.git`  
> Branch: `exp/minimal-exploratory-memory-validation`  
> Primary plan: `docs/46_c_probe_policy_and_stepwise_online_plan.md`

## Bootstrap

If there is no local checkout:

```bash
git clone https://github.com/wudixzy/memory.git
cd memory
git fetch origin
git switch exp/minimal-exploratory-memory-validation
```

If needed:

```bash
git switch -c exp/minimal-exploratory-memory-validation \
  --track origin/exp/minimal-exploratory-memory-validation
```

Verify before doing any work:

```bash
git status
git branch --show-current
git log -5 --oneline
```

The active branch must be:

```text
exp/minimal-exploratory-memory-validation
```

Do not work on `main`.

If clone/fetch/push authentication fails, report the exact error. Do not create an unrelated replacement project.

---

# 1. Read order

Read in this order:

1. `AGENTS.md`
2. `docs/46_c_probe_policy_and_stepwise_online_plan.md`
3. `docs/45_b_c_boundary_corrected_retest_results.md`
4. `experiments/exploratory_memory_mvp/prompts.py`
5. `experiments/exploratory_memory_mvp/common.py`
6. `experiments/exploratory_memory_mvp/run_c.py`
7. `experiments/exploratory_memory_mvp/run_online_pair.py`
8. `experiments/exploratory_memory_mvp/alfworld_carrier.py`

The previous B cycle is complete enough for this MVP. Do not reopen B design unless you find a concrete implementation/reproducibility bug.

---

# 2. Scientific objective

The current target is:

```text
frozen corrected B
  -> C creates one grounded local probe policy
  -> exploratory memory stores that probe
  -> stepwise online actor sees the memory
  -> actor performs the probe against real observations
  -> probe yields comparative evidence
  -> actor continues the original task
```

The key design correction is:

```text
C should NOT emit a pre-expanded open-loop action program.
C should emit a capability-grounded local probe specification/policy.
```

And:

```text
the online actor must decide one action at a time from the latest observation,
not plan the complete future sequence from the initial state.
```

---

# 3. Freeze B

Do not change B's scientific role, prompt, or corrected public input representation.

Keep:

```text
B: Which incumbent comparison is worth opening?
```

B must remain separate from concrete alternative synthesis.

Do NOT:

- give B `capabilities.json`;
- make B propose an alternative;
- change OPEN/NONE criteria to improve downstream results;
- add a new B heuristic/rule gate;
- expand the B evaluation set in this cycle.

If previous ignored B artifacts are unavailable in a fresh clone, rerun the existing corrected B on the five P cases only to obtain structured OPEN diagnoses. Do not modify B while doing so.

Use:

```text
qwen3.8-flash
thinking=false
temperature=0
```

---

# 4. Correct C's input boundary

The previous C context was too thin for robust target binding.

C should now receive a small public package containing:

```text
B OPEN diagnosis / functional contract
current task/instruction
relevant public current state
relevant current trajectory context
pre-update established memory
real carrier capability/action evidence
```

Do not include evaluator-only information.

Specifically exclude:

- case type P/N1/N2;
- oracle alternative actions;
- oracle outcome;
- evaluator rationale;
- hidden benchmark answer.

Add/retain explicit leakage tests.

Do not add current-task/state information to B merely because C now receives it.

---

# 5. Correct capability representation for C

The current capability document unions actions/entities observed across multiple states. That is acceptable as a vocabulary/reference source but insufficient to prove a future sequence is executable.

Keep the representation simple.

Prefer two semantic groups:

```text
entry_state_capabilities:
  public observation
  currently admissible actions
  currently visible/referenced entities

historical_capability_vocabulary:
  real action schemas / action names / public historically observed capability evidence
```

The first grounded action/anchor in C's probe must be legal in the actual probe-entry state.

Do not implement a large handcrafted transition model to predict every future legal action.

Future legality should be resolved through the stepwise online environment loop.

---

# 6. Replace C's exact action sequence with a probe specification

Change the main C output contract away from:

```json
{"actions": ["a1", "a2", "a3", "..."]}
```

Use a compact local-probe object instead.

A suggested schema is:

```json
{
  "decision": "CREATE",
  "type": "exploratory",
  "scope": "...",
  "hypothesis": "...",
  "guidance": "...",
  "probe_spec": {
    "local_function": "...",
    "grounded_start": {
      "action": "exact currently legal entry action",
      "why_grounded": "short statement"
    },
    "adaptive_policy": "short semantic local policy driven by observations",
    "evidence_goal": "what comparative evidence this probe seeks",
    "stop_conditions": ["..."],
    "required_downstream_state": "..."
  },
  "reason": "..."
}
```

You may simplify field names, but preserve the distinction:

```text
grounded starting capability
+ adaptive local policy
+ evidence goal
+ stop condition
+ downstream contract
```

C may return `NONE` when no credible grounded local probe can be formed.

Do not force CREATE.

Do not encode the evaluator oracle alternative into the prompt.

Do not make C replan the full task.

---

# 7. C validation philosophy

Use deterministic code only for genuinely mechanical checks.

Appropriate:

- JSON/schema validation;
- entry action is currently admissible;
- referenced public entity/capability exists;
- evaluator fields are absent;
- artifact logging.

Do not implement complex handcrafted semantic rules for:

- whether the probe is a good alternative;
- whether it is sufficiently informative;
- whether it is semantically local;
- whether its hypothesis is valuable.

For the five P cases, inspect these semantic properties directly from artifacts.

The P001 failure from the previous run should be used as a regression case: the new representation should not rely on a globally observed but state-invalid later action sequence.

---

# 8. C retest

Run corrected C only on the five existing P cases whose B result is OPEN.

Produce a case-level review table:

```text
case
C CREATE/NONE
correct target binding?
contract match?
grounded start action legal?
adaptive rather than open-loop?
local rather than whole-task replan?
potentially informative?
```

Do not add a large automatic semantic grader.

Use direct review plus mechanical entry-action validation.

Only cases that pass this review should proceed to online E0/E1.

---

# 9. Rewrite online execution as a true stepwise loop

The current actor's one-shot full-plan behavior does not match the intended method.

Replace it with:

```text
for each decision step:
    observe latest public state
    obtain current admissible actions
    provide task + established memory (+ exploratory memory in E1)
    ask actor for ONE next action
    validate action is currently admissible
    execute action
    store new observation
    continue until task done or step cap
```

Actor output should be minimal, for example:

```json
{
  "action": "exact currently admissible action",
  "probe_status": "NOT_ACTIVE | ACTIVE | EVIDENCE_OBTAINED | ABORTED"
}
```

The actor must not emit an entire future plan.

Persist every step's:

- actor prompt/input;
- visible response;
- selected action;
- current admissible actions;
- environment observation/result;
- probe status;
- token/cost telemetry.

Do not depend on hidden chain-of-thought.

---

# 10. Exploratory-memory lifecycle inside E1

Distinguish persistent-store status from runtime episode guidance.

When the exploratory memory is first activated:

```text
persistent status: active -> consumed
```

But during the current episode:

```text
retain the same exploratory memory as runtime probe guidance
until the local probe completes or aborts
```

After probe completion/abort, the actor may continue the original task using normal task context and established memory.

The consumed exploratory memory must not be returned to the future active exploratory pool.

Do not remove it after only the first action of a multi-step probe.

---

# 11. E0/E1 experiment

Use the same task/state/model configuration.

## E0

```text
established memory only
```

## E1

```text
same established memory
+ corrected exploratory probe specification
```

Run only on up to 3 of the best corrected-C cases first.

Do not scale beyond that before reviewing the traces.

At every step both conditions must receive the actual current observation and admissible actions.

Record:

```text
exploratory memory presented?
probe activated?
probe entry action executed?
probe followed adaptively?
discriminative evidence obtained?
probe stopped locally?
original task completed afterward?
```

Do not interpret "alternative worse" as probe failure if the execution yields useful comparative evidence.

If E1 ignores a valid exploratory memory, one explicit E2 diagnostic is allowed later, but only after the E1 trace has been reviewed.

---

# 12. Keep the experiment small

Do NOT in this cycle:

- optimize or redesign B;
- change carrier/benchmark;
- add WebShop/MLE/AIDE;
- add Stage 1;
- add A reconciliation;
- build graph memory;
- add generic exploration baseline;
- add VOI/exploration scores;
- add a global search controller;
- add rule-based trajectory segmentation;
- build a state-transition planner;
- expand to many seeds/tasks;
- build an automatic semantic probe grader.

The intended cycle is only:

```text
freeze B
-> correct C representation
-> inspect 5 C outputs
-> run stepwise E0/E1 on <=3 good cases
-> report failure location
```

---

# 13. Expected failure localization

Classify problems before patching them.

Possible categories:

```text
C target binding
C entry grounding
C semantic probe quality
online exploratory-memory authority
stepwise actor legality/control
task continuation after probe
```

Do not attribute an online actor failure to B/C unless the trace supports that conclusion.

Do not rescue a weak result with ad-hoc semantic rules.

---

# 14. Required report

Add a new result report under `docs/` containing:

1. exact C input change;
2. old exact-sequence vs new probe-policy representation;
3. five-case C result table;
4. P001 regression analysis;
5. selected <=3 E0/E1 cases and why they were selected;
6. full stepwise mechanism summary per case;
7. whether exploratory memory had behavioral authority;
8. whether probe produced comparative evidence;
9. whether the actor continued/completed the original task;
10. concise failure localization and next recommendation.

Do not claim full closed-loop persistent-memory success.

---

# 15. Tests

Add focused tests for at least:

- C input excludes evaluator-only information;
- C receives task/state/context needed for target binding;
- CREATE requires a grounded start action;
- grounded start action is legal at entry;
- C no longer requires a complete future action list;
- stepwise actor emits one action per model call;
- chosen action is validated against current admissible actions;
- E0/E1 differ only by exploratory-memory intervention where intended;
- exploratory memory can be consumed persistently while retained as current runtime probe guidance;
- artifacts are saved on failure.

Keep tests narrow. Do not refactor unrelated repository infrastructure.

---

# 16. Git discipline

Before modifying:

```bash
git status
git branch --show-current
```

Before committing:

```bash
git status
git diff
git diff --check
```

Run focused MVP tests, Ruff, and compile checks.

Do not commit credentials or runtime benchmark data.

Commit and push to the existing branch:

```bash
git add <relevant files>
git commit -m "exp: use probe policy and stepwise online actor"
git push origin exp/minimal-exploratory-memory-validation
```

Do not force-push.

At completion report:

- final commit SHA;
- changed files;
- tests/commands run;
- five-case C results;
- selected E0/E1 cases;
- per-case online mechanism outcome;
- best evidence-based failure localization.
