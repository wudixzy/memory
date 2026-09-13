"""Synthetic AppWorld-shaped fixtures for the offline census tests.

These fixtures are infrastructure only. They exist so the census logic can be
tested without the 59 MB benchmark checkout, and they are never scientific
evidence for anything.
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path

CANARY = "appworld:test:00000000-0000-0000-0000-000000000000"

#: (family, [instructions per sibling number], [num_api_calls per sibling])
FAMILIES = (
    # A family whose reference procedure resolves the same entity twice, with a
    # registered-band cost gap and no comparison marker -> should shortlist.
    (
        "aaaaaaa",
        [
            "Like all the songs from the artists I follow.",
            "Like all the songs from the artists I follow.",
            "Like all the songs from the artists I follow.",
        ],
        [90, 40, 60],
    ),
    # A family whose instruction demands the comparison -> gate 5 rejection.
    (
        "bbbbbbb",
        [
            "See if it is a better deal and order whichever option is cheaper.",
            "Order whichever option is cheaper.",
            "Order whichever option is cheaper.",
        ],
        [40, 30, 35],
    ),
    # A family with no cost gap -> rejected below the registered band.
    (
        "ccccccc",
        ["Do the thing.", "Do the thing.", "Do the thing."],
        [50, 51, 50],
    ),
    # A family with no reference solution at all -> rejected as unanalysable.
    (
        "ddddddd",
        ["Send a message to my roommates.", "Send a message to my siblings.", "Send a message."],
        [None, None, None],
    ),
)

#: The reference procedure used for the first family's three siblings.
DUPLICATE_PROBE_SOLUTION = """
from appworld.common.utils import find_all_from_pages


def _solution(main_user, apis, requester, public_data):
    access_token = apis.spotify.access_token_from(main_user)
    songs = find_all_from_pages(apis.spotify.show_song_library, access_token=access_token)
    if public_data.mode in ("a", "b"):
        for song in songs:
            detail = apis.spotify.show_song(song_id=song.song_id)
            apis.spotify.like_song(raise_on_failure=False, access_token=access_token,
                                   song_id=detail.song_id)
        for song in songs:
            detail = apis.spotify.show_song(song_id=song.song_id)
            apis.spotify.like_song(raise_on_failure=False, access_token=access_token,
                                   song_id=detail.song_id)
    return None
"""

SIMPLE_SOLUTION = """
def _solution(main_user, apis, requester, public_data):
    access_token = apis.phone.access_token_from(main_user)
    apis.phone.send_text_message(to="x", message="y")
    return None
"""

EVALUATION_TEMPLATE = """# Canary String: {canary}
def evaluate(test, public_data, private_data, main_user, models, ground_truth_answer):
    with test("assert model changes match phone.Message"):
        test.case(models.changed_model_names(), "==", {{"phone.Message"}})
"""

#: Minimal api docs covering the APIs the fixture solutions call.
API_DOCS = (
    (
        "spotify",
        "access_token_from",
        "Get an access token.",
        [{"name": "main_user", "type": "string"}],
        {"success": {"access_token": "string"}, "failure": {"message": "string"}},
    ),
    (
        "spotify",
        "show_song_library",
        "Get a list of songs in the user's song library.",
        [{"name": "access_token", "type": "string"}, {"name": "page_index", "type": "integer"}],
        {"success": [{"song_id": 1, "title": "string"}], "failure": {"message": "string"}},
    ),
    (
        "spotify",
        "show_song",
        "Get details of a specific song.",
        [{"name": "song_id", "type": "integer"}],
        {
            "success": {"song_id": 1, "title": "string", "release_date": "2019-01-01"},
            "failure": {"message": "string"},
        },
    ),
    (
        "spotify",
        "search_songs",
        "Search songs.",
        [
            {"name": "query", "type": "string"},
            {"name": "artist_id", "type": "integer"},
            {"name": "page_index", "type": "integer"},
        ],
        {
            "success": [{"song_id": 1, "title": "string", "release_date": "2019-01-01"}],
            "failure": {"message": "string"},
        },
    ),
    (
        "spotify",
        "like_song",
        "Like a song.",
        [{"name": "access_token", "type": "string"}, {"name": "song_id", "type": "integer"}],
        {"success": {"message": "string"}, "failure": {"message": "string"}},
    ),
    # A list API with no server-side filter: must NOT be accepted as a strict
    # bulk replacement for a per-entity probe.
    (
        "spotify",
        "show_downloaded_songs",
        "List downloaded songs.",
        [{"name": "access_token", "type": "string"}, {"name": "page_index", "type": "integer"}],
        {
            "success": [{"song_id": 1, "release_date": "2019-01-01"}],
            "failure": {"message": "string"},
        },
    ),
    (
        "phone",
        "access_token_from",
        "Get an access token.",
        [{"name": "main_user", "type": "string"}],
        {"success": {"access_token": "string"}, "failure": {"message": "string"}},
    ),
    (
        "phone",
        "search_contacts",
        "Search contacts.",
        [{"name": "query", "type": "string"}, {"name": "relationship", "type": "string"}],
        {
            "success": [{"contact_id": 1, "email": "user@example.com"}],
            "failure": {"message": "string"},
        },
    ),
    (
        "phone",
        "send_text_message",
        "Send a text message.",
        [{"name": "to", "type": "string"}, {"name": "message", "type": "string"}],
        {"success": {"message": "string"}, "failure": {"message": "string"}},
    ),
)


def write_api_docs_db(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute(
        """
        CREATE TABLE api_docs (
            id INTEGER PRIMARY KEY,
            app_name_ TEXT,
            api_name TEXT,
            path TEXT,
            method TEXT,
            description TEXT,
            parameters TEXT,
            response_schemas TEXT,
            record_hash TEXT
        )
        """
    )
    for index, (app, api, description, parameters, schema) in enumerate(API_DOCS, start=1):
        connection.execute(
            "INSERT INTO api_docs VALUES (?,?,?,?,?,?,?,?,?)",
            (
                index,
                app,
                api,
                f"/{app}/{api}",
                "POST",
                description,
                json.dumps(parameters),
                json.dumps(schema),
                f"hash-{index}",
            ),
        )
    connection.commit()
    connection.close()
    return path


def write_task(
    tasks_root: Path,
    task_id: str,
    instruction: str,
    num_api_calls: int | None,
    solution_source: str | None,
    requirements: list[str] | None = None,
) -> None:
    task_dir = tasks_root / task_id
    (task_dir / "ground_truth").mkdir(parents=True, exist_ok=True)
    (task_dir / "dbs").mkdir(parents=True, exist_ok=True)
    (task_dir / "specs.json").write_text(
        json.dumps(
            {
                "instruction": instruction,
                "supervisor": {"first_name": "Test", "last_name": "User"},
                "datetime": "2023-05-18T12:00:00",
                "db_version": "0.1.0",
                "canary_string": CANARY,
            }
        ),
        encoding="utf-8",
    )
    metadata = {
        "mode": "full",
        "difficulty": 1,
        "num_apps": 1,
        "num_apis": 3,
        "num_api_calls": num_api_calls if num_api_calls is not None else 0,
        "num_solution_code_lines": 10,
    }
    (task_dir / "ground_truth" / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    if num_api_calls is None:
        # Missing metadata must be reported as unknown, not as zero.
        (task_dir / "ground_truth" / "metadata.json").write_text(
            json.dumps({k: v for k, v in metadata.items() if k != "num_api_calls"}),
            encoding="utf-8",
        )
    (task_dir / "ground_truth" / "evaluation.py").write_text(
        EVALUATION_TEMPLATE.format(canary=CANARY), encoding="utf-8"
    )
    (task_dir / "ground_truth" / "test_data.json").write_text(
        json.dumps(
            [
                {"requirement": requirement, "label": "no_op_fail"}
                for requirement in (requirements or ["assert model changes match phone.Message"])
            ]
        ),
        encoding="utf-8",
    )
    (task_dir / "ground_truth" / "public_data.json").write_text(
        json.dumps({"mode": "a"}), encoding="utf-8"
    )
    (task_dir / "ground_truth" / "private_data.json").write_text(
        json.dumps({"secret_id": 7}), encoding="utf-8"
    )
    if solution_source is not None:
        (task_dir / "ground_truth" / "solution.py").write_text(solution_source, encoding="utf-8")
    (task_dir / "dbs" / "supervisor.jsonl").write_text(
        json.dumps(
            [
                "INSERT INTO supervisors (first_name, last_name) VALUES (?, ?)",
                ["Test", "User"],
                False,
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def write_dataset(root: Path) -> Path:
    """Create the synthetic benchmark tree and return its `data/` root."""

    data_root = root / "data"
    tasks_root = data_root / "tasks"
    tasks_root.mkdir(parents=True, exist_ok=True)
    (data_root / "datasets").mkdir(parents=True, exist_ok=True)
    (data_root / "version.txt").write_text("test-0.1.0\n", encoding="utf-8")
    write_api_docs_db(data_root / "base_dbs" / "api_docs.db")

    for family, instructions, calls in FAMILIES:
        for number, instruction in enumerate(instructions, start=1):
            task_id = f"{family}_{number}"
            if family == "aaaaaaa":
                solution = DUPLICATE_PROBE_SOLUTION
            elif family == "ddddddd":
                solution = None
            else:
                solution = SIMPLE_SOLUTION
            write_task(
                tasks_root,
                task_id,
                instruction,
                calls[number - 1],
                solution,
            )
    (data_root / "datasets" / "train.txt").write_text(
        "\n".join(f"{family}_{number}" for family, _, _ in FAMILIES for number in (1, 2, 3)) + "\n",
        encoding="utf-8",
    )
    return data_root


class synthetic_dataset:
    """Context manager yielding a synthetic `data/` root."""

    def __enter__(self) -> Path:
        self._tmp = tempfile.TemporaryDirectory()
        return write_dataset(Path(self._tmp.name))

    def __exit__(self, *args) -> None:
        self._tmp.cleanup()
