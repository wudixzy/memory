# 102. Phase 1C — Flash Scale-Aware Hypothesis Pilot

Date: 2026-09-21  
Branch: \`exp/minimal-exploratory-memory-validation\`  
Frozen Phase 1B implementation baseline: \`c8daa67ba9d9d6257d65e446b437d362e60abc61\`

## 1. Purpose

Phase 0/1A/1B established that the minimum exploratory-memory mechanism can be implemented and audited:

- B/C can create a future-facing exploratory H;
- H can change future behavior and is one-shot consumed;
- automatic retrieval can activate an H in a later task;
- actual probe evidence can enter A and materialize Established Memory;
- leakage/provenance/temporal/fact-commit boundaries are hardened;
- the complete minimum longitudinal loop has executed;
- Phase 1B is frozen as \`READY_FOR_SCALE_WITH_KNOWN_LIMITATIONS\`.

What is still unknown is the core scale hypothesis:

\[
\boxed{
\text{As history accumulates, does history-derived exploratory memory begin to
produce cumulative value beyond persistent generic exploration?}
}
\]

This is still a hypothesis pilot, not the final paper experiment. Optimize for a direct answer, not reviewer-proof protocol complexity.

## 2. Three hypotheses observed in this pilot

### H1 — History changes future exploration

As task history grows, Targeted should create/retrieve/execute probes that differ from persistent generic exploration.

### H2 — Exploration history reduces redundant exploration

Once an exploratory H has actually been activated, it enters the offline exploration-history archive. Future C calls can see a few relevant prior tested hypotheses and should sometimes avoid proposing an equivalent experiment or create a materially different one.

### H3 — The above mechanisms begin to improve cumulative behavior

The main behavioral question is whether Targeted's cumulative search cost begins to improve relative to Generic as history grows.

H3 is the main outcome. H1/H2 explain why it does or does not occur.

## 3. Scope: Flash first, Max later only if justified

The first pilot uses only:

\`\`\`text
qwen3.8-flash
thinking = false
temperature = 0
\`\`\`

Use Flash for every model-facing role in this pilot:

- generic/targeted candidate selector;
- H retrieval;
- B;
- exploration-history retrieval;
- C;
- A;
- comparison/H reconciliation.

Use strict structured output where the existing implementation supports it.

Do not run qwen3.8-max in this cycle.

After the complete Flash pilot and semantic review, the researcher may authorize a Max replication with the frozen same protocol if the Flash run shows either a mechanism signal or a behavioral scale signal.

Do not build mixed Flash/Max configurations in this pilot.

## 4. Experiment size

Use one fresh continuous stream:

\[
\boxed{32\ \text{tasks}}
\]

Target composition:

\`\`\`text
8 pick_and_place_simple
8 pick_clean_then_place_in_recep
8 pick_cool_then_place_in_recep
8 pick_heat_then_place_in_recep
\`\`\`

Interleave families deterministically:

\`\`\`text
simple -> clean -> cool -> heat -> repeat
\`\`\`

This is one dependent longitudinal stream, not \(n=32\) independent trials.

The pilot has exactly two arms:

\[
32 \times 2 = 64\ \text{episodes}
\]

No repetitions and no third arm.

## 5. Fresh-stream registration

Before any model/API call, construct and commit a dedicated Phase 1C registry.

Eligibility must use only public pre-outcome information.

Minimum intended conditions:

- task belongs to one of the four admitted families;
- task ID has not been used in previous Source/Calibration/Target/Phase1B development runs;
- exclude the untouched B1-R reserve rather than consuming it incidentally;
- reset/initial public state is available;
- requested target is not already exposed by an exact public take action at entry;
- enough public candidate receptacles exist to make the search subproblem meaningful.

Do not inspect hidden placement, PDDL answer, task outcome, oracle route, or expected arm winner.

Select exactly 8 per family with a deterministic, predeclared public-only rule and salt; then interleave them as above.

Persist:

- eligible fresh universe;
- exclusion manifest/reasons;
- frozen 32-task registry;
- exact order;
- replay specs / initial public fingerprints where available;
- registry digest.

If fewer than 8 eligible untouched tasks exist for any family, STOP before model calls and report the public-only shortage. Do not relax criteria after inspecting outcomes.

## 6. Initialization

Both arms start independently from the same warm start:

\[
K_0^{established}=K^*
\]

Generic:

\`\`\`text
K_established = K*
\`\`\`

Targeted:

\`\`\`text
K_established = K*
active_H = empty
exploration_history = empty
comparison_ledger = empty
\`\`\`

The two arms never share evolved memory.

This pilot deliberately remains warm-start. It does not test native Stage1/cold-start formation.

## 7. Arm G — Generic Evolving Exploration

G deliberately reuses the already tested Phase 1A C2 generic-exploration primitive.

For every task:

\`\`\`text
current public task/state
+ current G Established Memory
-> C2 generic structured probe
-> at most 2 candidate probes
-> deterministic canonical continuation if needed
-> actual evidence
-> A
-> K_established_G(t+1)
\`\`\`

Important:

- G performs the generic C2 exploration opportunity on every eligible task;
- stop the probe early if the exact target is acquired;
- C2 receives no H, B/C history, comparison history or exploration archive;
- A can evolve G's Established Memory from its own actual evidence;
- G does not run B/C/H/archive.

The pilot intentionally does not add a PROBE/NONE gate.

## 8. Arm T — Targeted Exploratory Memory

T uses the frozen Phase 1B mechanism plus the exploration-history lifecycle.

Persistent state:

\[
K_t^{established}
+
K_{t,active}^{exploratory}
+
\mathcal E_t^{history}
+
\text{comparison ledger}
\]

### 8.1 Task start

Retrieve at most one active H using the current public task/state.

If an H is activated:

\`\`\`text
targeted H probe
-> at most 2 candidate probes
-> H consumed
-> archive tested H
-> canonical continuation if target not acquired
\`\`\`

If no H is activated:

\`\`\`text
canonical continuation directly
\`\`\`

Do not fallback to Generic C2 in T when no H is active/relevant.

### 8.2 Fact commit and archive

Once an H is actually activated, mechanically append one compact \`ExplorationHistoryRecord\`.

Minimum record:

\`\`\`text
exploration_id
source_h_id
source_comparison_id
scope
hypothesis
realization_pattern
source_task_id / creation provenance
activation_task_id
evidence_id
related_post_test_memory_ids
\`\`\`

The archive records that the experiment was attempted. It must not mechanically label true/false, confirmed/falsified, or confidence.

Actual task/probe evidence is fact-committed exactly as in frozen Phase 1B.

### 8.3 A

Actual evidence goes through the frozen Phase 1B A semantics.

A continues to own:

- evidence interpretation;
- comparison epistemic assessment for consumed-H evidence;
- Established Memory ADD/REFINE/SPECIALIZE/MERGE.

After accepted A materialization, mechanically link relevant new/updated Established Memory IDs back to the archived exploration record as \`related_post_test_memory_ids\`.

### 8.4 B/C after the episode

B keeps the frozen responsibility boundary:

\`\`\`text
completed current trajectory + K_pre -> OPEN / NONE + Functional Contract
\`\`\`

B does not receive exploration history in this pilot.

If B=OPEN:

1. retrieve up to 3 relevant exploration-history summaries;
2. pass the abstract Functional Contract, current Established Memory, capabilities and those compact history summaries to C;
3. C returns CREATE or NONE.

C should use prior history only semantically:

- return NONE when the proposed experiment would merely repeat an equivalent tested hypothesis in a comparable scope;
- CREATE when the proposal is materially different in scope, realization, capability context, or because new Established Memory changes the unresolved comparison;
- a justified retest is allowed.

Do not implement a hard similarity threshold or rule-based hypothesis dedup.

## 9. Exploration-history retrieval

Keep this intentionally lightweight.

Only call it when:

\`\`\`text
B = OPEN
and archive is non-empty
\`\`\`

Input:

- current abstract Functional Contract;
- compact archive summaries only.

Output:

- at most 3 existing \`exploration_id\` values;
- or NONE.

Use qwen3.8-flash with a strict ID-only schema.

Do not pass raw archived trajectories or the whole evidence store.

C receives the selected compact history records.

Do not build embeddings, Graph retrieval, vector stores, or a new online controller for this pilot.

## 10. Controlled execution boundary

Keep the existing controlled search abstraction.

Both arms share:

- same task/replay spec;
- same public initial state;
- same Flash backbone;
- same candidate selector interface;
- same maximum probe budget = 2;
- same deterministic candidate executor;
- same canonical continuation;
- same target-acquisition endpoint;
- same A contracts;
- same failure/fact-commit semantics.

Canonical continuation remains deterministic. This pilot intentionally tests the scale value of exploration scheduling/content/history rather than restoring a full autonomous actor.

## 11. Primary outcome

Use one primary behavioral quantity:

\[
C_a(N)=\sum_{t=1}^{N}\text{environment actions to exact target acquisition}_{a,t}
\]

for:

\[
a \in \{G,T\}
\]

Report cumulative curves at:

\[
N=8,16,24,32
\]

and:

\[
\Delta C(N)=C_T(N)-C_G(N)
\]

Do not require monotonic improvement or T superiority from the first task.

Also retain per-task paired action deltas and candidate inspections descriptively.

## 12. Minimal mechanism observations

Do not create a large metric suite.

### M1 — Does comparative memory actually grow/evolve?

Record enough raw state to inspect:

- B OPEN/NONE;
- C CREATE/NONE;
- comparison NEW/REFINE/MERGE/DUPLICATE;
- active/created/consumed H.

At the end, semantically inspect whether the system produced useful diversity/reuse or mostly near-duplicates.

### M2 — Does history actually change future exploration?

Record:

- H retrieval ACTIVATE/NONE;
- targeted probe sequence;
- G C2 probe sequence;
- A SUPPORTING/CONTRADICTING/INCONCLUSIVE.

### M3 — Does the archive reduce redundant exploration?

Record:

- archive size;
- history retrieval calls/top-k;
- C CREATE/NONE with relevant history;
- C reason/audit text.

After the run, manually/agent-review the small set of cases where relevant history was returned and C either suppressed or retested a proposal.

Classify descriptively:

- reasonable duplicate suppression;
- materially different new exploration;
- justified retest;
- apparent redundant retest;
- possible over-suppression.

Do not use these post-hoc labels to alter the run.

## 13. Cost/model telemetry

Record model calls, input/output/cached tokens and available cost estimates by arm, role, task and checkpoint.

This is secondary. Do not optimize the pilot based on token cost after seeing outcomes.

## 14. Implementation discipline

Create a new versioned path such as:

\`\`\`text
phase1c-scale-pilot-v1
\`\`\`

Do not change the frozen Phase 1B scientific behavior in place.

Reuse existing Phase 1A C2, Phase 1B A/B/C/H/retrieval/reconciliation and controlled execution code where practical.

Before model calls:

1. implement archive/history retrieval and two-arm runner;
2. create/freeze fresh public-only 32-task registry;
3. add focused no-model tests;
4. verify G/T same task replay/public fingerprint;
5. verify no archive/history enters G;
6. verify archive is written only after actual H activation;
7. verify history retrieval returns only existing archive IDs;
8. verify C sees only compact selected archive summaries;
9. verify no hidden/evaluator data;
10. run focused/regression tests, Ruff, compileall and git diff --check;
11. commit and push the immutable Phase 1C transition.

Only then run paid calls.

## 15. Run discipline

Run the complete 32-task G and T streams with the frozen registry.

Do not tune after early tasks, replace tasks, change prompts/models halfway, stop because one arm looks bad, inspect hidden placement, add Max during the Flash run, or rerun failed semantic calls for a nicer result.

Use existing fail-closed behavior and preserve every failure artifact.

An infrastructure failure that prevents the environment/API from running may stop the run, but a scientific/semantic failure is evidence and should remain in the stream.

## 16. Interpretation after the Flash pilot

This pilot is exploratory hypothesis evidence.

Worth continuing toward Max/larger-scale testing if either:

1. **behavioral scale signal:** Targeted cumulative cost begins to improve relative to Generic as N grows; or
2. **mechanism signal:** H/comparison/archive/A dynamics clearly evolve with history and T behavior increasingly differs from G, even if 32-task cumulative cost has not yet separated.

If after 32 tasks H remains mostly repetitive, archive rarely changes C, retrieval rarely activates useful H, A rarely accumulates meaningful comparative evidence, and G/T behavior does not structurally diverge, review the scale hypothesis before spending on Max or longer streams.

Do not automatically run Max. Stop after Flash results and semantic review for researcher decision.

## 17. Explicitly deferred

This pilot does not include:

- qwen3.8-max;
- Established-only third arm;
- archive ablation;
- native cold start / production Stage1;
- multiple independent streams;
- repeated seeds;
- second benchmark;
- mixed-model configurations;
- retrieval algorithm comparison;
- paper-level significance testing.

## 18. Outputs

Before calls:

- \`docs/103_phase1c_flash_scale_pilot_transition.md\`
- committed fresh registry/exclusion manifest.

After run:

- \`docs/104_phase1c_flash_scale_pilot_results.md\`
- \`docs/105_phase1c_flash_scale_pilot_semantic_review.md\`

The final review must state separately:

- performance signal;
- H1 mechanism evidence;
- H2 archive/redundancy evidence;
- H3 cumulative-behavior evidence;
- known failures/limitations;
- whether a Max replication is worth running.

No paper-level superiority claim is permitted from this single-stream pilot.
