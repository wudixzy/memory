"""Small JSON schemas, immutable raw snapshots, and explicit availability."""

from __future__ import annotations

import difflib
import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


def unavailable(reason: str = "not exposed by adapter") -> dict:
    return {"status": "unavailable", "reason": reason}


def available(value: Any) -> dict:
    return {"status": "available", "data": value}


@dataclass(frozen=True)
class ModelConfig:
    provider: str = "deepseek"
    model: str = "deepseek-v4-flash"
    thinking: bool = False
    temperature: float = 0
    evaluation_type: str = "common-backbone"

    def __post_init__(self):
        if (self.provider, self.model, self.thinking, self.temperature, self.evaluation_type) != (
            "deepseek",
            "deepseek-v4-flash",
            False,
            0,
            "common-backbone",
        ) or self.thinking is not False:
            raise ValueError("Phase-1 backbone policy violation")


@dataclass
class Manifest:
    run_id: str
    pair: str
    task_id: str
    task_order_index: int = 0
    environment_seed: int | None = None
    model_config: ModelConfig = field(default_factory=ModelConfig)
    upstream_repo: Any = field(default_factory=unavailable)
    upstream_commit: Any = field(default_factory=unavailable)
    benchmark_repo: Any = field(default_factory=unavailable)
    benchmark_commit: Any = field(default_factory=unavailable)
    environment_lock: Any = field(default_factory=unavailable)
    original_model_configuration: Any = field(default_factory=unavailable)
    patches: list = field(default_factory=list)
    memory_mode: str = "online"
    evaluator_leakage: bool | None = None
    isolation_status: str = "not_verified"
    scientific_evidence: bool = False
    synthetic: bool | None = None
    mechanism_fidelity: str = "not_verified"
    feedback_protocol: Any = field(default_factory=unavailable)
    execution_restrictions: list = field(default_factory=list)
    execution_kind: str = "infrastructure_test"
    status: str = "running"
    termination_category: str | None = None
    schema_version: str = "1.2"
    intervention: dict = field(default_factory=lambda: {"type": "NoIntervention"})
    initial_environment: Any = field(default_factory=unavailable)
    system_prompt: Any = field(default_factory=unavailable)

    def to_dict(self) -> dict:
        result = asdict(self)
        result.update(result.pop("model_config"))
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "Manifest":
        data = dict(data)
        config = {key: data.pop(key) for key in ModelConfig.__dataclass_fields__}
        return cls(model_config=ModelConfig(**config), **data)


@dataclass(frozen=True)
class MemorySnapshot:
    # Canonical strings detach snapshots from mutable adapter state. Raw strings
    # retain their exact content; structured JSON retains all fields.
    raw_json: str
    metadata_json: str

    @classmethod
    def capture(cls, raw: Any, metadata: Any = None) -> "MemorySnapshot":
        return cls(canonical(raw), canonical(metadata if metadata is not None else []))

    @property
    def raw(self) -> Any:
        return json.loads(self.raw_json)

    @property
    def metadata(self) -> Any:
        return json.loads(self.metadata_json)

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.raw_json.encode()).hexdigest()

    @property
    def size_bytes(self) -> int:
        return len(self.raw_json.encode())

    def to_dict(self) -> dict:
        return available(
            {
                "raw": self.raw,
                "metadata": self.metadata,
                "sha256": self.sha256,
                "size_bytes": self.size_bytes,
            }
        )


def memory_diff(before: MemorySnapshot, after: MemorySnapshot) -> dict:
    return {
        "before_sha256": before.sha256,
        "after_sha256": after.sha256,
        "before_raw": before.raw,
        "after_raw": after.raw,
        "before_metadata": before.metadata,
        "after_metadata": after.metadata,
        "text_diff": "\n".join(
            difflib.unified_diff(
                before.raw_json.splitlines(),
                after.raw_json.splitlines(),
                fromfile="before",
                tofile="after",
                lineterm="",
            )
        ),
        "size_growth_bytes": after.size_bytes - before.size_bytes,
    }
