"""Config-driven C1/C2/C3 Frozen-history runner scaffolding for Phase 1.

Unique target task is the primary scientific unit; repetition is nested metadata.
Enforces K* identicality, one-shot H lifecycle, action-index interface,
and actual-execution pairing proof across conditions.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable

_EXPERIMENTS = Path(__file__).resolve().parents[1]
if str(_EXPERIMENTS) not in sys.path:
    sys.path.insert(0, str(_EXPERIMENTS))

from exploratory_memory_mvp.alfworld_carrier import (  # noqa: E402
    PairingError,
    StepwiseTask,
    build_pairing_proof,
)
from exploratory_memory_mvp.c2_generic import (  # noqa: E402
    get_fair_c2_exploratory_memory,
)
from exploratory_memory_mvp.common import (  # noqa: E402
    DEFAULT_ENV_FILE,
    build_actor_base_input,
    make_run_directory,
    safe_error,
    write_json,
)
from exploratory_memory_mvp.k_star import (  # noqa: E402
    compute_k_star_digest,
    get_phase1_k_star,
)
from exploratory_memory_mvp.phase1_config import (  # noqa: E402
    PHASE1_MODEL,
    PHASE1_PROVIDER,
    Phase1RunConfig,
    validate_phase1_config,
)
from exploratory_memory_mvp.run_online_pair import _run_actor_condition  # noqa: E402


def build_phase1_condition_configs(
    *,
    target_id: str,
    target_seed: int,
    repetition_index: int,
    output_dir: Path,
    c3_exploratory_memory: dict[str, Any],
    c2_exploratory_memory: dict[str, Any] | None = None,
    k_star: list[dict[str, Any]] | None = None,
    target_registry_sha256: str | None = None,
    step_cap: int = 32,
    allow_network: bool = False,
) -> dict[str, Phase1RunConfig]:
    """Build the three frozen-history configs without creating a model client."""

    if k_star is None:
        k_star = get_phase1_k_star()
    if c2_exploratory_memory is None:
        c2_exploratory_memory = get_fair_c2_exploratory_memory()
    common = {
        "target_id": target_id,
        "target_seed": target_seed,
        "repetition_index": repetition_index,
        "output_dir": output_dir,
        "k_star": k_star,
        "step_cap": step_cap,
        "target_registry_sha256": target_registry_sha256,
        "allow_network": allow_network,
    }
    return {
        "C1": Phase1RunConfig(condition="C1", exploratory_memory=None, **common),
        "C2": Phase1RunConfig(
            condition="C2", exploratory_memory=c2_exploratory_memory, **common
        ),
        "C3": Phase1RunConfig(
            condition="C3", exploratory_memory=c3_exploratory_memory, **common
        ),
    }


def run_phase1_episode(
    config: Phase1RunConfig,
    *,
    transport_factory: Callable | None = None,
    env_file: Path = DEFAULT_ENV_FILE,
    episode: StepwiseTask | None = None,
    pairing_proof: dict | None = None,
    pairing_role: str | None = None,
) -> dict[str, Any]:
    """Execute one Phase 1 episode under the specified config-driven condition."""
    validate_phase1_config(config)

    config.output_dir.mkdir(parents=True, exist_ok=True)

    if episode is None:
        episode = StepwiseTask(config.target_id, config.target_seed)

    initial_state = {
        "observation": episode.state["observation"],
        "admissible_actions": list(episode.state["admissible_actions"]),
        "won": episode.state.get("won"),
        "done": episode.state.get("done", False),
    }
    b_input = build_actor_base_input(
        task_id=config.target_id,
        seed=config.target_seed,
        initial_state=initial_state,
        established_memories=config.k_star,
    )
    case = {
        "case_id": config.target_id,
        "task_id": config.target_id,
        "seed": config.target_seed,
        "repetition_index": config.repetition_index,
    }
    condition_label = f"{config.condition.lower()}_rep{config.repetition_index:02d}"

    row = _run_actor_condition(
        condition=condition_label,
        b_input=b_input,
        case=case,
        output=config.output_dir,
        exploratory_memory=config.exploratory_memory,
        allow_network=config.allow_network,
        env_file=env_file,
        step_cap=config.step_cap,
        transport_factory=transport_factory,
        explicit_diagnostic=config.explicit_diagnostic,
        episode=episode,
        pairing_proof=pairing_proof,
        pairing_role=pairing_role,
    )

    # Keep each condition's immutable config beside its own artifacts.  The
    # three-arm runner must never overwrite a shared root run_config.json.
    write_json(config.output_dir / condition_label / "run_config.json", config.to_dict())

    summary = {
        "condition": config.condition,
        "target_id": config.target_id,
        "target_seed": config.target_seed,
        "repetition_index": config.repetition_index,
        "k_star_sha256": compute_k_star_digest(config.k_star),
        "status": row.get("status"),
        "won": row.get("execution", {}).get("won", False),
        "actor_steps": row.get("actor_steps", 0),
        "probe_activated": row.get("probe_activated", False),
        "probe_evidence_ready": row.get("probe_evidence_ready", False),
        "probe_stopped_locally": row.get("probe_stopped_locally", False),
        "runtime_guidance_removed": row.get("runtime_guidance_removed", False),
        "artifacts_dir": str(config.output_dir / condition_label),
        "provider": PHASE1_PROVIDER,
        "model": PHASE1_MODEL,
    }
    write_json(config.output_dir / condition_label / "episode_summary.json", summary)
    return summary


def run_phase1_paired_target(
    target_id: str,
    target_seed: int,
    repetition_index: int,
    output_dir: Path,
    *,
    c3_exploratory_memory: dict[str, Any],
    c2_exploratory_memory: dict[str, Any] | None = None,
    k_star: list[dict[str, Any]] | None = None,
    transport_factory: Callable | None = None,
    allow_network: bool = False,
    step_cap: int = 32,
    env_file: Path = DEFAULT_ENV_FILE,
    target_registry_sha256: str | None = None,
) -> dict[str, Any]:
    """Execute a strictly paired C1, C2, and C3 comparison on a single target task.

    The actual execution states of C1, C2, and C3 share the verified replay specification.
    """
    if k_star is None:
        k_star = get_phase1_k_star()
    if c2_exploratory_memory is None:
        c2_exploratory_memory = get_fair_c2_exploratory_memory()

    make_run_directory(output_dir)

    c1_episode = None
    c2_episode = None
    c3_episode = None
    pairing_proofs: dict[str, dict] = {}

    try:
        c1_episode = StepwiseTask(target_id, target_seed)
        c2_episode = StepwiseTask(target_id, target_seed, replay_spec=c1_episode.replay_spec)
        c3_episode = StepwiseTask(target_id, target_seed, replay_spec=c1_episode.replay_spec)

        # Build a proof for each actual intervention arm against C1.  A single
        # C1/C3 proof is not enough to identify the separately-created C2
        # execution episode.
        pairing_proofs = {
            "c1_c2": build_pairing_proof(c1_episode, c2_episode),
            "c1_c3": build_pairing_proof(c1_episode, c3_episode),
        }
        write_json(output_dir / "pairing_proofs.json", pairing_proofs)
        # Preserve the historical singular artifact as the primary C1/C3
        # proof for tooling written before the three-arm runner existed.
        write_json(output_dir / "pairing_proof.json", pairing_proofs["c1_c3"])
        if not all(proof["pairing_valid"] for proof in pairing_proofs.values()):
            raise PairingError(f"Target {target_id} has an invalid condition pairing proof")

        write_json(
            output_dir / "paired_initial_states.json",
            {
                "actual_execution": True,
                "conditions": {
                    "c1": c1_episode.state,
                    "c2": c2_episode.state,
                    "c3": c3_episode.state,
                },
                "fingerprints": {
                    "c1": c1_episode.initial_public_state_fingerprint,
                    "c2": c2_episode.initial_public_state_fingerprint,
                    "c3": c3_episode.initial_public_state_fingerprint,
                },
            },
        )

        c1_pairing_proof = pairing_proofs["c1_c2"]
        c2_pairing_proof = pairing_proofs["c1_c2"]
        c3_pairing_proof = pairing_proofs["c1_c3"]

        configs = build_phase1_condition_configs(
            target_id=target_id,
            target_seed=target_seed,
            repetition_index=repetition_index,
            output_dir=output_dir,
            k_star=k_star,
            c2_exploratory_memory=c2_exploratory_memory,
            c3_exploratory_memory=c3_exploratory_memory,
            step_cap=step_cap,
            allow_network=allow_network,
            target_registry_sha256=target_registry_sha256,
        )
        c1_config = configs["C1"]
        c1_summary = run_phase1_episode(
            c1_config,
            transport_factory=transport_factory,
            env_file=env_file,
            episode=c1_episode,
            pairing_proof=c1_pairing_proof,
            pairing_role="e0",
        )

        c2_config = configs["C2"]
        c2_summary = run_phase1_episode(
            c2_config,
            transport_factory=transport_factory,
            env_file=env_file,
            episode=c2_episode,
            pairing_proof=c2_pairing_proof,
            pairing_role="e1",
        )

        c3_config = configs["C3"]
        c3_summary = run_phase1_episode(
            c3_config,
            transport_factory=transport_factory,
            env_file=env_file,
            episode=c3_episode,
            pairing_proof=c3_pairing_proof,
            pairing_role="e1",
        )

        overall = {
            "target_id": target_id,
            "target_seed": target_seed,
            "repetition_index": repetition_index,
            "pairing_valid": all(
                proof["pairing_valid"] for proof in pairing_proofs.values()
            ),
            "public_initial_match": all(
                proof["public_initial_match"] for proof in pairing_proofs.values()
            ),
            "pairing_proofs": pairing_proofs,
            "c1": c1_summary,
            "c2": c2_summary,
            "c3": c3_summary,
            "artifacts_dir": str(output_dir),
        }
        write_json(output_dir / "target_set_summary.json", overall)
        return overall
    except Exception as error:
        err = safe_error(error)
        write_json(output_dir / "failure.json", err)
        raise
    finally:
        for ep in (c1_episode, c2_episode, c3_episode):
            if ep is not None:
                try:
                    ep.close()
                except Exception:
                    pass
