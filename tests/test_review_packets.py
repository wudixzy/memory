"""Offline tests for the reserve manifest and the bounded review packets.

A synthetic census artifact plus a synthetic benchmark tree; no model call, no
network access, no benchmark execution. Covers the properties `docs/29` relies
on: every reserve family is emitted, a packet identifies its family and is
hard-bounded in bytes, unmeasured quantities stay explicit, provenance is
checkable against the local checkout, forbidden consumers are refused, and the
builder stays inside the census import boundary.
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from fixtures_census import DUPLICATE_PROBE_SOLUTION, write_api_docs_db, write_task  # noqa: E402

from memory_census.api_surface import ApiSurface  # noqa: E402
from memory_census.boundary import (  # noqa: E402
    ALLOWED_CONSUMERS,
    FORBIDDEN_CONSUMERS,
    FORBIDDEN_IMPORT_PREFIXES,
    FORBIDDEN_NETWORK_MODULES,
    BoundaryViolation,
    assert_boundary_intact,
    imported_module_names,
    iter_source_files,
    static_import_violations,
)
from memory_census.packets import (  # noqa: E402
    MANIFEST_VERSION,
    PACKET_CONSUMER,
    PACKET_VERSION,
    RESERVE_STATUS,
    UNMEASURED,
    USAGE_SCOPE,
    PacketBudgetError,
    PacketLimits,
    build_packet,
    build_reserve_manifest,
    canonical_sha256,
    file_fact,
    packet_paths,
    packet_text,
    render_packet_markdown,
    reserve_entries,
)

PACKETS_MODULE = ROOT / "src" / "memory_census" / "packets.py"
REVIEW_SCRIPT = ROOT / "scripts" / "analysis" / "appworld_review_packets.py"

#: Marker `packets._cap_text` appends to every capped string.
TRUNCATION_MARKER = "…[truncated]"

#: Imports `packets.py` is allowed to have. Everything else — the AppWorld
#: runtime, the ACE runtime, a model client, a socket — breaks the boundary the
#: module's own docstring claims it respects.
ALLOWED_BUILDER_IMPORTS = frozenset(
    {
        "__future__",
        "dataclasses",
        "hashlib",
        "json",
        "pathlib",
        "memory_census.api_surface",
        "memory_census.boundary",
    }
)


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


script = load("appworld_review_packets", REVIEW_SCRIPT)

FAMILY = "aaaaaaa"
SOURCE_TASK = "aaaaaaa_1"
TARGET_TASK = "aaaaaaa_2"
SIBLING_TASK = "aaaaaaa_3"
RESERVE_FAMILIES = (FAMILY, "bbbbbbb", "ccccccc")
REJECTED_FAMILY = "ddddddd"
INSTRUCTION = "Like all the songs from the artists I follow."
PLAYBOOK_SHA = "3c4f46888c9159088c3eb8f70e879d4d28a5704ab9f15d132563ba0ee2730b7b"
LINEAGE_WARNING = "sibling instructions differ beyond a parameter substitution"


def line_of(solution: str, needle: str) -> int:
    for number, line in enumerate(solution.splitlines(), start=1):
        if needle in line:
            return number
    raise AssertionError(f"synthetic solution has no line containing {needle!r}")


def call_sites(solution: str = DUPLICATE_PROBE_SOLUTION) -> list[dict]:
    return [
        {
            "name": "spotify.access_token_from",
            "line": line_of(solution, "access_token_from"),
            "inside_loop": False,
        },
        {
            "name": "spotify.show_song_library",
            "line": line_of(solution, "show_song_library"),
            "inside_loop": False,
            "via_pagination_helper": True,
        },
        {
            "name": "spotify.show_song",
            "line": line_of(solution, "show_song(song_id"),
            "inside_loop": True,
            "resolution_key": "song.id",
            "read_fields": ["genre"],
        },
    ]


def reserve_record(
    family: str = FAMILY,
    instruction: str = INSTRUCTION,
    solution: str = DUPLICATE_PROBE_SOLUTION,
) -> dict:
    """One synthetic Stage-A reserve record, shaped like a real census record."""

    source_task_id, target_task_id, sibling_task_id = (f"{family}_{n}" for n in (1, 2, 3))
    sites = call_sites(solution)
    tasks = [
        {
            "task_id": task_id,
            "number": number,
            "split": "dev",
            "difficulty": 2,
            "num_apps": 1,
            "num_apis": 10,
            "num_api_calls": 40,
            "instruction": instruction,
            "has_reference_solution": True,
        }
        for number, task_id in enumerate((source_task_id, target_task_id, sibling_task_id), 1)
    ]
    return {
        "family": family,
        "task_ids": [source_task_id, target_task_id, sibling_task_id],
        "status": RESERVE_STATUS,
        "status_reasons": ["b_route_saving_below_registered_band", "reference_cost_gap_band:weak"],
        "tasks": tasks,
        "cost": {
            "tasks": [
                {"task_id": source_task_id, "number": 1, "total_calls": 90},
                {"task_id": target_task_id, "number": 2, "total_calls": 40},
            ]
        },
        "comparison_gate": {
            "forces_comparison": False,
            "triggers": [],
            "per_task": {source_task_id: False, target_task_id: False},
        },
        "strategy": {
            "reference_procedure_identical_across_family": True,
            "structural_saving_call_sites": 1,
            "alternatives_note": "offline structural hypotheses only",
            "procedure_signatures": {
                source_task_id: "spotify.access_token_from -> spotify.show_song[loop]",
                target_task_id: "spotify.access_token_from -> spotify.show_song[loop]",
            },
            "alternatives": [
                {
                    "alternative_id": "duplicate-entity-probe-cache",
                    "kind": "duplicate-entity-probe",
                    "summary": "cache repeated entity lookups instead of re-resolving them",
                    "replaces": ["spotify.show_song"],
                    "saving_call_sites": 1,
                    "verdict": "supported",
                    "verification": {
                        "probe_api": {"name": "spotify.show_song"},
                        "bulk_api": {"name": "spotify.search_songs"},
                    },
                },
                {
                    "alternative_id": "bulk-filter-route:spotify.search_songs",
                    "kind": "bulk-filter-route",
                    "summary": "replace per-entity probes with one filtered list call",
                    "replaces": ["spotify.show_song"],
                    "saving_call_sites": 4,
                    "verdict": "weakly_supported",
                },
            ],
            "per_task": {
                source_task_id: {"task_id": source_task_id, "call_sites": sites},
                target_task_id: {"task_id": target_task_id, "call_sites": sites},
            },
        },
        "state_differences": {
            "pairs": [],
            "selected_pair": {
                "family": family,
                "source_task_id": source_task_id,
                "target_task_id": target_task_id,
                "classification": "parameter_value_change",
                "classification_rationale": "only a public_data scalar changed",
                "strategy_relevant_change": False,
                "route_changed": False,
                "strategy_shift_witness": False,
                "same_reference_solution": True,
                "instruction": {
                    "identical": True,
                    "source_instruction": instruction,
                    "target_instruction": instruction,
                    "changed_spans": [],
                },
                "public_data": {
                    "value_changes": [{"key": "top_k", "source": 4, "target": 6}],
                },
                "private_data": {"keys_only_in_source": [], "value_changes": []},
                "seed_state": {"row_count_changes": [{"table": "supervisor.tasks"}]},
                "evaluator": {"requirements_identical": True, "target_requirements": ["no change"]},
                "reference": {"both_solutions_available": True, "same_reference_solution": True},
                "change_evidence": [
                    {"kind": "instruction_span", "op": "replace", "source_text": "4"},
                    {"kind": "branch_parameter", "key": "genre", "target": "EDM"},
                ],
            },
            "role_assignment": {
                "source_task_ids": [source_task_id],
                "target_task_ids": [target_task_id],
                "status": "nominated",
                "basis": "sibling state-difference selection",
                "selection_rule": "the cost gap is never consulted",
                "rationale": "the target is the sibling with the largest setup change",
                "selected_pair": {
                    "classification": "parameter_value_change",
                    "route_changed": False,
                },
                "cost_was_not_consulted": True,
                "review_override": None,
            },
        },
        "candidate": {
            "family": family,
            "source_task_ids": [source_task_id],
            "target_task_ids": [target_task_id],
            "candidate_C": {"strategy": "C", "status": "reference_procedure"},
            "candidate_B": {
                "strategy": "B",
                "status": "reference_supported_route",
                "alternative_id": "duplicate-entity-probe-cache",
                "route": "duplicate-entity-probe",
                "description": "cache entity-keyed lookups instead of re-resolving them",
                "replaces": ["spotify.show_song"],
                "evidence_class": "reference_only",
                "evidence_grade": "reference_supported",
                "verdict": "supported",
                "structural_saving_call_sites": 1,
                "discoverability": "unmeasured",
                "rejected_alternatives": [
                    {"alternative_id": "cache-by-api-only", "verdict": "refuted"}
                ],
                "refuted_candidates": ["cache-by-api-only"],
            },
            "cost_C": {"strategy": "C", "value": 40, "unit": "public_api_calls"},
            "cost_B": {"strategy": "B", "value": "unknown", "unit": "public_api_calls"},
            "c_success_on_target": {
                "status": "reference_only",
                "target_task_id": target_task_id,
                "reference_call_count_on_target": 40,
            },
            "c_vs_b_comparison": {"cost_C": {"value": 40}, "cost_B": {"value": "unknown"}},
            "why_C_is_source_appropriate": "C is the benchmark's own reference procedure here.",
            "why_B_is_target_better": "unknown: B has never been executed on the target.",
            "k0_static_overlap": {
                "level": "medium",
                "statement": "the K_0 playbook encodes the scaffolding the costly route uses",
                "matched_scaffolding_terms": ["page_index"],
                "matched_preference_terms": [],
            },
            "admission": {
                "status": RESERVE_STATUS,
                "reason_code": "b_route_saving_below_registered_band",
                "reason": "the structural saving bound does not reach the registered band",
                "gates": [{"gate": "G5_candidate_b_route", "passed": False}],
            },
            "evidence_provenance": {
                "family": family,
                "per_task": {source_task_id: {"solution_sha256": "0" * 64}},
            },
        },
    }


def artifact_records() -> list[dict]:
    """Artifact order deliberately differs from family-id order."""

    rejected = {**reserve_record(REJECTED_FAMILY), "status": "rejected"}
    unstated = reserve_record("eeeeeee")
    del unstated["status"]
    return [
        reserve_record("ccccccc"),
        rejected,
        reserve_record(FAMILY),
        unstated,
        reserve_record("bbbbbbb"),
    ]


def census_artifact(*records: dict) -> dict:
    return {
        "census_version": "synthetic-census-v1",
        "registry_version": "synthetic-registry-v1",
        "generated_by": "tests/test_review_packets.py",
        "families": list(records),
        "family_lineage": [
            {
                "family": record["family"],
                "lineage_warnings": [LINEAGE_WARNING] if record["family"] == "bbbbbbb" else [],
            }
            for record in records
        ],
        "provenance": {
            "benchmark": {"benchmark_version": "0.1.0", "data_root": "/synthetic/data"},
            "playbook": {
                "path": "experiments/playbooks/appworld_initial_playbook.txt",
                "sha256": PLAYBOOK_SHA,
            },
        },
    }


def write_benchmark(root: Path, families=RESERVE_FAMILIES) -> Path:
    data_root = root / "data"
    tasks_root = data_root / "tasks"
    tasks_root.mkdir(parents=True, exist_ok=True)
    write_api_docs_db(data_root / "base_dbs" / "api_docs.db")
    for family in families:
        for number in (1, 2, 3):
            write_task(
                tasks_root,
                f"{family}_{number}",
                INSTRUCTION,
                40,
                DUPLICATE_PROBE_SOLUTION,
            )
    return data_root


class ReviewFixture:
    """Synthetic census artifact + benchmark tree + api docs db for one test."""

    def __enter__(self) -> "ReviewFixture":
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.artifact = census_artifact(*artifact_records())
        self.census_path = root / "census.json"
        self.census_path.write_text(json.dumps(self.artifact, indent=2) + "\n", encoding="utf-8")
        self.data_root = write_benchmark(root)
        self.out_dir = root / "packets"
        self.surface = ApiSurface(self.data_root / "base_dbs" / "api_docs.db")
        self.manifest = build_reserve_manifest(
            self.artifact,
            census_path=self.census_path,
            data_root=self.data_root,
            packet_dir=self.out_dir,
        )
        return self

    def __exit__(self, *args) -> None:
        self.surface.close()
        self._tmp.cleanup()

    def record(self, family: str = FAMILY) -> dict:
        return next(r for r in self.artifact["families"] if r["family"] == family)

    def entry(self, family: str = FAMILY) -> dict:
        return next(e for e in self.manifest["families"] if e["family_id"] == family)

    def census_ref(self, family: str = FAMILY) -> dict:
        return {
            **self.manifest["census"],
            "json_pointer": self.entry(family)["candidate_record"]["json_pointer"],
            "benchmark_version": self.artifact["provenance"]["benchmark"]["benchmark_version"],
            "playbook": self.artifact["provenance"]["playbook"],
        }

    def packet_for(self, record: dict, **kwargs) -> dict:
        return build_packet(
            record,
            data_root=self.data_root,
            api_surface=self.surface,
            census_ref=self.census_ref(record["family"]),
            **kwargs,
        )

    def packet(self, family: str = FAMILY, **kwargs) -> dict:
        return self.packet_for(self.record(family), **kwargs)

    def run_script(self, *extra: str) -> str:
        """Run the review script on the fixture; returns its stdout."""

        args = [
            "--census",
            str(self.census_path),
            "--data-root",
            str(self.data_root),
            "--api-docs-db",
            str(self.data_root / "base_dbs" / "api_docs.db"),
            "--out-dir",
            str(self.out_dir),
            *extra,
        ]
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.script_status = script.main(args)
        return output.getvalue()


def pathological_record() -> dict:
    """A reserve record whose evidence is far larger than any budget allows."""

    record = reserve_record()
    long_text = "the reference procedure resolves the same entity more than once " * 40
    record["tasks"][0]["instruction"] = long_text
    record["tasks"][1]["instruction"] = long_text
    selected = record["state_differences"]["selected_pair"]
    selected["instruction"] = {
        "identical": False,
        "source_instruction": long_text,
        "target_instruction": long_text,
        "changed_spans": [{"op": "replace", "source_text": long_text} for _ in range(20)],
    }
    selected["private_data"] = {f"secret_{index}": long_text for index in range(60)}
    selected["change_evidence"] = [
        {"kind": "instruction_span", "source_text": long_text, "target_text": long_text}
        for _ in range(40)
    ]
    record["strategy"]["alternatives"] = [
        {
            "alternative_id": f"bulk-filter-route:spotify.api_{index}",
            "summary": long_text,
            "replaces": [f"spotify.api_{other}" for other in range(20)],
            "saving_call_sites": index,
            "verdict": "weakly_supported",
        }
        for index in range(20)
    ]
    record["strategy"]["per_task"][SOURCE_TASK]["call_sites"] = [
        {"name": f"spotify.api_{index}", "line": index + 1, "read_fields": [long_text]}
        for index in range(40)
    ]
    record["candidate"]["k0_static_overlap"]["matched_scaffolding_terms"] = [
        f"term {index} {long_text}" for index in range(60)
    ]
    record["candidate"]["candidate_B"] = {
        **record["candidate"]["candidate_B"],
        "description": long_text,
        "replaces": [f"spotify.api_{index}" for index in range(60)],
    }
    return record


class ReviewFixtureTest(unittest.TestCase):
    def setUp(self):
        self.fixture = ReviewFixture()
        self.fixture.__enter__()
        self.addCleanup(self.fixture.__exit__, None, None, None)


class ReserveEmissionTests(ReviewFixtureTest):
    def census_sha256(self) -> str:
        return hashlib.sha256(self.fixture.census_path.read_bytes()).hexdigest()

    def test_reserve_entries_are_the_reserves_only_in_family_id_order(self):
        entries = reserve_entries(self.fixture.artifact)
        self.assertEqual(
            [record["family"] for _, record in entries],
            sorted(RESERVE_FAMILIES),
        )
        # Indices stay artifact-order positions, so a reviewer can dereference
        # `/families/<index>` in the census JSON.
        self.assertEqual([index for index, _ in entries], [2, 4, 0])

    def test_manifest_emits_every_reserve_family_once(self):
        manifest = self.fixture.manifest
        self.assertEqual(manifest["manifest_version"], MANIFEST_VERSION)
        self.assertEqual(
            [entry["family_id"] for entry in manifest["families"]],
            sorted(RESERVE_FAMILIES),
        )
        self.assertEqual(manifest["counts"]["reserve_families"], len(RESERVE_FAMILIES))
        self.assertEqual(
            manifest["counts"]["census_families"], len(self.fixture.artifact["families"])
        )
        self.assertEqual(manifest["counts"]["packets"], len(RESERVE_FAMILIES))
        self.assertEqual(manifest["census"]["sha256"], self.census_sha256())
        for entry in manifest["families"]:
            self.assertEqual(entry["status"], RESERVE_STATUS)
            self.assertEqual(
                entry["admission"]["reason_code"], "b_route_saving_below_registered_band"
            )
            self.assertEqual(
                entry["packet"]["path"],
                str(self.fixture.out_dir / entry["family_id"] / "packet.json"),
            )
            self.assertEqual(entry["source_task_id"], f"{entry['family_id']}_1")
            self.assertEqual(entry["target_task_id"], f"{entry['family_id']}_2")

    def test_manifest_carries_lineage_warnings_and_evidence_paths(self):
        self.assertEqual(self.fixture.entry("bbbbbbb")["lineage_warnings"], [LINEAGE_WARNING])
        self.assertEqual(self.fixture.entry(FAMILY)["lineage_warnings"], [])
        for entry in self.fixture.manifest["families"]:
            for task_id in entry["task_ids"]:
                files = entry["evidence"]["tasks"][task_id]
                self.assertEqual(
                    files["solution"]["path"],
                    str(
                        self.fixture.data_root / "tasks" / task_id / "ground_truth" / "solution.py"
                    ),
                )
                self.assertTrue(files["solution"]["sha256"])
                self.assertEqual(files["db_seed_files_total"], 1)
        self.assertEqual(
            self.fixture.manifest["families"][0]["evidence"]["playbook"]["sha256"], PLAYBOOK_SHA
        )

    def test_script_check_mode_covers_every_reserve_without_writing(self):
        output = self.fixture.run_script("--check")
        self.assertEqual(self.fixture.script_status, 0)
        self.assertRegex(
            output,
            rf"checked {len(RESERVE_FAMILIES)} packet\(s\) for "
            rf"{len(RESERVE_FAMILIES)} reserve families; max packet \d+ bytes",
        )
        self.assertFalse(self.fixture.out_dir.exists())

    def test_script_family_filter_builds_only_the_requested_family(self):
        output = self.fixture.run_script("--family", "bbbbbbb", "--check")
        self.assertEqual(self.fixture.script_status, 0)
        self.assertIn(
            f"checked 1 packet(s) for {len(RESERVE_FAMILIES)} reserve families",
            output,
        )

    def test_script_refuses_to_run_without_a_census_artifact(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = script.main(["--census", str(self.fixture.out_dir / "absent.json"), "--check"])
        self.assertEqual(status, 2)
        self.assertIn("no census artifact at", output.getvalue())


class PacketIdentityTests(ReviewFixtureTest):
    def test_packet_identifies_its_family_tasks_and_consumer(self):
        packet = self.fixture.packet()
        self.assertEqual(packet["packet_version"], PACKET_VERSION)
        self.assertEqual(packet["packet_id"], FAMILY)
        self.assertEqual(packet["consumer"], PACKET_CONSUMER)
        self.assertEqual(packet["usage_scope"], USAGE_SCOPE)
        self.assertIn("Never inject into Generator/Reflector/Curator", packet["usage_scope"])
        family = packet["family"]
        self.assertEqual(family["family_id"], FAMILY)
        self.assertEqual(family["task_ids"], [SOURCE_TASK, TARGET_TASK, SIBLING_TASK])
        self.assertEqual(family["source_task_id"], SOURCE_TASK)
        self.assertEqual(family["target_task_id"], TARGET_TASK)
        self.assertEqual(family["admission"]["status"], RESERVE_STATUS)
        self.assertIn("b_route_saving_below_registered_band", family["admission"]["status_reasons"])
        self.assertEqual(packet["instructions"]["source"]["task_id"], SOURCE_TASK)
        self.assertTrue(packet["instructions"]["source"]["available"])
        self.assertEqual(packet["instructions"]["target"]["instruction"], INSTRUCTION)
        self.assertEqual(packet["instructions"]["source"]["split"], "dev")

    def test_packet_carries_the_evidence_docs_29_asks_for(self):
        packet = self.fixture.packet()
        self.assertEqual(
            packet["reference_strategy_C"]["focus_apis"],
            ["spotify.show_song", "spotify.search_songs"],
        )
        self.assertEqual(
            packet["reference_strategy_C"]["focus_basis"],
            "candidate-B route APIs named by the census",
        )
        self.assertEqual(
            packet["state_setup_differences"]["classification"], "parameter_value_change"
        )
        self.assertTrue(packet["state_setup_differences"]["available"])
        self.assertEqual(packet["comparison_gate"]["forces_comparison"], False)
        self.assertEqual(packet["k0_static_playbook_overlap"]["level"], "medium")
        self.assertEqual(
            packet["candidate_b_routes"]["candidate_B_status"], "reference_supported_route"
        )
        self.assertEqual(
            [route["verdict"] for route in packet["candidate_b_routes"]["census_alternatives"]],
            ["supported", "weakly_supported"],
        )
        documented = {doc["name"]: doc for doc in packet["public_api_documentation"]}
        self.assertTrue(documented["spotify.show_song"]["documented"])
        self.assertIn("song_id", documented["spotify.show_song"]["response_fields"])
        self.assertIn("search_songs", documented["spotify.search_songs"]["name"])

    def test_packet_snippets_are_windows_not_whole_solutions(self):
        packet = self.fixture.packet()
        solution_lines = len(DUPLICATE_PROBE_SOLUTION.splitlines())
        windows = packet["reference_solution_snippets"]["windows"]
        self.assertEqual([window["role"] for window in windows], ["source", "target"])
        for window in windows:
            self.assertEqual(window["cite"], "spotify.show_song")
            self.assertIn("show_song(song_id", window["code"])
            self.assertLess(len(window["code"].splitlines()), solution_lines)
        for facts in packet["reference_solution_snippets"]["per_role"]:
            self.assertEqual(facts["solution_lines"], solution_lines)
            self.assertEqual(facts["emitted_windows"], 1)
            self.assertLess(facts["emitted_lines"], solution_lines)

    def test_packet_paths_are_deterministic_per_family(self):
        repo_dir = ROOT / "artifacts" / "appworld_review_packets"
        paths = packet_paths(FAMILY, repo_dir)
        self.assertEqual(paths["path"], f"artifacts/appworld_review_packets/{FAMILY}/packet.json")
        self.assertEqual(
            paths["markdown_path"], f"artifacts/appworld_review_packets/{FAMILY}/packet.md"
        )
        outside = packet_paths(FAMILY, self.fixture.out_dir)
        self.assertEqual(outside["path"], str(self.fixture.out_dir / FAMILY / "packet.json"))

    def test_markdown_rendering_names_the_family_and_its_packet_id(self):
        markdown = render_packet_markdown(self.fixture.packet())
        self.assertIn(f"# Reserve review packet — {FAMILY}", markdown)
        self.assertIn("## Provenance", markdown)

    def test_packet_identity_is_stable_across_builds(self):
        with ReviewFixture() as fixture:
            first = packet_text(fixture.packet())
            second = packet_text(fixture.packet())
        self.assertEqual(first, second)
        self.assertTrue(first.endswith("\n"))


class UnmeasuredTests(ReviewFixtureTest):
    def test_every_unmeasured_statement_is_explicit_in_packet_and_manifest(self):
        packet = self.fixture.packet()
        for block in (packet["unmeasured"], self.fixture.manifest["unmeasured"]):
            for key, statement in UNMEASURED.items():
                self.assertIn(key, block)
                self.assertTrue(str(block[key]).strip())
            self.assertNotEqual(block, {})
        self.assertEqual(packet["unmeasured"], dict(UNMEASURED))
        for key in (
            "cost_B",
            "B_success_on_target",
            "K0_discoverability",
            "model_discovered_route",
        ):
            self.assertEqual(packet["unmeasured"][key], "unmeasured")
        self.assertIn("cost(C), never cost(B)", packet["unmeasured"]["statement"])
        self.assertIn("not an agent discovery", packet["unmeasured"]["not_a_discovery_claim"])

    def test_reference_cost_is_labelled_as_cost_c_and_never_as_cost_b(self):
        packet = self.fixture.packet()
        cost = packet["target_reference_public_api_cost"]
        self.assertEqual(cost["unit"], "public_api_calls")
        self.assertIn("This is cost(C); it is not cost(B)", cost["basis"])
        self.assertEqual(cost["cost_C"]["value"], 40)
        self.assertEqual(cost["c_success_on_target"]["reference_call_count_on_target"], 40)
        self.assertEqual(
            packet["candidate_b_routes"]["candidate_B"]["discoverability"], "unmeasured"
        )

    def test_markdown_states_the_unmeasured_block_before_the_evidence(self):
        markdown = render_packet_markdown(self.fixture.packet())
        self.assertIn("## Unmeasured (do not assume)", markdown)
        self.assertIn("- `cost_B`: unmeasured", markdown)
        self.assertIn("**Not authorized.**", markdown)
        self.assertLess(
            markdown.index("## Unmeasured (do not assume)"),
            markdown.index("## Instructions"),
        )


class ProvenanceTests(ReviewFixtureTest):
    def test_file_fact_is_repo_relative_and_hashes_the_file(self):
        tracked = PACKETS_MODULE
        fact = file_fact(tracked)
        self.assertEqual(fact["path"], "src/memory_census/packets.py")
        self.assertTrue(fact["exists"])
        self.assertEqual(fact["bytes"], tracked.stat().st_size)
        self.assertEqual(fact["sha256"], hashlib.sha256(tracked.read_bytes()).hexdigest())
        self.assertEqual(file_fact(None), {"path": None, "exists": False})
        self.assertFalse(file_fact(self.fixture.out_dir / "absent.json")["exists"])

    def test_packet_provenance_points_at_checkable_local_files(self):
        packet = self.fixture.packet()
        provenance = packet["provenance"]
        self.assertEqual(
            Path(provenance["census"]["path"]).resolve(), self.fixture.census_path.resolve()
        )
        self.assertEqual(
            provenance["census"]["sha256"],
            hashlib.sha256(self.fixture.census_path.read_bytes()).hexdigest(),
        )
        self.assertEqual(provenance["census"]["json_pointer"], "/families/2")
        self.assertEqual(provenance["census"]["census_version"], "synthetic-census-v1")
        self.assertEqual(provenance["census"]["registry_version"], "synthetic-registry-v1")
        self.assertEqual(provenance["benchmark"]["version"], "0.1.0")
        self.assertEqual(provenance["playbook"]["sha256"], PLAYBOOK_SHA)
        api_docs_db = provenance["api_docs_db"]
        self.assertEqual(
            api_docs_db["sha256"],
            hashlib.sha256(
                (self.fixture.data_root / "base_dbs" / "api_docs.db").read_bytes()
            ).hexdigest(),
        )
        for task in provenance["tasks"]:
            solution = task["files"]["solution"]
            self.assertTrue(
                solution["path"].endswith(f"{task['task_id']}/ground_truth/solution.py")
            )
            self.assertEqual(
                solution["sha256"],
                hashlib.sha256(
                    (
                        self.fixture.data_root
                        / "tasks"
                        / task["task_id"]
                        / "ground_truth"
                        / "solution.py"
                    ).read_bytes()
                ).hexdigest(),
            )
        self.assertIn("data/base_dbs/api_docs.db", provenance["sources"])

    def test_record_hash_identifies_the_exact_census_record(self):
        packet = self.fixture.packet()
        record = self.fixture.record()
        self.assertEqual(packet["provenance"]["census"]["record_sha256"], canonical_sha256(record))
        record["status_reasons"].append("changed after the packet was built")
        self.assertNotEqual(
            canonical_sha256(record), packet["provenance"]["census"]["record_sha256"]
        )

    def test_evidence_drift_is_reported_when_the_checkout_moved(self):
        # The fixture artifact records a placeholder solution hash, so every
        # packet must report drift rather than silently trusting the census.
        drift = self.fixture.packet()["provenance"]["evidence_drift"]
        self.assertEqual([entry["task_id"] for entry in drift], [SOURCE_TASK])
        self.assertEqual(drift[0]["field"], "solution_sha256")
        self.assertEqual(drift[0]["census"], "0" * 64)
        self.assertEqual(
            drift[0]["local"],
            self.fixture.entry(FAMILY)["evidence"]["tasks"][SOURCE_TASK]["solution"]["sha256"],
        )

    def test_no_drift_is_reported_when_the_recorded_hash_matches(self):
        record = self.fixture.record()
        on_disk = self.fixture.entry(FAMILY)["evidence"]["tasks"][SOURCE_TASK]["solution"]["sha256"]
        record["candidate"]["evidence_provenance"]["per_task"][SOURCE_TASK] = {
            "solution_sha256": on_disk
        }
        record["candidate"]["evidence_provenance"]["per_task"][TARGET_TASK] = {
            "solution_sha256": on_disk
        }
        packet = self.fixture.packet_for(record)
        self.assertEqual(packet["provenance"]["evidence_drift"], [])

    def test_manifest_records_the_candidate_record_location_and_hash(self):
        entry = self.fixture.entry(FAMILY)
        self.assertEqual(entry["candidate_record"]["json_pointer"], "/families/2")
        self.assertEqual(
            entry["candidate_record"]["sha256"],
            hashlib.sha256(self.fixture.census_path.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            entry["candidate_record"]["record_sha256"], canonical_sha256(self.fixture.record())
        )
        self.assertIn("unmeasured", self.fixture.manifest)
        self.assertEqual(
            self.fixture.manifest["generated_by"], "scripts/analysis/appworld_review_packets.py"
        )


class ConsumerBoundaryTests(ReviewFixtureTest):
    def test_default_consumer_is_the_research_side_review(self):
        self.assertIn(PACKET_CONSUMER, ALLOWED_CONSUMERS)
        self.assertEqual(self.fixture.packet()["consumer"], PACKET_CONSUMER)

    def test_adaptive_loop_consumers_are_rejected(self):
        for consumer in FORBIDDEN_CONSUMERS:
            with self.subTest(consumer=consumer), self.assertRaises(BoundaryViolation):
                self.fixture.packet(consumer=consumer)

    def test_consumer_validation_ignores_case_and_padding(self):
        with self.assertRaises(BoundaryViolation):
            self.fixture.packet(consumer="  Generator ")
        # Validation normalizes the name; the packet records it as given.
        self.assertEqual(
            self.fixture.packet(consumer="Research-Side-Review")["consumer"],
            "Research-Side-Review",
        )

    def test_unknown_consumers_are_rejected(self):
        with self.assertRaises(BoundaryViolation):
            self.fixture.packet(consumer="some-new-agent")


class ImportIsolationTests(unittest.TestCase):
    def test_census_sources_stay_inside_the_boundary(self):
        assert_boundary_intact()
        self.assertEqual(static_import_violations(), [])
        scanned = {path.name for path in iter_source_files()}
        self.assertIn(PACKETS_MODULE.name, scanned)

    def test_packet_builder_imports_only_offline_modules(self):
        modules = set(imported_module_names(PACKETS_MODULE))
        forbidden = {
            module
            for module in modules
            for prefix in FORBIDDEN_IMPORT_PREFIXES + FORBIDDEN_NETWORK_MODULES
            if module == prefix or module.startswith(prefix + ".")
        }
        self.assertEqual(forbidden, set())
        self.assertEqual(
            modules - ALLOWED_BUILDER_IMPORTS,
            set(),
            "packets.py must stay offline: extend ALLOWED_BUILDER_IMPORTS only if the "
            "new import cannot execute a benchmark, call a model, or open a socket",
        )

    def test_review_script_imports_the_builder_without_crossing_the_boundary(self):
        modules = list(imported_module_names(REVIEW_SCRIPT))
        self.assertIn("memory_census.packets", modules)
        for module in modules:
            for prefix in FORBIDDEN_IMPORT_PREFIXES + FORBIDDEN_NETWORK_MODULES:
                self.assertFalse(
                    module == prefix or module.startswith(prefix + "."),
                    f"{REVIEW_SCRIPT.name} imports forbidden module {module!r}",
                )


class ByteBudgetTests(ReviewFixtureTest):
    def test_a_realistic_packet_fits_without_degrading(self):
        packet = self.fixture.packet()
        size = len(packet_text(packet).encode("utf-8"))
        self.assertLessEqual(size, PacketLimits().max_packet_bytes)
        self.assertNotIn("degradations", packet)
        self.assertEqual(packet["truncations"], [])

    def test_a_packet_that_cannot_be_bounded_is_refused(self):
        with self.assertRaises(PacketBudgetError):
            self.fixture.packet_for(pathological_record(), limits=PacketLimits(max_packet_bytes=64))

    def test_every_limit_is_either_respected_or_refused(self):
        record = pathological_record()

        def attempt(limit: int) -> tuple[dict, int] | None:
            try:
                packet = self.fixture.packet_for(
                    record, limits=PacketLimits(max_packet_bytes=limit)
                )
            except PacketBudgetError:
                return None
            size = len(packet_text(packet).encode("utf-8"))
            self.assertLessEqual(size, limit)
            return packet, size

        packet, natural = attempt(PacketLimits().max_packet_bytes)
        self.assertIsNotNone(packet)
        self.assertLessEqual(natural, PacketLimits().max_packet_bytes)

        # "fits at limit L" is monotone in L, so the smallest fitting limit can
        # be found by bisection; the packet one byte below it must be refused.
        low, high = 1, natural
        while low < high:
            middle = (low + high) // 2
            if attempt(middle) is None:
                low = middle + 1
            else:
                high = middle
        floor = low
        self.assertIsNotNone(attempt(floor))
        self.assertIsNone(attempt(floor - 1))
        self.assertGreater(natural, floor + 1, "fixture is already at the degradation floor")

        squeezed, size = attempt(natural - 1)
        self.assertLessEqual(size, natural - 1)
        self.assertTrue(squeezed["degradations"])
        for dropped in squeezed["degradations"]:
            self.assertIn("section", dropped)
            self.assertIn("reason", dropped)
            self.assertIn("dropped", dropped)
        # Identity, unmeasured statements and provenance survive every drop.
        self.assertEqual(squeezed["packet_id"], FAMILY)
        self.assertEqual(squeezed["packet_version"], PACKET_VERSION)
        self.assertEqual(squeezed["consumer"], PACKET_CONSUMER)
        self.assertEqual(squeezed["unmeasured"], dict(UNMEASURED))
        self.assertEqual(squeezed["family"]["source_task_id"], SOURCE_TASK)
        self.assertTrue(squeezed["provenance"]["census"]["record_sha256"])

    def test_oversized_strings_lists_and_dicts_are_capped_and_reported(self):
        packet = self.fixture.packet_for(pathological_record())
        limits = PacketLimits()
        marker = len(TRUNCATION_MARKER)
        sections = set()
        for truncation in packet["truncations"]:
            self.assertIn("section", truncation)
            sections.add(truncation["section"])
        self.assertIn("state_setup_differences.change_evidence", sections)
        self.assertIn("candidate_b_routes.census_alternatives", sections)
        for window in packet["reference_solution_snippets"]["windows"]:
            self.assertLessEqual(len(window["code"]), limits.max_snippet_chars + marker)
            self.assertLessEqual(len(window["code"].splitlines()), limits.max_snippet_lines)
        self.assertLessEqual(
            len(packet["instructions"]["source"]["instruction"]),
            limits.max_instruction_chars + marker,
        )
        self.assertLessEqual(len(packet["public_api_documentation"]), limits.max_api_docs)
        self.assertLessEqual(
            len(packet["candidate_b_routes"]["census_alternatives"]),
            limits.max_alternatives,
        )
        self.assertLessEqual(
            len(packet["state_setup_differences"].get("change_evidence") or []),
            limits.max_change_evidence,
        )
        for doc in packet["public_api_documentation"]:
            if doc.get("documented"):
                self.assertLessEqual(len(doc["description"]), limits.max_api_description_chars)


if __name__ == "__main__":
    unittest.main()
