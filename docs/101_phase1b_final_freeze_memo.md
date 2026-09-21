# Phase 1B Final Freeze Memo

Date: 2026-09-21

Branch: `exp/minimal-exploratory-memory-validation`
Baseline under test: `f6bc77207557af68e913e5c037d5371651274dfb`

## Decision

**`READY_FOR_SCALE_WITH_KNOWN_LIMITATIONS`**

This is a code/artifact correctness decision, not a method-effectiveness
claim. No model/API call, six-task rerun, twelve-task rerun, or fresh task was
performed in this cycle.

## Core regression: saved Closure Task 3

Source artifact:

```text
artifacts/exploratory_memory_mvp/
  phase1b-prescale-closure-20260921-0745fcd/tasks/03-b74ce78e8759/
```

The saved A output contains:

```text
evidence_role = CONTRADICTING
comparison_assessment = PARTIALLY_RESOLVED
operation = REFINE
target_memory_ids = []
```

The final field is an invalid Established Memory binding, but the first two
semantic judgments are valid for the actual consumed-H probe. The regression
now produces the following behavior without changing the saved artifact:

```text
epistemic assessment       ACCEPTED
current evidence binding   ACCEPTED mechanically
REFINE([]) update          REJECTED: needs one target
Established Memory change  NONE from this update
factual evidence           PRESERVED
H lifecycle                CONSUMED and preserved
```

The runner-owned evidence binding is checked against the consumed H's
comparison ID and the saved `evidence_id`; the model does not provide either
reference.

## Valid-update regressions

| saved case | assessment | update | result |
|---|---|---|---|
| Closure Task 1, `tasks/01-fe5a5bac7cf1` | `IRRELEVANT / REMAINS_OPEN` without H | none | accepted; no unsupported comparison update |
| Closure Task 2, `tasks/02-f13421bdbb8a` | `SUPPORTING / PARTIALLY_RESOLVED` | `ADD` | accepted; Established Memory entry materializes with runner lineage |
| Closure Task 3, `tasks/03-b74ce78e8759` | `CONTRADICTING / PARTIALLY_RESOLVED` | malformed `REFINE([])` | assessment accepted; update rejected only |
| Closure Task 4, `tasks/04-6ce98e7a5d4c` | `SUPPORTING / PARTIALLY_RESOLVED` | legal `REFINE` | accepted; target version/lineage remains materialized |

An additional invalid-assessment fixture confirms that an invalid
`evidence_role` is rejected and cannot be materialized. Fake-transport
execution confirms that every new runner output contains
`epistemic_validation.json`, `updates_validation.json`, and
`materialization.json` while preserving the existing fact-commit artifacts.

## Invariants checked

- A semantic assessment is independent of update target binding.
- Invalid update targets are never guessed, clamped, or converted to ADD.
- Valid ADD/REFINE/SPECIALIZE/MERGE semantics remain mechanical and
  lineage-preserving.
- The actual evidence ID and comparison ID remain runner-owned.
- Factual evidence and consumed-H lifecycle are not rolled back by offline
  validation/materialization failure.
- Existing B→C source-answer firewall, C future-facing entity isolation,
  temporal facts, compact reconciliation context, and no-unsupported-RESOLVED
  invariants remain covered by the regression suite.
- Task 5's entity-bearing Functional Contract remains fail-closed.
- Task 6's possible near-duplicate comparison identity remains unchanged and
  is not patched here.

## Verification

Commands run without network/model access:

```text
python -m unittest tests.test_phase1b_longitudinal -v
ruff check experiments/exploratory_memory_mvp/phase1b_contract.py \
  experiments/exploratory_memory_mvp/run_phase1b_longitudinal.py \
  experiments/exploratory_memory_mvp/prompts_phase1b.py \
  tests/test_phase1b_longitudinal.py
python -m compileall -q experiments/exploratory_memory_mvp \
  tests/test_phase1b_longitudinal.py
git diff --check
```

The focused suite passed 19/19 tests. The Phase 1 regression suite passed
87/87 tests, and the MVP regression suite passed 21/21 tests. Ruff,
compileall, and `git diff --check` also passed.

## Known limitations carried into scale

1. A B Functional Contract can still fail closed when the contract itself
   contains a source entity; this is an intentional safety boundary.
2. Comparison identity can produce a possible near-duplicate rather than
   merging two semantically similar open comparisons; this is a scale-quality
   signal, not patched in this cycle.
3. Retrieval quality has not been validated at scale.
4. The controlled ALFWorld search abstraction is not a complete autonomous
   actor and its acquisition endpoint must not be confused with full task
   completion.

These limitations do not represent a new method-superiority result. The next
cycle may proceed directly to a fresh 40–60 task longitudinal scale-aware
experiment with these signals preregistered for measurement; it must not
reuse the old development stream as confirmatory evidence.
