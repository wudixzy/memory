"""Bounded research-side review packets for the Stage-A reserve families.

`docs/29_parallel_candidate_review_plan.md` routes every reserve family through a
parallel semantic review, and `docs/27` Phase 1 assigns Claude Code the
family/task IDs plus a *bounded* per-family evidence packet. The evidence a
reviewer needs is exactly what `memory_census.boundary` forbids inside the
adaptive loop: benchmark instructions, evaluator ground truth, released
reference solutions, and privileged API documentation. This module therefore
builds **research-side packets only**, and says so in every packet.

Properties this module guarantees:

* one packet per reserve family, carrying only the fields `docs/29` section 2
  lists — family/source/target IDs, instructions, normalized state/setup
  differences, reference strategy C and its target call count, census B routes
  including weak/rejected ones, bounded reference-solution snippets, public API
  documentation excerpts, the comparison gate, the K_0 static-playbook overlap,
  and provenance paths/hashes;
* hard, deterministic caps on every snippet, list, string, and on the serialized
  packet size, so a packet cannot become a whole-solution or whole-database dump;
* an explicit `usage_scope` and an explicit `unmeasured` block: `cost(B)`,
  `B_success_on_target`, `K_0_discoverability` and any model-discovered route are
  unknown, and the reference route is not an agent discovery;
* provenance (repository-relative path plus sha256) for every file a claim
  rests on, including a drift check against the hashes the census recorded.

Nothing here executes a benchmark, calls a model, or touches the network. The
static boundary scan in `memory_census.boundary` covers this module because it
lives in the census package.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from memory_census.api_surface import ApiSurface
from memory_census.boundary import assert_consumer_allowed

ROOT = Path(__file__).resolve().parents[2]

PACKET_VERSION = "review-packet-v1"
MANIFEST_VERSION = "reserve-manifest-v1"

#: Census status whose families are the review pool.
RESERVE_STATUS = "reserve"

#: The only consumer a packet may be handed to.
PACKET_CONSUMER = "research-side-review"

USAGE_SCOPE = (
    "research-side privileged evidence: benchmark instructions, evaluator ground truth, "
    "released reference solutions and API documentation, used for candidate triage only. "
    "Never inject into Generator/Reflector/Curator or any actor/memory-updater context."
)

#: Statements a packet may not leave implicit. Each one is a field the reviewer
#: is most likely to assume, and none of them has been measured.
UNMEASURED = {
    "cost_B": "unmeasured",
    "B_success_on_target": "unmeasured",
    "K0_discoverability": "unmeasured",
    "model_discovered_route": "unmeasured",
    "statement": (
        "no B trajectory exists: no model rollout and no benchmark execution has run any "
        "route named in this packet, so cost(B), B_success_on_target and any saving are "
        "unknown. The reference call count on the target is cost(C), never cost(B)"
    ),
    "not_a_discovery_claim": (
        "the reference procedure is benchmark ground truth, not an agent discovery. Nothing "
        "in this packet is evidence that an agent can find or execute B on the target"
    ),
}

#: Per-task files a packet cites. Contents are never inlined; only path + hash.
TASK_EVIDENCE_FILES = (
    ("specs", "specs.json"),
    ("solution", "ground_truth/solution.py"),
    ("metadata", "ground_truth/metadata.json"),
    ("evaluation", "ground_truth/evaluation.py"),
    ("public_data", "ground_truth/public_data.json"),
    ("private_data", "ground_truth/private_data.json"),
)

#: Reference-solution context lines emitted on each side of a cited call site.
SNIPPET_CONTEXT_LINES = 3


class PacketBudgetError(RuntimeError):
    """Raised when a packet cannot be brought under its byte budget honestly."""


@dataclass(frozen=True)
class PacketLimits:
    """Every cap a packet respects.

    The defaults were calibrated against the 26 real reserve families: all of
    them serialize well under `max_packet_bytes` without any degradation step
    firing, so the caps bound the packet rather than routinely truncate it.
    """

    max_packet_bytes: int = 65_536
    max_string_chars: int = 800
    max_list_items: int = 12
    max_dict_keys: int = 40
    max_instruction_chars: int = 1_200
    #: Reference-solution snippet windows, per role (source and target).
    max_snippet_windows: int = 3
    max_snippet_lines: int = 12
    max_snippet_chars: int = 1_600
    #: API documentation excerpts.
    max_api_docs: int = 20
    max_api_fields: int = 40
    max_api_parameters: int = 12
    max_api_description_chars: int = 400
    #: Candidate-B routes, including weak and rejected ones.
    max_alternatives: int = 8
    #: Normalized state/setup difference blocks. Values inside a state diff can
    #: be long literals; they are capped much harder than route prose.
    max_change_evidence: int = 6
    max_state_changes: int = 8
    max_state_string_chars: int = 320
    max_seed_tables: int = 16
    max_evaluator_requirements: int = 6
    max_reference_block_chars: int = 600
    #: Per-block byte ceilings: no single evidence block may dominate a packet.
    max_state_block_bytes: int = 2_000
    max_role_block_bytes: int = 1_500
    max_route_block_bytes: int = 2_500
    #: Reference-procedure call-site outline, per role.
    max_call_sites: int = 12
    #: db seed files hashed per task.
    max_seed_files: int = 3
    #: Degradation steps allowed before a packet is declared unbounded.
    max_degradations: int = 256


def _repo_path(path: Path | str | None) -> str | None:
    if path is None:
        return None
    candidate = Path(path)
    try:
        return str(candidate.resolve().relative_to(ROOT))
    except (ValueError, OSError):
        return str(candidate)


def file_fact(path: Path | None) -> dict:
    """Path plus size and sha256, without ever reading the file into a packet."""

    if path is None:
        return {"path": None, "exists": False}
    fact: dict = {"path": _repo_path(path), "exists": path.is_file()}
    if fact["exists"]:
        payload = path.read_bytes()
        fact["bytes"] = len(payload)
        fact["sha256"] = hashlib.sha256(payload).hexdigest()
    return fact


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def packet_paths(family: str, packet_dir: Path | str) -> dict:
    """Deterministic packet locations for one family."""

    directory = Path(packet_dir) / family
    return {
        "path": _repo_path(directory / "packet.json"),
        "markdown_path": _repo_path(directory / "packet.md"),
    }


def _cap_text(text: object, limit: int) -> tuple[object, bool]:
    if isinstance(text, str) and len(text) > limit:
        return text[:limit] + "…[truncated]", True
    return text, False


def _shrink(value: object, limits: PacketLimits, stats: dict, path: str = "") -> object:
    """Bound one evidence block: cap strings, list lengths and dict breadth.

    Truncation is counted per block so a packet can report how much of each
    section survived instead of silently dropping evidence.
    """

    if isinstance(value, str):
        capped, truncated = _cap_text(value, limits.max_string_chars)
        if truncated:
            stats["strings"] = stats.get("strings", 0) + 1
        return capped
    if isinstance(value, dict):
        capped_items = list(value.items())[: limits.max_dict_keys]
        if len(capped_items) < len(value):
            stats["keys"] = stats.get("keys", 0) + (len(value) - len(capped_items))
        return {key: _shrink(item, limits, stats, f"{path}.{key}") for key, item in capped_items}
    if isinstance(value, (list, tuple)):
        capped_items = list(value)[: limits.max_list_items]
        if len(capped_items) < len(value):
            stats["items"] = stats.get("items", 0) + (len(value) - len(capped_items))
        return [_shrink(item, limits, stats, path) for item in capped_items]
    return value


def _bounded(value: object, limits: PacketLimits) -> tuple[object, dict]:
    stats: dict = {}
    return _shrink(value, limits, stats), stats


def _iter_lists(value: object, path: str = ""):
    """Deterministic depth-first walk over every list in a nested structure."""

    if isinstance(value, dict):
        for key in sorted(value):
            yield from _iter_lists(value[key], f"{path}.{key}")
    elif isinstance(value, list):
        yield path, value
        for item in value:
            yield from _iter_lists(item, path)


def _longest_string(value: object) -> tuple[str, str, int] | None:
    best: tuple[str, str, int] | None = None
    if isinstance(value, dict):
        for key in sorted(value):
            candidate = _longest_string(value[key])
            if candidate and (best is None or candidate[2] > best[2]):
                best = candidate
    elif isinstance(value, list):
        for item in value:
            candidate = _longest_string(item)
            if candidate and (best is None or candidate[2] > best[2]):
                best = candidate
    elif isinstance(value, str) and (best is None or len(value) > best[2]):
        best = ("", value, len(value))
    return best


def _truncate_longest_string(value: object) -> bool:
    """Halve the longest string anywhere in `value`; False when none is left."""

    found = _longest_string(value)
    if found is None or found[2] < 80:
        return False

    def walk(node: object) -> bool:
        if isinstance(node, dict):
            for key in sorted(node, key=lambda k: -len(node[k]) if isinstance(node[k], str) else 0):
                if isinstance(node[key], str) and len(node[key]) == found[2]:
                    node[key] = node[key][: max(40, found[2] // 2)] + "…[truncated]"
                    return True
                if walk(node[key]):
                    return True
        elif isinstance(node, list):
            for item in node:
                if isinstance(item, str) and len(item) == found[2]:
                    index = node.index(item)
                    node[index] = item[: max(40, found[2] // 2)] + "…[truncated]"
                    return True
                if walk(item):
                    return True
        return False

    return walk(value)


def _bounded_block(value: object, limits: PacketLimits, max_bytes: int) -> tuple[object, dict]:
    """Bound one evidence block by bytes as well as by shape.

    `_shrink` caps strings and list lengths, but a nested literal (a
    `private_data` file-path map, an evaluator requirement dump) can still be
    large after that. This adds a per-block byte ceiling and sheds the longest
    lists, then the longest strings, until the block fits.
    """

    stats: dict = {}
    shrunk = _shrink(value, limits, stats)
    if max_bytes <= 0 or len(json.dumps(shrunk, sort_keys=True)) <= max_bytes:
        return shrunk, stats
    stats["byte_limited"] = True
    for _ in range(limits.max_degradations):
        if len(json.dumps(shrunk, sort_keys=True)) <= max_bytes:
            return shrunk, stats
        candidates = [(len(items), path, items) for path, items in _iter_lists(shrunk) if items]
        if candidates:
            _, _, items = max(candidates, key=lambda entry: (entry[0], entry[1]))
            items.pop()
            stats["items"] = stats.get("items", 0) + 1
            continue
        if not _truncate_longest_string(shrunk):
            return shrunk, stats
        stats["strings"] = stats.get("strings", 0) + 1
    return shrunk, stats


def _truncation(section: str, stats: dict) -> dict | None:
    if not stats:
        return None
    return {"section": section, **stats}


def _narrow(limits: PacketLimits, **overrides) -> PacketLimits:
    return dataclasses.replace(limits, **overrides)


def _dedupe(values) -> list:
    seen, ordered = set(), []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def reserve_entries(artifact: dict) -> list[tuple[int, dict]]:
    """Every reserve family in the artifact, with its index in `families`.

    Ordered by family id rather than by the census review rank: `docs/29`
    section 1 warns against inheriting the offline ranking into the review pool.
    """

    indexed = list(enumerate(artifact.get("families", [])))
    reserves = [
        (index, record) for index, record in indexed if record.get("status") == RESERVE_STATUS
    ]
    return sorted(reserves, key=lambda pair: pair[1]["family"])


def build_reserve_manifest(
    artifact: dict,
    *,
    census_path: Path | str,
    data_root: Path | str,
    packet_dir: Path | str,
    limits: PacketLimits | None = None,
) -> dict:
    """Machine-readable list of every reserve family and its evidence paths.

    `docs/29` section 1: family ID, proposed source/target task IDs, the current
    admission reason, the candidate-record path, and the supporting benchmark
    files. Each file is reported as path + sha256 so a reviewer can check a
    claim against the local checkout.
    """

    limits = limits or PacketLimits()
    data_root = Path(data_root)
    census_path = Path(census_path)
    lineage = {
        entry["family"]: entry.get("lineage_warnings", [])
        for entry in artifact.get("family_lineage", [])
    }
    playbook = artifact.get("provenance", {}).get("playbook", {}) or {}

    families = []
    for index, record in reserve_entries(artifact):
        candidate = record["candidate"]
        role = record.get("state_differences", {}).get("role_assignment", {}) or {}
        task_ids = list(record["task_ids"])
        evidence = {task_id: task_evidence(data_root, task_id, limits) for task_id in task_ids}
        fact = file_fact(census_path)
        fact["container"] = _repo_path(census_path)
        families.append(
            {
                "family_id": record["family"],
                "status": record["status"],
                "source_task_id": (candidate.get("source_task_ids") or [None])[0],
                "target_task_id": (candidate.get("target_task_ids") or [None])[0],
                "source_task_ids": list(candidate.get("source_task_ids") or []),
                "target_task_ids": list(candidate.get("target_task_ids") or []),
                "task_ids": task_ids,
                "role_assignment": {
                    "status": role.get("status"),
                    "basis": role.get("basis"),
                    "selection_rule": role.get("selection_rule"),
                    "cost_was_not_consulted": role.get("cost_was_not_consulted"),
                },
                "admission": {
                    **_admission_fields(candidate),
                    "status": record["status"],
                    "status_reasons": list(record.get("status_reasons") or []),
                },
                "candidate_record": {
                    "path": fact["path"],
                    "json_pointer": f"/families/{index}",
                    "sha256": fact.get("sha256"),
                    "record_sha256": canonical_sha256(record),
                },
                "packet": packet_paths(record["family"], packet_dir),
                "evidence": {
                    "tasks": evidence,
                    "api_docs_db": file_fact(data_root / "base_dbs" / "api_docs.db"),
                    "playbook": {
                        "path": playbook.get("path"),
                        "sha256": playbook.get("sha256"),
                    },
                    "benchmark_version": artifact.get("provenance", {})
                    .get("benchmark", {})
                    .get("benchmark_version"),
                },
                "lineage_warnings": list(lineage.get(record["family"], [])),
            }
        )

    return {
        "manifest_version": MANIFEST_VERSION,
        "generated_by": "scripts/analysis/appworld_review_packets.py",
        "usage_scope": USAGE_SCOPE,
        "census": {
            "path": _repo_path(census_path),
            "sha256": file_fact(census_path).get("sha256"),
            "census_version": artifact.get("census_version"),
            "registry_version": artifact.get("registry_version"),
        },
        "unmeasured": dict(UNMEASURED),
        "counts": {
            "reserve_families": len(families),
            "census_families": len(artifact.get("families", [])),
            "packets": len(families),
        },
        "families": families,
    }


def task_evidence(data_root: Path, task_id: str, limits: PacketLimits) -> dict:
    """Path + hash for each task file a packet cites (never their contents)."""

    task_dir = Path(data_root) / "tasks" / task_id
    evidence = {key: file_fact(task_dir / relative) for key, relative in TASK_EVIDENCE_FILES}
    dbs_dir = task_dir / "dbs"
    seeds = sorted(dbs_dir.glob("*.jsonl")) if dbs_dir.is_dir() else []
    evidence["db_seed"] = [file_fact(path) for path in seeds[: limits.max_seed_files]]
    evidence["db_seed_files_total"] = len(seeds)
    return evidence


def _task_records(record: dict) -> dict[str, dict]:
    return {task["task_id"]: task for task in record.get("tasks", [])}


def _admission_fields(candidate: dict) -> dict:
    """Admission verdict and reason.

    `Candidate.to_dict` nests these under `admission`; the top-level fallbacks
    keep older or hand-built records readable instead of silently emitting null
    reason codes.
    """

    admission = candidate.get("admission", {}) or {}
    return {
        "status": admission.get("status") or candidate.get("status"),
        "reason_code": admission.get("reason_code") or candidate.get("reason_code"),
        "reason": admission.get("reason") or candidate.get("reason"),
    }


def _focus_apis(record: dict) -> tuple[list[str], str]:
    """APIs the packet should show snippets and docs for.

    Candidate-B routes first: they name the calls a reviewer has to judge. When
    the census named no route, the packet falls back to the reference
    procedure's own API outline, and says so — the reviewer still has to see
    what C does, but nothing here pretends a B route exists.
    """

    candidate_b = record["candidate"].get("candidate_B", {}) or {}
    apis = list(candidate_b.get("replaces") or [])
    for alternative in record.get("strategy", {}).get("alternatives", []):
        apis.extend(alternative.get("replaces") or [])
        cheaper = alternative.get("alternative_id", "").partition(":")[2]
        if cheaper:
            apis.append(cheaper)
        verification = alternative.get("verification", {}) or {}
        for key in ("probe_api", "bulk_api"):
            embedded = verification.get(key)
            if isinstance(embedded, dict) and embedded.get("name"):
                apis.append(embedded["name"])
    apis = _dedupe(apis)
    if apis:
        return apis, "candidate-B route APIs named by the census"

    signatures = record.get("strategy", {}).get("procedure_signatures", {}) or {}
    apis = _dedupe(
        token.split("[")[0].strip()
        for signature in signatures.values()
        for token in str(signature).split("->")
    )
    return apis, "reference-procedure outline: the census named no candidate-B route"


def _snippet_windows(
    role: str,
    task_id: str,
    solution_path: Path | None,
    call_sites: list[dict],
    focus: list[str],
    limits: PacketLimits,
) -> tuple[list[dict], dict | None, dict]:
    """Bounded context windows around the call sites that matter for B."""

    if solution_path is None or not solution_path.is_file():
        return (
            [],
            None,
            {
                "role": role,
                "task_id": task_id,
                "windows": 0,
                "reason": "no released reference solution",
            },
        )
    lines = solution_path.read_text(encoding="utf-8").splitlines()
    focus_set = set(focus)
    selected = [site for site in call_sites if site.get("name") in focus_set]
    basis = "candidate-B APIs"
    if not selected and call_sites:
        # No cited API is actually called by this reference program (e.g. the
        # census route names a bulk API C does not use). Show the program's own
        # first call sites so the reviewer can still judge the structure.
        selected = list(call_sites)[: limits.max_snippet_windows]
        basis = "reference call-site outline (no cited candidate-B API appears in this solution)"
    if not selected:
        return (
            [],
            None,
            {"role": role, "task_id": task_id, "windows": 0, "reason": "no call sites to cite"},
        )

    windows: list[dict] = []
    seen_ranges: list[tuple[int, int]] = []
    stats = {"strings": 0, "windows_dropped": 0, "lines_dropped": 0}
    for site in selected:
        if len(windows) >= limits.max_snippet_windows:
            stats["windows_dropped"] += 1
            continue
        line = int(site.get("line") or 0)
        if line < 1:
            stats["windows_dropped"] += 1
            continue
        start = max(1, line - SNIPPET_CONTEXT_LINES)
        end = min(len(lines), line + SNIPPET_CONTEXT_LINES)
        if any(start <= other_start and end >= other_end for other_start, other_end in seen_ranges):
            continue
        snippet_lines = lines[start - 1 : end]
        if len(snippet_lines) > limits.max_snippet_lines:
            stats["lines_dropped"] += len(snippet_lines) - limits.max_snippet_lines
            snippet_lines = snippet_lines[: limits.max_snippet_lines]
        text = "\n".join(snippet_lines)
        capped, was_truncated = _cap_text(text, limits.max_snippet_chars)
        if was_truncated:
            stats["strings"] += 1
        seen_ranges.append((start, end))
        windows.append(
            {
                "role": role,
                "task_id": task_id,
                "cite": site.get("name"),
                "line_range": [start, end],
                "code": capped,
                "truncated": was_truncated,
            }
        )
    facts = {
        "role": role,
        "task_id": task_id,
        "solution_lines": len(lines),
        "cited_call_sites": len(selected),
        "emitted_windows": len(windows),
        "emitted_lines": sum(
            window["line_range"][1] - window["line_range"][0] + 1 for window in windows
        ),
        "coverage": "bounded context windows only; the full solution is never inlined",
        "selection_basis": basis,
    }
    truncation = (
        {"section": f"reference_solution_snippets.{role}", **stats} if any(stats.values()) else None
    )
    return windows, truncation, facts


def _call_site_outline(
    call_sites: list[dict], limits: PacketLimits
) -> tuple[list[dict], dict | None]:
    """Compact normalized description of what the reference program calls."""

    fields = (
        "name",
        "line",
        "inside_loop",
        "via_pagination_helper",
        "read_fields",
        "guards",
        "resolution_key",
    )
    outline = [
        {key: site.get(key) for key in fields if site.get(key) not in (None, [], (), "")}
        for site in call_sites[: limits.max_call_sites]
    ]
    stats = {}
    if len(call_sites) > len(outline):
        stats["items"] = len(call_sites) - len(outline)
    return outline, ({"section": "reference_strategy_C.call_sites", **stats} if stats else None)


def _api_documentation(
    surface: ApiSurface | None,
    focus: list[str],
    signature_apis: list[str],
    limits: PacketLimits,
) -> tuple[list[dict], list[dict]]:
    """Documented request/response surface for the APIs in play, bounded."""

    ordered = _dedupe([*focus, *signature_apis])[: limits.max_api_docs]
    docs, truncations = [], []
    for name in ordered:
        doc = surface.doc(name) if surface is not None else None
        if doc is None:
            docs.append({"name": name, "documented": False})
            continue
        docs.append(
            {
                "name": name,
                "documented": True,
                "description": doc.description[: limits.max_api_description_chars],
                "parameters": [
                    {
                        "name": parameter.get("name"),
                        "type": parameter.get("type"),
                        "required": parameter.get("required"),
                    }
                    for parameter in doc.parameters[: limits.max_api_parameters]
                ],
                "parameters_total": len(doc.parameters),
                "response_shape": doc.response_shape,
                "response_fields": list(doc.response_fields[: limits.max_api_fields]),
                "response_fields_total": len(doc.response_fields),
            }
        )
    if surface is not None and len(_dedupe([*focus, *signature_apis])) > len(ordered):
        truncations.append(
            {
                "section": "public_api_documentation",
                "items": len(_dedupe([*focus, *signature_apis])) - len(ordered),
            }
        )
    return docs, truncations


def _state_setup_differences(record: dict, limits: PacketLimits) -> tuple[dict, list[dict]]:
    """Normalized source→target condition change, bounded per sub-block."""

    pair = (record.get("state_differences", {}) or {}).get("selected_pair") or {}
    truncations: list[dict] = []
    if not pair:
        return {
            "available": False,
            "reason": "the census recorded no analysable sibling pair",
        }, truncations

    narrow = _narrow(limits, max_list_items=limits.max_change_evidence)
    evidence, stats = _bounded_block(
        pair.get("change_evidence"), narrow, limits.max_state_block_bytes
    )
    truncation = _truncation("state_setup_differences.change_evidence", stats)
    if truncation:
        truncations.append(truncation)

    values = _narrow(
        narrow,
        max_list_items=limits.max_state_changes,
        max_dict_keys=24,
        max_string_chars=limits.max_state_string_chars,
    )
    block = _narrow(values, max_list_items=limits.max_state_changes)
    chunks = {
        "instruction": _bounded_block(
            pair.get("instruction"),
            _narrow(block, max_string_chars=limits.max_instruction_chars),
            limits.max_state_block_bytes,
        ),
        "public_data": _bounded_block(pair.get("public_data"), block, limits.max_state_block_bytes),
        "private_data": _bounded_block(
            pair.get("private_data"), block, limits.max_state_block_bytes
        ),
        "seed_state": _bounded_block(
            pair.get("seed_state"),
            _narrow(block, max_dict_keys=limits.max_seed_tables, max_string_chars=200),
            limits.max_state_block_bytes,
        ),
        "evaluator": _bounded_block(
            pair.get("evaluator"),
            _narrow(block, max_list_items=limits.max_evaluator_requirements, max_string_chars=400),
            limits.max_state_block_bytes,
        ),
        "reference": _bounded_block(
            pair.get("reference"),
            _narrow(block, max_string_chars=limits.max_reference_block_chars),
            limits.max_state_block_bytes,
        ),
    }
    normalized = {
        "available": True,
        "source_task_id": pair.get("source_task_id"),
        "target_task_id": pair.get("target_task_id"),
        "classification": pair.get("classification"),
        "classification_rationale": pair.get("classification_rationale"),
        "strategy_relevant_change": pair.get("strategy_relevant_change"),
        "route_changed": pair.get("route_changed"),
        "strategy_shift_witness": pair.get("strategy_shift_witness"),
        "same_reference_solution": pair.get("same_reference_solution"),
        "change_evidence": evidence,
        "per_block_byte_ceiling": limits.max_state_block_bytes,
        **{name: chunk for name, (chunk, _) in chunks.items()},
    }
    for name, (_, stats) in chunks.items():
        truncation = _truncation(f"state_setup_differences.{name}", stats)
        if truncation:
            truncations.append(truncation)
    return normalized, truncations


def _candidate_routes(record: dict, limits: PacketLimits) -> tuple[dict, list[dict]]:
    """Census B hypotheses: supported, weak, rejected, and none-at-all."""

    strategy = record.get("strategy", {})
    candidate = record["candidate"]
    candidate_b = candidate.get("candidate_B", {}) or {}
    truncations: list[dict] = []

    narrow = _narrow(limits, max_list_items=limits.max_alternatives, max_dict_keys=24)
    alternatives = [
        _bounded_block(alternative, narrow, limits.max_route_block_bytes)[0]
        for alternative in (strategy.get("alternatives") or [])[: limits.max_alternatives]
    ]
    if len(strategy.get("alternatives") or []) > len(alternatives):
        truncations.append(
            {
                "section": "candidate_b_routes.census_alternatives",
                "items": len(strategy.get("alternatives") or []) - len(alternatives),
            }
        )

    payload, stats = _bounded_block(candidate_b, narrow, limits.max_route_block_bytes)
    truncation = _truncation("candidate_b_routes.candidate_B", stats)
    if truncation:
        truncations.append(truncation)

    return (
        {
            "census_alternatives": alternatives,
            "census_alternatives_total": len(strategy.get("alternatives") or []),
            "alternatives_note": strategy.get("alternatives_note"),
            "structural_saving_call_sites": strategy.get("structural_saving_call_sites"),
            "candidate_B": payload,
            "candidate_B_status": candidate_b.get("status"),
            "verdict": candidate_b.get("verdict"),
            "evidence_grade": candidate_b.get("evidence_grade"),
            "rejected_alternatives": candidate_b.get("rejected_alternatives") or [],
            "refuted_candidates": candidate_b.get("refuted_candidates") or [],
            "c_vs_b_comparison": _bounded_block(
                candidate.get("c_vs_b_comparison"), narrow, limits.max_route_block_bytes
            )[0],
            "why_B_is_target_better": candidate.get("why_B_is_target_better"),
            "weak_or_rejected_note": (
                "every census route here is an offline structural hypothesis. 'weakly_supported' "
                "and 'refuted_by_review' routes are included on purpose: they are candidates a "
                "reviewer may rehabilitate or must rule out, never credited savings"
            ),
        },
        truncations,
    )


def _role_assignment_block(record: dict, limits: PacketLimits, truncations: list[dict]) -> dict:
    """Why these siblings are the source and the target.

    Deliberately a projection: the census role record embeds a full copy of the
    selected pair's change evidence, which the packet already carries once under
    `state_setup_differences`. Duplicating it would double the largest block for
    no reviewer benefit.
    """

    role = (record.get("state_differences", {}) or {}).get("role_assignment") or {}
    if not role:
        return {"available": False}
    selected = role.get("selected_pair") or {}
    projection = {
        "available": True,
        "status": role.get("status"),
        "basis": role.get("basis"),
        "selection_rule": role.get("selection_rule"),
        "rationale": role.get("rationale"),
        "cost_was_not_consulted": role.get("cost_was_not_consulted"),
        "review_override": role.get("review_override"),
        "source_task_ids": role.get("source_task_ids"),
        "target_task_ids": role.get("target_task_ids"),
        "selected_pair": {
            "classification": selected.get("classification"),
            "route_changed": selected.get("route_changed"),
            "strategy_shift_witness": selected.get("strategy_shift_witness"),
        },
        "note": (
            "roles come from sibling state-difference selection, never from the cost gap; "
            "the full change evidence is in `state_setup_differences`"
        ),
    }
    block, stats = _bounded_block(projection, limits, limits.max_role_block_bytes)
    truncation = _truncation("reference_strategy_C.role_assignment", stats)
    if truncation:
        truncations.append(truncation)
    return block


def build_packet(
    record: dict,
    *,
    data_root: Path | str,
    limits: PacketLimits | None = None,
    api_surface: ApiSurface | None = None,
    census_ref: dict | None = None,
    lineage_warnings: list[str] | None = None,
    consumer: str = PACKET_CONSUMER,
) -> dict:
    """One self-contained, bounded, research-side packet for a reserve family.

    `consumer` is checked against `memory_census.boundary`: a packet may only be
    handed to the research-side review, never to Generator/Reflector/Curator.
    """

    limits = limits or PacketLimits()
    assert_consumer_allowed(consumer)
    data_root = Path(data_root)
    truncations: list[dict] = []
    tasks = _task_records(record)
    candidate = record["candidate"]
    source_id = (candidate.get("source_task_ids") or [None])[0]
    target_id = (candidate.get("target_task_ids") or [None])[0]

    # --- instructions -----------------------------------------------------
    instruction_limits = _narrow(limits, max_string_chars=limits.max_instruction_chars)
    instructions, evidence_paths = {}, []
    for role, task_id in (("source", source_id), ("target", target_id)):
        task = tasks.get(task_id)
        if task is None:
            instructions[role] = {"task_id": task_id, "available": False}
            continue
        instructions[role] = {
            "task_id": task_id,
            "available": True,
            "split": task.get("split"),
            "difficulty": task.get("difficulty"),
            "num_apps": task.get("num_apps"),
            "num_apis": task.get("num_apis"),
            "num_api_calls": task.get("num_api_calls"),
            "has_reference_solution": task.get("has_reference_solution"),
            "instruction": _shrink(task.get("instruction"), instruction_limits, {}),
        }
        paths = task_evidence(data_root, task_id, limits)
        evidence_paths.append({"task_id": task_id, "files": paths})

    # --- normalized state/setup differences -------------------------------
    state_differences, state_truncations = _state_setup_differences(record, limits)
    truncations.extend(state_truncations)

    # --- reference strategy C and its measured-by-benchmark cost ----------
    strategy = record.get("strategy", {})
    signatures = strategy.get("procedure_signatures", {}) or {}
    per_task = strategy.get("per_task", {}) or {}
    focus, focus_basis = _focus_apis(record)
    signature_apis = _dedupe(
        token.split("[")[0].strip()
        for signature in signatures.values()
        for token in str(signature).split("->")
    )

    call_sites = {}
    for role, task_id in (("source", source_id), ("target", target_id)):
        outline, truncation = _call_site_outline(
            (per_task.get(task_id, {}) or {}).get("call_sites") or [], limits
        )
        call_sites[role] = {
            "task_id": task_id,
            "procedure_signature": signatures.get(task_id),
            "call_sites": outline,
        }
        if truncation:
            truncations.append({**truncation, "section": f"{truncation['section']}.{role}"})

    reference_cost, stats = _bounded(
        record.get("cost", {}).get("tasks") or [], _narrow(limits, max_list_items=4)
    )
    if stats:
        truncations.append({"section": "target_reference_public_api_cost.per_task", **stats})

    # --- bounded reference-solution snippets ------------------------------
    windows: list[dict] = []
    snippet_facts = []
    for role, task_id in (("source", source_id), ("target", target_id)):
        solution_path = data_root / "tasks" / str(task_id) / "ground_truth" / "solution.py"
        role_windows, truncation, facts = _snippet_windows(
            role,
            task_id,
            solution_path,
            (per_task.get(task_id, {}) or {}).get("call_sites") or [],
            focus,
            limits,
        )
        windows.extend(role_windows)
        snippet_facts.append(facts)
        if truncation:
            truncations.append(truncation)

    # --- public API documentation excerpts --------------------------------
    docs, doc_truncations = _api_documentation(api_surface, focus, signature_apis, limits)
    truncations.extend(doc_truncations)

    # --- candidate-B routes ----------------------------------------------
    routes, route_truncations = _candidate_routes(record, limits)
    truncations.extend(route_truncations)

    # --- gates, K0 overlap, provenance ------------------------------------
    gate, stats = _bounded(record.get("comparison_gate"), limits)
    if stats:
        truncations.append({"section": "comparison_gate", **stats})
    k0, stats = _bounded(candidate.get("k0_static_overlap"), limits)
    if stats:
        truncations.append({"section": "k0_static_playbook_overlap", **stats})

    playbook = (census_ref or {}).get("playbook") or {}
    provenance = {
        "census": {
            "path": (census_ref or {}).get("path"),
            "sha256": (census_ref or {}).get("sha256"),
            "json_pointer": (census_ref or {}).get("json_pointer"),
            "record_sha256": canonical_sha256(record),
            "census_version": (census_ref or {}).get("census_version"),
            "registry_version": (census_ref or {}).get("registry_version"),
        },
        "benchmark": {
            "data_root": _repo_path(data_root),
            "version": (census_ref or {}).get("benchmark_version"),
        },
        "api_docs_db": file_fact(data_root / "base_dbs" / "api_docs.db"),
        "playbook": {"path": playbook.get("path"), "sha256": playbook.get("sha256")},
        "tasks": evidence_paths,
        "evidence_drift": _evidence_drift(record, data_root, evidence_paths),
        "sources": [
            "data/tasks/<task_id>/specs.json",
            "data/tasks/<task_id>/ground_truth/solution.py",
            "data/tasks/<task_id>/ground_truth/public_data.json",
            "data/tasks/<task_id>/ground_truth/private_data.json",
            "data/tasks/<task_id>/dbs/<app>.jsonl",
            "data/base_dbs/api_docs.db",
            "experiments/playbooks/appworld_initial_playbook.txt",
            "artifacts/appworld_family_census/census.json",
        ],
    }

    packet = {
        "packet_version": PACKET_VERSION,
        "packet_id": record["family"],
        "usage_scope": USAGE_SCOPE,
        "consumer": consumer,
        "unmeasured": dict(UNMEASURED),
        "not_authorized": (
            "this packet authorizes no K_0 probe, no model rollout, no benchmark execution and "
            "no adaptive-loop injection; it is candidate-triage input only"
        ),
        "family": {
            "family_id": record["family"],
            "task_ids": list(record["task_ids"]),
            "source_task_id": source_id,
            "target_task_id": target_id,
            "source_task_ids": list(candidate.get("source_task_ids") or []),
            "target_task_ids": list(candidate.get("target_task_ids") or []),
            "admission": {
                **_admission_fields(candidate),
                "status": record["status"],
                "status_reasons": list(record.get("status_reasons") or []),
                "gates": _shrink((candidate.get("admission") or {}).get("gates"), limits, {}),
            },
            "lineage_warnings": list(lineage_warnings or []),
        },
        "instructions": instructions,
        "state_setup_differences": state_differences,
        "reference_strategy_C": {
            "role_assignment": _role_assignment_block(record, limits, truncations),
            "candidate_C": _shrink(candidate.get("candidate_C"), limits, {}),
            "why_C_is_source_appropriate": candidate.get("why_C_is_source_appropriate"),
            "reference_procedure_identical_across_family": strategy.get(
                "reference_procedure_identical_across_family"
            ),
            "procedure_signatures": _shrink(signatures, limits, {}),
            "call_site_outline": call_sites,
            "focus_apis": focus,
            "focus_basis": focus_basis,
        },
        "target_reference_public_api_cost": {
            "cost_C": _shrink(candidate.get("cost_C"), limits, {}),
            "c_success_on_target": _shrink(candidate.get("c_success_on_target"), limits, {}),
            "per_task_reference_counts": reference_cost,
            "unit": "public_api_calls",
            "basis": (
                "benchmark ground-truth metadata (`num_api_calls` for the released reference "
                "solution). This is cost(C); it is not cost(B)"
            ),
        },
        "candidate_b_routes": routes,
        "reference_solution_snippets": {
            "windows": windows,
            "per_role": snippet_facts,
            "limits": {
                "max_windows_per_role": limits.max_snippet_windows,
                "max_lines_per_window": limits.max_snippet_lines,
                "max_chars_per_window": limits.max_snippet_chars,
            },
        },
        "public_api_documentation": docs,
        "comparison_gate": gate,
        "k0_static_playbook_overlap": k0,
        "provenance": provenance,
    }
    packet["truncations"] = truncations
    return _enforce_byte_budget(packet, limits)


def _evidence_drift(record: dict, data_root: Path, evidence_paths: list[dict]) -> list[dict]:
    """Compare on-disk reference-solution hashes with the hashes the census saw."""

    recorded = (record.get("candidate", {}).get("evidence_provenance", {}) or {}).get(
        "per_task", {}
    ) or {}
    drift = []
    for entry in evidence_paths:
        task_id = entry["task_id"]
        expected = (recorded.get(task_id) or {}).get("solution_sha256")
        actual = (entry["files"].get("solution") or {}).get("sha256")
        if expected and actual and expected != actual:
            drift.append(
                {
                    "task_id": task_id,
                    "field": "solution_sha256",
                    "census": expected,
                    "local": actual,
                    "note": "local benchmark checkout has moved since the census ran",
                }
            )
    return drift


def _degradation_targets(packet: dict):
    """Deterministic order in which optional evidence is dropped.

    Only bounded evidence lists are droppable; required identity, gate and
    provenance fields are never touched, so a degraded packet stays usable.
    """

    return [
        (
            "reference_solution_snippets.windows",
            packet["reference_solution_snippets"]["windows"],
            1,
        ),
        ("public_api_documentation", packet["public_api_documentation"], 1),
        (
            "candidate_b_routes.census_alternatives",
            packet["candidate_b_routes"]["census_alternatives"],
            1,
        ),
        (
            "state_setup_differences.change_evidence",
            packet["state_setup_differences"].get("change_evidence", []),
            0,
        ),
        (
            "reference_strategy_C.call_site_outline.source.call_sites",
            packet["reference_strategy_C"]["call_site_outline"]["source"]["call_sites"],
            0,
        ),
        (
            "reference_strategy_C.call_site_outline.target.call_sites",
            packet["reference_strategy_C"]["call_site_outline"]["target"]["call_sites"],
            0,
        ),
        (
            "target_reference_public_api_cost.per_task_reference_counts",
            packet["target_reference_public_api_cost"]["per_task_reference_counts"],
            0,
        ),
        ("k0_static_playbook_overlap.matched_terms", _k0_terms(packet), 0),
    ]


def _k0_terms(packet: dict) -> list:
    block = packet.get("k0_static_playbook_overlap")
    if not isinstance(block, dict):
        return []
    terms = block.get("matched_scaffolding_terms")
    return terms if isinstance(terms, list) else []


def _dropped_label(item: object) -> dict:
    """Small identity tag for a dropped item, so the record stays auditable."""

    if isinstance(item, dict):
        keys = ("alternative_id", "name", "role", "task_id", "cite", "line_range", "kind")
        label = {key: item[key] for key in keys if key in item}
        return label or {"keys": sorted(item)[:8]}
    if isinstance(item, str):
        return {"text": item[:120]}
    return {"value": str(item)[:120]}


def _enforce_byte_budget(packet: dict, limits: PacketLimits) -> dict:
    """Drop optional evidence until the serialized packet fits its budget.

    The degradation record is part of the packet and is therefore counted in
    every size measurement; a packet that had to shed evidence says so.
    """

    degradations: list[dict] = []
    for _ in range(limits.max_degradations):
        if degradations:
            packet["degradations"] = degradations
        elif "degradations" in packet:
            del packet["degradations"]
        size = len(packet_text(packet).encode("utf-8"))
        if size <= limits.max_packet_bytes:
            return packet
        for label, container, minimum in _degradation_targets(packet):
            if len(container) > minimum:
                dropped = container.pop()
                degradations.append(
                    {
                        "section": label,
                        "reason": f"packet exceeded {limits.max_packet_bytes} bytes",
                        "dropped": _dropped_label(dropped),
                    }
                )
                break
        else:
            raise PacketBudgetError(
                f"packet for {packet.get('packet_id')!r} is {size} bytes and every optional "
                f"evidence block is already at its floor; refusing to emit an unbounded packet"
            )
    raise PacketBudgetError(
        f"packet for {packet.get('packet_id')!r} still exceeds {limits.max_packet_bytes} bytes "
        f"after {limits.max_degradations} degradation steps"
    )


def packet_text(packet: dict) -> str:
    """Canonical serialization: sorted keys, stable indent, trailing newline."""

    return json.dumps(packet, indent=2, sort_keys=True) + "\n"


def _render_code_block(code: str) -> str:
    return "\n".join(f"    {line}" for line in str(code).splitlines())


def render_packet_markdown(packet: dict) -> str:
    """Prompt-ready rendering of an already-bounded packet."""

    family = packet["family"]
    lines = [
        f"# Reserve review packet — {packet['packet_id']}",
        "",
        f"- packet version: `{packet['packet_version']}`",
        f"- family: `{family['family_id']}`",
        f"- source task: `{family['source_task_id']}`",
        f"- target task: `{family['target_task_id']}`",
        f"- census admission: `{family['admission']['reason_code']}` "
        f"— {family['admission']['reason']}",
        "",
        f"**Usage scope.** {packet['usage_scope']}",
        "",
        f"**Not authorized.** {packet['not_authorized']}",
        "",
        "## Unmeasured (do not assume)",
        "",
    ]
    for key, value in sorted(packet["unmeasured"].items()):
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Instructions", ""])
    for role in ("source", "target"):
        block = packet["instructions"].get(role, {})
        lines.append(f"### {role} — `{block.get('task_id')}`")
        lines.append("")
        lines.append(f"> {block.get('instruction')}")
        lines.append("")
        lines.append(
            f"- split `{block.get('split')}`, difficulty `{block.get('difficulty')}`, "
            f"reference public API calls `{block.get('num_api_calls')}`"
        )
        lines.append("")

    state = packet["state_setup_differences"]
    lines.extend(["## Normalized state/setup differences", ""])
    if state.get("available"):
        lines.append(f"- classification: `{state.get('classification')}`")
        lines.append(f"- strategy-relevant change: `{state.get('strategy_relevant_change')}`")
        lines.append(f"- route changed: `{state.get('route_changed')}`")
        lines.append(f"- rationale: {state.get('classification_rationale')}")
        for item in state.get("change_evidence") or []:
            lines.append(f"- change evidence: `{json.dumps(item, sort_keys=True)}`")
    else:
        lines.append(f"- unavailable: {state.get('reason')}")
    lines.append("")

    lines.extend(["## Reference strategy C", ""])
    lines.append(f"- {packet['reference_strategy_C'].get('why_C_is_source_appropriate')}")
    for role in ("source", "target"):
        outline = packet["reference_strategy_C"]["call_site_outline"].get(role, {})
        lines.append(f"- {role} procedure: `{outline.get('procedure_signature')}`")
    cost = packet["target_reference_public_api_cost"]
    lines.append(
        f"- target reference public API cost: `{cost['cost_C'].get('value')}` "
        f"{cost['unit']} ({cost['basis']})"
    )
    lines.append("")

    lines.extend(["## Candidate-B routes (census hypotheses)", ""])
    routes = packet["candidate_b_routes"]
    lines.append(f"- {routes['weak_or_rejected_note']}")
    lines.append(f"- census B status: `{routes['candidate_B_status']}`")
    lines.append(f"- alternatives note: {routes['alternatives_note']}")
    for alternative in routes["census_alternatives"]:
        lines.append(
            f"- `{alternative.get('alternative_id')}` ({alternative.get('verdict')}, "
            f"{alternative.get('saving_call_sites')} call site(s)): {alternative.get('summary')}"
        )
    lines.append("")

    lines.extend(["## Reference-solution snippets (bounded)", ""])
    for facts in packet["reference_solution_snippets"]["per_role"]:
        lines.append(
            f"- {facts.get('role')} `{facts.get('task_id')}`: "
            f"{facts.get('emitted_windows')} window(s), "
            f"{facts.get('emitted_lines')}/{facts.get('solution_lines')} lines, "
            f"{facts.get('selection_basis')}"
        )
    for window in packet["reference_solution_snippets"]["windows"]:
        lines.extend(
            [
                "",
                f"### {window['role']} `{window['task_id']}` "
                f"lines {window['line_range'][0]}-{window['line_range'][1]} "
                f"(cited: `{window.get('cite')}`)",
                "",
                "```python",
                _render_code_block(window["code"]),
                "```",
            ]
        )
    lines.append("")

    lines.extend(["## Public API documentation excerpts", ""])
    for doc in packet["public_api_documentation"]:
        if not doc.get("documented"):
            lines.append(f"- `{doc['name']}`: not present in the public API docs")
            continue
        lines.append(
            f"- `{doc['name']}` ({doc['response_shape']}): {doc['description']} "
            f"| params: {', '.join(str(p.get('name')) for p in doc['parameters'])} "
            f"| fields: {', '.join(doc['response_fields'])}"
        )
    lines.append("")

    gate = packet["comparison_gate"] or {}
    lines.extend(
        [
            "## Gates",
            "",
            f"- target forces comparison: `{gate.get('forces_comparison')}`",
            f"- K_0 static-playbook overlap: "
            f"`{(packet['k0_static_playbook_overlap'] or {}).get('level')}` "
            f"({(packet['k0_static_playbook_overlap'] or {}).get('statement')})",
            "",
            "## Provenance",
            "",
        ]
    )
    provenance = packet["provenance"]
    lines.append(
        f"- census: `{provenance['census']['path']}#{provenance['census']['json_pointer']}`"
    )
    lines.append(f"- census sha256: `{provenance['census']['sha256']}`")
    lines.append(f"- record sha256: `{provenance['census']['record_sha256']}`")
    lines.append(f"- api docs db: `{provenance['api_docs_db']['path']}`")
    lines.append(
        f"- playbook: `{provenance['playbook']['path']}` "
        f"sha256 `{provenance['playbook']['sha256']}`"
    )
    for task in provenance["tasks"]:
        for key, fact in sorted(task["files"].items()):
            if isinstance(fact, dict) and fact.get("path"):
                lines.append(
                    f"- `{task['task_id']}` {key}: `{fact['path']}` sha256 `{fact.get('sha256')}`"
                )
    drift = provenance.get("evidence_drift") or []
    lines.append(f"- evidence drift vs census hashes: {drift if drift else 'none'}")
    lines.append(f"- truncations: {packet.get('truncations') or 'none'}")
    lines.append("")
    return "\n".join(lines)
