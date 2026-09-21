# Phase 1D Flash Long-Horizon Validation Plan

Date: 2026-09-21
Branch: `exp/minimal-exploratory-memory-validation`
Status: protocol prepared; researcher authorization required; no run started

## 1. Purpose and authorization boundary

Phase 1C completed a single 32-task Flash development stream. Its artifacts
showed a real H1 mechanism signal and a descriptive cumulative T-versus-G
action signal, but H2 duplicate suppression remains unresolved. The H2 audit
in `docs/107_phase1c_h2_exploration_history_audit.md` found no correctness
blocker and one confirmed redundant CREATE.

This document prepares, but does not authorize or execute, a longer-horizon
validation. No model/API transport is initialized by this document. Phase 1D
must begin only after explicit researcher authorization and a new immutable
transition commit.

The default question is:

> Does the Phase 1C mechanism/value signal survive as longitudinal history
> grows from N=32 to N=64?

This remains development validation, not a paper-level superiority test.

## 2. Continue from the frozen Phase 1C endpoint

Do not restart from `K*`. Continue from the exact saved endpoint of the
immutable Phase 1C run:

```text
runtime:
artifacts/exploratory_memory_mvp/phase1c-scale-pilot-v1-20260921-60c2474

G endpoint:
G_memory_snapshots/M_032.json

T endpoint:
T_state_snapshots/M_032.json
```

The continuation must verify the saved state digests against
`stream_summary.json` before any model call. The two arms remain independent:

```text
G: its M_032 Established Memory only
T: its M_032 Established Memory + active H + comparison ledger
   + exploration history
```

No state is copied from G to T or from T to G. The Phase 1C task 32 artifacts
remain immutable and are not re-executed.

## 3. Fresh suffix population

Add exactly 32 fresh, untouched tasks for indices 33–64:

```text
8 pick_and_place_simple
8 pick_clean_then_place_in_recep
8 pick_cool_then_place_in_recep
8 pick_heat_then_place_in_recep
```

Use the same deterministic interleave as Phase 1C:

```text
simple -> clean -> cool -> heat -> repeat
```

Before any model/API call, build and freeze a new public-only registry. The
eligible universe must exclude:

* every Phase 1C task ID;
* all historical Source, Calibration, Target and Phase 1B development task
  IDs required by the existing registry discipline;
* the protected B1-R reserve and any other committed exclusion set;
* tasks outside the four admitted families;
* public entry states where the exact target take action is already available;
* public states without enough candidate receptacles to form a meaningful
  search subproblem.

Eligibility and deterministic selection may use only public task/family
metadata, public instruction, public reset observation, ordered admissible
actions and public affordance structure. Do not inspect PDDL, hidden
placements, oracle routes, prior arm outcomes or expected winners. If any
family has fewer than eight eligible tasks, stop before model calls and report
the public-only shortage; do not relax criteria after looking at outcomes.

Persist and commit before the run:

* the complete eligible universe;
* inclusion/exclusion reasons;
* selected task IDs and exact order;
* requested seed and replay specifications;
* public initial fingerprints;
* registry and selected-ID digests;
* a proof that the suffix is disjoint from every protected population.

The suffix is the only new population. Do not resample the first 32 tasks.

## 4. Frozen arms and per-task behavior

Keep the exact Phase 1C scientific behavior. The only change is the fresh
task suffix and the continued memory state.

### G — persistent generic exploration

For every suffix task, G receives the same Phase 1C generic C2 opportunity:

```text
G Established Memory
-> generic candidate selector, maximum two candidate probes
-> deterministic canonical continuation if needed
-> target acquisition evidence
-> Phase 1B A/fact commit
-> next G Established Memory
```

G must not receive T's H, comparison ledger or exploration history. Do not
add a Generic `PROBE/NONE` gate.

### T — history-conditioned exploratory memory

T continues its Phase 1C state:

```text
T Established Memory
active H
comparison ledger
Exploration History
```

At task start, retrieve at most one active H. If activated, run the same
targeted two-candidate probe, consume the H, append one compact archive record
only after actual activation, and continue canonically if needed. If no H is
activated, go directly to canonical continuation; do not fall back to Generic
C2.

After actual execution, retain the frozen Phase 1B ordering:

```text
fact commit
-> A actual-evidence reconciliation
-> B on the pre-update established snapshot
-> history retrieval only after B=OPEN
-> C with the abstract contract and compact selected history
-> H/comparison identity reconciliation
```

Do not change prompts, schemas, lifecycle, archive semantics, comparison
identity, probe budget, or canonical executor during the suffix run.

## 5. Shared mechanical controls

G/T must share, for every target:

* exact task ID and order;
* same replay specification;
* same public initial fingerprint;
* `qwen3.8-flash`, `thinking=false`, `temperature=0`;
* same candidate-index selector interface;
* maximum two candidate probes;
* same controlled executor and canonical continuation;
* same exact-target-acquisition endpoint;
* same fact-commit and fail-closed semantics;
* same artifact and usage retention.

Pairing must be verified before the first model call for each pair. A failed
pairing blocks the pair; do not replace or selectively rerun it for a nicer
result.

## 6. Primary quantities

Keep the Phase 1C primary behavioral quantity:

```text
C_G(N) = cumulative G environment actions to exact target acquisition
C_T(N) = cumulative T environment actions to exact target acquisition
Delta C(N) = C_T(N) - C_G(N)
```

Report cumulative checkpoints:

```text
N = 40, 48, 56, 64
```

Also report the marginal suffix, separately from the already observed
development stream:

```text
C_G(33:64)
C_T(33:64)
Delta C(33:64)
```

The scientific longitudinal unit remains the stream, not 32 independent
replicates. Do not turn the continuation into a significance test.

Retain descriptive per-task paired deltas, candidate inspections,
environment actions, selector calls, input/output/cached tokens and available
cost records. The acquisition endpoint still does not claim complete
ALFWorld clean/cool/heat/place success.

## 7. Minimal mechanism observations

Do not create a larger metric suite. At checkpoints and at the final suffix,
record:

```text
B OPEN/NONE
C CREATE/NONE
H created / active / consumed
H activation count
archive size
history retrieval SELECT/NONE and selected real IDs
comparison count/status
reconciliation operation
```

Also retain descriptive growth telemetry for:

```text
active H backlog
comparison backlog
reconciliation input characters/tokens
history retrieval and C context size
```

Repeat the manual H2 audit on suffix cases and the combined endpoint, using
the same four CREATE labels and three NONE labels. Do not use those labels to
modify the running protocol.

## 8. Run discipline and failure policy

Before paid calls, run focused no-model tests, Phase 1B/Phase 1C regressions,
Ruff, compile checks and `git diff --check`; then commit and push an immutable
Phase 1D transition. That transition must freeze the registry, continuation
state digests and the exact model/config.

During the authorized run:

* do not tune after early checkpoints;
* do not retry scientific/model failures;
* do not replace tasks;
* do not add Max or a third arm;
* do not inspect hidden target placement;
* preserve all failure artifacts;
* stop only if an infrastructure failure prevents protocol execution.

No Phase 1D command, transport, registry or task selection is created by this
planning-only cycle.

## 9. Interpretation categories

The post-run review should distinguish:

### Scale-positive

Cumulative T advantage continues or grows, while H/comparison state remains
semantically reasonable.

### Saturation

The advantage stabilizes and the history/backlog also stabilizes without a
correctness failure.

### Scale degradation

The advantage shrinks or reverses as accumulated state grows.

### Mechanism overproduction

H/comparison backlog grows through repeated near-duplicate proposals, even if
the behavioral endpoint is temporarily favorable.

### Mechanism-positive / behavior-negative

History continues to alter exploration in interpretable ways, but cumulative
behavior does not improve. This is useful negative evidence against the
value hypothesis, not a reason to hide the mechanism signal.

## 10. Validation-to-formal roadmap

The intended progression is:

```text
Phase 1C Flash 32-task pilot
    -> Phase 1C H2 artifact audit
    -> Phase 1D Flash N=32 to N=64 validation
    -> cross-model validation
    -> freeze Method v1 / Evaluation v1
    -> formal controlled longitudinal evaluation
    -> full-system/native-cold-start evaluation
    -> cross-benchmark generality if justified
```

The project should not remain indefinitely in development validation. A
reasonable gate into formal experiments is:

1. accumulated history continues to produce meaningful exploration
   differentiation;
2. no systematic redundancy or severe over-suppression is visible;
3. longer-horizon accumulation does not collapse the mechanism;
4. no correctness blocker remains in provenance, facts, H lifecycle or A/B/C
   boundaries;
5. preferably the core mechanism is reproduced with a second model.

After those conditions are sufficiently met, stop tuning on development
streams, freeze Method v1 and Evaluation v1, register fresh confirmatory
streams, and begin paper-level evaluation.

The later formal stage should eventually address:

* multiple independent longitudinal streams;
* a fresh confirmatory population;
* stream-level statistical units;
* full-task completion in addition to target acquisition;
* environment-action and model/token cost;
* at least two model configurations;
* an attribution control if needed to isolate H content from no-H/generic
  opportunity asymmetry.

These are not Phase 1D implementation requirements.

## 11. Current status

Phase 1D is **pending researcher authorization**. This document does not
authorize model calls, Flash execution, Max execution, lifecycle changes, or
fresh target selection. The current Phase 1C stream remains development
evidence and must not be relabeled as confirmatory evidence after any protocol
change.
