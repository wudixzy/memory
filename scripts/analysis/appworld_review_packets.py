"""Write the reserve-family manifest and bounded review packets. Offline only.

Reads the ignored Stage-A census artifact plus the local benchmark checkout and
writes, per reserve family, one self-contained research-side packet under
`artifacts/appworld_review_packets/` (gitignored). No model call, no network
access, no benchmark execution. See `docs/29_parallel_candidate_review_plan.md`.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from memory_census.api_surface import ApiSurface  # noqa: E402
from memory_census.boundary import assert_boundary_intact  # noqa: E402
from memory_census.census import DEFAULT_API_DOCS_DB, DEFAULT_DATA_ROOT  # noqa: E402
from memory_census.packets import (  # noqa: E402
    PacketLimits,
    build_packet,
    build_reserve_manifest,
    packet_text,
    render_packet_markdown,
    reserve_entries,
)

DEFAULT_CENSUS = ROOT / "artifacts/appworld_family_census/census.json"
DEFAULT_OUT_DIR = ROOT / "artifacts/appworld_review_packets"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--census", default=str(DEFAULT_CENSUS))
    parser.add_argument("--data-root", default=str(DEFAULT_DATA_ROOT))
    parser.add_argument("--api-docs-db", default=str(DEFAULT_API_DOCS_DB))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument(
        "--family",
        action="append",
        default=None,
        help="limit packet generation to this family id (repeatable); default is every reserve",
    )
    parser.add_argument(
        "--max-packet-bytes",
        type=int,
        default=PacketLimits().max_packet_bytes,
        help="hard byte ceiling for one serialized packet",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="build in memory and report, without writing any file",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    assert_boundary_intact()

    census_path = Path(args.census)
    if not census_path.is_file():
        print(f"no census artifact at {census_path}; run appworld_family_census.py first")
        return 2
    artifact = json.loads(census_path.read_text(encoding="utf-8"))
    data_root = Path(args.data_root)
    out_dir = Path(args.out_dir)
    limits = PacketLimits(max_packet_bytes=args.max_packet_bytes)

    manifest = build_reserve_manifest(
        artifact,
        census_path=census_path,
        data_root=data_root,
        packet_dir=out_dir,
        limits=limits,
    )
    wanted = set(args.family or [entry["family_id"] for entry in manifest["families"]])
    lineage = {
        entry["family"]: entry.get("lineage_warnings", [])
        for entry in artifact.get("family_lineage", [])
    }

    census_ref = {
        "path": manifest["census"]["path"],
        "sha256": manifest["census"]["sha256"],
        "json_pointer": None,
        "census_version": manifest["census"]["census_version"],
        "registry_version": manifest["census"]["registry_version"],
        "benchmark_version": artifact.get("provenance", {})
        .get("benchmark", {})
        .get("benchmark_version"),
        "playbook": artifact.get("provenance", {}).get("playbook", {}),
    }

    written, sizes = [], {}
    surface = ApiSurface(args.api_docs_db)
    try:
        for index, record in reserve_entries(artifact):
            family = record["family"]
            if family not in wanted:
                continue
            packet = build_packet(
                record,
                data_root=data_root,
                limits=limits,
                api_surface=surface,
                census_ref={**census_ref, "json_pointer": f"/families/{index}"},
                lineage_warnings=lineage.get(family, []),
            )
            text = packet_text(packet)
            sizes[family] = len(text.encode("utf-8"))
            if not args.check:
                directory = out_dir / family
                directory.mkdir(parents=True, exist_ok=True)
                (directory / "packet.json").write_text(text, encoding="utf-8")
                (directory / "packet.md").write_text(
                    render_packet_markdown(packet), encoding="utf-8"
                )
            written.append(family)
            drift = packet["provenance"]["evidence_drift"]
            if drift:
                print(f"warning: evidence drift for {family}: {drift}")
    finally:
        surface.close()

    for entry in manifest["families"]:
        path = out_dir / entry["family_id"] / "packet.json"
        if entry["family_id"] in sizes and path.is_file():
            entry["packet"]["sha256"] = _sha256(path)
            entry["packet"]["bytes"] = sizes[entry["family_id"]]
    if not args.check:
        manifest["counts"]["packets_written"] = len(written)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "reserve_manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    print(
        f"{'checked' if args.check else 'wrote'} {len(written)} packet(s) for "
        f"{manifest['counts']['reserve_families']} reserve families; "
        f"max packet {max(sizes.values()) if sizes else 0} bytes"
    )
    if not args.check:
        print(f"manifest: {out_dir / 'reserve_manifest.json'}")
    return 0


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
