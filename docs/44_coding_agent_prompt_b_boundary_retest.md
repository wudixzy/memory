# Coding-Agent Prompt: B/C Boundary-Correct Retest

Use this prompt with a coding agent that starts without a local repository checkout.

---

You are starting without a local copy of the repository.

Repository:

```text
https://github.com/wudixzy/memory.git
```

Target branch:

```text
exp/minimal-exploratory-memory-validation
```

Do not work directly on `main`.

## 0. Bootstrap

Clone and switch to the existing experiment branch:

```bash
git clone https://github.com/wudixzy/memory.git
cd memory
git fetch origin
git switch exp/minimal-exploratory-memory-validation
```

If necessary:

```bash
git switch -c exp/minimal-exploratory-memory-validation \
  --track origin/exp/minimal-exploratory-memory-validation
```

Verify before editing:

```bash
git status
git branch --show-current
git log -5 --oneline
```

The active branch must be:

```text
exp/minimal-exploratory-memory-validation
```

If clone/fetch/push authentication fails, report the exact failure. Do not create an unrelated replacement project.

## 1. Read order

Read these files before changing code:

1. `AGENTS.md`
2. `docs/43_b_c_boundary_correction_and_retest_plan.md`
3. `docs/42_exploratory_memory_mvp_qwen38_comparison.md`
4. `docs/40_exploratory_memory_mvp_carrier_fit.md`
5. relevant MVP code under `experiments/exploratory_memory_mvp/`

Docs 43 and the current branch-level `AGENTS.md` define the next task. Do not restart older AppWorld/H1-H4 work.

## 2. Scientific task

The previous Experiment-A implementation accidentally made B responsible for part of C's job.

Correct decomposition:

```text
B: Which incumbent comparison is worth opening?
C: What grounded alternative can be tested once to answer it?
```

B diagnoses a question.

C instantiates an experiment.

A B=`OPEN` decision must **not** require B to already know, name, or verify a concrete alternative.

C may later return `NONE` if no grounded alternative can be formed.

Your task is to make the smallest implementation change needed to test this corrected boundary on the existing 11 ALFWorld cases.

Do not change carrier, benchmark, or case count unless a concrete data-integrity problem forces it.

## 3. Keep these experimental factors fixed

Use the existing:

```text
carrier: ALFWorld TextWorld
cases: 11 curated cases (5 P, 3 N1, 3 N2)
model: qwen3.8-flash
thinking: disabled
temperature: 0
```

Do not switch models in this cycle. The purpose is to isolate the interface correction.

Do not add multi-seed sweeps before the corrected single-run gate is understood.

## 4. Correct B input representation

The previous public representation blurred current execution with historical memory.

B must now receive four logically distinct parts:

```text
current task
current initial/public state
current completed trajectory
pre-update established memory
```

The current completed trajectory is the incumbent A execution that B is diagnosing.

The pre-update established memory is what history already established before this trajectory.

Do not nest the current trajectory under the established-memory object as `historical_experience`.

Preferred public shape:

```json
{
  "current_task": {...},
  "current_initial_state": {...},
  "current_trajectory": {...},
  "pre_update_established_memories": [...]
}
```

The current trajectory should expose enough visible execution information to recognize local cost/repetition and final outcome.

For P cases, pre-update memory supports feasibility/reuse of A but must not contain the hidden alternative or its outcome.

For N1 cases, pre-update memory may contain the already-recorded comparative evidence.

For N2 cases, keep the existing low-policy-value setup.

Keep evaluator labels, oracle actions, hidden alternatives, and evaluator rationale out of all model-visible inputs.

## 5. Correct B semantics

Rewrite B prompt semantics around the intended role.

B should ask only:

1. What local incumbent behavior in the current trajectory, if any, is a meaningful target for comparison?
2. Does history establish only that this realization works, or does it contain comparative evidence that closes the question?
3. If unresolved, could answering this comparison materially change future policy?

Explicitly tell B:

```text
Do not require evidence that a concrete alternative already exists.
Do not propose or ground an alternative.
C will do that later.
```

Also state explicitly:

```text
A successful incumbent proves feasibility, not comparative superiority.
An alternative missing from memory is not evidence that the comparison is resolved.
```

Remove wording equivalent to:

```text
whether supplied evidence supports a different realization
```

from the main B condition.

Do not give the main B condition `capabilities.json`.

## 6. B diagnostic output

The previous exact `{"decision":"NONE"}` output was too opaque for failure localization.

Use a compact explicit judgment schema for both decisions, for example:

```json
{
  "decision": "OPEN | NONE",
  "incumbent_segment": "short description or null",
  "evidence_status": {
    "feasibility_support": "short statement",
    "comparative_support": "short statement",
    "policy_relevance": "short statement"
  },
  "functional_contract": {
    "available_state": "...",
    "local_function": "...",
    "required_downstream_state": "...",
    "constraints": ["..."]
  },
  "warrant": "short final justification"
}
```

For `NONE`, `incumbent_segment` and `functional_contract` may be null if there is no meaningful target.

For `OPEN`, both must be populated.

These are explicit task judgments for auditability, not hidden chain-of-thought. Keep them concise.

Update validators/tests accordingly without adding semantic rules.

## 7. Do not move C into B

C keeps the real capability document.

C receives only after B=`OPEN`:

```text
B diagnosis
+ relevant established memory
+ exact real capability/action descriptions
```

C owns:

- concrete alternative synthesis;
- grounding;
- action/tool legality;
- local contract matching;
- executable one-shot exploratory memory.

Do not make B prove these things.

Do not change C unless an actual C failure is observed after B starts opening cases.

## 8. Implementation discipline

Likely files to touch:

```text
experiments/exploratory_memory_mvp/common.py
experiments/exploratory_memory_mvp/prompts.py
experiments/exploratory_memory_mvp/run_b.py
```

Fixture changes are allowed only if needed to represent current trajectory separately from pre-update memory.

Avoid unrelated refactors.

Do not implement handcrafted rules for:

- OPEN/NONE;
- segment detection;
- policy relevance;
- strategy families;
- alternative existence;
- exploration value.

Deterministic code is appropriate only for mechanical checks such as:

- schema validation;
- evaluator leakage;
- provenance separation;
- environment replay;
- success/steps;
- action/capability grounding for C;
- artifact logging;
- telemetry.

## 9. Representation audit before model calls

Before any paid call, generate new B inputs for all 11 cases.

Manually inspect at least:

- one P;
- one N1;
- one N2.

Confirm all of the following:

```text
current trajectory is explicit and separate
pre-update memory is separate
oracle alternative absent
case label absent
evaluator rationale absent
capabilities.json absent from B prompt
```

Save a short audit memo or include these examples in the result report.

Do not proceed if the boundary is still ambiguous.

## 10. Main retest

Run exactly one deterministic corrected B call on each of the 11 cases with `qwen3.8-flash`, thinking off, temperature 0.

Produce a table with:

```text
case
case type (evaluator-side only)
B decision
incumbent segment summary
comparative-support summary
policy-relevance summary
```

For every P case that remains `NONE`, directly inspect the returned diagnostic fields and explain the immediate reason.

Do not automatically optimize the prompt again inside the same run.

## 11. C execution

If one or more cases return B=`OPEN`, run the existing C stage for those cases.

Record:

```text
C CREATE/NONE
grounded?
local?
executable?
probe capable of producing comparative evidence?
```

Do not run E0/E1 until at least one credible B->C exploratory probe exists.

## 12. If B is still all/almost-all NONE

Do not add capabilities to B and do not add OPEN heuristics.

Run at most one small diagnostic on the 5 P cases:

### Segment-hint diagnostic

Give B only an evaluator-reviewed incumbent-segment description, such as:

```text
candidate incumbent segment: the receptacle-search portion before the requested object is found
```

Do not provide:

- the hidden alternative;
- oracle action sequence;
- oracle outcome;
- full capability document.

This is a diagnostic condition, not the proposed method.

Interpretation:

```text
segment hint -> OPEN
    likely localization/representation bottleneck

segment hint -> still NONE
    comparative-status / policy-relevance judgment remains the bottleneck
```

After this diagnostic, stop and report. Do not keep patching.

## 13. What not to do

Do not:

- change benchmark;
- integrate WebShop/MLE/AIDE;
- give the main B condition capabilities;
- reveal the oracle alternative;
- add rule-based OPEN gates;
- add automatic segmentation heuristics;
- add strategy/context taxonomies;
- add VOI/exploration scores;
- modify C before C is actually tested;
- run broad replicate sweeps;
- implement Stage 1/A/full closed loop.

The purpose is to isolate one design correction.

## 14. Required result document

Add a new tracked report under `docs/` containing:

1. exact code/interface changes;
2. one old-vs-new B input example;
3. the corrected B prompt contract;
4. 11-case corrected result table;
5. direct review of P-case diagnostics;
6. C results if reached;
7. segment-hint diagnostic only if needed;
8. conclusion choosing among:
   - previous implementation/prompt mis-specified B;
   - segment-localization remains difficult;
   - genuine comparative-diagnosis difficulty remains;
   - evidence still ambiguous.

Do not claim the full memory method works.

## 15. Tests

Run focused tests for the MVP package and add/update only tests necessary to protect interpretation:

- current trajectory and pre-update memory are separate;
- evaluator fields never enter B/C;
- B prompt does not contain capability document;
- B output validator accepts the new diagnostic schema;
- C still receives capability information only after B=`OPEN`;
- artifacts are saved on failure.

Do not turn testing into a repository-wide refactor.

## 16. Commit and push

Before commit:

```bash
git status
git diff
```

Verify no credentials/runtime benchmark data are tracked.

Then commit and push to the same branch:

```bash
git add <relevant files>
git commit -m "exp: correct B C boundary and retest B"
git push origin exp/minimal-exploratory-memory-validation
```

Do not force-push.

At completion report:

- final commit SHA;
- files changed;
- tests/commands run;
- corrected 11-case B result;
- any C results;
- whether the segment-hint diagnostic was needed;
- your best failure localization from the evidence.
