# Exploratory-memory MVP carrier fit and case curation

Date: 2026-09-16
Branch: `exp/minimal-exploratory-memory-validation`
Selected carrier: **ALFWorld TextWorld**, from the pinned AutoManual checkout.
## Selection memo

ALFWorld TextWorld supplies the needed small controlled loop. A task can be
reset to the same seed, an explicit action route can be replayed, and the
public boundary exposes observations, admissible text actions, reward, `done`,
and `won`. The route is a local realization of the task: replacing a search
segment leaves the take/place subgoal and downstream destination unchanged.
The environment therefore supplies direct comparative evidence through success
and executed-step count, and the same task/seed can be replayed for E0/E1.

The pinned setup was fetched with:

```text
python scripts/setup/automanual.py --fetch
python scripts/setup/automanual.py --apply-patches
conda run -n memory-automanual python scripts/smoke/automanual_worker.py --execute --seed 42
```

The smoke run used the real TextWorld environment and did not request or
serialize an expert plan. The MVP adapter similarly requests only public text
state and admissible commands. The upstream checkout and downloaded benchmark
data are runtime prerequisites and remain ignored rather than being committed.

AppWorld was not selected. The previous final sanity probe recorded that the
available setup did not provide the required real checkout/data path; that
failure is documented in `docs/36_appworld_final_sanity_probe_results.md`.
This milestone does not restart the large AppWorld mining pipeline. No
WebShop/ScienceWorld adapter was added because ALFWorld already met the
lightweight admission test with several directly inspectable cases.

The requested model override for this experiment is DashScope
`qwen3.7-flash`, with thinking disabled, temperature zero, and the API key read
from the repository-adjacent `.env` file. No DeepSeek call is part of this
experiment.

## Directly inspected routes

The following routes were selected by reading the task observations and real
admissible actions, then replayed from a fresh seed-42 state. `A` is the
established listed-order route; `B` is a source-directed local replacement.
Both routes succeeded in the inspection replays.

| task | A steps | B steps | local comparison |
|---|---:|---:|---|
| AlarmClock → Desk, 314 | 17 | 5 | listed-order search vs. direct source |
| Pencil → Shelf, 310 | 14 | 5 | listed-order search vs. direct source |
| Plate → Dresser, 218 | 17 | 5 | listed-order search vs. direct source |
| SoapBottle → Cabinet, 414 | 30 | 6 | listed-order search vs. direct source |
| SoapBottle → Cabinet, 417 | 11 | 6 | listed-order search vs. direct source |
| Book → Sofa, 229 | 5 | 5 | initial `look` vs. redundant `inventory` |
| Laptop → Desk, 306 | 5 | 5 | initial `look` vs. redundant `inventory` |
| Candle → Toilet, 427 | 6 | 6 | initial `look` vs. redundant `inventory` |

The first five are P cases: the public established memory supports the
listed-order realization, while the source-directed realization is withheld
from B/C and is retained only in evaluator notes. The next three are N2
controls: although `inventory` is legal, the initial observation already
exposes the relevant navigation targets, so resolving that comparison would
not change future policy. Three N1 rows reuse three P task states but add
explicit matched evidence to established memory, making the corresponding
comparison already resolved.

The full fixture has 11 cases (5 P, 3 N1, 3 N2) in
`experiments/exploratory_memory_mvp/cases/cases.json`. Its `evaluator_notes`
are evaluator-side only. B/C/actor inputs are generated separately and are
audited for hidden-field leakage before model calls.

## Limits of the fit

This carrier demonstrates local action substitution and measured execution
cost, not general strategy discovery. The curated routes are intentionally
small and hand-inspected. The result should be interpreted as a mechanism
probe, not as an ALFWorld benchmark result or evidence that the full persistent
memory method works.
