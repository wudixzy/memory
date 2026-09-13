"""BF-1 — isolated-K0 behavioral corpus over the registered ACE no-GT loop.

`docs/31` section 4. Every selected task is run once, from the *exact* official
ACE initial playbook `K0`, through the native
Generator -> AppWorld -> Reflector -> Curator path that
`memory_validation.adapters.ace_appworld.run_task` already provides. This module
adds no memory logic, no alternate prompt and no classifier: it schedules tasks,
proves the reset, counts public API traffic, and preserves whatever happened.

Guarantees enforced here:

* one fresh agent, world and guest per task — `run_task` constructs them, and
  this driver always hands it the *same* `K0` checkpoint, never the previous
  task's learned playbook;
* the reset is verified, not assumed: after each task the `memory_before`
  artifact is compared to the `K0` digest, and a mismatch stops the corpus
  (`K0Mismatch`) instead of continuing on unknown playbook state;
* task outcomes are preserved as-is (failed, `max_steps_without_update`,
  evaluator-false). Nothing is rerun to obtain a success;
* the run ledger is shared across tasks with a hard USD cap; hitting it stops
  the corpus cleanly and keeps every artifact written so far;
* public API responses and failed public calls are counted separately from LLM
  calls, from executor events, never from model text.

Only a task id, the `K0` checkpoint and a transport are handed to the adapter.
Selection features, evaluator output and every research-side artifact stay
outside the Generator/Reflector/Curator context (`memory_behavior.boundary`).
"""

from __future__ import annotations

import json
from contextlib import ExitStack
from dataclasses import asdict
from pathlib import Path

from memory_behavior import measure
from memory_validation.schemas import MemorySnapshot
from memory_validation.telemetry import Budget, BudgetExceeded, RunLedger

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CORPUS_DIR = ROOT / "artifacts/ace-appworld-behavior-k0-v1"
CORPUS_VERSION = "bf1-isolated-k0-corpus-v1"
REQUIRED_SELECTOR_VERSION = "bf0-behavior-selector-v1"
MAX_GENERATOR_STEPS = 40

#: `docs/31` section 11: USD 5 for the isolated corpus, with the registered
#: per-call reservation unchanged (1 MiB input, 8192 output). The per-task cost
#: guard is tightened from the registered 3 USD batch value to 0.75 USD — above
#: the 0.098 USD largest real ACE task measured so far (`docs/24`) and above a
#: full 40-step task, so it stops runaway tasks without truncating normal ones.
CORPUS_BUDGET = Budget(
    max_calls_per_task=42,
    max_calls_per_run=42 * 30,
    max_input_tokens_per_task=4194304,
    max_output_tokens_per_task=344064,
    max_cost_usd_per_task=0.75,
    max_cost_usd_per_run=5.0,
    max_cost_cny_per_task=0,
    max_cost_cny_per_run=0,
)

#: Statuses the adapter writes when a task ran to a real end, success or not.
#: These are preserved as task outcomes; anything else stops the corpus.
TASK_OUTCOME_STATUSES = (
    "completed",
    "failed",
    "max_steps_without_update",
    "budget_exceeded",
    "interrupted",
)

#: Failure types that mean the local execution facility broke rather than the
#: task failing. They stop the corpus (fail closed) and are never auto-retried.
INFRASTRUCTURE_FAILURE_TYPES = ("SandboxError", "ProviderError", "K0Mismatch")

STOP_STATUSES = ("completed", "stopped_budget", "stopped_infrastructure", "interrupted")


class CorpusError(RuntimeError):
    """Raised when the corpus cannot be started or continued safely."""


class SelectionMismatch(CorpusError):
    """Raised when the frozen selection is not the registered one."""


class K0Mismatch(CorpusError):
    """Raised when a task did not start from the official `K0` playbook."""


def save_json(path: Path, value) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def load_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def initial_playbook_text() -> str:
    from memory_validation.adapters.ace_appworld import initial_playbook

    return initial_playbook()


def k0_checkpoint() -> MemorySnapshot:
    """The official ACE initial playbook plus its `next_global_id`, unchanged.

    Derived from the pinned `appworld_initial_playbook.txt` and the upstream
    `get_next_global_id`, i.e. the same state a fresh native agent starts from.
    """

    from appworld_experiments.code.ace.playbook import get_next_global_id

    playbook = initial_playbook_text()
    return MemorySnapshot.capture(
        {"playbook": playbook, "next_global_id": get_next_global_id(playbook)},
        {"format": "official_ace_playbook_and_id", "role": "K0"},
    )


def registered_plan(selection_path: Path | str | None = None) -> dict:
    """Unpaid plan view. Imports no AppWorld runtime and makes no model call."""

    from memory_validation.adapters.ace_appworld import PIN, PRICES, verify_pin

    verify_pin()
    playbook = initial_playbook_text()
    selection = None
    if selection_path is not None:
        manifest = load_json(selection_path)
        selection = {
            "path": str(Path(selection_path)),
            "selector_version": manifest.get("selector_version"),
            "status": manifest.get("status"),
            "tasks": len(manifest.get("tasks", [])),
            "digest": measure.selection_digest(manifest),
        }
    return {
        "corpus_version": CORPUS_VERSION,
        "mode": "plan",
        "model_calls": 0,
        "network": "none in plan mode",
        "upstream_commit": PIN,
        "initial_playbook_sha256": measure.sha256_text(playbook),
        "initial_playbook_bytes": len(playbook.encode("utf-8")),
        "provider": "deepseek",
        "request_model": "deepseek-v4-flash",
        "accepted_response_model": "deepseek-flash",
        "thinking": False,
        "temperature": 0,
        "max_generator_steps": MAX_GENERATOR_STEPS,
        "native_path": "Generator -> AppWorld -> Reflector -> Curator (official no-GT)",
        "reset_policy": (
            "the exact K0 checkpoint is restored before every task and each task's "
            "memory_before digest must equal the K0 digest; mismatch stops the corpus"
        ),
        "isolation": {
            "per_task": "fresh native agent, world and guest",
            "carried_between_tasks": ["task id", "K0 checkpoint", "run ledger", "transport"],
            "never_in_ace_context": [
                "selection features and exclusions",
                "evaluator results of other tasks",
                "strategy cards and candidate records",
            ],
        },
        "budget": asdict(CORPUS_BUDGET),
        "prices": asdict(PRICES),
        "selection": selection
        or {
            "path": None,
            "required": True,
            "note": "pass --selection with the frozen BF-0 manifest",
        },
        "output": str(DEFAULT_CORPUS_DIR),
        "authorization": "explicit --execute required; --offline runs the synthetic wiring check",
        "scientific_evidence": False,
    }


def reset_proof(task_dir: Path, k0: MemorySnapshot) -> dict:
    """Compare the artifact the adapter wrote *before* the Generator with K0."""

    task_dir = Path(task_dir)
    before = measure.read_available_json(task_dir / "memory_before.json")
    observed = before.get("sha256") if isinstance(before, dict) else None
    raw = before.get("raw") if isinstance(before, dict) else None
    expected_next = k0.raw.get("next_global_id")
    observed_next = raw.get("next_global_id") if isinstance(raw, dict) else None
    return {
        "artifact": "memory_before.json",
        "k0_sha256": k0.sha256,
        "memory_before_sha256": observed,
        "expected_next_global_id": expected_next,
        "observed_next_global_id": observed_next,
        "verified": bool(observed == k0.sha256 and observed_next == expected_next),
        "rule": (
            "memory_before is written by the adapter before the first Generator call; "
            "a mismatch means the task did not start from official K0"
        ),
    }


def _playbook_of(snapshot) -> str:
    raw = (snapshot or {}).get("raw")
    return raw.get("playbook", "") if isinstance(raw, dict) else ""


def _task_record(
    task_dir: Path,
    *,
    index: int,
    entry: dict,
    proof: dict,
    ledger_before: dict,
    ledger_after: dict,
    relative_to: Path,
) -> dict:
    """Compact per-task record: paths, digests, counts and costs only."""

    manifest = measure.read_available_json(task_dir / "manifest.json") or {}
    usage = measure.read_available_json(task_dir / "usage.json") or {}
    evaluator = measure.read_available_json(task_dir / "evaluator.json")
    observations = measure.read_jsonl(task_dir / "observations.jsonl")
    digests = measure.artifact_digests(task_dir)
    public = measure.public_call_counts(observations)
    before = measure.read_available_json(task_dir / "memory_before.json")
    after = measure.read_available_json(task_dir / "memory_after.json")
    return {
        "index": index,
        "task_id": entry["task_id"],
        "path": str(task_dir.relative_to(relative_to)),
        "task_status": manifest.get("status", "missing_manifest"),
        "termination_category": manifest.get("termination_category"),
        "evaluator_success": measure.evaluator_success(evaluator),
        "agent_completed": (evaluator or {}).get("agent_completed"),
        "instruction": entry.get("instruction"),
        "instruction_source": "bf0 selection manifest (task-visible specification)",
        "features": entry.get("features"),
        "reset": proof,
        "artifacts": {
            "count": digests["count"],
            "combined_sha256": digests["combined_sha256"],
            "digests": digests["files"],
        },
        "public_calls": public,
        "llm_calls": usage.get("llm_calls"),
        "cost": {
            "accounted_usd_this_task": round(
                ledger_after["cost_usd"] - ledger_before["cost_usd"], 9
            ),
            "accounted_usd_run_total": ledger_after["cost_usd"],
            "ledger_calls_this_task": ledger_after["calls"] - ledger_before["calls"],
            "estimated_cost_usd": usage.get("estimated_cost_usd"),
            "cost_basis": (
                "provider_reported"
                if usage.get("provider_reported_cost_usd") is not None
                else "price_table_estimate"
            ),
            "price_table": usage.get("price_table"),
        },
        "memory": {
            "before_sha256": (before or {}).get("sha256"),
            "after_sha256": (after or {}).get("sha256"),
            "changed": (before or {}).get("sha256") != (after or {}).get("sha256"),
            "entries_before": len(measure.playbook_entries(_playbook_of(before))),
            "entries_after": len(measure.playbook_entries(_playbook_of(after))),
            "size_growth_bytes": usage.get("memory_size_growth_bytes"),
        },
    }


def _index_of(records) -> dict:
    """Manifest/path/digest/cost index; never raw artifact payloads."""

    return {
        "corpus_version": CORPUS_VERSION,
        "note": (
            "raw task artifacts stay under artifacts/; this index holds paths, digests and costs"
        ),
        "tasks": [
            {
                "index": record["index"],
                "task_id": record["task_id"],
                "path": record["path"],
                "task_status": record["task_status"],
                "evaluator_success": record["evaluator_success"],
                "reset_verified": record["reset"]["verified"],
                "artifacts_combined_sha256": record["artifacts"]["combined_sha256"],
                "artifact_count": record["artifacts"]["count"],
                "public_api_responses": record["public_calls"]["public_api_responses"],
                "failed_public_calls": record["public_calls"]["failed_public_calls"],
                "llm_calls": record["llm_calls"],
                "accounted_usd_this_task": record["cost"]["accounted_usd_this_task"],
            }
            for record in records
        ],
    }


def run_corpus(
    output_dir: Path | str,
    selection_path: Path | str,
    transport,
    *,
    runner=None,
    k0: MemorySnapshot | None = None,
    synthetic: bool = False,
    remote_url: str | None = None,
    resume: bool = False,
    verify: bool = True,
) -> dict:
    """Run the frozen selection once, isolated to `K0`, and return the state.

    `runner` exists so the scheduling, reset proof, ledger and artifact
    bookkeeping can be exercised without paid model calls. The default is the
    registered adapter; no other production path is used.
    """

    output = Path(output_dir)
    selection_path = Path(selection_path)
    selection = load_json(selection_path)
    if selection.get("selector_version") != REQUIRED_SELECTOR_VERSION:
        raise SelectionMismatch("selection manifest was produced by a different selector version")
    if selection.get("status") != "selected":
        raise SelectionMismatch(f"selection status is {selection.get('status')!r}, not 'selected'")
    entries = selection.get("tasks") or []
    if not entries:
        raise SelectionMismatch("selection manifest contains no tasks")
    digest = measure.selection_digest(selection)

    if runner is None and verify and not synthetic:
        from memory_validation.adapters.ace_appworld import verify_pin

        verify_pin()
    if k0 is None:
        k0 = k0_checkpoint()

    ledger = RunLedger()
    records: list[dict] = []
    start = 0
    if output.exists():
        if not resume:
            raise CorpusError("output already exists; no overwrite and no task rerun")
        previous = load_json(output / "corpus.json")
        if previous.get("status") not in (
            "stopped_budget",
            "stopped_infrastructure",
            "interrupted",
        ):
            raise CorpusError(f"corpus status {previous.get('status')!r} cannot be resumed")
        if previous["selection"]["digest"] != digest:
            raise SelectionMismatch("resume selection digest differs from the recorded one")
        if previous["k0"]["sha256"] != k0.sha256:
            raise K0Mismatch("resume K0 checkpoint differs from the recorded one")
        records = previous["tasks"]
        ledger = RunLedger(**previous["ledger"])
        start = len(records)
    else:
        output.mkdir(parents=True, exist_ok=False)
        save_json(output / "selection.json", selection)
        save_json(
            output / "k0_checkpoint.json",
            {
                "sha256": k0.sha256,
                "raw": k0.raw,
                "metadata": k0.metadata,
                "source": (
                    "third_party/ace-appworld/experiments/playbooks/appworld_initial_playbook.txt"
                ),
            },
        )

    state = {
        "corpus_version": CORPUS_VERSION,
        "status": "running",
        "mode": "offline_synthetic" if synthetic else "real",
        "scientific_evidence": False,
        "selection": {
            "path": str(selection_path),
            "digest": digest,
            "selector_version": selection["selector_version"],
            "dataset": selection.get("dataset"),
            "tasks": len(entries),
        },
        "k0": {
            "sha256": k0.sha256,
            "next_global_id": k0.raw.get("next_global_id"),
            "source": (
                "third_party/ace-appworld/experiments/playbooks/appworld_initial_playbook.txt"
            ),
        },
        "budget": asdict(CORPUS_BUDGET),
        "stop_reason": None,
        "active_task": None,
        "ledger": asdict(ledger),
        "tasks": records,
    }
    save_json(output / "corpus.json", state)

    def stop(status: str, reason: str) -> None:
        state["status"], state["stop_reason"] = status, reason
        state["active_task"] = None
        state["ledger"] = asdict(ledger)
        save_json(output / "corpus.json", state)
        save_json(output / "index.json", _index_of(records))

    with ExitStack() as stack:
        if runner is None:
            from memory_validation.adapters.ace_appworld import run_task as native_runner

            runner = native_runner
            if remote_url is None:
                from memory_validation.adapters.ace_execution import RemoteAPIs

                remote_url = stack.enter_context(RemoteAPIs()).url
        for index in range(start, len(entries)):
            entry = entries[index]
            task_id = entry["task_id"]
            if ledger.uncertain:
                stop("stopped_infrastructure", "unknown_prior_accounting")
                break
            if ledger.cost_usd >= CORPUS_BUDGET.max_cost_usd_per_run:
                stop("stopped_budget", "run_cost_cap_reached")
                break
            task_dir = output / "tasks" / f"{index:02d}_{task_id}"
            if task_dir.exists():
                stop("stopped_infrastructure", "task_directory_exists_no_rerun")
                break
            state["active_task"] = {
                "index": index,
                "task_id": task_id,
                "path": str(task_dir.relative_to(output)),
            }
            save_json(output / "corpus.json", state)
            ledger_before = {"cost_usd": ledger.cost_usd, "calls": ledger.calls}
            error: BaseException | None = None

            def verify_before(actual: MemorySnapshot) -> None:
                """Fail before Generator if this fresh task is not exact K0."""

                if actual.sha256 != k0.sha256 or actual.raw != k0.raw:
                    raise K0Mismatch(
                        "adapter snapshot before Generator differs from the registered K0"
                    )

            try:
                runner(
                    task_id,
                    task_dir,
                    transport,
                    checkpoint=k0,
                    ledger=ledger,
                    synthetic=synthetic,
                    remote_url=remote_url,
                    task_index=index,
                    verify_before=verify_before,
                )
            except KeyboardInterrupt:
                proof = reset_proof(task_dir, k0)
                if proof["memory_before_sha256"] is not None:
                    records.append(
                        _task_record(
                            task_dir,
                            index=index,
                            entry=entry,
                            proof=proof,
                            ledger_before=ledger_before,
                            ledger_after=asdict(ledger),
                            relative_to=output,
                        )
                    )
                stop("interrupted", "keyboard_interrupt")
                raise
            except Exception as caught:  # classified below, never swallowed
                error = caught
            proof = reset_proof(task_dir, k0)
            record = _task_record(
                task_dir,
                index=index,
                entry=entry,
                proof=proof,
                ledger_before=ledger_before,
                ledger_after=asdict(ledger),
                relative_to=output,
            )
            records.append(record)
            save_json(task_dir / "corpus_task.json", record)
            state["tasks"] = records
            state["active_task"] = None
            state["ledger"] = asdict(ledger)
            save_json(output / "corpus.json", state)
            if not proof["verified"]:
                reason = (
                    "k0_reset_mismatch"
                    if proof["memory_before_sha256"]
                    else "no_memory_before_artifact"
                )
                stop("stopped_infrastructure", reason)
                break
            if isinstance(error, BudgetExceeded):
                stop("stopped_budget", "task_budget_exceeded")
                break
            if error is not None:
                category = type(error).__name__
                if record["task_status"] in TASK_OUTCOME_STATUSES:
                    # A preserved task outcome (failed task, exhausted steps).
                    # It stays in the corpus and the next task starts from K0.
                    continue
                if category in INFRASTRUCTURE_FAILURE_TYPES:
                    stop("stopped_infrastructure", category)
                    break
                stop("stopped_infrastructure", f"unclassified:{category}")
                break
        else:
            state["status"] = "completed"
    stop(state["status"], state["stop_reason"])
    return state
