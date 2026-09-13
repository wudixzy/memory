"""Public-API interaction-cost model, restricted to what the offline data supports.

`docs/26` registers *public environment/API calls* as the primary first-stage
cost. Offline, the only benchmark-authored measurement of that quantity is
`ground_truth/metadata.json:num_api_calls`, which records how many public API
calls the **reference solution** made while it executed during task generation.

The mistake this module exists to prevent
-----------------------------------------

Within a family every sibling shares one reference solution file, so a sibling
costing 214 calls and one costing 138 are *both* executing strategy C. Their
difference is how much data each sibling holds — it is **not** `cost(C)` versus
`cost(B)`, and it is not evidence that a cheaper strategy exists. A lower
reference count on the target is not a low-cost witness for B.

So the sibling gap is kept, as a **diagnostic** (`FamilyCost.reference_cost_gap`),
and the two quantities the B analysis actually needs are kept separate:

* `cost_C` — the target sibling's own recorded call count. This is a legitimate
  reference-only measurement of C on the target.
* `cost_B` — **unknown**. No B trajectory has ever been executed, and no offline
  arithmetic recovers one. The census writes `unknown`; it never substitutes the
  target sibling's reference count, an alternative's call-site count, or a
  ratio for it.

The only C-versus-B quantity the census can honestly produce is a *structural*
saving bound from the released reference source (how many call sites B would not
need). That bound is reported as a bound, labelled as such, and never as a
measured cost.
"""

from __future__ import annotations

from dataclasses import dataclass

from memory_census.dataset import CensusTask

#: Calls every reference solution makes regardless of strategy: the final
#: `supervisor.complete_task` plus one `access_token_from` bootstrap.
CONSTANT_OVERHEAD_CALLS = 2

#: `docs/26` utility-gap bands.
GAP_BAND_WEAK = 0.10
GAP_BAND_STRONG = 0.25
GAP_ABSOLUTE_STRONG = 3


@dataclass(frozen=True)
class TaskCost:
    task_id: str
    number: int
    total_calls: int | None
    comparable_calls: int | None
    has_reference_solution: bool
    difficulty: int | None
    num_apps: int | None
    num_apis: int | None

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "number": self.number,
            "total_calls": self.total_calls,
            "comparable_calls": self.comparable_calls,
            "has_reference_solution": self.has_reference_solution,
            "difficulty": self.difficulty,
            "num_apps": self.num_apps,
            "num_apis": self.num_apis,
        }


@dataclass(frozen=True)
class FamilyCost:
    """Per-family cost table plus the *diagnostic* sibling gap.

    The nominated pair here is explicitly **not** a source/target role
    assignment. Roles come from `admission.role_assignment`, which is driven by
    the recorded state difference; cost may not name them. The
    `source_task`/`target_task` properties are compatibility aliases for
    `costliest_task`/`cheapest_task`, documented as diagnostic-only.
    """

    family: str
    tasks: tuple[TaskCost, ...]
    costliest_task: str | None
    cheapest_task: str | None
    costliest_total_calls: int | None
    cheapest_total_calls: int | None
    absolute_gap: int | None
    gap_ratio: float | None
    band: str
    basis: str
    limitations: tuple[str, ...]

    # --- compatibility aliases, diagnostic only ---------------------------
    # The names below are kept because earlier census code and the census test
    # suite address this pair as source/target. They are **not** a role
    # assignment: the pair is the costliest/cheapest sibling, and roles come
    # from `admission.role_assignment`, which is driven by the recorded state
    # difference. Reading `source_task` as "the source sibling" would re-make
    # exactly the error this module exists to prevent.

    @property
    def source_task(self) -> str | None:
        """Alias of `costliest_task`; diagnostic only, never a role."""

        return self.costliest_task

    @property
    def target_task(self) -> str | None:
        """Alias of `cheapest_task`; diagnostic only, never a role."""

        return self.cheapest_task

    @property
    def source_total_calls(self) -> int | None:
        return self.costliest_total_calls

    @property
    def target_total_calls(self) -> int | None:
        return self.cheapest_total_calls

    def task_cost(self, task_id: str) -> TaskCost | None:
        for cost in self.tasks:
            if cost.task_id == task_id:
                return cost
        return None

    def reference_cost_gap(self) -> dict:
        """The sibling call-count gap, as the diagnostic it is."""

        return {
            "costliest_task": self.costliest_task,
            "cheapest_task": self.cheapest_task,
            "costliest_total_calls": self.costliest_total_calls,
            "cheapest_total_calls": self.cheapest_total_calls,
            "absolute_gap": self.absolute_gap,
            "gap_ratio": None if self.gap_ratio is None else round(self.gap_ratio, 4),
            "band": self.band,
            "basis": self.basis,
            "diagnostic_only": True,
            "aliases": {
                "source_task": self.costliest_task,
                "target_task": self.cheapest_task,
                "note": "compatibility aliases for costliest_task/cheapest_task; they are not a "
                "source/target role assignment and must not be read as one",
            },
            "comparison": "cost(C on one sibling) vs cost(C on another sibling)",
            "is_not": "cost(C) vs cost(B); a lower reference count on the target is not a "
            "low-cost witness for strategy B",
            "limitations": list(self.limitations),
        }

    def to_dict(self) -> dict:
        return {
            "costliest_task": self.costliest_task,
            "cheapest_task": self.cheapest_task,
            "costliest_total_calls": self.costliest_total_calls,
            "cheapest_total_calls": self.cheapest_total_calls,
            "absolute_gap": self.absolute_gap,
            "gap_ratio": None if self.gap_ratio is None else round(self.gap_ratio, 4),
            "band": self.band,
            "basis": self.basis,
            "limitations": list(self.limitations),
            "tasks": [t.to_dict() for t in self.tasks],
        }


@dataclass(frozen=True)
class StrategyCost:
    """One strategy's interaction cost, or an explicit `unknown`."""

    strategy: str
    value: int | None
    unit: str
    basis: str
    evidence_class: str
    target_task_id: str | None = None

    def to_dict(self) -> dict:
        return {
            "strategy": self.strategy,
            "value": "unknown" if self.value is None else self.value,
            "unit": self.unit,
            "basis": self.basis,
            "evidence_class": self.evidence_class,
            "target_task_id": self.target_task_id,
        }


def task_cost(task: CensusTask) -> TaskCost:
    total = task.metadata.num_api_calls
    comparable = None if total is None else max(0, total - CONSTANT_OVERHEAD_CALLS)
    return TaskCost(
        task_id=task.task_id,
        number=task.number,
        total_calls=total,
        comparable_calls=comparable,
        has_reference_solution=task.solution_source is not None,
        difficulty=task.metadata.difficulty,
        num_apps=task.metadata.num_apps,
        num_apis=task.metadata.num_apis,
    )


def _band(gap_ratio: float | None, absolute_gap: int | None) -> str:
    """`docs/26` utility-gap band: >=3 fewer calls AND a real relative gap.

    Both legs are required. A 3-call difference on a 200-call task is not a
    meaningful utility gap, and a large percentage on a task whose siblings
    both cost under ten calls is noise; requiring both keeps the band honest.

    This band grades the *diagnostic* sibling gap. It never grades cost(B).
    """

    if gap_ratio is None or absolute_gap is None:
        return "unknown"
    if absolute_gap >= GAP_ABSOLUTE_STRONG and gap_ratio >= GAP_BAND_STRONG:
        return "strong"
    if gap_ratio >= GAP_BAND_WEAK or absolute_gap >= GAP_ABSOLUTE_STRONG:
        return "weak"
    return "negligible"


def family_cost(tasks: list[CensusTask]) -> FamilyCost:
    """Per-sibling reference costs and the diagnostic costliest/cheapest gap."""

    costs = tuple(sorted((task_cost(t) for t in tasks), key=lambda c: c.number))
    limitations: list[str] = [
        "cost is the reference solution's executed API-call count (benchmark metadata), "
        "not a measured strategy distribution",
        "both endpoints of this gap are the *same* strategy C running on different siblings, "
        "so the gap is a data volume diagnostic and not cost(C) vs cost(B)",
        "a within-family gap can be driven by entity or record counts rather than by any "
        "strategy difference; the census does not claim otherwise",
    ]
    measured = [c for c in costs if c.total_calls is not None]
    if not measured:
        return FamilyCost(
            family=tasks[0].family,
            tasks=costs,
            costliest_task=None,
            cheapest_task=None,
            costliest_total_calls=None,
            cheapest_total_calls=None,
            absolute_gap=None,
            gap_ratio=None,
            band="unknown",
            basis="missing_metadata",
            limitations=tuple(limitations),
        )
    if not all(c.has_reference_solution for c in measured):
        limitations.append(
            "at least one sibling has no released reference solution, so the family's "
            "procedure could not be read end-to-end"
        )
    if len(measured) < 2:
        return FamilyCost(
            family=tasks[0].family,
            tasks=costs,
            costliest_task=None,
            cheapest_task=None,
            costliest_total_calls=None,
            cheapest_total_calls=None,
            absolute_gap=None,
            gap_ratio=None,
            band="unknown",
            basis="single_measured_task",
            limitations=tuple(limitations),
        )
    costliest = max(measured, key=lambda c: (c.total_calls, -c.number))
    cheapest = min(measured, key=lambda c: (c.total_calls, c.number))
    absolute_gap = int(costliest.total_calls) - int(cheapest.total_calls)
    comparable_gap = abs(int(costliest.comparable_calls) - int(cheapest.comparable_calls))
    denominator = max(1, int(costliest.comparable_calls or 0))
    gap_ratio = comparable_gap / denominator if denominator else None
    return FamilyCost(
        family=tasks[0].family,
        tasks=costs,
        costliest_task=costliest.task_id,
        cheapest_task=cheapest.task_id,
        costliest_total_calls=costliest.total_calls,
        cheapest_total_calls=cheapest.total_calls,
        absolute_gap=absolute_gap,
        gap_ratio=gap_ratio,
        band=_band(gap_ratio, absolute_gap),
        basis="reference_solution_metadata",
        limitations=tuple(limitations),
    )


def strategy_cost_c(cost: FamilyCost, target_task_id: str | None) -> StrategyCost:
    """cost(C) on the target: the reference procedure's own recorded call count.

    This is a real measurement of C — the benchmark generator executed the
    released reference solution on that sibling and recorded how many public API
    calls it made — so it is admissible reference-only evidence about C.

    With no nominated target the record stays a complete `StrategyCost` with
    `value=None` (`unknown`) rather than a bare ``{"value": "unknown"}`` dict, so
    every renderer can read the same fields for every family.
    """

    task = cost.task_cost(target_task_id) if target_task_id else None
    if target_task_id is None:
        basis = (
            "no target sibling was nominated for this family, so there is no target on which "
            "C's cost could be read; the field stays unknown rather than being filled from "
            "another sibling"
        )
    else:
        basis = (
            "the released reference solution is strategy C for this family; "
            "ground_truth/metadata.json records how many public API calls it made while "
            "executing on the nominated target sibling"
        )
    return StrategyCost(
        strategy="C",
        value=None if task is None else task.total_calls,
        unit="public_api_calls",
        basis=basis,
        evidence_class="reference_only" if task and task.total_calls is not None else "unknown",
        target_task_id=target_task_id,
    )


def strategy_cost_b() -> StrategyCost:
    """cost(B) on the target: always `unknown` in this stage.

    Nothing offline measures B: B has never been executed, by a model or by the
    benchmark. Reporting a number here — a sibling's reference count, an
    alternative's call-site count, a difference of the two — would be a
    fabrication, so the field is `unknown` and the structural bound lives in
    `c_vs_b_comparison` where its basis can be stated.
    """

    return StrategyCost(
        strategy="B",
        value=None,
        unit="public_api_calls",
        basis=(
            "strategy B has no executed trajectory in this stage: no model rollout and no "
            "benchmark execution produced one, and no offline arithmetic recovers a cost for "
            "a route that was never run. See c_vs_b_comparison.structural_saving_call_sites "
            "for the static bound that is available instead"
        ),
        evidence_class="unknown",
        target_task_id=None,
    )
