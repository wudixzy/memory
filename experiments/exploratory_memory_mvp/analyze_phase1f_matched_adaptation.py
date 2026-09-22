"""Deterministic paired report for a completed Phase 1F-MA artifact bundle."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

EXPERIMENTS = Path(__file__).resolve().parents[1]
if str(EXPERIMENTS) not in sys.path:
    sys.path.insert(0, str(EXPERIMENTS))

from exploratory_memory_mvp.common import SchemaError, make_run_directory, write_json  # noqa: E402
from exploratory_memory_mvp.run_phase1f_matched_adaptation import (  # noqa: E402
    ARMS,
    MODELS,
    PHASE1F_PROTOCOL_VERSION,
    PHASE1F_SUMMARY_SCHEMA,
)

CONTRASTS = (("T0", "G"), ("T1", "G"), ("T1", "T0"))


def _action_value(row: dict[str, Any]) -> int | None:
    value = row.get("actions_to_target_acquisition")
    if type(value) is int and value >= 0:
        return value
    return None


def _contrast_summary(rows: list[dict[str, Any]], *, left: str, right: str) -> dict[str, Any]:
    paired: list[dict[str, Any]] = []
    missing = 0
    for item in rows:
        left_value = item["actions"][left]
        right_value = item["actions"][right]
        if left_value is None or right_value is None:
            missing += 1
            delta = None
        else:
            delta = left_value - right_value
            paired.append({"task_id": item["task_id"], "delta": delta})
        item.setdefault("contrasts", {})[f"{left}-{right}"] = delta
    values = [item["delta"] for item in paired]
    return {
        "left_minus_right": f"{left}-{right}",
        "paired_n": len(values),
        "missing_pair_n": missing,
        "total_delta": sum(values) if values else None,
        "mean_delta": (sum(values) / len(values)) if values else None,
        "per_task": paired,
    }


def _arm_summary(items: list[dict[str, Any]], arm: str) -> dict[str, Any]:
    values = [item["actions"][arm] for item in items]
    observed = [value for value in values if value is not None]
    return {
        "task_n": len(items),
        "target_acquired_n": sum(
            item["rows"][arm].get("target_acquired") is True for item in items
        ),
        "actions_observed_n": len(observed),
        "actions_missing_n": len(values) - len(observed),
        "total_actions_to_acquisition": sum(observed) if len(observed) == len(values) else None,
        "mean_actions_to_acquisition": (sum(observed) / len(observed) if observed else None),
    }


def _summarize_group(items: list[dict[str, Any]]) -> dict[str, Any]:
    arms = {arm: _arm_summary(items, arm) for arm in ARMS}
    contrasts = {
        f"{left}-{right}": _contrast_summary(items, left=left, right=right)
        for left, right in CONTRASTS
    }
    return {"task_n": len(items), "arms": arms, "contrasts": contrasts}


def build_phase1f_report(summary: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(summary, dict) or summary.get("schema_version") != PHASE1F_SUMMARY_SCHEMA:
        raise SchemaError("Input is not a Phase 1F matched-adaptation summary")
    if summary.get("protocol") != PHASE1F_PROTOCOL_VERSION:
        raise SchemaError("Phase 1F summary protocol is not recognized")
    results = summary.get("results")
    if not isinstance(results, list):
        raise SchemaError("Phase 1F paired results must be a list")

    model_items: dict[str, list[dict[str, Any]]] = {model: [] for model in MODELS}
    seen_pairs: set[tuple[str, str]] = set()
    for task_result in results:
        if not isinstance(task_result, dict) or task_result.get("pairing_valid") is not True:
            raise SchemaError("Phase 1F analyzer requires valid paired task rows")
        task_id = task_result.get("task_id")
        family = task_result.get("task_family")
        if not isinstance(task_id, str) or not isinstance(family, str):
            raise SchemaError("Phase 1F paired task identity is malformed")
        for model in MODELS:
            model_rows = task_result.get(model.replace("qwen3.8-", ""))
            if not isinstance(model_rows, dict) or set(model_rows) != set(ARMS):
                raise SchemaError(f"Phase 1F task is missing {model} G/T0/T1 rows")
            identity = (model, task_id)
            if identity in seen_pairs:
                raise SchemaError("Phase 1F paired result contains a duplicate model/task")
            seen_pairs.add(identity)
            for arm in ARMS:
                row = model_rows[arm]
                if not isinstance(row, dict):
                    raise SchemaError("Phase 1F arm summary is malformed")
                if row.get("task_id") != task_id or row.get("task_family") != family:
                    raise SchemaError("Phase 1F arm identity differs from paired task")
            model_items[model].append(
                {
                    "task_id": task_id,
                    "task_family": family,
                    "phase": task_result.get("phase"),
                    "rows": model_rows,
                    "actions": {arm: _action_value(model_rows[arm]) for arm in ARMS},
                    "contrasts": {},
                }
            )

    report_models: dict[str, Any] = {}
    for model, items in model_items.items():
        family_items: dict[str, list[dict[str, Any]]] = defaultdict(list)
        phase_items: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in items:
            family_items[item["task_family"]].append(item)
            if isinstance(item["phase"], str) and item["phase"]:
                phase_items[item["phase"]].append(item)
        report_models[model] = {
            "overall": _summarize_group(items),
            "by_family": {
                family: _summarize_group(group) for family, group in sorted(family_items.items())
            },
            "by_phase": {
                phase: _summarize_group(group) for phase, group in sorted(phase_items.items())
            },
            "by_h_activation": {
                arm: {
                    state: _arm_summary(
                        [
                            item
                            for item in items
                            if (item["rows"][arm].get("activated_h_id") is not None)
                            == (state == "h_active")
                        ],
                        arm,
                    )
                    for state in ("h_active", "no_h")
                }
                for arm in ("T0", "T1")
            },
            "t1_no_h_generic_probe": [
                {
                    "task_id": item["task_id"],
                    "task_family": item["task_family"],
                    "probe_route": item["rows"]["T1"].get("probe_route"),
                    "candidate_sequence": item["rows"]["T1"].get("candidate_sequence"),
                    "probe_action_count": item["rows"]["T1"].get("probe_environment_action_count"),
                    "probe_acquired_target": item["rows"]["T1"].get("probe_acquired_target"),
                    "continuation_action_count": item["rows"]["T1"].get(
                        "continuation_environment_action_count"
                    ),
                }
                for item in items
                if item["rows"]["T1"].get("activated_h_id") is None
                and item["rows"]["T1"].get("probe_route") == "generic_c2_then_continuation"
            ],
            "per_task": [
                {
                    "task_id": item["task_id"],
                    "task_family": item["task_family"],
                    "phase": item["phase"],
                    "actions_to_target_acquisition": item["actions"],
                    "contrasts": {
                        f"{left}-{right}": (
                            item["actions"][left] - item["actions"][right]
                            if item["actions"][left] is not None
                            and item["actions"][right] is not None
                            else None
                        )
                        for left, right in CONTRASTS
                    },
                }
                for item in items
            ],
        }

    return {
        "schema_version": "phase1f-matched-adaptation-analysis-v1",
        "protocol": PHASE1F_PROTOCOL_VERSION,
        "endpoint": "environment actions to exact target acquisition",
        "interpretation": "descriptive paired development evidence; not causal",
        "registry_sha256": summary.get("registry_sha256"),
        "task_n": len(results),
        "models": report_models,
    }


def _markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# Phase 1F matched-adaptation report",
        "",
        f"Protocol: `{report['protocol']}`  ",
        f"Endpoint: {report['endpoint']}  ",
        f"Interpretation: {report['interpretation']}",
        "",
    ]
    for model in MODELS:
        section = report["models"][model]["overall"]
        lines.extend(
            [
                f"## {model}",
                "",
                "Arm summaries",
                "",
                "| Arm | Tasks | Acquired | Mean actions | Total actions* |",
                "|---|---:|---:|---:|---:|",
            ]
        )
        for arm in ARMS:
            data = section["arms"][arm]
            mean = (
                "—"
                if data["mean_actions_to_acquisition"] is None
                else f"{data['mean_actions_to_acquisition']:.3f}"
            )
            total = (
                "—"
                if data["total_actions_to_acquisition"] is None
                else str(data["total_actions_to_acquisition"])
            )
            lines.append(
                f"| {arm} | {data['task_n']} | {data['target_acquired_n']} | {mean} | {total} |"
            )
        lines.extend(
            [
                "",
                "Paired contrasts (left − right)",
                "",
                "| Contrast | Paired n | Missing pairs | Total delta | Mean delta |",
                "|---|---:|---:|---:|---:|",
            ]
        )
        for left, right in CONTRASTS:
            key = f"{left}-{right}"
            data = section["contrasts"][key]
            mean = "—" if data["mean_delta"] is None else f"{data['mean_delta']:.3f}"
            total = "—" if data["total_delta"] is None else str(data["total_delta"])
            lines.append(
                f"| {key} | {data['paired_n']} | {data['missing_pair_n']} | {total} | {mean} |"
            )
        lines.extend(
            [
                "",
                "*Total is reported only when every task has a target-acquisition action count.",
                "",
            ]
        )
        by_family = report["models"][model]["by_family"]
        if by_family:
            lines.extend(
                [
                    "Family contrast totals",
                    "",
                    "| Family | T0−G | T1−G | T1−T0 |",
                    "|---|---:|---:|---:|",
                ]
            )
            for family, family_data in by_family.items():
                values = [
                    family_data["contrasts"][key]["total_delta"]
                    for key in ("T0-G", "T1-G", "T1-T0")
                ]
                rendered = ["—" if value is None else str(value) for value in values]
                lines.append(f"| {family} | {rendered[0]} | {rendered[1]} | {rendered[2]} |")
            lines.append("")
        lines.extend(
            [
                "H-active / no-H outcomes (arm-local classification)",
                "",
                "| Arm | State | Tasks | Acquired | Mean actions |",
                "|---|---|---:|---:|---:|",
            ]
        )
        for arm, state_summaries in report["models"][model]["by_h_activation"].items():
            for state, data in state_summaries.items():
                mean = (
                    "—"
                    if data["mean_actions_to_acquisition"] is None
                    else f"{data['mean_actions_to_acquisition']:.3f}"
                )
                lines.append(
                    f"| {arm} | {state} | {data['task_n']} | {data['target_acquired_n']} | {mean} |"
                )
        lines.append("")
        lines.extend(
            [
                "T1 no-H generic-probe details",
                "",
                "| Task | Family | Route | Candidates | Probe actions | "
                "Acquired in probe | Continuation actions |",
                "|---|---|---|---|---:|---|---:|",
            ]
        )
        for row in report["models"][model]["t1_no_h_generic_probe"]:
            lines.append(
                f"| {row['task_id']} | {row['task_family']} | {row['probe_route']} | "
                f"{row['candidate_sequence']} | {row['probe_action_count']} | "
                f"{row['probe_acquired_target']} | {row['continuation_action_count']} |"
            )
        lines.append("")
    return "\n".join(lines)


def analyze_phase1f_summary(
    summary_or_path: dict[str, Any] | Path,
    output: Path,
) -> dict[str, Any]:
    if isinstance(summary_or_path, Path):
        try:
            summary = json.loads(summary_or_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            raise SchemaError("Phase 1F summary file is unavailable or invalid") from None
    else:
        summary = summary_or_path
    report = build_phase1f_report(summary)
    make_run_directory(output)
    write_json(output / "analysis.json", report)
    (output / "report.md").write_text(_markdown_report(report), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = analyze_phase1f_summary(args.summary, args.output)
    print(json.dumps({"task_n": report["task_n"], "models": list(report["models"])}, indent=2))


if __name__ == "__main__":
    main()
