# First infrastructure deliverable

Current schema 1.2 supports ordered append-only updater intervals. The historical
single-interval limitation below is superseded by
[multi-updater compatibility and diagnostic integration](08_multi_updater_diagnostic.md).

Latest additive embedding telemetry, direct-only transports and smoke finalization
are documented in [the embedding deliverable](06_embedding_wiring.md).

Historical first-deliverable report. Subsequent source fetch, text-only installation,
real environment smoke and JSON boundary verification are recorded in
[the source audit](04_automanual_source_audit.md) and
[the preparation report](05_automanual_reproducibility.md). Statements below about
unattempted installation and unresolved public model documentation describe the
earlier review, not the current preparation state. Full memory-loop integration,
strict evaluator isolation and real API compatibility remain unverified.

This implements observability and an offline synthetic fixture only. It does not
implement AutoManual's memory mechanism, validate H1–H4, or complete Phase 0/1.
The infrastructure uses Python >=3.10 with no runtime dependencies. The upstream
installation uses its own Python 3.9.16 environment; integrating these environments
is a later compatibility gate, not something verified by the fake adapter.

## Offline commands

From the repository root:

Create the environment once; reuse it if already present with the recorded versions.

```bash
conda env create -f configs/environment-infra-linux-64.yml
conda run -n memory-infra env PYTHONPATH=src python -m unittest discover -s tests -v
conda run -n memory-infra python scripts/smoke/offline.py
conda run -n memory-infra python scripts/setup/automanual.py
conda run -n memory-infra bash scripts/setup/install_automanual.sh
```

Environment creation downloads packages; the four execution commands are offline.
The smoke runs one synthetic task with two synthetic
call records. It neither imports an upstream benchmark nor loads `.env`. It writes
to a unique ignored `artifacts/<run_id>/fake_fixture/0_fixture/` directory. Existing
output directories are rejected. Every manifest has `scientific_evidence: false`
and `execution_kind: infrastructure_test`; call records say `provider: fake` and
`requested_model: fixture`. The manifest's Phase-1 model fields express the target
configuration, not a claim that the fixture called that model. Its reported cost
is exactly zero; token estimates are synthetic accounting test data.

Optional development checks (the runtime does not depend on Ruff):

```bash
conda run -n memory-infra ruff check src tests scripts
conda run -n memory-infra ruff format --check src tests scripts
conda run -n memory-infra python -m compileall -q src tests scripts
bash -n scripts/setup/install_automanual.sh
git diff --check
```

## Design and artifact contract

- `schemas.py`: flattened, round-trippable manifest; explicit availability
  envelopes; immutable JSON snapshots preserving raw memory plus independent
  normalized metadata. Raw text is retained exactly inside the JSON envelope.
  SHA-256 hashes canonical raw JSON; metadata does not alter raw memory identity.
  Diffs contain exact before/after raw values, metadata, hashes and a textual diff.
- `pipeline.py`: narrow adapter protocol and incremental artifact sink. All files
  in the validation protocol are created, including `trajectory.json`; unobserved
  stages contain `status: unavailable` with a reason, including JSONL streams.
  JSON writes replace temporary files atomically and streams flush each event.
  Normal errors and budget stops finalize partial artifacts and return a status.
  Interrupts finalize with `status: interrupted` and re-raise `KeyboardInterrupt`
  without the original exception body, so a sequential caller cannot accidentally
  continue as if it received an ordinary task result. Abrupt
  process death may leave a `running` manifest and a temporary file, but previous
  writes survive. I/O failures cannot guarantee artifact persistence.
- `branching.py`: `NoIntervention`, `MaskMemoryItem`, `NoMemory`. The mapping masker
  is explicitly format-specific; it is used only by the fake adapter. Future
  upstream adapters must implement their native format without losing information.
  `memory_diff.json` is the **overall** original-checkpoint to final-memory diff
  (`scope: overall`), including any intervention effects. `intervention_diff.json`
  is an explicitly reported full-state intervention diff (`scope: intervention`),
  never inferred from the injected/retrieved subset. Source checkpoints are immutable.
- `isolation.py`: provenance labels enforce the adaptive-input boundary. Only
  `actor_visible` evidence is accepted; unknown/evaluator-only evidence is rejected.
  This cannot detect mislabelled data or infer whether arbitrary text contains
  ground truth. Each real adapter still requires a source-level isolation audit.
  The fake updater receives its memory and visible trajectory; evaluator artifacts have
  no path to that updater. Generic manifests default to unverified isolation.
- `provider.py`: dependency-injected transport enables offline payload/response
  tests. The HTTP transport requires `allow_network=True`; only its construction
  loads `DEEPSEEK_KEY`, optionally from a specified `.env`. No shell sourcing,
  global environment mutation, key logging or credential serialization occurs.
  The endpoint is fixed to the official API; redirects are refused. Failure bodies
  are withheld and responses containing the credential are rejected. Only content
  and tool-message fields are exposed; `reasoning_content` is discarded. There is
  no hidden-chain-of-thought dependency, output cache, or automatic retry.
- `telemetry.py`: per-call tokens, cache hits, latency, retry count, requested and
  resolved models, and cost. A shared `RunLedger` carries cost across sequential
  tasks; callers must pass the same ledger for a run. Accounting uses provider cost
  when supplied, otherwise the versioned project planning price table. Missing
  usage stays null/unavailable; missing cache counts use all-miss pricing as a
  conservative estimate. Unknown usage blocks subsequent calls. The table is
  recorded in each task and is not asserted to be current provider billing.

Budgets are checked before a call using input/output reservations and again after
recording actual usage. The provider defaults to reserving the full context input
cap; a smaller bound must be justified by the caller's tokenizer/context checks.
Hard USD limits apply to this recorded accounting model, not a guaranteed provider
invoice: a changed rate or a provider overrun can make a completed call exceed its
reservation. The overrun is saved and the task stops as `budget_exceeded`. No call
already sent can be undone. Unknown failures are counted with unavailable tokens
and stop execution. Current trackers/ledgers are for sequential use only.

### Schema 1.1 audit and memory boundaries

`model_calls.jsonl` adds request/response events. Each event has a generated stable
`call_id`, `phase` (caller supplies actor/updater/etc.), `synthetic`, and `event`.
The request contains the filtered **actual transport payload**: visible messages,
function tool definitions and model/thinking/temperature/max_tokens/stream settings.
The response contains only the filtered visible message, not the raw provider object.
`usage.json` call entries carry the same ID/phase/synthetic fields; response messages
in `messages_visible.jsonl` also retain these metadata independently of their message
allowlist. No authentication headers or credential configuration enter this path.
Tools support function definitions only; adapters must not put secrets in prompts,
function descriptions, JSON schemas or argument text. This is not a semantic scrubber.

Requests are flushed before transport entry and remain on failure/interruption.
A request event alone means prepared intent, not proven server receipt; the usage
entry counts transport entry. A preflight budget refusal records zero sent calls.
One `finally` accounting site covers success, ordinary errors and interrupts;
response-log callback failures still account once. Missing/invalid usage preserves
independently valid counts, nulls invalid counts, and records safe field-level
`usage_issues` plus `accounting_trusted: false`. Visible responses survive these
validation failures. Uncertain costs are null, not zero; the shared ledger becomes
uncertain and blocks subsequent tasks. Missing cache count alone still uses the
documented conservative all-miss estimate; contradictory cache counts stop the run.

The plain fake adapter emits **synthetic response/usage records only**; there was
no sent model request to reconstruct. Provider-to-pipeline tests separately use an
injected offline transport and mark both request and response events synthetic.
Neither fixture is scientific evidence or evidence of API compatibility.

Adapters may call `sink.updater_boundary("before"/"after", full_snapshot)` at the
actual updater boundaries. These create `updater_memory_before.json`,
`updater_memory_after.json` and `updater_memory_diff.json` (`scope: updater`).
The current minimal contract supports one updater interval per task. Do not use
`memory_injected` as a generic substitute: it may be a retrieval subset. Missing
boundaries, including stopping before the updater runs, remain `unavailable`;
one observed boundary alone cannot produce a diff. The fake adapter explicitly
applies masking to a detached working state before entering its add-only updater,
so mask deletion appears in intervention/overall diffs, never in updater diff.

Compatibility: manifest version is now `1.1`; existing 1.0 manifests still deserialize.
Existing artifact names remain, with additive event files, boundary files and fields.
Consumers must treat `memory_diff` as overall (the previous documentation was wrong),
join calls by ID rather than line order, handle `interrupted` and unknown accounting,
and never infer absent 1.0 audit/boundary data. Old artifacts are not rewritten.

### Validated conda environment

Review validation used `memory-infra`, Python **3.10.20**, Ruff **0.12.0**, pip
**26.1.2**, conda **26.3.2**, Linux x86_64. The interpreter was
`/home/coolboy/miniconda3/envs/memory-infra/bin/python` (observation only, not a portable
configuration requirement). The runtime has no third-party dependencies. All package
versions/builds are recorded in `configs/environment-infra-linux-64.yml`, sanitized
to name/version/build with a public channel and no exported prefix or private URLs.
The file is a platform-specific resolved environment definition, not a cross-platform
or checksum-verified lock. Existing base and agenticMMRag environments were not changed;
the old ignored `.venv` was not reused or deleted. No upstream dependencies were installed.
Conda isolation does **not** solve the Python 3.10/3.9 integration boundary.

Review validation on 2026-09-11: **55 unittest tests passed** (35 original + 20
review regressions), Ruff check passed, format check passed for 13 Python files,
compileall and offline smoke passed. Both setup scripts' default plan modes,
`bash -n` and `git diff --check` passed. The commands are listed above. Tests use
offline injected transports and temporary synthetic credentials only; the real
`.env` was not read or modified. Real API calls: **0**, API cost: **$0**. No upstream
fetch/install, real adapter or Phase 0/1 execution was performed in this review.

Adapters must emit observations as they happen and keep their in-memory checkpoint
observable throughout an update. The sink is not a general secret or ground-truth
scrubber: adapters must never provide credentials to it, and must label evidence
correctly. No real adapter is admitted as scientific evidence in this deliverable.

## AutoManual + ALFWorld provenance and setup report

Verified by public Git refs and source reads on 2026-09-11:

| Component | Official source | Fixed commit |
| --- | --- | --- |
| AutoManual | https://github.com/minghchen/automanual | `aeb17e4a4fe8bb43b9eb390b7b0b94a3ca8b9324` |
| ALFWorld reference only | https://github.com/alfworld/alfworld | `aaba6870f86c5be6a08a491f32a50b906227bc3e` |
| TextWorld dependency | https://github.com/MarcCote/TextWorld | `634f9f91fec732a79dd9e7623675301a53f06623` |
| downward dependency | https://github.com/MarcCote/downward | `84769171b9d965bf5739eaa7cf6604b0d9697534` |

Execution must use the author's bundled `automanual/alfworld` at the AutoManual
commit, tree `cc528106f15eaaef06f4900e78c649f9f99a5d06`. It includes author changes
to object naming for code-based plans. The separately pinned official ALFWorld
HEAD is a provenance reference only; substituting it would change the environment.
The original ALFWorld base commit of the bundled copy is unavailable, and is
explicitly marked so in `configs/automanual_alfworld/upstream.json`.

Source retrieval, which downloads code but never executes a model or task:

```bash
python scripts/setup/automanual.py --fetch
python scripts/setup/automanual.py --check
```

The script fetches the exact SHA into ignored `third_party/automanual`, verifies
origin, SHA and cleanliness, and reports a requirements-file hash. An existing
dirty, unrelated or differently pinned checkout is refused without modification.
An interrupted initial clone is preserved for inspection. No reset/cleanup is
performed automatically. Nothing is vendored into this repository's Git history.

The [pinned upstream README](https://github.com/minghchen/automanual/blob/aeb17e4a4fe8bb43b9eb390b7b0b94a3ca8b9324/README.md)
specifies Python 3.9.16, its bundled ALFWorld requirements, and two source-branch
dependencies. The installation script replaces those floating branch URLs with
the verified SHAs above, without modifying source. In a dedicated environment:

```bash
conda create -y --name memory-automanual python=3.9.16
conda run -n memory-automanual bash scripts/setup/install_automanual.sh --install
```

This explicit command installs dependencies; it does not download benchmark data
or run tasks. Logs and a post-install `pip freeze` (including on failure) remain in
ignored `.runtime/automanual-setup`. Do not publish those raw logs/freezes without
checking for index credentials/private URLs. The upstream requirements are only
partially pinned (including `openai==1.35.3`, `gym==0.15.4`, `ai2thor==2.1.0`); no
resolved dependency lock or successfully installed environment is claimed yet.
Once an environment works, its sanitized freeze, platform metadata, data checksums
and any compatibility patch must be preserved in each real run's provenance.

The upstream example uses `gpt-4-1106-preview` and `--assistant_api`. The project
substitution is all roles on `deepseek-v4-flash`, non-thinking, temperature zero.
No provider or memory-mechanism patch to AutoManual has been applied. Its original
runner is not an appropriate smoke command: it loops over environments and may
remove an existing log directory. This deliverable never launches that runner.

### Outstanding reproducibility gates

1. Install and lock dependencies on the upstream Python version; this has not been
   attempted in this deliverable. Review validation uses infrastructure Python
   3.10.20; Python 3.9 integration still requires a separate compatibility decision.
2. Verify dataset availability and checksums, one official task, evaluator, reset
   behavior, raw memory interception and ground-truth isolation.
3. Audit the upstream Assistants/chat interface. A DeepSeek substitution may need
   a documented compatibility patch; do not rewrite the memory mechanism.
4. Resolve model-ID compatibility before a real run. The currently retrieved
   [official chat API documentation](https://api-docs.deepseek.com/api/create-chat-completion/)
   lists `deepseek-flash` and supports `thinking: {type: disabled}`. The project
   requires `deepseek-v4-flash`. We preserve the requested ID and do not assume
   alias equivalence or silently migrate. No paid call has tested this ID.
5. Revalidate prices before paid execution. The attempted project pricing URL did
   not load in this inspection; the local table remains a labelled planning estimate.

These are unverified gates, not evidence that the upstream is irreproducible.
Phase 0/1 and provider compatibility remain **not completed**. No ACE, AWM,
candidate mining or formal branch experiment is implemented.
