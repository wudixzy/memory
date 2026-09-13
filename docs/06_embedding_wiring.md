# Smoke terminal-state repair and embedding substitution

Subsequent work: [feedback proposal](07_feedback_protocol_proposal.md) and
[multi-updater / isolated diagnostic adapter](08_multi_updater_diagnostic.md).
That follow-up makes no additional paid embedding request and does not waive
the feedback-protocol or main-experiment admission gates.

Latest review and authorized one-request probe: see the final section below.
The following original deliverable record is historical, including its zero-call
and unverified-API statements; it is not the latest probe result.

Date: 2026-09-11. This original deliverable does not execute an actor/updater, a real
embedding endpoint, Phase 0/1, or a scientific experiment. `.env` is untouched
and was not read. Authorization of embedding choice is not API verification.

## Direct-only execution

Prefix every validation/install command with `python scripts/direct.py`.
This process-local wrapper removes **all case variants** of `*_proxy`, sets
`NO_PROXY=*` only as a supplement, disables pip config files, then execs the
command. No user shell, conda, Git or system config is modified. Both actual
HTTP transports also clear process proxy variables and explicitly construct
`urllib.request.ProxyHandler({})`, reject redirects and retain default TLS
certificate verification. Neither transport uses the OpenAI SDK, global
`OPENAI_BASE_URL`, a requests session or hidden SDK retries. They have zero
automatic retries. Failed direct downloads are not retried through proxies.
The setup shell scripts independently remove proxies; Git subprocesses remove
proxy environment variables and pass a process-only empty `http.proxy` override.

ALFWorld children receive only operational PATH/HOME/LANG/LC_ALL variables, not
credentials, proxy or provider config. The environment and Skill_Bank workers
reject Internet socket connects. Regression tests inject fake proxy URLs and
synthetic keys with network connects forbidden, inspect the explicit urllib
handler and subprocess environment, and verify independent endpoint routing.

## Terminal state and partial evidence

`scripts/smoke/automanual_env.py:execute` encloses execution after exclusive
ArtifactSink creation in one try/except/finally. Only successful worker/replay,
serialization, final data check **and final source check** permit `completed`.
Ordinary exceptions become `failed`; interrupts become `interrupted` and are
re-raised. A safe stage plus generic error category is recorded, never exception
text. Already acquired actions, observations, evaluator and trajectory remain.
Roundtrip exceptions/mismatches follow the same finalizer. Existing output
directories remain forbidden. Filesystem failure or abrupt process death still
cannot guarantee persistence. The owned-process-group timeout cleanup remains.

## Configuration, audit and currencies

`EmbeddingConfig` is independent of generation `ModelConfig`; configuration is
also recorded in `configs/automanual_alfworld/embedding.json`. It enforces the
authorized Beijing DashScope endpoint, text-embedding-v4, dimension 1024, float
encoding and DASHSCOPE_API_KEY. Key loading occurs only in explicitly opted-in
real transport construction. Generation stays DeepSeek/deepseek-v4-flash,
non-thinking/temperature 0 with its separate endpoint and DEEPSEEK_KEY.

Public official [synchronous embedding API documentation](https://help.aliyun.com/zh/model-studio/text-embedding-synchronous-api)
was fetched directly with ProxyHandler({}) on 2026-09-11, without credentials.
Beijing text-embedding-v4 synchronous input price: **CNY 0.0005 / 1000 tokens**
(CNY 0.5 / million). No free allowance is assumed; this is not Singapore pricing
or Batch pricing. Documented limits are 10 inputs/request and 8192 tokens/input.
The current documentation prominently uses a workspace-specific Beijing gateway;
we do not silently change the explicitly authorized legacy DashScope base URL.
Its actual compatibility is unverified until an explicit real probe succeeds.

`embedding.py` preserves input strings, restores response order by index and
rejects missing/duplicate/out-of-range indices, count mismatch, wrong dimensions,
empty vectors and non-finite/non-numeric elements (including booleans). No padding,
normalization, dimension/model migration or silent input truncation occurs.
LangChain bridge batches documents in groups of ten; each batch and query is a
separate counted transport entry, with no caching or hidden retry. Reservations
use the full documented input cap; tokenizer length compatibility remains a real
probe/production boundary, not a guessed byte-to-token conversion.

Telemetry additions are backward-compatible fields on the existing schema 1.1:
`kind`, `currency`, `input_count`, CNY estimate and price-source/date per call;
`embedding_calls`, `total_calls`, `accounted_cost_cny` in summaries; CNY task/run
caps and `RunLedger.cost_cny`. Existing `llm_calls` remains generation-only;
max_calls_per_task now limits **all** generation + embedding transport entries.
Token totals cover both. USD and CNY remain separate components of one shared
task/run budget; they are **never summed or implicitly converted**. A caller must
set both currency caps for a mixed-provider run. Unknown embedding cost is null,
not zero, and marks the shared ledger uncertain, blocking either provider next.
Synthetic calls explicitly report synthetic=true and actual zero CNY spend.

Embedding request/response events in `model_calls.jsonl` join usage by stable
call_id/phase and carry embedding identity. Requests contain only input text and
model/dimensions/encoding configuration; responses only validated ordered vectors.
Credential headers and raw provider response objects are excluded. Valid vectors
can be logged independently of missing usage. Sent attempts have one finally-based
accounting site, including transport interrupts and response/usage logging failure;
pre-send budget or request-log rejection records zero sent attempts.

## Official Skill_Bank boundary

Fixed AutoManual origin https://github.com/minghchen/automanual.git, commit
`aeb17e4a4fe8bb43b9eb390b7b0b94a3ca8b9324`. Existing patch 001 is retained.
Patch 002 changes only the constructor at original
`automanual_alfworld/autobuild_utils.py:161,164`: accept optional `embedding`,
otherwise keep the original OpenAIEmbeddings construction. It is explicitly an
**embedding substitution**, not evidence of retrieval equivalence to OpenAI.
The unmodified `get_relevant_skill:184–203` still filters success>=0, rebuilds
FAISS from task types, performs similarity k=1, defines retrieved helper code,
and returns the original formatted skill to its caller. Failure-record injection
is not removed. FAISS default distance/normalization is retained.

`scripts/smoke/skill_bank.py --execute` is an explicit Python 3.9.16 **offline
wiring check** using the actual patched official class and installed FAISS, not a
reimplementation. Two successful synthetic skills plus one excluded failure and
a differently named query use deterministic 1024-dimensional vectors. It verifies
document/query calls, reordered provider indices, beta selection and returned
content/helper function, immutable source fixture and unchanged upstream patches.
It records full fixture/config identity, requests, distance strategy and usage;
no published learned manual initializes this test. Configuration identity is
checked at each bridge call; no cross-model/dimension vector cache is used.
This is neither DashScope quality validation nor original-embedding equivalence.

Installed langchain-openai 0.1.8 was also inspected: `_get_len_safe_embeddings`
delegates to `_process_batched_chunked_embeddings`; a single chunk is returned
unchanged, whereas multiple chunks are weighted-averaged and normalized. The
tested native task-type keys/query are short, single-chunk inputs, so there is
no additional upstream local normalization to reproduce on this path. The
DashScope bridge deliberately does not emulate OpenAI tokenizer/chunk averaging
for arbitrarily long strings; long-input equivalence is unverified, and provider
length rejection stops rather than truncating or silently changing the algorithm.

## Environment changes and reproducibility

Only memory-automanual Python 3.9.16 receives packages. memory-infra remains
Python 3.10.20/Ruff 0.12.0; base and unrelated environments are unchanged.
`install_skill.sh --install` installs only imports required for official
Skill_Bank and their dependencies, with public PyPI, direct connections and
zero download retries. Initial attempt failed resolving old LangChain's
packaging<25 against text-constraints packaging==26.3. Its full ignored log remains
`.runtime/automanual-setup/skill-mSdzmJP8/install.log`. New skill constraints use
packaging 24.2, preserving the historical text-only lock. No core mechanism was
replaced to fix the dependency conflict. OpenAI 1.35.3 retains upstream pin;
HTTPX 0.27.2 avoids the removed proxies-constructor parameter incompatibility with
that old SDK. The SDK is an import dependency, not our actual network path.

Python 3.9 receives only the narrow embedding/config/telemetry bridge imports;
deferred annotations allow those imports. This does not claim the entire Python
3.10 infrastructure or a real actor adapter is Python 3.9 compatible. The real
environment continues using the existing 3.10-parent/3.9-worker JSON boundary.

## Reviewable real probe (NOT run in this deliverable)

```bash
python scripts/direct.py conda run -n memory-infra python scripts/smoke/embedding_probe.py
# Offline synthetic path only, no credential loading:
python scripts/direct.py conda run -n memory-infra python scripts/smoke/embedding_probe.py --offline
# Future explicit opt-in; this command reads local credentials and spends quota:
python scripts/direct.py conda run -n memory-infra python scripts/smoke/embedding_probe.py --execute
```

Fixed public inputs: `A small red book.` and `一本红色的小书。`. Exactly one
embedding request, max 16384 input tokens reserved, no retry, 30-second HTTP
timeout, CNY 0.008192 reservation and **CNY 0.01 task/run cap**. Stop on first
response, transport/shape/model/usage error, interruption or budget limit; save
partial usage and safe status in a unique ignored artifact directory. These are
planning bounds, not measured billing. No LLM request or environment is part of
the probe. Missing server model identity remains unavailable, never invented.

## Scientific gates remain separate

1. Whether native reward/won/done may enter the adaptive loop needs a protocol decision.
2. Generated Python can access hidden state/expert data; containment is unfinished.
3. Multiple updater intervals still need faithful shared artifact support.
4. Embedding substitution is authorized and audited here; it does not resolve 1–3
   or demonstrate real API compatibility/retrieval quality.

Official success feedback is neither removed nor reclassified. No actual
actor/updater executes; Phase 0 has **not** passed.

## Actual validation record

**98 tests passed** (68 previous + 30 new regressions). Ruff check/format check
passed for 23 Python files; compileall, both shell syntax checks and git diff
whitespace checks passed. All command executions below used the direct wrapper.
The original timeout test and new SIGKILL escalation test both pass.

```bash
python scripts/direct.py conda run -n memory-infra env PYTHONPATH=src python -m unittest discover -s tests -v
python scripts/direct.py conda run -n memory-infra ruff check src tests scripts
python scripts/direct.py conda run -n memory-infra ruff format --check src tests scripts
python scripts/direct.py conda run -n memory-infra python -m compileall -q src tests scripts
python scripts/direct.py conda run -n memory-infra python scripts/smoke/offline.py
python scripts/direct.py conda run -n memory-infra python scripts/smoke/embedding_probe.py
python scripts/direct.py conda run -n memory-infra python scripts/smoke/embedding_probe.py --offline
python scripts/direct.py conda run -n memory-infra python scripts/smoke/automanual_env.py
python scripts/direct.py conda run -n memory-infra python scripts/smoke/automanual_env.py --execute
python scripts/direct.py conda run -n memory-infra python scripts/smoke/skill_bank.py
python scripts/direct.py conda run -n memory-automanual python scripts/smoke/skill_bank.py --execute
python scripts/direct.py conda run -n memory-infra python scripts/setup/automanual.py
python scripts/direct.py conda run -n memory-infra python scripts/setup/automanual.py --check-patched
python scripts/direct.py conda run -n memory-infra python scripts/setup/automanual.py --verify-replay
python scripts/direct.py conda run -n memory-infra bash scripts/setup/install_automanual.sh
python scripts/direct.py conda run -n memory-infra bash scripts/setup/install_skill.sh
python scripts/direct.py conda run -n memory-automanual bash scripts/setup/install_skill.sh --install
python scripts/direct.py conda run -n memory-automanual python -m pip check
python scripts/direct.py bash -n scripts/setup/install_automanual.sh
python scripts/direct.py bash -n scripts/setup/install_skill.sh
python scripts/direct.py git diff --check
```

The first successful install log is `skill-m5tw1qf3`; a repeat using the complete
resolved `skill-constraints.txt` succeeded in `skill-okW0aNVc`. Both are under
ignored `.runtime/automanual-setup/`; the earlier failed attempt is retained.
Resolved imports: OpenAI 1.35.3, HTTPX 0.27.2, langchain-openai 0.1.8,
langchain-community 0.2.4, langchain-core 0.2.43, FAISS CPU 1.7.4, packaging 24.2,
NumPy 1.23.5. Pip is 24.0 upstream and 26.1.2 infra. All resolved pip versions are
in skill-constraints.txt; conda builds remain the existing environment-text-linux-64.yml.
This is a Linux version lock/reinstall check in the existing environment, not a
clean-room build or checksum-locked wheel distribution. Full upstream extras and
actor dependencies/runtime are not certified by pip check.

Source verification succeeded on the existing declared-patch checkout and on a
**temporary local clone**: pristine origin/HEAD/bundled tree verification, apply
001 and 002, then exact diff verification. No network fetch or reset/clean of the
existing checkout was involved. Patch 002 SHA-256:
`8a1c5f3ec764aed0d40af71852748a6c07cbf0f22b8650bedea227df276b6e08`.
Its diff preserves the upstream CRLF lines; applying both patches was actually
tested, not inferred from reverse applicability alone.

Final real environment evidence: `artifacts/automanual-env-0f5d8e6748ad`.
Two seed-42 replays, four actions each, observable replay equality and exact JSON
roundtrip passed; data unchanged and final source check passed. All step rewards
remain 0, won/done false. This does not establish full-state determinism or success.
Final Skill_Bank evidence: `artifacts/skill-wiring-22efd8242382`, two synthetic
embedding transport entries (documents/query), 1024 dimensions, EUCLIDEAN_DISTANCE,
normalize_L2=false, expected beta content and helper returned. The original
get_relevant_documents deprecation warning remains visible; behavior was not
rewritten to silence it. A portable small extract is
`configs/automanual_alfworld/embedding_wiring_evidence.json`.

Offline probe and fake pipeline also succeeded. Actual remote LLM/embedding
calls: **0 / 0**. Actual model fees: **USD 0 / CNY 0**. `.env` was neither read nor
modified; no Git commit was created. Existing user changes and previous artifacts
were retained. Missing real API verification and the three scientific gates above
remain explicit blockers, not failures hidden by synthetic evidence.

## Follow-up P2 review and single authorized real probe — 2026-09-11

### Repairs and compatibility

1. `src/memory_validation/embedding.py:EmbeddingProvider.embed` separates outcome
   (`status`, safe `error_category`), token validation (`token_usage_trusted`) and
   accounting trust (`accounting_trusted`). Explicit model mismatch is `failed` /
   `model_mismatch`, retains independently valid tokens and validated response
   vectors, but has null CNY cost. It marks the shared ledger uncertain, blocking
   both DeepSeek and DashScope on the next task. Invalid dimensions/index/numbers
   are `failed` / `invalid_vectors`; trustworthy model/usage still retain the
   incurred cost estimate, not zero. Mismatch also wins when vectors are invalid.
   Missing resolved identity stays null/unavailable, separately from mismatch:
   the local estimate then uses the requested endpoint/model tariff, not a claim
   that the server exposed its identity. Request/response/usage retain one call_id.
   The single finally accounting site, pre-send rejection and interrupt propagation
   remain. Response logging failure is failed without losing known usage/cost;
   usage callback failure does not duplicate the already recorded call.
2. `src/memory_validation/telemetry.py:UsageTracker.before_call` validates CNY
   reservation types before any transport. Only finite nonnegative int/float
   values are accepted (bool excluded). None means generation/USD reservation;
   numeric zero is a valid embedding/CNY reservation. NaN, infinities, negatives,
   strings and other types fail. Unknown prior CNY totals block rather than being
   truthiness-coerced to zero. Existing call/token/actual-overrun checks remain.
3. `UsageTracker.summary` filters provider-reported USD aggregation to USD calls.
   CNY calls cannot poison it. USD 0.1 plus a CNY call yields USD 0.1; any USD
   call with absent provider cost still makes that provider-reported total null.
   Pure embedding has an empty USD subtotal of 0, **not** a provider CNY quote.
   Estimated, accounted and provider-reported costs remain distinct, with no FX.

Schema 1.1 has two additive optional CallUsage fields: `token_usage_trusted`
(defaults null for existing generation callers) and `error_category` (safe enum-like
category, default null). `status` now correctly distinguishes failed embedding
output from valid accounting. Existing records remain readable; consumers must
not equate `accounting_trusted=true` with a successful call. No raw exceptions,
headers or provider objects were added. Probe reports additionally expose
transport_entries, resolved_model, input_tokens, provider_reported_cost_cny
(unavailable/null), estimated_cost_cny and HTTP timeout. Only a successful real
probe sets api_compatibility=`this_request_only_verified`.

### Offline verification before the real request

**106 tests passed: original 98 plus 8 regressions in
`tests/test_embedding_review.py`.** These cover mismatch with response/usage join
and cross-provider shared-ledger blocking; invalid vectors with retained nonzero
cost arithmetic; missing identity; simultaneous mismatch/invalid vectors; invalid
CNY types before transport; None versus zero reservation; pure/mixed/unknown USD
provider totals; response-log failure counted once. All injected responses are
synthetic, network is blocked and real credential transport construction is
forbidden in the new tests. Nonzero cost arithmetic tests do not incur spend.
Existing interruption/logging/pre-send regressions also passed.

Every validation command used `python scripts/direct.py`; transports retain
ProxyHandler({}), verified TLS, no redirects/retries. No global configuration was
changed. Reused memory-infra Python 3.10.20, Ruff 0.12.0, pip 26.1.2 and
memory-automanual Python 3.9.16. No dependency installs/environment changes.

Commands actually executed (all final checks passed):

```bash
python scripts/direct.py conda run -n memory-infra env PYTHONPATH=src python -m unittest discover -s tests -v
python scripts/direct.py conda run -n memory-infra ruff check src tests scripts
python scripts/direct.py conda run -n memory-infra ruff format --check src tests scripts
python scripts/direct.py conda run -n memory-infra python -m compileall -q src tests scripts
python scripts/direct.py bash -n scripts/setup/install_automanual.sh
python scripts/direct.py bash -n scripts/setup/install_skill.sh
python scripts/direct.py git diff --check
python scripts/direct.py conda run -n memory-infra python scripts/smoke/embedding_probe.py
python scripts/direct.py conda run -n memory-infra python scripts/smoke/embedding_probe.py --offline
python scripts/direct.py conda run -n memory-infra python scripts/smoke/offline.py
python scripts/direct.py conda run -n memory-infra python scripts/setup/automanual.py --check-patched
python scripts/direct.py conda run -n memory-infra python scripts/setup/automanual.py --verify-replay
python scripts/direct.py conda run -n memory-automanual python scripts/smoke/skill_bank.py --execute
python scripts/direct.py conda run -n memory-automanual python -m pip check
```

Initial Ruff found one new-test import-order issue, fixed with Ruff; subsequent
lint and format checks passed (24 Python files). Official Skill_Bank/FAISS offline
evidence: `artifacts/skill-wiring-ec52da7cd8b0`; existing upstream deprecation warning
retained. Original pin plus patches 001/002 and pristine-to-patched local temporary
clone replay passed. Patches unchanged. pip check: no broken requirements.
Offline probe: `artifacts/embedding-probe-2fb6ef53674f`; fake pipeline:
`artifacts/offline-b3ddc9a82504/fake_fixture/0_fixture`. No real actor/updater or
environment experiment was launched by these checks.

### Price gate and actual one-request result

Before execution the official synchronous embedding page linked above was fetched
again directly using the direct wrapper and urllib ProxyHandler({}), timeout 30,
without credentials. On 2026-09-11 its **Beijing text-embedding-v4** row still
specified CNY 0.0005 per thousand input tokens, 10 items/request, 8192 tokens/item.
Thus 16384 reserved tokens cost CNY 0.008192, below both task and run caps of
CNY 0.01. No free allocation or Batch discount was assumed.

The following command was then executed **exactly once**, after all gates passed:

```bash
python scripts/direct.py conda run -n memory-infra python scripts/smoke/embedding_probe.py --execute
```

Result: completed, exit 0. Artifacts:
`artifacts/embedding-probe-a6a87e8e8ebf/` (`probe.json`, `usage.json`,
`embedding_calls.jsonl`). The request and validated response join usage through
call_id `36c9ad90cd264b479f68a0bc34291f4b`, phase `compatibility_probe`.

| Item | Actual result |
|---|---|
| Transport entries / real requests / retries | 1 / 1 / 0 |
| Endpoint | https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings |
| Region / encoding | Beijing / float |
| Requested / returned model | text-embedding-v4 / text-embedding-v4 |
| Inputs | `A small red book.` and `一本红色的小书。` only |
| Validated output | 2 vectors, each 1024 finite numeric elements |
| Input tokens | 12 |
| Latency | 0.315739156 seconds |
| Provider-reported CNY cost | unavailable / null |
| Local estimated/accounted CNY cost | 0.000006 (12 × 0.5 / million) |
| Task/run hard cap | CNY 0.01 each |
| Safe failure category | null (success) |
| Generation-model calls / USD spend | 0 / 0 |

The CNY estimate is **not an observed bill or provider-reported charge**. Only
the explicitly opted-in real transport loaded local credentials; no key or .env
content was printed, serialized or modified. Runtime artifacts remain ignored.
No second real request was made. This proves only this particular embedding
request and capture path work, not retrieval quality, OpenAI equivalence, or
Phase 0. Official-success-feedback protocol, generated-Python hidden-state
isolation and multiple updater intervals remain separate unresolved gates.

Final `git status --short` (existing work retained; no commit):

```text
 M README.md
?? .env.example
?? .gitignore
?? configs/
?? docs/03_infrastructure.md
?? docs/04_automanual_source_audit.md
?? docs/05_automanual_reproducibility.md
?? docs/06_embedding_wiring.md
?? pyproject.toml
?? scripts/
?? src/
?? tests/
```
