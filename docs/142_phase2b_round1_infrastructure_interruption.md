# Phase 2B Round 1 — Infrastructure Interruption

Date: 2026-09-25
Branch: `exp/minimal-exploratory-memory-validation`
Frozen transition: `11b80a9f40e8b8f3e0706a5053eaa4ff71c7b941`

This records the incomplete first Phase 2B calibration execution. It is not a
completed Round 1 result, not a tuning decision, and not a Phase 2B gate.

## Frozen corpus collection

The fixed corpus completed before memory tuning:

| Item | Result |
| --- | --- |
| Runtime | `artifacts/exploratory_memory_mvp/phase2b-native-corpus-v1/` |
| Population registry identity | `5d8b1620bdb469920d29bf7c276fca46acd8eb6930a8473346f3e8a57f7e5424` |
| Run manifest SHA-256 | `3fd74a4dc482ac1994ee4577d59cca02270ca7fd2c3d83691c5f6e92c0ec5beb` |
| Manifest identity validation | PASS; exact 24 registry rows / replay specs |
| Terminal trajectories | 24/24 |
| Task outcomes | 3 wins, 21 terminal non-wins |
| Environment actions | 1,091 |
| Flash actor calls | 1,091 |
| Semantic retries / task replacements | 0 / 0 |
| Input / cached input / output tokens | 3,238,458 / 1,946,624 / 12,928 |
| Known cost subtotal | CNY 0.6828292 across 365 priced calls; 726 calls unpriced |

The cost subtotal is partial and is not an estimate for unavailable pricing
records. All task summaries report `completed_terminal`; the non-win outcomes
remain valid observed full-task trajectories, not missing tasks.

## Round 1 interruption

The frozen Flash Round-1 calibration stream is at
`artifacts/exploratory_memory_mvp/phase2b-round1-flash-calibration-v1/`.

| Item | Result |
| --- | --- |
| Config SHA-256 | `5aaa50b66ff2f42112d2bc4c53a0300bc9e1b444d9f8d8deef9afad8b2144f94` |
| Stream summary SHA-256 | `44723633017f5edf9111199c64db254a148f68ffcd0efa24dc00b396a566e07e` |
| Run status | `stopped_infrastructure_failure` |
| Attempted calibration tasks | 8 of 12, in frozen order |
| Stage 1 | 8 accepted, 0 failed closed |
| A | 1 accepted, 6 semantic/schema failed closed, 1 transport failure |
| Model calls | 8 Stage 1 + 8 A attempts = 16 |
| Input / cached input / output tokens | 325,994 / 6,144 / 8,180 |
| Known cost subtotal | CNY 0.2367099 across 9 priced calls; 7 unpriced |
| Usage-unavailable calls | 1 |
| Semantic retries / task replacements | 0 / 0 |

Six visible A responses were rejected by the local frozen validator: task 1
and task 7 failed `CREATE/UPDATE requires evidence-bound Support`; tasks 3–6
failed `UPDATE requires exactly one active memory target`. Task 2 A was
accepted. These are observable contract-validation outcomes, not a semantic
judgment about the model's hidden reasoning. Raw responses, parsed output,
usage and validation artifacts remain in their task directories.

On task 8, Stage 1 was accepted and its Candidate Support was runner-bound.
The A request produced no visible response; the privacy-safe transport artifact
records only `error_class = DashScopeError`, with no usage response. The run
manifest marks the task and stream `stopped_infrastructure_failure`. Its
pre-task state digest is
`fb5a9d5c47f4980f7c776bd3d3f099fb0c98c974510188d0948237be916f8e64`, and its
post-task state digest is
`e8d72c6ab2d713372a67a2c7e643d4821f2eb0637d88cfb0f70c235a6852eb68`.
The task facts, trajectory and valid Stage 1 Support remain persisted; A did
not materialize a memory mutation for task 8.

The transport intentionally does not persist the underlying exception message,
so the artifacts do not distinguish provider-side, network, or other
transport-level causes beyond the safe error class. No retry was attempted.

## Stop decision and boundary

Round 1 is incomplete and cannot support its planned 12-task calibration
review. No semantic tuning change was made. Do not continue from task 9, replay
task 8, restart the stream, or start Round 2/3/4 automatically: the frozen
runner has no resume path, and any recovery would require an explicit
researcher-approved protocol decision.

No Phase 2C/B/C/H integration, Max sanity run, formal evaluation, Phase 2A-X
cross-feed call, or Method v1 freeze occurred. The Phase 2A-X package remains
`FROZEN_OPTIONAL_DIAGNOSTIC`. The original Phase 2B transition and all Phase 1
and Phase 2A historical artifacts remain unchanged.

Next action: researcher review of whether to stop this Phase 2B cycle or
separately authorize a bounded, provenance-preserving infrastructure recovery
protocol. This document does not authorize more model/API calls.
