"""Human review registry: families the automatic pass must not silently re-admit.

Everything here is auditable in one place. The census never drops a family
because of a registry entry without recording the entry, its author date, and
its reason in the report.

Current entries reflect already-completed project history:

* ``432dc7a`` is the coupon family used by the completed ACE AppWorld batch
  (`docs/21`-`docs/24`). Its instruction explicitly asks the agent to compare
  the two promotions and pick the cheaper one, which trips `docs/26` gate 5:
  the instruction itself forces the comparison, so reusing a known-good
  strategy cannot suppress it. `docs/24` additionally records that ACE formed
  *healthy* conditional comparison memory on this family, so the candidate was
  correctly stopped. It is retained here as an explicit counter-example.
"""

from __future__ import annotations

from dataclasses import dataclass

REGISTRY_VERSION = "registry-2026-09-13"


@dataclass(frozen=True)
class RegistryEntry:
    family: str
    status: str  # "rejected" | "hold" | "note"
    reason_code: str
    reason: str
    recorded: str
    source: str
    #: Alternative ids the manual review found to be wrong. Listed here so the
    #: census can mark them refuted instead of crediting a detector artifact.
    refuted_alternatives: tuple[str, ...] = ()
    #: Reference facts the manual review established that no detector recovers.
    reviewed_findings: tuple[str, ...] = ()
    #: APIs the review found to be avoidable on the reference solution itself.
    reviewed_avoidable_apis: tuple[str, ...] = ()
    #: Exact reference calls saved by removing those, per the review.
    reviewed_counterfactual: str = ""

    def to_dict(self) -> dict:
        return {
            "family": self.family,
            "status": self.status,
            "reason_code": self.reason_code,
            "reason": self.reason,
            "recorded": self.recorded,
            "source": self.source,
            "refuted_alternatives": list(self.refuted_alternatives),
            "reviewed_findings": list(self.reviewed_findings),
            "reviewed_avoidable_apis": list(self.reviewed_avoidable_apis),
            "reviewed_counterfactual": self.reviewed_counterfactual,
        }


ENTRIES: tuple[RegistryEntry, ...] = (
    RegistryEntry(
        family="432dc7a",
        status="rejected",
        reason_code="target_forces_comparison",
        reason=(
            "Instruction states 'See if it is a better deal ... whichever option is cheaper'. "
            "The target instruction itself demands the comparison, so a learned preference "
            "cannot suppress it (docs/26 gate 5). ACE additionally formed healthy conditional "
            "comparison memory on this family, and docs/24 records the branch test was "
            "correctly stopped."
        ),
        recorded="2026-09-13",
        source="docs/21_appworld_ab_execution_plan.md, docs/24_ace_appworld_real_batch_results.md",
    ),
    RegistryEntry(
        family="ec437da",
        status="hold",
        reason_code="target_forces_comparison",
        reason=(
            "Instruction states 'Do whatever is cheaper' between gift-wrap options. Same "
            "gate-5 concern as 432dc7a: the choice is stated as the task. Retained for review "
            "rather than auto-admitted."
        ),
        recorded="2026-09-13",
        source="docs/26_strategy_lockin_experiment_plan.md (gate 5)",
    ),
    RegistryEntry(
        family="27e1026",
        status="rejected",
        reason_code="b_route_scope_mismatch",
        reason=(
            "The proposed spotify.search_songs alternative is a global catalogue search, "
            "while C obtains songs from the user's song, album and playlist libraries. "
            "Matching response fields do not establish that B visits the same user-scoped "
            "entity set or succeeds on the target; B success and cost are unknown."
        ),
        recorded="2026-09-13",
        source=(
            "manual review of 27e1026 reference solution against "
            "data/base_dbs/api_docs.db; Stage-A Codex review"
        ),
    ),
)

#: Families where a human review pass established a fact the automatic
#: detectors mis-report. These notes override the derived claim rather than
#: silently deleting it, so a reviewer can see both.
REVIEWED_NOTES: tuple[RegistryEntry, ...] = (
    RegistryEntry(
        family="57c3486",
        status="note",
        reason_code="detector_false_positive",
        reason=(
            "The derived 'bulk-filter-route:spotify.search_artists' is a false positive and is "
            "marked refuted: search_artists matches artist objects by query/genre/follower "
            "count and cannot substitute for resolving one known artist_id."
        ),
        recorded="2026-09-13",
        source=(
            "manual review of third_party/ace-appworld/data/tasks/57c3486_*/ground_truth/"
            "solution.py against data/base_dbs/api_docs.db"
        ),
        refuted_alternatives=("bulk-filter-route:spotify.search_artists",),
        reviewed_findings=(
            "The reference solution pages spotify.show_following_artists, whose records already "
            "carry artist_id, and then calls spotify.show_artist(artist_id=...) once per "
            "followed artist purely to obtain the name. The artist_id is already in hand, so "
            "that per-artist call is avoidable.",
            "spotify.search_songs accepts an artist_id filter, so the per-artist song lookup "
            "does not require the separate show_artist resolution either.",
            "These findings are reference-structural: the census cannot confirm what the frozen "
            "following-artist pages contain for a specific generated task.",
        ),
    ),
    RegistryEntry(
        family="ce359b5",
        status="note",
        reason_code="scope_correction",
        reason=(
            "The 'bulk-filter-route:spotify.search_songs' entry is kept as supported "
            "(min_release_date / max_release_date are documented server-side filters and "
            "search_songs returns release_date), but the reference task comment claiming "
            "show_song_library 'will have release_date information' is wrong: the documented "
            "response carries only added_at. The per-song probe is therefore not avoidable via "
            "the library listing."
        ),
        recorded="2026-09-13",
        source=(
            "manual review of data/tasks/ce359b5_*/ground_truth/solution.py against "
            "data/base_dbs/api_docs.db (spotify.show_song_library response schema)"
        ),
        reviewed_findings=(
            "The avoidable calls are the repeated per-branch spotify.show_song sites, not the "
            "library listing.",
            "The benchmark's own task comment misstates the documented library response, which "
            "is itself a discoverability hazard worth noting for the explorability probe.",
        ),
    ),
)

_BY_FAMILY = {entry.family: entry for entry in ENTRIES}
_NOTES_BY_FAMILY = {entry.family: entry for entry in REVIEWED_NOTES}
_REFUTED_BY_FAMILY = {entry.family: set(entry.refuted_alternatives) for entry in REVIEWED_NOTES}


def refuted_alternatives_for(family: str) -> set[str]:
    """Alternative ids a manual review marked refuted, so scoring cannot credit them."""

    return set(_REFUTED_BY_FAMILY.get(family, set()))


def notes_for(family: str) -> dict | None:
    entry = _NOTES_BY_FAMILY.get(family)
    return entry.to_dict() if entry else None


def reviewed_notes() -> list[dict]:
    return [e.to_dict() for e in REVIEWED_NOTES]


def entry_for(family: str) -> RegistryEntry | None:
    return _BY_FAMILY.get(family)


def rejections() -> list[dict]:
    return [e.to_dict() for e in ENTRIES if e.status == "rejected"]


def holds() -> list[dict]:
    return [e.to_dict() for e in ENTRIES if e.status == "hold"]
