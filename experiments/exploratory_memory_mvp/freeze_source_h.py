"""Freeze one verified source-H entry without making a model call.

The command consumes already-saved source/B/C artifacts.  It never creates a
transport or model client; C must already have produced a validated CREATE
result in the supplied parsed artifact.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .common import read_json, write_json
from .h_manifest import (
    DEFAULT_H_MANIFEST_PATH,
    append_frozen_h_entry,
    freeze_source_h_entry,
    load_h_manifest,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--h-id", required=True)
    parser.add_argument("--source-task-id", required=True)
    parser.add_argument("--source-history", type=Path, required=True)
    parser.add_argument("--b-artifact", type=Path, required=True)
    parser.add_argument("--c-artifact", type=Path, required=True)
    parser.add_argument("--offline-config", type=Path, required=True)
    parser.add_argument("--creation-version", required=True)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_H_MANIFEST_PATH)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    entry = freeze_source_h_entry(
        h_id=args.h_id,
        source_task_id=args.source_task_id,
        source_history_path=args.source_history,
        b_artifact_path=args.b_artifact,
        c_artifact_path=args.c_artifact,
        offline_model_config=read_json(args.offline_config),
        creation_version=args.creation_version,
    )
    manifest = append_frozen_h_entry(load_h_manifest(args.manifest), entry)
    output = args.output or args.manifest
    write_json(output, manifest)
    print(f"h_id={entry['h_id']}")
    print(f"manifest_sha256={manifest['manifest_sha256']}")


if __name__ == "__main__":
    main()
