# Phase 1E Cross-Model Final Review

Status: development/validation review only. The complete task population and
state lineage validate, but this is one reused 64-task stream per model, not a
fresh confirmatory comparison or a paper-level estimate.

## 1. Review scope and evidence boundary

This review combines:

* the immutable Max task artifacts 1–61 and validated M61 state;
* the separately committed Max continuation for tasks 62–64;
* the deterministic 1–64 reconstruction in
  `artifacts/exploratory_memory_mvp/phase1e-max-combined-reconstruction-v1-20260922`;
* frozen Flash results in docs/104–105 and docs/110–111;
* the frozen Phase 1E H2 review rubric, including C-visible history only.

No hidden placement, PDDL answer, oracle route, or model rationale is used.
No model/API call or rerun occurred during final analysis. No Phase 1C/1D
runtime, Phase 1E prompt, model setting, memory state, or task population was
changed.

## 2. Cross-model outcome

The Flash and Max runs independently built their own G/T state from canonical
K*. They share the registered 64-task development population, but neither
model inherited the other model's evolved memory.

| Model | N=32 G/T/Delta | N=33–64 G/T/Delta | N=64 G/T/Delta |
|---|---:|---:|---:|
| Flash | 446 / 405 / **-41** | 351 / 300 / **-51** | 797 / 705 / **-92** |
| Max | 349 / 378 / **+29** | 289 / 307 / **+18** | 638 / 685 / **+47** |

The behavioral direction does not cross-model replicate. Max's G arm used
159 fewer acquisition actions than Flash G over the reused stream; Max T used
20 fewer than Flash T. Those between-model totals are descriptive and do not
isolate capability as a cause. Within Max, T was 47 actions higher than G
(7.4% of G's 638 actions); per-task median delta was zero, with 26 T-lower,
18 equal, and 20 T-higher pairs. The net is adverse but not uniformly so.

### CM1 — mechanism replication

Max did build and use independent exploratory state: 35 retained H, 22 actual
activations/consumptions, 22 Exploration History records, and 21 comparisons.
History-bearing cases reached C and C created H proposals. This supports a
qualitative mechanism replication: the Max implementation did not collapse
to no-H behavior.

### CM2 — lifecycle and H2

Using the frozen rubric, the 35 history-visible parsed CREATE cases were
classified as 27 materially different, 5 justified retests, and 3 redundant
near-duplicates. Two parsed NONE cases were one reasonable suppression and one
possible over-suppression. Two additional C outputs with visible history
failed parsing and are unclassified. This does not show systematic H2
duplication, but the denominator of NONE decisions is very small.

At N=64, Max had 8 active H versus Flash's 3; Max had created more H (35 vs
26) despite a slightly smaller archive (22 vs 23). Max had 21 comparisons,
all `OPEN`, while Flash had 21 comparisons (17 `PARTIALLY_RESOLVED`, 4
`OPEN`). The final three Max tasks created three H, activated one, and raised
active backlog from 6 to 8. These are scale/lifecycle concerns, not evidence
that the state is corrupted. They indicate Max's memory evolution and
comparison-state interpretation differ from Flash.

### CM3 — behavioral value

The Max H-active subset was slightly favorable to T over tasks 1–64
(`Delta=-7` across 22 tasks; 4 lower / 11 equal / 7 higher), and favorable in
the 33–64 suffix (`-15` across 11 tasks). The no-H subset was unfavorable
(`+54` over 42 tasks; 22 lower / 7 equal / 13 higher), including `+33` in the
suffix. T's frozen no-H path does not fall back to G's generic probe, so this
is a real protocol tradeoff and not evidence that an active H caused those
extra actions. Under the preregistered full-arm comparison, however, Max T
did not improve cumulative acquisition cost.

The Flash advantage was concentrated in H-active episodes (Flash H-active
`Delta=-99` combined; no-H `+7`). Max's corresponding split was H-active
`-7`, no-H `+54`. This reversal and concentration make a
capability-/policy-dependent value hypothesis plausible, but the present
single-stream design cannot establish it.

### CM4 — model-dependent failure structure

| Mechanism/failure | Flash, N=1–64 | Max, N=1–64 | Interpretation |
|---|---:|---:|---|
| B→C source-entity firewall rejection | 7 total: 1 in Phase 1C + 6 in Phase 1D | 21 | More frequent with Max; fail-closed behavior, not data leakage into C |
| B response/schema failure | 0 reported in frozen Flash results | 2 (tasks 33 and 41, invalid JSON) | Model-dependent semantic-interface failure |
| C response/schema failure | 2 in Phase 1D (plus no additional Phase 1C failure reported) | 2 (tasks 10 and 54, invalid JSON) | Similar count, different exact episodes |
| Parsed C CREATE / NONE | 26 / 28 | 37 / 2 | Max strongly favored CREATE among its observed valid C outputs |
| H total / active at N=64 | 26 / 3 | 35 / 8 | More creation and larger active backlog with Max |
| Comparison statuses at N=64 | 17 partial / 4 open | 21 open | Epistemic evolution differed substantially |

Max's 21 B→C rejections occurred in tasks 1–61; the resumed tasks 62–64
passed the handoff. The firewall retained its fail-closed behavior. These
rejections reduce C opportunity and are a model-dependent quality limitation,
not a correctness violation. Two H/comparison reconciliation outputs were
also rejected by validation (tasks 5 and 49); neither corrupted the stored
state. The two B invalid-JSON episodes were tasks 33 and 41. The two C
invalid-JSON episodes were tasks 10 and 54. All 64 T A epistemic/materialized
stages report accepted; no task-level rollback or acquisition/pairing failure
was found.

## 3. Cost and context interpretation

Max recorded 529 model calls versus 578 Flash calls across Phase 1C+1D.
Recorded Max token sums were 4,752,181 input, 321,664 cached input, and
79,851 output tokens, with one task-19 history-retrieval usage record
unavailable. The 334 Max records containing cost estimates point at Flash
pricing metadata despite resolved `qwen3.8-max`; they are not a reliable Max
price total. Exact Max billing remains unknown. Flash had its own partial
known-cost records; cost comparisons should therefore not be inferred from
the recorded subtotals.

Max context grew substantially between the first and second halves: median
serialized C input rose from 12,088 to 78,288 bytes, and median reconciliation
input from 14,848 to 42,853 bytes. These are JSON byte lengths, not token
counts. No context-limit failure was established, but the C-context growth is
a relevant scale pressure for a fresh formal protocol.

## 4. Correctness assessment

The combined 64-pair reconstruction is valid as a segmented continuation:

* original indices 1–61 are represented once; resumed indices 62–64 are
  represented once;
* all pairs match the frozen registry and public initial fingerprint;
* G/T resume initial states equal original M61, and M61→M64 lineage validates;
* all saved requests are Max-only; 529 call IDs are unique, with zero retry
  evidence;
* all 64 targets were acquired in both arms;
* no source runtime, registry, task, prompt, method, or model was changed.

The initial storage failure remains in the historical record, but it does not
invalidate the scientifically completed 1–64 stream after the authorized
continuation. Provenance must still be described as segmented.

## 5. Final interpretation

**`MECHANISM_REPLICATED_BEHAVIOR_NEGATIVE`** is the best-supported Phase 1E
development description.

Max independently formed and activated history-derived H and accumulated
exploration history, so the mechanism replicated qualitatively. Yet the full
Max T arm used 47 more acquisition actions than its paired G arm. The adverse
aggregate is concentrated in no-H episodes, while H-active episodes are
slightly favorable; this is a meaningful tradeoff signal, not proof that H
itself harms behavior. In contrast, Flash showed a favorable T−G direction.

The cross-model validation objective is therefore **not satisfied as a
cross-model behavioral-value replication**. The data support review of a
possible capability-dependent hypothesis—history-derived targeting may help
a weaker generic search policy more than a stronger one, while T's no-H
abstention from generic exploration can carry a cost. This remains a
hypothesis, not a causal conclusion.

## 6. Research recommendation

Return to researcher review of the intended scientific claim and comparison
framing before any formal evaluation. Do not automatically tune the method,
change the no-H behavior, start another development stream, promote an actor,
freeze Method/Evaluation v1, or launch fresh confirmatory experiments. The
next step requires explicit researcher authorization.
