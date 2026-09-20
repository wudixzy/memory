# Phase 1A Controlled Targeting v2 Results

Date: 2026-09-20  
Branch: `exp/minimal-exploratory-memory-validation`  
Protocol: `phase1a-controlled-targeting-v2`

This is the first controlled C2/C3 targeting run. It is a narrow receptacle-search
measurement, not a result for the full persistent-memory method.

Scientific unit: 20 unique target tasks. The 40 actor episodes are the two paired
arms for those 20 units, not `n = 40`.

## Frozen setup and artifacts

Transition commit: `8103a79cca8a9cbf8912d7a7526d4d73700da32a`  
Pre-target scope-review commit: `4f01e89`  
Selector: DashScope-compatible `qwen3.8-max`, `thinking=false`, `temperature=0`,
strict dynamic zero-based `candidate_index` schema.  
Offline B/C: DashScope-compatible `qwen3.8-flash`, `thinking=false`,
`temperature=0`, one call per source stage.

Committed public target registry:

```text
experiments/exploratory_memory_mvp/cases/phase1_registered_targets.json
registry_sha256 = 0e43d9846ad96249ef1b421b02585a0fff1190e76eb6156b64da6c805588d
```

The exact runtime roots are:

```text
source:
artifacts/exploratory_memory_mvp/phase1a-controlled-targeting-v2-source-20260920-8103a79

targets:
artifacts/exploratory_memory_mvp/phase1a-controlled-targeting-v2-targets-20260920-4f01e89
```

The first target launch attempt failed before `make_run_directory` because a shell
variable was not passed into the nested shell, leaving `--output` as `.`. It made no
model call and no episode artifact. The same frozen command was then launched with
the explicit output path above; that run completed normally.

## Source 5 -> B/C -> H

All five frozen source histories were created by the deterministic public canonical
K* incumbent executor. All five history executions completed. B and C were called
once per source; no source was replaced because of its result.

| source | B | C | source-H result | target applicability review |
|---|---|---|---|---|
| `AlarmClock -> Desk-314` | `OPEN` | `CREATE` | `phase1a-source-h-00` frozen | eligible |
| `Pencil -> Shelf-310` | `OPEN` | `CREATE` | `phase1a-source-h-01` frozen | eligible |
| `Plate -> Dresser-218` | `OPEN` | `CREATE` | `phase1a-source-h-02` frozen | eligible |
| `SoapBottle -> Cabinet-414` | `OPEN` | `CREATE` | `phase1a-source-h-03` frozen | eligible |
| `SoapBottle -> Cabinet-417` | `OPEN` | `CREATE` | `phase1a-source-h-04` frozen | rejected before targets |

There were no B=`NONE` or C=`NONE` cases in this source run, and no source
infrastructure failures. The fifth H was not silently assigned: its future-facing
scope explicitly says “liquid or hygiene product”, which is narrower than the
frozen family contract. It remains in the complete source-H manifest as preserved
source evidence, but was excluded from target assignment because no narrower
public-only contract was pre-frozen.

Scope review:

```text
source-H manifest:       3298cddbba85d80e55d1d42c22dcf10e1563af734f821303fcd0628a9e9b3849
scope review:            57426c10c6a52d5a5a88014e19fb2b8a941543a88036c9737f38b4ee2cd5f8b7
target-eligible H:       4
derived H manifest:      69742e9e733fcbe509954c5431dd2e4c5a78e06f30577ee3504ac12f9a7a97e4
eligible IDs:            h-00, h-01, h-02, h-03
rejected ID:             h-04
```

The full values are in the runtime JSON artifacts and the committed
`experiments/exploratory_memory_mvp/cases/phase1a_h_scope_review.json`.

## Outcome-blind H assignment

Assignment used the frozen stable-hash salt
`phase1a-receptacle-search-h-assignment-v1` over the four target-eligible H IDs.
No target outcome or hidden placement was read during assignment.

```text
assignment_digest = c2717b28bab8a9c816ff99411e3af210bdf7b1f47f874d32896c60e256daf43f
```

Assignment counts:

| H | target count |
|---|---:|
| `phase1a-source-h-00` | 3 |
| `phase1a-source-h-01` | 5 |
| `phase1a-source-h-02` | 5 |
| `phase1a-source-h-03` | 7 |

The uneven counts and the fact that all Hs express closely related open-surface-first
variants mean source clustering must be considered when interpreting this first pass.

## C2/C3 target results

`A` means target acquired within the two-candidate-probe budget. `—` means not
acquired within the budget. The winner is acquisition-first, then fewer candidate
probes; when both arms fail or tie on probes it is `TIE`.

| target (registry order) | H | C2 | C3 | paired |
|---|---|---|---|---|
| `simple/SprayBottle -> Toilet-426` | h-02 | A/1 | A/2 | C2 |
| `clean/Apple -> Fridge-27` | h-02 | — | — | TIE |
| `cool/Pot -> Shelf-1` | h-00 | A/1 | A/1 | TIE |
| `heat/Egg -> GarbageCan-2` | h-03 | A/2 | — | C2 |
| `cool/Lettuce -> DiningTable-21` | h-00 | — | — | TIE |
| `heat/Egg -> SideTable-21` | h-01 | A/1 | A/2 | C2 |
| `clean/Ladle -> DiningTable-27` | h-03 | A/2 | A/2 | TIE |
| `cool/Bread -> CounterTop-7` | h-03 | — | — | TIE |
| `simple/Book -> Sofa-229` | h-01 | A/1 | A/1 | TIE |
| `heat/Mug -> Cabinet-20` | h-02 | — | — | TIE |
| `clean/DishSponge -> Toilet-427` | h-03 | A/1 | — | C2 |
| `clean/DishSponge -> Cabinet-414` | h-01 | — | — | TIE |
| `clean/Apple -> Microwave-14` | h-02 | — | — | TIE |
| `heat/Apple -> GarbageCan-12` | h-03 | — | A/1 | C3 |
| `heat/Potato -> GarbageCan-14` | h-03 | — | A/2 | C3 |
| `cool/Bread -> CounterTop-15` | h-03 | — | — | TIE |
| `cool/WineBottle -> Cabinet-17` | h-03 | — | — | TIE |
| `cool/Mug -> CoffeeMachine-30` | h-01 | — | A/1 | C3 |
| `cool/Cup -> Microwave-30` | h-01 | — | — | TIE |
| `heat/Plate -> CounterTop-28` | h-01 | — | — | TIE |

Mechanical aggregate:

| metric | C2 | C3 |
|---|---:|---:|
| acquired within budget | 7/20 | 8/20 |
| not acquired within budget | 13/20 | 12/20 |
| selector calls | 35 | 36 |
| environment actions in probes | 57 | 48 |
| schema failures | 0 | 0 |

Paired acquisition tuples:

```text
C2 only: 2
C3 only: 3
both acquired: 5
both not acquired: 10
```

Paired endpoint comparison:

```text
C2 win: 4
TIE:    13
C3 win: 3
abstention/runner failure: 0
```

Thus C3 had one more raw acquisition than C2, but did not have a positive paired
win/loss signal: C2 won one more paired unit. Ten target units produced no acquisition
for either arm under the pre-registered budget.

## Source clustering view

| assigned H | n | C2 acquired | C3 acquired | C2 wins | C3 wins | ties |
|---|---:|---:|---:|---:|---:|---:|
| h-00 | 3 | 1 | 1 | 0 | 0 | 3 |
| h-01 | 5 | 0 | 1 | 0 | 1 | 4 |
| h-02 | 5 | 3 | 3 | 2 | 0 | 3 |
| h-03 | 7 | 3 | 3 | 2 | 2 | 3 |

This is not evidence that any individual source H is generally better. It shows that
the small first pass is dependent on the deterministic source-H assignment mix.

## Leakage, pairing, and artifact checks

The actual run mechanically recorded:

* 20/20 C2/C3 pairings valid before selector calls;
* registry and public initial fingerprint checks passed for every target episode;
* all 40 episode summaries present;
* no selector schema failures and no runner-level target failures;
* first-step C2/C3 selector inputs identical after removing the intended H field for
  20/20 target units;
* no `source_task_id`, source-history, source-grounding, oracle, evaluator, or
  pairing fields found in target selector inputs;
* exact selected candidate sequences, public observations, environment actions, and
  usage artifacts retained under each target directory.

## Token and cost telemetry

These are local estimated DashScope accounting values, not provider-invoiced costs;
provider-reported USD was unavailable. The project telemetry also labels the pricing
source conservatively, so these values should be treated as budget estimates.

| stage | model | calls | input tokens | output tokens | estimated CNY |
|---|---|---:|---:|---:|---:|
| source B | `qwen3.8-flash` | 5 | 33,728 | 1,777 | 0.0317803 |
| source C | `qwen3.8-flash` | 5 | 16,832 | 3,342 | 0.0224890 |
| target C2 selector | `qwen3.8-max` | 35 | 42,371 | 258 | 0.0345934 |
| target C3 selector | `qwen3.8-max` | 36 | 43,721 | 276 | 0.0357220 |
| **total** | — | **81** | **136,652** | **5,653** | **0.1245847** |

The run measured assembled selector prompt usage but did not claim exact C2/C3 token
parity. The extra C3 call is a consequence of the observed C3 sequences, not a retry.

## Interpretation and negative evidence

The controlled measurement instrument worked mechanically: it isolated candidate
selection, enforced the same two-probe budget and executor, paired actual episodes, and
preserved public evidence. It does not support a claim that history-derived targeting
improves the target endpoint in this first pass.

The observed pattern is mixed and weak:

* C3 acquired 8 versus C2's 7, but C2 won 4 paired units versus C3's 3.
* C3 often selected open-surface candidates, but ten tasks remained unresolved for
  both arms within the fixed budget.
* C2 produced two exclusive acquisitions and two lower-probe wins on cases where both
  acquired; C3 produced three exclusive acquisitions.
* The target pool contains four task families, but the probe endpoint intentionally
  stops at acquisition. These results are not full-task success or downstream
  transformation evidence.
* H-04 was preserved as a source result but excluded from assignment for a public
  scope mismatch; no target was selected or relabelled using that rejection.

No C1, repetition, B1-R, B2/B3, second model, target resampling, or post-outcome H/C2
change was performed. The old autonomous actor route remains historical negative
evidence.

## Recommendation

Do not expand this into repetitions or a larger matrix yet. First review the H
hypothesis/quality and the controlled two-probe endpoint, especially the ten
both-fail units and the source-cluster dependence. The current result is useful
mechanism evidence that the C2/C3 comparison can be executed and audited, but it is
not evidence of general exploratory-memory superiority or a positive targeting-value
claim.
