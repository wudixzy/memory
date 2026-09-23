# Coding-Agent Handoff — Phase 2A Core Method Integration Preparation

> Date: 2026-09-23
> Branch: exp/minimal-exploratory-memory-validation
> Governing plan: docs/128_phase2_core_method_integration_validation_plan.md
> Current task: prepare Phase 2A frozen semantic integration replay
> Authorization: implementation, deterministic/no-model analysis, tests, registry creation, documentation, and immutable transition commit are authorized. Do not call Flash/Max or any paid/external model API. Stop after the transition is frozen and report the commit.

---

# 1. Read before editing

Read in order:

1. docs/128_phase2_core_method_integration_validation_plan.md
2. docs/127_semantic_review_bundle_handoff.md
3. docs/review_samples/phase1f_semantic_review/README.md
4. docs/current_state/09_project_master_handoff.md
5. docs/current_state/02_method_architecture.md
6. docs/current_state/03_component_contracts.md
7. docs/37_method_structural_initialization.md
8. docs/38_exploratory_memory_lifecycle.md
9. docs/126_phase1f_ma_v2_semantic_review.md

Also recover the historical Stage 1 Open Mining / Stage 2 Local Knowledge Reconciliation / Support-aware reconciliation design from project docs. Do not replace it with a new architecture.

---

# 2. Scientific hypothesis

Test preparation targets:

[
oxed{
	ext{A material part of Phase 1F memory-evolution instability may come from the MVP bypass/compression of Stage1 and overloading A,}
}
]

rather than a demonstrated need for a heavier comparison-state machine.

Phase 2A therefore isolates representation/integration:

~~~text
same frozen actual trajectory
same pre-task Established Memory
same H/provenance where applicable
-> Stage1 Candidate + Support
-> A / local reconciliation
~~~

No environment rerun is needed for Phase 2A preparation.

---

# 3. Frozen conceptual constraints

## Stage1

~~~text
Full completed trajectory
No Existing Memory
-> Candidate Content + Support
~~~

Support semantically includes Direct Grounding, Minimal Global Context, provenance, and optional bounded verification grounding.

Stage1 does not decide historical superiority, comparison resolution, future H, or Graph policy.

## A / Stage2

Primary comparison:

~~~text
Candidate <-> Current Text Memory
~~~

Use bounded relevant Existing Memory and compact Support context.

Reasoning:

~~~text
Existing coverage
-> semantic delta
-> decision relevance
-> evidence sufficiency
-> minimal mutation
~~~

## Support

Keep complete historical Support auditable; keep model-facing Support bounded and diagnostic.

## B/C/H

Do not tune B/C/H as part of Phase 2A preparation except strictly mechanical compatibility changes. Document any required compatibility change.

## Graph

Do not implement a new Graph design. Keep compatibility only.

## Comparison ledger

Do not add new states, scores, or taxonomy. Preserve existing records as provenance/telemetry.

---

# 4. Phase 2A data source

Use only frozen existing artifacts.

Primary source:

~~~text
docs/review_samples/phase1f_semantic_review/
~~~

Build a deterministic registry selecting these primary diagnostics:

- case 03 cool Pan;
- case 02 cool Egg;
- case 05 clean Cloth;
- case 09 Max T1 SoapBar;
- case 04 Lettuce;
- case 01 cool Tomato;
- case 10 Task1 -> Task2 topology chain.

Resolve exact case IDs/paths from the bundle index/manifest. Do not guess.

Remaining bundle cases may be secondary review inputs, but keep primary vs secondary explicit.

Do not inspect hidden PDDL/oracle/evaluator fields to construct model-visible inputs.

---

# 5. Implementation target

Create a new versioned Phase 2A path. Do not mutate historical Phase 1C–1F runners or artifacts.

Follow existing repository naming conventions; a phase2a_* namespace under experiments/exploratory_memory_mvp is acceptable if consistent.

Implement:

## A. Stage1 input builder

From the frozen actual trajectory/evidence package construct the historical Stage1 view.

Requirements:

- current completed trajectory only;
- no Existing Memory;
- no E0/counterfactual reference;
- no hidden placement/oracle answer;
- retain actual H activation/probe facts when part of the trajectory;
- deterministic source references.

## B. Stage1 output schema

Use the minimum schema needed for historical Candidate + Support.

Do not introduce comparative-strength enums or new permanent Memory taxonomy.

It must support:

- Candidate semantic content;
- direct grounding;
- minimal global context;
- provenance;
- source H/comparison references when applicable as provenance, not truth labels.

## C. A input builder

Construct:

~~~text
Candidate
+ Candidate Support
+ bounded relevant pre-task Established Memory
+ compact relevant Support view if available
+ provenance/H-test context
~~~

Use pre-task memory snapshot. Do not let current-trajectory updates leak into the historical side.

## D. Historical baseline

Saved Phase 1F A outputs are the historical comparison condition.

Do not rerun or modify them.

## E. Review artifact builder

Prepare deterministic output alignment so future authorized runs can inspect, per case/model:

~~~text
source trajectory/evidence
historical A output
Stage1 input
Stage1 raw/parsed output
A restored input
A restored raw/parsed output
proposed memory mutation
token/cost telemetry
provenance checks
~~~

Manual Flash/Max comparison on the same evidence must be easy.

---

# 6. Mechanical validations before any model call

Add tests/assertions that:

1. every registry entry resolves to frozen source artifacts;
2. source digests are frozen;
3. Stage1 has no Existing Memory;
4. Stage1/A have no E0 researcher counterfactual;
5. no hidden PDDL/oracle/evaluator leakage;
6. A uses pre-task Established Memory;
7. matched Flash/Max cases use equivalent public evidence inputs;
8. Phase 1 artifacts are read-only;
9. comparison ledger is not semantically rewritten by preparation code;
10. H provenance is preserved when present;
11. schema failures are fail-closed;
12. new output paths are versioned and cannot overwrite old runs.

Run repository-standard focused tests, compileall, lint/ruff if configured, and git diff --check.

---

# 7. Prompts to freeze, not execute

## Stage1 prompt

Encode the historical contract:

- whole-trajectory understanding;
- potentially reusable Candidate Experience;
- evidence-grounded;
- minimal context needed to avoid misinterpretation;
- no historical comparison;
- no unnecessary generalization;
- no superiority/default claim unless literally supported by the trajectory;
- no exploration recommendation.

## A prompt

Encode historical local reconciliation:

- Existing Memory first;
- Candidate has no automatic write authority;
- evaluate semantic delta;
- conservative generalization;
- specialization for missing conditions;
- unresolved/contested is legal;
- minimal mutation;
- support-only update is legal;
- no opportunistic cleanup;
- claim authority must not exceed evidence.

Do not optimize A to match old Flash labels.

---

# 8. Review rubric to freeze now

Required dimensions:

~~~text
evidence_fidelity
scope_fidelity
preference_overreach
useful_learning
contradiction_handling
cross_model_semantic_agreement
input_token_cost
~~~

Preference overreach means a memory update asserts or operationally encodes a default/preference/superiority claim not supported by available evidence.

Do not require reviewers to reproduce OPEN / PARTIAL / RESOLVED.

---

# 9. Transition document

After implementation/tests create an immutable transition document, recommended:

~~~text
docs/130_phase2a_semantic_integration_transition.md
~~~

Record:

- exact parent commit;
- registry path + digest;
- selected cases;
- source artifact digests;
- Stage1 schema/prompt digest;
- A schema/prompt digest;
- intended later model configs;
- output directory;
- leakage checks;
- test commands/results;
- explicit statement that 0 model/API calls were made during preparation;
- exact later commands for Flash and Max;
- stop rule.

Commit and push transition before any future model call.

---

# 10. Model config to prepare, not execute

Prepare matched configs for:

~~~text
qwen3.8-flash
qwen3.8-max
thinking = false
temperature = 0
~~~

If the repo frozen config differs, use the exact existing Phase 1F configs and document them.

Do not silently change provider/model defaults.

---

# 11. Non-goals

Do not:

- run Phase 2B/C/D;
- run new ALFWorld episodes;
- call Flash/Max;
- tune B/C/H;
- add Graph ontology;
- add confidence scores;
- add NONE/INDIRECT/MATCHED/DIRECT;
- redesign comparison ledger;
- create a Boundary Retriever;
- rewrite old Phase 1 artifacts;
- make Claim + Evidence Basis + Unresolved Boundary a mandatory physical schema;
- optimize behavioral score.

---

# 12. Deliverable / stop condition

Stop when Phase 2A preparation is complete and pushed.

Report:

1. commit SHA;
2. files added/changed;
3. registry size and digest;
4. selected primary cases;
5. tests and results;
6. compatibility issues;
7. exact later execution commands;
8. confirmation that no model/API call was made.

Do not proceed to model execution until researcher authorization.
