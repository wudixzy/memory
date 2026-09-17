# Coding-agent handoff: paired-state reproducibility + evaluation transition

You are starting without assuming a local checkout.

Repository:

```text
https://github.com/wudixzy/memory.git
```

Target branch:

```text
exp/minimal-exploratory-memory-validation
```

Do not work on `main`.

Bootstrap:

```bash
git clone https://github.com/wudixzy/memory.git
cd memory
git fetch origin
git switch exp/minimal-exploratory-memory-validation
```

If needed:

```bash
git switch -c exp/minimal-exploratory-memory-validation \
  --track origin/exp/minimal-exploratory-memory-validation
```

Verify:

```bash
git status
git branch --show-current
git log -5 --oneline
```

If clone/fetch/push authentication fails, report the exact failure. Do not create a replacement repository.

---

## Read first

Read in this order:

1. `AGENTS.md`
2. `docs/58_evaluation_readiness_transition_plan.md`
3. `docs/57_action_index_and_chinese_review_results.md`
4. `docs/human_review/README_zh.md`
5. `experiments/exploratory_memory_mvp/alfworld_carrier.py`
6. `experiments/exploratory_memory_mvp/run_online_pair.py`
7. `experiments/exploratory_memory_mvp/run_transfer_pair.py`
8. focused MVP tests

The current method is frozen.

Do not redesign B, C, H, A, Functional Contract semantics, probe runtime state, action-index selection, or the online/offline split.

The current architecture is:

```text
OFFLINE / BETWEEN EPISODES
trajectory/evidence
-> Stage 1 later in full system (still bypassed here)
-> A reconciliation
-> B unresolved-comparison diagnosis
-> C exploratory-memory synthesis
-> consolidation/index refresh

ONLINE / LIGHTWEIGHT
memory retrieval/activation
-> target-time grounding
-> stepwise actor
-> mechanical runtime bookkeeping
-> environment/tool execution
-> fact/evidence logging
```

Principle:

```text
Online writes facts; offline writes knowledge.
```

---

# Phase 1 — Audit ALFWorld reset determinism with NO model calls

The previous harness checked equality of two preflight `reset_task()` calls, then discarded them and created fresh `StepwiseTask` instances for actual E0/E1 execution.

That is not a valid pairing proof once reset variance exists.

Your first task is therefore infrastructure-only.

## 1. Build a reset audit

Use at least:

```text
Apple/Microwave target:
pick_clean_then_place_in_recep-Apple-None-Microwave-14/
trial_T20190909_120203_117379

plus one simple pick-and-place task already used by the MVP
```

For each task, instantiate the real carrier repeatedly under the same nominal seed, with no LLM/model calls.

A useful audit count is 10 resets per task.

Persist per reset:

```text
task_id
requested seed
game/task file identity
exact initial observation
ordered initial admissible_actions
public metadata available from the carrier
canonical initial-public-state fingerprint/hash
```

Do not expose hidden benchmark/evaluator answers to any future model payload.

Produce a compact table showing how many unique fingerprints occur.

## 2. Inspect the pinned carrier implementation

Trace the vendored/pinned ALFWorld/TextWorld initialization path sufficiently to identify what controls:

```text
game selection/loading
object placement/state
entity/object numbering
reset RNG
```

Current code already calls:

```text
random.seed(seed)
np.random.seed(seed)
env.seed(seed)
```

Do not assume that is sufficient merely because the code contains those calls.

Document what actually explains the observed variance if you can establish it.

Do not use web research unless repository/vendor code is insufficient and a specific upstream behavior must be verified.

## 3. Classify the variance

Try to distinguish:

```text
A. cosmetic/entity-number variation only
B. same public state but different hidden world state
C. truly different object/layout/world state
```

The Apple review already suggests meaningful object-location variation; verify this mechanically rather than assuming it.

No paid model calls should occur in Phase 1.

---

# Phase 2 — Establish a valid actual-execution pairing mechanism

Choose the least invasive valid mechanism supported by the pinned carrier.

Priority order:

## Option A — deterministic initialization fix

If a missing seed or initialization-order issue exists, fix it.

Acceptance evidence:

```text
repeated same task + same seed
-> same execution initial state/fingerprint
```

across the audit repetitions.

## Option B — state/environment clone or snapshot

If TextWorld/ALFWorld exposes a legitimate copy/clone/snapshot mechanism, create one base episode state and derive both actual E0 and actual E1 executions from exact copies.

Do not invent a fake semantic replay layer.

## Option C — stable replayable episode specification

If a stable underlying game/state identifier can reconstruct the same world state, persist that spec and use it for both conditions.

## If none is valid

STOP paired causal evaluation and write a carrier blocker.

Do not rejection-sample outcomes.

Do not repeatedly reset until E0 and E1 happen to produce favorable behavior.

Do not claim that same task ID / seed / instruction proves same hidden state if it does not.

---

# Phase 3 — Refactor the paired runner so the verified state is ACTUALLY executed

The current scientific paired path must no longer do:

```text
preflight reset E0
preflight reset E1
compare
throw away
new actual E0
new actual E1
```

The actual execution episodes themselves must carry the pairing proof.

Refactor minimally.

A good artifact is:

```json
{
  "pairing_mode": "deterministic_seed | cloned_state | replayable_episode_spec",
  "task_id": "...",
  "requested_seed": 42,
  "game_identity": "...",
  "e0_initial_fingerprint": "...",
  "e1_initial_fingerprint": "...",
  "public_initial_match": true,
  "underlying_state_match_evidence": "..."
}
```

Save this beside every scientific paired run.

Do not pass pairing metadata to the actor.

Keep the action-index actor interface unchanged.

Keep `probe_runtime_state` mechanical.

Keep H lifecycle unchanged.

---

# Phase 4 — Tiny post-fix pairing sanity only

After the actual pairing invariant is valid, rerun only the existing Apple/Microwave setup.

Do not change:

```text
source H
target task
actor prompt semantics
qwen3.8-flash
thinking=false
temperature=0
step cap
action-index harness
probe_runtime_state
```

Run only:

```text
3 ACTUALLY PAIRED E0/E1 repetitions
```

Each repetition must include a valid `pairing_proof` artifact.

Record:

```text
pairing proof status
E0 won / steps
E1 won / steps
all action indices valid?
H activated?
EVIDENCE_OBTAINED / probe-ready?
H removed?
semantic actor failure if task failed despite legal action indices
```

This remains infrastructure sanity, not a performance experiment.

Do not tune H based on these three pairs.

---

# Phase 5 — Tests required

Add focused tests for at least:

1. reset-audit fingerprints are canonical and deterministic for identical input values;
2. scientific paired runner does not rely on discarded preflight resets;
3. actual E0/E1 initial execution states are the states represented by `pairing_proof`;
4. pairing proof is model-invisible;
5. failure to establish a valid pair blocks the causal paired path;
6. action-index semantics remain unchanged;
7. invalid index handling remains unchanged;
8. `probe_runtime_state` remains mechanical;
9. H active/consumed/runtime lifecycle remains unchanged;
10. A remains E1-only;
11. evaluator isolation remains intact;
12. failure artifacts remain auditable.

Do not add a semantic planner or fallback controller to make the tests pass.

---

# Phase 6 — Produce a pairing infrastructure result memo

Add:

```text
docs/60_pairing_infrastructure_validation_results.md
```

Include:

## Reset audit

```text
task
nominal seed
number of resets
unique public fingerprints
observed world/layout/object variance
identified RNG/state cause if known
```

## Pairing mechanism

```text
which option was implemented
why it is valid
what evidence proves actual E0/E1 state equality
```

or, if blocked:

```text
why strict pairing is unsupported by this carrier/harness
what claims must therefore be avoided
```

## Tiny Apple sanity

Only if pairing was fixed:

```text
3 paired runs
E0/E1 results
pairing proof
actor semantic failures
```

Do not claim method effectiveness from these runs.

---

# Phase 7 — Draft the paper-level evaluation specification

Do not launch broad evaluation yet.

Create:

```text
docs/61_paper_level_evaluation_design.md
```

This document should synthesize the current project history and specify the next experimental program.

## Required section A — Scientific questions

At minimum:

```text
Does targeted history-derived exploratory memory improve future behavior?
When does it help or hurt?
Does it outperform generic exploration?
What is the performance/cost tradeoff?
Can evidence be conservatively absorbed into persistent memory?
```

## Required section B — Core conditions

Specify:

```text
C0 no memory
C1 retrospective established memory only
C2 retrospective memory + generic exploration
C3 retrospective + targeted exploratory memory (ours)
```

Explain why:

```text
C3 vs C2
```

is the central contribution test.

Do not accidentally give C2 the B/C-derived targeted hypothesis.

## Required section C — Metrics hierarchy

Separate:

### End-to-end

```text
task success / reward
solution quality
steps/tool calls
tokens/cost
latency if relevant
```

### Mechanism

```text
B OPEN rate
B precision/recall on labelled audit subset
C CREATE / usable-probe rate
H retrieval/activation rate
incremental behavioral effect
productive-evidence rate
positive/negative evidence frequency
probe termination/recovery
downstream completion
```

### Memory evolution

```text
A update rate
evidence-supported update rate
over-generalization
under-update
resolved-question reopening
memory growth/cost
later-task benefit
```

## Required section D — Actor reliability policy

Specify that the main actor backbone must have sufficiently reliable base execution.

Action-index / structured action selection should be retained when the carrier supports it.

Separate:

```text
transport/action-interface failure
semantic actor execution failure
memory retrieval failure
H authority/grounding failure
probe-control failure
A/memory-update failure
```

Qwen3.8-Flash may remain a weak-model robustness setting, but do not make the main conclusion depend on it if base execution is unstable.

## Required section E — Benchmark admission criteria

Use the project's previous AppWorld/ACE and ALFWorld lessons.

Require candidates to offer as much as possible:

```text
sequential/repeated task structure
memory can actually alter future policy
alternative local realizations
success/quality/cost signal
trajectory/tool-call observability
replayability or defensible randomized protocol
sufficient base actor reliability
manageable run/API cost
```

Do not select a benchmark only because it is popular.

If existing repository documents already discuss candidate benchmark/baseline pairs, reference them and update the reasoning rather than starting from zero.

Do not perform a fresh large literature review in this coding cycle unless explicitly necessary.

## Required section F — Online/offline cost accounting

State the architecture explicitly:

```text
ONLINE:
retrieval / small rerank
memory/H context tokens
normal stepwise actor calls
mechanical runtime bookkeeping

OFFLINE:
Stage 1
A
B
C
consolidation/index refresh
```

Report online task-time overhead separately from offline memory-maintenance cost.

## Required section G — Preliminary experiment matrix

Provide a practical matrix such as:

```text
benchmark × C0/C1/C2/C3 × actor backbone × repetitions
```

but do not launch it.

Estimate rough run counts, model-call counts, and cost categories using current telemetry where possible.

Clearly mark assumptions and unknowns.

## Required section H — What remains intentionally deferred

Examples:

```text
production Stage 1 implementation
automatic H retrieval tuning
graph memory
large-scale memory consolidation engineering
extra ablations beyond the core comparison
```

---

# Phase 8 — Update branch-level AGENTS.md only if necessary

If implementation work changes the active branch priority, keep `AGENTS.md` aligned with this transition:

```text
pairing validity first
human review gate
then paper-level evaluation implementation
```

Do not rewrite project history unnecessarily.

---

# Stop rule

After:

```text
pairing audit/fix or explicit blocker
+ tiny pairing sanity if possible
+ docs/60 result memo
+ docs/61 evaluation design
```

STOP.

Do not begin broad evaluation runs.

Do not implement retrieval or Stage 1.

Do not redesign B/C/H/A.

Return the artifacts for researcher review.

---

# Verification

Before committing:

```bash
git status
git diff
git diff --check
```

Run:

```text
focused MVP tests
Ruff
compile checks
```

Do not commit `.env`, API keys, credentials, runtime benchmark dumps, or large ignored artifacts.

Commit and push to:

```text
exp/minimal-exploratory-memory-validation
```

Suggested commit message:

```text
exp: validate paired state and draft evaluation design
```

Do not force-push.

At completion report:

```text
final commit SHA
changed files
tests/checks
reset determinism result
selected pairing mechanism or blocker
post-fix Apple pairing sanity
paper-level evaluation design path
remaining scientific/infrastructure uncertainty
```
