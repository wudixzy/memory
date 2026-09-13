"""Read-only access to AppWorld task data, plus the official family grouping rule.

Family grouping is not invented here: AppWorld itself defines a *scenario* as a
`generator_id` with numbered sibling tasks. `appworld/task.py` implements
`task_id_to_generator_id`, `task_id_to_number`, and
`_maybe_assure_num_tasks_per_scenario`, which assert that a task id contains
exactly one underscore and that a scenario's numbers form a contiguous range
starting at 1. `task_family_of` mirrors that contract without importing the
runtime (see `memory_census.boundary`).

The census reads only files that ship with the benchmark checkout:

    data/tasks/<task_id>/specs.json
    data/tasks/<task_id>/dbs/<app>.jsonl        (task-input state seed)
    data/tasks/<task_id>/ground_truth/*         (research-side only)

`dbs/*.jsonl` here holds only the seed rows (mostly supervisor/admin accounts);
app-domain data lives in the shared `data/base_dbs/`. The census therefore does
not claim per-task app-data volumes offline.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Protocol

DATASET_SPLITS = ("train", "dev", "test_normal", "test_challenge")

_INSERT_RE = re.compile(r'INSERT\s+INTO\s+"?(\w+)"?', re.IGNORECASE)


class CensusDataError(RuntimeError):
    """Raised when the benchmark checkout cannot support a census run."""


def task_family_of(task_id: str) -> str:
    """Official scenario id for a task id.

    Mirrors `appworld.task.task_id_to_generator_id`: exactly one underscore,
    family = prefix, sibling number = suffix.
    """

    if task_id.count("_") != 1:
        raise CensusDataError(
            f"task id {task_id!r} must contain exactly one underscore "
            "(appworld.task.task_id_to_generator_id contract)"
        )
    family, _, number = task_id.partition("_")
    if not family or not number.isdigit() or int(number) < 1:
        raise CensusDataError(f"task id {task_id!r} is not <generator_id>_<number>")
    return family


def task_number_of(task_id: str) -> int:
    """Sibling number of a task id (mirrors `appworld.task.task_id_to_number`)."""

    task_family_of(task_id)
    return int(task_id.partition("_")[2])


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


@dataclass(frozen=True)
class TaskSpecs:
    task_id: str
    instruction: str
    datetime: str
    db_version: str
    canary_string: str | None
    supervisor: dict
    extras: dict = field(default_factory=dict)


@dataclass(frozen=True)
class TaskMetadata:
    """Benchmark-authored metadata for one task (`ground_truth/metadata.json`)."""

    difficulty: int | None
    num_apps: int | None
    num_apis: int | None
    num_api_calls: int | None
    num_solution_code_lines: int | None
    mode: str | None
    raw: dict

    @classmethod
    def from_dict(cls, payload: dict) -> "TaskMetadata":
        return cls(
            difficulty=payload.get("difficulty"),
            num_apps=payload.get("num_apps"),
            num_apis=payload.get("num_apis"),
            num_api_calls=payload.get("num_api_calls"),
            num_solution_code_lines=payload.get("num_solution_code_lines"),
            mode=payload.get("mode"),
            raw=payload,
        )


@dataclass(frozen=True)
class CensusTask:
    task_id: str
    family: str
    number: int
    #: The task directory itself, so callers can read the input db seed
    #: (`dbs/*.jsonl`) without re-deriving it from the data root.
    task_dir: Path
    specs: TaskSpecs
    metadata: TaskMetadata
    evaluation_path: Path
    evaluation_source: str
    test_data: list
    public_data: dict
    private_data: dict
    answer: object
    solution_source: str | None
    solution_path: Path | None
    split: str | None
    #: sha256 of specs.json + evaluation.py + metadata.json, for provenance.
    evidence_digest: str


class CensusDataset(Protocol):
    """Minimal interface so tests can run against synthetic inputs."""

    def families(self) -> dict[str, list[str]]: ...

    def task(self, task_id: str) -> CensusTask: ...

    def task_ids(self) -> list[str]: ...

    def anchor(self) -> dict: ...


def _read_json(path: Path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def read_state_seed_counts(task_dir: Path) -> dict[str, int]:
    """Row counts of the task-input db seed, keyed `<app>.<table>`.

    This is provenance/coverage evidence only: AppWorld seeds only a small
    subset of tables per task, so these counts are not app-data volumes.
    """

    counts: dict[str, int] = {}
    dbs_dir = task_dir / "dbs"
    if not dbs_dir.is_dir():
        return counts
    for jsonl_path in sorted(dbs_dir.glob("*.jsonl")):
        app = jsonl_path.stem
        for line in jsonl_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                statement = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(statement, list) or not statement:
                continue
            match = _INSERT_RE.match(str(statement[0]))
            if match:
                key = f"{app}.{match.group(1)}"
                counts[key] = counts.get(key, 0) + 1
    return counts


class AppWorldDataset:
    """Read a local AppWorld checkout without importing the runtime."""

    def __init__(self, data_root: Path | str):
        self.data_root = Path(data_root)
        self.tasks_root = self.data_root / "tasks"
        if not self.tasks_root.is_dir():
            raise CensusDataError(f"no tasks directory at {self.tasks_root}")
        self._splits = self._load_splits()
        self._task_cache: dict[str, CensusTask] = {}

    def _load_splits(self) -> dict[str, str]:
        split_of: dict[str, str] = {}
        datasets_dir = self.data_root / "datasets"
        for split in DATASET_SPLITS:
            path = datasets_dir / f"{split}.txt"
            if not path.exists():
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                task_id = line.strip()
                if task_id:
                    split_of[task_id] = split
        return split_of

    def version(self) -> str | None:
        path = self.data_root / "version.txt"
        return path.read_text(encoding="utf-8").strip() if path.exists() else None

    def task_ids(self) -> list[str]:
        return sorted(p.name for p in self.tasks_root.iterdir() if p.is_dir())

    def families(self) -> dict[str, list[str]]:
        grouped: dict[str, list[str]] = {}
        for task_id in self.task_ids():
            grouped.setdefault(task_family_of(task_id), []).append(task_id)
        return {
            family: sorted(task_ids, key=task_number_of)
            for family, task_ids in sorted(grouped.items())
        }

    def lineage_warnings(self, family: str, task_ids: Iterable[str]) -> list[str]:
        """Report deviations from the upstream contiguous-1..N scenario contract."""

        numbers = sorted(task_number_of(t) for t in task_ids)
        expected = list(range(1, len(numbers) + 1))
        if numbers != expected:
            return [
                f"scenario {family} numbers {numbers} are not the contiguous "
                f"range {expected} required by appworld.task._maybe_assure_num_tasks_per_scenario"
            ]
        return []

    def task(self, task_id: str) -> CensusTask:
        if task_id in self._task_cache:
            return self._task_cache[task_id]
        task_dir = self.tasks_root / task_id
        if not task_dir.is_dir():
            raise CensusDataError(f"unknown task {task_id!r} under {self.tasks_root}")
        specs_raw = _read_json(task_dir / "specs.json")
        if specs_raw is None:
            raise CensusDataError(f"task {task_id!r} has no specs.json")
        meta_raw = _read_json(task_dir / "ground_truth" / "metadata.json") or {}
        evaluation_path = task_dir / "ground_truth" / "evaluation.py"
        evaluation_source = (
            evaluation_path.read_text(encoding="utf-8") if evaluation_path.exists() else ""
        )
        solution_path = task_dir / "ground_truth" / "solution.py"
        solution_source = (
            solution_path.read_text(encoding="utf-8") if solution_path.exists() else None
        )
        director = specs_raw.get("supervisor") or specs_raw.get("main_user") or {}
        specs = TaskSpecs(
            task_id=task_id,
            instruction=specs_raw.get("instruction", ""),
            datetime=specs_raw.get("datetime", ""),
            db_version=specs_raw.get("db_version", ""),
            canary_string=specs_raw.get("canary_string"),
            supervisor=director,
            extras={
                key: value
                for key, value in specs_raw.items()
                if key
                not in {"instruction", "datetime", "db_version", "canary_string", "supervisor"}
            },
        )
        spec_bytes = (task_dir / "specs.json").read_bytes()
        meta_bytes = (
            (task_dir / "ground_truth" / "metadata.json").read_bytes()
            if (task_dir / "ground_truth" / "metadata.json").exists()
            else b""
        )
        eval_bytes = evaluation_path.read_bytes() if evaluation_path.exists() else b""
        digest = sha256_bytes(spec_bytes + meta_bytes + eval_bytes)
        task = CensusTask(
            task_id=task_id,
            family=task_family_of(task_id),
            number=task_number_of(task_id),
            task_dir=task_dir,
            specs=specs,
            metadata=TaskMetadata.from_dict(meta_raw),
            evaluation_path=evaluation_path,
            evaluation_source=evaluation_source,
            test_data=_read_json(task_dir / "ground_truth" / "test_data.json") or [],
            public_data=_read_json(task_dir / "ground_truth" / "public_data.json") or {},
            private_data=_read_json(task_dir / "ground_truth" / "private_data.json") or {},
            answer=_read_json(task_dir / "ground_truth" / "answer.json"),
            solution_source=solution_source,
            solution_path=solution_path if solution_source else None,
            split=self._splits.get(task_id),
            evidence_digest=digest,
        )
        self._task_cache[task_id] = task
        return task

    def anchor(self) -> dict:
        """Stable identity of the analysed dataset, for the provenance block."""

        families = self.families()
        digest = hashlib.sha256()
        for task_id in self.task_ids():
            digest.update(task_id.encode())
            digest.update(self.task(task_id).evidence_digest.encode())
        return {
            "data_root": str(self.data_root),
            "benchmark_version": self.version(),
            "task_count": len(self.task_ids()),
            "family_count": len(families),
            "dataset_split_files": {
                split: sum(1 for v in self._splits.values() if v == split)
                for split in DATASET_SPLITS
            },
            "dataset_content_sha256": digest.hexdigest(),
        }
