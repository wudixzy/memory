"""Frozen actor configuration manifest for the Phase 1 pilot.

The actor is a scientific factor selected by an independent reliability gate.
This module deliberately does not decide which model passes that gate.  It
only makes the selected provider/model/prompt/runtime configuration explicit
and checks that every condition uses the same manifest.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

_EXPERIMENTS = Path(__file__).resolve().parents[1]
if str(_EXPERIMENTS) not in sys.path:
    sys.path.insert(0, str(_EXPERIMENTS))

from exploratory_memory_mvp.common import SchemaError, _nonempty_string, read_json  # noqa: E402

DEFAULT_ACTOR_MANIFEST_PATH = (
    Path(__file__).resolve().parent / "cases" / "phase1_actor_manifest.json"
)
ACTOR_MANIFEST_KEYS = frozenset(
    {
        "schema_version",
        "manifest_id",
        "provider",
        "model_name",
        "thinking",
        "temperature",
        "step_cap",
        "actor_prompt_version",
        "transport_config_provenance",
        "selection_status",
        "manifest_sha256",
    }
)
ACTOR_SELECTION_STATUSES = frozenset(
    {
        "candidate_pending_independent_reliability_gate",
        "passed_independent_reliability_gate",
        "rejected_independent_reliability_gate",
    }
)


def compute_actor_manifest_digest(manifest: dict[str, Any]) -> str:
    """Hash an actor manifest without its self-referential digest field."""

    payload = dict(manifest)
    payload.pop("manifest_sha256", None)
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def validate_actor_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """Validate the frozen actor contract without imposing a model choice."""

    if not isinstance(manifest, dict) or set(manifest) != ACTOR_MANIFEST_KEYS:
        keys = set(manifest) if isinstance(manifest, dict) else type(manifest)
        raise SchemaError(f"Actor manifest has invalid fields: {keys}")
    for key in (
        "schema_version",
        "manifest_id",
        "provider",
        "model_name",
        "actor_prompt_version",
        "transport_config_provenance",
        "selection_status",
    ):
        _nonempty_string(manifest[key], "actor_manifest." + key)
    if manifest["selection_status"] not in ACTOR_SELECTION_STATUSES:
        raise SchemaError(
            "actor_manifest.selection_status is not a recognized independent-gate status"
        )
    if type(manifest["thinking"]) is not bool:
        raise SchemaError("actor_manifest.thinking must be boolean")
    if type(manifest["temperature"]) not in {int, float} or manifest["temperature"] < 0:
        raise SchemaError("actor_manifest.temperature must be non-negative")
    if type(manifest["step_cap"]) is not int or manifest["step_cap"] <= 0:
        raise SchemaError("actor_manifest.step_cap must be positive")
    digest = manifest["manifest_sha256"]
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(char not in "0123456789abcdef" for char in digest)
    ):
        raise SchemaError("actor_manifest.manifest_sha256 must be lowercase SHA-256")
    if digest != compute_actor_manifest_digest(manifest):
        raise SchemaError("Actor manifest digest does not match its contents")
    return manifest


def assert_actor_gate_passed(manifest: dict[str, Any]) -> dict[str, Any]:
    """Fail closed for scientific C1/C2/C3 execution until the gate passes."""

    validate_actor_manifest(manifest)
    status = manifest["selection_status"]
    if status != "passed_independent_reliability_gate":
        raise SchemaError(
            "Scientific Phase 1A execution requires an actor manifest with "
            "selection_status=passed_independent_reliability_gate; "
            f"got {status}"
        )
    return manifest


def load_actor_manifest(path: Path = DEFAULT_ACTOR_MANIFEST_PATH) -> dict[str, Any]:
    """Load and validate the committed actor manifest."""

    return validate_actor_manifest(read_json(path))


def get_phase1_actor_manifest() -> dict[str, Any]:
    """Return a detached copy of the current planning manifest."""

    return json.loads(json.dumps(load_actor_manifest(), ensure_ascii=False))
