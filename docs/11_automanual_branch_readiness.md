# Phase 1: scoped rule masking and reset verification

2026-09-11. Both remaining technical checks pass. **Phase 1 engineering
connection conditions are satisfied within the scopes below.** This is not H1–H4
evidence, general benchmark determinism, or authorization for paid experiments.
No calibration rerun, candidate mining, real model/embedding request or dependency
installation was performed. New cost: **USD 0 / CNY 0**.

## Real checkpoint and restoration

Source: `artifacts/automanual-calibration-f13a39e724d0/task_00/memory_after.json`.

- Snapshot SHA-256: `1ccc7b7eb51c9780aa5db68a78215342219588d017fd300729b9bea9616fd349`.
- File SHA-256: `1537d850722c75db985b54955229b27fd03327d260a7d5d13f45273bd97bcaec`.
- Target: **rule_2**, the first numeric rule ID absent from official initial
  rules (rule_0/rule_1), in the first task's post-task checkpoint. No expected
  effect, outcome or harmfulness criterion selected it.
- Topic: non-portable objects / adapting when take_from returns Nothing happens.
  Its example is comments, with **no function definitions**.

`AutoManualAdapter.restore_checkpoint` writes the two original native file texts
into a fresh branch-only directory and calls the official Rule_Manager/Skill_Bank
load methods. It restores the additional full-snapshot in-memory history,
all_rules, manual, responds and cur_epoch fields; the native history→all_rules
alias is preserved where present. Next epoch is 1, not epoch_0. Embedding identity
must match; incomplete native saved files are not silently reconstructed.

Both branches' complete before/after snapshots equal the source, including raw
file text, skills, rule IDs and metadata. Historical snapshot metadata stays
source metadata; the new execution manifest separately labels the operation
offline. SHA-256 checks over **every original calibration artifact** before and
after validation confirm no old artifact was changed. Task data and declared
upstream patches are also unchanged.

## Exact intervention scope

**actor_rule_injection_mask**: `MaskMemoryItem("rule_2")` filters a copy only at
the official `Rule_Manager.rule_string` and `define_functions_from_rules` entry
points called by official run_trail. The full persistent rules remain 0–5;
Builder still sees the same full collection. There is no global deletion,
updater intervention, renumbering or change to native write_rule allocation.

Observed through official autobuild_case→run_trail→Worker chat request assembly:

- Intact rule text/helper-source IDs: 0,1,2,3,4,5.
- Masked IDs: 0,1,3,4,5. Exact text comparison removes **only** rule_2's text
  and example block. Non-target example strings are unchanged.
- The actual Worker message list contains the assembled rule text. Model output
  is unavailable: execution deliberately stops at the first client request.
- Rule_2 has no helper to remove. A **separate synthetic fixture**, not inserted
  into the real checkpoint, exercises the same official helper assembly: the
  target-only function is absent, a non-target function executes, and a same-name
  pre-existing public helper is preserved.
- The real guest retains callable get_object_with_id, find_object and
  go_to_put_object. Rule_1 and the retrieved skill also provide find_object;
  these remain available and keep their native injection order.

Alternative content deliberately retained: rule_4 also discusses non-portability;
rule_3/rule_5 cover related task steps; epoch_0 history and the learned
look_at_obj_in_light skill remain intact. The returned skill string is byte-equal
between branches. Masking one channel therefore does **not** remove all related
knowledge, and is not evidence of a behavioral effect. Formulated non-null manuals
are explicitly unsupported by this small mask. NoMemory was not added.

## Offline request and vector replay

Execution: `artifacts/automanual-branch-check-8dc5ce2a5726/`.
`intact/` and `masked/` contain full snapshots, exact intervention/overall diffs,
actual visible Worker request messages, rule/helper injection events, guest
events and zero-call usage. The top-level report and manifest identify the source,
scope, patch provenance and technical-verification nature.

The injected offline client capture bypasses provider.complete and stops before
any model service transport. Its audit request records the native visible
messages/max_tokens and fixed non-thinking configuration; no-tools is represented
as an empty list. This is request assembly evidence, **not a sent API payload or
new generation**. No returned response or token usage is fabricated.

Official nonempty Skill_Bank→FAISS uses vectors from the original
`task_01/model_calls.jsonl`, matching phase, exact input list, model, dimensions,
encoding and embedding identity. Documents and query both use
`["look_at_obj_in_light"]`. Original call IDs:

- documents: `ce607d8c35c048c6af72a0ee074f7539`;
- query: `25868cee6d274532ab67f5cffc3e32c8`.

Replay events retain source path/file hash/call ID, without adding CallUsage or
new fees. A missing exact match fails; there is no network fallback. FAISS and
native skill/helper selection remain unchanged. Internet socket connections and
.env reads are prohibited by the explicit validation entry.

## Reset and complete action replay

Same environment factory and AutoManualAdapter.reset_task as calibration/branch
execution, bundled fixed source/data, seed 42. Each task gets **two independent
new environments**; the saved action sequence is unchanged and no model is used.

| Original task | Saved actions | Replay A vs B | Both replays vs original |
|---|---:|---|---|
| `look_at_obj_in_light-AlarmClock-None-DeskLamp-303/trial_T20190908_144950_175895` | 27 | Equal | Equal |
| `look_at_obj_in_light-AlarmClock-None-DeskLamp-314/trial_T20190908_042426_942777` | 6 | Equal | Equal |

Compared raw initial observation, every action and raw step observation, numeric
reward, won and done. All first-divergence fields are null. Four replay files
`reset_0_0.json` … `reset_1_1.json` preserve all 66 replayed action results.
Evaluator fields are diagnostic-only and never supplied to actor/updater.
This proves reproducibility for **these two tasks, seed and action paths only**;
it does not compare every hidden state or establish benchmark-wide determinism.
No alternate seed/task/action or repeated search for matching results was used.

## Verification and Phase 1 status

**153 unit tests pass in 2.732 s**, including three new focused tests for full
restore/source immutability, exact vector lookup and first reset divergence.
The opt-in official validation additionally checks prompt/helper assembly and
the independent helper fixture. Ruff check, format (38 files), compileall, default
plan and git diff check pass. Existing environments/dependencies are unchanged.

```bash
python scripts/direct.py conda run -n memory-infra env PYTHONPATH=src python -m unittest discover -s tests -v
python scripts/direct.py conda run -n memory-automanual python scripts/smoke/automanual_branches.py --execute
python scripts/direct.py conda run -n memory-infra python scripts/smoke/automanual_branches.py
python scripts/direct.py conda run -n memory-infra ruff check src tests scripts
python scripts/direct.py conda run -n memory-infra ruff format --check src tests scripts
python scripts/direct.py conda run -n memory-infra python -m compileall -q src tests scripts
python scripts/direct.py git diff --check
```

The official environment validation ran once. Final whitespace formatting and
root-manifest export were added afterward; the saved manifest records the hashes
of the actually executed revision explicitly. No environment replay was repeated
for those bookkeeping changes. No upstream patch edit/replay, install or .env
inspection. All commands used scripts/direct.py; zero real API calls/fees.

| Phase 1 engineering condition | Status |
|---|---|
| Five sequential online non-thinking tasks | Pass: reviewed calibration, not rerun |
| Usage/cost captured | Pass: reviewed calibration |
| Memory evolves across tasks | Pass: reviewed native inheritance/update evidence |
| Raw actions/observations captured | Pass: reviewed calibration and complete replay inputs |
| Task reset verified | Pass for the two documented full action paths at seed 42 |
| Targeted memory intervention technically possible | Pass for actor_rule_injection_mask, not global deletion/updater masking |

No H1–H4 conclusion, new paid-run authorization or candidate-mining start follows
from these engineering gates. Existing changes are retained; no Git commit.
