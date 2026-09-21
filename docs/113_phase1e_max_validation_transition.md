# Phase 1E qwen3.8-max Cross-Model Validation — Immutable Transition

Status: no-model transition. The Max run is authorized only after the commit
containing this document has been pushed. This transition itself makes no
model/API call.

## Scientific boundary

Phase 1E is an independent cross-model development validation, not fresh
confirmatory evaluation and not a paper-level superiority result. It changes
only the model backbone from the frozen Phase 1C/1D Flash configuration to
`qwen3.8-max`. No Flash-evolved memory or semantic output is loaded.

## Frozen population identity

The committed combined manifest is:

```text
experiments/exploratory_memory_mvp/cases/phase1e_cross_model_registry.json
```

It is an exact public registry copy, not a new sample:

| source | registry SHA-256 | selected-ID SHA-256 | global indices |
|---|---|---|---:|
| Phase 1C | `0975718ce5de471e70bc29412291558ac50db5b2a40dfa958f6fe115184119f9` | `0cf944c9e2ebe229a95337f720fa88effff0ce94a2d9d146dff0a07022ab7672` | 1–32 |
| Phase 1D | `c58a93a098a2f0e03e9a453a1519f880c2ed066e02ca02aa2483a928fd74dfc7` | `76404ac40fbffabfe20301a191a866109b5d0039d3998bbc64fd4a79f6f8e7ff` | 33–64 |

Combined registry SHA-256:

```text
a46ecec068060ccc264dcc994b74e088776b98e3b9f2c31982bfb83a3e5b1a7f
```

Combined selected-ID SHA-256:

```text
69cf0bc660df2283aa55b668aece2cecca39da73d76e31e886968da003bc3fe7
```

The population has exactly 64 tasks, 16 from each admitted family, with the
same interleave and exact replay/public fingerprints as the source registries.
No task selection used Flash outcomes, hidden placement, PDDL, oracle routes or
expected winners.

## Frozen Max initialization and protocol

Both Max arms start independently from:

```text
K_established = canonical K*
active H = empty
Exploration History = empty
comparison ledger = empty
```

The canonical K* digest is:

```text
331728a3e001c8a3bc7e992d7605ee428501c34d0d5d8fed75a19abd98314447
```

The fresh G/T arm state digest is identical at initialization:

```text
01c1987f5b8fb06e29f8b10e8f81569e0dd47b65aa001e744f2a5bb4a8a493e4:4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945
```

Every model-facing role is frozen to:

```text
provider = dashscope-compatible
model = qwen3.8-max
thinking = false
temperature = 0
```

The candidate budget remains two, and the selector, retrieval, B/C/A,
history, reconciliation, executor, continuation, acquisition endpoint,
pairing and fact-commit semantics are delegated to the frozen Phase 1C
implementation.

## No-model verification

Before this transition:

* 122 focused Phase 1E/Phase 1D/Phase 1C/Phase 1B/Phase 1A/MVP tests passed;
* prepare-only mode returned `model_calls=0` and did not create task episodes;
* Ruff passed;
* compile checks passed;
* `git diff --check` passed;
* the combined manifest rebuild was deterministic;
* no Max or Flash model transport was initialized for Phase 1E.

The exact commit containing this document is the immutable transition commit.
Only after it is pushed may the single 64-task Max G/T stream execute. No
retry, task replacement, prompt/method change, Flash fallback, third arm or
result-driven stopping is permitted.
