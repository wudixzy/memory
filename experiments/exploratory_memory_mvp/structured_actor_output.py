"""Strict per-step structured-output contract for the actor development diagnostic.

The action-index enum is intentionally rebuilt from the current ordered
admissible-action list on every step.  This module only constructs and audits
the provider request; it does not select, clamp, or otherwise repair an
action.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .common import SchemaError

STRUCTURED_OUTPUT_SCHEMA_VERSION = "actor_action_index_probe_dynamic_json_schema_v1"
STRUCTURED_OUTPUT_NAME = "alfworld_actor_action_index_probe"
PROBE_STATUS_VALUES = ("NOT_ACTIVE", "ACTIVE", "EVIDENCE_OBTAINED", "ABORTED")


def _validate_admissible_actions(admissible_actions: list[str]) -> None:
    if not isinstance(admissible_actions, list) or not admissible_actions:
        raise SchemaError("Strict actor schema requires a non-empty action list")
    if any(type(action) is not str or not action for action in admissible_actions):
        raise SchemaError("Strict actor schema requires non-empty string actions")


def build_dynamic_actor_response_format(admissible_actions: list[str]) -> dict[str, Any]:
    """Build the exact strict JSON-schema request for one current state."""

    _validate_admissible_actions(admissible_actions)
    return {
        "type": "json_schema",
        "json_schema": {
            "name": STRUCTURED_OUTPUT_NAME,
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "action_index": {
                        "type": "integer",
                        "enum": list(range(len(admissible_actions))),
                    },
                    "probe_status": {
                        "type": "string",
                        "enum": list(PROBE_STATUS_VALUES),
                    },
                },
                "required": ["action_index", "probe_status"],
                "additionalProperties": False,
            },
        },
    }


def validate_dynamic_actor_response_format(
    response_format: dict[str, Any], admissible_actions: list[str]
) -> dict[str, Any]:
    """Fail closed unless a request exactly matches the current action list."""

    _validate_admissible_actions(admissible_actions)
    if not isinstance(response_format, dict) or set(response_format) != {
        "type",
        "json_schema",
    }:
        raise SchemaError("Strict actor response format has invalid top-level fields")
    if response_format["type"] != "json_schema":
        raise SchemaError("Strict actor response format must use json_schema")
    wrapper = response_format["json_schema"]
    if not isinstance(wrapper, dict) or set(wrapper) != {"name", "strict", "schema"}:
        raise SchemaError("Strict actor json_schema wrapper is malformed")
    if wrapper["name"] != STRUCTURED_OUTPUT_NAME or wrapper["strict"] is not True:
        raise SchemaError("Strict actor json_schema name/strict flag is malformed")
    schema = wrapper["schema"]
    if not isinstance(schema, dict) or set(schema) != {
        "type",
        "properties",
        "required",
        "additionalProperties",
    }:
        raise SchemaError("Strict actor JSON schema is malformed")
    if schema["type"] != "object" or schema["additionalProperties"] is not False:
        raise SchemaError("Strict actor schema must be an object without extra properties")
    if schema["required"] != ["action_index", "probe_status"]:
        raise SchemaError("Strict actor schema must require both output fields")
    properties = schema["properties"]
    if not isinstance(properties, dict) or set(properties) != {
        "action_index",
        "probe_status",
    }:
        raise SchemaError("Strict actor schema properties are malformed")
    action_schema = properties["action_index"]
    if not isinstance(action_schema, dict) or set(action_schema) != {"type", "enum"}:
        raise SchemaError("Strict actor action_index schema is malformed")
    if action_schema["type"] != "integer" or action_schema["enum"] != list(
        range(len(admissible_actions))
    ):
        raise SchemaError("Strict actor action_index enum does not match current actions")
    status_schema = properties["probe_status"]
    if not isinstance(status_schema, dict) or set(status_schema) != {"type", "enum"}:
        raise SchemaError("Strict actor probe_status schema is malformed")
    if status_schema["type"] != "string" or status_schema["enum"] != list(
        PROBE_STATUS_VALUES
    ):
        raise SchemaError("Strict actor probe_status enum is malformed")
    return response_format


def dynamic_actor_response_format_digest(response_format: dict[str, Any]) -> str:
    """Return a stable digest for the saved per-step provider request."""

    serialized = json.dumps(
        response_format, ensure_ascii=False, sort_keys=True, allow_nan=False
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
