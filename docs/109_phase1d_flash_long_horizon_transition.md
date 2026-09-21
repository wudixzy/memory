# Phase 1D Flash Long-Horizon Validation — Immutable Transition

Date: 2026-09-21
Branch: `exp/minimal-exploratory-memory-validation`
Protocol: `phase1d-long-horizon-v1`
Status: no-model transition; execution is authorized only after this
transition commit is pushed

## 1. Scientific boundary

Phase 1D is a development/validation continuation of the single Phase 1C
Flash stream. It tests whether the observed history-conditioned mechanism and
descriptive action signal survive from global task index 32 to 64. It is not a
paper-level superiority result, a fresh actor gate, or a confirmatory
evaluation.

No Phase 1D model/API call has been made before the commit containing this
transition document. No Max call is authorized.

## 2. Frozen Phase 1C source endpoint

Source execution commit:

```text
60c24741195d1aee2086989c331933480073c0fe
```

Source runtime:

```text
artifacts/exploratory_memory_mvp/phase1c-scale-pilot-v1-20260921-60c2474
```

The continuation loads, validates and does not re-execute:

```text
G_memory_snapshots/M_032.json
T_state_snapshots/M_032.json
```

The source summary digests are:

```text
G: ba87aae11c164c3342f1670f23e4106eabe3808661ea93aa577610d797f07c7e:4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945
T: 136464ab32cefddfd47ccd58ce31a8d5b7af56811f69097c1a2f9b4eb73dc8b3:430cd8fcc4d8353f50fc339fdcd1ac044824797510135d81b36ffdbf27b662a2
```

The Phase 1D runner recomputes both digests, checks the Phase 1C run commit,
checks that source `paired_results.jsonl` contains exactly global indices 1–32,
and fails closed before any model call on mismatch.

## 3. Frozen public-only suffix registry

Registry:

```text
experiments/exploratory_memory_mvp/cases/phase1d_long_horizon_registry.json
```

The complete pinned `valid_unseen` public census contains 135 records. To
avoid allowing repeated ALFWorld reset variance to change a pre-registered
eligibility decision, Phase 1D reuses the complete public census already
collected in the immutable Phase 1C registry. This reuses only public task
metadata, instruction, reset observation and ordered public affordances; it
does not reuse Phase 1C outcomes. The new suffix selection is applied only
after adding the Phase 1C selected IDs to the protected exclusion inventory.

| item | frozen value |
|---|---:|
| public census | 135 |
| eligible universe | 56 |
| eligible simple / clean / cool / heat | 13 / 20 / 11 / 12 |
| selected suffix | 32 |
| selected simple / clean / cool / heat | 8 / 8 / 8 / 8 |
| global indices | 33–64 |
| requested seed | 42 |
| Phase 1C registry SHA-256 | `0975718ce5de471e70bc29412291558ac50db5b2a40dfa958f6fe115184119f9` |
| Phase 1C selected-ID SHA-256 | `0cf944c9e2ebe229a95337f720fa88effff0ce94a2d9d146dff0a07022ab7672` |
| Phase 1D registry SHA-256 | `c58a93a098a2f0e03e9a453a1519f880c2ed066e02ca02aa2483a928fd74dfc7` |
| Phase 1D selected-ID SHA-256 | `76404ac40fbffabfe20301a191a866109b5d0039d3998bbc64fd4a79f6f8e7ff` |

The selected order is exactly:

```text
33 simple, 34 clean, 35 cool, 36 heat, repeated through 64
```

The protected inventory includes the committed historical Source,
Calibration, Target, Phase 1B development and B1-R reservations, plus all 32
Phase 1C selected tasks. The registry contains the full public census,
eligible universe, exclusion reasons, replay specifications, public initial
fingerprints and a disjointness proof. Hidden PDDL placement, oracle routes,
arm outcomes and expected winners are not used by selection.

## 4. Frozen protocol and model

Both G and T continue from their own Phase 1C endpoint state. No state is
shared between arms. The implementation is versioned as
`run_phase1d_long_horizon.py`; it delegates episode semantics to the frozen
Phase 1C runner functions without changing their prompts, schemas, archive,
retrieval, reconciliation, selector, executor, continuation or fact-commit
behavior.

```text
selector / B / C / A / retrieval / reconciliation: qwen3.8-flash
provider: existing DashScope-compatible direct transport
thinking: false
temperature: 0
maximum candidate probes: 2
```

The only new task execution is 32 G/T pairs for indices 33–64. Each pair
must pass the existing actual replay/public fingerprint proof before the first
model call for that pair. No retry, task replacement, prompt change, model
change or result-driven stopping is permitted.

## 5. No-model verification before execution

Focused no-model tests cover:

* exact Phase 1C M32 state digest restoration and source commit binding;
* global continuation indices 33–64 and no task 1–32 rerun in prepare mode;
* complete 32-task suffix, 8 tasks per family, deterministic interleave and
  stable registry rebuild;
* disjointness from Phase 1C and protected historical sets;
* Flash-only model configuration and the unchanged two-probe/mechanical
  protocol contract;
* prepare-only mode not initializing model transport.

The prepared runtime must be created under a new ignored Phase 1D artifact
directory. The original Phase 1C runtime remains byte-for-byte untouched.

The exact Git commit containing this document is the immutable transition
commit. Only after it is pushed may the single authorized 64-episode Phase 1D
Flash suffix execute.
