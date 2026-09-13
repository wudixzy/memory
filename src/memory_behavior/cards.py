"""BF-2a — strategy cards extracted offline from real ACE artifacts.

`docs/31` section 5. One machine-readable card per real rollout, built only from
what a run actually persisted: executed actions, public API observations, the
playbook before/after and the native evaluator's success flag.

Rules:

* **Artifacts only.** No model call, no network, no reference solution, no
  evaluator ground truth, no hidden chain-of-thought. Evaluator text (test
  requirements, reports) is never copied into a card — only the boolean.
* **Deterministic.** The same artifacts always produce the same card.
* **Research-side.** Cards are analysis artifacts. They are not memory, and
  `memory_behavior.boundary` keeps them out of the adaptive-loop import graph.
* **No causality.** `behavioral_prior_summary` states what a learned delta could
  favor, mechanically derived from the delta text. It never claims that the
  delta caused the observed behavior.
"""

from __future__ import annotations

import json
from pathlib import Path

from memory_behavior import measure
from memory_census.state_diff import instruction_template

CARD_VERSION = "bf2-strategy-card-v1"
ABSTRACT_GOAL_LIMIT = 240

SEARCH_PATTERNS = ("enumerate", "filtered", "direct", "mixed", "unknown")
IDENTITY_RESOLUTIONS = ("direct", "multi_hop", "none", "unknown")

#: Fields `docs/31` section 5 requires on every card.
REQUIRED_FIELDS = (
    "task_id",
    "abstract_goal",
    "success",
    "strategy_signature",
    "public_api_calls",
    "search_pattern",
    "identity_resolution",
    "fallbacks_observed",
    "repeated_or_redundant_work",
    "memory_delta",
    "behavioral_prior_summary",
    "evidence_paths",
)

#: Artifacts a card cites as its evidence base.
EVIDENCE_ARTIFACTS = (
    "manifest.json",
    "actions.jsonl",
    "observations.jsonl",
    "evaluator.json",
    "memory_before.json",
    "memory_after.json",
    "memory_diff.json",
)


def abstract_goal(instruction: str) -> str:
    """Instruction with its sampled literals masked, for cross-task comparison."""

    masked = " ".join(instruction_template(instruction or "").split())
    if len(masked) > ABSTRACT_GOAL_LIMIT:
        return masked[: ABSTRACT_GOAL_LIMIT - 1].rstrip() + "…"
    return masked


def _apps_of(calls) -> list[str]:
    return sorted({call["app"] for call in calls})


def _behavioral_prior_summary(delta: dict, calls) -> str:
    added = delta["added"]
    if not added:
        return (
            "No playbook delta was persisted in this run, so no behavioral prior is "
            "attributed to it."
        )
    sections: dict[str, int] = {}
    for entry in added:
        sections[entry["section"]] = sections.get(entry["section"], 0) + 1
    section_text = ", ".join(f"{name}={count}" for name, count in sorted(sections.items()))
    apps = _apps_of(calls)
    app_text = ", ".join(apps) if apps else "no app"
    return (
        f"DeltaK adds {len(added)} entries ({section_text}) that could favor reuse of the "
        f"recorded routes in {app_text}; the observed trajectory executed "
        f"{len(measure.strategy_signature(calls))} distinct public calls. Mechanical "
        "summary of the persisted text only — not a causal claim about this trajectory."
    )


def extract_card(
    task_dir: Path | str,
    *,
    instruction: str | None = None,
    instruction_source: str | None = None,
) -> dict:
    """Build one card from a completed or failed task artifact directory."""

    task_dir = Path(task_dir)
    manifest = measure.read_available_json(task_dir / "manifest.json") or {}
    actions = measure.read_jsonl(task_dir / "actions.jsonl")
    observations = measure.read_jsonl(task_dir / "observations.jsonl")
    evaluator = measure.read_available_json(task_dir / "evaluator.json")
    before = measure.read_available_json(task_dir / "memory_before.json")
    after = measure.read_available_json(task_dir / "memory_after.json")
    corpus_task = measure.read_json(task_dir / "corpus_task.json") or {}

    if instruction is None:
        instruction = corpus_task.get("instruction")
        instruction_source = "corpus_task.json (bf0 selection manifest)"
    if instruction is None:
        instruction = measure.instruction_from_messages(
            measure.read_jsonl(task_dir / "messages_visible.jsonl")
        )
        instruction_source = "messages_visible.jsonl Generator prompt (fallback)"

    calls = measure.calls_from_actions(actions)
    public = measure.public_call_counts(observations)
    playbook_before = (before or {}).get("raw", {}).get("playbook", "")
    playbook_after = (after or {}).get("raw", {}).get("playbook", "")
    delta = measure.playbook_delta(playbook_before, playbook_after)

    fallbacks = [{**site, "kind": "failed_public_call"} for site in public["failed_call_sites"]] + [
        {
            "kind": event.get("kind"),
            "step": event.get("step"),
            "app": event.get("app"),
            "api": event.get("api"),
        }
        for event in observations
        if event.get("kind") in ("public_api_rejected", "public_api_limit")
    ]
    evidence = [relative for relative in EVIDENCE_ARTIFACTS if (task_dir / relative).exists()]
    if (task_dir / "corpus_task.json").exists():
        evidence.append("corpus_task.json")

    return {
        "card_version": CARD_VERSION,
        "task_id": manifest.get("task_id") or corpus_task.get("task_id") or task_dir.name,
        "abstract_goal": abstract_goal(instruction or ""),
        "instruction": instruction,
        "instruction_source": instruction_source,
        "instruction_sha256": measure.sha256_text(instruction or ""),
        "success": measure.evaluator_success(evaluator),
        "agent_completed": (evaluator or {}).get("agent_completed"),
        "run_status": manifest.get("status", corpus_task.get("task_status", "unknown")),
        "strategy_signature": measure.strategy_signature(calls),
        "public_api_calls": public["public_api_responses"],
        "public_api_failed_calls": public["failed_public_calls"],
        "public_api_rejected_calls": public["rejected_public_calls"],
        "search_pattern": measure.search_pattern(calls),
        "identity_resolution": measure.identity_resolution(calls),
        "fallbacks_observed": fallbacks,
        "repeated_or_redundant_work": measure.repeated_work(calls),
        "memory_delta": delta["added"],
        "memory_delta_removed": delta["removed"],
        "memory_delta_summary": {
            "added": len(delta["added"]),
            "removed": len(delta["removed"]),
            "edited": len(delta["edited"]),
            "entries_before": delta["entries_before"],
            "entries_after": delta["entries_after"],
            "changed": delta["changed"],
        },
        "behavioral_prior_summary": _behavioral_prior_summary(delta, calls),
        "applications": _apps_of(calls),
        "state_changing_calls": measure.state_changing_calls(calls),
        "executed_steps": len(actions),
        "public_call_counts": public,
        "evidence_paths": evidence,
        "evidence_note": (
            "every field is derived from these persisted artifacts; no model call, "
            "reference solution or evaluator ground-truth text is used"
        ),
    }


def card_is_complete(card: dict) -> dict:
    """Field and evidence completeness, for the corpus-to-card hand-off check."""

    missing = [name for name in REQUIRED_FIELDS if name not in card or card[name] is None]
    unknown_labels = []
    if card.get("search_pattern") not in SEARCH_PATTERNS:
        unknown_labels.append("search_pattern")
    if card.get("identity_resolution") not in IDENTITY_RESOLUTIONS:
        unknown_labels.append("identity_resolution")
    return {
        "complete": not missing and not unknown_labels,
        "missing_fields": missing,
        "invalid_labels": unknown_labels,
        "evidence_paths": list(card.get("evidence_paths") or []),
    }


def extract_cards(corpus_root: Path | str, output_dir: Path | str | None = None) -> dict:
    """Extract every task card under a corpus root and write an index."""

    corpus_root = Path(corpus_root)
    tasks_root = corpus_root / "tasks"
    if not tasks_root.is_dir():
        raise FileNotFoundError(f"no tasks directory under {corpus_root}")
    output = Path(output_dir) if output_dir is not None else corpus_root / "analysis" / "cards"
    output.mkdir(parents=True, exist_ok=True)
    cards = []
    for task_dir in sorted(path for path in tasks_root.iterdir() if path.is_dir()):
        card = extract_card(task_dir)
        card["artifact_path"] = str(task_dir)
        corpus_task = measure.read_json(task_dir / "corpus_task.json") or {}
        card["cross_check"] = {
            "corpus_public_api_responses": (corpus_task.get("public_calls") or {}).get(
                "public_api_responses"
            ),
            "card_public_api_calls": card["public_api_calls"],
            "match": (corpus_task.get("public_calls") or {}).get("public_api_responses")
            == card["public_api_calls"],
            "corpus_reset_verified": (corpus_task.get("reset") or {}).get("verified"),
        }
        cards.append(card)
        (output / f"{card['task_id']}.json").write_text(
            json.dumps(card, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )
    index = {
        "cards_version": CARD_VERSION,
        "corpus_root": str(corpus_root),
        "count": len(cards),
        "cards": [
            {
                "task_id": card["task_id"],
                "path": str((output / f"{card['task_id']}.json").relative_to(output)),
                "success": card["success"],
                "run_status": card["run_status"],
                "public_api_calls": card["public_api_calls"],
                "search_pattern": card["search_pattern"],
                "identity_resolution": card["identity_resolution"],
                "memory_delta_entries": card["memory_delta_summary"]["added"],
                "completeness": card_is_complete(card),
                "cross_check_match": card["cross_check"]["match"],
            }
            for card in cards
        ],
    }
    (output / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    return index
