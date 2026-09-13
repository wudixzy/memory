"""Opt-in official Agent/InteractEnv contract check with synthetic hidden sentinels."""

import argparse
import inspect
import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def execute():
    sys.path.insert(0, str(ROOT / "third_party/automanual/automanual_alfworld"))
    sys.path.insert(0, str(Path(__file__).parent))
    import env_history
    from automanual_env import source_check
    from env_history import Agent, InteractEnv

    from memory_validation.sandbox import CodeSandbox

    source = source_check()

    class SyntheticRawEnvironment:
        steps = 0

        def step(self, actions):
            self.steps += 1
            terminal = self.steps == 2
            return (
                ["Synthetic ordinary observation"],
                [987654],
                [terminal],
                {
                    "won": [terminal],
                    "admissible_commands": [["SYNTHETIC_ADMISSIBLE_SENTINEL"]],
                    "expert_plan": [["SYNTHETIC_EXPERT_SENTINEL"]],
                    "hidden_state": ["SYNTHETIC_HIDDEN_SENTINEL"],
                },
            )

    env = InteractEnv(
        SyntheticRawEnvironment(),
        0,
        "fixture-task",
        0,
        "Synthetic room\nYour task is to: synthetic task.",
    )
    agent = Agent(env)
    first = agent.observation("look()")
    first_report = agent.report()
    assert "Succeed:" not in first_report
    assert env.reward is False
    second = agent.observation("inventory()")
    terminal_report = agent.report()
    assert terminal_report.count("Succeed: True") == 1
    assert env.reward is True
    assert agent.observation("look()") == "Done."
    assert "Succeed:" not in agent.report()  # no extra success polling feedback
    visible = "\n".join((first, first_report, second, terminal_report))
    for marker in (
        "987654",
        "SYNTHETIC_ADMISSIBLE_SENTINEL",
        "SYNTHETIC_EXPERT_SENTINEL",
        "SYNTHETIC_HIDDEN_SENTINEL",
    ):
        assert marker not in visible
    helper_calls = []

    def helper_rpc(event):
        method = event.get("method")
        if event.get("target") != "agent" or method not in ("go_to", "open", "put_in_or_on"):
            raise ValueError("helper_capability_denied")
        helper_calls.append(method)
        return "closed" if method == "go_to" else "synthetic_1"

    with CodeSandbox(helper_rpc) as guest:
        guest.execute(
            "import re\n"
            + "\n".join(
                inspect.getsource(getattr(env_history, name))
                for name in ("get_object_with_id", "find_object", "go_to_put_object")
            )
        )
        guest.execute(
            "found = find_object(agent, ['fixture_1'], 'synthetic')\n"
            "assert found == (['synthetic_1'], 'fixture_1')\n"
            "assert go_to_put_object(agent, 'fixture_2', 'synthetic_1') == 'synthetic_1'"
        )
    assert helper_calls == ["go_to", "open", "go_to", "open", "put_in_or_on"]
    source_check()
    return {
        "synthetic": True,
        "diagnostic": True,
        "scientific_evidence": False,
        "source": source,
        "normal_observation": first,
        "nonterminal_report": first_report,
        "terminal_report": terminal_report,
        "hidden_sentinel_isolation": True,
        "raw_numeric_reward_discarded": True,
        "won_consumed_at_native_boundary": True,
        "official_helpers_in_os_guest": helper_calls,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if args.execute:
        result = execute()
        directory = ROOT / "artifacts" / ("feedback-contract-" + uuid.uuid4().hex[:12])
        directory.mkdir(exist_ok=False)
        (directory / "feedback.json").write_text(
            json.dumps(result, ensure_ascii=False), encoding="utf-8"
        )
        print(
            json.dumps({"status": "completed", "artifacts": str(directory), "real_model_calls": 0})
        )
    else:
        print(json.dumps({"mode": "plan_only", "real_model_calls": 0}))


if __name__ == "__main__":
    main()
