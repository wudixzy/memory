# Five-task AutoManual online calibration

2026-09-11. Run **automanual-calibration-f13a39e724d0** completed all five
official task/update loops. `synthetic=false`, `scientific_evidence=false`.
**Phase 1 is not fully complete:** native targeted checkpoint intervention remains
unconnected; reset evidence is scoped rather than full hidden-state determinism.
No candidate mining, H1–H4 judgment, paid rerun or independent probe was performed.

## Fixed selection and execution

Before any model request, `configs/automanual_alfworld/calibration_tasks.json`
fixed this order and seed **42** for every task:

| Epoch / artifact directory | Official train task ID |
|---|---|
| 0 / task_00 | `look_at_obj_in_light-AlarmClock-None-DeskLamp-303/trial_T20190908_144950_175895` |
| 1 / task_01 | `look_at_obj_in_light-AlarmClock-None-DeskLamp-314/trial_T20190908_042426_942777` |
| 2 / task_02 | `look_at_obj_in_light-Book-None-DeskLamp-317/trial_T20190909_201143_217673` |
| 3 / task_03 | `look_at_obj_in_light-CD-None-DeskLamp-317/trial_T20190908_032827_984500` |
| 4 / task_04 | `look_at_obj_in_light-Newspaper-None-DeskLamp-216/trial_T20190908_143004_004127` |

Pinned bundled loader `alfred_tw_env.py:97` uses unsorted `os.walk`; no published
train_list exists in this checkout. We sort relative task paths lexicographically,
excluding only the loader's unsupported movable/Sliced names, and take the first
five of the bundled 54. No answer, difficulty, previous success or solvability
ranking selected/replaced a task. The resulting single task-family concentration
limits generalization. All required files were already bundled; no downloads.
The run summary records SHA-256 for all 15 task files before model execution;
source and selected data checks pass after each task.

One Python 3.9.16 worker owns the original Rule_Manager and Skill_Bank throughout.
Official simple-example initial rules and empty bank initialize once. Each task
gets a new real environment, InteractEnv and Worker guest, with epoch 0–4.
Task reset clears role, call IDs, sink, agent, trajectory and fixture offsets,
not persistent memory. Same-task replanning retains Python variables and actual
environment progress. Rules, native saves, check_rule and conditional run_merge
remain official. There is no concurrent scheduler or restart/resume mechanism.

The approved protocol is `automanual-native-won-v1-2026-09-11`. Official chat,
restricted Python and DashScope substitution are accepted for this calibration,
not claimed equivalent to the paper configuration or admitted as H1–H4 evidence.
Prompts and model-created rules were not repaired after observing their behavior.

## Measured results

All terminal statuses are **completed**, all official won values **true**.
Input below separates generation from embedding; cached is a subset of generation
input. Provider-reported USD fees are **null** for every task. USD and CNY columns
are local token-price estimates, not observed invoices or exchanged currencies.

| Epoch | Actions | Generation / embedding requests | Gen input / cached / output | Emb input | USD estimate | CNY estimate | Task seconds |
|---|---:|---:|---|---:|---:|---:|---:|
| 0 | 27 | 6 / 0 | 36606 / 28160 / 6793 | 0 | 0.010854360 | 0 | 33.918 |
| 1 | 6 | 2 / 2 | 8748 / 3712 / 1586 | 12 | 0.003436272 | 0.000006 | 8.934 |
| 2 | 8 | 2 / 2 | 8841 / 4992 / 1807 | 12 | 0.003353052 | 0.000006 | 9.713 |
| 3 | 28 | 2 / 2 | 9809 / 5760 / 1893 | 12 | 0.003520860 | 0.000006 | 11.513 |
| 4 | 8 | 2 / 2 | 9261 / 4864 / 1772 | 12 | 0.003474684 | 0.000006 | 9.389 |
| Total | 77 | **14 / 8** | **73265 / 47488 / 13851** | **48** | **0.024639228** | **0.000024** | **73.467** |

22 actual transports, **zero network retries**, five paid task starts exactly
once each. Every generation requested `deepseek-v4-flash`, non-thinking,
temperature 0; every returned generation ID was **deepseek-flash**. The bridge
now refuses other returned generation identities (including missing identity).
All eight embeddings returned **text-embedding-v4**, Beijing endpoint,
1024 finite float dimensions. Each retrieval uses one document embedding and one
query embedding; usage, vectors and requests are saved. No standalone probe.

Epoch 0 used all three native Worker attempts: its first generated block raised
an ordinary AssertionError after unsuccessful actions; official replanning
continued with the same guest/environment and achieved success on attempt three.
It then performed success-code summarization and indirect-success Builder
classification/update. Epochs 1–4 were direct successes. No facility failure,
unknown accounting, model identity change or budget termination occurred.

Limits: 12 combined requests/task, 60/run; USD 6/task and 6/run;
CNY 0.05/task and 0.20/run. The same RunLedger persists throughout, while each
task receives a new UsageTracker. Generation reserves the documented full
1,048,576 input context plus native 2000 output tokens (USD 0.3169728/request).
Embedding reserves 8192 tokens/input item. Actual usage is also checked.

Public prices were rechecked directly with TLS verification, no credentials,
on 2026-09-11 and remain applicable:

- [DeepSeek official pricing](https://api-docs.deepseek.com/quick_start/pricing/):
  peak upper-bound USD/million input hit **0.006**, input miss **0.30**, output
  **1.20**; legacy request ID served by Flash. Off-peak discounts are not assumed.
- [DashScope synchronous embeddings](https://help.aliyun.com/zh/model-studio/text-embedding-synchronous-api):
  Beijing text-embedding-v4 **CNY 0.0005/1000 input tokens**, no free allowance.
  Embedding provider fee is unavailable (not a provider invoice); CNY telemetry
  contains the local estimate only.

Observed mean is 4.4 transports/task (2.8 generation, 1.6 embedding),
USD 0.0049278456 plus CNY 0.0000048/task. This five-task, one-family sample is
not a robust forecast for larger or longer-memory sequences; no scaling authorized.

## Continuous memory and actual retrieval

Full snapshots match exactly at all four task transitions, including raw native
files and history; no extra task-initialization mutation needed a synthetic hash
adjustment. Each task's before→ordered update intervals→after chain was verified.

| Epoch | Rules before→after | Skill entries before→after | Complete updater intervals | Full memory bytes before→after |
|---|---|---|---:|---|
| 0 | 2→6 | 0→1 | 13 | 2076→68605 |
| 1 | 6→6 | 1→1 | 10 | 68605→82164 |
| 2 | 6→6 | 1→1 | 10 | 82164→98310 |
| 3 | 6→7 | 1→1 | 11 | 98310→126767 |
| 4 | 7→7 | 1→1 | 10 | 126767→142859 |

54 intervals include control/history and native persistence, not only LLM writes.
Native merge entry executes, but the rule count never exceeds 12: no merge model
call or renumbering was necessary. Memory growth includes histories and raw-file
copies, not just useful rule text.

Epoch 0 creates `look_at_obj_in_light` with native success flag 0 (indirect success,
eligible under official >=0 filter). Epoch 1 retrieves that entry, then replaces
it with its direct-success skill (flag 1), exactly as native add_skill dictates.
Epochs 2–4 retrieve the epoch-1 skill; later successes do not replace a direct
success entry. Every query and returned key is `look_at_obj_in_light`.
FAISS remains 1024-dimensional with `_normalize_L2=false`; no similarity changes.
With only one eligible entry, this verifies nonempty retrieval/injection, not
ranking quality or OpenAI embedding equivalence.

`memory_injections.jsonl` records actual FAISS keys, query, embedding identity,
returned skill text, helper source processed by the official AST selector and
actual role prompts. The helper name observed is `find_object`. Returned skill
text was verified literally present in each subsequent Worker request.
`model_calls.jsonl` contains document/query inputs, vectors and actual visible
generation request/response messages, linked to `usage.json` by call_id.
`retrieval_state` now reports currently eligible keys and explicitly describes
the non-checkpointed, per-query rebuilt index; it no longer always says empty.

## Phase 1 conditions, without automatic admission

| Existing condition | Actual status |
|---|---|
| Five sequential online tasks, specified non-thinking backbone | Pass for documented common-backbone chat path, all five completed |
| Usage and cost captured | Pass: both providers, per-task/run ledger, independent USD/CNY, actual returned IDs |
| Memory evolves across tasks | Pass: same native instances, four exact inheritance links, skills and rules updated |
| Raw actions/observations captured | Pass: 77 actions, initial observations, official evaluator and all update intervals |
| Task reset verified | Scoped/partial: existing docs/05 two-replay action/evaluator check still applies to its task; this run's first two task/seed initial observations equal offline resets. No five-task full-state or matched-action replay claim |
| Targeted native memory intervention technically possible | **Not complete**: prepare_memory still accepts only NoIntervention |

The shared MaskMemoryItem/NoMemory only supports mapping-memory adapters, not the
native Rule_Manager+Skill_Bank+history/files state. A shallow deletion could leave
helper examples/manual/history/skills accessible and interact with native
len(all_rules)-based new IDs. We did not add a checkpoint/renumbering framework or
claim masking tested. The smallest next work is a native derived-copy rule-mask
test covering actual text/helper injection, preserving source and unrelated skills;
no paid branch is needed for that technical check. Do not begin candidate mining
on the strength of this calibration alone.

## Implementation and validation record

- `scripts/smoke/automanual_calibration.py`: plan-first fixed five-task entry;
  two-task `--offline` wiring path; one existing 3.9 worker, no task retry.
- `scripts/smoke/automanual_adapter.py`: reuses its existing official connection
  worker for the sequence, initializes memory once, preserves per-task artifacts,
  validates state continuity and stops on incomplete execution.
- `adapters/automanual.py`: task-local reset, epoch, current retrieval state and
  observed FAISS/helper injection; strict returned generation identity.
- `telemetry.py`: optional max_calls_per_run and RunLedger.calls; existing
  keyword-based Budget callers remain valid. Schema stays 1.2; old artifacts untouched.
- `automanual_worker.py`: existing scoped environment factory accepts explicit
  task ID. No upstream edits, new patches, dependencies or installation.
  Existing 001–003 are checked, not reinstalled/replayed; runtime hashes are in
  manifests. Reused memory-infra 3.10.20 / Ruff 0.12.0 and memory-automanual 3.9.16.

**150 unit tests pass (2.566 s)**, including two new targeted regressions for
task-local reset and shared task/run call/currency accounting. Two offline
two-task development runs were made; the final one additionally proves a helper
written by the first official Builder is callable in the next Worker guest with
no execution errors: `artifacts/automanual-sequential-offline-a207ffeb1e3b/`.
The earlier diagnostic `...998fc82de804/` is retained unchanged; a misplaced
recovery-fixture snippet found during code inspection was corrected before the
final offline check and paid run. Neither diagnostic is scientific evidence.
Official nonempty FAISS offline check: `artifacts/skill-wiring-9653c2b5730f/`.
Ruff check/format (36 files), compileall, default plan and git diff check pass.

Commands (all tests, public-document retrieval and paid requests direct-only):

```bash
python scripts/direct.py conda run -n memory-infra env PYTHONPATH=src python -m unittest discover -s tests -v
python scripts/direct.py conda run -n memory-infra ruff check src tests scripts
python scripts/direct.py conda run -n memory-infra ruff format --check src tests scripts
python scripts/direct.py conda run -n memory-infra python -m compileall -q src tests scripts
python scripts/direct.py conda run -n memory-automanual python scripts/smoke/skill_bank.py --execute
python scripts/direct.py conda run -n memory-infra python scripts/smoke/automanual_calibration.py --offline
python scripts/direct.py conda run -n memory-infra python scripts/smoke/automanual_calibration.py
# Ran exactly once; not permission for another run:
python scripts/direct.py conda run -n memory-infra python scripts/smoke/automanual_calibration.py --execute
python scripts/direct.py git diff --check
```

Both transports retain ProxyHandler({}), verified TLS and zero hidden retries.
No global proxy/configuration or .env edits. Artifact audit confirms model IDs,
usage trust, literal skill injection, cross-task snapshots and runtime hashes.
An initial read-only hash audit used the wrong relative directory for patch
filenames; correcting that audit path passed all files (no runtime repair/retry).
Artifacts remain ignored; no Git commit. All old runs retain their original labels.
