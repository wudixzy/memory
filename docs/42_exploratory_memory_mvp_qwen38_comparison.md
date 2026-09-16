# Exploratory-memory MVP: Qwen3.8 and prompt follow-up

Date: 2026-09-16
Branch: `exp/minimal-exploratory-memory-validation`
Carrier: ALFWorld TextWorld
Cases: 11 hand-curated cases (5 P, 3 N1, 3 N2)

This report combines the first `qwen3.7-flash` run recorded in
`docs/41_exploratory_memory_mvp_results.md` with two follow-up runs using
DashScope `qwen3.8-flash`. It evaluates only Experiment A (B diagnosis and,
if B opens a case, C synthesis). It does not claim that the full
persistent-memory method works.

## Prompt audit and intervention

The original B prompt had a real asymmetry. It strongly instructed B to return
`NONE` when no meaningful comparison was evident and not to invent an
alternative, but it did not explicitly state that a successful historical
realization A establishes feasibility only; it does not establish that A is
better than every other local realization. It also left local segmentation,
functional-contract extraction, discriminative evidence, and future-policy
relevance as one implicit judgment.

The follow-up therefore made a small semantic prompt intervention, not a
handcrafted classifier:

* explicitly distinguish “A is feasible” from “A is preferred to all local
  alternatives”;
* state that an alternative missing from memory is not evidence that the
  comparison is resolved;
* ask B to inspect local segment, functional contract, discriminability, and
  policy relevance in that order;
* make the `NONE`/`OPEN` contract and warrant requirement explicit; and
* send the optimized B prompt as one user message containing the instructions
  and input JSON. C was also clarified to require a precondition/postcondition
  matching B's contract and to emit only a local substitution, although C was
  not reached in these runs.

The evaluator label, expected decision, oracle action list, and curation notes
remain evaluator-only. The public input hash is identical across all three
arms; the old-prompt hashes are identical between the Qwen3.7 and Qwen3.8
baseline arms, while all 11 optimized-prompt hashes differ as intended. The
runtime prompt audit found zero hidden-field leaks in each arm.

## Experiment-A comparison

`B valid` means a parseable response satisfying the strict B JSON contract.
The counts in the decision columns are counts of cases with that decision.

| model | B prompt | B valid | P: `OPEN/NONE` | N1: `OPEN/NONE` | N2: `OPEN/NONE` | C calls |
|---|---|---:|---:|---:|---:|---:|
| `qwen3.7-flash` | original | 11/11 | 0/5 | 0/3 | 0/3 | 0 |
| `qwen3.8-flash` | original | 11/11 | 0/5 | 0/3 | 0/3 | 0 |
| `qwen3.8-flash` | optimized | 11/11 | 0/5 | 0/3 | 0/3 | 0 |

Every raw visible B response was `{"decision":"NONE"}` (with insignificant
whitespace variation in the first run). The Qwen3.8 baseline and optimized
runs each recorded `proxy_disabled: true` for all 11 calls. Both were launched
with proxy variables removed, `NO_PROXY=*`, and the transport also uses an
empty `urllib` proxy handler.

The result is conservative but scientifically negative for the intended gate:

* all six negative controls were rejected as expected;
* all five P cases were missed;
* C was correctly skipped because no B result was `OPEN`; and
* E0/E1 (and the optional E2 diagnostic) were not run because the Experiment-A
  stop condition was reached.

The per-case outcome is uniform: all five P cases, all three N1 cases, and all
three N2 cases returned `NONE` in each arm. The route evidence and case-level
semantic rationale are in `docs/40_exploratory_memory_mvp_carrier_fit.md` and
the evaluator-isolated fixture at
`experiments/exploratory_memory_mvp/cases/cases.json`.

## Telemetry

| run | input tokens | output tokens | cached input | estimated cost |
|---|---:|---:|---:|---:|
| Qwen3.7 original | 58,888 | 73 | 4,736 | CNY 0.01107824 |
| Qwen3.8 original | 58,888 | 55 | 0 | CNY 0.04725890 |
| Qwen3.8 optimized | 61,638 | 55 | 0 | CNY 0.04945890 |

Qwen3.8 estimates use the Beijing uncached rates recorded by the runner and
are not directly comparable to the historical Qwen3.7 estimate because the
models have different published prices and the first run included cached
input. The runner does not deduct free allowances. References: [Qwen3.8-Flash
model information](https://help.aliyun.com/en/model-studio/qwen3-8-flash),
[DashScope model pricing](https://help.aliyun.com/en/model-studio/model-pricing),
and [Qwen context-cache guidance](https://help.aliyun.com/en/model-studio/context-cache).

All Qwen3.8 calls explicitly set `temperature: 0`,
`enable_thinking: false`, and `preserve_thinking: false`; only visible assistant
content is persisted. This avoids making the result depend on hidden reasoning
content. The current runner and raw per-case artifacts are under:

```text
artifacts/exploratory_memory_mvp/experiment_a-qwen38-baseline-20260916/
artifacts/exploratory_memory_mvp/experiment_a-qwen38-optimized-20260916/
```

## Combined interpretation

The evidence does not support the simple conclusion that the previous failure
was only a Qwen3.7 capability problem.

1. Qwen3.7 and Qwen3.8 received the same public inputs and the same original
   prompt, and produced the same `0/5` P recall with perfect negative-control
   rejection. There is no observed model-version improvement on this gate.
2. The Qwen3.8 optimized prompt directly repaired the identified epistemic
   asymmetry, but still produced exactly the same decisions. The prompt had a
   genuine defect, but that defect was not the sole bottleneck in this case
   presentation.
3. The strongest current localization is the B-facing problem formulation:
   B must infer a policy-relevant alternative from one successful route while
   the alternative and its comparative outcome are intentionally withheld.
   The carrier can execute the withheld local route, but the public evidence
   may be too underdetermined for a conservative B to name it without
   hallucinating an alternative.

Thus the current result is best described as **B/case-interface failure, with
model capability and prompt sensitivity not fully ruled out**, rather than as
an isolated model-capability diagnosis. The one deterministic run per arm is
also too small to estimate variance.

## Open interface-design question for review

B's actual public input contains the current observation and state-specific
`admissible_actions`, plus the established memory and historical trajectory. It
does not contain the full `capabilities.json` view; that view is deliberately
reserved for C. Historical action strings show what A executed, but they do
not establish that an unobserved alternative exists, has legal arguments, or
can be executed while preserving the downstream state.

The current B prompt nevertheless asks whether the supplied evidence supports
another realization and whether it can produce discriminative evidence. This
creates a role-boundary ambiguity: B may be asked to infer an executable
alternative without the information needed to verify it. A `NONE` response
may therefore reflect epistemic caution caused by the interface, rather than
only failure to recognize the semantic comparison. The Qwen3.7/Qwen3.8
comparison cannot isolate these explanations.

No implementation decision is made here. Before the next run, the design
should choose explicitly among: (1) B diagnoses only an abstract open
comparison and C verifies grounding/executability; (2) B also receives a
public capability view that excludes evaluator labels and oracle outcomes; or
(3) a carrier whose relevant alternatives are naturally visible in public
state/action affordances. This is a design question for review, not a reason
to add an `OPEN` heuristic.

## Failure localization

* **Carrier/case problem:** ALFWorld TextWorld passes the mechanical carrier
  fit. Established routes succeed, local source-directed routes were directly
  replayed during curation, step differences are observable, and matched
  reset/replay is available. The remaining concern is that the intended P
  comparison is not explicitly represented in B's public input; its alternative
  is evaluator-side by design.
* **B diagnosis problem:** confirmed bottleneck. B is valid and selective on
  N1/N2, but has zero recall on P in all three arms.
* **C synthesis problem:** untested; no C call was permitted after the stop
  condition.
* **Grounding/execution problem:** generated C grounding and execution are
  untested. The mechanical validator and real carrier replays only establish
  offline support for the curated action traces.
* **Online exploratory-memory authority:** untested. No E0/E1 pair was run,
  so there is no evidence about whether an actor would follow a generated
  exploratory memory.

## Next decision

Do not start a large benchmark or add an `OPEN` heuristic. The next useful
small experiment should improve the semantically reviewed public
representation of the local segment and its available realizations, while
still withholding evaluator labels and oracle outcomes, then rerun the same
11-case gate across more than one deterministic replicate. If several P cases
survive, proceed to the prescribed E0/E1 paired online test. Until then, the
MVP should be reported as a negative Experiment-A result.

## Verification

The MVP contract tests pass (`8` tests), Ruff passes for the MVP code and
tests, and the MVP modules compile successfully. The full repository test
command was also run, but it retains two known AppWorld-data errors: the
pinned `third_party/ace-appworld/experiments/playbooks/appworld_initial_playbook.txt`
and the target task input state are absent. This is the same setup failure
documented in `docs/36_appworld_final_sanity_probe_results.md`; it is unrelated
to the ALFWorld/Qwen3.8 MVP.

## Reproduction commands

Both Qwen3.8 runs used the same cases, carrier, seed, credentials file, and
network policy; only the prompt arm changed:

```bash
env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY \
  -u http_proxy -u https_proxy -u all_proxy \
  NO_PROXY='*' no_proxy='*' PYTHONPATH=src \
  conda run --no-capture-output -n memory-automanual \
  python experiments/exploratory_memory_mvp/run_experiment_a.py \
  --allow-network --env-file /home/coolboy/projects/memory/.env \
  --prompt-variant baseline \
  --output artifacts/exploratory_memory_mvp/experiment_a-qwen38-baseline-20260916

env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY \
  -u http_proxy -u https_proxy -u all_proxy \
  NO_PROXY='*' no_proxy='*' PYTHONPATH=src \
  conda run --no-capture-output -n memory-automanual \
  python experiments/exploratory_memory_mvp/run_experiment_a.py \
  --allow-network --env-file /home/coolboy/projects/memory/.env \
  --prompt-variant optimized \
  --output artifacts/exploratory_memory_mvp/experiment_a-qwen38-optimized-20260916
```
