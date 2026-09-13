# AutoManual bounded real single-task connection

Date: 2026-09-11. **Completed, existing Phase 0 checklist met for this path.**
This is connection validation, `synthetic=false, scientific_evidence=false`, not
H1–H4 evidence, Phase 1, or proof of unrestricted-upstream mechanism equivalence.
The user explicitly authorized exactly one task startup, at most 12 combined
generation/embedding transports, zero network retries, task/run USD 6 and CNY 0.01
caps. We started it once, did not restart it, and did not repeat the embedding probe.

## Minimal fixes and effective protocol

- `sandbox.py` / `sandbox_guest.py`: `GeneratedCodeError` is distinct from
  `SandboxError`. Ordinary guest exceptions retain the living guest, variables,
  helpers and actual environment progress. Built-in exception type and at most
  500 printable/newline characters of guest-local message cross the boundary;
  no traceback or host exception object does. Custom exceptions use a generic
  description rather than executing arbitrary custom `__str__`. Timeout, guest
  exit, communication and logging failures still terminate the owned process.
- `adapters/automanual.py`: ordinary errors return to official `run_trail`'s
  existing exception/report/replanning path. Facility aborts escape that ordinary
  handler and terminate the task, with no guest reconstruction. Original three
  Worker attempts and subsequent success/failure updates are unchanged.
- The effective, **AutoManual-only** feedback version is
  `automanual-native-won-v1-2026-09-11`. AGENTS §10 and docs/01 §6.1 now adopt the
  precise docs/07 native won-derived consumers, cadence, granularity and stopping
  semantics. No numeric reward, admissible commands, expert plans, hidden state
  or extra evaluator diagnostics are added to actor/updater input. Evaluator
  artifacts remain separately captured. Broader historical proposals are not
  automatically approved. No new approval framework was implemented.
- Shared manifest schema remains **1.2**, with additive `feedback_protocol`,
  `execution_restrictions` and nullable safe `termination_category`; defaults
  preserve reading old manifests. Old artifacts are untouched. `completed`
  means the official task/update pipeline completed, independently of task won;
  `failed`, `budget_exceeded` and `interrupted` remain distinct.

## Real provider connection and limits

The same official adapter supports either fixture transport or explicitly
injected real transports. `--execute` remains synthetic; `--execute-real` is the
bounded real entry; default remains a credential-free plan. The real branch does
not consume fixture responses, fixed token counts, synthetic zero prices or fixed
update/call cardinalities. Native chat wrapper counters now use the actual
provider's validated input/output counts. Actual messages, response content and
usage join by call_id. Unknown model tariff/usage blocks the shared ledger;
explicit model mismatch preserves visible output but cannot use the request tariff.

The shared task tracker counts **both** providers toward 12 transports and keeps
USD/CNY separate. Every generation reserves 1,048,576 input tokens and the native
2000 output cap, **USD 0.3169728** at the current peak upper-bound table. The
official cl100k_base prompt gate remains untouched, but is not used as a proven
DeepSeek billing bound. Twelve such generation reservations total USD 3.8036736
(a conservative planning envelope, not actual billed tokens). Embedding retains
8192-token/item CNY reservations, CNY 0.01 shared task/run limits, and zero retries.
The Python 3.10 parent allows 900 seconds for this bounded worker, covering up to
12 sequential 60-second generation timeouts plus orchestration; guest execution
limits remain unchanged. Budget/unknown-accounting stops preserve partial state.

Prices were fetched directly without credentials on 2026-09-11:

- [DeepSeek official pricing](https://api-docs.deepseek.com/quick_start/pricing/):
  Flash peak USD/million cache-hit 0.006, cache-miss 0.30, output 1.20; off-peak
  is half. The local table deliberately uses peak as an upper estimate. The
  source explicitly accepts legacy `deepseek-v4-flash` at Flash tariffs while
  serving V4.1 Flash. Requests stay on the specified legacy ID; returned identity
  is recorded separately, not silently rewritten. Accepted response IDs are
  explicitly listed in the adapter from this documentation, not fuzzy matching.
- [DashScope synchronous embedding](https://help.aliyun.com/zh/model-studio/text-embedding-synchronous-api):
  Beijing text-embedding-v4 remains CNY 0.0005/thousand input tokens; 1024/float,
  10 items, 8192 tokens/item. No free allowance or Batch discount is assumed.

Transports use explicit `ProxyHandler({})`, normal TLS verification, no redirects
and no SDK retries. No global OpenAI endpoint mutation is used. Credentials are
loaded only on explicit real transport construction; the real generation transport
read local configuration, while the unused embedding transport did not load its
key. The environment was created before credential loading; generated Python sees
only its cleared OS-sandbox environment and validated RPC capabilities. `.env`
was not printed, edited or serialized.

## Validation performed, not an expanded test campaign

Reused memory-infra Python 3.10.20 / Ruff 0.12.0 and memory-automanual Python
3.9.16. **No dependency installation, upstream patch modification, base changes,
full setup replay or unrelated smoke reruns.** Existing patches 001/002/003 were
verified by the worker before and after both task runs, together with task data
checksums. Their hashes are in each manifest. Runtime injection/guest/entry/provider
file hashes identify this revision separately from the unchanged patches.

**148 tests passed in 2.695 s** (144 existing, with the ordinary-error test repaired,
plus four focused connection regressions). New tests cover returned usage instead
of constants, nonzero real-path estimates, full-context pre-send reservation,
12-call refusal, unknown-price model blocking and code/facility distinction.
Injected offline transports and credential/network guards prevent real calls.
Ruff check, format check (35 files), compileall and git diff check passed.
The unrelated default-plan/timeout/no-proxy tests continue to pass in the suite.

Official recovery regression (real text environment, synthetic model fixture):
`artifacts/automanual-diagnostic-18adb68a24ce/`. First block defines helper/text,
executes an action, then raises NameError. Second block uses that same text/helper
and executes the next real action, with no execution error in its official report.
The original official flow completes failure updates and two merges: 8 synthetic
generations, 3 actions, 28 contiguous memory intervals. This is wiring evidence,
not an answer-bearing fixture or a model capability result.

Commands actually run (all direct, no proxies):

```bash
python scripts/direct.py conda run -n memory-infra env PYTHONPATH=src python -m unittest discover -s tests -v
python scripts/direct.py conda run -n memory-infra ruff check src tests scripts
python scripts/direct.py conda run -n memory-infra ruff format --check src tests scripts
python scripts/direct.py conda run -n memory-infra python -m compileall -q src tests scripts
python scripts/direct.py git diff --check
python scripts/direct.py conda run -n memory-infra python scripts/smoke/automanual_adapter.py
python scripts/direct.py conda run -n memory-infra python scripts/smoke/automanual_adapter.py --execute --recovery
# Executed exactly ONCE after offline checks; do not rerun without a new task authorization:
python scripts/direct.py conda run -n memory-infra python scripts/smoke/automanual_adapter.py --execute-real
```

Ruff formatting/import fixes were applied before final checks. Direct Python/urllib
public-document fetches supplied the price evidence above; they were not model
requests. Read-only artifact/status checks followed execution. No .env inspection
command, extra generation probe or standalone embedding probe ran.

## Actual single-task result

Artifacts: **`artifacts/automanual-real-ec50329edb5f/`**.
Manifest status completed, termination_category null, synthetic false,
scientific_evidence false. Runtime 8.6213 seconds; HTTP latency sum 7.3237 seconds.

Task: `pick_and_place_simple-AlarmClock-None-Desk-314/trial_T20190908_185938_027368`,
seed 42. Official simple-example initial rules (two), empty native Skill_Bank.
No learned manual, solution fixture or analyst-authored strategy was supplied.

| Actual call | Request → returned model | Input / cached / output tokens | Retries |
|---|---|---|---|
| Worker `ccc2ae45cf8d4bcb8e18ad8445753cea` | deepseek-v4-flash → deepseek-flash | 2024 / 0 / 654 | 0 |
| Builder `b73e1d7eac204a43b864753e2d1c167a` | deepseek-v4-flash → deepseek-flash | 3795 / 0 / 1099 | 0 |
| Total | 2 actual generation transports; 0 embeddings | **5819 / 0 / 1753** | **0** |

All calls non-thinking, temperature 0. USD provider-reported cost **null**, not
an observed invoice. Local peak-upper-bound estimate/accounted cost:
**USD 0.0038493**; CNY embedding cost **0** (no request). Both caps respected.
No free allowance is used to make these claims. Billing may use off-peak rates;
the saved local estimate is intentionally not a charge measurement.

Five actual environment actions: go_to desk_1, go_to dresser_1, take alarmclock_2,
go_to desk_1, put alarmclock_2 on desk_1. All came from the real Worker response.
The official TextWorld evaluator returned reward 0 / won=false / done=false for
the first four, reward 1 / won=true / done=true for the last. Official result:
`is_success=true`, `error_step=0` (direct success); no replan or classifier was
needed. No success signal was fabricated. Numeric reward remained evaluator data.

Twelve actual full-state updater intervals: add_skill, skill save, epoch history,
rule save, one write_rule, two update_rule, stop_generating, report, check_rule,
rule save and final run_merge save. Rules grew 2→3, so the official merge loop
correctly made **zero merge model calls**. Before→each interval→final SHA chain
and trigger call IDs were verified in both Python 3.9 worker and 3.10 parent.
Memory raw serialized size grew 2005→24368 bytes (+22363, including native files
and histories; not a pure rule-text growth metric). All visible requests/responses,
actions, observations, evaluator, interval inputs/outputs and full memory are saved.
Singular injected/updater files are explicitly unavailable in favor of actual
role injection events and ordered updates; no final-only surrogate. The manifest
system_prompt summary remains unavailable; the actual system messages are in
model_calls.jsonl. Missing provider fees and hidden reasoning are not invented.

## Existing Phase 0 checklist and next smallest action

| Existing criterion | Result |
|---|---|
| Upstream setup documented | Pass: docs/05–06 and existing environment locks; no new dependency needed |
| Upstream fixed | Pass: AutoManual aeb17e4a4fe8bb43b9eb390b7b0b94a3ca8b9324, bundled tree cc528106f15eaaef06f4900e78c649f9f99a5d06, declared 001–003 and data checks unchanged |
| DeepSeek-V4-Flash compatibility | Pass for the specified request ID and exercised official chat role path; actual returned alias/backend caveat recorded |
| One official task executes | Pass: real Worker control flow and 5 real environment actions |
| Evaluator executes | Pass: official TextWorld result, task success true |
| Memory before/after captured | Pass: successful skill, native Builder mutations, all 12 intervals and exact chain |
| No fatal undocumented dependency | Pass on this installed text/chat path; full upstream extras remain outside scope |

Thus the **existing Phase 0 connection gate passes** for this documented path;
success was observed but is not a necessary completion criterion. This does not
grant H1–H4 admission or erase deviations. Manifest mechanism_fidelity remains
`non_faithful_pending_review`, evaluator_leakage remains null rather than claiming
universal absence of leakage. Reviewed boundary enforcement is a narrower claim.

Remaining differences/coverage: restricted Python/resources and safe error text
are not unrestricted exec equivalence; official chat differs from paper Assistants;
DashScope substitution is not OpenAI embedding retrieval equivalence; this real
run does not test indirect success, real-model recovery/failure/merge, Formulator,
nonempty retrieval, arbitrary future code or full hidden-state determinism.
Synthetic recovery covers the requested error behavior, not every branch. The
Builder also mentioned a prior-epoch rule from its native static example; that is
visible model behavior retained without repairing prompts or memory after the fact.

**Next minimum action:** review these two real call traces and resulting native
skill/rule changes, accept or reject the documented mechanism differences, then
separately authorize a five-task calibration budget if appropriate. No automatic
Phase 1, extra API call, candidate mining or broader framework work is scheduled.

Final Git status: modified AGENTS.md, README.md, docs/01_validation_protocol.md;
existing untracked .env.example/.gitignore/configs/src/scripts/tests and docs/03–08
retained; new docs/09 added. .env, artifacts, runtime and third_party remain ignored.
No Git commit. Current round: **2 real LLM requests, 0 embedding requests, 0 retries**.
