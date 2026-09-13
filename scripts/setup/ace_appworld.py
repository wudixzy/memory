"""Pinned ACE setup helpers; reuse the encrypted data, never download task data again."""

import argparse
import hashlib
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UPSTREAM = ROOT / "third_party/ace-appworld"
PIN = "928e86877d34cd10eaba159606386f93a1765090"
URL = "https://github.com/ace-agent/ace-appworld"
BUNDLE = ROOT / "artifacts/appworld-feasibility-20260912/data-0.1.0.bundle"
DATA_SHA = "fd9f9608c2ec71ed0ac25c3633a738b9129a318a129e31230425b9188e508250"


def git(*args):
    return subprocess.check_output(
        [sys.executable, str(ROOT / "scripts/direct.py"), "git", "-C", str(UPSTREAM), *args],
        text=True,
    ).strip()


def verify():
    assert git("rev-parse", "HEAD") == PIN
    assert git("remote", "get-url", "origin").removesuffix(".git") == URL
    assert hashlib.sha256(BUNDLE.read_bytes()).hexdigest() == DATA_SHA


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch-source-bundles", action="store_true")
    parser.add_argument("--unpack", action="store_true")
    parser.add_argument("--record-environment", action="store_true")
    parser.add_argument("--verify-patches", action="store_true")
    args = parser.parse_args()
    verify()
    if args.record_environment:
        import importlib.metadata
        import platform

        versions = {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()}
        record = {
            "environment": "memory-ace-appworld",
            "python": platform.python_version(),
            "platform": platform.platform(),
            "upstream_commit": PIN,
            "upstream_url": URL,
            "data_sha256": DATA_SHA,
            "packages": dict(sorted(versions.items())),
            "pip_check": subprocess.run(
                [sys.executable, "-m", "pip", "check"], text=True, capture_output=True
            ).stdout.strip(),
        }
        config = ROOT / "configs/ace_appworld"
        (config / "environment-lock.json").write_text(json.dumps(record, indent=2) + "\n")
        # Editable source installations are pinned by repo SHA + patches instead of local paths.
        (config / "requirements-lock.txt").write_text(
            "\n".join(
                f"{name}=={version}"
                for name, version in sorted(versions.items())
                if name.lower() not in ("appworld", "appworld-experiments")
            )
            + "\n"
        )
        print("Environment and public dependency versions recorded")
    elif args.verify_patches:
        import tempfile

        from appworld.common.constants import PASSWORD, SALT
        from appworld.common.utils import unpack_bundle

        paths = [
            "src/appworld/common/constants.py",
            "src/appworld/common/path_store.py",
            "src/appworld/collections/models.py",
            "src/appworld/apps/model_lib.py",
            "experiments/code/ace/adaptation_agent.py",
            "experiments/code/ace/adaptation_react.py",
            "experiments/code/ace/__init__.py",
        ]
        with tempfile.TemporaryDirectory(prefix="ace-patch-check-") as tmp:
            base = Path(tmp)
            for relative in paths:
                destination = base / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(
                    subprocess.check_output(
                        [
                            sys.executable,
                            str(ROOT / "scripts/direct.py"),
                            "git",
                            "-C",
                            str(UPSTREAM),
                            "show",
                            f"{PIN}:{relative}",
                        ]
                    )
                )
            unpack_bundle(
                str(UPSTREAM / "src/appworld/.source/apps.bundle"),
                str(base / "src/appworld"),
                PASSWORD,
                SALT,
            )
            for patch_file in sorted((ROOT / "configs/ace_appworld/patches").glob("*.patch")):
                subprocess.run(
                    [
                        sys.executable,
                        str(ROOT / "scripts/direct.py"),
                        "git",
                        "apply",
                        str(patch_file),
                    ],
                    cwd=base,
                    check=True,
                )
            for relative in paths:
                assert (base / relative).read_bytes() == (UPSTREAM / relative).read_bytes(), (
                    relative
                )
        print("Original pin + declared patches reproduce all patched files exactly")
    elif args.fetch_source_bundles:
        # Git LFS is unavailable locally. Fetch only the four pinned LFS objects,
        # verifying both the committed pointer's digest and byte count.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        for relative in (
            "src/appworld/.source/apps.bundle",
            "src/appworld/.source/tests.bundle",
            "generate/.source/tasks.bundle",
            "generate/.source/data.bundle",
        ):
            pointer = git("show", f"{PIN}:{relative}")
            digest = pointer.split("oid sha256:")[1].splitlines()[0]
            size = int(pointer.split("size ")[1])
            destination = UPSTREAM / relative
            if hashlib.sha256(destination.read_bytes()).hexdigest() == digest:
                continue
            assert destination.read_text().strip() == pointer
            with opener.open(
                f"https://media.githubusercontent.com/media/ace-agent/ace-appworld/{PIN}/{relative}",
                timeout=60,
            ) as response:
                data = response.read()
            assert len(data) == size and hashlib.sha256(data).hexdigest() == digest
            destination.write_bytes(data)
            print(json.dumps({"source": relative, "sha256": digest, "bytes": size}))
    elif args.unpack:
        # Patched upstream has no implicit dotenv loading. Official unpacker.
        import os

        from appworld.common.constants import PASSWORD, SALT
        from appworld.common.utils import unpack_bundle
        from appworld.install import install_repo

        os.chdir(UPSTREAM)
        install_repo()
        if (UPSTREAM / "data").exists():
            raise FileExistsError("Data exists; refusing to replace it")
        unpack_bundle(str(BUNDLE), str(UPSTREAM), PASSWORD, SALT)
        print("Official source and existing data bundle unpacked")
    else:
        print(
            json.dumps(
                {
                    "mode": "plan",
                    "pin": PIN,
                    "data_sha256": DATA_SHA,
                    "environment": "memory-ace-appworld",
                    "model_calls": 0,
                }
            )
        )


if __name__ == "__main__":
    main()
