"""Synthetic fixtures for the behavior-first tests.

Infrastructure only. They build an AppWorld-shaped checkout and ACE-shaped task
artifacts so the selector, corpus scheduler, card extractor and candidate
generator can be tested without the benchmark, without the ACE runtime, and
without any paid model call. Nothing here is scientific evidence.

The fixture checkout deliberately writes a *poisoned* `ground_truth/` for every
task: `metadata.json` is not valid JSON and `solution.py` raises when read. A
selector that touched reference material would fail loudly instead of silently
producing a different selection.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from memory_validation.pipeline import ArtifactSink
from memory_validation.schemas import MemorySnapshot

CANARY = "appworld:fixture:00000000-0000-0000-0000-000000000000"

PLAYBOOK_K0 = """## STRATEGIES AND HARD RULES
[shr-00001] Always look at API specifications before calling an API.

## APIs TO USE FOR SPECIFIC INFORMATION
[api-00001] Use supervisor.show_profile for account details.

## OTHERS
[oth-00001] Call supervisor.complete_task() when the task is done.
"""

DEFAULT_APPS = (
    "amazon",
    "file_system",
    "gmail",
    "phone",
    "simple_note",
    "spotify",
    "todoist",
    "venmo",
)

#: Eligible instructions: no cheapest/best/exhaustive-comparison language.
ELIGIBLE_INSTRUCTIONS = (
    "How many playlists do I have in Spotify?",
    "Send a message to my roommate on Venmo about the rent.",
    "Search my Gmail for the invoice from Amazon and save it to my file system.",
    "Add the movie I watched last night to my Todoist list.",
    "Find the person who sent me the payment request on Venmo and send them a note.",
    "Show me the songs I liked in Spotify and add them to a Simple Note.",
    "Which Amazon orders arrived at my phone number last week?",
    "List the people I follow on Spotify.",
    "Check my Gmail for the invitation and reply to the sender.",
    "What is my Todoist task for tomorrow?",
    "Send the file from my file system to my friend on Gmail.",
    "Show the balance on my Venmo account.",
    "If there is no invoice in Gmail, look in the file system.",
    "Add a task to my Todoist list and share it with my roommate.",
    "Find the songs in my Spotify playlist that I have not listened to.",
    "Send money to the person named in my last Venmo request.",
)

#: Instructions the registered BF-0 rules must exclude.
BANNED_INSTRUCTIONS = (
    "Order whichever option is cheaper on Amazon.",
    "Find the cheapest flight in my Gmail and book it.",
    "Compare all the options in the file system and pick the best deal.",
    "Determine the exhaustive list of songs in my Spotify library.",
    "Prove that this is the optimal order in my Amazon cart.",
    "Rank every candidate in my Todoist list.",
    "Show me all possible combinations of Amazon orders.",
)


def k0_snapshot() -> MemorySnapshot:
    """A stand-in for the official ACE initial playbook, same artifact shape."""

    return MemorySnapshot.capture(
        {"playbook": PLAYBOOK_K0, "next_global_id": "oth-00002"},
        {"format": "official_ace_playbook_and_id", "role": "K0"},
    )


def learned_snapshot(entries=("oth-00002",)) -> MemorySnapshot:
    """K0 plus the synthetic entries a fake run 'learned'."""

    extra = "\n".join(
        f"[{entry}] Synthetic learned entry {entry} about spotify search APIs." for entry in entries
    )
    return MemorySnapshot.capture(
        {"playbook": f"{PLAYBOOK_K0}{extra}\n", "next_global_id": f"oth-{len(entries) + 2:05d}"},
        {"format": "official_ace_playbook_and_id", "role": "K0"},
    )


def build_data_root(
    root: Path,
    tasks,
    *,
    apps=DEFAULT_APPS,
    version: str = "0.1.0-fixture",
    poison_ground_truth: bool = True,
) -> Path:
    """Write an AppWorld-shaped checkout.

    `tasks` is a sequence of `{"task_id", "instruction", "split"}` mappings.
    """

    root = Path(root)
    (root / "tasks").mkdir(parents=True, exist_ok=True)
    (root / "datasets").mkdir(parents=True, exist_ok=True)
    (root / "base_dbs").mkdir(parents=True, exist_ok=True)
    (root / "version.txt").write_text(f"{version}\n", encoding="utf-8")

    database = root / "base_dbs" / "api_docs.db"
    connection = sqlite3.connect(database)
    try:
        connection.execute("create table api_docs (app_name_ text, api_name text)")
        connection.executemany(
            "insert into api_docs values (?, ?)",
            [(app, f"{app}_api_{index}") for app in apps for index in range(1, 4)],
        )
        connection.commit()
    finally:
        connection.close()

    splits: dict[str, list[str]] = {}
    for task in tasks:
        task_dir = root / "tasks" / task["task_id"]
        (task_dir / "dbs").mkdir(parents=True, exist_ok=True)
        (task_dir / "dbs" / "fixture.jsonl").write_text("", encoding="utf-8")
        (task_dir / "specs.json").write_text(
            json.dumps(
                {
                    "instruction": task["instruction"],
                    "supervisor": {"first_name": "Fixture", "last_name": "User"},
                    "datetime": "2023-05-18T12:00:00",
                    "db_version": "0.1.0",
                    "canary_string": CANARY,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        if poison_ground_truth:
            ground_truth = task_dir / "ground_truth"
            ground_truth.mkdir(parents=True, exist_ok=True)
            (ground_truth / "metadata.json").write_text("{ not json at all", encoding="utf-8")
            (ground_truth / "solution.py").write_text(
                "raise RuntimeError('ground truth must never be read by BF-0')\n", encoding="utf-8"
            )
            (ground_truth / "test_data.json").write_text("[not json]", encoding="utf-8")
        splits.setdefault(task["split"], []).append(task["task_id"])

    for split, task_ids in splits.items():
        (root / "datasets" / f"{split}.txt").write_text(
            "\n".join(sorted(task_ids)) + "\n", encoding="utf-8"
        )
    return root


def default_tasks(
    families: int = 16, siblings: int = 3, split_cycle=("train", "dev")
) -> list[dict]:
    """A diverse, eligible task set: one instruction family per scenario."""

    tasks = []
    for index in range(families):
        family = f"{index:07x}"[:7]
        for sibling in range(1, siblings + 1):
            instruction = ELIGIBLE_INSTRUCTIONS[(index + sibling) % len(ELIGIBLE_INSTRUCTIONS)]
            tasks.append(
                {
                    "task_id": f"{family}_{sibling}",
                    "instruction": instruction,
                    "split": split_cycle[index % len(split_cycle)],
                }
            )
    return tasks


def selection_manifest(tasks, digest_source: str = "fixture") -> dict:
    """A minimal but schema-valid BF-0 manifest for corpus tests."""

    return {
        "selector_version": "bf0-behavior-selector-v1",
        "status": "selected",
        "dataset": {"data_root": digest_source, "task_count": len(tasks)},
        "counts": {"selected": len(tasks)},
        "tasks": [
            {
                "rank": rank,
                "task_id": task["task_id"],
                "family": task["task_id"].split("_")[0],
                "split": task.get("split"),
                "instruction": task["instruction"],
                "features": {"fixture": True},
            }
            for rank, task in enumerate(tasks)
        ],
    }


def scripted_trajectory(
    *,
    actions,
    public_events,
    success: bool = True,
    report: str = ">> Passed Requirement\nassert answers match.",
    llm_calls: int = 6,
    cost_usd: float = 0.02,
) -> dict:
    """Artifact payloads for one scripted task run."""

    return {
        "actions": [
            {"step": index, "code": code, "synthetic": False} for index, code in enumerate(actions)
        ],
        "observations": [{"step": index, **event} for index, event in enumerate(public_events)],
        "evaluator": {
            "tracker": {"success": success, "num_tests": 2, "difficulty": 2},
            "report": report,
            "agent_completed": True,
        },
        "usage": {
            "llm_calls": llm_calls,
            "accounted_cost_usd": cost_usd,
            "estimated_cost_usd": cost_usd,
            "provider_reported_cost_usd": None,
            "price_table": {"version": "fixture"},
            "memory_size_growth_bytes": 64,
        },
    }


def write_task_artifacts(
    directory: Path,
    *,
    task_id: str,
    snapshot_before: MemorySnapshot,
    snapshot_after: MemorySnapshot,
    script,
    task_status: str = "completed",
    termination_category: str | None = None,
    instruction: str | None = None,
    selection_features=None,
) -> Path:
    """Write a complete ACE-shaped task artifact directory."""

    directory = Path(directory)
    sink = ArtifactSink(directory)
    sink.write(
        "manifest",
        {
            "task_id": task_id,
            "status": task_status,
            "termination_category": termination_category,
            "synthetic": True,
            "scientific_evidence": False,
            "pair": "ace_appworld",
        },
    )
    sink.write("memory_before", snapshot_before.to_dict())
    sink.write("memory_after", snapshot_after.to_dict())
    sink.write("evaluator", {"status": "available", "data": script["evaluator"]})
    sink.write("usage", {"status": "available", "data": script["usage"]})
    for action in script["actions"]:
        sink.emit("actions", action)
    for observation in script["observations"]:
        sink.emit("observations", observation)
    sink.updates.close_partial("fixture")
    if instruction is not None:
        (directory / "corpus_task.json").write_text(
            json.dumps(
                {
                    "task_id": task_id,
                    "task_status": task_status,
                    "instruction": instruction,
                    "features": selection_features,
                    "reset": {
                        "verified": True,
                        "k0_sha256": snapshot_before.sha256,
                        "memory_before_sha256": snapshot_before.sha256,
                    },
                    "public_calls": {"public_api_responses": len(script["observations"])},
                }
            )
            + "\n",
            encoding="utf-8",
        )
    return directory


def fake_runner(
    *,
    script,
    before=None,
    after=None,
    task_status: str = "completed",
    raises=None,
    ledger_add_usd: float = 0.0,
    ledger_uncertain: bool = False,
    observe=None,
):
    """A stand-in for `ace_appworld.run_task` with the same keyword contract.

    It writes the same artifact set the adapter writes, so the corpus scheduler,
    reset proof, counting and index logic run for real. `observe` receives each
    call for assertions.
    """

    def runner(
        task_id,
        directory,
        transport,
        *,
        checkpoint=None,
        ledger=None,
        synthetic=False,
        remote_url=None,
        task_index=0,
        verify_before=None,
    ):
        snapshot_before = before if before is not None else checkpoint
        snapshot_after = after if after is not None else checkpoint
        write_task_artifacts(
            directory,
            task_id=task_id,
            snapshot_before=snapshot_before,
            snapshot_after=snapshot_after,
            script=script,
            task_status=task_status,
        )
        if verify_before is not None:
            verify_before(snapshot_before)
        if ledger is not None:
            ledger.calls += script["usage"]["llm_calls"]
            ledger.cost_usd += ledger_add_usd
            if ledger_uncertain:
                ledger.uncertain = True
        if observe is not None:
            observe(
                {
                    "task_id": task_id,
                    "task_index": task_index,
                    "directory": directory,
                    "checkpoint_sha256": None if checkpoint is None else checkpoint.sha256,
                    "synthetic": synthetic,
                }
            )
        if raises is not None:
            raise raises
        return None, type("Manifest", (), {"status": task_status})()

    return runner
