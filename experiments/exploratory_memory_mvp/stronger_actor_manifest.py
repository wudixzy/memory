"""Independent development manifest for one stronger actor candidate.

This manifest is intentionally separate from the scientific actor manifest.  It
freezes one development-only model choice without changing actor admission
status or the committed Phase 1 actor candidate.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .actor_manifest import validate_actor_manifest
from .common import SchemaError, _nonempty_string, read_json

DEFAULT_STRONGER_ACTOR_MANIFEST_PATH = (
    Path(__file__).resolve().parent / "cases" / "phase1_stronger_actor_manifest.json"
)

STRONGER_ACTOR_MANIFEST_KEYS = frozenset(
    {
        "schema_version",
        "manifest_id",
        "status",
        "selection_basis",
        "selection_reference",
        "actor_manifest",
        "manifest_sha256",
    }
)


def compute_stronger_actor_manifest_digest(manifest: dict[str, Any]) -> str:
    """Hash the wrapper without its self-referential digest field."""

    payload = dict(manifest)
    payload.pop("manifest_sha256", None)
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def load_stronger_actor_manifest(
    path: Path = DEFAULT_STRONGER_ACTOR_MANIFEST_PATH,
) -> dict[str, Any]:
    """Load one pending, development-only stronger actor candidate."""

    manifest = read_json(path)
    if not isinstance(manifest, dict) or set(manifest) != STRONGER_ACTOR_MANIFEST_KEYS:
        raise SchemaError("Stronger actor manifest has invalid fields")
    if manifest["status"] != "development_candidate":
        raise SchemaError("Stronger actor manifest must remain a development candidate")
    for key in ("schema_version", "manifest_id", "selection_basis", "selection_reference"):
        _nonempty_string(manifest[key], "stronger_actor_manifest." + key)
    actor_manifest = manifest["actor_manifest"]
    validate_actor_manifest(actor_manifest)
    if actor_manifest["selection_status"] != "candidate_pending_independent_reliability_gate":
        raise SchemaError("Stronger actor candidate must remain pending the independent gate")
    digest = manifest["manifest_sha256"]
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(char not in "0123456789abcdef" for char in digest)
    ):
        raise SchemaError("Stronger actor manifest digest is malformed")
    if digest != compute_stronger_actor_manifest_digest(manifest):
        raise SchemaError("Stronger actor manifest digest does not match its contents")
    return manifest
