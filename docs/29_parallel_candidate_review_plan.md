# Parallel agent review plan for AppWorld reserve families

2026-09-13. This document supersedes any remaining requirement for a human to manually inspect the 26 Stage-A reserve families before further filtering. The scientific gates from `docs/26_strategy_lockin_experiment_plan.md` remain unchanged; only the review mechanism changes.

**Status:** completed on 2026-09-13. All 26 reserve families were packetized
and passed through the independent reviewer protocol. The final automated
result was 17 rejects, 9 review-quality reserves and 0 promoted families; see
[`docs/30_parallel_candidate_review_results.md`](30_parallel_candidate_review_results.md).
Because no family was promoted, scripted-B and K₀ explorability were not run.

## Decision

Do **not** manually review reserve families one by one.

Use an agentic pipeline:

```text
Stage-A census
    -> 26 reserve families
    -> Claude Code returns the family/task IDs and prepares reproducible review packets
    -> Codex writes a lightweight parallel DeepSeek-Flash reviewer + fixed prompt/schema
    -> all reserve packets are reviewed concurrently
    -> automatic evidence validation + aggregation/adjudication
    -> top 3-5 families only
    -> scripted-B environment validation
    -> K0 explorability only after scripted B succeeds
```

The purpose of this review is candidate triage, not scientific proof. Reviewer output cannot establish that B succeeds, is cheaper, is discoverable, or is caused by memory.

## 1. Review pool

Default pool: **all reserve families produced by the reproducible census**, currently 26 in `docs/28_appworld_family_census.md`.

Claude Code should regenerate the census if needed, then return to Codex a machine-readable list containing at least:

- family ID;
- proposed source task ID(s);
- proposed target task ID(s);
- current census admission reason;
- paths to the candidate record and supporting benchmark files.

Do not pre-filter to the current top-10 merely to reduce reviewer cost. Reviewing 20-30 families is cheap enough and avoids inheriting ranking errors from the offline heuristics.

## 2. Review packet

Codex should generate one self-contained **research-side packet per family**. The packet may contain privileged benchmark information because it is for candidate selection only, but it must never enter ACE Generator/Reflector/Curator.

Each packet should include only evidence needed to judge the strategy hypothesis:

- family/source/target IDs;
- source and target instructions;
- normalized state/setup differences relevant to the candidate;
- current reference strategy C and its target call count;
- current candidate-B hypotheses from the census, including rejected/weak routes;
- concise reference-solution snippets around the relevant API calls;
- relevant API documentation excerpts/schemas;
- comparison/exploration gate output;
- K0 static-playbook overlap summary;
- provenance paths/hashes so claims can be checked locally.

Avoid dumping whole databases or giant solution files into each prompt. The packet builder should extract bounded evidence snippets and preserve exact source paths/line or symbol references.

## 3. Parallel DeepSeek reviewers

Codex, not Claude Code, should own the lightweight reviewer harness and prompt so that the implementation worker does not also become the final scientific judge.

Use the same low-cost DeepSeek Flash family currently configured for project agents. For Anthropic-compatible calls, the project model name is `deepseek-flash[1m]`. Authentication must come from local `.env` `DEEPSEEK_KEY`; never print or persist the key.

Recommended first pass:

- **2 independent reviews per family**;
- review all ~26 reserves;
- concurrency around 8-12 workers unless provider limits require less;
- deterministic/low-temperature settings where supported;
- no hidden chain-of-thought requirement;
- save only final structured reviewer outputs and usage/cost telemetry.

This is roughly 52 small semantic-review calls, which is preferable to sequential human inspection.

## 4. Reviewer question

The reviewer is not asked `Is this a good paper example?` and is not asked to find a positive result.

It must answer:

> Given the provided source/target benchmark evidence, is there a concrete strategy B that plausibly removes unnecessary public API/tool work on the target while preserving the task semantics, without relying on information unavailable to the agent? If yes, specify exactly which calls/steps C performs, which B replaces or removes, why source C is natural, why target C can remain successful, and what must still be verified by execution.

The reviewer must aggressively reject shortcuts that change scope, omit required entities, use evaluator-only information, rely on target answers, or merely exploit data-volume differences.

## 5. Required JSON output

Each independent review should return strict JSON similar to:

```json
{
  "family": "...",
  "source_task": "...",
  "target_task": "...",
  "verdict": "promote_to_scripted_validation|reserve|reject",
  "confidence": 0.0,
  "candidate_B": {
    "summary": "...",
    "public_api_route": ["..."],
    "replaces_C_steps": ["..."],
    "estimated_min_saving_calls": 0,
    "saving_basis": "..."
  },
  "source_C_natural": {
    "verdict": true,
    "reason": "..."
  },
  "target_C_still_successful": {
    "status": "supported|unknown|false",
    "reason": "..."
  },
  "target_forces_comparison": false,
  "scope_equivalence": "supported|uncertain|refuted",
  "privileged_information_needed_by_B": false,
  "evidence": [
    {"source": "packet-path-or-symbol", "claim": "..."}
  ],
  "execution_checks_required": ["..."],
  "rejection_reasons": []
}
```

Do not allow free-form-only output to drive admission decisions.

## 6. Automatic evidence checks

Codex should validate reviewer outputs before aggregation. At minimum:

- family/source/target IDs must match the packet;
- every named API must exist in the supplied API surface or packet;
- evidence references must point to supplied packet evidence;
- reviewers may not mark B success or measured cost as established before execution;
- a route needing evaluator/setup/ground-truth-only values is rejected;
- a route that changes entity scope or task semantics is rejected or sent to adjudication;
- `estimated_min_saving_calls` is a hypothesis/bound, never reported as measured `cost(B)`.

Malformed or unsupported reviews are re-run once with an error-focused prompt; persistent failures are marked unusable, not silently repaired by hand.

## 7. Aggregation and disagreement

For each family, compare the two independent reviews.

### Promote automatically to the next diagnostic queue when

- both reviewers choose `promote_to_scripted_validation`;
- both identify semantically equivalent B routes;
- neither requires privileged information;
- both accept source-C naturalness and target semantic equivalence;
- the predicted saving is plausibly meaningful under the registered >=3 calls or >=25% criterion.

### Reject automatically when

- both reject for the same substantive reason; or
- deterministic evidence validation refutes the proposed route.

### Adjudicate when

- reviewers disagree on verdict;
- they propose materially different B routes;
- scope equivalence is uncertain;
- only one reviewer finds a meaningful saving.

Adjudication should be a **third independent DeepSeek Flash review** that sees the original packet plus the two structured conclusions, but not hidden reasoning. Codex then applies deterministic schema/evidence checks to the adjudicator result.

No human semantic inspection is required in this stage.

## 8. Output of the parallel review stage

Track:

- complete review pool IDs;
- two reviewer outputs per family;
- adjudication output where used;
- per-family final automated verdict;
- reason codes;
- usage/token/cost totals;
- top candidate queue.

The tracked summary should contain the final top **3-5 families at most**, while raw reviewer artifacts may remain ignored if large.

This stage still does **not** authorize K0 explorability runs.

## 9. Scripted-B validation after review

For each promoted family, Claude Code may implement a research-side AppWorld diagnostic route B, and Codex reviews/runs it.

The diagnostic must establish with the real benchmark environment/evaluator:

```text
success(B) = true
cost(B) < cost(C)
```

using public environment/API calls only. Prefer the existing registered threshold of >=3 calls saved or >=25% reduction.

This validates **existence** of a better successful route, not model discoverability.

Stop a candidate if B fails, changes semantics, requires privileged information, or the measured saving is trivial.

## 10. K0 explorability comes last

Only families with a benchmark-executed successful cheaper B move to the paid/model stage.

Then run the ACE official-initial-playbook condition K0 and ask whether the same backbone can discover B or another successful route B' with lower measured cost than C.

Do not attribute non-discovery to persistent memory unless `P(BetterAlternative | K0) > 0` has empirical support.

## 11. Implementation ownership

### Claude Code

- regenerate census and return all reserve family/task IDs;
- help build bounded per-family evidence packets;
- implement scripted-B diagnostics only for families promoted after parallel review;
- run local/offline tests;
- do not commit/push by default.

### Codex

- write/own the parallel reviewer script and fixed reviewer prompt/schema;
- launch DeepSeek Flash reviews concurrently;
- validate structured outputs against evidence;
- aggregate/adjudicate reviews;
- review any scripted-B diagnostic implementation and run/tests;
- synchronize docs/status;
- commit and push accepted work.

This division is deliberate: CC prepares/implements; Codex controls the independent reviewer ensemble and final evidence gate.

## 12. Stop rule for AppWorld

After all reserve families have been agent-reviewed, run scripted-B validation for at most the top 3-5.

If none yields a real successful B with meaningful measured savings, stop AppWorld for B instead of writing more candidate detectors.

If successful B routes exist but none is discoverable under K0, stop AppWorld + current backbone for this B experiment before attempting learned-memory branches.
