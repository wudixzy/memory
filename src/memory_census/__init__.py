"""Offline AppWorld task-family census for the Stage-A strategy-lock-in search.

This package is **research-side** tooling. It reads benchmark internals
(instructions, evaluator ground truth, reference solutions, metadata) to select
candidate task families for `docs/26_strategy_lockin_experiment_plan.md`.

Hard boundaries (enforced by `memory_census.boundary` and its tests):

* it performs no network access and runs no benchmark code;
* it never imports the AppWorld runtime or `memory_validation` ACE runtime;
* everything it produces is *reference-only* evidence. An offline census cannot
  establish K_0 discoverability, memory authority, or a causal B effect, and it
  must never be injected into Generator/Reflector/Curator.
"""

CENSUS_VERSION = "census-v1"

__all__ = ["CENSUS_VERSION"]
