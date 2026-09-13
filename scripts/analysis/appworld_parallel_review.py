"""Run the bounded DeepSeek review over every AppWorld reserve packet.

This is a deliberately narrow, research-side triage script.  It does not
execute AppWorld, ACE, an actor, or an updater.  It stores only structured
review conclusions and sanitized usage telemetry; provider response bodies and
credentials are never persisted.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from memory_validation.provider import load_key  # noqa: E402
from memory_validation.telemetry import PriceTable  # noqa: E402

PACKET_ROOT = ROOT / "artifacts/appworld_review_packets"
DEFAULT_OUT = ROOT / "artifacts/appworld_parallel_review"
MODEL = "deepseek-flash[1m]"
ENDPOINT = "https://api.deepseek.com/anthropic/v1/messages"
# The first pass showed that 1,400 tokens can truncate a valid JSON object
# while the model is listing bounded evidence. This remains a small output cap,
# but leaves room for a complete strict object and does not permit free prose.
MAX_OUTPUT_TOKENS = 5_000
RETRY_LIMIT = 1

VERDICTS = {"promote_to_scripted_validation", "reserve", "reject"}
STATUSES = {"supported", "unknown", "false"}
SCOPES = {"supported", "uncertain", "refuted"}
TOP_KEYS = {
    "family",
    "source_task",
    "target_task",
    "verdict",
    "confidence",
    "candidate_B",
    "source_C_natural",
    "target_C_still_successful",
    "target_forces_comparison",
    "scope_equivalence",
    "privileged_information_needed_by_B",
    "evidence",
    "execution_checks_required",
    "rejection_reasons",
}
CANDIDATE_KEYS = {
    "summary",
    "public_api_route",
    "replaces_C_steps",
    "estimated_min_saving_calls",
    "saving_basis",
}
SOURCE_KEYS = {"verdict", "reason"}
TARGET_KEYS = {"status", "reason"}
EVIDENCE_KEYS = {"source", "claim"}

SYSTEM_PROMPT = """You are an adversarial scientific reviewer for one bounded AppWorld
strategy-lock-in packet. The packet is research-side privileged evidence for
candidate triage only. Do not seek a positive result and do not use hidden
chain-of-thought.

Answer the registered question: does the packet support a concrete target
strategy B that preserves task semantics and entity scope while plausibly
removing unnecessary public API work from strategy C? Attack shortcuts: global
versus user-scoped entities, omitted required entities, evaluator/setup/ground
truth dependence, data-volume-only gaps, explicit comparison requirements,
reference-code static artifacts, unsupported API response fields, and changed
task semantics.

Return ONLY one JSON object matching the supplied schema. Do not add keys,
markdown, commentary, measured costs, execution results, or model-discovery
claims. `estimated_min_saving_calls` is a hypothesis/bound only. `supported`
for C means supported by packet evidence, not a new benchmark execution.
Use exact API names from the packet in `public_api_route`. Use exact packet
paths or section references present in the packet for evidence.source.
Keep the response compact: summary/reasons under 240 characters each,
at most 4 evidence items, at most 4 execution checks, and at most 6 rejection
reasons. Do not cite a sibling task or file unless its exact path is present in
the packet. The full answer should fit comfortably below 1,500 tokens.
"""

SCHEMA_TEXT = json.dumps(
    {
        "family": "...",
        "source_task": "...",
        "target_task": "...",
        "verdict": "promote_to_scripted_validation|reserve|reject",
        "confidence": 0.0,
        "candidate_B": {
            "summary": "...",
            "public_api_route": ["exact.app_api"],
            "replaces_C_steps": ["..."],
            "estimated_min_saving_calls": 0,
            "saving_basis": "hypothesis/bound, not measured cost(B)",
        },
        "source_C_natural": {"verdict": True, "reason": "..."},
        "target_C_still_successful": {"status": "supported|unknown|false", "reason": "..."},
        "target_forces_comparison": False,
        "scope_equivalence": "supported|uncertain|refuted",
        "privileged_information_needed_by_B": False,
        "evidence": [{"source": "packet path or section", "claim": "..."}],
        "execution_checks_required": ["..."],
        "rejection_reasons": ["reason code or concise reason"],
    },
    sort_keys=True,
)


def _packet_text(packet: dict) -> str:
    return json.dumps(packet, sort_keys=True, ensure_ascii=False)


def _exact_dict(value: object, keys: set[str], name: str, errors: list[str]) -> dict | None:
    if not isinstance(value, dict):
        errors.append(f"{name}: expected object")
        return None
    extra = set(value) - keys
    missing = keys - set(value)
    if extra:
        errors.append(f"{name}: unexpected keys {sorted(extra)}")
    if missing:
        errors.append(f"{name}: missing keys {sorted(missing)}")
    return value


def _strings(value: object, name: str, errors: list[str]) -> bool:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        errors.append(f"{name}: expected list of strings")
        return False
    return True


def _section_reference_exists(reference: str, packet: dict) -> bool:
    """Accept an exact path, path-with-line-suffix, or resolvable packet path."""

    reference = reference.strip().strip("`")
    packet_text = _packet_text(packet)
    if reference in packet_text:
        return True
    # Evidence paths may carry a line number or JSON fragment after the exact
    # repository-relative path. Only accept the suffix when the base path is a
    # concrete path value already present in this packet.
    path_values = []

    def collect(value: object) -> None:
        if isinstance(value, dict):
            for item in value.values():
                collect(item)
        elif isinstance(value, list):
            for item in value:
                collect(item)
        elif isinstance(value, str) and "/" in value and len(value) >= 8:
            path_values.append(value)

    collect(packet)
    if any(path in reference for path in path_values):
        return True

    dotted = reference.removeprefix("packet.").replace("/", ".")
    tokens = [token for token in re.split(r"\.|\[|\]", dotted) if token]
    current: object = packet
    for token in tokens:
        if isinstance(current, dict) and token in current:
            current = current[token]
        elif isinstance(current, list) and token.isdigit() and int(token) < len(current):
            current = current[int(token)]
        else:
            return False
    return True


def validate_review(review: object, packet: dict) -> list[str]:
    """Deterministic schema/evidence checks; no reviewer prose is trusted."""

    errors: list[str] = []
    top = _exact_dict(review, TOP_KEYS, "review", errors)
    if top is None:
        return errors
    family = packet["family"]
    for field, expected in (
        ("family", family["family_id"]),
        ("source_task", family["source_task_id"]),
        ("target_task", family["target_task_id"]),
    ):
        if top.get(field) != expected:
            errors.append(f"{field}: does not match packet ({expected!r})")
    if top.get("verdict") not in VERDICTS:
        errors.append("verdict: invalid enum")
    if type(top.get("confidence")) not in (int, float) or not 0 <= top["confidence"] <= 1:
        errors.append("confidence: expected number in [0, 1]")

    candidate = _exact_dict(top.get("candidate_B"), CANDIDATE_KEYS, "candidate_B", errors)
    if candidate is not None:
        if not isinstance(candidate.get("summary"), str):
            errors.append("candidate_B.summary: expected string")
        route = candidate.get("public_api_route")
        if _strings(route, "candidate_B.public_api_route", errors):
            known = {
                doc["name"]
                for doc in packet.get("public_api_documentation", [])
                if doc.get("documented")
            }
            for api in route:
                if api not in known:
                    errors.append(f"candidate_B.public_api_route: API not in packet docs: {api}")
        _strings(candidate.get("replaces_C_steps"), "candidate_B.replaces_C_steps", errors)
        saving = candidate.get("estimated_min_saving_calls")
        if type(saving) is not int or saving < 0:
            errors.append("candidate_B.estimated_min_saving_calls: expected nonnegative integer")
        if not isinstance(candidate.get("saving_basis"), str):
            errors.append("candidate_B.saving_basis: expected string")

    source = _exact_dict(top.get("source_C_natural"), SOURCE_KEYS, "source_C_natural", errors)
    if source is not None:
        if type(source.get("verdict")) is not bool or not isinstance(source.get("reason"), str):
            errors.append("source_C_natural: invalid fields")
    target = _exact_dict(
        top.get("target_C_still_successful"), TARGET_KEYS, "target_C_still_successful", errors
    )
    if target is not None:
        if target.get("status") not in STATUSES or not isinstance(target.get("reason"), str):
            errors.append("target_C_still_successful: invalid fields")
    if type(top.get("target_forces_comparison")) is not bool:
        errors.append("target_forces_comparison: expected boolean")
    if top.get("scope_equivalence") not in SCOPES:
        errors.append("scope_equivalence: invalid enum")
    if type(top.get("privileged_information_needed_by_B")) is not bool:
        errors.append("privileged_information_needed_by_B: expected boolean")
    evidence = top.get("evidence")
    if not isinstance(evidence, list) or len(evidence) > 4:
        errors.append("evidence: expected list with at most 4 items")
    else:
        for index, item in enumerate(evidence):
            item_dict = _exact_dict(item, EVIDENCE_KEYS, f"evidence[{index}]", errors)
            if item_dict is not None:
                source_value = item_dict.get("source")
                if not isinstance(source_value, str) or not source_value.strip():
                    errors.append(f"evidence[{index}].source: expected nonempty string")
                elif not _section_reference_exists(source_value, packet):
                    errors.append(f"evidence[{index}].source: reference is absent from packet")
                if not isinstance(item_dict.get("claim"), str) or not item_dict["claim"].strip():
                    errors.append(f"evidence[{index}].claim: expected nonempty string")
    checks = top.get("execution_checks_required")
    if _strings(checks, "execution_checks_required", errors) and len(checks) > 4:
        errors.append("execution_checks_required: at most 4 items")
    reasons = top.get("rejection_reasons")
    if _strings(reasons, "rejection_reasons", errors) and len(reasons) > 6:
        errors.append("rejection_reasons: at most 6 items")

    gate_forces = bool((packet.get("comparison_gate") or {}).get("forces_comparison"))
    if gate_forces and top.get("target_forces_comparison") is not True:
        errors.append("target_forces_comparison: contradicts packet gate")
    # These are valid structured negative findings, not malformed output. The
    # aggregator turns them into a deterministic reject and preserves the
    # conclusion for audit.

    # Catch prohibited positive claims while allowing ordinary statements that
    # say execution is still required or that a value is unknown.
    prose = json.dumps(top, sort_keys=True).lower()
    positive_patterns = (
        r"cost\s*\(\s*b\s*\)\s*(?:=|is)\s*\d",
        r"b_success_on_target\s*[=:]\s*(?:true|verified|established)",
        r"k0[_ ]discoverability\s*[=:]\s*(?:true|verified|established)",
        r"(?<!not )measured\s+(?:cost|saving).*\bb\b",
        r"b\s+(?:was|is)\s+(?:executed|measured|discovered)\b",
    )
    for pattern in positive_patterns:
        if re.search(pattern, prose):
            errors.append("review contains an unexecuted positive B/cost/discovery claim")
            break
    return errors


def meaningful_saving(review: dict, packet: dict) -> bool:
    saving = review["candidate_B"]["estimated_min_saving_calls"]
    cost = (packet.get("target_reference_public_api_cost") or {}).get("cost_C") or {}
    value = cost.get("value")
    return (
        type(saving) is int
        and saving >= 3
        or (type(saving) is int and type(value) is int and value > 0 and saving / value >= 0.25)
    )


def route_key(review: dict) -> tuple:
    candidate = review["candidate_B"]
    return (
        tuple(candidate["public_api_route"]),
        tuple(step.strip().lower() for step in candidate["replaces_C_steps"]),
    )


def reason_code(review: dict, packet: dict) -> str:
    if review.get("target_forces_comparison"):
        return "target_forces_comparison"
    if review.get("scope_equivalence") == "refuted":
        return "scope_refuted"
    if review.get("privileged_information_needed_by_B"):
        return "privileged_information_required"
    if not review.get("source_C_natural", {}).get("verdict"):
        return "source_C_not_natural"
    if not review.get("candidate_B", {}).get("public_api_route"):
        return "no_concrete_B_route"
    if not meaningful_saving(review, packet):
        return "saving_not_meaningful"
    return "reviewer_reject"


def _request(prompt: str, key: str, timeout: int) -> tuple[dict | None, dict]:
    body = {
        "model": MODEL,
        "max_tokens": MAX_OUTPUT_TOKENS,
        "temperature": 0,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": prompt}],
    }
    request = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
        method="POST",
    )
    started = time.monotonic()
    telemetry: dict = {
        "model": MODEL,
        "latency_seconds": None,
        "status": "failed",
        "input_tokens": None,
        "output_tokens": None,
        "cached_input_tokens": None,
        "estimated_cost_usd": None,
    }
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        telemetry["status"] = f"http_{error.code}"
        telemetry["latency_seconds"] = round(time.monotonic() - started, 3)
        return None, telemetry
    except (OSError, ValueError, TimeoutError):
        telemetry["status"] = "request_failed"
        telemetry["latency_seconds"] = round(time.monotonic() - started, 3)
        return None, telemetry
    telemetry["latency_seconds"] = round(time.monotonic() - started, 3)
    usage = payload.get("usage") if isinstance(payload, dict) else None
    if isinstance(usage, dict):
        telemetry["input_tokens"] = usage.get("input_tokens")
        telemetry["output_tokens"] = usage.get("output_tokens")
        telemetry["cached_input_tokens"] = usage.get("cache_read_input_tokens")
        if type(telemetry["input_tokens"]) is int and type(telemetry["output_tokens"]) is int:
            cached = telemetry["cached_input_tokens"]
            if type(cached) is not int or cached < 0 or cached > telemetry["input_tokens"]:
                cached = 0
                telemetry["cached_input_tokens"] = 0
            telemetry["estimated_cost_usd"] = PriceTable().estimate(
                telemetry["input_tokens"], cached, telemetry["output_tokens"]
            )
    blocks = payload.get("content", []) if isinstance(payload, dict) else []
    text = "".join(block.get("text", "") for block in blocks if isinstance(block, dict))
    telemetry["status"] = "completed"
    return {"text": text}, telemetry


def _parse_json(text: str) -> object:
    return json.loads(text.strip())


def review_one(packet_path: Path, reviewer: str, key: str, timeout: int) -> dict:
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    base_prompt = (
        f"Review pass: {reviewer}. Do not coordinate with another pass.\n"
        f"Required JSON schema:\n{SCHEMA_TEXT}\n\n"
        f"Bounded packet JSON:\n{_packet_text(packet)}"
    )
    attempts = []
    for attempt in range(RETRY_LIMIT + 1):
        prompt = base_prompt
        if attempts:
            prompt += (
                "\n\nYour previous output failed deterministic validation with these errors; "
                "return corrected JSON only:\n"
            )
            prompt += "\n".join(f"- {error}" for error in attempts[-1]["validation_errors"])
        response, telemetry = _request(prompt, key, timeout)
        entry = {"attempt": attempt, "telemetry": telemetry}
        if response is None:
            entry["validation_errors"] = ["provider request failed"]
            attempts.append(entry)
            continue
        try:
            parsed = _parse_json(response["text"])
        except (TypeError, ValueError, json.JSONDecodeError):
            entry["validation_errors"] = ["response was not strict JSON"]
            attempts.append(entry)
            continue
        errors = validate_review(parsed, packet)
        entry["review"] = parsed
        entry["validation_errors"] = errors
        attempts.append(entry)
        if not errors:
            return {
                "family": packet["packet_id"],
                "reviewer": reviewer,
                "status": "usable",
                "attempts": attempts,
                "final": parsed,
            }
    return {
        "family": packet["packet_id"],
        "reviewer": reviewer,
        "status": "unusable_review",
        "attempts": attempts,
        "final": None,
    }


def adjudicate_one(
    packet: dict,
    primary: list[dict],
    key: str,
    timeout: int,
) -> dict:
    """Run the third review only for a substantive primary disagreement."""

    conclusions = [item["final"] for item in primary if item["status"] == "usable"]
    prompt = (
        "This is an adjudication pass, not a vote. Inspect the original bounded packet and the "
        "two structured primary conclusions below. Re-evaluate the evidence independently, "
        "resolve route/scope/semantic disagreements conservatively, and return only the required "
        "JSON schema. Do not add hidden reasoning or claim execution results.\n\n"
        f"Required JSON schema:\n{SCHEMA_TEXT}\n\n"
        f"Original bounded packet JSON:\n{_packet_text(packet)}\n\n"
        "Primary structured conclusions:\n"
        f"{json.dumps(conclusions, sort_keys=True, ensure_ascii=False)}"
    )
    attempts = []
    for attempt in range(RETRY_LIMIT + 1):
        current_prompt = prompt
        if attempts:
            current_prompt += (
                "\n\nThe previous adjudication output failed deterministic validation. "
                "Return corrected JSON only. Errors:\n"
                + "\n".join(f"- {error}" for error in attempts[-1]["validation_errors"])
            )
        response, telemetry = _request(current_prompt, key, timeout)
        entry = {"attempt": attempt, "telemetry": telemetry}
        if response is None:
            entry["validation_errors"] = ["provider request failed"]
            attempts.append(entry)
            continue
        try:
            parsed = _parse_json(response["text"])
        except (TypeError, ValueError, json.JSONDecodeError):
            entry["validation_errors"] = ["response was not strict JSON"]
            attempts.append(entry)
            continue
        errors = validate_review(parsed, packet)
        entry["review"] = parsed
        entry["validation_errors"] = errors
        attempts.append(entry)
        if not errors:
            return {
                "family": packet["packet_id"],
                "reviewer": "adjudicator",
                "status": "usable",
                "attempts": attempts,
                "final": parsed,
            }
    return {
        "family": packet["packet_id"],
        "reviewer": "adjudicator",
        "status": "unusable_review",
        "attempts": attempts,
        "final": None,
    }


def _promotable(review: dict, packet: dict) -> bool:
    return (
        review["verdict"] == "promote_to_scripted_validation"
        and review["source_C_natural"]["verdict"] is True
        and review["target_C_still_successful"]["status"] == "supported"
        and review["target_forces_comparison"] is False
        and review["scope_equivalence"] == "supported"
        and review["privileged_information_needed_by_B"] is False
        and bool(review["candidate_B"]["public_api_route"])
        and meaningful_saving(review, packet)
    )


def aggregate_family(packet: dict, outputs: list[dict]) -> dict:
    usable = [item["final"] for item in outputs if item["status"] == "usable"]
    if len(usable) < 2:
        return {
            "family": packet["packet_id"],
            "verdict": "reserve",
            "reason_code": "unusable_review",
            "review_count": len(usable),
            "promoted": False,
        }
    if any(review["scope_equivalence"] == "refuted" for review in usable):
        return {
            "family": packet["packet_id"],
            "verdict": "reject",
            "reason_code": "scope_refuted",
            "review_count": len(usable),
            "promoted": False,
        }
    if len(usable) == 2 and all(_promotable(review, packet) for review in usable):
        if route_key(usable[0]) == route_key(usable[1]):
            return {
                "family": packet["packet_id"],
                "verdict": "promote_to_scripted_validation",
                "reason_code": "dual_agreement_meaningful_route",
                "review_count": 2,
                "promoted": True,
            }
    codes = [reason_code(review, packet) for review in usable]
    if all(review["verdict"] == "reject" for review in usable) and len(set(codes)) == 1:
        verdict, code = "reject", codes[0]
    else:
        verdict, code = "reserve", "disagreement_requires_adjudication"
    return {
        "family": packet["packet_id"],
        "verdict": verdict,
        "reason_code": code,
        "review_count": len(usable),
        "promoted": False,
    }


def apply_adjudication(packet: dict, primary: list[dict], adjudication: dict) -> dict:
    """Apply a validated third conclusion without treating it as execution evidence."""

    if adjudication.get("status") != "usable":
        return {
            "family": packet["packet_id"],
            "verdict": "reserve",
            "reason_code": "unusable_adjudication",
            "review_count": len([x for x in primary if x["status"] == "usable"]),
            "promoted": False,
        }
    review = adjudication["final"]
    primary_reviews = [item["final"] for item in primary if item["status"] == "usable"]
    if _promotable(review, packet) and any(
        route_key(review) == route_key(candidate) for candidate in primary_reviews
    ):
        verdict, code, promoted = (
            "promote_to_scripted_validation",
            "adjudicated_meaningful_route",
            True,
        )
    elif review["verdict"] == "reject":
        verdict, code, promoted = "reject", reason_code(review, packet), False
    else:
        verdict, code, promoted = "reserve", "adjudication_not_promotable", False
    return {
        "family": packet["packet_id"],
        "verdict": verdict,
        "reason_code": code,
        "review_count": len(primary_reviews),
        "promoted": promoted,
    }


def _load_packets(packet_root: Path) -> list[Path]:
    manifest = json.loads((packet_root / "reserve_manifest.json").read_text(encoding="utf-8"))
    expected = {entry["family_id"] for entry in manifest["families"]}
    paths = sorted(packet_root.glob("*/packet.json"))
    actual = {path.parent.name for path in paths}
    if actual != expected:
        raise RuntimeError(f"packet pool mismatch: expected {len(expected)}, found {len(actual)}")
    return paths


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def run(args: argparse.Namespace) -> dict:
    packet_paths = _load_packets(Path(args.packet_root))
    key = load_key(Path(args.env_file))
    jobs = [(path, reviewer) for path in packet_paths for reviewer in ("A", "B")]
    outputs: list[dict] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = [
            pool.submit(review_one, path, reviewer, key, args.timeout) for path, reviewer in jobs
        ]
        for future in concurrent.futures.as_completed(futures):
            outputs.append(future.result())
    outputs.sort(key=lambda item: (item["family"], item["reviewer"]))
    by_family = {}
    for item in outputs:
        by_family.setdefault(item["family"], []).append(item)
    adjudications: list[dict] = []
    finals = []
    for path in packet_paths:
        packet = json.loads(path.read_text(encoding="utf-8"))
        pair = by_family[packet["packet_id"]]
        result = aggregate_family(packet, pair)
        if result["reason_code"] == "disagreement_requires_adjudication":
            adjudication = adjudicate_one(packet, pair, key, args.timeout)
            adjudications.append(adjudication)
            result = apply_adjudication(packet, pair, adjudication)
        finals.append(result)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    _write_json(out_dir / "review_outputs.json", outputs)
    _write_json(out_dir / "adjudications.json", adjudications)
    _write_json(out_dir / "final_results.json", finals)
    telemetry = [attempt["telemetry"] for item in outputs for attempt in item["attempts"]]
    adjudication_telemetry = [
        attempt["telemetry"] for item in adjudications for attempt in item["attempts"]
    ]
    all_telemetry = telemetry + adjudication_telemetry
    summary = {
        "model": MODEL,
        "endpoint": ENDPOINT,
        "research_side_only": True,
        "primary_calls": len(telemetry),
        "successful_review_outputs": sum(item["status"] == "usable" for item in outputs),
        "adjudication_calls": len(adjudication_telemetry),
        "total_calls": len(all_telemetry),
        "total_input_tokens": sum(x["input_tokens"] or 0 for x in all_telemetry),
        "total_output_tokens": sum(x["output_tokens"] or 0 for x in all_telemetry),
        "estimated_cost_usd": round(sum(x["estimated_cost_usd"] or 0 for x in all_telemetry), 8),
        "latency_seconds": round(sum(x["latency_seconds"] or 0 for x in all_telemetry), 3),
        "verdict_distribution": dict(Counter(item["verdict"] for item in finals)),
        "promoted_families": [item["family"] for item in finals if item["promoted"]],
        "note": (
            "Reviewer outputs are triage hypotheses; no B success, measured cost(B), or K0 "
            "discovery is established."
        ),
    }
    _write_json(out_dir / "summary.json", summary)
    return summary


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet-root", default=str(PACKET_ROOT))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT))
    parser.add_argument("--env-file", default=str(ROOT / ".env"))
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--timeout", type=int, default=120)
    return parser.parse_args(argv)


if __name__ == "__main__":
    result = run(parse_args())
    print(json.dumps(result, indent=2, sort_keys=True))
