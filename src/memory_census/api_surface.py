"""The public API surface, read from the benchmark's own documentation database.

`data/base_dbs/api_docs.db` is the table behind `apis.api_docs.show_api_doc`,
i.e. the documentation an AppWorld agent can read at runtime. Reading it turns
"a bulk alternative probably exists" from a guess into a claim the benchmark
itself supports, so every structural alternative in `memory_census.strategy`
is checked here before the rubric credits it.

The check is deliberately one-directional: a *documented* response field
**supports** an alternative; a *missing* field **refutes** it. Absence of a
candidate API from the docs is reported as `unknown`, never as support.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

#: Relative to the benchmark `data/` root.
API_DOCS_RELATIVE_PATH = Path("base_dbs/api_docs.db")


@dataclass(frozen=True)
class ApiDoc:
    app: str
    api: str
    description: str
    parameters: tuple[dict, ...]
    response_fields: tuple[str, ...]
    response_shape: str  # "list" | "object" | "unknown"

    @property
    def name(self) -> str:
        return f"{self.app}.{self.api}"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameter_names": [p.get("name") for p in self.parameters],
            "response_fields": list(self.response_fields),
            "response_shape": self.response_shape,
        }


def _shape_and_fields(schema: object) -> tuple[str, tuple[str, ...]]:
    if not isinstance(schema, dict):
        return "unknown", ()
    success = schema.get("success")
    if isinstance(success, list):
        first = success[0] if success else None
        if isinstance(first, dict):
            return "list", tuple(sorted(first))
        return "list", ()
    if isinstance(success, dict):
        return "object", tuple(sorted(success))
    return "unknown", ()


class ApiSurface:
    """Read-only view of the public API documentation shipped with the benchmark."""

    def __init__(self, api_docs_db: Path | str):
        self.path = Path(api_docs_db)
        if not self.path.exists():
            raise FileNotFoundError(f"no api docs database at {self.path}")
        self._connection = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True)
        self._connection.row_factory = sqlite3.Row

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> "ApiSurface":
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def api_names(self) -> list[str]:
        rows = self._connection.execute(
            "select app_name_, api_name from api_docs order by app_name_, api_name"
        )
        return [f"{row['app_name_']}.{row['api_name']}" for row in rows]

    def doc(self, name: str) -> ApiDoc | None:
        app, _, api = name.partition(".")
        row = self._connection.execute(
            "select * from api_docs where app_name_ = ? and api_name = ?", (app, api)
        ).fetchone()
        if row is None:
            return None
        try:
            parameters = tuple(json.loads(row["parameters"] or "[]"))
        except json.JSONDecodeError:
            parameters = ()
        try:
            schema = json.loads(row["response_schemas"] or "null")
        except json.JSONDecodeError:
            schema = None
        shape, fields = _shape_and_fields(schema)
        return ApiDoc(
            app=app,
            api=api,
            description=(row["description"] or "").strip(),
            parameters=parameters,
            response_fields=fields,
            response_shape=shape,
        )

    def field_source(self, field: str, excluding: str | None = None) -> list[str]:
        """Documented APIs whose response carries `field` (list or object shape)."""

        found = []
        for name in self.api_names():
            if name == excluding:
                continue
            doc = self.doc(name)
            if doc and field in doc.response_fields:
                found.append(name)
        return found

    def supports_alternative(
        self,
        cheaper_api: str,
        required_fields: tuple[str, ...],
        replaces_api: str | None = None,
    ) -> dict:
        """Can `cheaper_api` supply `required_fields` without per-entity probes?

        `replaces_api` is reported alongside so a reviewer can see which probe
        the alternative would remove.
        """

        doc = self.doc(cheaper_api)
        if doc is None:
            return {
                "verdict": "unknown",
                "reason": f"{cheaper_api} is not present in the public api docs",
                "cheaper_api": cheaper_api,
                "replaces_api": replaces_api,
                "required_fields": list(required_fields),
            }
        missing = [f for f in required_fields if f not in doc.response_fields]
        if missing:
            sources = {f: self.field_source(f, excluding=cheaper_api) for f in missing}
            return {
                "verdict": "refuted",
                "reason": (
                    f"{cheaper_api} response does not document field(s) {missing}; "
                    "a client-side filter on those fields is not supported by the public docs"
                ),
                "cheaper_api": cheaper_api,
                "replaces_api": replaces_api,
                "required_fields": list(required_fields),
                "missing_fields": missing,
                "fields_available_from": sources,
                "cheaper_api_doc": doc.to_dict(),
            }
        return {
            "verdict": "documented",
            "reason": (
                f"{cheaper_api} documents all required field(s) {list(required_fields)}, so the "
                "bulk route needs no per-entity detail probe for them"
            ),
            "cheaper_api": cheaper_api,
            "replaces_api": replaces_api,
            "required_fields": list(required_fields),
            "cheaper_api_doc": doc.to_dict(),
        }
