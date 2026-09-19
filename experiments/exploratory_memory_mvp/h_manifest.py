"""Frozen source-H provenance manifest and validation.

Phase 1 C3 is history-derived.  A schema-valid handwritten H is therefore not
enough for a scientific run: it must be registered with source history, B/C
artifact digests, K* identity, and the future-facing H digest.  Source-only
provenance is kept in this manifest and is never passed to the target actor.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

_EXPERIMENTS = Path(__file__).resolve().parents[1]
if str(_EXPERIMENTS) not in sys.path:
    sys.path.insert(0, str(_EXPERIMENTS))

from exploratory_memory_mvp.common import (  # noqa: E402
    C_PROBE_KEYS,
    ENTITY_RE,
    EVALUATOR_ONLY_KEYS,
    MODEL_INVISIBLE_KEYS,
    SchemaError,
    _nonempty_string,
    assert_no_evaluator_keys,
    read_json,
)
from exploratory_memory_mvp.k_star import compute_k_star_digest, get_phase1_k_star  # noqa: E402
from exploratory_memory_mvp.phase1_applicability import (  # noqa: E402
    PHASE1A_APPLICABILITY_CONTRACT_ID,
    PHASE1A_H_FAMILY,
    validate_public_applicability,
)
from exploratory_memory_mvp.phase1_population import (  # noqa: E402
    DEFAULT_SOURCE_RESERVATION_PATH,
    load_frozen_source_task_ids,
)
from exploratory_memory_mvp.target_registry import (  # noqa: E402
    DEFAULT_REGISTRY_PATH,
    load_target_registry,
    validate_target_registry,
)

DEFAULT_H_MANIFEST_PATH = (
    Path(__file__).resolve().parent / "cases" / "phase1_source_h_manifest.json"
)
H_MANIFEST_KEYS = frozenset(
    {"schema_version", "manifest_id", "created_at", "manifest_status", "entries", "manifest_sha256"}
)
H_ENTRY_KEYS = frozenset(
    {
        "h_id",
        "h_family_id",
        "applicability_contract_id",
        "source_task_id",
        "source_task_seed",
        "source_history_identity",
        "source_history_sha256",
        "k_star_sha256",
        "b_artifact_sha256",
        "c_artifact_sha256",
        "future_h_sha256",
        "future_h",
        "offline_model_config",
        "creation_version",
    }
)
OFFLINE_CONFIG_KEYS = frozenset(
    {"provider", "model_name", "thinking", "temperature", "prompt_version"}
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
FUTURE_H_KEYS = frozenset({"type", "scope", "hypothesis", "guidance", "probe_policy"})


def canonical_digest(value: Any) -> str:
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def compute_future_h_digest(future_h: dict[str, Any]) -> str:
    return canonical_digest(future_h)


def compute_h_manifest_digest(manifest: dict[str, Any]) -> str:
    payload = dict(manifest)
    payload.pop("manifest_sha256", None)
    return canonical_digest(payload)


def _assert_sha(value: Any, name: str) -> None:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise SchemaError(f"{name} must be a lowercase SHA-256 digest")


def compute_file_sha256(path: Path) -> str:
    """Hash an artifact's bytes; callers cannot substitute a claimed digest."""

    if not path.is_file():
        raise SchemaError(f"Required H provenance artifact is missing: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_future_h(future_h: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(future_h, dict) or set(future_h) != FUTURE_H_KEYS:
        raise SchemaError("Future-facing H has invalid fields")
    if future_h.get("type") != "exploratory":
        raise SchemaError("Future-facing H type must be exploratory")
    for key in ("scope", "hypothesis", "guidance"):
        _nonempty_string(future_h.get(key), "future_h." + key)
    probe = future_h.get("probe_policy")
    if not isinstance(probe, dict) or set(probe) != C_PROBE_KEYS:
        raise SchemaError("Future-facing H probe_policy has invalid fields")
    for key in (
        "local_function",
        "realization_pattern",
        "adaptive_policy",
        "evidence_goal",
        "required_downstream_state",
    ):
        _nonempty_string(probe.get(key), "future_h.probe_policy." + key)
    for key in ("capability_requirements", "stop_conditions"):
        value = probe.get(key)
        if not isinstance(value, list) or not value or any(
            not isinstance(item, str) or not item.strip() for item in value
        ):
            raise SchemaError(f"future_h.probe_policy.{key} must be non-empty strings")
    assert_no_evaluator_keys(future_h)
    serialized = json.dumps(future_h, ensure_ascii=False, sort_keys=True)
    if ENTITY_RE.search(serialized):
        raise SchemaError("Future-facing H must not contain exact source entity IDs")
    for forbidden in ("source_grounding", "provenance", "oracle", "evaluator"):
        if forbidden in serialized.lower():
            raise SchemaError(f"Source-only field leaked into future-facing H: {forbidden}")
    return future_h


def validate_h_entry(entry: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(entry, dict) or set(entry) != H_ENTRY_KEYS:
        keys = set(entry) if isinstance(entry, dict) else type(entry)
        raise SchemaError(f"Source-H entry has invalid fields: {keys}")
    for key in (
        "h_id",
        "h_family_id",
        "applicability_contract_id",
        "source_task_id",
        "source_history_identity",
        "creation_version",
    ):
        _nonempty_string(entry[key], "h_entry." + key)
    if entry["applicability_contract_id"] != PHASE1A_APPLICABILITY_CONTRACT_ID:
        raise SchemaError("Source-H applicability contract is not the frozen Phase 1A contract")
    if type(entry["source_task_seed"]) is not int:
        raise SchemaError("h_entry.source_task_seed must be an integer")
    for key in (
        "source_history_sha256",
        "k_star_sha256",
        "b_artifact_sha256",
        "c_artifact_sha256",
        "future_h_sha256",
    ):
        _assert_sha(entry[key], "h_entry." + key)
    if entry["source_history_identity"] != f"sha256:{entry['source_history_sha256']}":
        raise SchemaError(
            "h_entry.source_history_identity must identify the recorded source-history digest"
        )
    offline = entry["offline_model_config"]
    if not isinstance(offline, dict) or set(offline) != OFFLINE_CONFIG_KEYS:
        raise SchemaError("h_entry.offline_model_config has invalid fields")
    for key in ("provider", "model_name", "prompt_version"):
        _nonempty_string(offline[key], "h_entry.offline_model_config." + key)
    if type(offline["thinking"]) is not bool:
        raise SchemaError("h_entry.offline_model_config.thinking must be boolean")
    if type(offline["temperature"]) not in {int, float} or offline["temperature"] < 0:
        raise SchemaError("h_entry.offline_model_config.temperature must be non-negative")
    future_h = validate_future_h(entry["future_h"])
    if entry["future_h_sha256"] != compute_future_h_digest(future_h):
        raise SchemaError("h_entry.future_h_sha256 does not match future_h")
    serialized = json.dumps(entry, ensure_ascii=False, sort_keys=True).lower()
    for forbidden in EVALUATOR_ONLY_KEYS | MODEL_INVISIBLE_KEYS:
        if f'"{forbidden}"' in serialized:
            raise SchemaError(
                "Evaluator/model-invisible key leaked into source-H entry: "
                f"{forbidden}"
            )
    # Source-only fields are allowed in this manifest but not inside future_h.
    return entry


def validate_h_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(manifest, dict) or set(manifest) != H_MANIFEST_KEYS:
        keys = set(manifest) if isinstance(manifest, dict) else type(manifest)
        raise SchemaError(f"Source-H manifest has invalid fields: {keys}")
    for key in ("schema_version", "manifest_id", "created_at", "manifest_status"):
        _nonempty_string(manifest[key], "h_manifest." + key)
    entries = manifest["entries"]
    if not isinstance(entries, list):
        raise SchemaError("h_manifest.entries must be a list")
    seen = set()
    for entry in entries:
        validate_h_entry(entry)
        if entry["h_id"] in seen:
            raise SchemaError("Duplicate h_id in source-H manifest")
        seen.add(entry["h_id"])
    digest = manifest["manifest_sha256"]
    _assert_sha(digest, "h_manifest.manifest_sha256")
    if digest != compute_h_manifest_digest(manifest):
        raise SchemaError("Source-H manifest digest does not match")
    return manifest


def load_h_manifest(path: Path = DEFAULT_H_MANIFEST_PATH) -> dict[str, Any]:
    return validate_h_manifest(read_json(path))


def validate_h_entry_referential_integrity(
    entry: dict[str, Any],
    source_registry: dict[str, Any],
    *,
    k_star: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Check a live entry against the frozen Source set, seed, K*, and scope."""

    validate_h_entry(entry)
    validate_target_registry(source_registry)
    if entry["h_family_id"] != PHASE1A_H_FAMILY:
        raise SchemaError("Source-H entry is outside the frozen Phase 1A H family")
    source_ids = source_registry["partitions"]["source"]
    if entry["source_task_id"] not in source_ids:
        raise SchemaError("Source-H entry is not tied to the frozen Phase 1 source set")
    records = {
        record["target_id"]: record
        for record in source_registry["candidate_universe"]["records"]
    }
    source_record = records.get(entry["source_task_id"])
    if source_record is None:
        raise SchemaError("Source-H entry source task is missing from public registry")
    if entry["source_task_seed"] != source_record["requested_seed"]:
        raise SchemaError("Source-H source seed differs from frozen source protocol")
    canonical_k_star = get_phase1_k_star() if k_star is None else k_star
    if entry["k_star_sha256"] != compute_k_star_digest(canonical_k_star):
        raise SchemaError("Source-H K* digest differs from canonical Phase 1 K*")
    validate_public_applicability(source_record)
    return entry


def _validate_source_reservation_matches_registry(
    source_ids: list[str], registry: dict[str, Any]
) -> None:
    """Require the standalone Source reservation and registry to be identical."""

    if source_ids != registry["partitions"]["source"]:
        raise SchemaError(
            "Frozen Source reservation does not exactly match the target registry Source set"
        )


def _read_json_artifact(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise SchemaError(f"{label} artifact is missing: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SchemaError(f"{label} artifact is not valid JSON: {path}") from error
    if not isinstance(value, dict):
        raise SchemaError(f"{label} artifact must be a JSON object: {path}")
    return value


def _source_artifact_identity(value: dict[str, Any]) -> tuple[str, int] | None:
    candidates = [value]
    for key in ("current_task", "target_task", "task"):
        nested = value.get(key)
        if isinstance(nested, dict):
            candidates.append(nested)
    for candidate in candidates:
        task_id = candidate.get("task_id")
        seed = candidate.get("seed", candidate.get("requested_seed"))
        if isinstance(task_id, str) and type(seed) is int:
            return task_id, seed
    return None


def _validate_recorded_offline_config(value: Any, label: str) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != OFFLINE_CONFIG_KEYS:
        raise SchemaError(f"{label} offline_model_config is malformed")
    for key in ("provider", "model_name", "prompt_version"):
        _nonempty_string(value[key], f"{label}.offline_model_config.{key}")
    if type(value["thinking"]) is not bool:
        raise SchemaError(f"{label}.offline_model_config.thinking must be boolean")
    if type(value["temperature"]) not in {int, float} or value["temperature"] < 0:
        raise SchemaError(f"{label}.offline_model_config.temperature must be non-negative")
    return value


def _load_c_result_artifact(path: Path) -> tuple[dict[str, Any], dict[str, Any] | None]:
    from exploratory_memory_mvp.common import validate_c_result  # noqa: PLC0415

    result = _read_json_artifact(path, "C")
    recorded_config = _validate_recorded_offline_config(
        result.get("offline_model_config"), "C"
    )
    # Permit a saved result wrapper while always validating the actual parsed C
    # object that supplies the future-facing projection.
    if isinstance(result.get("parsed_output"), dict):
        result = result["parsed_output"]
    elif isinstance(result.get("result"), dict):
        result = result["result"]
    validate_c_result(result)
    return result, recorded_config


def _load_b_result_artifact(path: Path) -> tuple[dict[str, Any], dict[str, Any] | None]:
    from exploratory_memory_mvp.common import validate_b_result  # noqa: PLC0415

    result = _read_json_artifact(path, "B")
    recorded_config = _validate_recorded_offline_config(
        result.get("offline_model_config"), "B"
    )
    if isinstance(result.get("parsed_output"), dict):
        result = result["parsed_output"]
    elif isinstance(result.get("result"), dict):
        result = result["result"]
    validate_b_result(result)
    return result, recorded_config


def freeze_source_h_entry(
    *,
    h_id: str,
    source_task_id: str,
    source_history_path: Path,
    b_artifact_path: Path,
    c_artifact_path: Path,
    offline_model_config: dict[str, Any],
    creation_version: str,
    source_registry_path: Path = DEFAULT_REGISTRY_PATH,
    source_reservation_path: Path = DEFAULT_SOURCE_RESERVATION_PATH,
    k_star: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create one live H entry by hashing and projecting real artifacts.

    The caller supplies paths, not SHA strings.  The utility derives the
    source task seed from the frozen public source registry, hashes every
    artifact itself, and derives ``future_h`` from the stored C result.
    """

    _nonempty_string(h_id, "h_id")
    _nonempty_string(source_task_id, "source_task_id")
    _nonempty_string(creation_version, "creation_version")
    if not isinstance(offline_model_config, dict):
        raise SchemaError("offline_model_config must be an object")
    registry = load_target_registry(source_registry_path)
    source_ids = load_frozen_source_task_ids(source_reservation_path)
    _validate_source_reservation_matches_registry(source_ids, registry)
    if source_task_id not in source_ids:
        raise SchemaError("Cannot freeze H from a task outside the frozen source set")
    source_record = next(
        record
        for record in registry["candidate_universe"]["records"]
        if record["target_id"] == source_task_id
    )
    validate_public_applicability(source_record)
    source_history_sha256 = compute_file_sha256(source_history_path)
    b_artifact_sha256 = compute_file_sha256(b_artifact_path)
    c_artifact_sha256 = compute_file_sha256(c_artifact_path)
    source_history = _read_json_artifact(source_history_path, "Source history")
    identity = _source_artifact_identity(source_history)
    if identity != (source_task_id, source_record["requested_seed"]):
        raise SchemaError("Source history artifact task/seed does not match frozen source")
    b_result, b_recorded_config = _load_b_result_artifact(b_artifact_path)
    if b_result["decision"] != "OPEN":
        raise SchemaError("Cannot freeze a source H from a B=NONE artifact")
    c_result, c_recorded_config = _load_c_result_artifact(c_artifact_path)
    if b_recorded_config is None or c_recorded_config is None:
        raise SchemaError(
            "B and C freeze artifacts must embed offline_model_config; a separate claim is "
            "not sufficient to prove provenance"
        )
    for recorded_config in (b_recorded_config, c_recorded_config):
        if recorded_config != offline_model_config:
            raise SchemaError("Recorded B/C model configuration differs from freeze config")
    if b_recorded_config is not None and c_recorded_config is not None:
        if b_recorded_config != c_recorded_config:
            raise SchemaError("B and C artifacts were produced under different configurations")
    from exploratory_memory_mvp.common import future_exploratory_memory  # noqa: PLC0415

    future_h = future_exploratory_memory(c_result)
    if future_h is None:
        raise SchemaError("Cannot freeze a source H from a C=NONE artifact")
    entry = {
        "h_id": h_id,
        "h_family_id": PHASE1A_H_FAMILY,
        "applicability_contract_id": PHASE1A_APPLICABILITY_CONTRACT_ID,
        "source_task_id": source_task_id,
        "source_task_seed": source_record["requested_seed"],
        "source_history_identity": f"sha256:{source_history_sha256}",
        "source_history_sha256": source_history_sha256,
        "k_star_sha256": compute_k_star_digest(
            get_phase1_k_star() if k_star is None else k_star
        ),
        "b_artifact_sha256": b_artifact_sha256,
        "c_artifact_sha256": c_artifact_sha256,
        "future_h_sha256": compute_future_h_digest(future_h),
        "future_h": future_h,
        "offline_model_config": offline_model_config,
        "creation_version": creation_version,
    }
    validate_h_entry_referential_integrity(entry, registry, k_star=k_star)
    return entry


def validate_frozen_h_entry_artifacts(
    entry: dict[str, Any],
    *,
    source_history_path: Path,
    b_artifact_path: Path,
    c_artifact_path: Path,
    source_registry_path: Path = DEFAULT_REGISTRY_PATH,
    source_reservation_path: Path = DEFAULT_SOURCE_RESERVATION_PATH,
    k_star: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Recompute all live-artifact claims in an already frozen H entry."""

    registry = load_target_registry(source_registry_path)
    source_ids = load_frozen_source_task_ids(source_reservation_path)
    _validate_source_reservation_matches_registry(source_ids, registry)
    validate_h_entry_referential_integrity(entry, registry, k_star=k_star)
    if compute_file_sha256(source_history_path) != entry["source_history_sha256"]:
        raise SchemaError("Source history artifact hash does not match frozen H")
    if compute_file_sha256(b_artifact_path) != entry["b_artifact_sha256"]:
        raise SchemaError("B artifact hash does not match frozen H")
    if compute_file_sha256(c_artifact_path) != entry["c_artifact_sha256"]:
        raise SchemaError("C artifact hash does not match frozen H")
    source_history = _read_json_artifact(source_history_path, "Source history")
    source_record = next(
        record
        for record in registry["candidate_universe"]["records"]
        if record["target_id"] == entry["source_task_id"]
    )
    if _source_artifact_identity(source_history) != (
        entry["source_task_id"],
        source_record["requested_seed"],
    ):
        raise SchemaError("Source history task/seed identity does not match frozen H")
    c_result, c_recorded_config = _load_c_result_artifact(c_artifact_path)
    b_result, b_recorded_config = _load_b_result_artifact(b_artifact_path)
    if b_result["decision"] != "OPEN":
        raise SchemaError("Frozen source H must retain a B=OPEN artifact")
    if b_recorded_config is None or c_recorded_config is None:
        raise SchemaError(
            "B and C freeze artifacts must embed offline_model_config; a separate claim is "
            "not sufficient to prove provenance"
        )
    for recorded_config in (b_recorded_config, c_recorded_config):
        if recorded_config != entry["offline_model_config"]:
            raise SchemaError("Frozen H offline model config differs from B/C artifact config")
    from exploratory_memory_mvp.common import future_exploratory_memory  # noqa: PLC0415

    projected = future_exploratory_memory(c_result)
    if projected != entry["future_h"]:
        raise SchemaError("Frozen H differs from future-facing projection of C artifact")
    if compute_future_h_digest(projected) != entry["future_h_sha256"]:
        raise SchemaError("Frozen H future-facing digest does not match projection")
    return entry


def append_frozen_h_entry(
    manifest: dict[str, Any], entry: dict[str, Any]
) -> dict[str, Any]:
    """Return a new manifest containing one validated live source-H entry."""

    validate_h_manifest(manifest)
    validate_h_entry(entry)
    if any(existing["h_id"] == entry["h_id"] for existing in manifest["entries"]):
        raise SchemaError(f"Duplicate source-H ID: {entry['h_id']}")
    result = json.loads(json.dumps(manifest, ensure_ascii=False))
    result["entries"].append(json.loads(json.dumps(entry, ensure_ascii=False)))
    result["manifest_status"] = "live_entries_frozen_from_verified_b_c_artifacts"
    result["manifest_sha256"] = compute_h_manifest_digest(result)
    return validate_h_manifest(result)


def find_h_entry(manifest: dict[str, Any], h_id: str) -> dict[str, Any]:
    validate_h_manifest(manifest)
    matches = [entry for entry in manifest["entries"] if entry["h_id"] == h_id]
    if len(matches) != 1:
        raise SchemaError(f"Registered source H not found: {h_id}")
    return matches[0]


def verify_h_assignment(
    entry: dict[str, Any],
    *,
    target_id: str,
    target_family: str,
    target_record: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Verify public family/identity and, when supplied, scope applicability."""

    validate_h_entry(entry)
    _nonempty_string(target_id, "target_id")
    _nonempty_string(target_family, "target_family")
    if entry["h_family_id"] != target_family:
        raise SchemaError("Registered H family does not match target assignment")
    if target_record is not None:
        if target_record.get("target_id") != target_id:
            raise SchemaError("Target record identity differs from H assignment target")
        validate_public_applicability(target_record)
    return {"target_id": target_id, "h_id": entry["h_id"], "h_family_id": target_family}
