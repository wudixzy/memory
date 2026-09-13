"""Research-side / adaptive-loop isolation boundary for the census package.

`AGENTS.md` section 10 and `docs/26` require evaluator-only or hidden
ground-truth information to stay out of the actor/memory-updater loop. The
census is allowed to read that information for *candidate selection only*, so
the boundary has two halves:

1. **Import firewall.** The census must not import the AppWorld runtime or the
   `memory_validation` ACE runtime. Any accidental import would make it possible
   for census data to travel into an adaptive loop through a shared module.
2. **Provenance marking.** Every evidence artifact carries an explicit usage
   scope so a reviewer can confirm it was never routed into a prompt.

The firewall is checked structurally — every census source is parsed and any
forbidden import is a violation — and the census run additionally diffs
`sys.modules` around itself, so a runtime import introduced at call time is
recorded in provenance rather than assumed absent.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Iterable

#: Modules the census may never import. Prefix match.
FORBIDDEN_IMPORT_PREFIXES = (
    "appworld",
    "appworld_experiments",
    "memory_validation",
    "torch",
    "transformers",
    "openai",
    "anthropic",
)

#: Network-capable modules the census may never import.
FORBIDDEN_NETWORK_MODULES = (
    "socket",
    "requests",
    "httpx",
    "urllib.request",
    "urllib.error",
    "http.client",
    "aiohttp",
    "ftplib",
    "telnetlib",
    "smtplib",
)

#: Where census artifacts may be consumed. Anything outside this is a violation.
ALLOWED_CONSUMERS = ("research-side-review", "candidate-selection")

#: Consumers that must never see census artifacts.
FORBIDDEN_CONSUMERS = (
    "generator",
    "reflector",
    "curator",
    "actor",
    "memory-updater",
    "inducer",
    "builder",
)


class BoundaryViolation(RuntimeError):
    """Raised when the census crosses the research-side isolation boundary."""


def package_root() -> Path:
    return Path(__file__).resolve().parent


def iter_source_files(root: Path | None = None):
    base = root or package_root()
    yield from sorted(base.rglob("*.py"))


def imported_module_names(path: Path) -> list[str]:
    """Return every module name imported by one Python source file."""

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.append(node.module)
            # `from . import x` / `from .mod import x` are intra-package.
            elif node.level:
                continue
    return names


def static_import_violations(root: Path | None = None) -> list[dict]:
    """Scan census sources for forbidden imports without importing anything."""

    violations: list[dict] = []
    for path in iter_source_files(root):
        for module in imported_module_names(path):
            for prefix in FORBIDDEN_IMPORT_PREFIXES + FORBIDDEN_NETWORK_MODULES:
                if module == prefix or module.startswith(prefix + "."):
                    violations.append(
                        {
                            "file": path.name,
                            "module": module,
                            "forbidden_prefix": prefix,
                        }
                    )
    return violations


def loaded_module_violations() -> list[str]:
    """Return forbidden modules currently loaded in this interpreter."""

    loaded = []
    for name in list(sys.modules):
        for prefix in FORBIDDEN_IMPORT_PREFIXES:
            if name == prefix or name.startswith(prefix + "."):
                loaded.append(name)
    return sorted(loaded)


def census_induced_imports(baseline: Iterable[str]) -> list[str]:
    """Forbidden modules loaded now that were not loaded at `baseline`."""

    return sorted(set(loaded_module_violations()) - set(baseline))


def module_snapshot() -> tuple[str, ...]:
    """Module names to diff against, for callers that want the delta form."""

    return tuple(sorted(sys.modules))


def assert_boundary_intact(root: Path | None = None) -> None:
    """Raise `BoundaryViolation` if census *code* crosses the isolation boundary.

    The check is structural and deterministic: every census source is parsed and
    any import of the AppWorld runtime, the `memory_validation` ACE runtime, or
    a network module is a violation.

    It is deliberately **not** a claim about `sys.modules`. In a shared
    interpreter — the project test suite imports the ACE runtime in unrelated
    modules — a forbidden module can already be loaded before the census starts,
    or be loaded after it by a different test. Whether the census pulled it in
    is measured where it can be measured honestly: `run_census` diffs
    `sys.modules` around its own execution and records the delta in provenance.
    """

    static = static_import_violations(root)
    if static:
        detail = ", ".join(f"{v['file']}->{v['module']}" for v in static)
        raise BoundaryViolation(f"census source imports forbidden modules: {detail}")


def boundary_report(root: Path | None = None, run_delta: list[str] | None = None) -> dict:
    """Machine-readable boundary status for the census provenance block."""

    static = static_import_violations(root)
    return {
        "status": "intact" if not static and not run_delta else "violated",
        "scanned_files": [p.name for p in iter_source_files(root)],
        "static_forbidden_imports": static,
        "forbidden_imports_during_census_run": list(run_delta or []),
        "forbidden_modules_present_in_host": loaded_module_violations(),
        "check_scope": (
            "static parse of every census source plus a sys.modules delta measured "
            "around the census run itself. Modules already present in the host process "
            "are reported but not attributed to the census, because a shared interpreter "
            "can load them independently of this package."
        ),
        "allowed_consumers": list(ALLOWED_CONSUMERS),
        "forbidden_consumers": list(FORBIDDEN_CONSUMERS),
        "note": (
            "Census artifacts are research-side candidate-selection evidence only. "
            "They must never be injected into Generator/Reflector/Curator prompts or "
            "any actor/memory-updater context."
        ),
    }


def assert_consumer_allowed(consumer: str) -> None:
    """Guard for any future code path that would hand census data to a consumer."""

    normalized = consumer.strip().lower()
    if normalized in FORBIDDEN_CONSUMERS:
        raise BoundaryViolation(
            f"census artifacts must not be exposed to adaptive-loop consumer {consumer!r}"
        )
    if normalized not in ALLOWED_CONSUMERS:
        raise BoundaryViolation(
            f"unknown census consumer {consumer!r}; allowed consumers are {ALLOWED_CONSUMERS}"
        )
