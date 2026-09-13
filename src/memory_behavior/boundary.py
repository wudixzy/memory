"""Research-side / adaptive-loop isolation for the behavior-first stage.

`AGENTS.md` section 10 and `docs/31` require two things of this stage:

1. research-side material (task selection features, evaluator results, strategy
   cards, candidate records) never enters Generator/Reflector/Curator context;
2. the research modules are not importable from the adaptive-loop runtime, so a
   future edit cannot wire that material into a prompt by accident.

Both are checked structurally, on source text, without importing anything:

* every research module is parsed and any import of the AppWorld runtime or the
  `memory_validation` ACE runtime is a violation;
* every module of `memory_validation` is parsed and any import of
  `memory_behavior` is a violation.

The AST helper is reused from `memory_census.boundary` rather than re-written;
only the module sets and consumer policy are stage-specific.
"""

from __future__ import annotations

from pathlib import Path

from memory_census.boundary import imported_module_names

PACKAGE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]

#: Research-side modules. This is the scanned set; `corpus` is deliberately not
#: in it, because the corpus driver is the one module allowed to touch the
#: registered ACE adapter and must not import the research modules either.
RESEARCH_MODULES = (
    "boundary.py",
    "measure.py",
    "selection.py",
    "cards.py",
    "candidates.py",
)

#: The adaptive-loop package. Nothing here may import `memory_behavior`.
ADAPTIVE_LOOP_PACKAGE = "memory_validation"

FORBIDDEN_IMPORT_PREFIXES = (
    "appworld",
    "appworld_experiments",
    "memory_validation",
    "memory_behavior.corpus",
    "torch",
    "transformers",
    "openai",
    "anthropic",
)

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

#: Where behavior-first artifacts may be consumed.
ALLOWED_CONSUMERS = (
    "research-side-analysis",
    "candidate-selection",
    "coding-agent-review",
    "corpus-orchestration",
)

#: Consumers that must never see them.
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
    """Raised when behavior-first code crosses the isolation boundary."""


def research_files() -> list[Path]:
    return [PACKAGE_ROOT / name for name in RESEARCH_MODULES]


def adaptive_loop_files() -> list[Path]:
    root = REPOSITORY_ROOT / "src" / ADAPTIVE_LOOP_PACKAGE
    return sorted(root.rglob("*.py")) if root.is_dir() else []


def _violations(paths, prefixes) -> list[dict]:
    violations: list[dict] = []
    for path in paths:
        for module in imported_module_names(path):
            for prefix in prefixes:
                if module == prefix or module.startswith(prefix + "."):
                    violations.append(
                        {"file": path.name, "module": module, "forbidden_prefix": prefix}
                    )
    return violations


def static_import_violations() -> list[dict]:
    """Research modules importing the runtime or a network module.

    The corpus driver is narrow orchestration and deliberately imports the
    registered ACE adapter. A separate check forbids it from importing the
    research selector/cards/candidates modules.
    """

    return _violations(research_files(), FORBIDDEN_IMPORT_PREFIXES + FORBIDDEN_NETWORK_MODULES)


def adaptive_loop_import_violations() -> list[dict]:
    """Adaptive-loop modules importing the research package."""

    return _violations(adaptive_loop_files(), ("memory_behavior",))


def corpus_research_import_violations() -> list[dict]:
    """The corpus driver must not import selection/cards/candidates."""

    return _violations(
        [PACKAGE_ROOT / "corpus.py"],
        ("memory_behavior.selection", "memory_behavior.cards", "memory_behavior.candidates"),
    )


def assert_boundary_intact() -> None:
    static = static_import_violations()
    if static:
        detail = ", ".join(f"{v['file']}->{v['module']}" for v in static)
        raise BoundaryViolation(f"behavior-first source imports forbidden modules: {detail}")
    adaptive = adaptive_loop_import_violations()
    if adaptive:
        detail = ", ".join(f"{v['file']}->{v['module']}" for v in adaptive)
        raise BoundaryViolation(f"adaptive-loop source imports research modules: {detail}")
    corpus = corpus_research_import_violations()
    if corpus:
        detail = ", ".join(f"{v['file']}->{v['module']}" for v in corpus)
        raise BoundaryViolation(f"corpus driver imports research modules: {detail}")


def assert_consumer_allowed(consumer: str) -> None:
    """Guard for any code path that would hand behavior artifacts to a consumer."""

    normalized = consumer.strip().lower()
    if normalized in FORBIDDEN_CONSUMERS:
        raise BoundaryViolation(
            f"behavior-first artifacts must not be exposed to adaptive-loop consumer {consumer!r}"
        )
    if normalized not in ALLOWED_CONSUMERS:
        raise BoundaryViolation(
            f"unknown behavior-first consumer {consumer!r}; allowed: {ALLOWED_CONSUMERS}"
        )


def boundary_report() -> dict:
    static = static_import_violations()
    adaptive = adaptive_loop_import_violations()
    corpus = corpus_research_import_violations()
    return {
        "status": "intact" if not (static or adaptive or corpus) else "violated",
        "scanned_research_modules": list(RESEARCH_MODULES),
        "static_forbidden_imports": static,
        "adaptive_loop_imports_of_research": adaptive,
        "corpus_imports_of_research": corpus,
        "adaptive_loop_package": f"src/{ADAPTIVE_LOOP_PACKAGE}",
        "check_scope": (
            "static parse of the research modules, the corpus driver and every "
            f"src/{ADAPTIVE_LOOP_PACKAGE} source; no interpreter imports are attributed"
        ),
        "allowed_consumers": list(ALLOWED_CONSUMERS),
        "forbidden_consumers": list(FORBIDDEN_CONSUMERS),
        "note": (
            "Selection features, evaluator output, strategy cards and candidate "
            "records are research-side analysis artifacts. The ACE Generator, "
            "Reflector and Curator receive only the task id, the exact K0 "
            "checkpoint and the transport."
        ),
    }
