# Behavior-first isolated-K0 corpus results

2026-09-13. This records the BF-0–BF-2 work authorized by [`docs/31_behavior_first_candidate_mining_plan.md`](31_behavior_first_candidate_mining_plan.md). It does not run scripted B, target K0 explorability, a learned-memory branch, Minimal-B, or a closed-loop diagnosis.

## Corpus outcome

BF-0 deterministically discovered 732 released AppWorld tasks and selected 30 tasks from 30 distinct scenario families (seed `20260913`). Nineteen tasks were excluded by the registered instruction-level forced-comparison/optimality gate; 713 remained eligible. The selected IDs, in run order, were:

```text
22cc237_1 4ec8de5_3 2c544f9_2 bcb9696_3 d37c235_1 59bcfc8_2
530b157_3 e201314_3 fddb6b6_2 5e27cd7_1 a3ba388_3 66b7899_3
a5b0084_3 6f4b9a5_2 906f2c7_2 8d42650_3 ffe6d5e_1 3aa1a22_1
83a7951_1 f099b4c_3 a7179fa_1 0d8a4ee_1 988af8e_1 986aa4e_1
6104387_2 3c13f5a_2 b0a8eae_1 92fe421_2 b05f69a_1 fb05fed_2
```

The real ACE online/no-GT run cleanly stopped after 23 tasks, before the remaining seven were started. The 23rd task exceeded the registered per-task guard; no retry or silent relaxation occurred. This is a guard stop, not a claim about the seven unrun tasks.

| Measure | Result |
|---|---:|
| Task artifacts retained | 23 |
| Native completed / `budget_exceeded` | 22 / 1 |
| Evaluator success / false / unavailable | 18 / 4 / 1 |
| Exact K0 pre-Generator reset checks | 23 / 23 passed |
| Model calls | 462 |
| Input / cached input / output tokens | 6,316,447 / 5,138,560 / 962,846 |
| Accounted USD cost | 1.53961266 |
| Public API responses / failed responses | 660 / 6 |

Each task used native ACE Generator → AppWorld → Reflector → Curator. Every task received the same immutable K0 checkpoint; no `K_i` was supplied to task `i+1`. The corpus index and raw artifacts are ignored local evidence under `artifacts/ace-appworld-behavior-k0-v1/run-01/`; they were never supplied to the adaptive loop as research-side context.

## DeltaK and behavioral observations

Twenty of 23 cards had a non-empty real playbook delta (46 changed/added entries total). Nineteen tasks contained at least one entry in a strategy, common-mistake, verification, or template section (37 such entries). This is evidence that ACE can persist reusable-looking material here, not evidence that any entry has cross-task behavioral authority.

The conservative card extractor labeled every observed route `mixed` and every identity-resolution trace `multi_hop`. Thus this corpus did not provide a real source trajectory with the registered direct/filtered source-C signature needed by the initial deterministic transfer screen. Cards retain raw evidence paths and never reconstruct a route from a benchmark reference solution.

## BF-2 candidate queue and gate decision

The offline `DeltaK_i × T_j` screen considered the 23 cards and returned **0 candidate tuples**. Its rejection counts were:

| Reason | Ordered pairs |
|---|---:|
| Same task (`i == j`) | 23 |
| Source DeltaK empty | 66 |
| Source strategy not reusable under the direct/filtered gate | 352 |
| Source task not successful | 88 |

This is not proof that no cheaper B exists in AppWorld. It establishes that the isolated corpus did not yield a credible tuple with actual source C, relevant real DeltaK, and a concrete semantics-preserving B route. A heuristic based merely on shared apps or a shorter source trace was not promoted because it cannot establish target entity scope or task semantics.

The final queue is empty; no scripted-B validation or K0 explorability is justified. This meets the registered AppWorld kill signal for candidate generation: stop AppWorld **for Problem B** rather than add another detector. AppWorld/ACE remains useful A-side evidence, but renewed B work needs a separate scientific decision, not a retry of the frozen reserve pool or this corpus.
