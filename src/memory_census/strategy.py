"""Strategy-structure evidence, derived offline and checked against the API docs.

What the offline data can and cannot show
-----------------------------------------

`ground_truth/solution.py` is the reference implementation for a task; 147 of
the 732 released tasks have one. Every released sibling of a family comes from
the same generator and therefore uses the *same reference procedure* — the
differences between siblings live in `public_data`/`private_data`, i.e. in the
data. So the census can establish:

* the reference procedure's public-API call structure (loop-driven probes,
  pagination, soft probes);
* which of those probes the **documented** API surface makes unavoidable, by
  looking for a cheaper API that returns the same field without a per-entity
  call (`memory_census.api_surface`);
* how many of the reference target's call sites are avoidable *if* such an
  alternative exists.

It cannot establish that any agent would find or choose an alternative. That
needs a K_0 rollout, which this stage does not run, so alternatives stay tagged
``reference_only`` and the discoverability criterion is capped offline.

Two structural shortcuts are detectable without speculation:

``duplicate-entity-probe``
    the reference procedure calls the same entity-keyed API more than once
    (the same entity is resolved twice). A cache that keys on
    ``(api, entity_id)`` removes every repeat; the saving is exact — the
    multiplicity is visible in the source, not inferred from data.
``bulk-filter-route``
    the reference procedure probes one entity per iteration, and the public
    docs contain a paginated list API that already returns the needed field.
"""

from __future__ import annotations

import ast
import re
from collections import Counter
from dataclasses import dataclass

from memory_census.api_surface import ApiSurface

#: Helpers that turn one call site into an unbounded number of public calls.
PAGINATION_HELPERS = ("find_all_from_pages", "yield_page")
PAGINATION_MAX_PAGES = 10  # src/appworld/common/utils.py:find_all_from_pages

#: Reference solutions wrap calls across lines and pass API functions as
#: first-class values to pagination helpers (`find_all_from_pages(\n
#: apis.spotify.show_song_library,\n ...)`), so the opening parenthesis is
#: frequently absent. Match the attribute itself and confirm the call with the
#: AST rather than by requiring an adjacent `(`.
_APIS_CALL_RE = re.compile(r"\bapis\.([a-z_][a-z_0-9]*)\.([a-z_0-9]+)")
_ENTITY_ARG_RE = re.compile(r"(\w*_id)\s*=\s*([^,)\n]+)")
_ATTR_USE_RE = re.compile(
    r"\b(?:song|song_details|details|item|record|entry|row|profile|result)\.([a-z_]+)"
)

#: ``public_data``/``private_data`` are evaluator-side ground-truth inputs.
#: They are legitimate research-side reading material and forbidden in any
#: adaptive loop, so every mention is recorded rather than stripped.
GROUND_TRUTH_INPUT_TOKENS = ("public_data", "private_data", "ground_truth")


@dataclass(frozen=True)
class ApiCallSite:
    app: str
    api: str
    line: int
    inside_loop: bool
    via_pagination_helper: bool
    raise_on_failure_false: bool
    entity_key: str | None
    entity_expression: str | None
    #: Fields the solution reads off this call's result. A bulk route only
    #: replaces a per-entity probe if it can *express the question* the probe
    #: answers, which is judged against these fields.
    read_fields: tuple[str, ...] = ()
    #: `public_data` equalities guarding this call site. Sites guarded on the
    #: same key with different values can never both execute.
    guards: tuple[tuple[str, str], ...] = ()

    @property
    def name(self) -> str:
        return f"{self.app}.{self.api}"

    @property
    def is_entity_probe(self) -> bool:
        return self.entity_key is not None

    @property
    def resolution_key(self) -> str | None:
        """What this call resolves: an API applied to one entity expression.

        Keying on the API name alone conflates genuinely different entities
        (`show_profile(email=...)` inside a contact loop is not a repeat just
        because the same API appears twice), so the entity expression is part
        of the identity.
        """

        if self.entity_expression is None:
            return None
        return f"{self.name}({self.entity_key}={self.entity_expression})"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "line": self.line,
            "inside_loop": self.inside_loop,
            "via_pagination_helper": self.via_pagination_helper,
            "raise_on_failure_false": self.raise_on_failure_false,
            "entity_key": self.entity_key,
            "entity_expression": self.entity_expression,
            "resolution_key": self.resolution_key,
            "read_fields": list(self.read_fields),
            "guards": [list(pair) for pair in self.guards],
        }


@dataclass(frozen=True)
class Alternative:
    """A reference-supported cheaper route to the same target evidence."""

    alternative_id: str
    kind: str  # "duplicate-entity-probe" | "bulk-filter-route"
    summary: str
    replaces: tuple[str, ...]
    saving_basis: str
    saving_call_sites: int
    verdict: str  # "supported" | "weakly_supported" | "refuted" | "unknown"
    verification: dict
    evidence_class: str = "reference_only"
    #: True when the counted call sites are guarded by mutually exclusive
    #: `public_data` branches, so no single execution can realize them. The
    #: figure is then an upper bound kept for review, never a credited saving.
    saving_is_upper_bound: bool = False

    def to_dict(self) -> dict:
        return {
            "alternative_id": self.alternative_id,
            "kind": self.kind,
            "summary": self.summary,
            "replaces": list(self.replaces),
            "saving_basis": self.saving_basis,
            "saving_call_sites": self.saving_call_sites,
            "saving_is_upper_bound": self.saving_is_upper_bound,
            "verdict": self.verdict,
            "verification": self.verification,
            "evidence_class": self.evidence_class,
        }


@dataclass(frozen=True)
class SolutionAnalysis:
    task_id: str
    available: bool
    call_sites: tuple[ApiCallSite, ...]
    distinct_apis: tuple[str, ...]
    static_call_sites: int
    loop_driven_call_sites: int
    paginated_call_sites: int
    ground_truth_inputs_used: tuple[str, ...]
    attribute_uses: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "available": self.available,
            "distinct_apis": list(self.distinct_apis),
            "static_call_sites": self.static_call_sites,
            "loop_driven_call_sites": self.loop_driven_call_sites,
            "paginated_call_sites": self.paginated_call_sites,
            "ground_truth_inputs_used": list(self.ground_truth_inputs_used),
            "attribute_uses": list(self.attribute_uses),
            "call_sites": [c.to_dict() for c in self.call_sites],
        }


def _enclosing_loop_lines(tree: ast.AST) -> set[int]:
    lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
            for child in ast.walk(node):
                if isinstance(child, ast.stmt) and child is not node:
                    lines.add(child.lineno)
    return lines


def _pagination_wrapped_references(tree: ast.AST) -> list[ast.Attribute]:
    """`apis.x.y` attribute nodes handed to a pagination helper as its API argument.

    `find_all_from_pages(apis.spotify.show_song_library, ...)` mentions the API
    without an adjacent `(`, but the helper *invokes* it once per page, so the
    reference is a genuine call site. The helper's API argument is its first
    positional argument, so only that reference counts — a nested
    `find_all_from_pages(...)` around a real call is not page-driven.
    """

    wrapped: list[ast.Attribute] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
        if name not in PAGINATION_HELPERS or not node.args:
            continue
        first = node.args[0]
        if (
            isinstance(first, ast.Attribute)
            and isinstance(first.value, ast.Attribute)
            and isinstance(first.value.value, ast.Name)
            and first.value.value.id == "apis"
        ):
            wrapped.append(first)
    return wrapped


def _api_call_nodes(tree: ast.AST) -> list[ast.Call]:
    """`apis.<app>.<api>(...)` call nodes with an explicit call, in source order.

    Going through the AST matters: a parenthesised expression after an
    attribute (`(apis.x.y or default)()`) is not a public-API call. Forms that
    *do* call the API without an adjacent `(` — the pagination-helper argument —
    are recovered separately by `_pagination_wrapped_references`.
    """

    nodes: list[ast.Call] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute):
            continue
        inner = func.value
        if (
            isinstance(inner, ast.Attribute)
            and isinstance(inner.value, ast.Name)
            and inner.value.id == "apis"
        ):
            nodes.append(node)
    nodes.sort(key=lambda node: (node.lineno, node.col_offset))
    return nodes


def public_data_attribute(node: ast.AST) -> str | None:
    """Key of a `public_data.<key>` / `public_data['<key>']` reference."""

    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        if node.value.id == "public_data":
            return node.attr
    if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
        if node.value.id == "public_data":
            slice_node = node.slice
            if isinstance(slice_node, ast.Constant) and isinstance(slice_node.value, str):
                return slice_node.value
    return None


def _equality_guards(test: ast.AST) -> tuple[tuple[str, str], ...]:
    """`public_data.<key> == <literal>` equalities inside one branch test."""

    guards: list[tuple[str, str]] = []
    for node in ast.walk(test):
        if not isinstance(node, ast.Compare) or len(node.ops) != 1:
            continue
        if not isinstance(node.ops[0], ast.Eq) or len(node.comparators) != 1:
            continue
        key = public_data_attribute(node.left)
        comparator = node.comparators[0]
        if key is None or not isinstance(comparator, ast.Constant):
            continue
        guards.append((key, str(comparator.value)))
    return tuple(guards)


def _guards_by_line(tree: ast.AST) -> dict[int, tuple[tuple[str, str], ...]]:
    """Active `public_data` equality guards at every statement line.

    The released solutions branch on `public_data` and repeat the same call in
    each branch:

        if public_data.before_after == "before":
            for song in songs: apis.spotify.show_song(song_id=song.song_id)
        if public_data.before_after == "after":
            for song in songs: apis.spotify.show_song(song_id=song.song_id)

    A `public_data` key holds exactly one value per task, so those two call
    sites can never both execute. Counting them as a repeated resolution would
    invent a saving that no execution can realize, which is why the guard set is
    tracked here and used by `_max_co_occurring`.
    """

    guards: dict[int, tuple[tuple[str, str], ...]] = {}

    def visit_block(statements: list[ast.stmt], active: tuple[tuple[str, str], ...]) -> None:
        for statement in statements:
            guards[statement.lineno] = active
            visit(statement, active)

    def visit(node: ast.AST, active: tuple[tuple[str, str], ...]) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.If):
                visit_block(child.body, active + _equality_guards(child.test))
                visit_block(child.orelse, active)
            elif isinstance(child, (ast.For, ast.AsyncFor, ast.While)):
                visit_block(child.body, active)
                visit_block(child.orelse, active)
            else:
                if isinstance(child, ast.stmt):
                    guards.setdefault(child.lineno, active)
                visit(child, active)

    visit_block(getattr(tree, "body", []), ())
    return guards


def _compatible(left: tuple[tuple[str, str], ...], right: tuple[tuple[str, str], ...]) -> bool:
    """Can two guarded call sites execute in the same task?"""

    left_map = dict(left)
    for key, value in right:
        if key in left_map and left_map[key] != value:
            return False
    return True


def _max_co_occurring(sites: list[ApiCallSite]) -> int:
    """Largest number of mutually compatible call sites that can run together.

    A loop-driven call site executes an unbounded number of times at runtime, so
    this is a count of *call sites*, not of calls; the runtime multiplicity is
    data-dependent and is not recovered offline.
    """

    if not sites:
        return 0
    if len(sites) > 12:  # pragma: no cover - released solutions stay far below this
        return len(sites)
    best = 0
    for mask in range(1, 1 << len(sites)):
        chosen = [sites[index] for index in range(len(sites)) if mask & (1 << index)]
        if len(chosen) <= best:
            continue
        if all(
            _compatible(left.guards, right.guards)
            for i, left in enumerate(chosen)
            for right in chosen[i + 1 :]
        ):
            best = len(chosen)
    return best


def _read_fields_by_call_line(tree: ast.AST) -> dict[int, tuple[str, ...]]:
    """Fields read off each `x = apis.app.api(...)` result, keyed by call line.

    The released solutions name the result and then read fields from it
    (`detail = apis.spotify.show_song(...)` ... `detail.song_id`), so the fields
    a probe actually supplies are recoverable without dataflow analysis beyond
    one assignment hop.
    """

    assigned: dict[str, list[int]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        value = node.value
        if not isinstance(target, ast.Name) or not isinstance(value, ast.Call):
            continue
        func = value.func
        if (
            isinstance(func, ast.Attribute)
            and isinstance(func.value, ast.Attribute)
            and isinstance(func.value.value, ast.Name)
            and func.value.value.id == "apis"
        ):
            assigned.setdefault(target.id, []).append(value.lineno)
    if not assigned:
        return {}
    fields: dict[str, set[str]] = {name: set() for name in assigned}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute) or not isinstance(node.value, ast.Name):
            continue
        if node.value.id in fields:
            fields[node.value.id].add(node.attr)
    by_line: dict[int, tuple[str, ...]] = {}
    for name, lines in assigned.items():
        for line in lines:
            by_line[line] = tuple(sorted(fields[name]))
    return by_line


def _entity_keyword(node: ast.Call) -> tuple[str, str] | None:
    """First `<name>_id=<expr>` keyword argument, as (key, expression text)."""

    for keyword in node.keywords:
        if keyword.arg and keyword.arg.endswith("_id"):
            try:
                expression = " ".join(ast.unparse(keyword.value).split())
            except Exception:  # pragma: no cover - defensive for exotic nodes
                return None
            return keyword.arg, expression
    return None


def _is_soft_call(node: ast.Call) -> bool:
    """True when the call passes `raise_on_failure=False`, or `False` positionally."""

    for keyword in node.keywords:
        if keyword.arg == "raise_on_failure":
            return isinstance(keyword.value, ast.Constant) and keyword.value.value is False
    return False


def analyze_solution(task_id: str, source: str | None) -> SolutionAnalysis:
    if not source:
        return SolutionAnalysis(
            task_id=task_id,
            available=False,
            call_sites=(),
            distinct_apis=(),
            static_call_sites=0,
            loop_driven_call_sites=0,
            paginated_call_sites=0,
            ground_truth_inputs_used=(),
            attribute_uses=(),
        )
    try:
        tree = ast.parse(source)
        loop_lines = _enclosing_loop_lines(tree)
        wrapped = _pagination_wrapped_references(tree)
        read_fields = _read_fields_by_call_line(tree)
        guards = _guards_by_line(tree)
    except SyntaxError:
        loop_lines, wrapped, read_fields, guards = set(), [], {}, {}

    sites: list[ApiCallSite] = []
    for node in _api_call_nodes(tree):
        app, api = node.func.value.attr, node.func.attr
        if app == "supervisor" and api == "complete_task":
            continue
        keyword = _entity_keyword(node)
        sites.append(
            ApiCallSite(
                app=app,
                api=api,
                line=node.lineno,
                inside_loop=node.lineno in loop_lines,
                via_pagination_helper=False,
                raise_on_failure_false=_is_soft_call(node),
                entity_key=keyword[0] if keyword else None,
                entity_expression=keyword[1] if keyword else None,
                read_fields=read_fields.get(node.lineno, ()),
                guards=guards.get(node.lineno, ()),
            )
        )
    for reference in wrapped:
        app, api = reference.value.attr, reference.attr
        if app == "supervisor" and api == "complete_task":
            continue
        sites.append(
            ApiCallSite(
                app=app,
                api=api,
                line=reference.lineno,
                inside_loop=reference.lineno in loop_lines,
                via_pagination_helper=True,
                raise_on_failure_false=False,
                entity_key=None,
                entity_expression=None,
            )
        )
    sites.sort(key=lambda site: (site.line, site.name, site.via_pagination_helper))
    return SolutionAnalysis(
        task_id=task_id,
        available=True,
        call_sites=tuple(sites),
        distinct_apis=tuple(sorted({s.name for s in sites})),
        static_call_sites=len(sites),
        loop_driven_call_sites=sum(1 for s in sites if s.inside_loop),
        paginated_call_sites=sum(1 for s in sites if s.via_pagination_helper),
        ground_truth_inputs_used=tuple(
            token for token in GROUND_TRUTH_INPUT_TOKENS if token in source
        ),
        attribute_uses=tuple(sorted(set(_ATTR_USE_RE.findall(source)))),
    )


def procedure_signature(analysis: SolutionAnalysis) -> str:
    """Structural signature of a reference procedure.

    Siblings sharing a signature run the *same* procedure over different data,
    which localizes a within-family cost gap to the data rather than to a
    strategy decision.
    """

    if not analysis.available:
        return "unavailable"
    parts = []
    for site in analysis.call_sites:
        flags = []
        if site.inside_loop:
            flags.append("loop")
        if site.via_pagination_helper:
            flags.append("page")
        if site.raise_on_failure_false:
            flags.append("soft")
        parts.append(f"{site.name}[{'+'.join(flags)}]" if flags else site.name)
    return " -> ".join(parts)


def procedure_diff(sources: dict[str, str | None], target: str) -> dict:
    signatures = {
        task_id: procedure_signature(analyze_solution(task_id, source))
        for task_id, source in sources.items()
    }
    target_signature = signatures.get(target)
    differing = sorted(t for t, s in signatures.items() if s != target_signature)
    return {
        "signatures": signatures,
        "target": target,
        "siblings_with_different_procedure": differing,
        "reference_procedure_identical_across_family": not differing,
    }


def _duplicate_probe_alternative(
    analysis: SolutionAnalysis, entity_apis: dict[str, dict]
) -> Alternative | None:
    """Same entity-keyed API resolved more than once by one reference procedure.

    The reference solutions branch on `public_data`, so several mutually
    exclusive loops can each resolve the same entity set. Exactly one branch
    runs per task, which means the counted call sites are an **upper bound**:
    the runtime saving is at most (distinct resolving sites - 1) calls per
    entity. The report carries that bound rather than the raw count.
    """

    # Only loop-driven probes resolve a *collection* of entities one call at a
    # time; a single non-looped lookup cannot repeat, and a probe whose entity
    # argument is a literal (not the loop variable) is not the same entity each
    # iteration.
    by_key: dict[str, list[ApiCallSite]] = {}
    for site in analysis.call_sites:
        if site.is_entity_probe and site.inside_loop and site.resolution_key:
            by_key.setdefault(site.resolution_key, []).append(site)
    # Only sites that can run in the *same* execution count. The released
    # solutions repeat the same probe once per `public_data` branch, and exactly
    # one branch runs per task; counting those as repeats would credit a saving
    # no execution can realize.
    repeats: dict[str, int] = {}
    excluded: dict[str, int] = {}
    for key, sites in by_key.items():
        if len(sites) < 2:
            continue
        co_occurring = _max_co_occurring(sites)
        if co_occurring > 1:
            repeats[key] = co_occurring
        else:
            excluded[key] = len(sites)
    if not repeats:
        return None
    repeated_apis = sorted({key.split("(")[0] for key in repeats})
    return Alternative(
        alternative_id="duplicate-entity-probe-cache",
        kind="duplicate-entity-probe",
        summary=(
            "Cache entity-keyed lookups by (api, entity expression) and reuse them instead of "
            "re-resolving the same entity within one execution. The released reference solution "
            f"resolves {repeated_apis} on an already-seen entity expression more than once in a "
            "single path."
        ),
        replaces=tuple(repeated_apis),
        saving_basis=(
            "call sites of one entity expression that can co-occur in a single execution; "
            "this is an upper bound on runtime savings, "
            "counted in the released reference solution; sites guarded by mutually exclusive "
            "public_data branches are excluded because only one of them ever runs, and the "
            "runtime multiplicity per site is data-dependent, so this remains a bound on call "
            "sites rather than a count of calls"
        ),
        saving_call_sites=sum(count - 1 for count in repeats.values()),
        verdict="supported",
        verification={
            "repeated_resolution_keys": repeats,
            "excluded_mutually_exclusive_keys": excluded,
            "co_occurrence_note": (
                f"excluded {len(excluded)} entity expression(s) whose repeats are guarded by "
                "mutually exclusive public_data branches; they cannot both execute, so they "
                "yield no runtime saving"
            ),
            "runtime_multiplicity": (
                "a loop-driven call site runs once per entity, so the runtime saving is at "
                "least the co-occurring site count but its exact size is not recovered offline"
            ),
            "entity_apis": {k: v for k, v in entity_apis.items() if k in repeated_apis},
        },
    )


_NAME_PREFIXES = ("show", "search", "get", "list", "remove", "add", "create", "update")
_NAME_SUFFIXES = ("library", "s", "es")


def resource_tokens(api_name: str) -> set[str]:
    """Resource nouns in an API name, so `show_artist` and `search_artists` match.

    Purely structural field-name overlap produces false routes (`show_artist`
    "replaced" by `search_songs` because both return an `id` and a `name`), so
    a bulk candidate must also name the same resource as the probe.
    """

    _, _, api = api_name.partition(".")
    tokens: set[str] = set()
    for word in re.split(r"[_]+", api):
        if word in _NAME_PREFIXES:
            continue
        for suffix in _NAME_SUFFIXES:
            if len(word) > len(suffix) + 2 and word.endswith(suffix):
                word = word[: -len(suffix)]
                break
        if word:
            tokens.add(word)
    return tokens


def _takes_access_token(surface: ApiSurface, api_name: str) -> bool:
    """Is this API user-scoped? The benchmark's own docs answer it.

    `access_token` is how AppWorld's APIs address one user's account; APIs
    without it operate on the global catalogue.
    """

    doc = surface.doc(api_name)
    return bool(doc) and any(p.get("name") == "access_token" for p in doc.parameters)


def _bulk_filter_alternative(
    analysis: SolutionAnalysis, surface: ApiSurface | None
) -> Alternative | None:
    """A paginated list API documents the field a per-entity probe fetches."""

    if surface is None:
        return None
    probes = [s for s in analysis.call_sites if s.is_entity_probe and s.inside_loop]
    listing_apis = [s.name for s in analysis.call_sites if s.via_pagination_helper]
    if not probes:
        return None
    for probe in probes:
        probe_doc = surface.doc(probe.name)
        if probe_doc is None:
            continue
        candidates = []
        for name in surface.api_names():
            if name == probe.name or name.split(".")[0] != probe.app:
                continue
            doc = surface.doc(name)
            if doc is None or doc.response_shape != "list":
                continue
            if not probe_doc.response_fields:
                continue
            if not set(probe_doc.response_fields) <= set(doc.response_fields):
                continue
            if not (resource_tokens(probe.name) & resource_tokens(name)):
                continue
            # A route only replaces per-iteration probing if the list API can be
            # narrowed server-side; otherwise it is a superset that still forces
            # a full scan and saves nothing.
            filter_params = [
                p.get("name")
                for p in doc.parameters
                if p.get("name") not in {"access_token", "page_index"}
            ]
            candidates.append((name, filter_params))
        if not candidates:
            continue
        chosen, filter_params = sorted(candidates)[0]
        bulk_doc = surface.doc(chosen)
        if bulk_doc is None:
            continue
        # Documenting the same response fields is not enough: the bulk API must
        # be able to *ask the probe's question*. `spotify.search_artists`
        # documents every field `spotify.show_artist` returns, but it filters on
        # query/genre/follower counts and cannot resolve a known `artist_id`, so
        # crediting it as a replacement would be a false positive.
        expressible = [
            {"field": field, "filter": param}
            for field in probe.read_fields
            for param in filter_params
            if field == param or field == re.sub(r"^(?:min|max)_", "", param)
        ]
        direct_key = bool(probe.entity_key and probe.entity_key in filter_params)
        # Entity scope matters as much as expressibility. The reference solutions
        # obtain their entities from user-scoped listings ("Get a list of songs
        # in the user's song library", access-token APIs) and then probe each
        # one. A global catalogue search that takes no access token returns
        # entities from outside the user's account, so it cannot be assumed to
        # answer the same question even though it documents the same fields.
        user_scoped_listings = [name for name in listing_apis if _takes_access_token(surface, name)]
        bulk_is_user_scoped = any(p.get("name") == "access_token" for p in bulk_doc.parameters)
        scope_mismatch = bool(user_scoped_listings) and not bulk_is_user_scoped
        if scope_mismatch:
            verdict = "weakly_supported"
            route_reason = (
                f"the probe resolves entities obtained from user-scoped listing(s) "
                f"{user_scoped_listings}, but {chosen} takes no access_token and is a global "
                "catalogue API, so it cannot be assumed to cover the same entity set: it may "
                "return items outside the user's account"
            )
        elif direct_key or expressible:
            verdict = "supported"
            if direct_key:
                route_reason = (
                    f"{chosen} accepts the probe's own entity key "
                    f"{probe.entity_key!r} as a server-side filter"
                )
            else:
                pairs = ", ".join(f"{e['field']} via {e['filter']}" for e in expressible)
                route_reason = (
                    f"{chosen} can express the question the probe answers: the reference "
                    f"solution reads {pairs}, which the bulk API filters on server-side"
                )
        else:
            verdict = "weakly_supported"
            reads = list(probe.read_fields) or ["(no field read recovered)"]
            route_reason = (
                f"{chosen} documents the same fields but offers no filter that expresses what "
                f"{probe.name} answers (the solution reads {reads}; the bulk filters are "
                f"{filter_params}), so a per-entity substitution is unproven and the route "
                "would still require scanning the collection"
            )
        return Alternative(
            alternative_id=f"bulk-filter-route:{chosen}",
            kind="bulk-filter-route",
            summary=(
                f"{probe.name} is called once per iteration to read "
                f"{list(probe.read_fields) or list(probe_doc.response_fields)}; {chosen} is a "
                f"paginated list API whose documented response carries those fields. "
                f"{route_reason}."
            ),
            replaces=(probe.name,),
            saving_basis=(
                "co-occurring call sites of the probe API in the released reference solution, "
                "against a documented response-field superset"
                + (
                    " whose server-side filter expresses the probe's own question"
                    if verdict == "supported"
                    else "; the substitution is unproven offline, so the route is surfaced for "
                    "review rather than credited"
                )
                + "; the per-iteration probe count is data-dependent and is not recovered offline"
            ),
            saving_call_sites=_max_co_occurring(
                [s for s in analysis.call_sites if s.name == probe.name]
            ),
            verdict=verdict,
            verification={
                "probe_api": probe_doc.to_dict(),
                "probe_fields_read_by_solution": list(probe.read_fields),
                "probe_entity_key": probe.entity_key,
                "bulk_api": bulk_doc.to_dict(),
                "bulk_filter_parameters": filter_params,
                "bulk_candidates": [c[0] for c in sorted(candidates)],
                "expressible_filters": expressible,
                "entity_key_is_a_bulk_filter": direct_key,
                "user_scoped_listings_in_solution": user_scoped_listings,
                "bulk_api_is_user_scoped": bulk_is_user_scoped,
                "scope_mismatch": scope_mismatch,
                "expressibility_reason": route_reason,
            },
        )
    return None


def cross_source_join_notes(analysis: SolutionAnalysis, surface: ApiSurface | None) -> list[dict]:
    """Flag probes whose field an earlier bulk listing in the same solution returns.

    This is a review flag, not a scored alternative: whether the cheaper join is
    always valid depends on the data, which the offline census cannot see. It
    exists so a reviewer can spot the `show_album_library` / per-song
    `show_song` redundancy without re-reading every reference solution.
    """

    if surface is None or not analysis.available:
        return []
    listing_apis = [s.name for s in analysis.call_sites if s.via_pagination_helper]
    if not listing_apis:
        return []
    notes: list[dict] = []
    for probe in analysis.call_sites:
        if not (probe.is_entity_probe and probe.inside_loop):
            continue
        probe_doc = surface.doc(probe.name)
        if probe_doc is None:
            continue
        for listing in listing_apis:
            listing_doc = surface.doc(listing)
            if listing_doc is None or listing.split(".")[0] != probe.app:
                continue
            shared = sorted(set(probe_doc.response_fields) & set(listing_doc.response_fields))
            if shared:
                notes.append(
                    {
                        "probe_api": probe.name,
                        "listing_api": listing,
                        "fields_already_listed": shared,
                        "note": (
                            "the solution already pages through a listing that documents these "
                            "fields; a per-entity probe for them may be avoidable, but the "
                            "offline census cannot confirm the joined values match"
                        ),
                    }
                )
    return notes


def _reviewed_alternatives(family: str, analyses: dict[str, SolutionAnalysis]) -> list[Alternative]:
    """Alternatives a manual review established that no detector recovers.

    These come from `memory_census.registry.REVIEWED_NOTES` and are labelled
    `evidence_class="human_review"` so a reader can always tell a reviewed
    finding from an automatic one. The call-site count is still computed from
    the released solution, so the number stays machine-checkable.
    """

    from memory_census.registry import notes_for

    note = notes_for(family)
    if not note:
        return []
    performed = Counter(
        site.name
        for analysis in analyses.values()
        if analysis.available
        for site in analysis.call_sites
    )
    # A reviewed finding names the API it concerns as an explicit field rather
    # than leaving it to substring matching over prose.
    replaced = sorted({api for api in note.get("reviewed_avoidable_apis", []) if api in performed})
    if not replaced:
        return []
    return [
        Alternative(
            alternative_id="reviewed-avoidable-resolution",
            kind="reviewed-avoidable-resolution",
            summary=" ".join(note.get("reviewed_findings") or []),
            replaces=tuple(replaced),
            saving_basis=(
                "human review of the released reference solution against the documented API "
                "surface; counts the reference solution's own call sites for the named APIs"
            ),
            saving_call_sites=sum(performed[name] for name in replaced),
            verdict="supported",
            verification={
                "review_reason_code": note["reason_code"],
                "review_source": note["source"],
                "reference_call_site_counts": {name: performed[name] for name in replaced},
                "counterfactual": note.get("reviewed_counterfactual", ""),
            },
            evidence_class="human_review",
        )
    ]


def family_strategy_evidence(
    tasks: list,
    reference_pool: dict[str, int] | None = None,
    surface: ApiSurface | None = None,
) -> dict:
    """Assemble the offline strategy-structure record for one family."""

    pool = reference_pool or {}
    analyses = {t.task_id: analyze_solution(t.task_id, t.solution_source) for t in tasks}
    available = [a for a in analyses.values() if a.available]

    alternatives: dict[str, Alternative] = {}
    for analysis in available:
        entity_apis = {
            s.name: {"entity_key": s.entity_key} for s in analysis.call_sites if s.is_entity_probe
        }
        for candidate in (
            _duplicate_probe_alternative(analysis, entity_apis),
            _bulk_filter_alternative(analysis, surface),
        ):
            if candidate is not None:
                alternatives.setdefault(candidate.alternative_id, candidate)
    if tasks:
        for alternative in _reviewed_alternatives(tasks[0].family, analyses):
            alternatives.setdefault(alternative.alternative_id, alternative)

    repeated_within_solution = sorted(
        {
            key.split("(")[0]
            for analysis in available
            for key, count in Counter(
                s.resolution_key for s in analysis.call_sites if s.resolution_key and s.inside_loop
            ).items()
            if count > 1
        }
    )
    pool_evidence = {
        alt.alternative_id: {
            "replaces": list(alt.replaces),
            "reference_solution_uses_in_suite": {name: pool.get(name, 0) for name in alt.replaces},
            "repeated_within_one_solution": [
                name for name in alt.replaces if name in repeated_within_solution
            ],
        }
        for alt in alternatives.values()
    }

    if not available:
        alternatives = {}
        alternatives_note = "no released reference solution for this family"
    elif alternatives:
        alternatives_note = ""
    else:
        alternatives_note = (
            "no documented cheaper route found: every loop-driven call site is either "
            "unavoidable per the public docs or not superset by any list API"
        )

    return {
        "solutions_available": len(available),
        "solutions_missing": len(tasks) - len(available),
        "reference_procedure_identical_across_family": bool(available)
        and len({a.distinct_apis for a in available}) == 1,
        "procedure_signatures": {t: procedure_signature(a) for t, a in analyses.items()},
        "alternatives": [a.to_dict() for a in alternatives.values()],
        "alternatives_note": alternatives_note,
        "cross_source_join_notes": [
            note for a in available for note in cross_source_join_notes(a, surface)
        ],
        "alternative_pool_evidence": pool_evidence,
        "loop_driven_call_sites": {
            t: sum(1 for s in a.call_sites if s.inside_loop)
            for t, a in analyses.items()
            if a.available
        },
        "per_task": {t: a.to_dict() for t, a in analyses.items()},
        "evidence_class": "reference_only",
        "procedure_diff": procedure_diff(
            {task.task_id: task.solution_source for task in tasks},
            tasks[0].task_id,
        )
        if tasks
        else {},
    }


def structural_saving_call_sites(alternatives: list[dict]) -> int:
    """Largest static saving among the non-refuted alternative routes.

    The *maximum* rather than the sum: two detected routes frequently replace
    overlapping call sites (a duplicate-probe cache and a bulk listing can both
    cover the same per-entity probe), so summing would double-count the same
    reference calls. The figure is a bound on the route, not a measured cost.
    """

    best = 0
    for alternative in alternatives:
        if alternative.get("verdict") not in {"supported", "weakly_supported"}:
            continue
        best = max(best, int(alternative.get("saving_call_sites") or 0))
    return best


def build_reference_api_pool(solution_sources: list[str | None]) -> dict[str, int]:
    """How often each public API appears across all released reference solutions."""

    pool: dict[str, int] = {}
    for source in solution_sources:
        if not source:
            continue
        for name in {m.group(1) + "." + m.group(2) for m in _APIS_CALL_RE.finditer(source)}:
            pool[name] = pool.get(name, 0) + 1
    return pool
