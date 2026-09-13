# Multi-updater observation and official offline diagnostic adapter

Historical deliverable below. The scoped feedback exception is now approved;
ordinary guest errors are recoverable and a bounded real connection smoke is
authorized. See [the current follow-up](09_automanual_real_connection.md).
Earlier artifacts and results are unchanged.

Date: 2026-09-11. **Diagnostic only; no main experiment admission, no Phase 0.**
The [feedback proposal](07_feedback_protocol_proposal.md) is pending review and
does not amend AGENTS.md or docs/01. No real LLM/embedding request is authorized
or executed here; the previous embedding probe is not repeated.

## Schema 1.2 and compatibility

`Manifest.schema_version` defaults to `1.2`; 1.0/1.1 manifests still deserialize
with their original version. Additive `synthetic` defaults to null when not
specified, not an invented assertion about historical execution. This diagnostic
explicitly sets synthetic=true, execution_kind=synthetic_diagnostic,
scientific_evidence=false and isolation_status=diagnostic_boundary_pending_review.
Additive mechanism_fidelity defaults to not_verified for historical manifests;
this diagnostic explicitly sets **non_faithful_pending_review** rather than
inferring faithfulness from using official classes.

`updates.jsonl` is a new **append-only** journal. `ArtifactSink.begin_update` /
`finish_update` take full `MemorySnapshot` boundaries. IDs `update_000001`, etc.
are stable within an exclusive task directory, and sequence is start order.
Each begin/end carries phase, sequence, optional real trigger call_id (null for
non-model control operations), input/output reference envelopes, before/after,
status and exact interval diff. All are raw-preserving availability envelopes;
JSON strings retain Unicode and newlines. Input metadata is also detached from
mutable caller objects. References can include native operation arguments/results
inline and a model_calls call_id, not fictional model requests for metadata writes.

Begin is flushed before the native operation. End is appended, never replacing
begin or prior intervals; duplicate finish is rejected. A failed/interrupted
operation may have mutated memory: its missing end boundary remains unavailable,
**even if final task memory is available**. The task finalizer closes active
intervals as failed/interrupted/budget_exceeded without guessing an after state.
An abrupt kill can leave an open begin; the reader returns running + unavailable
after. Physical truncation/corruption of a JSON line raises a read error; no
claim of crash-proof storage or guaranteed persistence on filesystem failure.
The journal is sequential, not a concurrent multi-process writer.

Three independent diff semantics:

| Artifact | Exact meaning |
|---|---|
| `memory_diff.json`, scope=overall | Immutable original checkpoint → actual final task memory, including intervention effects |
| `intervention_diff.json`, scope=intervention | Explicit full pre/post intervention states; never assumed from retrieved text |
| `updates.jsonl` end.diff, scope=updater_interval | Actual full before/after of this particular native operation |

`read_updates(directory)` prefers the new journal. An empty journal explicitly
means no update began. For old directories without it, exposed legacy boundary
files are returned as a single `legacy_single` interval, with unspecified phase,
null call_id and unknown legacy terminal status. Missing old boundaries stay
unavailable; no old artifacts are rewritten. It does not infer updater execution
from overall task diffs or updater prose alone.

The old `updater_boundary` API and single `updater_memory_*` files remain for
existing fake/legacy callers and now additionally emit one journal interval.
New multi-interval callers leave singular files unavailable; at a second interval
all five singular updater files explicitly direct readers to updates.jsonl.
They are **not last-update aliases**. Mixing a new-API interval then starting a
legacy interval is refused. Old-only consumers must migrate to read_updates;
they cannot represent a multi-update task by selecting the final interval.

## Actual official-code connection

`scripts/smoke/automanual_adapter.py` is plan-only by default. `--execute` launches
a Python 3.9.16 trusted worker from the Python 3.10 infrastructure command. It uses
the existing single-task loader and **bundled** ALFWorld, not another ALFWorld HEAD
or the 135-task/deleting upstream runner. The diagnostic still runs official
`autobuild_case_trail.run`, `run_trail`, `run_merge`, `ChatGPT_Agent` Worker/Builder,
`Rule_Manager`, `Skill_Bank`, `InteractEnv` and `Agent` implementations.

Initial memory is a detached copy of official **simple-example init_rules** (two
rules, including helper source), empty skill bank, no published learned manual.
The independent `diagnostic_responses.json` fixture was authored without hidden
task answers. It deliberately inspects only and emits synthetic placeholder rule
operations solely to exercise merge instrumentation. This is **not a natural
memory failure candidate** and must never initialize a scientific experiment.

Official chat prompt assembly, examples, tokenizer and histories are retained.
A scoped OpenAI-constructor injection supplies only a tiny offline client object;
its chat boundary delegates to the existing `DeepSeekProvider` with an injected
fixture transport and synthetic=true. Thus actual assembled messages, requested
model/decoding config, visible outputs and usage join by the same stable call_id.
No alternate Planner/Builder classes emulate the algorithm. The fixture is finite;
exhaustion stops rather than repeating or falling back to a model. Paid transport
constructors are explicitly disabled and the trusted worker rejects Internet
connects. `execute_real_models()` always raises; the CLI offers no real-model flag.

Generation remains deepseek / deepseek-v4-flash / thinking=false / temperature=0,
max_tokens=2000. It uses the already-official **chat** path, not Assistants emulation.
The injected client rejects unverified stop/tools options; default null stop/tools
and zero penalties do not change text sampling. This is not a real API test.
Native consumed-token values and CallUsage counts are **synthetic** (1 input and
1 output token per fixture response), not tokenizer or server usage measurements.
A labelled zero-spend synthetic price table prevents reporting fictional spend.

Embedding stays Beijing DashScope text-embedding-v4 / 1024 / float. Full config and
identity hash are captured in snapshots. This task's empty bank follows official
no-success-skill retrieval and makes **zero embedding calls**, synthetic or real.
The separate official Skill_Bank/FAISS smoke still tests nonempty retrieval with
deterministic offline vectors; no string-match replacement or vector mixing.

### Complete memory and mutation capture

Every snapshot contains native all_rules, global_history, manual, cur_epoch,
responds, skill_dict, embedding configuration, and exact saved native JSON strings
when files exist. Unsaved native files and unused derived FAISS state are explicitly
unavailable. Retrieval text is not used as a substitute for this state. Native
files are saved only in an exclusive temporary diagnostic location, never an
upstream checkpoint; their actual contents survive inside boundary snapshots.

Scoped wrappers call original native methods in original order, capturing skill
add/failure/save, epoch history, each rule write/update/delete, history retrieval,
report/control mutations, save and each arrange_rules. A tiny explicit hook covers
the direct check_rule assignment, which otherwise is not a method call. Save
operations are included because they also change native history metadata and disk
state. No-op saves remain observed no-op intervals, not invented LLM updates.

The fixture yields **28 intervals**: failure skill and save; epoch history and save;
13 writes; report; check_rule; save; first delete/report/arrange; second pair of
deletes/report/arrange; final save. Both merge generations and both renumberings
remain separate. Every before hash is verified against the preceding actual after
hash, from checkpoint through final memory: the exercised path has no unobserved
full-state gap. This does not prove coverage of other entry points such as Formulator.

Rule correspondence is recorded from **observed Python dictionary identity**
before/after the original arrange_rules operation. Deleted rules map to null;
surviving object identities map to their actual new keys. Exact text/state changes
remain in the diff, including upstream reference replacements. It does not assume
IDs are stable across tasks, infer lineage from similar wording, or repair the
upstream renumbering/replacement implementation.

| Artifact | Real interception / unavailable scope |
|---|---|
| manifest | Pin, declared patch hashes, runtime injection/guest/fixture hashes, task seed, diagnostic policy, environment lock reference |
| memory before/after | Complete native state and saved raw JSON strings; no hidden engine state |
| memory injected | Singular file unavailable; exact role add_prompt strings in memory_injections.jsonl and actual request prompts in model_calls.jsonl (includes labelled static examples) |
| visible messages / call audit | Official chat client boundary through shared provider; synthetic usage joined by call_id |
| actions / observations | Before/after official raw environment step; initial raw text; model reports retain official transformations |
| evaluator | Actual raw numeric reward/done/won saved diagnostic-only; only native Agent/InteractEnv feedback returns to adaptive flow |
| updater input/output | Ordered operation arguments/results and model references in journal; singular files unavailable |
| updater diffs | Per-operation full-state interval; overall/intervention independent |
| isolation events | Sandbox readiness, result/stop/refusal categories, no raw exception body |
| trajectory | Actual step prefix and official task result, explicitly synthetic diagnostic |

The Python 3.9 worker now imports the tested observability subset directly
(pipeline annotations are deferred); this is a measured additional compatibility
surface, **not** a blanket Python 3.9 support promise. The Python 3.10 parent
reads/validates all full memory boundaries and call links from UTF-8 JSON after
worker exit. Guest code-object transport is only between the **same Python version**
worker/guest for the official compiled helper AST; it never crosses the 3.10/3.9
boundary. Arbitrary pickle/object graphs are not accepted. Other memory/upstream
objects do not cross the JSON boundary.

## Generated Python isolation and limitations

Local checks found bubblewrap 0.11.1, libseccomp 2.6.0 and working unprivileged
user/network namespaces on Linux WSL2 6.18.33.2 x86_64. No OS package was installed
or global setting changed. `CodeSandbox` fails closed on bootstrap/policy failure;
it has no local-exec fallback.

- Trusted worker owns actual environment/evaluator and Rule_Manager. The guest
  receives proxies, not those objects. Parent validates exact RPC fields, target,
  role, method, argument types/bounds and return type; no arbitrary getattr path.
- Bubblewrap creates new user/mount/PID/network/IPC/UTS namespaces, drops
  capabilities and clears environment. Only the conda runtime, system libraries,
  trusted guest bootstrap, private proc/dev and read-only empty tmp are mounted.
  Host project, home, task data and evaluator objects are absent. No provider
  key, proxy or provider routing config is inherited. TLS settings are unchanged.
- After interpreter bootstrap, libseccomp denies process creation/exec, sockets,
  connection, ptrace/cross-process memory, mount/namespace changes, bpf/keyctl,
  handle-based filesystem access and io_uring creation. This is an OS-enforced
  boundary, not an attribute-name filter, removed builtins or Python audit hook.
- Generated Python retains normal Python constructs/imports available in its
  runtime, helper definitions and persistent **Worker-only** local state. Each
  Builder block gets its own guest, preventing access to Worker's Python locals.
  Official helper AST selection/compilation is retained; executable helper bodies
  run only in the guest. Non-helper rule/skill storage algorithms stay official.
- Limits: 5-second guest exchange deadline, 10-second lifetime CPU limit,
  512 MiB address space, no file writes, 32 FDs, 100 RPCs/block and 1 MiB message
  limit. Nonblocking writes enforce deadlines under hostile RPC backpressure.
  Worker timeout is 180 seconds; termination targets only the owned process group.
  Guest fork/exec are forbidden; PID namespace teardown kills guest descendants.
  Exception, interrupt and log failure paths close guests and retain prior events.

Tested refusals: synthetic host-file/key sentinel, project paths, proc-root paths,
hidden object access, socket creation, fork/subprocess, unauthorized RPCs/fields,
cross-role rule/action access; tests use no real secret. Tested normal behavior:
Unicode/multiline Python, persistent helper locals, official get_object_with_id /
find_object / go_to_put_object through synthetic approved RPC, and real diagnostic
look/inventory observations. Timeout testing keeps an unrelated sentinel process
alive while killing the owned guest. Native feedback sentinel checks verify that
raw numeric reward, expert/admissible/hidden fields are not passed to the actor.

**Not established:** a formally verified sandbox, resistance to kernel/runtime
exploits or side channels, other OS/architectures, complete cgroup accounting of
the trusted environment, all Python packages/native extensions, arbitrary future
RPC handlers, long-running legitimate plans or every official example. Resource
limits and restricted capabilities can reject code the original unrestricted exec
accepted. Sandbox errors are safe generic categories, not the full original
Python exception string. These and chat/embedding substitutions require mechanism
impact review; we explicitly do **not** claim full behavioral equivalence or
mechanism-faithful main admission yet.

## Patch, dependency and failure record

Original pin and existing patches 001/002 are preserved. New
`003-execution-observation.patch` adds narrow executor injection points and a
no-op-default observation context around check_rule. Default Builder executor
scope is explicitly limited to rule_manager rather than incidental function
locals; the diagnostic replaces it with OS containment. No memory algorithm is
rewritten. The single small patch contains the required execution/observation
hooks; actual provider substitution and per-method logging are scoped runtime
injections in the separately hashed adapter module, restored on exit.

Setup still verifies origin, HEAD, bundled tree, no staged/untracked changes and
every exact declared diff block. Patch files grouped by purpose can differ from
Git's filename ordering, so comparison sorts **whole exact blocks**, not source
lines or hunks. This does not ignore modifications. Original pin → patches
001/002/003 is replayed in a temporary local clone; the existing checkout is never
reset/cleaned. Overlapping patches on the same file are not supported by this
simple exact-block contract; none are introduced here.

No conda or pip packages were installed/upgraded. Reused memory-infra (Python
3.10.20, Ruff 0.12.0) and memory-automanual (Python 3.9.16), existing dependency
locks in configs/automanual_alfworld. The first official tokenizer load failed
because its cl100k_base vocabulary cache was absent; the offline network guard
blocked its attempted connection. No API or credential loader was involved.
`scripts/setup/tokenizer.py --fetch` then fetched the public vocabulary **directly**
once with ProxyHandler({}), verified the upstream SHA-256 and stored it only in
ignored .runtime/automanual-tokenizer. No proxy retry, TLS bypass, tokenizer
substitution or local inference model download occurred. Its default mode is
plan-only; a populated cache is checked without a second download.

Vocabulary URL: https://openaipublic.blob.core.windows.net/encodings/cl100k_base.tiktoken
SHA-256: `223921b76ee99bde995b7ff738513eef100fb51d18c93597a113bcffe865b2a7`.
Environment/runtime information is also recorded in
`configs/automanual_alfworld/diagnostic_environment.json` without local prefixes,
credentials or private URLs. This is a version/platform record, not an OS image
lock or a clean-room reinstall claim.

## Verification commands and evidence

All commands use `python scripts/direct.py`, with no process proxies. Default
tests do not load ALFWorld or real credentials and do not connect to the Internet;
small local bubblewrap tests require the documented Linux capabilities. Real
environment and official helper/Skill_Bank integration are explicit opt-in.

```bash
python scripts/direct.py conda run -n memory-infra env PYTHONPATH=src python -m unittest discover -s tests -v
python scripts/direct.py conda run -n memory-infra ruff check src tests scripts
python scripts/direct.py conda run -n memory-infra ruff format --check src tests scripts
python scripts/direct.py conda run -n memory-infra python -m compileall -q src tests scripts
python scripts/direct.py bash -n scripts/setup/install_automanual.sh
python scripts/direct.py bash -n scripts/setup/install_skill.sh
python scripts/direct.py git diff --check
python scripts/direct.py conda run -n memory-infra python scripts/smoke/offline.py
python scripts/direct.py conda run -n memory-infra python scripts/smoke/automanual_adapter.py
python scripts/direct.py conda run -n memory-infra python scripts/smoke/automanual_adapter.py --execute
python scripts/direct.py conda run -n memory-automanual python scripts/smoke/feedback_contract.py --execute
python scripts/direct.py conda run -n memory-automanual python scripts/smoke/skill_bank.py --execute
python scripts/direct.py conda run -n memory-infra python scripts/smoke/automanual_env.py --execute
python scripts/direct.py conda run -n memory-infra python scripts/setup/automanual.py --check-patched
python scripts/direct.py conda run -n memory-infra python scripts/setup/automanual.py --verify-replay
python scripts/direct.py conda run -n memory-automanual python -m pip check
python scripts/direct.py conda run -n memory-infra python -m pip check
```

### Final measured results

**144 tests passed** (106 existing + 38 new), final run 2.665 seconds; no skips.
New tests: 15 journal/compatibility/partial-update tests, 19 RPC/OS containment
tests, 3 diagnostic admission/default-plan tests, 1 exact patch-block ordering
regression. Ruff check passed, format check passed for 34 Python files,
compileall passed. Both shell syntax checks, root `git diff --check`, and both
conda environments' `pip check` passed (`No broken requirements found.`).
The first lint attempts found import order and long fixture-string lines;
these were corrected, and the final listed checks were rerun successfully.

The three setup/default diagnostic plan modes and existing setup/install plan
modes passed without network or credential loading. Additional commands actually
executed, beyond the verification list above:

```bash
python scripts/direct.py conda run -n memory-infra python scripts/setup/tokenizer.py
python scripts/direct.py conda run -n memory-infra python scripts/setup/tokenizer.py --fetch
python scripts/direct.py conda run -n memory-infra python scripts/smoke/feedback_contract.py
python scripts/direct.py conda run -n memory-infra python scripts/setup/automanual.py
python scripts/direct.py conda run -n memory-infra bash scripts/setup/install_automanual.sh
python scripts/direct.py conda run -n memory-infra bash scripts/setup/install_skill.sh
```

| Final evidence | Result / artifact directory |
|---|---|
| Official AutoManual synthetic diagnostic | `artifacts/automanual-diagnostic-ee7ffaac441c/`: completed; 8 synthetic generation calls, 0 embeddings; 3 real actions; official failure=false-success result; 28 contiguous full-state update intervals |
| Official native feedback and public helpers | `artifacts/feedback-contract-7e129811ad46/feedback.json`: sentinel isolation and all three official public helpers through OS guest passed; synthetic raw environment, not real success evidence |
| Real environment, no model | `artifacts/automanual-env-83b173713f05/`: two same-seed four-action replays and exact JSON roundtrip passed, final source/data unchanged; all reward 0, won/done false |
| Official nonempty Skill_Bank / FAISS | `artifacts/skill-wiring-b537e8b6f209/`: offline document/query vectors and selected beta/helper passed; existing upstream get_relevant_documents deprecation warning retained |
| Fake shared pipeline | `artifacts/offline-b3f924e4d46d/fake_fixture/0_fixture/`: completed, non-scientific fixture |

Earlier successful diagnostic directories `automanual-diagnostic-f62e82c912cd`,
`automanual-diagnostic-421861f5d59b`, `automanual-diagnostic-719321f1f5a9` and feedback
checks were retained. They are development wiring iterations, not independent
experimental repetitions. Final adapter manifest explicitly says
`mechanism_fidelity=non_faithful_pending_review`; it is not admitted as primary
evidence. Full runtime injection/guest/fixture hashes matched current files.

Concrete interval examples in the final `updates.jsonl`: `update_000023` is the
first native arrange_rules, mapping deleted rule_2 to null and old rule_3 to new
rule_2; `update_000027` is the second, mapping its rule_2/rule_3 to null and its
old rule_4 to new rule_2. The same textual ID thus denotes different native
objects at successive checkpoints. Both original full states, mappings and diffs
are retained rather than overwritten. Singular updater files remain unavailable.

Pin/patch verification and pristine local-clone replay both passed. Patch 003
SHA-256: `1b47b91703a53863db531613f521440367939ee21f5ee621ba3f3ecdf516789d`.
Extra raw `git -C third_party/automanual diff --check` reported the **two existing
CRLF additions in patch 002** as trailing whitespace. We preserved the reviewed
patch bytes. A process-only CRLF-aware check passed:

```bash
python scripts/direct.py git -c core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol -C third_party/automanual diff --check
```

No global Git setting changed. Only the four files declared by 001/002/003 are
modified in the upstream checkout. Root status was inspected, including all
untracked paths (not just tracked diff). `.env`, runtime vocabulary, artifacts and
third_party checkout remain ignored. A static credential-pattern check over
in-scope source/docs/config/tests found no matches; it did not read `.env`.

Final `git status --short` (existing work preserved; no commit):

```text
 M README.md
?? .env.example
?? .gitignore
?? configs/
?? docs/03_infrastructure.md
?? docs/04_automanual_source_audit.md
?? docs/05_automanual_reproducibility.md
?? docs/06_embedding_wiring.md
?? docs/07_feedback_protocol_proposal.md
?? docs/08_multi_updater_diagnostic.md
?? pyproject.toml
?? scripts/
?? src/
?? tests/
```

## Remaining gates before a paid single-task Phase 0

1. Explicit review/approval of docs/07 boundary wording and exact native feedback
   cadence; diagnostic status is not main-run permission.
2. Review containment policy, restricted Python/error behavior and provider/runtime
   patch impact; broaden normal-path coverage if needed without weakening isolation.
3. Implement a separately reviewed real-provider bridge using this instrumentation,
   enforce per-call accounting/token reservations and enable it only after approval.
   The current synthetic client is not an enabled production adapter.
4. Recheck official generation API model/backend/prices and obtain a separately
   authorized minimal compatibility/task budget. No DeepSeek API compatibility was
   measured here; prior embedding compatibility is only one prior request.
5. Verify real model-generated task execution, memory before/after, evaluator and
   all actual update intervals; include successful native skill writes and other
   encountered branches, failures, reset and partial-run evidence. Current fixture
   covers failure + two merges, not a successful learned skill or Formulator.
6. Review deterministic resets/targeted native interventions and long-term skill
   retrieval state for later branching. Shared mask regression passing does not
   mean real AutoManual masking/admission is already complete.

Only after all protocol Phase 0 criteria are met may Phase 0 be declared passed.
This deliverable performs **0 real LLM calls, 0 real embedding calls; USD 0 / CNY 0**.
No .env access/modification, paid probe repetition, formal experiment or Git commit.
