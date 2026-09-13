# AGENTS.md

This file defines the implementation contract for coding agents working in this repository.

## 1. Current scientific objective

The current objective is **phenomenon validation**, not a new memory method and not benchmark optimization.

Implement infrastructure that can test H1–H4 from `docs/01_validation_protocol.md` on real upstream persistent-memory baselines.

Do not implement a novel memory algorithm unless a later task explicitly requests it.

## 2. Read order

Before coding, read:

1. `README.md`
2. `docs/00_research_brief.md`
3. `docs/01_validation_protocol.md`
4. `docs/02_compute_budget.md`
5. this file

## 3. Phase-1 model policy

All Phase-1 pre-experiments use the same backbone unless explicitly changed by a later instruction:

```yaml
provider: deepseek
model: deepseek-v4-flash
thinking: false
temperature: 0
```

Interpret this as a **common-backbone mechanism evaluation**, not exact reproduction of the original paper model.

Rules:

1. Use DeepSeek official API by default.
2. Use **non-thinking** mode for all actor, planner, builder, reflector, curator, inducer, or other LLM roles in the Phase-1 causal comparison.
3. Where a baseline uses multiple LLM roles, keep their backbone identical unless the upstream architecture fundamentally requires otherwise.
4. Do not use `deepseek-v4-pro`, the original paper model, or a local model during initial candidate mining unless explicitly requested.
5. If a model/provider compatibility patch is required, document it separately from any memory-mechanism patch.
6. Do not compare branches using different model IDs, thinking modes, or temperatures.

Later confirmation may use DeepSeek-V4-Pro and/or the original paper backbone on a small set of confirmed cases. Such runs must be labeled separately.

## 4. Priority order

Unless explicitly changed:

1. repository-wide artifact schema + telemetry;
2. AutoManual + ALFWorld Phase 0/1 with DeepSeek-V4-Flash;
3. ACE online/no-GT + AppWorld Phase 0/1 with DeepSeek-V4-Flash;
4. AWM + WebArena reproducibility gate with DeepSeek-V4-Flash;
5. natural candidate mining;
6. targeted H2/H3/H4 branch validation.

## 5. Upstream-code policy

### Use official memory implementations

Primary evidence must use official upstream implementations for the memory mechanism.

Do not silently rewrite a method from the paper. Do not call an adapter `AWM`, `ACE`, or `AutoManual` if its core memory mechanism has been materially replaced.

Changing only the backbone to the project-wide DeepSeek-V4-Flash setting is permitted in Phase 1 and should be labeled **mechanism-faithful / common-backbone**, not exact paper reproduction.

### Pin upstream state

For every external repository record:

- repository URL;
- commit SHA;
- environment/dependency lock;
- local patch/diff if any;
- original upstream model configuration;
- project Phase-1 model substitution.

Preferred layout:

```text
third_party/
  automanual/
  ace-appworld/
  agent-workflow-memory/
```

Do not vendor large upstream repositories directly into Git history unless explicitly requested. Prefer setup scripts/submodules or a reproducible clone-and-pin workflow.

### Patch discipline

A patch is acceptable when it is required for:

- compatibility with current Python/package APIs;
- logging/instrumentation;
- deterministic task reset;
- model/provider configuration;
- fixing an obvious runtime failure without changing the memory algorithm.

Every patch must be documented in the run manifest.

If a patch changes what memory is formed, retrieved, applied, or updated, mark the run **non-faithful** until reviewed.

## 6. Proposed repository structure

Use this structure unless the codebase demonstrates a simpler equivalent:

```text
memory/
├── README.md
├── AGENTS.md
├── docs/
├── configs/
│   ├── automanual_alfworld/
│   ├── ace_appworld/
│   └── awm_webarena/
├── scripts/
│   ├── setup/
│   ├── smoke/
│   └── run/
├── src/
│   └── memory_validation/
│       ├── schemas/
│       ├── telemetry/
│       ├── adapters/
│       ├── branching/
│       ├── candidate_mining/
│       └── analysis/
├── tests/
└── artifacts/          # gitignored except tiny fixtures/examples
```

Keep the shared instrumentation independent of any single upstream framework.

## 7. Required shared interfaces

Design minimal interfaces around experimental observability, not around a hypothetical universal memory framework.

Suggested conceptual interfaces:

```python
class PairAdapter:
    def setup_check(self) -> dict: ...
    def reset_task(self, task_id: str, seed: int | None = None) -> None: ...
    def snapshot_memory(self) -> object: ...
    def run_task(self, task_id: str, intervention=None) -> object: ...
    def collect_artifacts(self) -> object: ...
```

Interventions should minimally support:

```python
NoIntervention()
MaskMemoryItem(memory_id=...)
NoMemory()
```

Do not force memory systems with very different structures into a lossy common representation. Save raw memory plus a normalized metadata layer.

## 8. Artifact requirements

Every task run must preserve the files defined in `docs/01_validation_protocol.md`.

At minimum:

- manifest;
- memory before;
- memory actually injected/available;
- visible model messages;
- actions;
- observations;
- evaluator output;
- updater input/output;
- memory after;
- memory diff;
- token/cost telemetry.

If an upstream framework does not expose one of these, explicitly mark it `unavailable` rather than inventing data.

The manifest must include at least:

```json
{
  "provider": "deepseek",
  "model": "deepseek-v4-flash",
  "thinking": false,
  "temperature": 0,
  "evaluation_type": "common-backbone"
}
```

## 9. No hidden chain-of-thought dependency

Do not require or attempt to recover hidden model chain-of-thought.

Persist only:

- model messages actually returned by the API/framework;
- visible rationales if the baseline itself exposes them;
- tool calls;
- environment actions;
- observations;
- memory/update artifacts.

Causal claims should rest on behavior, evidence acquisition, and memory state, not private reasoning traces.

## 10. Ground-truth/evaluator isolation

This is a hard requirement.

For the main H1–H4 experiment:

> evaluator-only or hidden ground-truth information must never enter the actor/memory-updater loop.

Approved AutoManual-only exception (`automanual-native-won-v1-2026-09-11`):
the audited pinned `autobuild_case` path may retain its existing won-derived
boolean success feedback, at the original consumers, frequency, granularity and
stopping/skill/history/Builder boundaries. This does not permit numeric reward,
admissible commands, expert plans, walkthroughs, hidden state or additional
evaluator diagnostics in the adaptive loop. See docs/07 for the exact field table.
Generated Python remains confined to approved action/rule operations; evaluator
artifacts remain separate. This exception does not extend to other baselines or
establish mechanism equivalence. Record its version and execution restrictions
in the manifest. Single-task connection validation is not H1–H4 evidence.

Particularly for ACE + AppWorld, use the official no-GT online path and verify in code that hidden task ground truth is not passed into reflector/curator prompts.

If an upstream baseline normally uses hidden evaluator feedback, create a clearly labeled diagnostic run; do not mix it with the main endogenous-evidence experiment.

## 11. Branch experiment discipline

H2/H4 require counterfactual branches.

A branch experiment must hold fixed as much as possible:

- task ID;
- initial environment state;
- benchmark version;
- `deepseek-v4-flash` model;
- non-thinking mode;
- temperature / decoding parameters;
- system prompt;
- all memory except the targeted intervention.

Never compare two unrelated tasks and call that a causal memory intervention.

For a memory item intervention:

1. save immutable `K_t`;
2. create a derived copy with `m_i` masked/reduced;
3. never mutate the original checkpoint;
4. record the exact textual/structural diff;
5. run intact and intervention branches under the same harness.

## 12. Candidate mining should not define the answer

Candidate mining can use heuristics or an auxiliary classifier, but H2–H4 confirmation must come from branch experiments and raw evidence.

Useful candidate heuristics include:

- persistent rule/workflow strongly repeated across updates;
- memory item present while a relevant inspect/verify action disappears;
- repeated success with increasingly homogeneous trajectories;
- task failure after reuse of a broad rule;
- intact trajectory skips an evidence-bearing action seen in earlier/no-memory trajectories.

Do not automatically label these as harmful.

## 13. Repetition and randomness

Use non-thinking DeepSeek-V4-Flash at temperature 0 for candidate screening.

Remote APIs and web environments may still not be perfectly deterministic.

For confirmed stochastic H2/H4 cases:

- screening: 3 repetitions/branch;
- confirmation: default 5 repetitions/branch;
- record every run, including failures that contradict the hypothesis.

## 14. Cost telemetry is mandatory

Before scaling beyond five tasks, implement:

- calls/task;
- input/output/cached tokens;
- latency;
- retry count;
- cost estimate/provider cost;
- memory size growth.

Hard budget limits should terminate cleanly and save partial artifacts.

See `docs/02_compute_budget.md`.

## 15. API vs local GPU

Primary Phase-1 runs use the **DeepSeek-V4-Flash API** and require no local inference GPU.

Do not switch to a local model merely to reduce cost. Local-model experiments belong to a later robustness stage unless explicitly requested.

Local GPU may be used for auxiliary trace analysis, but the target H1–H4 claim should be recoverable from saved raw artifacts without depending on that auxiliary model.

## 16. Secrets

Never commit API keys, cookies, benchmark credentials, tokens, or private URLs.

Use `.env` locally and commit only `.env.example`.

Add secret-bearing files and runtime benchmark state to `.gitignore` before first execution.

## 17. Tests required before a real run

At minimum add unit/integration tests for:

1. manifest serialization;
2. memory snapshot hashing/diff;
3. usage aggregation;
4. targeted memory masking without mutating source checkpoint;
5. evaluator-ground-truth isolation assertion where possible;
6. task-reset reproducibility check;
7. a tiny fake adapter that exercises the full artifact pipeline without any paid API.

The fake adapter is only an infrastructure test and must never be used as scientific evidence.

## 18. Completion criteria for each pair

### Phase 0 complete

- upstream setup documented;
- upstream commit pinned;
- DeepSeek-V4-Flash compatibility confirmed;
- one official task executes;
- evaluator executes;
- memory before/after captured;
- no fatal undocumented dependency.

### Phase 1 complete

- five sequential online tasks execute with DeepSeek-V4-Flash non-thinking;
- usage/cost captured;
- memory evolves across tasks;
- raw actions/observations captured;
- task reset verified;
- targeted memory intervention technically possible.

Only then should candidate mining begin.

## 19. When to stop and report instead of patching indefinitely

Stop and write a reproducibility report if:

- required upstream artifacts are missing/private;
- core memory logic is absent from the release;
- environment no longer runs without major redesign;
- reproducing the loop would require reimplementing the baseline from the paper;
- evaluation cannot be separated from hidden-information leakage;
- adapting the baseline to DeepSeek-V4-Flash would require changing the core memory algorithm rather than only the model/provider interface.

A failed reproducibility gate is a useful project result. Do not hide it behind a large custom rewrite.

## 20. First coding-agent deliverable

The first implementation PR should contain only:

- `.gitignore` / `.env.example`;
- shared artifact schemas;
- DeepSeek-V4-Flash provider/config abstraction;
- token/cost telemetry abstraction;
- fake adapter/tests;
- upstream setup/pinning scripts for AutoManual + ALFWorld;
- a smoke-test command that does not yet launch a large paid run.

Do not start all three environments in one PR.

## 21. Commit and push preference

User instruction (2026-09-13): when asked to commit or submit repository work,
complete the commit and push it to the branch's configured upstream by default.
Do not stop at a local commit or request separate push confirmation, unless the
user explicitly asks for local-only work. This does not authorize automatic
commits for every task or force pushes. Report push failures and unresolved
remote changes accurately; never overwrite remote history to satisfy this rule.

## 22. Current B-focused priority — supersedes Sections 4 and 20 for the next cycle

The current research priority is defined by `docs/26_strategy_lockin_experiment_plan.md`.
Do **not** continue broad AutoManual sampling, single-rule masking, or add a new baseline by default.

The next scientific target is **success-induced strategy lock-in**: learned memory may be correct and useful but still concentrate behavior on a known-good strategy C, reducing discovery of another successful strategy with lower task-relevant interaction cost.

Immediate order:

1. reuse the existing ACE/AppWorld setup;
2. perform a research-side AppWorld task-family census;
3. produce a top-10 candidate table using the registered gates/rubric;
4. let a reviewer select at most three families;
5. only then run initial-playbook explorability probes;
6. source-memory formation and memory-authority gates follow only for surviving families;
7. formal Minimal-B branches come last.

A candidate must have multiple successful strategies, a meaningful cost difference, a source-appropriate strategy C, a target where C still succeeds, and a better strategy that the same backbone can discover without learned memory. Targets that explicitly force exhaustive comparison are weak B tests and should normally be rejected.

## 23. Codex CLI / Claude Code worker workflow

For the next cycle, the preferred local workflow is documented in `docs/27_codex_claude_code_workflow.md`.

Expected layout:

```text
Codex working directory: /home/coolboy/projects/memory
Git repository:          /home/coolboy/projects/memory/memory
```

Codex is the orchestrator/reviewer/final integrator. Claude Code is the implementation worker and must run from the inner Git repository. Use the repository wrapper:

```bash
bash /home/coolboy/projects/memory/memory/scripts/agents/run_cc_deepseek.sh ...
```

The wrapper owns the Claude Code DeepSeek configuration. Do not duplicate credential values into prompts or tracked configuration.

Workflow discipline:

1. Codex reads the newest scientific plan and gives Claude Code a focused implementation package.
2. Claude Code implements/analyzes/tests but does not commit or push by default.
3. Codex independently reviews the diff, evidence, and relevant tests.
4. Codex sends concrete revision feedback back to Claude Code when needed.
5. Codex owns final status/docs synchronization, commit, and push.

Do not let agent orchestration become a new infrastructure project. The first delegated package is the Stage-A AppWorld candidate census/report, not another generic framework or paid experiment.

## 24. Current reserve-review override — supersedes the reviewer-selection step in Section 22

The Stage-A census is complete (`docs/28_appworld_family_census.md`): 244 AppWorld families produced 26 reserve families and no automatic shortlist under the conservative offline gates.

Do **not** manually inspect the reserve families one by one and do not stop AppWorld merely because the offline census could not measure B success/cost/discoverability. Follow `docs/29_parallel_candidate_review_plan.md`.

Current order:

1. Claude Code regenerates the census if needed and returns **all reserve family/source/target IDs** plus paths to their evidence records.
2. Codex owns a lightweight review-packet builder, reviewer prompt/schema, and parallel DeepSeek Flash review harness.
3. Review all ~26 reserve families, normally with **2 independent DeepSeek reviews per family** and a third reviewer only for disagreements.
4. Reviewer outputs must be strict structured JSON and are candidate-triage evidence only. They may propose B but may not claim B success or measured cost.
5. Codex automatically validates IDs, API names, evidence references, scope equivalence, and privileged-information dependence before aggregation.
6. Promote at most 3-5 families to **scripted-B environment validation**. Claude Code may implement those diagnostics; Codex reviews/runs them.
7. Only a benchmark-executed B with `success=true` and meaningful measured public-call savings proceeds to K0 explorability.
8. K0 explorability, natural memory formation, memory authority, Minimal-B and closed-loop diagnosis remain later gates.

No human semantic review is required for this reserve-triage stage. Do not pre-filter to the current top-10 solely to save tokens; reviewing all 20-30 reserves is cheap enough and reduces ranking bias.

For the reviewer ensemble, the project Claude/Anthropic-compatible model name is `deepseek-flash[1m]`. Keep reviewer credentials local via `.env`/the existing secret-handling policy; do not print or commit them.

If no scripted-B diagnostic among the promoted top 3-5 yields a successful route with meaningful measured savings, stop AppWorld for B rather than adding more candidate detectors.