"""Phase 1 experiment configuration schema and validation.

Defines the config-driven structure for C1, C2, and C3 Frozen-history runs,
enforcing condition isolation, identical K*, and explicit repetition metadata.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

_EXPERIMENTS = Path(__file__).resolve().parents[1]
if str(_EXPERIMENTS) not in sys.path:
    sys.path.insert(0, str(_EXPERIMENTS))

from exploratory_memory_mvp.actor_manifest import (  # noqa: E402
    assert_actor_gate_passed,
    get_phase1_actor_manifest,
    validate_actor_manifest,
)
from exploratory_memory_mvp.c2_generic import (  # noqa: E402
    validate_c2_exploratory_memory,
)
from exploratory_memory_mvp.common import (  # noqa: E402
    C_PROBE_KEYS,
    ENTITY_RE,
    EVALUATOR_ONLY_KEYS,
    MODEL_INVISIBLE_KEYS,
    SchemaError,
    _nonempty_string,
    assert_no_evaluator_keys,
)
from exploratory_memory_mvp.k_star import (  # noqa: E402
    assert_k_star_valid,
    compute_k_star_digest,
    get_phase1_k_star,
)
from exploratory_memory_mvp.probe_budget import (  # noqa: E402
    PHASE1_PROBE_BUDGET,
    probe_budget_digest,
    validate_probe_budget,
)

Phase1Condition = Literal["C1", "C2", "C3"]
# These names remain compatibility aliases for artifact summaries.  The
# validator no longer treats any particular model as a scientific invariant;
# the frozen actor manifest is the invariant instead.
_PLANNING_ACTOR_MANIFEST = get_phase1_actor_manifest()
PHASE1_PROVIDER = _PLANNING_ACTOR_MANIFEST["provider"]
PHASE1_MODEL = _PLANNING_ACTOR_MANIFEST["model_name"]
PHASE1_THINKING = _PLANNING_ACTOR_MANIFEST["thinking"]
PHASE1_TEMPERATURE = _PLANNING_ACTOR_MANIFEST["temperature"]
FUTURE_H_KEYS = frozenset({"type", "scope", "hypothesis", "guidance", "probe_policy"})


@dataclass
class Phase1RunConfig:
    condition: Phase1Condition
    target_id: str
    target_seed: int
    repetition_index: int
    output_dir: Path
    k_star: list[dict[str, Any]] = field(default_factory=get_phase1_k_star)
    exploratory_memory: dict[str, Any] | None = None
    step_cap: int | None = None
    provider: str | None = None
    model_name: str | None = None
    thinking: bool | None = None
    temperature: float | None = None
    target_registry_sha256: str | None = None
    allow_network: bool = False
    dry_run: bool = False
    explicit_diagnostic: bool = False
    actor_manifest: dict[str, Any] = field(default_factory=get_phase1_actor_manifest)
    h_id: str | None = None
    h_manifest_sha256: str | None = None
    probe_budget: dict[str, Any] = field(
        default_factory=lambda: json.loads(json.dumps(PHASE1_PROBE_BUDGET))
    )

    def __post_init__(self) -> None:
        """Fill compatibility fields from the frozen actor manifest."""

        manifest = validate_actor_manifest(self.actor_manifest)
        if self.provider is None:
            self.provider = manifest["provider"]
        if self.model_name is None:
            self.model_name = manifest["model_name"]
        if self.thinking is None:
            self.thinking = manifest["thinking"]
        if self.temperature is None:
            self.temperature = manifest["temperature"]
        if self.step_cap is None:
            self.step_cap = manifest["step_cap"]

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["output_dir"] = str(self.output_dir)
        result["k_star_sha256"] = compute_k_star_digest(self.k_star)
        result["actor_manifest_sha256"] = self.actor_manifest["manifest_sha256"]
        result["probe_budget_sha256"] = probe_budget_digest(self.probe_budget)
        result["config_sha256"] = compute_phase1_config_digest(result)
        return result


def compute_phase1_config_digest(config_dict: dict[str, Any]) -> str:
    """Hash a run config without a self-referential ``config_sha256`` field."""

    payload = dict(config_dict)
    payload.pop("config_sha256", None)
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def validate_phase1_config(
    config: Phase1RunConfig, *, require_actor_gate: bool = False
) -> Phase1RunConfig:
    """Validate Phase 1 run configuration against condition contracts and isolation rules."""
    if config.condition not in {"C1", "C2", "C3"}:
        raise SchemaError(f"Invalid Phase 1 condition: {config.condition}")

    _nonempty_string(config.target_id, "target_id")
    if type(config.target_seed) is not int:
        raise SchemaError("target_seed must be an integer")
    if type(config.repetition_index) is not int or config.repetition_index < 0:
        raise SchemaError("repetition_index must be a non-negative integer")
    if type(config.step_cap) is not int or config.step_cap <= 0:
        raise SchemaError("step_cap must be a positive integer")
    manifest = validate_actor_manifest(config.actor_manifest)
    if require_actor_gate:
        assert_actor_gate_passed(manifest)
    for field_name in ("provider", "model_name", "thinking", "temperature", "step_cap"):
        if getattr(config, field_name) != manifest[field_name]:
            raise SchemaError(f"Phase 1 {field_name} differs from frozen actor manifest")
    if config.target_registry_sha256 is not None:
        if (
            not isinstance(config.target_registry_sha256, str)
            or len(config.target_registry_sha256) != 64
            or any(char not in "0123456789abcdef" for char in config.target_registry_sha256)
        ):
            raise SchemaError("target_registry_sha256 must be a lowercase SHA-256 digest")

    assert_k_star_valid(config.k_star)
    validate_probe_budget(config.probe_budget)

    if config.condition == "C1":
        if config.exploratory_memory is not None:
            raise SchemaError("Condition C1 (Established-Only) must not have an exploratory memory")
    elif config.condition == "C2":
        if config.exploratory_memory is None:
            raise SchemaError("Condition C2 requires a structured generic exploratory memory")
        validate_c2_exploratory_memory(config.exploratory_memory)
    elif config.condition == "C3":
        if config.exploratory_memory is None:
            raise SchemaError("Condition C3 requires a history-derived exploratory memory")
        if set(config.exploratory_memory) != FUTURE_H_KEYS:
            raise SchemaError("Condition C3 must receive future-facing H only")
        if config.exploratory_memory.get("type") != "exploratory":
            raise SchemaError("Condition C3 exploratory memory type is malformed")
        for key in ("scope", "hypothesis", "guidance"):
            _nonempty_string(config.exploratory_memory.get(key), "C3 " + key)
        probe = config.exploratory_memory.get("probe_policy")
        if not isinstance(probe, dict) or set(probe) != C_PROBE_KEYS:
            raise SchemaError("Condition C3 probe policy is malformed")
        for key in (
            "local_function",
            "realization_pattern",
            "adaptive_policy",
            "evidence_goal",
            "required_downstream_state",
        ):
            _nonempty_string(probe.get(key), "C3 probe_policy." + key)
        for key in ("capability_requirements", "stop_conditions"):
            value = probe.get(key)
            if not isinstance(value, list) or not value or any(
                not isinstance(item, str) or not item.strip() for item in value
            ):
                raise SchemaError("C3 probe policy lists must contain non-empty strings")
        assert_no_evaluator_keys(config.exploratory_memory)
        future_text = json.dumps(
            config.exploratory_memory, ensure_ascii=False, sort_keys=True
        )
        if ENTITY_RE.search(future_text):
            raise SchemaError("C3 future-facing H must not contain exact entity IDs")
        _nonempty_string(config.h_id, "C3 h_id")
        if (
            not isinstance(config.h_manifest_sha256, str)
            or len(config.h_manifest_sha256) != 64
            or any(char not in "0123456789abcdef" for char in config.h_manifest_sha256)
        ):
            raise SchemaError("C3 h_manifest_sha256 must be a lowercase SHA-256 digest")
    elif config.h_id is not None or config.h_manifest_sha256 is not None:
        raise SchemaError("Only C3 may carry source-H manifest identity")

    serialized = str(config.to_dict()).lower()
    for forbidden in EVALUATOR_ONLY_KEYS | MODEL_INVISIBLE_KEYS:
        if f"'{forbidden}'" in serialized or f'"{forbidden}"' in serialized:
            raise SchemaError(f"Evaluator/oracle key '{forbidden}' leaked into Phase 1 run config")

    return config


def validate_condition_parity(
    configs: dict[str, Phase1RunConfig], *, require_actor_gate: bool = False
) -> dict[str, Phase1RunConfig]:
    """Check frozen factors shared by C1/C2/C3 before execution."""

    if set(configs) != {"C1", "C2", "C3"}:
        raise SchemaError("Phase 1 parity requires exactly C1, C2, and C3")
    for config in configs.values():
        validate_phase1_config(config, require_actor_gate=require_actor_gate)
    first = configs["C1"]
    first_k = compute_k_star_digest(first.k_star)
    first_actor = first.actor_manifest["manifest_sha256"]
    first_budget = probe_budget_digest(first.probe_budget)
    for condition, config in configs.items():
        if config.target_id != first.target_id or config.target_seed != first.target_seed:
            raise SchemaError(f"{condition} target identity drifted from C1")
        if config.repetition_index != first.repetition_index:
            raise SchemaError(f"{condition} repetition metadata drifted from C1")
        if compute_k_star_digest(config.k_star) != first_k:
            raise SchemaError(f"{condition} K* drifted from C1")
        if config.actor_manifest["manifest_sha256"] != first_actor:
            raise SchemaError(f"{condition} actor manifest drifted from C1")
        if probe_budget_digest(config.probe_budget) != first_budget:
            raise SchemaError(f"{condition} probe budget drifted from C1")
        if config.step_cap != first.step_cap:
            raise SchemaError(f"{condition} step cap drifted from C1")
        if config.target_registry_sha256 != first.target_registry_sha256:
            raise SchemaError(f"{condition} target registry digest drifted from C1")
    return configs
