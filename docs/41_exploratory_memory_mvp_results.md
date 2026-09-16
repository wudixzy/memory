# Minimal exploratory-memory MVP results

Date: 2026-09-16
Branch: `exp/minimal-exploratory-memory-validation`
Carrier: ALFWorld TextWorld
Model: DashScope `qwen3.7-flash`; thinking disabled; temperature `0`
Experiment artifact root: `artifacts/exploratory_memory_mvp/experiment_a-qwen-20260916/`

## Result

Experiment A ran B once per curated case over 11 cases. B returned valid JSON
for every call and produced this confusion table:

| case type | cases | expected `OPEN`/`NONE` | observed `OPEN`/`NONE` | interpretation |
|---|---:|---:|---:|---|
| P | 5 | 5 / 0 | 0 / 5 | all positive cases missed |
| N1 | 3 | 0 / 3 | 0 / 3 | all already-resolved controls rejected |
| N2 | 3 | 0 / 3 | 0 / 3 | all non-policy-relevant controls rejected |

Thus B was perfectly conservative on these negative controls but had zero
recall on P cases. Since no P case survived B, C was skipped for all 11 cases
and no E0/E1 online pair was run. This is a negative Experiment-A result, not
evidence that the full persistent-memory method works.

The complete evaluator-side case definitions, public B inputs, raw visible
prompts/responses, parsed responses, model-event logs, carrier traces, and
per-call usage reports are present under the artifact root. Runtime artifacts
are ignored by Git; the tracked case fixture and reports contain their
provenance without committing benchmark/runtime data or credentials.

The reproducible full-run command was:

```bash
PYTHONPATH=src conda run --no-capture-output -n memory-automanual \
  python experiments/exploratory_memory_mvp/run_experiment_a.py \
  --allow-network --env-file /home/coolboy/projects/memory/.env \
  --output artifacts/exploratory_memory_mvp/experiment_a-qwen-20260916
```

The reviewed table can be regenerated with:

```bash
PYTHONPATH=src python experiments/exploratory_memory_mvp/review_cases.py \
  --experiment-a artifacts/exploratory_memory_mvp/experiment_a-qwen-20260916 \
  --output /tmp/exploratory-memory-review.md
```

## Telemetry

The 11 B calls used 58,888 input tokens, 73 output tokens, and 4,736 cached
input tokens. The Qwen pricing estimate recorded by the runner was **CNY
0.01107824**; free allowances were not deducted. No DeepSeek call was made.

The runner stores the raw visible assistant message and provider-reported
usage, while filtering `reasoning_content` and not depending on hidden
chain-of-thought. The DashScope model/endpoint and pricing references are
encoded in `experiments/exploratory_memory_mvp/model.py`.

## Failure localization

* **Carrier/case:** The carrier fit remains positive at the mechanical level.
  Five P routes and three negative controls were directly inspected. The
  established routes succeeded in real TextWorld; the P route pairs have
  local source-directed alternatives with measured step differences. However,
  the alternative is intentionally withheld from B, so the public case may
  not expose enough evidence for a conservative model to infer the intended
  comparison. This is an uncertainty about case presentation, not a license
  to add a semantic rule.
* **B diagnosis:** This is the observed bottleneck: `0/5` P cases were opened,
  while all six N1/N2 controls returned the expected `NONE`. The current
  prompt/model combination does not formulate an open comparison from one
  established successful route plus the current public state.
* **C synthesis:** Not tested. There were zero C model calls because the
  protocol correctly gates C on `B=OPEN`.
* **Grounding/execution:** Not tested for generated C output. The deterministic
  action validator and the real carrier replay are covered offline/at curation,
  but no generated exploratory memory reached execution.
* **Online exploratory-memory authority:** Not tested. E0/E1 and optional E2
  were correctly withheld after the Experiment-A stop condition.

## Uncertainties and next decision

This was one deterministic (`temperature=0`) run on 11 hand-curated cases, so
it does not establish model variance or generality. The next useful research
step would be to revise the case/prompt presentation under semantic review and
rerun this small gate; it should not add a handcrafted OPEN classifier or jump
to a large benchmark sweep. Under the current protocol, the MVP stops before
online testing.
