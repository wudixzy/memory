"""Behavior-first AppWorld candidate mining (`docs/31`), isolated from ACE.

Modules and their sides of the isolation boundary:

* `measure` - pure standard-library measurement over persisted artifacts.
* `boundary` - the research-side / adaptive-loop import firewall.
* `selection`, `cards`, `candidates` - research-side only. They must never be
  importable from the actor/memory-updater path.
* `corpus` - orchestrator-side driver for the registered ACE online/no-GT loop.
  It is the only module here that hands anything to the runtime, and what it
  hands over is a task id, the exact `K0` checkpoint and a transport.
"""

BEHAVIOR_STAGE = "bf1-behavior-first-corpus-v1"
