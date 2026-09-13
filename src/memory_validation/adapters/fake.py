"""Synthetic deterministic fixture. Never an AutoManual implementation or evidence."""

from memory_validation.branching import mask_mapping_memory
from memory_validation.isolation import Evidence, adaptive_input
from memory_validation.schemas import MemorySnapshot, available
from memory_validation.telemetry import CallUsage


class FakeAdapter:
    pair = "fake_fixture"
    scientific_evidence = False

    def __init__(self):
        self.memory = {"fixture-rule": "Synthetic fixture: inspect the room."}
        self.state = {}

    def setup_check(self) -> dict:
        return {"ready": True, "network": False, "scientific_evidence": False}

    def reset_task(self, task_id: str, seed: int | None = None) -> dict:
        self.state = {"task_id": task_id, "seed": seed, "position": "room", "steps": 0}
        return dict(self.state)

    def snapshot_memory(self) -> MemorySnapshot:
        return MemorySnapshot.capture(
            self.memory, [{"memory_id": key, "kind": "synthetic_fixture"} for key in self.memory]
        )

    def prepare_memory(self, checkpoint, intervention):
        return mask_mapping_memory(checkpoint, intervention)

    def run_task(self, task_id, memory, sink, usage):
        # All text and usage below are explicitly synthetic, generated without an LLM.
        sink.intervention(self.snapshot_memory(), memory)
        self.memory = memory.raw
        usage.before_call(8, 2)
        actor_id = usage.new_call_id()
        message = {"role": "assistant", "content": "Synthetic fixture: inspect room"}
        sink.model_event(
            {
                "call_id": actor_id,
                "phase": "actor",
                "synthetic": True,
                "event": "response",
                "message": message,
            }
        )
        usage.record(
            CallUsage(
                8,
                2,
                0,
                0,
                provider="fake",
                requested_model="fixture",
                resolved_model="fixture",
                provider_reported_cost_usd=0,
                call_id=actor_id,
                phase="actor",
                synthetic=True,
            )
        )
        self.state["steps"] += 1
        action = {"action": "inspect", "step": 1}
        observation = {"observation": "Synthetic room contains a box", "step": 1}
        sink.emit("actions", action)
        sink.emit("observations", observation)
        trace = [action, observation]
        sink.write("trajectory", available(trace))
        # Evaluator data only goes to its artifact. Updater input is constructed
        # from explicitly actor-visible observations, never from evaluator output.
        evaluator = Evidence({"success": True, "hidden_target": "fixture-only"}, "evaluator_only")
        sink.write("evaluator", available(evaluator.value))
        updater = adaptive_input(
            [Evidence({"memory": memory.raw, "trajectory": trace}, "actor_visible")]
        )
        sink.write("updater_input", available(updater))
        usage.before_call(12, 3)
        sink.updater_boundary("before", self.snapshot_memory())
        updater_id = usage.new_call_id()
        sink.model_event(
            {
                "call_id": updater_id,
                "phase": "updater",
                "synthetic": True,
                "event": "response",
                "message": {"role": "assistant", "content": "Synthetic update"},
            }
        )
        usage.record(
            CallUsage(
                12,
                3,
                4,
                0,
                provider="fake",
                requested_model="fixture",
                resolved_model="fixture",
                provider_reported_cost_usd=0,
                call_id=updater_id,
                phase="updater",
                synthetic=True,
            )
        )
        self.memory = memory.raw
        self.memory[f"seen-{task_id}"] = observation["observation"]
        sink.write("updater_output", available({"operation": "fixture_add", "task": task_id}))
        sink.updater_boundary("after", self.snapshot_memory())
