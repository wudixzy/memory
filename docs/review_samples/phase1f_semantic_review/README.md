# Phase 1F Semantic Review Bundle

> **The bundle is intended for researcher review of A/comparison semantics,
> especially feasibility evidence versus comparative evidence. It is not a
> new experiment or a relabeling dataset.**

This bundle assembles a compact, source-grounded subset of frozen Phase 1C,
Phase 1D, Phase 1E, and Phase 1F-MA-v2 artifacts. It supports human review
of A's inputs and assessments, their relation to public evidence, and how
early evidence/routing differences appear in later comparison/H topology.

No semantic correctness judgment is made here. The bundle does not decide
whether a Flash or Max assessment was right, whether an H was objectively
useful, or what Method v1 should be.

## Evidence boundary

Included: public task instructions, reset observations/actions, public
trajectory records, model inputs/outputs, validators, and public-facing
memory/H/comparison/archive fields. No hidden PDDL file/content, hidden
placement, oracle/expert route, evaluator answer, or privileged state was
opened or used. `won`, `reward`, and related evaluator fields are removed
from structured projections. Registry `replay_spec` fields are omitted;
pairing proofs retain only task ID, seed, and public fingerprints, while
carrier-internal file identities/hashes are omitted.

Raw model responses and parsed outputs are copied exactly when present.
Structured inputs/state are field-preserving or concise projections.
Prompt instruction messages are retained; large episode-specific user
payloads are referenced by source path/digest and represented in adjacent
structured input projections rather than duplicated in full prompt files.
Unavailable or inapplicable stages are marked `not_available` with a
stage-specific reason; their expected source paths remain recorded.
Manifests record source path/SHA-256, extraction type, removed JSON
pointers, and output SHA-256. Large evidence-store histories are referenced
by source snapshot digest rather than copied wholesale.

## Selection

There are 12 cases. A deterministic scan covered all 64 aligned Flash/Max
task identities for accepted A `PARTIALLY_RESOLVED` versus `REMAINS_OPEN`
with actual H activation. See `selection_universe.json` for the full
candidate universe and selected strata. Five matched cases cover probe
misses/hits and a clean-family related-realization case. Additional cases
meet explicit criteria for Flash partial assessments after H-probe
acquisition, Max acquisitions with A remaining open, and the early
two-episode T0/T1 topology chain. One prereported Max cool-Pan outlier is
included only as context.

Selection is for review coverage, not score balancing or model preference.
Categories may overlap; see `index.md`.

## Source coverage

* Phase 1C Flash: `phase1c-scale-pilot-v1-20260921-60c2474`
* Phase 1D Flash: `phase1d-long-horizon-v1-20260921-ac0bb2b`
* Phase 1E Max: original tasks 1–61 and resume tasks 62–64
* Phase 1F-MA-v2: the frozen 12-task six-stream runtime

Only selected review files are copied/extracted; complete runtime
directories are not included. `bundle_manifest.json` and per-case
`manifest.json` map outputs back to source artifacts.

No model/API call was made. Frozen artifacts were not modified. This is
evidence assembly only.
