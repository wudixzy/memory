# Phase 2 — Core Method Integration Validation Plan

> Status: PLANNED / ENGINEERING PREPARATION AUTHORIZED
> Date: 2026-09-23
> Branch: exp/minimal-exploratory-memory-validation
> Parent evidence boundary: Phase 1F-MA-v2 + semantic review bundle (docs/124–127)
> Purpose: move from exploratory-memory MVP validation to validation of the integrated core method.
> Model/API boundary: this document authorizes implementation, deterministic replay preparation, tests, registries, and transition freezing. Do not start new model/API calls until the Phase 2A transition is committed and the researcher explicitly authorizes execution.

---

## 0. Why the project is changing phase

Phase 1B–1F tested the exploratory-memory mechanism, lifecycle, transfer, long-horizon accumulation, cross-model behavior, and no-H composition. The latest semantic review exposed a more fundamental issue:

- Flash and Max often understood the same local facts but assigned different epistemic states;
- one-sided successful realizations could be promoted into stronger reusable guidance even when the same A output admitted that no direct comparison existed;
- evidence direction, scope relevance, comparison state, and Established Memory mutation were being decided inside one overloaded A call;
- early schema/interface differences could change H availability and later memory topology.

Historical method review changes the attribution. The original method had already converged on:

~~~text
Full completed trajectory
  -> Stage 1: Open Mining
       Candidate Content + Support
  -> Stage 2 / A: Local Knowledge Reconciliation
       Candidate + Support + bounded Existing Memory
  -> Established Memory / Support / optional Graph mutation
~~~

The original method also explicitly stated that Candidate <-> Current Text Memory is the primary comparison object. Historical raw trajectories are evidence fallback, not the default comparison context.

The Phase 1 exploratory-memory MVP intentionally bypassed or compressed much of this Stage1 -> support-aware reconciliation path in order to isolate B/C/H. Therefore the current working hypothesis is:

[
oxed{
	ext{Part of the observed memory-evolution instability may come from the MVP collapsing Stage1 + Stage2 into an A-centric update path,}
}
]

rather than from a demonstrated need for a heavier comparison-state subsystem.

This hypothesis must now be tested in the context of the integrated method.

---

# 1. Phase 2 scientific scope

Phase 2 is not another isolated Stage1 patch test.

It validates the integrated epistemic/exploratory core:

[
oxed{
K_t
ightarrow
	ext{Online Acting}
ightarrow
	au_{t+1}
ightarrow
Stage1
ightarrow
A
ightarrow
B/C/H
ightarrow
	ext{future evidence}
ightarrow
Stage1/A
ightarrow
K_{t+n}
}
]

Primary questions:

1. Native memory formation: can Stage1 -> support-aware A form evidence-calibrated Established Memory from real trajectories?
2. Exploratory evidence absorption: can evidence produced by a consumed H return through the same native Stage1/A path without a special-purpose epistemic update engine?
3. Longitudinal semantic stability: does the integrated method remain coherent across episodes and across Flash/Max?
4. Targeted exploration value: with the same native Established-Memory formation and the same base online exploration policy, does B/C/H add value beyond an Established-only system?

Phase 2 is development/integration evidence, not the final publication-scale superiority experiment.

---

# 2. Historical design frozen for this phase

Do not redesign these unless Phase 2 produces a concrete failure.

## 2.1 Stage 1

Stage 1 performs single-trajectory open mining.

Input:

~~~text
Full completed trajectory
No Existing Memory
~~~

Conceptual output:

~~~text
Candidate
├── Content
└── Support
    ├── Direct Grounding
    ├── Minimal Global Context
    └── optional Builder Verification Grounding
~~~

Stage 1 must be trajectory-grounded, recall-biased but selective, and avoid unnecessary generalization.

Stage 1 does not perform historical reconciliation, exploration judgment, comparison-state updates, or Graph planning.

## 2.2 A / Stage 2

A is the conservative local knowledge reconciler.

Primary semantic comparison:

~~~text
Candidate <-> Current Text Memory
~~~

Bounded context may include semantic/exact retrieval, bounded Graph context when available, and a small Support view.

Core reasoning:

~~~text
Existing coverage
-> Candidate semantic delta
-> decision relevance
-> evidence sufficiency
-> minimal necessary mutation
~~~

A may semantically perform new / merge / dedup / refine / generalize / specialize / contradiction reconciliation / scope revision / provenance accumulation / concept alignment.

## 2.3 Support

Support is historical evidence for maintenance, not normal Agent-facing Memory.

~~~text
Historical Support Log
  = complete / auditable

Current LLM-facing Support View
  = small / deduplicated / diagnostic
~~~

Prefer diagnostic evidence:

~~~text
boundary / counter-support
>
provenance-diverse representative positive
>
large numbers of duplicate positives
~~~

Do not require Stage 2 to reread the complete historical trajectory archive.

## 2.4 B / C / H

Keep the existing responsibility boundary:

~~~text
B = diagnose one policy-relevant unresolved comparison
C = synthesize one grounded local future experiment
H = one-shot exploratory memory
~~~

Do not move concrete-alternative generation back into B. Do not make C read the full completed source trajectory. Do not convert H into an open-loop future action list.

## 2.5 Graph

Graph design is historically settled enough for the present phase.

Do not redesign or claim Graph contribution in Phase 2. Maintain compatibility with the existing semantics:

- Tool / Capability anchors;
- Semantic Concept organization;
- cross-memory / cross-trajectory grounding;
- stable relational semantics;
- retrieval / bounded local expansion;
- optional Text / Graph / Support mutations under Stage 2.

Graph is not the exploration search-space controller.

## 2.6 Native cold start

Method-native initialization remains:

[
G_0=G_{tool},quad
K_0^{established}=arnothing,quad
K_0^{exploratory}=arnothing,quad
mathcal E_0^{history}=arnothing,quad
mathcal T_0=arnothing.
]

---

# 3. What changes relative to Phase 1F

The central change is restoration of the native upstream memory-formation path.

Old exploratory MVP approximation:

~~~text
raw-ish episode evidence
+ H / probe trace
+ existing memory
-> A
-> memory mutation + comparison labels
~~~

Phase 2 core path:

~~~text
actual completed trajectory
-> Stage1
-> Candidate + Support
-> A with bounded Existing Memory
-> Established Memory / Support update
~~~

If the trajectory consumed H, the H relationship is provenance/context for Stage1/A; it does not create a separate truth-update engine.

---

# 4. Established Memory representation during Phase 2

Do not introduce a new mandatory three-field physical schema solely because of the semantic review.

The useful review lens is:

[
oxed{
Claim + Evidence Basis + Unresolved Boundary
}
]

This is currently a semantic audit lens. It maps to the historical architecture:

- Claim -> Current Text Memory semantics;
- Evidence Basis -> Support + bindings / compact Support view;
- Unresolved Boundary -> conditional scope, boundary/counter-support, unresolved/contested semantics.

The implementation should preserve these meanings without inventing a second epistemic store.

---

# 5. Comparison ledger policy

Do not redesign the comparison ledger before testing restored Stage1/A.

For Phase 2A–2C:

- preserve existing comparison records when needed for provenance and historical compatibility;
- treat them primarily as exploration bookkeeping / telemetry;
- do not use OPEN / PARTIALLY_RESOLVED / RESOLVED as the primary scientific outcome;
- do not tune A to reproduce historical Flash PARTIALLY_RESOLVED judgments;
- do not add comparative-strength scores such as NONE / INDIRECT / MATCHED / DIRECT.

The source of epistemic truth remains Established Memory + Support.

After Phase 2C, review whether the ledger carries indispensable information not already represented by Text Memory + Support + H/exploration provenance.

---

# 6. Phase 2A — Frozen semantic integration replay

## 6.1 Purpose

Validate restored Stage1 -> support-aware A before a new longitudinal environment stream. This is an integration gate, not the final Phase 2 result.

Phase 2A scope clarification: the selected Phase 1F records end at target
acquisition and are not full completed ALFWorld benchmark trajectories. The
Phase 2A replay therefore validates Stage1 -> Candidate+Support -> A on the
complete observed search/acquisition trajectory only. Full completed-task
native Stage1 remains a Phase 2B question.

## 6.2 Data

Use the existing frozen semantic-review bundle:

~~~text
docs/review_samples/phase1f_semantic_review/
~~~

Primary diagnostics:

1. cool Pan — successful H realization, Flash/Max threshold divergence;
2. cool Egg — same negative direction, different comparison state;
3. clean Cloth — negative H evidence, Max IRRELEVANT issue;
4. SoapBar — closed-first H loses locally to open-surface observation;
5. cool Lettuce — H scope mismatch negative control;
6. cool Tomato — H retrieval/scope-transfer mismatch;
7. Task1 -> Task2 topology chain — early interface difference amplification.

The complete 12-case bundle may be processed as secondary audit if cheap.

No hidden PDDL/oracle/evaluator information may be added to model-visible inputs.

## 6.3 Conditions

Historical condition: use saved Phase 1F A artifacts. Do not rerun or modify them.

Restored condition:

~~~text
same frozen actual trajectory
-> Stage1
-> Candidate + Support
-> A(Candidate, Support, bounded pre-task Established Memory)
~~~

Flash and Max must receive equivalent evidence representations for matched cases.

## 6.4 Stage1 requirements

Stage1 should preserve semantically:

- what potentially reusable thing happened;
- direct grounding proving it happened;
- minimal global context needed not to misread it;
- provenance;
- relationship to an activated H when one existed.

Stage1 must not decide comparative superiority, PARTIALLY_RESOLVED, future H, or global strategy ranking.

## 6.5 A requirements

A receives Candidate, Candidate Support, bounded relevant pre-task Established Memory, compact relevant Support view if available, and provenance/H-test context.

A may learn useful conditional knowledge from one-sided evidence. It must not promote a stronger default/preference claim beyond what the evidence basis supports.

## 6.6 Review dimensions

Freeze these review dimensions before model calls:

- evidence fidelity;
- scope fidelity;
- preference overreach;
- useful learning;
- contradiction handling;
- cross-model semantic agreement;
- context/token cost.

Primary diagnostic construct: Unjustified Preference Promotion. This is a review construct, not a new permanent Memory field.

## 6.7 Gate

Proceed only if:

- clear cases no longer systematically promote feasibility into unsupported preference;
- useful updates remain;
- Stage1 output is grounded and sufficiently stable;
- Flash/Max disagreement is reduced or explainable by genuine ambiguity rather than arbitrary status calibration;
- context/token growth is bounded;
- no provenance/leakage/correctness blocker exists.

If Stage1 is unstable, or A remains equally unstable after Candidate + Support, stop and diagnose Stage1/A.

---

# 7. Phase 2B — Native memory-formation and accumulation audit

## 7.1 Purpose

Test the original memory-construction path from empty experience memory without yet confounding it with a new endogenous policy stream.

## 7.2 Protocol

Start with empty Established Memory, empty Support store, and no experience-derived Semantic Concepts.

Sequentially process a preregistered stream of real completed trajectories:

~~~text
tau_1 -> Stage1/A -> K_1
tau_2 -> Stage1/A -> K_2
...
~~~

Use a frozen trajectory corpus selected before observing Phase 2 outputs. Prefer approximately 20–30 real trajectories.

For cross-model attribution, Flash and Max should process the same frozen evidence stream where possible. This isolates builder semantics from actor-generated trajectory differences.

This is an offline formation/accumulation audit, not yet an endogenous cold-start acting claim.

## 7.3 Audit targets

Inspect Candidate quality, CREATE vs support-only accumulation, merge/dedup, specialization/generalization, scope retention, support/counter-support binding, provenance independence, duplicate-positive handling, unresolved/contested preservation, semantic drift, and cross-model topology divergence.

Repeated positive trajectories should not automatically cause repeated stronger rewrites.

## 7.4 Gate

Stop before 2C for widespread over-generalization, rapid preference hardening from feasibility-only evidence, unstable Candidate extraction, uncontrolled duplication, severe cross-model regime divergence, or provenance/support corruption.

---

# 8. Phase 2C — One-step exploratory closed-loop integration

## 8.1 Purpose

Validate that exploratory evidence can be absorbed by the same native memory-evolution path.

[
K_t
ightarrow
B
ightarrow
C/H
ightarrow
	ext{real future H test}
ightarrow
	au_H
ightarrow
Stage1
ightarrow
A
ightarrow
K_{t+1}.
]

## 8.2 Cases

Use approximately 6–10 preregistered development source/target chains covering:

- successful H realization;
- locally contradicting H realization;
- non-diagnostic H test;
- scope-mismatch / wrong-retrieval control;
- repeated or near-duplicate exploration-history situation when available.

## 8.3 Main questions

Ask whether B/C/H created real evidence acquisition, Stage1 represented the H test correctly, A absorbed it conservatively, positive evidence stayed useful without unjustified preference, negative evidence became counter-support/boundary revision rather than global falsification, a special PARTIALLY_RESOLVED state was actually necessary, and H lifecycle/history stayed correct.

## 8.4 Gate

If H evidence cannot naturally enter Stage1/A, stop and fix the integration interface. Do not add a second special-purpose comparison updater.

---

# 9. Phase 2D — Short full-core longitudinal validation

## 9.1 Purpose

After 2A–2C pass, test the integrated core longitudinally. This is where the project begins testing something close to the intended full method rather than an isolated MVP component.

## 9.2 Arms

E-only:

~~~text
native Stage1/A memory formation
+ Established Memory reuse
+ same frozen base generic exploration policy
- no B/C/H
~~~

Full:

~~~text
native Stage1/A memory formation
+ Established Memory reuse
+ B/C/H
+ H-active -> targeted local probe
+ no-H -> same base generic exploration policy
~~~

No-H policy must be symmetric. Do not recreate the historical T0 asymmetry where silence disabled generic exploration.

## 9.3 Initialization

Both arms start from empty experience-derived Established/Exploratory Memory and empty Exploration History. Tool/capability scaffold may be initialized from environment schema.

## 9.4 Execution topology

Each longitudinal stream is strictly sequential. Independent model/arm streams may run in parallel:

~~~text
Flash / E-only   sequential
Flash / Full     sequential
Max   / E-only   sequential
Max   / Full     sequential
~~~

Recommended development scale: 24–32 tasks per stream. Freeze exact count and public-only/outcome-blind registry before calls.

## 9.5 Retrieval

Use the current lightweight retrieval path needed for the integrated core, but do not introduce a new Graph controller.

Record retrieval outcomes so failures can be attributed to Established Memory retrieval, H retrieval/scope compatibility, actor grounding, Stage1, A, B, or C.

Graph contribution and final automatic-retrieval architecture remain separate later validations.

## 9.6 Measurements

Behavioral:
- task success/completion;
- environment actions/tool calls;
- tokens/API cost;
- online latency;
- H-active vs no-H;
- Full vs E-only cumulative differences.

Memory evolution:
- active Memory size;
- CREATE / UPDATE / RETIRE;
- support-only updates;
- scope changes;
- counter-support / unresolved cases;
- duplicate semantic memory;
- semantic drift;
- earliest Flash/Max divergence point.

Exploration:
- B OPEN/NONE;
- C CREATE/NONE;
- H activation/consumption;
- productive / negative / non-diagnostic H tests;
- exploration-history reuse;
- repeated hypothesis rate;
- scope/retrieval mismatch.

## 9.7 Stop rule

Once the preregistered stream completes, do not extend because the result is interesting, tune prompts in-place, replace tasks, or add an arm ad hoc.

If semantically stable enough, move to method freeze + formal evaluation design.

If behaviorally negative but semantically coherent, analyze the method instead of patching until score improves.

---

# 10. Comparison-ledger decision after 2C/2D

Only after native Stage1/A is tested should we decide ledger weight.

Question:

> Does the ledger encode indispensable information not already available from Established Memory + Support + H/exploration provenance?

Possible decisions:

- KEEP — explicit persistent comparison identity/state is genuinely necessary;
- LIGHTEN — retain only question identity, source memory/provenance, linked H, activation/test provenance, and resulting Candidate/Support refs;
- REMOVE AS INDEPENDENT SUBSYSTEM — B can diagnose unresolved comparisons directly and exploration history prevents repeated H.

Do not decide this from Phase 1F status labels alone.

---

# 11. Graph boundary during Phase 2

Phase 2 must remain compatible with the existing Graph design but does not test Graph contribution.

Required:

- stable IDs and provenance for later Graph binding;
- no new taxonomy conflicting with Semantic Concept promotion;
- Text / Support mutations separable from optional Graph mutations;
- Graph not required for Phase 2A success.

Deferred:

- Graph materialization density;
- relation-list optimization;
- Graph contribution ablation;
- Graph-specific online retrieval value;
- multi-hop Graph traversal policy.

---

# 12. Reproducibility and authorization discipline

For every Phase 2 subphase:

1. freeze protocol before model calls;
2. freeze input registry / artifact digests;
3. freeze prompts, model configs, parsing schema;
4. commit transition;
5. only then run authorized calls;
6. preserve raw + parsed outputs;
7. semantic failures remain data; no silent retry unless protocol defines schema retry;
8. results and semantic review are separate commits/docs;
9. never rewrite Phase 1 artifacts.

Phase 2A must be prepared first. Later phases require the previous gate to pass.

---

# 13. Immediate authorized engineering task

Current coding task is Phase 2A preparation only:

- implement historical Stage1 Candidate + Support path for frozen replay;
- implement/adapt support-aware A input construction using bounded pre-task Established Memory;
- preserve Phase 1F artifacts as historical baseline;
- build deterministic Phase 2A registry from the semantic-review bundle;
- add leakage/provenance checks;
- add Flash/Max matched-input assertions;
- add review-artifact generation;
- add tests;
- write an immutable Phase 2A transition document;
- commit/push preparation.

Do not start new model/API calls without explicit researcher authorization after the transition is frozen.

---

# 14. Success criterion for this planning cycle

The planning cycle is complete when the repository contains:

- this Phase 2 plan;
- a Phase 2A coding-agent handoff;
- current-state documents pointing to Phase 2 as active;
- no modification to frozen Phase 1 results;
- no new model/API result presented as already run.

The next scientific checkpoint is the frozen Phase 2A transition, not another conceptual redesign.
