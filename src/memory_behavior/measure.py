"""Deterministic measurement over persisted ACE artifacts.

Pure standard library and no runtime import, so the same functions serve the
corpus driver at run time and the research-side strategy-card extractor
offline. A card and its corpus index entry are therefore computed from the same
files by the same rules and can be compared field by field.

Everything here reads only what the ACE adapter persisted: executed actions,
public API observations, evaluator output, the playbook before/after and the
usage summary. Nothing reads hidden chain-of-thought, reference solutions or
evaluator ground truth (`AGENTS.md` sections 8-10).

API-name heuristics (`read_kind`, `state_changing`, `search_pattern`) label
behavior for triage. They are documented rules over public API names, not
semantic judgements, and unknown inputs are labeled `unknown` rather than
guessed.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

#: Pagination/ordering arguments that do not narrow a query.
PAGINATION_KEYS = frozenset({"page", "page_index", "page_limit", "limit", "offset", "sort_by"})

#: Argument names that identify one entity rather than filtering a collection.
IDENTIFIER_SUFFIXES = ("_id", "_ids", "_name", "_names", "_email", "_token", "_number", "_code")

#: Public API verbs that change state. Read verbs are everything else.
STATE_CHANGING_PREFIXES = (
    "add",
    "archive",
    "book",
    "cancel",
    "clear",
    "comment",
    "complete",
    "create",
    "delete",
    "download",
    "follow",
    "invite",
    "join",
    "leave",
    "like",
    "mark",
    "move",
    "order",
    "pay",
    "post",
    "register",
    "remove",
    "rename",
    "reply",
    "schedule",
    "send",
    "set",
    "share",
    "star",
    "subscribe",
    "transfer",
    "unfollow",
    "unlike",
    "unstar",
    "update",
    "upload",
    "write",
)

ENUMERATE_PREFIXES = ("show", "list")
FILTERED_PREFIXES = ("search", "find", "filter", "query")
DIRECT_PREFIXES = ("get", "read", "view", "fetch", "load", "download", "show", "list")

CALL_RE = re.compile(
    r"\bapis\.(?P<app>[A-Za-z_][A-Za-z0-9_]*)\.(?P<api>[A-Za-z_][A-Za-z0-9_]*)\s*\("
)
ARG_KEY_RE = re.compile(r"(?:^|,)\s*([A-Za-z_][A-Za-z0-9_]*)\s*=")
ENTRY_RE = re.compile(r"^\[(?P<entry_id>[^\]\s]+)\]\s*(?P<content>.*)$")
SECTION_RE = re.compile(r"^#{1,6}\s*(?P<title>.+?)\s*$")
INSTRUCTION_RE = re.compile(r"^Task:\s*(?P<instruction>.+?)\s*$", re.MULTILINE)


def selection_digest(manifest: dict) -> str:
    """Content digest of a selection/analysis manifest, shared by producers.

    Lives here so the corpus driver can re-check a frozen manifest without
    importing the research-side selection module.
    """

    payload = json.dumps(manifest, ensure_ascii=False, sort_keys=True, allow_nan=False)
    return sha256_bytes(payload.encode("utf-8"))


def read_json(path: Path):
    """Parsed JSON, or None when the file is absent or unreadable."""

    path = Path(path)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def read_available_json(path: Path):
    """Payload of an ``available(...)`` artifact, preserving ordinary JSON.

    ArtifactSink wraps selected values, but manifests and memory snapshots are
    ordinary JSON. The latter are core reset and outcome evidence.
    """

    value = read_json(path)
    if isinstance(value, dict) and value.get("status") == "available":
        return value.get("data")
    if isinstance(value, dict) and value.get("status") == "unavailable":
        return None
    return value
    return None


def read_jsonl(path: Path) -> list[dict]:
    """Every decodable JSON line; malformed lines are skipped, not invented."""

    path = Path(path)
    if not path.exists():
        return []
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            events.append(value)
    return events


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_file(path: Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def artifact_digests(directory: Path, *, skip_directories=("native",)) -> dict:
    """Path + digest index of one task directory; never the raw payloads."""

    directory = Path(directory)
    files: dict[str, str] = {}
    for path in sorted(directory.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(directory)
        if relative.parts and relative.parts[0] in skip_directories:
            continue
        files[str(relative)] = sha256_file(path)
    combined = hashlib.sha256()
    for name, digest in sorted(files.items()):
        combined.update(f"{name}:{digest}\n".encode())
    return {"count": len(files), "files": files, "combined_sha256": combined.hexdigest()}


def evaluator_success(evaluator) -> bool | None:
    """Native evaluator success, or None when the artifact does not carry it."""

    if not isinstance(evaluator, dict):
        return None
    tracker = evaluator.get("tracker")
    if isinstance(tracker, dict) and isinstance(tracker.get("success"), bool):
        return tracker["success"]
    return None


def public_call_counts(events) -> dict:
    """Public API responses and failures counted separately, from real events.

    `public_api_response` is emitted once per dispatched public call, before the
    native failure check can raise, so a failed call still appears here. A call
    counts as failed when the native response status is not 200 — the same
    condition `appworld.requester.raise_if_failure` uses. Rejected (capability
    or path-parameter refused before dispatch) and rate-limited calls are kept
    in their own counters and are never added to the dispatched total.
    """

    dispatched, failed = 0, 0
    rejected, limited = 0, 0
    status_histogram: dict[str, int] = {}
    failures: list[dict] = []
    for event in events:
        kind = event.get("kind")
        if kind == "public_api_response":
            dispatched += 1
            status = event.get("status_code")
            status_histogram[str(status)] = status_histogram.get(str(status), 0) + 1
            if status != 200:
                failed += 1
                failures.append(
                    {
                        "step": event.get("step"),
                        "app": event.get("app"),
                        "api": event.get("api"),
                        "status_code": status,
                    }
                )
        elif kind == "public_api_rejected":
            rejected += 1
        elif kind == "public_api_limit":
            limited += 1
    return {
        "public_api_responses": dispatched,
        "successful_public_calls": dispatched - failed,
        "failed_public_calls": failed,
        "rejected_public_calls": rejected,
        "rate_limited_public_calls": limited,
        "status_histogram": dict(sorted(status_histogram.items())),
        "failed_call_sites": failures,
        "counted_from": "observations.jsonl public_api_response events",
    }


def executed_calls(code: str) -> list[dict]:
    """Public API calls appearing in one executed code block, in source order.

    Argument names come from a bounded textual scan of the call's argument list,
    so a nested call inside an argument is not attributed to the outer call.
    Only names are recorded; values stay in the raw action artifact.
    """

    calls = []
    for match in CALL_RE.finditer(code or ""):
        tail = code[match.end() :]
        depth, end = 1, len(tail)
        for position, character in enumerate(tail):
            if character == "(":
                depth += 1
            elif character == ")":
                depth -= 1
                if depth == 0:
                    end = position
                    break
        arguments = tail[:end]
        keys = sorted({key for key in ARG_KEY_RE.findall(arguments) if key not in PAGINATION_KEYS})
        calls.append({"app": match.group("app"), "api": match.group("api"), "arg_keys": keys})
    return calls


def calls_from_actions(actions) -> list[dict]:
    """Every executed call with its step index, in execution order."""

    calls = []
    for action in actions:
        for call in executed_calls(action.get("code", "")):
            calls.append({**call, "step": action.get("step")})
    return calls


def strategy_signature(calls) -> list[str]:
    """Ordered unique `app.api` sequence: what the agent actually did."""

    signature = []
    for call in calls:
        name = f"{call['app']}.{call['api']}"
        if name not in signature:
            signature.append(name)
    return signature


def is_state_changing(call) -> bool:
    api = call["api"]
    if call["app"] == "supervisor":
        return False
    return api.startswith(STATE_CHANGING_PREFIXES) or api in ("complete_task",)


def state_changing_calls(calls) -> list[str]:
    return [f"{call['app']}.{call['api']}" for call in calls if is_state_changing(call)]


def read_kind(call) -> str | None:
    """`enumerate` | `filtered` | `direct` | None for a non-read call."""

    api = call["api"]
    if call["app"] == "supervisor" or is_state_changing(call):
        return None
    has_identifier = any(key.endswith(IDENTIFIER_SUFFIXES) for key in call["arg_keys"])
    if api.startswith(FILTERED_PREFIXES):
        return "direct" if has_identifier else "filtered"
    if api.startswith(ENUMERATE_PREFIXES) or api.startswith(DIRECT_PREFIXES):
        if not call["arg_keys"]:
            return "enumerate"
        return "direct" if has_identifier else "filtered"
    if call["arg_keys"]:
        return "filtered"
    return None


def search_pattern(calls) -> str:
    """Aggregate read shape: enumerate/filtered/direct/mixed/unknown."""

    kinds = [kind for kind in (read_kind(call) for call in calls) if kind]
    if not kinds:
        return "unknown"
    unique = set(kinds)
    if len(unique) == 1:
        return unique.pop()
    return "mixed"


def identity_resolution(calls) -> str:
    """Whether the run resolved an entity through chained lookups."""

    kinds = [read_kind(call) for call in calls]
    if not any(kinds):
        return "unknown"
    first_lookup = next(
        (index for index, kind in enumerate(kinds) if kind in ("enumerate", "filtered")), None
    )
    if first_lookup is None:
        return "direct" if any(kind == "direct" for kind in kinds) else "none"
    if any(kind == "direct" for kind in kinds[first_lookup + 1 :]):
        return "multi_hop"
    return "none"


def repeated_work(calls) -> list[dict]:
    """Identical `app.api` calls with identical argument names, two or more times."""

    seen: dict[tuple, list] = {}
    for call in calls:
        key = (call["app"], call["api"], tuple(call["arg_keys"]))
        seen.setdefault(key, []).append(call.get("step"))
    repeated = [
        {"call": f"{key[0]}.{key[1]}", "count": len(steps), "steps": steps}
        for key, steps in seen.items()
        if len(steps) > 1
    ]
    return sorted(repeated, key=lambda item: (-item["count"], item["call"]))


def normalize_section(title: str) -> str:
    """Curator section names, normalized the way the native curator does."""

    return title.strip().lower().replace(" ", "_").replace("&", "and").rstrip(":")


def playbook_entries(playbook: str) -> list[dict]:
    """`[id] content` bullets with the section they appear under, in order.

    The format is the upstream playbook contract: `## SECTION` headings and one
    `[id]` bullet per entry. Continuation lines are joined to the entry they
    belong to; text before the first entry is ignored.
    """

    entries: list[dict] = []
    section = "unknown"
    current: dict | None = None
    for raw_line in (playbook or "").splitlines():
        line = raw_line.strip()
        heading = SECTION_RE.match(line)
        if heading:
            section = normalize_section(heading.group("title"))
            current = None
            continue
        entry = ENTRY_RE.match(line)
        if entry:
            current = {
                "entry_id": entry.group("entry_id"),
                "section": section,
                "content": entry.group("content").strip(),
            }
            entries.append(current)
        elif current is not None and line:
            current["content"] = f"{current['content']} {line}".strip()
    return entries


def playbook_delta(before: str, after: str) -> dict:
    """Exact added/removed entries between two playbook states."""

    before_entries = playbook_entries(before)
    after_entries = playbook_entries(after)
    before_ids = {entry["entry_id"] for entry in before_entries}
    after_ids = {entry["entry_id"] for entry in after_entries}
    before_text = {entry["entry_id"]: entry["content"] for entry in before_entries}
    after_text = {entry["entry_id"]: entry["content"] for entry in after_entries}
    added = [entry for entry in after_entries if entry["entry_id"] not in before_ids]
    removed = [entry for entry in before_entries if entry["entry_id"] not in after_ids]
    edited = [
        {
            "entry_id": entry_id,
            "before": before_text[entry_id],
            "after": after_text[entry_id],
            "section": next(e["section"] for e in after_entries if e["entry_id"] == entry_id),
        }
        for entry_id in sorted(before_ids & after_ids)
        if before_text[entry_id] != after_text[entry_id]
    ]
    return {
        "added": added,
        "removed": removed,
        "edited": edited,
        "entries_before": len(before_entries),
        "entries_after": len(after_entries),
        "changed": bool(added or removed or edited),
    }


def instruction_from_messages(messages) -> str | None:
    """Fallback instruction recovery from the visible Generator prompt.

    The native Generator prompt renders `Task: <instruction>` on its own line;
    only messages the API actually returned are scanned, and no other part of
    the prompt is interpreted.
    """

    for message in messages:
        if message.get("role") != "user":
            continue
        matches = INSTRUCTION_RE.findall(message.get("content") or "")
        if matches:
            return matches[-1].strip()
    return None
