# AGENTS.md

Active branch:

    exp/minimal-exploratory-memory-validation

Current cycle: **Phase 1A Controlled Targeting Fast Track (v2)**.

Baseline:

    bd4541698f37639e9a29a3e79543cda56609c047

Read first:

1. docs/83_phase1a_controlled_targeting_fast_track_plan.md
2. docs/82_phase1_s1c_structured_output_results.md
3. docs/63_phase1_fair_c2_specification.md
4. docs/69_phase1_pre_pilot_correction_results.md

## Scientific goal

Stop actor micro-optimization and obtain the first direct evidence for:

    C3 history-derived targeting
    vs
    C2 fair structured generic exploration

on the frozen 20-target receptacle-search distribution.

The retired autonomous actor and docs/67–82 remain historical evidence. Do not
weaken the old runner's pending-actor gate; implement a separate versioned
`phase1a-controlled-targeting-v2` path.

## Controlled actor contract

Only the search selector makes an online policy decision.

Selector input is public and symmetric across C2/C3:

- target object type parsed from the public task instruction;
- current public observation;
- remaining candidate receptacles;
- inspected-candidate public ledger;
- canonical established search guidance;
- C2 generic H or C3 targeted H.

Selector output:

    {"candidate_index": legal_index}

Use one frozen selector config:

    qwen3.8-max
    temperature=0
    thinking=false
    strict dynamic JSON schema

The shared executor deterministically navigates to the selected candidate, opens it
when the exact public action is legal, inspects the public result, and takes only an
exact matching target object when its exact take action is admissible.

No semantic fallback, wrong-object take, hidden state, oracle, clamp, retry-to-repair,
or condition-specific execution logic.

Controlled probe budget:

    max_candidate_probes = 2

Primary endpoint is target acquisition, not full downstream task completion.

## This cycle

1. Implement/freeze the controlled parser, ledger, selector interface, executor,
   paired runner and focused no-model tests.
2. Commit/push the immutable no-model transition.
3. Generate deterministic canonical-K* source trajectories for the existing Source 5.
4. Fix mandatory B/C source referential binding; run B/C once per source with one
   frozen offline config.
5. Preserve B=NONE/C=NONE; never swap source tasks for favorable H.
6. If zero live H entries survive, STOP.
7. Otherwise freeze source-H manifest and run exactly the frozen 20 targets:
      C2 x1 + C3 x1
   with paired replay specs.
8. Commit/push the result and STOP for researcher review.

## Primary metrics

Per unique target:

- target acquired within two candidate probes;
- candidate probes to acquisition;
- paired C3-vs-C2 win/tie/loss.

Environment steps, selector calls, tokens and cost are secondary.

Scientific n = 20 targets, not 40 episodes.

## Allowed checks before paid calls

Only focused parser/executor/ledger tests, pairing/leakage tests, fake-selector
condition-isolation tests, structured candidate-enum tests, and one no-model/synthetic
mechanical smoke.

No paid pilot and no new actor gate.

## Forbidden

Do not:

- run B1-R;
- rerun/tune S1/S1C or any autonomous actor;
- test a second selector model;
- change K* or history representation;
- resample Source/Target;
- add C1/repetitions before first C2/C3 review;
- run Stage1/A/native cold start/Phase 2+;
- use hidden placement/PDDL/expert/evaluator information.

The next milestone is the first real paired C3-vs-C2 targeting-value result.
