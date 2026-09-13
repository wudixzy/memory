"""BF-0 — deterministic AppWorld task selection for the behavior-first corpus.

`docs/31` section 3. The selector reads the pinned benchmark checkout and picks
~30 tasks that maximise behavioral and transfer diversity. Rules:

* **Discovery, not a hand list.** Task ids come from the checkout's own
  `data/tasks/` directories; families and numbers come from the upstream
  `appworld.task` id contract as mirrored by `memory_census.dataset`.
* **No reference material.** Selection reads `specs.json`, the split files and
  the public `api_docs.db` app descriptions. It never opens `ground_truth/`
  (solution code, evaluator, answers, benchmark metadata) — diversity is
  measured on the instruction and the public app surface, not on reference-call
  gaps.
* **Registered exclusions.** Instructions that explicitly demand a
  cheapest/best/maximised choice, exhaustive comparison, or an optimality proof
  are excluded by named regexes, each exclusion recorded with its match.
* **Seeded and repeatable.** The same checkout and seed always produce the same
  ordered selection; ties break on `sha256(seed:task_id)`.
* **No frozen-pool priority.** The `docs/31` section 2 holds are annotated
  *after* selection for the report only. Membership is never a feature, so it
  cannot change who is chosen.
* **Stop instead of loosening.** Fewer than `MIN_ELIGIBLE_TASKS` eligible tasks
  is reported as `insufficient_eligible`, not silently relaxed.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from memory_behavior.measure import selection_digest
from memory_census.dataset import DATASET_SPLITS, task_family_of, task_number_of

SELECTOR_VERSION = "bf0-behavior-selector-v1"
DEFAULT_DATA_ROOT = Path(__file__).resolve().parents[2] / "third_party/ace-appworld/data"
DEFAULT_SEED = 20260913
TARGET_TASKS = 30
MIN_ELIGIBLE_TASKS = 24
MAX_TASKS_PER_FAMILY = 1

#: Split files are read in this fixed order for the coverage pass.
SPLIT_ORDER = DATASET_SPLITS

#: Apps that exist for every task and carry no task-specific signal.
INFRASTRUCTURE_APPS = ("admin", "api_docs", "supervisor")

#: Named exclusion rule (`docs/31` section 3). Each entry is
#: `(pattern_id, regex, rationale)`; the first match wins and is recorded.
EXCLUSION_PATTERNS: tuple[tuple[str, str, str], ...] = (
    (
        "cheapest_or_best_choice",
        r"\b(cheapest|cheaper|best|optimal|optimality|maximi[sz]e[sd]?|maximi[sz]ing|"
        r"minimi[sz]e[sd]?|minimi[sz]ing|most cost[- ]effective|lowest (cost|price)|"
        r"most expensive|best value|whichever is (cheaper|better))\b",
        "instruction requires a cheapest/best choice, which forces the comparison "
        "regardless of what memory favors",
    ),
    (
        "compare_all_or_every",
        r"\b(compare|compares|comparing|comparison|rank|ranks|ranking)\b[^.;]{0,60}?"
        r"\b(all|every|each|both|options|alternatives|candidates)\b",
        "instruction explicitly asks to compare/rank all or every option",
    ),
    (
        "all_then_compare",
        r"\b(all|every|each|both)\b[^.;]{0,60}?"
        r"\b(compare|comparison|cheaper|cheapest|best|optimal|rank)\b",
        "instruction ties all/every/each to a comparison or an optimum",
    ),
    (
        "exhaustive",
        r"\b(exhaustive|exhaustively|exhaustiveness)\b",
        "instruction explicitly requires exhaustive exploration",
    ),
    (
        "all_possible_options",
        r"\b(all|every|each)\s+(possible\s+)?(option|alternative|combination|permutation|"
        r"candidate|choice)s?\b",
        "instruction asks for all/every possible option",
    ),
    (
        "prove_optimality",
        r"\b(prove|proving|guarantee|guaranteeing)\b[^.;]{0,40}?"
        r"\b(optimal|optimality|globally|cheapest|best|minimum)\b",
        "instruction requires proving/guaranteeing an optimum",
    ),
)

#: Instruction behavior cues. Diversity features only; no cue is a shortcut or
#: a B detector, and none reads the reference solution.
FEATURE_CUES: tuple[tuple[str, str], ...] = (
    ("search_cue", r"\b(search|look up|look for|find|find out|which|what)\b"),
    ("list_cue", r"\b(list|show me|show all|how many|count)\b"),
    ("inspect_cue", r"\b(check|see if|inspect|examine|details?|status|look at|review)\b"),
    (
        "direct_lookup_cue",
        r"\b(named|with (this|the) (phone )?(number|email|id|name)|by (its|their|the) "
        r"(id|name|number)|whose (id|name|number))\b",
    ),
    ("fallback_cue", r"\b(if not|if there (is|are) no|otherwise|in case|unless|instead)\b"),
    ("verification_cue", r"\b(make sure|ensure|verify|confirm|double[- ]check)\b"),
    (
        "filter_cue",
        r"\b(that (has|have|is|are|were)|whose|between|under|over|more than|"
        r"less than|after|before|only|except)\b",
    ),
    ("cross_app_cue", r"\b(and then|then use|using the .* (id|token|code)|from the .* app)\b"),
    ("self_identity_cue", r"\b(my|me|mine|myself|i)\b"),
    ("other_identity_cue", r"\b(they|them|their|he|she|his|her|the person|the user|someone)\b"),
)

#: Diversity dimensions and their weights in the coverage score. `apps` is
#: measured from instruction mentions against the public app vocabulary.
DIMENSION_WEIGHTS: tuple[tuple[str, float], ...] = (
    ("family", 3.0),
    ("app_combo", 2.0),
    ("split", 1.5),
    ("search_shape", 1.0),
    ("identity_shape", 1.0),
    ("verification_cue", 0.5),
    ("fallback_cue", 0.5),
    ("cross_app_cue", 0.5),
    ("filter_cue", 0.5),
    ("length_bucket", 0.25),
)

#: Families that appear in already-completed project work: the `docs/31`
#: section 2 frozen review-quality holds plus families used by the registered
#: ACE batch and the census registry. **Reported only.** The selector does not
#: read this mapping, so it cannot influence which tasks are chosen.
HISTORICAL_FAMILIES: dict[str, str] = {
    "23cf851": "docs/31 section 2 frozen review-quality hold",
    "302c169": "docs/31 section 2 frozen review-quality hold",
    "37a8675": "docs/31 section 2 frozen review-quality hold",
    "50e1ac9": "docs/31 section 2 frozen review-quality hold",
    "692c77d": "docs/31 section 2 frozen review-quality hold",
    "aa8502b": "docs/31 section 2 frozen review-quality hold",
    "ce359b5": "docs/31 section 2 frozen review-quality hold",
    "d0b1f43": "docs/31 section 2 frozen review-quality hold",
    "e85d92a": "docs/31 section 2 frozen review-quality hold",
    "60d0b5b": "registered ACE batch source task",
    "432dc7a": "registered ACE batch source/target task",
}


class SelectionError(RuntimeError):
    """Raised when the eligible pool cannot support the registered target."""


@dataclass(frozen=True)
class SelectionConfig:
    seed: int = DEFAULT_SEED
    target: int = TARGET_TASKS
    minimum: int = MIN_ELIGIBLE_TASKS
    max_per_family: int = MAX_TASKS_PER_FAMILY
    data_root: Path = field(default_factory=lambda: DEFAULT_DATA_ROOT)


def _read_json(path: Path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def humanize_app(app: str) -> str:
    return app.replace("_", " ")


def app_vocabulary(data_root: Path | str) -> dict:
    """Domain app names from the benchmark's public `api_docs` documentation.

    `data/base_dbs/api_docs.db` is the table behind `apis.api_docs`, i.e. what
    an agent can read at runtime. It is read read-only; no task ground truth is
    involved.
    """

    path = Path(data_root) / "base_dbs/api_docs.db"
    if not path.exists():
        raise SelectionError(f"missing public api documentation at {path}")
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        rows = connection.execute(
            "select app_name_, count(*) from api_docs group by app_name_"
        ).fetchall()
    finally:
        connection.close()
    counts = {app: int(count) for app, count in rows}
    domain = sorted(app for app in counts if app not in INFRASTRUCTURE_APPS)
    return {
        "source": "data/base_dbs/api_docs.db (public api_docs table)",
        "apps": sorted(counts),
        "domain_apps": domain,
        "infrastructure_apps": list(INFRASTRUCTURE_APPS),
        "api_counts": counts,
    }


def read_splits(data_root: Path | str) -> dict[str, str]:
    """Task id -> split, from the benchmark's own split files."""

    datasets = Path(data_root) / "datasets"
    split_of: dict[str, str] = {}
    for split in SPLIT_ORDER:
        path = datasets / f"{split}.txt"
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            task_id = line.strip()
            if task_id:
                split_of[task_id] = split
    return split_of


def discovered_tasks(data_root: Path | str) -> list[dict]:
    """Every real task in the checkout, with instruction-level facts only.

    Reads `specs.json` (the actor-visible task specification) and the split
    files. `ground_truth/` is never opened.
    """

    data_root = Path(data_root)
    tasks_root = data_root / "tasks"
    if not tasks_root.is_dir():
        raise SelectionError(f"no tasks directory at {tasks_root}")
    splits = read_splits(data_root)
    records = []
    for task_dir in sorted(path for path in tasks_root.iterdir() if path.is_dir()):
        task_id = task_dir.name
        specs_path = task_dir / "specs.json"
        specs = _read_json(specs_path)
        if specs is None:
            raise SelectionError(f"task {task_id!r} has no readable specs.json")
        instruction = str(specs.get("instruction") or "")
        records.append(
            {
                "task_id": task_id,
                "family": task_family_of(task_id),
                "number": task_number_of(task_id),
                "split": splits.get(task_id),
                "instruction": instruction,
                "instruction_sha256": hashlib.sha256(instruction.encode()).hexdigest(),
                "specs_sha256": hashlib.sha256(specs_path.read_bytes()).hexdigest(),
                "datetime": specs.get("datetime"),
            }
        )
    return records


def dataset_anchor(data_root: Path | str, records) -> dict:
    """Stable identity of the analysed checkout, without reference material."""

    data_root = Path(data_root)
    digest = hashlib.sha256()
    for record in sorted(records, key=lambda item: item["task_id"]):
        digest.update(f"{record['task_id']}:{record['specs_sha256']}\n".encode())
    version_path = data_root / "version.txt"
    families = {record["family"] for record in records}
    return {
        "data_root": str(data_root),
        "benchmark_version": (
            version_path.read_text(encoding="utf-8").strip() if version_path.exists() else None
        ),
        "task_count": len(records),
        "family_count": len(families),
        "split_counts": {
            split: sum(1 for record in records if record["split"] == split) for split in SPLIT_ORDER
        },
        "digest_scope": "sha256 over sorted '<task_id>:sha256(specs.json)>' lines",
        "dataset_content_sha256": digest.hexdigest(),
    }


def exclusion_for(instruction: str) -> dict | None:
    """First registered exclusion matching this instruction, or None."""

    for pattern_id, pattern, rationale in EXCLUSION_PATTERNS:
        match = re.search(pattern, instruction or "", re.IGNORECASE)
        if match:
            return {
                "pattern_id": pattern_id,
                "pattern": pattern,
                "matched_text": match.group(0)[:80],
                "rationale": rationale,
            }
    return None


def _length_bucket(words: int) -> str:
    for limit, name in ((12, "short"), (20, "medium"), (30, "long")):
        if words < limit:
            return name
    return "very_long"


def mentioned_apps(instruction: str, domain_apps) -> list[str]:
    """Domain apps the instruction names, matched on their humanized form."""

    found = []
    for app in domain_apps:
        name = re.escape(humanize_app(app)).replace(r"\ ", r"[ _]")
        if re.search(rf"\b{name}\b", instruction or "", re.IGNORECASE):
            found.append(app)
    return sorted(found)


def task_features(record: dict, domain_apps) -> dict:
    """Behavioral diversity features for one task. No reference material."""

    instruction = record["instruction"]
    cues = {
        name: bool(re.search(pattern, instruction, re.IGNORECASE)) for name, pattern in FEATURE_CUES
    }
    apps = mentioned_apps(instruction, domain_apps)
    if len(apps) >= 2:
        app_scope = "cross_app"
    elif len(apps) == 1:
        app_scope = "single_app"
    else:
        app_scope = "unmentioned"
    if cues["search_cue"] and cues["list_cue"]:
        search_shape = "search_and_list"
    elif cues["search_cue"]:
        search_shape = "search"
    elif cues["list_cue"]:
        search_shape = "list"
    else:
        search_shape = "neither"
    if cues["self_identity_cue"] and cues["other_identity_cue"]:
        identity_shape = "self_and_other"
    elif cues["other_identity_cue"]:
        identity_shape = "other"
    elif cues["self_identity_cue"]:
        identity_shape = "self"
    else:
        identity_shape = "neither"
    return {
        "feature_rule": "regex cues in memory_behavior.selection.FEATURE_CUES",
        "family": record["family"],
        "split": record["split"],
        **cues,
        "apps_mentioned": apps,
        "app_combo": "+".join(apps) if apps else "none",
        "app_scope": app_scope,
        "search_shape": search_shape,
        "identity_shape": identity_shape,
        "instruction_words": len(instruction.split()),
        "length_bucket": _length_bucket(len(instruction.split())),
    }


def _rank_key(task_id: str, seed: int) -> str:
    return hashlib.sha256(f"{seed}:{task_id}".encode()).hexdigest()


def _coverage_score(features: dict, covered: set) -> float:
    return sum(
        weight
        for dimension, weight in DIMENSION_WEIGHTS
        if (dimension, features[dimension]) not in covered
    )


def _mark_covered(features: dict, covered: set) -> None:
    covered.update((dimension, features[dimension]) for dimension, _ in DIMENSION_WEIGHTS)


def select_tasks(
    eligible: list[dict],
    features_of: dict[str, dict],
    config: SelectionConfig,
) -> list[str]:
    """Deterministic greedy coverage selection over behavioral dimensions.

    One split-coverage pass first (each registered split that has an eligible
    task contributes one pick), then greedy marginal-coverage picks until the
    target is reached. Family reuse is capped, and every tie breaks on
    `sha256(seed:task_id)`, so the result depends only on the checkout, the
    features and the seed.
    """

    if len(eligible) < config.minimum:
        raise SelectionError(
            f"{len(eligible)} eligible tasks is below the registered minimum "
            f"{config.minimum}; refusing to loosen the selection rules"
        )
    by_id = {record["task_id"]: record for record in eligible}
    chosen: list[str] = []
    covered: set = set()
    family_used: dict[str, int] = {}
    remaining = set(by_id)

    def best(candidates) -> str | None:
        admissible = [
            task_id
            for task_id in candidates
            if family_used.get(by_id[task_id]["family"], 0) < config.max_per_family
        ]
        if not admissible:
            return None
        return min(
            admissible,
            key=lambda task_id: (
                -_coverage_score(features_of[task_id], covered),
                family_used.get(by_id[task_id]["family"], 0),
                _rank_key(task_id, config.seed),
            ),
        )

    for split in SPLIT_ORDER:
        if len(chosen) >= config.target:
            break
        pick = best([task_id for task_id in remaining if by_id[task_id]["split"] == split])
        if pick is not None:
            chosen.append(pick)
            remaining.discard(pick)
            _mark_covered(features_of[pick], covered)
            family_used[by_id[pick]["family"]] = family_used.get(by_id[pick]["family"], 0) + 1

    while len(chosen) < config.target:
        pick = best(remaining)
        if pick is None:
            break
        chosen.append(pick)
        remaining.discard(pick)
        _mark_covered(features_of[pick], covered)
        family_used[by_id[pick]["family"]] = family_used.get(by_id[pick]["family"], 0) + 1
    return chosen


def historical_flag(family: str) -> dict:
    """Post-selection annotation; never a selection feature."""

    source = HISTORICAL_FAMILIES.get(family)
    return {
        "natural_historical_family": source is not None,
        "historical_sources": [source] if source else [],
    }


def build_selection(
    data_root: Path | str = DEFAULT_DATA_ROOT,
    config: SelectionConfig | None = None,
) -> dict:
    """Full BF-0 selection manifest. Never loosens the registered rules."""

    config = config or SelectionConfig(data_root=Path(data_root))
    records = discovered_tasks(data_root)
    vocabulary = app_vocabulary(data_root)
    features_of: dict[str, dict] = {}
    eligible: list[dict] = []
    exclusions: list[dict] = []
    for record in records:
        verdict = exclusion_for(record["instruction"])
        if verdict:
            exclusions.append(
                {
                    "task_id": record["task_id"],
                    "family": record["family"],
                    "split": record["split"],
                    **verdict,
                }
            )
            continue
        eligible.append(record)
        features_of[record["task_id"]] = task_features(record, vocabulary["domain_apps"])

    status, chosen, error = "selected", [], None
    if len(eligible) < config.minimum:
        status = "insufficient_eligible"
        error = (
            f"{len(eligible)} eligible tasks is below the registered minimum {config.minimum}; "
            "stopping instead of loosening the rules"
        )
    else:
        chosen = select_tasks(eligible, features_of, config)

    by_pattern: dict[str, int] = {}
    for exclusion in exclusions:
        by_pattern[exclusion["pattern_id"]] = by_pattern.get(exclusion["pattern_id"], 0) + 1
    by_id = {record["task_id"]: record for record in eligible}
    tasks = [
        {
            "rank": rank,
            "task_id": task_id,
            "family": by_id[task_id]["family"],
            "number": by_id[task_id]["number"],
            "split": by_id[task_id]["split"],
            "instruction": by_id[task_id]["instruction"],
            "instruction_sha256": by_id[task_id]["instruction_sha256"],
            "features": features_of[task_id],
            **historical_flag(by_id[task_id]["family"]),
        }
        for rank, task_id in enumerate(chosen)
    ]
    manifest = {
        "selector_version": SELECTOR_VERSION,
        "status": status,
        "error": error,
        "config": {
            "seed": config.seed,
            "target": config.target,
            "minimum_eligible": config.minimum,
            "max_per_family": config.max_per_family,
        },
        "rules": {
            "feature_rule": "regex cues in memory_behavior.selection.FEATURE_CUES",
            "exclusion_rule": "regex patterns in memory_behavior.selection.EXCLUSION_PATTERNS",
            "ranking_rule": (
                "split-coverage pass over the registered splits, then greedy marginal "
                "coverage over DIMENSION_WEIGHTS; ties break on sha256(seed:task_id); "
                "at most max_per_family tasks per scenario family"
            ),
            "reference_material_used": False,
            "ground_truth_paths_read": [],
            "historical_holds_have_priority": False,
        },
        "dataset": dataset_anchor(data_root, records),
        "app_vocabulary": {
            "source": vocabulary["source"],
            "domain_apps": vocabulary["domain_apps"],
            "infrastructure_apps": vocabulary["infrastructure_apps"],
            "api_counts": vocabulary["api_counts"],
        },
        "counts": {
            "discovered": len(records),
            "eligible": len(eligible),
            "excluded": len(exclusions),
            "selected": len(tasks),
            "shortfall": max(0, config.target - len(tasks)),
            "families_selected": len({task["family"] for task in tasks}),
            "splits_selected": {
                split: sum(1 for task in tasks if task["split"] == split) for split in SPLIT_ORDER
            },
        },
        "exclusions": {
            "by_pattern": dict(sorted(by_pattern.items())),
            "records": sorted(exclusions, key=lambda item: item["task_id"]),
        },
        "historical_context": {
            "used_as_selection_feature": False,
            "note": (
                "The docs/31 section 2 frozen holds and other previously studied families are "
                "annotated after selection only; they receive no access or priority."
            ),
            "known_families": dict(sorted(HISTORICAL_FAMILIES.items())),
            "selected_historical_families": sorted(
                {task["family"] for task in tasks if task["natural_historical_family"]}
            ),
        },
        "tasks": tasks,
    }
    return manifest


def write_selection(path: Path | str, manifest: dict) -> str:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return selection_digest(manifest)
