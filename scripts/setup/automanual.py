"""Plan (default), fetch pinned official source, or verify it. Never runs an agent."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PIN = ROOT / "configs/automanual_alfworld/upstream.json"


def git(directory: Path, *args: str) -> str:
    env = {k: v for k, v in os.environ.items() if not k.lower().endswith("_proxy")}
    env.update(NO_PROXY="*", no_proxy="*")
    # Override URL-specific and remote-specific Git proxies too, without printing
    # their names/values or changing any config file. This query is local-only.
    configured = subprocess.run(
        [
            "git",
            "-C",
            str(directory),
            "config",
            "--name-only",
            "--get-regexp",
            "[Pp][Rr][Oo][Xx][Yy]$",
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    overrides = [part for name in configured.stdout.splitlines() for part in ("-c", name + "=")]
    result = subprocess.run(
        ["git", *overrides, "-c", "http.proxy=", "-C", str(directory), *args],
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode:
        raise RuntimeError("Upstream Git operation failed (details withheld)")
    return result.stdout.strip()


def verify(directory: Path, pin: dict, declared_patch: Path | None = None) -> dict:
    if git(directory, "remote", "get-url", "origin") != pin["repository_url"]:
        raise RuntimeError("Existing upstream origin differs; no changes made")
    if git(directory, "rev-parse", "HEAD") != pin["commit"]:
        raise RuntimeError("Existing upstream commit differs; no changes made")
    tree = git(directory, "rev-parse", "HEAD:alfworld")
    if tree != pin["benchmark"]["execution_tree"]:
        raise RuntimeError("Bundled ALFWorld tree differs")
    patches = []
    if declared_patch is None:
        if git(directory, "status", "--porcelain", "--untracked-files=all"):
            raise RuntimeError("Upstream has local changes; no changes made")
    else:
        if git(directory, "diff", "--cached", "--binary"):
            raise RuntimeError("Unexpected staged upstream changes")
        if git(directory, "ls-files", "--others", "--exclude-standard"):
            raise RuntimeError("Undeclared untracked upstream files")
        declared = (
            list(declared_patch) if isinstance(declared_patch, (list, tuple)) else [declared_patch]
        )
        actual = git(directory, "diff", "--binary", "HEAD")

        # Disjoint patch blocks may be grouped by purpose rather than Git path order.
        # Compare every exact block, never ignore source hunks or disable cleanliness.
        def blocks(text):
            return sorted(
                part.strip() for part in re.split(r"(?m)(?=^diff --git )", text) if part.strip()
            )

        if blocks(actual) != blocks("\n".join(p.read_text().strip() for p in declared)):
            raise RuntimeError("Working tree does not match declared patch")
        patches = [
            {
                "category": "embedding_substitution"
                if p.name.startswith("002")
                else "execution_containment_and_observation"
                if p.name.startswith("003")
                else "dependency_compatibility",
                "file": p.name,
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            }
            for p in declared
        ]
    requirements = directory / pin["environment"]["requirements_path"]
    return {
        "commit": pin["commit"],
        "repository_url": pin["repository_url"],
        "requirements_sha256": hashlib.sha256(requirements.read_bytes()).hexdigest(),
        "environment_lock": pin["environment"]["resolved_lock"],
        "bundled_tree": tree,
        "verification": "declared_patch" if declared_patch else "pristine_pin",
        "local_patches": patches,
        "phase_0": "not_run",
    }


def fetch(directory: Path, pin: dict) -> dict:
    if not re.fullmatch(r"[0-9a-f]{40}", pin["commit"]):
        raise ValueError("A full commit SHA is required")
    if directory.exists():
        return verify(directory, pin)
    directory.mkdir(parents=True)
    git(directory, "init")
    git(directory, "remote", "add", "origin", pin["repository_url"])
    # Fetch exact SHA, never a floating branch. Failures leave the checkout in
    # place for inspection; we never reset or delete a preexisting directory.
    git(directory, "fetch", "--depth=1", "origin", pin["commit"])
    git(directory, "checkout", "--detach", pin["commit"])
    return verify(directory, pin)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--fetch", action="store_true")
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--check-patched", action="store_true")
    modes.add_argument("--apply-patches", action="store_true")
    modes.add_argument("--verify-replay", action="store_true")
    args = parser.parse_args()
    pin = json.loads(PIN.read_text())
    directory = ROOT / "third_party/automanual"
    declared_patch = sorted((ROOT / "configs/automanual_alfworld/patches").glob("*.patch"))
    if args.fetch:
        result = fetch(directory, pin)
    elif args.check:
        result = verify(directory, pin)
    elif args.check_patched:
        result = verify(directory, pin, declared_patch)
    elif args.apply_patches:
        verify(directory, pin)
        for p in declared_patch:
            git(directory, "apply", "--check", str(p))
            git(directory, "apply", str(p))
        result = verify(directory, pin, declared_patch)
    elif args.verify_replay:
        # Fresh local-only clone: never reset/clean or reverse the user's checkout.
        verify(directory, pin, declared_patch)
        with tempfile.TemporaryDirectory(prefix="memory-pin-replay-") as temporary:
            target = Path(temporary) / "source"
            git(directory, "clone", "--shared", "--no-checkout", str(directory), str(target))
            git(target, "remote", "set-url", "origin", pin["repository_url"])
            git(target, "checkout", "--detach", pin["commit"])
            verify(target, pin)
            for p in declared_patch:
                git(target, "apply", "--check", str(p))
                git(target, "apply", str(p))
            result = verify(target, pin, declared_patch)
            result["pristine_to_patched_replay"] = "verified_in_temporary_local_clone"
    else:
        result = {
            "mode": "plan_only",
            "network": False,
            "pin": pin,
            "target": str(directory),
            "installation": (
                "See docs/06_embedding_wiring.md; text environment and offline Skill_Bank "
                "validated, no real API validation"
            ),
        }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, ValueError):
        raise SystemExit("Setup failed; checkout preserved. Inspect origin, SHA and local status.")
