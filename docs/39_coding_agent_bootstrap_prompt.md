# Coding-Agent Bootstrap Prompt: Exploratory-Memory MVP

Use this prompt when the coding agent starts **without a local checkout** of the repository.

```text
You are starting without a local copy of the repository.

Repository:
  https://github.com/wudixzy/memory.git

Target branch:
  exp/minimal-exploratory-memory-validation

Do NOT work directly on `main`.

## 0. Bootstrap the repository first

Choose a clean working directory, then clone and switch to the target branch.

Preferred commands:

  git clone https://github.com/wudixzy/memory.git
  cd memory
  git fetch origin
  git switch exp/minimal-exploratory-memory-validation

If `git switch` cannot find the branch locally, use:

  git switch -c exp/minimal-exploratory-memory-validation --track origin/exp/minimal-exploratory-memory-validation

Verify before doing any research or implementation:

  git status
  git branch --show-current
  git log -5 --oneline

The active branch must be:

  exp/minimal-exploratory-memory-validation

Do not create a new experimental branch unless there is a concrete technical reason. Continue on the existing target branch so the work is visible in the same experiment history.

If the repository cannot be cloned, the branch cannot be fetched, or push authentication is unavailable, stop and report the exact Git/GitHub error rather than silently creating an unrelated local project.

Before coding, read in this order:

1. AGENTS.md
2. docs/37_minimal_exploratory_memory_validation_plan.md
3. docs/38_coding_agent_handoff_exploratory_memory_mvp.md
4. docs/36_appworld_final_sanity_probe_results.md only for the previous benchmark-failure lesson

The branch-level AGENTS.md and docs/37-38 supersede older H1-H4/AppWorld priorities for this experiment.

## 1. Scientific objective

Your goal is NOT to build the full persistent-memory system.

Implement and run the smallest interpretable MVP that tests this chain:

curated established memory + current context
-> B diagnoses whether a meaningful comparison remains open
-> C proposes one grounded local exploratory memory
-> a future matched task/state receives that exploratory memory
-> the actor either does or does not perform the intended one-shot probe
-> the probe either does or does not produce comparative evidence.

Stage 1, A reconciliation, the full persistent-memory closed loop, and large-scale benchmark evaluation are out of scope for this milestone.

## 2. Core implementation principle

DO NOT replace semantic research judgments with complicated handcrafted rules.

In particular, do not build heuristic taxonomies/classifiers for:
- strategy families;
- meaningful/open comparisons;
- context families;
- trajectory segmentation;
- exploration value;
- semantic case quality;
- tool-combination search.

For the first 10-20 cases, directly inspect real tasks, trajectories, established memories, tool/action schemas, and environment behavior. Write short evidence memos explaining the semantic judgment.

Use LLM/research-agent analysis for questions such as:
- whether a comparison is genuinely unresolved;
- whether resolving it could change future policy;
- what local segment is replaceable;
- what functional contract that segment implements;
- whether an alternative is semantically meaningful and local;
- whether a candidate case actually instantiates the scientific scenario.

Use deterministic code/rules only for mechanical and auditable work such as:
- trace collection and formatting;
- action/tool existence checks;
- structured-output parsing/validation;
- environment reset/replay;
- success/reward/cost/step collection;
- provenance and IDs;
- token/cost telemetry;
- paired-run configuration checks;
- evaluator/hidden-information isolation checks.

Do not over-engineer sample mining. If a human/research agent can understand a candidate by reading the trace and environment evidence, analyze it directly rather than encoding a brittle semantic rule.

## 3. Work order

Proceed in this order.

### Phase 0 — inspect existing repository support

Inspect the repository before adding code.

Reuse existing provider, DeepSeek, artifact, telemetry, and benchmark-adapter utilities only when they genuinely simplify the MVP. Avoid unrelated refactors and do not force this experiment into an old abstraction that obscures interpretation.

Default model policy unless technically blocked:

  provider: deepseek
  model: deepseek-v4-flash
  thinking: false
  temperature: 0

Do not depend on hidden chain-of-thought.

### Phase 1 — lightweight carrier-fit inspection

Inspect at most 2-3 plausible real carriers. Do not integrate all of them.

Good candidates to inspect first include lightweight interactive/search environments such as WebShop or ScienceWorld. MLE/AIDE is a later/harder option if lightweight carriers fail. AppWorld may be consulted for lessons learned, but do not restart a large AppWorld candidate-mining pipeline by default.

For each candidate carrier, directly inspect a small number of real samples and answer:

1. Can historical strategy A be represented as established memory?
2. Is A actually feasible/successful?
3. Is there a meaningful local comparison that remains unresolved?
4. Can an alternative be executed without replanning the whole task?
5. Does executing the alternative provide comparative evidence?
6. Can the same/matched future state be replayed for an established-only vs established+exploratory comparison?

Write a concise carrier-fit memo. Select one carrier only if it can supply several clean controlled cases.

If none fits cleanly, stop and report that result rather than building a large adapter anyway.

### Phase 2 — curate roughly 10-20 controlled cases

Use three case types only:

P — meaningful open comparison
  History supports A, but A vs an alternative is unresolved and potentially policy-changing.
  Expected B output: OPEN.

N1 — comparison already resolved
  History already contains discriminative evidence or the alternative is known invalid in scope.
  Expected B output: NONE.

N2 — technically open but not policy-relevant
  The comparison is not fully proven, but resolving it is unlikely to materially affect future policy.
  Expected B output: NONE.

Curate cases by direct semantic inspection. Do not build a heuristic auto-miner for this milestone.

Evaluator-only labels, oracle alternatives, hidden outcomes, and case-review notes must never enter B/C/actor prompts.

### Phase 3 — implement minimal B

Input:
  current task/state/trajectory
  + curated established memories

Output either NONE or one OPEN comparison containing:
- replaceable segment;
- functional contract;
- exploration warrant.

Do not put a handcrafted score/gate before B. B itself decides OPEN vs NONE.

Save raw prompt, raw response, parsed response, usage, and errors.

### Phase 4 — implement minimal C

Run C only when B returns OPEN.

Input:
  B output
  + relevant established memory
  + exact real carrier capability/tool/action descriptions

Output either NONE or exactly one exploratory-memory candidate containing:
- scope;
- hypothesis;
- guidance;
- grounded realization;
- reason/provenance references as needed.

C may semantically compose multiple real primitives when necessary. Do not enumerate a combinatorial tool/action search space with handcrafted rules.

Mechanical checks may verify that referenced primitives exist and arguments are structurally legal.

### Phase 5 — Experiment A: can B/C formulate the right experiment?

Run B/C over the curated cases.

For each case record at least:
- expected P/N1/N2 type;
- B OPEN/NONE;
- whether the target comparison is sensible;
- whether C is grounded;
- whether C is local/executable;
- whether executing the proposed probe can yield discriminative comparative evidence.

For 10-20 cases, direct semantic review is acceptable and preferred over building a complicated semantic grader.

Stop before online testing if B is effectively all-NONE, reopens nearly every negative, or C frequently hallucinates/non-locally replans/produces non-informative probes. Report the failure rather than rescuing it with ad-hoc rules.

### Phase 6 — Experiment B: does exploratory memory actually cause a one-shot probe?

Only if several positive cases survive Experiment A, run paired online tests:

E0 — established memory only
E1 — exactly the same setup + C-generated exploratory memory

Keep task/state/model/config matched except for the exploratory-memory intervention.

Record:
- was exploratory memory visible to the actor?
- did the actor locally follow it?
- was the alternative actually executed?
- did execution produce comparative evidence?

If E1 is ignored, optionally run:

E2 — explicit oracle instruction to perform the same local test once

Use E2 only to diagnose memory-authority failure vs an inherently unworkable case. Do not use it as scientific evidence for the method.

Do not add generic-exploration or current-only-targeted baselines in this first milestone.

## 4. Evaluation philosophy

The first milestone is evidence-first, not metric-heavy.

A useful exploratory probe is one that changes the epistemic status of the open comparison. The alternative does NOT need to outperform the incumbent.

All of the following can be useful outcomes:
- alternative B is better than A;
- B is worse than A under the relevant scope;
- B is equivalent in quality but cheaper;
- B violates a required constraint and can be ruled out.

The key question is whether the proposed test produces discriminative evidence, not whether exploration volume increases.

## 5. Explicit non-goals for this milestone

Do not add:
- Stage 1 candidate-experience extraction;
- A reconciliation/update;
- graph memory;
- context or strategy taxonomies;
- global trajectory segmentation;
- exploration-score/VOI gates;
- generic exploration controller;
- complex hypothesis lifecycle;
- large automatic case miner;
- large benchmark sweeps;
- MLE/AIDE integration before the simpler mechanism test is informative.

## 6. Expected deliverables

Commit a small, reviewable implementation plus evidence/results containing:

1. carrier-fit memo;
2. selected carrier, or an explicit no-fit result;
3. curated ~10-20 P/N1/N2 cases with short evidence notes;
4. minimal B/C runners;
5. Experiment-A raw prompts/responses and compact case table;
6. if Experiment A is promising, a small E0/E1 paired online experiment;
7. concise failure localization to one or more of:
   - carrier/case;
   - B diagnosis;
   - C synthesis;
   - grounding/execution;
   - online exploratory-memory authority.

Do not claim that the full method works from this MVP.

## 7. Git discipline and submission

Before editing:
  git status
  git branch --show-current

Before committing:
- inspect `git diff`;
- ensure no API keys, cookies, credentials, benchmark secrets, large runtime state, or unrelated files are included;
- keep the change focused on this MVP.

Then commit with a clear message and push to the same remote branch:

  git add <relevant files>
  git commit -m "exp: implement minimal exploratory-memory validation"
  git push origin exp/minimal-exploratory-memory-validation

If remote changes appeared after cloning, fetch and reconcile normally; do not force-push or overwrite remote history merely to complete the task.

At the end, report:
- final commit SHA;
- files changed;
- commands/tests/experiments run;
- result summary;
- important failures/uncertainties;
- anything that prevented push or reproducible execution.
```
