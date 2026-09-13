"""Incremental artifact sink and one-task harness; adapters own their memory logic."""

from __future__ import annotations

import os
import time
from dataclasses import asdict
from pathlib import Path
from typing import Protocol

from memory_validation.branching import NoIntervention
from memory_validation.provider import visible_message, visible_tools
from memory_validation.schemas import Manifest, MemorySnapshot, canonical, memory_diff, unavailable
from memory_validation.telemetry import Budget, BudgetExceeded, RunLedger, UsageTracker
from memory_validation.updates import UpdateJournal

JSON_ARTIFACTS = (
    "memory_before",
    "memory_injected",
    "trajectory",
    "evaluator",
    "updater_input",
    "updater_output",
    "memory_after",
    "memory_diff",
    "intervention_diff",
    "updater_memory_before",
    "updater_memory_after",
    "updater_memory_diff",
    "usage",
)
STREAM_ARTIFACTS = (
    "messages_visible",
    "model_calls",
    "actions",
    "observations",
    "isolation_events",
    "memory_injections",
)


class ArtifactSink:
    def __init__(self, directory: Path):
        # Exclusive creation prevents overwriting checkpoints or earlier runs.
        directory.mkdir(parents=True, exist_ok=False)
        self.directory = directory
        self._started_streams: set[str] = set()
        self._updater_before = None
        self._updater_finished = False
        self.updates = UpdateJournal(directory)
        for name in JSON_ARTIFACTS:
            self.write(name, unavailable("not reached or not exposed"))
        for name in STREAM_ARTIFACTS:
            (directory / f"{name}.jsonl").write_text(
                canonical(unavailable("not reached or not exposed")) + "\n"
            )

    def write(self, name: str, value):
        if name not in (*JSON_ARTIFACTS, "manifest"):
            raise ValueError("Unknown artifact name")
        destination = self.directory / f"{name}.json"
        temporary = destination.with_suffix(".json.tmp")
        with temporary.open("w", encoding="utf-8") as stream:
            stream.write(canonical(value) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(destination)

    def emit(self, name: str, value: dict):
        if name not in STREAM_ARTIFACTS:
            raise ValueError("Unknown stream name")
        if name == "messages_visible":
            metadata = {k: value[k] for k in ("call_id", "phase", "synthetic") if k in value}
            value = {**metadata, **visible_message(value)}
        if name == "model_calls":
            metadata = {k: value[k] for k in ("call_id", "phase", "synthetic", "event")}
            if value["event"] == "embedding_request":
                request = value["request"]
                value = {
                    **metadata,
                    "embedding_identity": value["embedding_identity"],
                    "request": {
                        k: request[k] for k in ("model", "dimensions", "encoding_format", "input")
                    },
                }
            elif value["event"] == "embedding_response":
                value = {
                    **metadata,
                    "embedding_identity": value["embedding_identity"],
                    "vectors": value["vectors"],
                }
            elif value["event"] == "request":
                request = value["request"]
                clean = {
                    k: request[k]
                    for k in ("model", "thinking", "temperature", "max_tokens", "stream")
                    if k in request
                }
                clean["messages"] = [visible_message(m) for m in request["messages"]]
                if "tools" in request:
                    clean["tools"] = visible_tools(request["tools"])
                value = {**metadata, "request": clean}
            elif value["event"] == "response":
                value = {**metadata, "message": visible_message(value["message"])}
            else:
                raise ValueError("Unknown model event")
        mode = "a" if name in self._started_streams else "w"
        with (self.directory / f"{name}.jsonl").open(mode, encoding="utf-8") as stream:
            stream.write(canonical(value) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        self._started_streams.add(name)

    def model_event(self, event: dict):
        self.emit("model_calls", event)
        if event["event"] == "response":
            self.emit("messages_visible", {**event, **event["message"]})

    def intervention(self, before: MemorySnapshot, after: MemorySnapshot):
        """Explicit full intervention states, never a retrieved subset."""
        self.write("intervention_diff", {"scope": "intervention", **memory_diff(before, after)})

    def updater_boundary(self, boundary: str, snapshot: MemorySnapshot):
        """Adapter supplies the full state at its actual updater boundary."""
        if self._updater_finished:
            raise ValueError("Updater interval already finished")
        if boundary == "before":
            if self._updater_before is not None or self.updates.sequence:
                raise ValueError("Only one updater interval supported per task")
            self._updater_before = snapshot
            self._legacy_update_id = self.begin_update("legacy_updater", snapshot)
        elif boundary != "after" or self._updater_before is None:
            raise ValueError("Invalid updater boundary")
        self.write("updater_memory_" + boundary, snapshot.to_dict())
        if boundary == "after":
            self.write(
                "updater_memory_diff",
                {"scope": "updater", **memory_diff(self._updater_before, snapshot)},
            )
            self._updater_finished = True
            self.finish_update(self._legacy_update_id, snapshot)

    def begin_update(self, phase, before=None, **metadata):
        update_id = self.updates.begin(phase, before, **metadata)
        if self.updates.sequence > 1:
            for name in (
                "updater_input",
                "updater_output",
                "updater_memory_before",
                "updater_memory_after",
                "updater_memory_diff",
            ):
                self.write(name, unavailable("multiple intervals: read updates.jsonl"))
        return update_id

    def finish_update(self, update_id, after=None, **metadata):
        self.updates.finish(update_id, after, **metadata)


class PairAdapter(Protocol):
    pair: str
    scientific_evidence: bool

    def setup_check(self) -> dict: ...
    def reset_task(self, task_id: str, seed: int | None = None) -> dict: ...
    def snapshot_memory(self) -> MemorySnapshot: ...
    def prepare_memory(self, checkpoint: MemorySnapshot, intervention) -> MemorySnapshot: ...
    def run_task(
        self, task_id: str, memory: MemorySnapshot, sink: ArtifactSink, usage: UsageTracker
    ) -> None: ...


def run_task(
    adapter: PairAdapter,
    manifest: Manifest,
    directory: Path,
    *,
    intervention=NoIntervention(),
    budget: Budget = Budget(),
    ledger: RunLedger | None = None,
) -> Manifest:
    if manifest.pair != adapter.pair:
        raise ValueError("Adapter/manifest pair mismatch")
    manifest.scientific_evidence = adapter.scientific_evidence
    if not adapter.scientific_evidence:
        manifest.execution_kind = getattr(adapter, "execution_kind", "infrastructure_test")
    manifest.intervention = {"type": type(intervention).__name__, **asdict(intervention)}
    sink = ArtifactSink(directory)
    usage = UsageTracker(
        budget,
        ledger,
        on_change=lambda value: sink.write("usage", value),
        on_event=sink.model_event,
    )
    started = time.monotonic()
    before = None
    sink.write("manifest", manifest.to_dict())
    try:
        if not adapter.setup_check().get("ready"):
            raise RuntimeError("Adapter setup is not ready")
        manifest.initial_environment = adapter.reset_task(
            manifest.task_id, manifest.environment_seed
        )
        before = adapter.snapshot_memory()
        sink.write("memory_before", before.to_dict())
        injected = adapter.prepare_memory(before, intervention)
        sink.write("memory_injected", injected.to_dict())
        # Only the adapter knows whether injection is a subset or full memory.
        # It must explicitly report intervention and updater boundaries.
        sink.write("manifest", manifest.to_dict())
        adapter.run_task(manifest.task_id, injected, sink, usage)
        manifest.status = "completed"
    except BudgetExceeded:
        manifest.status = "budget_exceeded"
        manifest.termination_category = "budget_or_accounting_stop"
    except KeyboardInterrupt:
        manifest.status = "interrupted"
        manifest.termination_category = "interrupted"
        raise KeyboardInterrupt() from None
    except Exception as error:
        # Raw exception text could contain credentials or evaluator internals.
        manifest.status = "failed"
        manifest.termination_category = {
            "ProviderError": "provider_error",
            "GeneratedCodeError": "unrecovered_generated_code_error",
            "SandboxError": "sandbox_facility_error",
        }.get(type(error).__name__, "execution_or_validation_error")
    finally:
        sink.updates.close_partial(
            manifest.status if manifest.status in ("interrupted", "budget_exceeded") else "failed"
        )
        summary = usage.summary()
        summary["wall_time_seconds"] = time.monotonic() - started
        summary["budget"] = asdict(budget)
        summary["memory_size_growth_bytes"] = unavailable("snapshot not available")
        try:
            after = adapter.snapshot_memory()
            sink.write("memory_after", after.to_dict())
            if before is not None:
                sink.write("memory_diff", {"scope": "overall", **memory_diff(before, after)})
                summary["memory_before_bytes"] = before.size_bytes
                summary["memory_after_bytes"] = after.size_bytes
                summary["memory_size_growth_bytes"] = after.size_bytes - before.size_bytes
        except Exception:
            if manifest.status == "completed":
                manifest.status = "failed"
        sink.write("usage", summary)
        sink.write("manifest", manifest.to_dict())
    return manifest
