"""Opt-in official Skill_Bank wiring check; all embeddings are synthetic/offline."""

import argparse
import contextlib
import importlib.util
import io
import json
import os
import socket
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def deny_network(event, args):
    if event == "socket.connect" and args[0].family in (socket.AF_INET, socket.AF_INET6):
        raise RuntimeError("Offline wiring forbids network")


def execute():
    if sys.version_info[:3] != (3, 9, 16):
        raise RuntimeError("Use memory-automanual Python 3.9.16")
    for key in list(os.environ):
        if key.lower().endswith("_proxy"):
            del os.environ[key]
    os.environ.update(NO_PROXY="*", no_proxy="*", LANGCHAIN_TRACING_V2="false")
    sys.addaudithook(deny_network)
    sys.path.insert(0, str(ROOT / "src"))
    from memory_validation.embedding import EmbeddingProvider, langchain_embedding
    from memory_validation.telemetry import UsageTracker

    spec = importlib.util.spec_from_file_location("pin_check", ROOT / "scripts/setup/automanual.py")
    setup = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(setup)
    pin = json.loads(setup.PIN.read_text())
    patches = sorted((ROOT / "configs/automanual_alfworld/patches").glob("*.patch"))
    provenance = setup.verify(ROOT / "third_party/automanual", pin, patches)
    sys.path.insert(0, str(ROOT / "third_party/automanual/automanual_alfworld"))
    from autobuild_utils import Skill_Bank

    requests = []
    events = []

    def transport(payload):
        requests.append(payload)
        # Query deliberately differs from selected key: selection must use FAISS.
        mapping = {
            "fixture_alpha": [1.0, 0.0],
            "fixture_beta": [0.0, 1.0],
            "fixture_query": [0.1, 0.9],
        }
        return {
            "model": payload["model"],
            "usage": {"prompt_tokens": len(payload["input"]) * 3},
            "data": [
                {"index": i, "embedding": mapping[t] + [0.0] * 1022}
                for i, t in reversed(list(enumerate(payload["input"])))
            ],
        }

    usage = UsageTracker(on_event=events.append)
    embedding = langchain_embedding(EmbeddingProvider(transport), usage, synthetic=True)
    directory = ROOT / "artifacts" / ("skill-wiring-" + uuid.uuid4().hex[:12])
    directory.mkdir(parents=True, exist_ok=False)
    bank = Skill_Bank(save_path=str(directory), embedding=embedding)
    bank.add_skill(
        "fixture_alpha", "synthetic alpha task", "合成初态\nalpha", "def alpha():\n    return 1"
    )
    bank.add_skill(
        "fixture_beta", "synthetic beta task", "合成初态\nbeta", "def beta():\n    return 2"
    )
    bank.add_failure("fixture_failed", "synthetic failure", "fixture", "diagnostic failure")
    before = json.loads(json.dumps(bank.skill_dict))
    scope = {}
    with contextlib.redirect_stdout(io.StringIO()):
        output = bank.get_relevant_skill("fixture_query", scope)
    assert "synthetic beta task" in output and "synthetic alpha task" not in output
    assert scope["beta"]() == 2 and "alpha" not in scope
    assert requests[0]["input"] == ["fixture_alpha", "fixture_beta"]
    assert requests[1]["input"] == ["fixture_query"]
    assert bank.skill_dict == before
    assert bank.vectordb.index.d == 1024 and bank.vectordb._normalize_L2 is False
    setup.verify(ROOT / "third_party/automanual", pin, patches)
    report = {
        "status": "completed",
        "synthetic": True,
        "scientific_evidence": False,
        "purpose": "wiring_only_not_quality_or_OpenAI_equivalence",
        "source": provenance,
        "embedding_identity": embedding.identity,
        "skill_fixture": before,
        "returned_skill": output,
        "injected_helpers": ["beta"],
        "distance_strategy": str(bank.vectordb.distance_strategy),
        "normalize_L2": bank.vectordb._normalize_L2,
        "index_dimension": bank.vectordb.index.d,
        "requests": requests,
        "usage": usage.summary(),
        "model_network_calls": 0,
    }
    (directory / "wiring.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": "completed", "synthetic": True, "artifacts": str(directory)}))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not args.execute:
        print(
            json.dumps(
                {
                    "mode": "plan_only",
                    "synthetic": True,
                    "network": False,
                    "environment": "memory-automanual",
                    "model_calls": 0,
                }
            )
        )
        return 0
    return execute()


if __name__ == "__main__":
    raise SystemExit(main())
