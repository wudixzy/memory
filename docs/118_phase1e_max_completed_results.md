# Phase 1E qwen3.8-max Cross-Model Validation — Completed Results

Status: **complete segmented development stream**. The initial runtime was
interrupted by a host temporary-storage failure at task 62. After a separately
committed infrastructure-only transition, the registered stream continued
from the original M61 states through tasks 62–64. This is not a physically
uninterrupted run, a fresh confirmatory evaluation, or a paper-level
superiority result.

## 1. Execution identity and integrity

| Item | Frozen/observed value |
|---|---|
| Branch | `exp/minimal-exploratory-memory-validation` |
| Original Phase 1E transition | `0ada22175818aa8aa6de6f152d91cb9e0ed0032d` |
| Resume transition | `30712c9c0d10c36734cc164532a4f983ec19683b` |
| Combined registry SHA-256 | `a46ecec068060ccc264dcc994b74e088776b98e3b9f2c31982bfb83a3e5b1a7f` |
| Selected-task-ID SHA-256 | `69cf0bc660df2283aa55b668aece2cecca39da73d76e31e886968da003bc3fe7` |
| G M61 state digest | `aded8deab94573908b26d5d0359890702a5575619e4ea7bcf570d5dadffbcfcd:4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945` |
| T M61 state digest | `ab8f31135e15a3df85336cc7da35a873a439725b4fdd7296396ad543f7aec4c3:ea68b1fb8453b313a3f0a492dd04615147baccdbdfe61dd6f0521705500c159a` |
| Final G M64 state digest | `2eab27139bfd38d5f6d09ef6cbae1915eefc439d991387ce9f10451f27c76c61:4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945` |
| Final T M64 state digest | `5b0b43d64fb07bad2bf86fd0e6727b6f204ebbe99dab351affc92d350ea260dd:b583db34a04adf7f00c40e0c42abf23e9de676d37bd4ff0a25444affb03fd971` |
| Combined results JSONL file SHA-256 | `3d79d2ab81d66a10534312a6cefef372a28f979b7ecef972e882b104dc3b218c` |
| Combined summary JSON file SHA-256 | `06eb6e3523bf37f81964dde23d1ba93be5a5e110c0fa4215608d48ed4bf90661` |
| Original runtime, tasks 1–61 | `artifacts/exploratory_memory_mvp/phase1e-cross-model-max-v1-20260922-0ada221` |
| Resume runtime, tasks 62–64 | `artifacts/exploratory_memory_mvp/phase1e-max-resume-v1-20260922-authorized-continuation` |
| Deterministic combined reconstruction | `artifacts/exploratory_memory_mvp/phase1e-max-combined-reconstruction-v1-20260922` |
| Combined status | `validated_complete_segmented_stream`; 64 pairs / 128 episodes |
| Model-call audit | 529 unique Max call IDs; duplicate/retry IDs = 0 |
| Pairing and registry checks | 64/64 valid; exact registered task/order/replay identity |
| Target acquisition | 64/64 in each arm; 128/128 episodes |
| Phase 1E Max configuration | `qwen3.8-max`, `thinking=false`, `temperature=0` for all roles |
| Flash calls in Phase 1E | 0 |
| Task retries/replacements | 0 / 0 |

The original task-62 carrier failure remains preserved in the original runtime.
It occurred before episode creation. The no-model preflight reproduced the
registered public reset fingerprints for tasks 62–64 using the dedicated
temporary directory recorded in `docs/117_phase1e_max_resume_transition.md`;
it executed zero environment actions and made zero model calls. The resume
loaded the exact G/T M61 state digests from the original run. The combined
validator then verified M61 equality, M62→M63→M64 continuity for both arms,
the Max-only model audit, and exact 1–64 registry coverage. The original
Phase 1C/1D/1E runtime artifacts were not rewritten.

The 128 summaries report `won=false` because the frozen endpoint is exact
target acquisition; downstream clean/cool/heat/place completion is not run.
That is not an acquisition failure.

## 2. Resumed task outcomes

| Index | Task family / target | G actions | T actions | T−G | T activated H? | Acquired in both? |
|---:|---|---:|---:|---:|---|---|
| 62 | clean / Cloth → Cabinet | 6 | 5 | -1 | Yes | Yes |
| 63 | cool / Tomato → Microwave | 4 | 11 | +7 | No | Yes |
| 64 | heat / Cup → Cabinet | 10 | 7 | -3 | No | Yes |

These are the only six new arm episodes. They ran in task order 62→63→64,
with the exact original task IDs, seeds, replay specifications, and public
initial fingerprints. No prior scientific/model call was retried.

## 3. Cumulative acquisition-action results

The primary measure is environment actions to exact target acquisition.
`Delta = T − G`; positive values mean more actions in T. All 64 pairs acquired
the target in both arms.

| Global N | G actions | T actions | Delta T−G | T lower / equal / higher |
|---:|---:|---:|---:|---:|
| 8 | 111 | 109 | -2 | 3 / 4 / 1 |
| 16 | 191 | 207 | +16 | 4 / 7 / 5 |
| 24 | 299 | 315 | +16 | 10 / 7 / 7 |
| 32 | 349 | 378 | +29 | 11 / 11 / 10 |
| 40 | 411 | 458 | +47 | 12 / 13 / 15 |
| 48 | 496 | 536 | +40 | 17 / 16 / 15 |
| 56 | 581 | 621 | +40 | 21 / 17 / 18 |
| 64 | 638 | 685 | **+47** | 26 / 18 / 20 |

| Segment | Tasks | G actions | T actions | Delta T−G |
|---|---:|---:|---:|---:|
| 1–32 | 32 | 349 | 378 | +29 |
| 33–64 | 32 | 289 | 307 | +18 |
| 1–64 | 64 | 638 | 685 | **+47** |

### H-active and no-H decomposition

H-active means T actually activated an H. It is descriptive post-hoc
stratification, not randomized attribution.

| Segment | Subset | n | G actions | T actions | Delta | T lower / equal / higher | Mean paired delta | Median |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1–32 | H-active | 11 | 65 | 73 | +8 | 0 / 7 / 4 | +0.73 | 0 |
| 1–32 | no-H | 21 | 284 | 305 | +21 | 11 / 4 / 6 | +1.00 | -1 |
| 33–64 | H-active | 11 | 81 | 66 | -15 | 4 / 4 / 3 | -1.36 | 0 |
| 33–64 | no-H | 21 | 208 | 241 | +33 | 11 / 3 / 7 | +1.57 | -1 |
| 1–64 | H-active | 22 | 146 | 139 | -7 | 4 / 11 / 7 | -0.32 | 0 |
| 1–64 | no-H | 42 | 492 | 546 | +54 | 22 / 7 / 13 | +1.29 | -1 |

The net positive T−G difference is concentrated in no-H episodes; H-active
episodes are slightly favorable to T in the full stream. This split does not
remove the protocol distinction that G always receives generic exploration
while T with no active H uses canonical continuation without a generic-probe
fallback.

### Family totals, tasks 1–64

| Family | n | G actions | T actions | Delta T−G |
|---|---:|---:|---:|---:|
| `pick_and_place_simple` | 16 | 192 | 203 | +11 |
| `pick_clean_then_place_in_recep` | 16 | 120 | 131 | +11 |
| `pick_cool_then_place_in_recep` | 16 | 195 | 197 | +2 |
| `pick_heat_then_place_in_recep` | 16 | 131 | 154 | +23 |

Largest T-lower deltas were task 55 Lettuce/CounterTop (`-12`), task 50
Mug/CoffeeMachine (`-6`), and task 5 SoapBottle/Toilet (`-4`). Largest
T-higher deltas were task 53 Watch/Safe (`+14`), tasks 16 Apple/GarbageCan,
20 Potato/GarbageCan, and 28 Mug/Cabinet (each `+9`), followed by task 34
Egg/Microwave (`+8`). These are descriptive outliers, not causal effects.

## 4. Mechanism and lifecycle trajectory

Counts below are T-arm cumulative state snapshots. `Created` is the number of
new persisted H IDs since the preceding listed checkpoint; activation is the
number of actual H activations in that interval. Comparisons at N=64 were all
`OPEN`.

| N | H total | Active | Consumed | Superseded | New H in interval | H activations in interval | Archive | Comparisons |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 8 | 6 | 2 | 2 | 2 | 6 | 2 | 2 | 2 |
| 16 | 9 | 1 | 6 | 2 | 3 | 4 | 6 | 3 |
| 24 | 15 | 4 | 7 | 4 | 6 | 1 | 7 | 6 |
| 32 | 21 | 5 | 11 | 5 | 6 | 4 | 11 | 9 |
| 40 | 23 | 4 | 14 | 5 | 2 | 3 | 14 | 11 |
| 48 | 27 | 4 | 18 | 5 | 4 | 4 | 18 | 14 |
| 56 | 30 | 4 | 21 | 5 | 3 | 3 | 21 | 17 |
| 61 | 32 | 6 | 21 | 5 | 2 | 0 | 21 | 19 |
| 64 | 35 | 8 | 22 | 5 | 3 | 1 | 22 | 21 |

At N=64, 35 H had been retained, 22 activated/consumed, 5 superseded, and 8
remained active. The last three tasks added three H but activated one; the
active backlog therefore rose from 6 to 8. The comparison ledger grew from
19 to 21. This is visible lifecycle pressure, not by itself a correctness
failure.

Cumulative T-stage outcomes at N=64 were: B `OPEN=62`, B invalid/failed=2;
C `CREATE=37`, `NONE=2`, B→C handoff rejected=21, C parse/schema failure=2,
and skipped before C=2. Accepted/parsed reconciliation outputs recorded 21
`ADD`, 14 `REFINE_EXISTING`, and 4 `NO_NEW_H`; two additional reconciliation
outputs were rejected by validation. All 21 final ledger comparisons were
`OPEN`.

## 5. H2 audit population and resumed cases

The exact frozen H2 labels and full tasks 1–61 case review are in
`docs/116_phase1e_max_prefix_diagnostic.md`. For the resumed suffix, the same
rubric was applied only to histories actually present in each C input, without
using later acquisition outcomes:

| Index | C-visible nearest prior exploration | C proposal versus visible history | Label | Reconciliation |
|---:|---|---|---|---|
| 62 | `exploration-h-f9e349c7471f657e`: cloth/towelholder-first | destination-type closed-storage-first is a different search realization and tests a different first candidate class | `MATERIALLY_DIFFERENT` | `REFINE_EXISTING` |
| 63 | `exploration-h-3ef3b43e4c09a8cb`: cooling-appliance-first | open-horizontal-surface-first is a different search direction from the visible appliance/cold-storage priorities | `MATERIALLY_DIFFERENT` | `ADD` |
| 64 | `exploration-h-f98f1efb76abeeb5`: mug/open-surface-first | same broad realization for cup rather than mug; C explicitly framed a target-type transfer test | `JUSTIFIED_RETEST` | `ADD` |

Full N=1–64 H2 counts:

| C=CREATE label | Count |
|---|---:|
| `MATERIALLY_DIFFERENT` | 27 |
| `JUSTIFIED_RETEST` | 5 |
| `REDUNDANT_NEAR_DUPLICATE` | 3 |
| `UNCLEAR` | 0 |

| C=NONE label | Count |
|---|---:|
| `REASONABLE_SUPPRESSION` | 1 |
| `POSSIBLE_OVER_SUPPRESSION` | 1 |
| `UNCLEAR` | 0 |

The audit population was 39 C cases with nonempty history actually visible to
C: 35 parsed CREATE, 2 parsed NONE, and 2 C errors with no decision to label.
Other cases were excluded because C was not reached (23), the archive was
empty (1), or records were offered to retrieval but none were visible to C
(1). One of those no-visible-history cases returned CREATE, but it is not
counted as evidence that C repeated or differed from shown history.

## 6. Model and cost telemetry

The 529 saved call records break down by role/phase as follows:

| Role | Calls |
|---|---:|
| A | 128 |
| B | 64 |
| G candidate selector | 114 |
| T candidate selector | 39 |
| active-H retrieval | 62 |
| exploration-history retrieval | 40 |
| C | 41 |
| H/comparison reconciliation | 41 |
| **Total** | **529** |

Recorded token totals: input `4,752,181`, cached input `321,664`, output
`79,851`. One call (task 19 T history retrieval) has unavailable usage; the
token sums therefore exclude that call's unavailable token fields. There are
334 calls with recorded cost estimates, but their pricing-source metadata
points to a Qwen 3.8 Flash pricing page while the resolved model is
`qwen3.8-max`. The recorded estimate subtotal is not treated as a valid Max
charge. Actual total Max cost is unavailable; no missing price was imputed.

Environment-action totals are the acquisition-action totals above (G=638,
T=685). They are not combined with model cost.

## 7. Context growth

Serialized input sizes below are JSON bytes, not tokenizer-derived token
counts. The comparison is descriptive; no context optimization was performed.

| T input | Tasks 1–32: n / median / max bytes | Tasks 33–64: n / median / max bytes |
|---|---:|---:|
| History-retrieval input | 24 / 6,493 / 10,340 | 16 / 20,442 / 22,528 |
| C input | 25 / 12,088 / 25,120 | 16 / 78,288 / 105,093 |
| Reconciliation input | 25 / 14,848 / 30,404 | 16 / 42,853 / 50,213 |

Context grew materially, especially for C. No context-limit or malformed-output
event was attributed to these byte sizes, but actual tokenizer measurements
are not available here.

## 8. Artifact provenance

The deterministic combined artifacts are read-only reconstructions stored
outside both source runtimes:

```text
artifacts/exploratory_memory_mvp/phase1e-max-combined-reconstruction-v1-20260922/combined_paired_results.jsonl
artifacts/exploratory_memory_mvp/phase1e-max-combined-reconstruction-v1-20260922/combined_stream_summary.json
```

The original task-62 failure and all original task artifacts remain unchanged.
Resume tasks 62–64, state-before/state-after snapshots, usage and errors remain
under the separate resume runtime. The execution must be cited as two
segments: original 1–61, then resumed 62–64 from the validated M61 endpoint.
