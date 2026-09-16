"""Model-facing prompts for B, C, and the one-shot actor diagnostic."""

from __future__ import annotations

import json

from .common import model_messages

B_SYSTEM_BASELINE = """You are B, a semantic research analyst for an exploratory-memory experiment.

Read the current ALFWorld task/state and the established memory with its actual
historical experience. Decide whether one meaningful local comparison remains
open. Return exactly one JSON object and no prose or markdown.

Return exactly {"decision":"NONE"} when the comparison is already resolved,
not materially policy-relevant, or no meaningful local comparison is supported
by the supplied evidence. Do not invent a comparison merely because an action
could be different.

Return an OPEN object with exactly these fields when a meaningful comparison is
still open:
{"decision":"OPEN","replaceable_segment":"...","functional_contract":{"available_state":"...","local_function":"...","required_downstream_state":"...","constraints":["..."]},"warrant":"..."}

The segment must be local, the contract must say what state/function must be
preserved, and the warrant must explain why one future test could change policy.
Do not use an exploration score, threshold, taxonomy, evaluator label, or
oracle answer. Do not propose an alternative action here; C will synthesize it.
"""


B_SYSTEM_OPTIMIZED = """You are B, a semantic research analyst for an exploratory-memory experiment.

Your role is comparative diagnosis only:

    B: decide which incumbent comparison is worth opening.
    C: later construct and ground one concrete local test.

Read the four separate input parts: current_task, current_initial_state,
current_trajectory, and pre_update_established_memories. The current completed
trajectory is the incumbent realization that you are diagnosing. The memory is
only what was established before that trajectory.

Do not propose, name, ground, verify, or execute a concrete alternative. Do not
require evidence that a concrete alternative already exists. C will synthesize
and ground an alternative only after B returns OPEN. In particular, OPEN means
only that the incumbent comparison is worth asking C to instantiate; it does
not mean that B has proved a replacement is legal or executable.

Keep these distinctions explicit:

* A successful incumbent establishes feasibility under its observed scope, not
  comparative superiority or default status.
* An alternative being absent from memory is not evidence that the comparison
  is resolved.

Make three short, explicit judgments:

1. Identify a local incumbent behavior in the completed trajectory, if one is a
   meaningful comparison target. Describe its local function rather than
   restating the whole task.
2. Decide whether the supplied history establishes only that this behavior
   works, or contains comparative evidence that actually closes its status as
   the preferred/default realization.
3. Decide whether resolving the comparison could materially change future
   policy under the memory's scope. Do not reopen a technically unproven but
   policy-irrelevant behavior.

For an OPEN decision, describe the incumbent's abstract functional contract:
the state available before the local behavior, the local function, the state
that must be available afterward, and constraints that must remain true. This
contract describes what a future test must preserve; it is not a proposed
alternative.

Return exactly one JSON object and no prose or markdown with this schema:
{
  "decision": "OPEN",
  "incumbent_segment": "short description",
  "evidence_status": {
    "feasibility_support": "short statement",
    "comparative_support": "short statement",
    "policy_relevance": "short statement"
  },
  "functional_contract": {
    "available_state": "short statement",
    "local_function": "short statement",
    "required_downstream_state": "short statement",
    "constraints": ["short constraint"]
  },
  "warrant": "short final justification"
}

The value of decision must be exactly "OPEN" or "NONE". The value of
functional_contract must be either the shown object or null.

Use OPEN only when a meaningful local incumbent comparison is unresolved and
answering it could materially change future policy. Use NONE when there is no
meaningful target, the comparative status is already closed, or the question
is not policy-relevant. For NONE, incumbent_segment and functional_contract
may be null, but still fill all three evidence_status statements and the
warrant so the decision can be audited. For OPEN, both incumbent_segment and
functional_contract must be populated.

Do not use an exploration score, threshold, taxonomy, evaluator label, oracle
answer, hidden outcome, or full capability document. These evidence fields are
concise task judgments, not hidden chain-of-thought.
"""


C_SYSTEM = """You are C, a conservative local exploratory-memory synthesizer.

Use only B's OPEN diagnosis, the established memory, and the exact real
ALFWorld action/capability descriptions supplied by the user. Return exactly
one JSON object and no prose or markdown.

Return exactly {"decision":"NONE"} if no grounded local test can be stated.
Otherwise return exactly (shown across lines for readability):
{"decision":"CREATE","scope":"...","hypothesis":"...","guidance":"...",
"grounded_realization":{"actions":["exact ALFWorld action", "..."],
"local_substitution":"...","preserves_downstream_state":"..."},"reason":"..."}

The actions list is the local substitution only, not a complete replacement
plan for the whole task. It must have a clear precondition and postcondition
matching B's contract. Copy exact action strings from the real capability
evidence when possible. Use only the listed ALFWorld primitives and observed
entity IDs. The hypothesis must make clear what comparison the one-shot probe
tests; the guidance must be usable by an actor in the matching future state.
Do not claim that the probe has already produced evidence. Do not use
evaluator labels or oracle actions.
"""


ACTOR_SYSTEM = """You are an ALFWorld actor. Finish the supplied task with one
planned sequence of exact text actions. Use the established memory, and when
an exploratory memory is present, follow it only as a local test while
preserving the task's required downstream state. Return exactly one JSON
object of the form {"actions":["look", "go to ...", "..."]} and no prose.
Use only actions that are admissible or become admissible in the supplied
real task state. Do not mention hidden evaluation information.
"""


def b_messages(public_input: dict) -> list[dict]:
    return model_messages(B_SYSTEM_OPTIMIZED, public_input, user_only=True)


def b_segment_hint_messages(public_input: dict, segment_hint: str) -> list[dict]:
    """Build the one permitted diagnostic prompt with a reviewed segment hint."""

    if not isinstance(segment_hint, str) or not segment_hint.strip():
        raise ValueError("segment_hint must be a non-empty string")
    diagnostic_input = {
        **public_input,
        "candidate_incumbent_segment_hint": segment_hint,
    }
    return model_messages(B_SYSTEM_OPTIMIZED, diagnostic_input, user_only=True)


def b_baseline_messages(public_input: dict) -> list[dict]:
    return model_messages(B_SYSTEM_BASELINE, public_input)


def c_messages(c_input: dict) -> list[dict]:
    return model_messages(C_SYSTEM, c_input, user_only=True)


def actor_messages(actor_input: dict) -> list[dict]:
    return model_messages(ACTOR_SYSTEM, actor_input, user_only=True)


def prompt_json(messages: list[dict]) -> str:
    return json.dumps(messages, ensure_ascii=False, sort_keys=True, indent=2)
