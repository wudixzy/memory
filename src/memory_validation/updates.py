"""Append-only update intervals. Snapshots are full native state, not retrieval text."""

from __future__ import annotations

import json
import os
from pathlib import Path

from memory_validation.schemas import available, canonical, memory_diff, unavailable


class UpdateJournal:
    def __init__(self, directory: Path):
        self.path = directory / "updates.jsonl"
        self.path.touch(exist_ok=False)
        self.sequence = 0
        self.active = {}

    def append(self, event):
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(canonical(event) + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    def begin(self, phase, before=None, *, call_id=None, input_ref=None):
        if not isinstance(phase, str) or not phase:
            raise ValueError("Update phase required")
        self.sequence += 1
        update_id = f"update_{self.sequence:06d}"
        event = {
            "schema_version": "1.2",
            "event": "begin",
            "update_id": update_id,
            "sequence": self.sequence,
            "phase": phase,
            "call_id": call_id,
            "input_ref": unavailable() if input_ref is None else available(input_ref),
            "before": unavailable() if before is None else before.to_dict(),
            "status": "running",
        }
        event = json.loads(canonical(event))  # Detach mutable input reference metadata too.
        self.append(event)
        self.active[update_id] = (event, before)
        return update_id

    def finish(self, update_id, after=None, *, status="completed", output_ref=None, lineage=None):
        if status not in ("completed", "failed", "interrupted", "budget_exceeded"):
            raise ValueError("Invalid update terminal status")
        event, before = self.active[update_id]
        self.append(
            {
                **event,
                "event": "end",
                "status": status,
                "after": unavailable() if after is None else after.to_dict(),
                "output_ref": unavailable() if output_ref is None else available(output_ref),
                "diff": unavailable("missing actual boundary")
                if before is None or after is None
                else available({"scope": "updater_interval", **memory_diff(before, after)}),
                "rule_id_correspondence": unavailable("not a recorded renumbering")
                if lineage is None
                else available(lineage),
            }
        )
        del self.active[update_id]

    def close_partial(self, status):
        for update_id in list(self.active):
            self.finish(update_id, status=status)


def read_updates(directory: Path):
    """Read 1.2 events or an old single interval without inventing missing boundaries."""
    path = directory / "updates.jsonl"
    if path.exists():
        intervals = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            event = json.loads(line)
            key = event["update_id"]
            if event["event"] == "begin":
                if key in intervals:
                    raise ValueError("Duplicate update ID")
                intervals[key] = {
                    **event,
                    "after": unavailable("interval not closed"),
                    "diff": unavailable("interval not closed"),
                    "output_ref": unavailable("interval not closed"),
                }
            elif event["event"] == "end" and key in intervals:
                if intervals[key]["event"] == "end":
                    raise ValueError("Duplicate interval end")
                intervals[key] = event
            else:
                raise ValueError("Invalid update journal")
        return list(intervals.values())

    def old(name):
        file = directory / (name + ".json")
        return json.loads(file.read_text()) if file.exists() else unavailable("legacy absent")

    before, after = old("updater_memory_before"), old("updater_memory_after")
    if before.get("status") != "available" and after.get("status") != "available":
        return []
    return [
        {
            "update_id": "legacy_single",
            "sequence": 1,
            "phase": "legacy_unspecified",
            "call_id": None,
            "status": "legacy_status_unavailable",
            "before": before,
            "after": after,
            "diff": old("updater_memory_diff"),
            "input_ref": old("updater_input"),
            "output_ref": old("updater_output"),
            "schema_version": "legacy",
        }
    ]
