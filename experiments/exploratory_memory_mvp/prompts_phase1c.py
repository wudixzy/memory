"""Phase 1C-only additions to the frozen Phase 1B prompt contracts."""

from __future__ import annotations

from .common import model_messages
from .prompts import C_SYSTEM

HISTORY_RETRIEVAL_SYSTEM = """You are an offline exploration-history retriever.

This call happens only after B has diagnosed an OPEN Functional Contract. Select
zero to three records from the supplied compact archive that are semantically
relevant to the current contract. Return only IDs that are actually listed.
Do not infer hidden outcomes, treat an attempted experiment as true or false,
or expose raw trajectories/evidence. The archive says only that a future-facing
exploration was actually activated in a previous task. It is supplied to help C
avoid redundant hypotheses while allowing justified retests when scope,
realization, capability, or established knowledge materially differs.

Return exactly one JSON object:
{"decision":"NONE","exploration_ids":[]}
or
{"decision":"SELECT","exploration_ids":["<one to three listed ids>"]}
"""

PHASE1C_C_APPENDIX = """

Phase 1C additionally supplies relevant_exploration_history. These are compact
offline summaries of experiments that were actually activated, not proof that
their hypotheses were correct or incorrect. Use them semantically:

* return NONE when the proposed experiment would merely repeat an equivalent
  tested hypothesis in a comparable scope;
* CREATE when the current scope, realization, capability context, or
  Established Memory makes the proposal materially different;
* a justified retest is allowed when the current unresolved question differs
  or the earlier test was not discriminative.

Do not copy exploration IDs, source provenance, source entity IDs, or old exact
actions into future-facing H. Do not output a semantic archive label.
"""


def history_retrieval_messages(retrieval_input: dict) -> list[dict[str, str]]:
    return model_messages(HISTORY_RETRIEVAL_SYSTEM, retrieval_input, user_only=True)


def phase1c_c_messages(c_input: dict) -> list[dict[str, str]]:
    return model_messages(C_SYSTEM + PHASE1C_C_APPENDIX, c_input, user_only=True)
