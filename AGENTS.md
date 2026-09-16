# AGENTS.md

This file defines the implementation contract for coding agents on branch:

```text
exp/minimal-exploratory-memory-validation
```

This branch intentionally supersedes the older H1-H4 / AppWorld execution priority that exists in previous repository history.

## 1. Current scientific objective

The current objective is **minimal mechanism validation for the new exploratory-memory design**.

Do not optimize a benchmark leaderboard and do not build the full persistent-memory system yet.

The first question is:

> Can persistent history identify a meaningful unresolved comparison, turn it into one grounded local exploratory memory, and cause a future matched agent to perform a one-shot probe that produces comparative evidence?

The MVP chain is:

```text
curated established memory + current context
  -> B: OPEN or NONE
  -> C: one grounded local exploratory memory
  -> future matched task/state
  -> exploratory memory changes local behavior
  -> probe produces comparative evidence
```

Stage 1 and A are deliberately excluded from the first milestone.

## 2. Required read order

Before coding, read:

1. `docs/37_minimal_exploratory_memory_validation_plan.md`
2. `docs/38_coding_agent_handoff_exploratory_memory_mvp.md`
3. `docs/36_appworld_final_sanity_probe_results.md` for the previous carrier failure lesson
4. this file

Older research documents remain useful historical context but do not override the current branch plan.

## 3. Most important implementation rule: semantics are not a handcrafted-rule problem

Do **not** build complicated heuristic/rule systems for questions that are fundamentally semantic.

In particular, do not create large rule pipelines for:

- deciding whether a comparison is meaningful/open;
- strategy-family classification;
- context-family classification;
- semantic trajectory segmentation;
- deciding whether two realizations are equivalent;
- deciding whether a case is scientifically useful;
- exploration-value scoring;
- enumerating tool combinations as the main alternative search mechanism.

For the first 10-20 cases, directly inspect the real task, trajectory/state, memory, tool schema, and environment behavior. Write a short evidence memo.

Use LLM/research-agent reasoning for semantic interpretation.

Use deterministic code for mechanical and auditable facts.

### Deterministic code is appropriate for

- trace collection and formatting;
- action/tool/API identity;
- capability existence checks;
- environment replay/reset;
- success/reward/cost/step capture;
- provenance and IDs;
- artifact storage;
- token/cost telemetry;
- structured-output validation;
- evaluator-information isolation checks.

Rule of thumb:

> If a competent researcher can answer the question by reading the sample, prefer direct semantic analysis over a brittle hand-built classifier.

## 4. Carrier policy

Treat benchmarks as **case carriers** for this MVP.

Do not require the full benchmark distribution to naturally express the research problem.

Inspect at most 2-3 plausible real environments and select one that can provide several clean controlled cases with:

- established strategy A;
- A feasible/successful;
- a meaningful local comparison not yet resolved;
- an executable local alternative;
- an environment signal that can provide comparative evidence;
- matched/replayable future context for established-only vs established+exploratory comparison.

Do not build a large automatic case-mining system merely to select a carrier.

If no candidate carrier cleanly supplies the needed cases, stop and report that result.

## 5. Controlled-case policy

The first case set should contain roughly 10-20 cases total:

- `P`: meaningful unresolved comparison -> expected B=`OPEN`;
- `N1`: comparison already resolved -> expected B=`NONE`;
- `N2`: technically open but not policy-relevant -> expected B=`NONE`.

Case labels and evaluator notes are evaluation-only information.

Never expose them to B, C, or the online actor.

Case curation is research analysis, not a heuristic-labeling task.

## 6. B contract

Input:

```text
current task/state/trajectory
+ curated established memories
```

Output:

```json
{"decision": "NONE"}
```

or:

```json
{
  "decision": "OPEN",
  "replaceable_segment": "...",
  "functional_contract": {
    "available_state": "...",
    "local_function": "...",
    "required_downstream_state": "...",
    "constraints": ["..."]
  },
  "warrant": "..."
}
```

Do not add a separate heuristic gate before B.

B itself may return `NONE`.

## 7. C contract

Run C only when B returns `OPEN`.

Input:

```text
B result
+ relevant established memory
+ exact real capability/tool/action descriptions
```

Output:

```json
{"decision": "NONE"}
```

or exactly one exploratory memory:

```json
{
  "decision": "CREATE",
  "type": "exploratory",
  "scope": "...",
  "hypothesis": "...",
  "guidance": "...",
  "grounded_realization": ["..."],
  "reason": "..."
}
```

C may semantically compose multiple retrieved real primitives when needed.

Do not replace C with a combinatorial rule-based tool search.

## 8. Experiment A

Run B/C over the curated controlled cases.

The first report should be case-level and evidence-first.

Record:

- B OPEN/NONE;
- whether B targeted the relevant local comparison;
- whether C is grounded in real capabilities;
- whether C is local rather than a whole-task replan;
- whether C is executable;
- whether executing the proposal can produce comparative evidence.

For 10-20 cases, semantic review may be performed directly from raw artifacts. Do not build a semantic grader merely to avoid reading the cases.

## 9. Experiment B

Only after Experiment A shows promising cases, run paired online conditions:

### E0

```text
established memory only
```

### E1

```text
same established memory
+ exploratory memory
```

Hold task/state/model/config fixed as much as possible.

Observe:

```text
exploratory memory visible?
-> actor locally follows it?
-> alternative executes?
-> comparative evidence obtained?
```

Optional E2 explicit-oracle instruction is allowed only as a diagnostic when E1 is ignored.

Do not add generic-exploration baselines in this first milestone.

## 10. What counts as a useful probe

A probe is useful when it changes the epistemic status of the comparison.

The alternative does not need to outperform the incumbent.

Useful evidence includes:

- alternative better;
- alternative worse under the same scope;
- same quality but different cost;
- alternative violates a required constraint;
- other discriminative evidence that would matter to future policy.

Do not equate "alternative lost" with "exploration failed".

## 11. Model policy

Unless technically blocked, use:

```yaml
provider: deepseek
model: deepseek-v4-flash
thinking: false
temperature: 0
```

Use the same model configuration across paired conditions.

This is mechanism screening, not a model-comparison study.

Do not depend on hidden chain-of-thought.

Persist only visible model responses, actions/tool calls, observations, memory artifacts, environment outputs, and telemetry.

## 12. Ground-truth/evaluator isolation

Hard requirement:

> evaluator-only information must never enter B, C, or actor inputs.

Examples of evaluator-only information:

- case type P/N1/N2;
- oracle alternative;
- hidden explanation for why the comparison is open/closed;
- hidden benchmark answer or evaluator diagnostics not normally visible to the actor.

Add explicit tests/assertions for this where feasible.

## 13. Minimal implementation preference

Prefer a small experiment-specific package such as:

```text
experiments/exploratory_memory_mvp/
  cases/
  prompts/
  run_b.py
  run_c.py
  run_online_pair.py
  review_cases.py
```

Reuse existing provider/telemetry helpers only when they reduce complexity.

Do not build a universal memory framework for this experiment.

## 14. Out of scope for the first milestone

Do not implement unless later explicitly requested:

- Stage 1 candidate-memory extraction;
- A reconciliation/update loop;
- graph memory;
- global strategy taxonomy;
- context classifier;
- global trajectory segmentation;
- exploration score/VOI gate;
- generic exploration baseline;
- current-only targeted baseline;
- complex hypothesis lifecycle;
- full online streams;
- large benchmark runs;
- MLE/AIDE integration before the simpler mechanism test passes.

## 15. Failure discipline

A negative mechanism result is useful.

If results are weak, localize failure to:

- carrier/case quality;
- B diagnosis;
- C synthesis;
- grounding/execution;
- online memory authority.

Do not rescue weak evidence with layers of ad-hoc rules or extra modules.

Stop and report when the current design does not work cleanly.

## 16. Required artifacts

For every scientific run preserve:

- case definition;
- exact B prompt/context;
- B raw and parsed output;
- exact C prompt/context;
- C raw and parsed output;
- real capability/tool references;
- online condition;
- actor-visible memory;
- actor actions/tool calls;
- observations/environment outputs;
- final task result;
- token/cost telemetry;
- evaluator-side review notes kept separate from actor inputs.

Do not store only aggregate labels.

## 17. Secrets

Never commit API keys, cookies, credentials, tokens, private URLs, or hidden benchmark state.

Use `.env` locally and keep secret/runtime artifacts gitignored.

## 18. Commit/push discipline

When asked to implement and submit work, commit and push to the current branch unless explicitly told otherwise.

Do not rewrite remote history merely to satisfy this preference.

Report failures accurately.

## 19. First milestone completion criteria

The first coding-agent package is complete when it contains:

1. a lightweight carrier-fit memo for at most 2-3 environments;
2. one selected carrier or an explicit no-fit report;
3. roughly 10-20 curated P/N1/N2 controlled cases if a carrier is selected;
4. minimal B/C runners with raw artifact logging;
5. Experiment-A case-level results;
6. if promising, a small E0/E1 paired online test;
7. a short failure analysis organized by stage.

The milestone does **not** need to prove the full persistent-memory method.
