# 106. Phase 1C Experiment Design Handoff

Date: 2026-09-21  
Branch: `exp/minimal-exploratory-memory-validation`  
Current protocol commit at handoff creation: `7ab583653b9666d41a40dca131afc2f32389b656`  
Frozen Phase 1B implementation baseline: `c8daa67ba9d9d6257d65e446b437d362e60abc61`

## 1. Purpose of this handoff

This document is the shortest path for a new researcher/agent to continue Phase 1C experiment design and execution without reopening the long Phase 0/1A/1B development history.

The current task is not to invent a new method and not to produce the final paper experiment.

The current task is:

\[
\boxed{
\text{Run one scale-aware hypothesis pilot that can tell us whether this research direction
deserves larger experiments.}
}
\]

The active experiment specification is `docs/102_phase1c_flash_scale_hypothesis_pilot_plan.md`.

## 2. Scientific story that is already stable

Persistent memory normally converts successful history into reusable guidance.

The epistemic gap motivating this project is:

\[
\boxed{
\text{Feasibility Evidence} \neq \text{Comparative Evidence}
}
\]

A successful realization proves that it worked in the observed scope. It does not prove that it is better than plausible alternatives.

The proposed method therefore maintains two main semantic forms:

- Established Memory: evidence-supported reusable guidance;
- Exploratory Memory \(H\): a future-facing, local, one-shot experiment derived from an unresolved comparative question.

The stable semantic loop is:

\[
K_t
\rightarrow
B
\rightarrow
C/H
\rightarrow
\text{future probe}
\rightarrow
E
\rightarrow
A
\rightarrow
K_{t+1}
\]

B diagnoses which incumbent comparison remains worth opening. B does not invent the concrete alternative.

C receives an abstract Functional Contract plus local public facts/capabilities and synthesizes one grounded future probe. C must not receive the completed source answer.

A sees actual E1 evidence only and conservatively reconciles Established Memory.

Online remains lightweight; heavy semantic memory evolution is between episodes.

## 3. Exploratory-memory lifecycle patch now part of the method

The current method distinguishes:

\[
K_{active}^{exploratory}
\]

from:

\[
\mathcal E^{history}
\]

An active H is online-retrievable and one-shot.

Once actually activated:

\[
H^{active}
\rightarrow
\text{consumed}
\]

and a compact record is appended to the offline exploration-history archive.

Consumption means only "this experiment was attempted once." It does not mean confirmed/falsified.

Future C can retrieve a few relevant archive records to avoid proposing an equivalent experiment again.

B does not read archive in the MVP.

No hard semantic similarity rule is used. C decides whether a related old exploration is equivalent, materially different, or worth retesting.

See `docs/38_exploratory_memory_lifecycle.md`.

## 4. What previous experiments have actually established

### Phase 0 / mechanism work

Established or audited:

- B/C responsibility boundary;
- source/future grounding separation;
- H target-time grounding;
- H one-shot lifecycle;
- public action-index execution;
- actual evidence logging;
- E1-only A;
- pairing/replay/public-state controls;
- fail-closed leakage behavior.

These are mechanism/instrument results, not method-effectiveness results.

### Phase 1A — single-transfer controlled targeting

A 20-target C2 vs C3 controlled targeting pilot established:

- H materially changes selector behavior;
- history-derived intervention is behaviorally real;
- immediate two-probe acquisition superiority was not observed;
- the two-probe endpoint was strongly censored;
- the small source set generated a low-diversity open-surface-first family.

Interpretation:

> Single-H micro-transfer is not the right main scale for the method.

Do not rerun or continue tuning Phase 1A.

### Phase 1B — longitudinal system calibration/hardening

The full minimum chain has now executed:

\[
B/C\text{ creates H}
\rightarrow
\text{future retrieval}
\rightarrow
\text{probe}
\rightarrow
A
\rightarrow
\text{Established Memory materialization}
\]

The system was hardened so that:

- facts commit independently of semantic failures;
- H consumption persists;
- B→C source-answer leakage is blocked;
- C future H entity leakage is blocked;
- evidence IDs/provenance are runner-owned;
- temporal entry/exposure/acquisition facts are explicit;
- reconciliation no longer invents epistemic closure;
- A assessment and Established Memory update failures are fault-isolated;
- ADD/REFINE/SPECIALIZE/MERGE have real materialization semantics.

Final Phase 1B decision:

`READY_FOR_SCALE_WITH_KNOWN_LIMITATIONS`

See `docs/101_phase1b_final_freeze_memo.md`.

## 5. Known limitations intentionally carried forward

These are not reasons to reopen development before Phase 1C:

1. B Functional Contract may fail closed if it contains source entities.
2. Comparison identity may create near-duplicate open comparisons.
3. Automatic H retrieval quality is not yet validated at scale.
4. The current ALFWorld executor is a controlled search abstraction, not a full autonomous actor.

These are scale-time diagnostics unless they create new correctness corruption.

## 6. The current hypothesis

The project now tests a scale-positive story.

### H1 — history changes future exploration

More history should produce different targeted H/probes than persistent generic exploration.

### H2 — exploration history suppresses redundancy

As \(\mathcal E^{history}\) grows, future C should sometimes stop proposing equivalent already-tested experiments or produce materially different ones.

### H3 — cumulative behavior begins to improve

If H1/H2 are useful, Targeted should begin to use exploration budget better and show improving cumulative search cost relative to Generic as history grows.

The pilot is allowed to show H1/H2 without a strong H3 effect yet; that can still justify a longer horizon.

## 7. Frozen Phase 1C pilot skeleton

### Model

Flash first:

```text
qwen3.8-flash
thinking=false
temperature=0
```

Use Flash for all model-facing roles.

Max is not part of the first pilot.

### Data

One fresh 32-task stream:

```text
8 simple
8 clean
8 cool
8 heat
```

Order is deterministic family interleave:

```text
simple -> clean -> cool -> heat -> repeat
```

The stream is continuous and dependent; checkpoints do not reset memory.

### Arm G — Generic Evolving Exploration

Reuse the Phase 1A C2 generic exploration primitive on every eligible task.

```text
G Established Memory
-> generic C2 probe <=2
-> deterministic continuation
-> actual evidence
-> A
-> next G Established Memory
```

G has no B/C/H/comparison/archive state.

### Arm T — Targeted Exploratory Memory

```text
T Established Memory
+ active H
+ comparison ledger
+ Exploration History
```

At task start:

```text
relevant active H -> targeted probe <=2 -> consume/archive -> continuation
no relevant H     -> continuation directly
```

After evidence:

```text
A -> Established Memory update
```

After episode:

```text
trajectory + K_pre
-> B
-> if OPEN:
     retrieve top-3 relevant archive records
     -> C
     -> CREATE / NONE
```

T does not fallback to generic C2 when no H exists.

## 8. Primary and mechanism observations

Primary behavioral measure:

\[
C_a(N)=\sum_{t=1}^{N}\text{environment actions to target acquisition}_{a,t}
\]

for \(a\in\{G,T\}\).

Report at:

\[
N=8,16,24,32
\]

and inspect:

\[
\Delta C(N)=C_T(N)-C_G(N)
\]

Do not demand monotonic superiority.

Mechanism review is intentionally minimal:

- M1: does H/comparison state actually grow/evolve?
- M2: does accumulated history actually change T probes relative to G?
- M3: does exploration history suppress/redirect repeated exploration?

## 9. Why Generic is intentionally simple

Do not reopen the debate about making Generic maximally reviewer-proof.

This is still a hypothesis pilot.

Generic intentionally reuses the already tested Phase 1A C2 primitive on every task.

The purpose is to ask whether a persistent history-conditioned exploration process begins to behave differently and accumulate value relative to persistent generic exploration.

A context-only PROBE/NONE gate, Established-only third arm, archive ablation and other controls are deferred until there is a signal worth explaining.

## 10. Why Flash is first

This pilot intentionally prioritizes Flash.

Reasons:

- it is cheaper for a longer longitudinal horizon;
- smaller models may benefit more from explicit persistent memory;
- if no mechanism develops under Flash, immediately running Max is not automatically useful.

If Flash shows a behavioral or meaningful mechanism signal, a later researcher decision can replicate the frozen protocol with Max.

Do not create mixed-model combinations in Phase 1C.

## 11. Fresh-task scientific boundary

Fresh selection is one of the few remaining high-risk design points.

Before calls:

- enumerate untouched public-only eligible tasks;
- exclude every previously consumed Source/Calibration/Target/Phase1B dev task;
- preserve the untouched B1-R reserve;
- require an actual search subproblem from public entry state;
- select deterministically before any arm result;
- commit exact registry/order/digest before model calls.

Never use hidden placement, PDDL answers, outcomes, oracle routes or expected arm winners.

If the required fresh pool is unavailable, stop before calls rather than contaminating the pilot.

## 12. What a new agent is allowed to discuss/change before execution

A new researcher may still discuss implementation-neutral details needed to instantiate `docs/102`, especially:

- exact public-only fresh eligibility implementation;
- deterministic fresh sampling salt;
- artifact/state schema for Exploration History;
- compact archive retrieval packet;
- how to reuse Phase 1A C2 without altering its scientific behavior;
- checkpoint/result-report layout;
- no-model tests proving G/T isolation and fresh registration.

These should remain minimal.

## 13. What a new agent should not reopen

Without new evidence, do not redesign:

- A/B/C semantic roles;
- B/C responsibility separation;
- H one-shot lifecycle;
- archive as offline-only history;
- B access to archive;
- source/future grounding;
- A counterfactual access;
- online semantic memory update;
- graph search controller;
- VOI planner;
- autonomous actor stack;
- native cold start;
- generic PROBE/NONE gate;
- third arm;
- archive ablation;
- Max-first experiment;
- multiple independent streams.

Do not use the old development tasks to tune Phase 1C.

## 14. Expected implementation workflow

### Before model calls

1. create a separate `phase1c-scale-pilot-v1` implementation path;
2. implement Exploration History state and fact commit;
3. implement top-3 archive retrieval;
4. pass only selected compact archive summaries to C;
5. reuse G=C2;
6. build the untouched 32-task registry;
7. prove G/T replay/public-state equivalence;
8. prove G cannot see T history;
9. prove archive is written only after actual H activation;
10. run no-model focused/regression checks;
11. commit/push immutable transition and `docs/103...`.

### Paid run

Run all 32 tasks for G and T with frozen Flash protocol.

No result-driven edits, retries, task replacement or Max calls.

### Review

Write `docs/104...` and `docs/105...`.

Separate:

- performance;
- H1;
- H2;
- H3;
- failure decomposition;
- Max recommendation.

Then STOP for researcher review.

## 15. What counts as a useful pilot result

### Strongest useful outcome

Targeted begins to improve cumulative cost relative to Generic and mechanism artifacts show H/archive/A functioning as expected.

### Still useful

Cumulative cost is not yet separated, but history clearly changes probes, archive reduces redundancy, and A/comparison state evolves. This can justify a longer horizon or Max replication.

### Weak/negative mechanism outcome

H remains repetitive, archive rarely changes C, retrieval rarely activates, or T/G behavior barely diverges. Review the scale hypothesis before spending more.

### Strong negative hypothesis evidence

The mechanism genuinely works and changes behavior, but cumulative behavior does not improve as history grows. This is more informative against the core idea than another micro-pilot failure.

## 16. Evidence discipline

Evidence strength order remains:

1. actual environment execution + immutable artifact;
2. deterministic replay/public-state proof;
3. committed fresh registry/digest;
4. model-visible input/output artifacts;
5. code invariant/test;
6. semantic reviewer judgment;
7. design prose.

Do not upgrade a semantic interpretation above actual execution evidence.

## 17. One-sentence project state

> The project has finished mechanism construction and interface hardening; the next task is the first 32-task Flash longitudinal pilot testing whether accumulated exploratory memory and exploration history begin to create scale-dependent value beyond persistent generic exploration.
