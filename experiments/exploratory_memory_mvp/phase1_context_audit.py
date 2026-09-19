"""Offline token/context parity audit for frozen C2/C3 actor artifacts."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any, Callable, Iterable

from .common import SchemaError, read_json, write_json


def _text_tokens(text: str, tokenizer: Callable[[str], list[int]] | None) -> tuple[int | None, str]:
    if tokenizer is None:
        return None, "unavailable"
    return len(tokenizer(text)), "provided_tokenizer"


def _record_from_input(
    actor_input: dict[str, Any],
    *,
    condition: str,
    prompt: list[dict[str, Any]] | None = None,
    tokenizer: Callable[[str], list[int]] | None = None,
) -> dict[str, Any]:
    if not isinstance(actor_input, dict):
        raise SchemaError("Actor input artifact must be an object")
    h = actor_input.get("exploratory_memory")
    context_text = json.dumps(actor_input, ensure_ascii=False, sort_keys=True)
    h_text = "" if h is None else json.dumps(h, ensure_ascii=False, sort_keys=True)
    prompt_text = (
        "" if prompt is None else "\n".join(str(message.get("content", "")) for message in prompt)
    )
    context_tokens, token_source = _text_tokens(context_text, tokenizer)
    h_tokens, _ = _text_tokens(h_text, tokenizer)
    prompt_tokens, _ = _text_tokens(prompt_text, tokenizer)
    return {
        "condition": condition,
        "has_exploratory_memory": h is not None,
        "h_characters": len(h_text),
        "h_tokens": h_tokens,
        "first_step_context_characters": len(context_text),
        "first_step_context_tokens": context_tokens,
        "prompt_characters": len(prompt_text),
        "prompt_tokens": prompt_tokens,
        "token_source": token_source,
    }


def audit_actor_inputs(
    artifacts: Iterable[tuple[str, Path]],
    *,
    tokenizer: Callable[[str], list[int]] | None = None,
) -> dict[str, Any]:
    """Audit first-step actor inputs without invoking a model or environment."""

    records = []
    for condition, path in artifacts:
        actor_input = read_json(path)
        prompt_path = path.with_name("actor_prompt.json")
        prompt = read_json(prompt_path) if prompt_path.is_file() else None
        records.append(
            _record_from_input(
                actor_input, condition=condition, prompt=prompt, tokenizer=tokenizer
            )
        )
    return summarize_context_audit(records, tokenizer_available=tokenizer is not None)


def summarize_context_audit(
    records: list[dict[str, Any]], *, tokenizer_available: bool
) -> dict[str, Any]:
    """Return per-condition distributions plus raw rows for review."""

    if not isinstance(records, list) or not records:
        raise SchemaError("Context audit needs at least one actor input")
    by_condition: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        by_condition.setdefault(record["condition"], []).append(record)

    def stats(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
        values = [row[key] for row in rows if row[key] is not None]
        if not values:
            return {"count": len(rows), "measured": False}
        values.sort()
        return {
            "count": len(values),
            "measured": True,
            "min": min(values),
            "max": max(values),
            "mean": statistics.fmean(values),
            "median": statistics.median(values),
            "p95": values[min(len(values) - 1, int(len(values) * 0.95))],
        }

    distributions = {}
    for condition, rows in sorted(by_condition.items()):
        distributions[condition] = {
            "h_tokens": stats(rows, "h_tokens"),
            "first_step_context_tokens": stats(rows, "first_step_context_tokens"),
            "prompt_tokens": stats(rows, "prompt_tokens"),
            "h_characters": stats(rows, "h_characters"),
            "first_step_context_characters": stats(rows, "first_step_context_characters"),
            "rows": rows,
        }
    return {
        "tokenizer_available": tokenizer_available,
        "exact_token_parity_claim": False,
        "conditions": distributions,
        "note": (
            "Token counts are reported only when a caller supplies the target tokenizer; "
            "character counts are not token parity."
        ),
    }


def load_optional_tokenizer() -> tuple[Callable[[str], list[int]] | None, str]:
    """Try a local tokenizer without requiring a package or network download."""

    try:
        import tiktoken  # type: ignore

        encoder = tiktoken.get_encoding("cl100k_base")
        return encoder.encode, "tiktoken:cl100k_base"
    except Exception:
        return None, "unavailable"


def main() -> None:
    """Audit saved actor inputs without starting a model or carrier."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artifact",
        action="append",
        required=True,
        metavar="CONDITION=PATH",
        help="Saved first-step actor_input.json, for example C2=/tmp/C2/actor_input.json",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    artifacts = []
    for item in args.artifact:
        condition, separator, path = item.partition("=")
        if not separator or not condition.strip() or not path.strip():
            parser.error("--artifact must have the form CONDITION=PATH")
        artifacts.append((condition.strip(), Path(path)))
    tokenizer, tokenizer_name = load_optional_tokenizer()
    report = audit_actor_inputs(artifacts, tokenizer=tokenizer)
    report["tokenizer"] = tokenizer_name
    if args.output is None:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    else:
        write_json(args.output, report)


if __name__ == "__main__":
    main()
