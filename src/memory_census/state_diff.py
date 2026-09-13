"""Reproducible source/target difference evidence, and what it does *not* imply.

Why this module exists
----------------------

In AppWorld a *scenario* (family) is one generator with numbered siblings, and
every sibling shares **one reference solution file**. The generator samples
per-sibling parameters into `public_data`/`private_data`, and the reference
solution is a single program parameterized by them.

Two consequences the earlier census got wrong:

1. `num_api_calls` differs between siblings because the *same* procedure ran
   over different data. A sibling that costs 214 and one that costs 138 are both
   executing strategy C; the difference is how many entities, rows or records
   that sibling's data contains. That is a **data-volume** difference, not
   `cost(C)` versus `cost(B)`, and it is not evidence that C was locked in.
2. Cost alone therefore cannot nominate a source and a target. Nomination needs
   a recorded *condition* difference: something about the target that changes
   what the task requires relative to the source.

So this module computes, reproducibly and from files that ship with the
benchmark, a difference record per ordered sibling pair, and classifies it:

``instruction_semantic_change``
    the instruction differs beyond literal slots (numbers, dates, quoted
    strings), i.e. the sentence template itself changed.
``branch_parameter_change``
    the reference program's *control flow* is conditioned on a `public_data`
    key (an `if`/`while`/ternary test), and that key holds different values on
    source and target. The same program takes a different path.
``precondition_change``
    `public_data`/`private_data` scalar values or evaluator requirement strings
    differ, but the reference program's control flow does not.
``workload_size_change``
    only collection sizes / entity counts differ. The executed reference
    structure is identical on both siblings.
``no_difference_detected``
    nothing above differs.
``unavailable``
    a sibling has no released reference solution, so no classification is made.

Only the first three are *strategy-relevant*; only the first two mean the
reference program's route itself changes (``route_changed``). A pure workload
difference must never be promoted into a strategy claim — `admission.py`
enforces that, and `rubric.py` scores the registered utility-gap criterion 0
when the family's siblings differ by volume alone.

Nothing here is a cost measurement. `cost.py` owns cost, `admission.py` owns
what may be admitted, and every value this module emits is reference-only
research-side evidence that must never reach an adaptive loop.
"""

from __future__ import annotations

import ast
import difflib
import re
from dataclasses import dataclass

from memory_census.dataset import CensusTask, read_state_seed_counts
from memory_census.strategy import public_data_attribute

#: Classification labels, ordered from strongest to weakest evidence.
INSTRUCTION_SEMANTIC_CHANGE = "instruction_semantic_change"
BRANCH_PARAMETER_CHANGE = "branch_parameter_change"
PRECONDITION_CHANGE = "precondition_change"
WORKLOAD_SIZE_CHANGE = "workload_size_change"
NO_DIFFERENCE = "no_difference_detected"
UNAVAILABLE = "unavailable"

CLASSIFICATIONS = (
    INSTRUCTION_SEMANTIC_CHANGE,
    BRANCH_PARAMETER_CHANGE,
    PRECONDITION_CHANGE,
    WORKLOAD_SIZE_CHANGE,
    NO_DIFFERENCE,
    UNAVAILABLE,
)

#: Classes that say something about *what the task requires*, as opposed to how
#: much of it there is.
STRATEGY_RELEVANT_CLASSIFICATIONS = (
    INSTRUCTION_SEMANTIC_CHANGE,
    BRANCH_PARAMETER_CHANGE,
    PRECONDITION_CHANGE,
)

#: Classes in which the reference program's own route changes between siblings.
ROUTE_CHANGING_CLASSIFICATIONS = (INSTRUCTION_SEMANTIC_CHANGE, BRANCH_PARAMETER_CHANGE)

#: How strongly each class speaks to a source/target strategy difference. Used
#: to order sibling pairs; it is a ranking of *evidence*, not of cost.
CLASS_RANK = {
    INSTRUCTION_SEMANTIC_CHANGE: 3,
    BRANCH_PARAMETER_CHANGE: 2,
    PRECONDITION_CHANGE: 1,
    WORKLOAD_SIZE_CHANGE: 0,
    NO_DIFFERENCE: 0,
    UNAVAILABLE: -1,
}

#: The rule used to nominate a source/target pair, published with the artifact
#: so a reviewer can re-derive the choice instead of trusting it.
SELECTION_RULE = (
    "strongest recorded difference classification first, then the most recorded change "
    "evidence, then the lowest (source sibling number, target sibling number). Cost is "
    "never consulted: both siblings are measured under the same reference procedure, so "
    "the costlier sibling is a statement about data volume, not about strategy"
)

_MAX_SPANS = 6

_NUMBER_RE = re.compile(r"\b\d+(?:\.\d+)?\b")
_QUOTED_RE = re.compile(r"'[^']*'|\"[^\"]*\"")


def sampled_values(public_data: dict) -> tuple[str, ...]:
    """The generator's sampled slot values, longest first.

    AppWorld interpolates `public_data` values straight into the instruction
    template ("released {before_after} {year} year"), so those values *are* the
    template's slots. Longest-first ordering keeps `in or before` from being
    half-masked by an earlier `before`.
    """

    values: set[str] = set()
    for value in public_data.values():
        if isinstance(value, bool) or value is None:
            continue
        if isinstance(value, (int, float, str)):
            text = str(value)
            if text:
                values.add(text)
                # Generators pluralize sampled nouns ("roommate" -> "roommates").
                values.add(text + "s")
    return tuple(sorted(values, key=lambda item: (-len(item), item)))


def instruction_template(text: str, values: tuple[str, ...] = ()) -> str:
    """Instruction with its sampled slots masked.

    Two siblings generated from one template differ only in the sampled values
    (a year, a count, a noun). Masking those values is what separates "the same
    request with different parameters" from "a different request" — without it,
    `before` versus `after` reads as a rewritten instruction instead of one slot
    holding a different word.
    """

    masked = _QUOTED_RE.sub("<str>", text)
    for value in values:
        masked = re.sub(
            rf"(?<![\w<]){re.escape(value)}(?![\w>])",
            "<value>",
            masked,
            flags=re.IGNORECASE,
        )
    return _NUMBER_RE.sub("<num>", masked)


def literal_tokens(text: str, values: tuple[str, ...] = ()) -> list[str]:
    """The sampled literal slots of an instruction, in order."""

    tokens = [match.group(0) for match in _QUOTED_RE.finditer(text)]
    tokens.extend(match.group(0) for match in _NUMBER_RE.finditer(text))
    for value in values:
        if re.search(rf"(?<![\w<]){re.escape(value)}(?![\w>])", text, flags=re.IGNORECASE):
            tokens.append(value)
    return tokens


@dataclass(frozen=True)
class InstructionDifference:
    identical: bool
    template_identical: bool
    source_instruction: str
    target_instruction: str
    changed_spans: tuple[dict, ...]
    literal_changes: tuple[dict, ...]
    semantic_change: bool
    #: Why the two instructions were judged the same or different request.
    template_basis: str
    masked_values: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "identical": self.identical,
            "template_identical": self.template_identical,
            "semantic_change": self.semantic_change,
            "source_instruction": self.source_instruction,
            "target_instruction": self.target_instruction,
            "changed_spans": [dict(span) for span in self.changed_spans],
            "literal_changes": [dict(change) for change in self.literal_changes],
            "source_template": instruction_template(self.source_instruction, self.masked_values),
            "target_template": instruction_template(self.target_instruction, self.masked_values),
            "template_basis": self.template_basis,
            "masked_values": list(self.masked_values),
        }


def _changed_spans(source: str, target: str) -> tuple[dict, ...]:
    """Concrete character-level changes, so a reviewer sees the words, not a count."""

    matcher = difflib.SequenceMatcher(a=source, b=target, autojunk=False)
    spans: list[dict] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        spans.append(
            {
                "op": tag,
                "source_text": source[i1:i2],
                "target_text": target[j1:j2],
                "source_context": " ".join(source[max(0, i1 - 30) : i2 + 30].split()),
                "target_context": " ".join(target[max(0, j1 - 30) : j2 + 30].split()),
            }
        )
        if len(spans) >= _MAX_SPANS:
            break
    return tuple(spans)


def instruction_difference(
    source_task: CensusTask, target_task: CensusTask
) -> InstructionDifference:
    source = source_task.specs.instruction
    target = target_task.specs.instruction
    # The union of both siblings' sampled values: a slot that holds "before" on
    # one sibling and "after" on the other must be masked on both sides.
    values = tuple(
        sorted(
            set(sampled_values(source_task.public_data))
            | set(sampled_values(target_task.public_data)),
            key=lambda item: (-len(item), item),
        )
    )
    source_template = instruction_template(source, values)
    target_template = instruction_template(target, values)
    template_identical = source_template == target_template
    literal_changes: list[dict] = []
    if not template_identical:
        source_literals = literal_tokens(source, values)
        target_literals = literal_tokens(target, values)
        for index in range(max(len(source_literals), len(target_literals))):
            left = source_literals[index] if index < len(source_literals) else None
            right = target_literals[index] if index < len(target_literals) else None
            if left != right:
                literal_changes.append({"slot": index, "source": left, "target": right})
    basis = (
        "the two instructions are identical"
        if source == target
        else (
            "masking every sampled public_data value leaves the same sentence, so the "
            "instructions are one template with different parameter words"
            if template_identical
            else "masking sampled public_data values still leaves different sentences"
        )
    )
    return InstructionDifference(
        identical=source == target,
        template_identical=template_identical,
        source_instruction=source,
        target_instruction=target,
        changed_spans=_changed_spans(source, target),
        literal_changes=tuple(literal_changes),
        semantic_change=not template_identical,
        template_basis=basis,
        masked_values=values,
    )


def branch_condition_keys(source: str | None) -> dict[str, list[dict]]:
    """`public_data` keys the reference program *tests*, with the test text.

    A key read as a plain value (a filter argument, an amount) parameterizes the
    data; a key used in an `if`/`while`/ternary test selects between code paths,
    so a change in its value changes which calls the program makes. Only the
    latter is control flow, and the census keeps the two apart.
    """

    if not source:
        return {}
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}
    found: dict[str, list[dict]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.If, ast.While, ast.IfExp)):
            continue
        test = node.test
        for sub in ast.walk(test):
            key = public_data_attribute(sub)
            if key is None:
                continue
            try:
                expression = " ".join(ast.unparse(test).split())
            except Exception:  # pragma: no cover - defensive for exotic nodes
                expression = ""
            entry = {"line": node.lineno, "expression": expression}
            if entry not in found.setdefault(key, []):
                found[key].append(entry)
    return {key: sorted(entries, key=lambda e: e["line"]) for key, entries in sorted(found.items())}


def solution_referenced_keys(source: str | None) -> dict[str, list[int]]:
    """Every `public_data` key the reference program mentions, and where."""

    if not source:
        return {}
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}
    keys: dict[str, list[int]] = {}
    for node in ast.walk(tree):
        key = public_data_attribute(node)
        if key is not None:
            keys.setdefault(key, []).append(node.lineno)
    return {key: sorted(lines) for key, lines in sorted(keys.items())}


def _is_collection(value: object) -> bool:
    return isinstance(value, (list, tuple, set))


def _summarize(value: object) -> object:
    """Render a value for the report without dumping a whole entity list."""

    if _is_collection(value):
        return {"collection": True, "size": len(value)}
    return value


def _mapping_difference(source: dict, target: dict, branch_keys: dict[str, list[dict]]) -> dict:
    """Key-level difference between two sibling parameter dictionaries."""

    source_keys = set(source)
    target_keys = set(target)
    value_changes: list[dict] = []
    volume_changes: list[dict] = []
    for key in sorted(source_keys & target_keys):
        left, right = source[key], target[key]
        if left == right:
            continue
        if _is_collection(left) and _is_collection(right):
            volume_changes.append(
                {
                    "key": key,
                    "source_size": len(left),
                    "target_size": len(right),
                    "kind": "collection_size",
                }
            )
        else:
            value_changes.append(
                {
                    "key": key,
                    "source": _summarize(left),
                    "target": _summarize(right),
                    "kind": "scalar_value",
                }
            )
    branch_key_changes = [change for change in value_changes if change["key"] in branch_keys]
    return {
        "keys_only_in_source": sorted(source_keys - target_keys),
        "keys_only_in_target": sorted(target_keys - source_keys),
        "value_changes": value_changes,
        "volume_changes": volume_changes,
        "branch_key_changes": branch_key_changes,
        "non_branch_value_changes": [
            change for change in value_changes if change["key"] not in branch_keys
        ],
    }


def _evaluator_difference(source_task: CensusTask, target_task: CensusTask) -> dict:
    source_requirements = [
        entry.get("requirement")
        for entry in source_task.test_data
        if isinstance(entry, dict) and isinstance(entry.get("requirement"), str)
    ]
    target_requirements = [
        entry.get("requirement")
        for entry in target_task.test_data
        if isinstance(entry, dict) and isinstance(entry.get("requirement"), str)
    ]
    return {
        "evaluation_source_identical": source_task.evaluation_source
        == target_task.evaluation_source,
        "requirements_identical": source_requirements == target_requirements,
        "source_requirements": source_requirements,
        "target_requirements": target_requirements,
        "requirements_only_in_source": [
            r for r in source_requirements if r not in target_requirements
        ],
        "requirements_only_in_target": [
            r for r in target_requirements if r not in source_requirements
        ],
    }


@dataclass(frozen=True)
class StateDifference:
    family: str
    source_task_id: str
    target_task_id: str
    classification: str
    strategy_relevant_change: bool
    route_changed: bool
    same_reference_solution: bool
    instruction: InstructionDifference
    public_data: dict
    private_data: dict
    seed_state: dict
    evaluator: dict
    reference: dict
    change_evidence: tuple[dict, ...]
    classification_rationale: str

    @property
    def strategy_shift_witness(self) -> bool:
        """Is there a condition change that could make C relatively worse?

        A pure workload rescale is explicitly *not* a witness: the same program
        runs the same route, only over more rows. Neither is a filter-argument
        value change that leaves the control flow untouched.
        """

        return self.route_changed or self.instruction.semantic_change

    def to_dict(self) -> dict:
        return {
            "family": self.family,
            "source_task_id": self.source_task_id,
            "target_task_id": self.target_task_id,
            "classification": self.classification,
            "classification_rationale": self.classification_rationale,
            "strategy_relevant_change": self.strategy_relevant_change,
            "route_changed": self.route_changed,
            "strategy_shift_witness": self.strategy_shift_witness,
            "same_reference_solution": self.same_reference_solution,
            "instruction": self.instruction.to_dict(),
            "public_data": self.public_data,
            "private_data": self.private_data,
            "seed_state": self.seed_state,
            "evaluator": self.evaluator,
            "reference": self.reference,
            "change_evidence": [dict(item) for item in self.change_evidence],
        }


def _classify(
    instruction: InstructionDifference,
    public_data: dict,
    private_data: dict,
    seed_state: dict,
    evaluator: dict,
    reference: dict,
) -> tuple[str, str]:
    """Strongest difference class present, with the reason it was chosen."""

    if not reference.get("both_solutions_available"):
        return UNAVAILABLE, "at least one sibling has no released reference solution"

    if instruction.semantic_change:
        source_template = instruction_template(
            instruction.source_instruction, instruction.masked_values
        )
        target_template = instruction_template(
            instruction.target_instruction, instruction.masked_values
        )
        return (
            INSTRUCTION_SEMANTIC_CHANGE,
            "the instruction template differs beyond its sampled slots "
            f"(source {source_template!r} vs target {target_template!r})",
        )
    if public_data["branch_key_changes"]:
        keys = ", ".join(change["key"] for change in public_data["branch_key_changes"])
        return (
            BRANCH_PARAMETER_CHANGE,
            f"the reference program's control flow tests public_data key(s) {keys}, whose "
            "values differ between the siblings, so the same program takes a different path",
        )
    if (
        public_data["non_branch_value_changes"]
        or public_data["keys_only_in_source"]
        or (public_data["keys_only_in_target"])
    ):
        return (
            PRECONDITION_CHANGE,
            "public_data values differ without changing the program's control flow (parameters "
            "consumed as values rather than branch tests)",
        )
    if private_data["value_changes"] or evaluator["requirements_identical"] is False:
        return (
            PRECONDITION_CHANGE,
            "private_data scalar values or evaluator requirement strings differ between the "
            "siblings",
        )
    if (
        public_data["volume_changes"]
        or private_data["volume_changes"]
        or seed_state.get("row_count_changes")
        or seed_state.get("tables_only_in_source")
        or seed_state.get("tables_only_in_target")
    ):
        return (
            WORKLOAD_SIZE_CHANGE,
            "only collection sizes / seed row counts differ; the instruction template and the "
            "reference program's control flow are identical, so the same route runs over a "
            "different amount of data",
        )
    return NO_DIFFERENCE, "no instruction, parameter, seed-state or evaluator difference detected"


def pair_state_difference(
    source_task: CensusTask,
    target_task: CensusTask,
    reference_analysis: dict | None = None,
) -> StateDifference:
    """Difference record for one ordered (source, target) sibling pair."""

    reference_analysis = reference_analysis or {}
    instruction = instruction_difference(source_task, target_task)
    branch_keys = branch_condition_keys(source_task.solution_source)
    referenced = solution_referenced_keys(source_task.solution_source)
    public_data = _mapping_difference(source_task.public_data, target_task.public_data, branch_keys)
    public_data["branch_condition_keys"] = branch_keys
    public_data["keys_referenced_by_reference_solution"] = sorted(referenced)
    private_data = _mapping_difference(source_task.private_data, target_task.private_data, {})
    seed_state = {
        "source_row_counts": read_state_seed_counts(source_task.task_dir),
        "target_row_counts": read_state_seed_counts(target_task.task_dir),
        "row_count_changes": [],
        "tables_only_in_source": [],
        "tables_only_in_target": [],
    }
    source_rows = seed_state["source_row_counts"]
    target_rows = seed_state["target_row_counts"]
    seed_state["row_count_changes"] = [
        {"table": table, "source_rows": source_rows[table], "target_rows": target_rows[table]}
        for table in sorted(set(source_rows) & set(target_rows))
        if source_rows[table] != target_rows[table]
    ]
    seed_state["tables_only_in_source"] = sorted(set(source_rows) - set(target_rows))
    seed_state["tables_only_in_target"] = sorted(set(target_rows) - set(source_rows))
    evaluator = _evaluator_difference(source_task, target_task)
    reference = {
        "both_solutions_available": source_task.solution_source is not None
        and target_task.solution_source is not None,
        "same_reference_solution": source_task.solution_source == target_task.solution_source,
        "source_procedure_signature": reference_analysis.get("source_signature"),
        "target_procedure_signature": reference_analysis.get("target_signature"),
        "procedure_identical": reference_analysis.get("source_signature")
        == reference_analysis.get("target_signature"),
    }
    classification, rationale = _classify(
        instruction, public_data, private_data, seed_state, evaluator, reference
    )
    evidence: list[dict] = []
    for span in instruction.changed_spans:
        evidence.append({"kind": "instruction_span", **span})
    for change in public_data["branch_key_changes"]:
        evidence.append(
            {
                "kind": "branch_parameter",
                "key": change["key"],
                "source": change["source"],
                "target": change["target"],
                "tested_at": [
                    {"line": entry["line"], "expression": entry["expression"]}
                    for entry in branch_keys.get(change["key"], [])
                ],
            }
        )
    for change in public_data["non_branch_value_changes"]:
        evidence.append({"kind": "public_data_value", **change})
    for change in private_data["value_changes"]:
        evidence.append({"kind": "private_data_value", **change})
    for change in public_data["volume_changes"] + private_data["volume_changes"]:
        evidence.append({"kind": "collection_size", **change})
    for change in seed_state["row_count_changes"]:
        evidence.append({"kind": "seed_row_count", **change})
    for requirement in evaluator["requirements_only_in_target"]:
        evidence.append({"kind": "evaluator_requirement_only_in_target", "text": requirement})
    for requirement in evaluator["requirements_only_in_source"]:
        evidence.append({"kind": "evaluator_requirement_only_in_source", "text": requirement})
    return StateDifference(
        family=source_task.family,
        source_task_id=source_task.task_id,
        target_task_id=target_task.task_id,
        classification=classification,
        strategy_relevant_change=classification in STRATEGY_RELEVANT_CLASSIFICATIONS,
        route_changed=classification in ROUTE_CHANGING_CLASSIFICATIONS,
        same_reference_solution=reference["same_reference_solution"],
        instruction=instruction,
        public_data=public_data,
        private_data=private_data,
        seed_state=seed_state,
        evaluator=evaluator,
        reference=reference,
        change_evidence=tuple(evidence),
        classification_rationale=rationale,
    )


def family_state_differences(
    tasks: list[CensusTask], reference_analyses: dict[str, dict] | None = None
) -> dict:
    """All ordered sibling pairs of one family, plus the family-level summary."""

    reference_analyses = reference_analyses or {}
    pairs: list[StateDifference] = []
    for source in tasks:
        for target in tasks:
            if source.task_id == target.task_id:
                continue
            pairs.append(
                pair_state_difference(
                    source,
                    target,
                    reference_analyses.get(source.task_id, {}),
                )
            )
    classes = sorted({pair.classification for pair in pairs})
    analysable = [pair for pair in pairs if pair.classification != UNAVAILABLE]
    selected = (
        min(
            analysable,
            key=lambda pair: (
                -CLASS_RANK.get(pair.classification, 0),
                -len(pair.change_evidence),
                pair.source_task_id,
                pair.target_task_id,
            ),
        )
        if analysable
        else None
    )
    return {
        "pairs": [pair.to_dict() for pair in pairs],
        "classifications_present": classes,
        "selection_rule": SELECTION_RULE,
        "selected_pair": selected.to_dict() if selected else None,
        "any_strategy_shift_witness": any(pair.strategy_shift_witness for pair in pairs),
        "all_pairs_workload_only": bool(pairs)
        and all(pair.classification == WORKLOAD_SIZE_CHANGE for pair in pairs),
        "any_pair_strategy_relevant": any(pair.strategy_relevant_change for pair in pairs),
    }
