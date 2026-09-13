# AutoManual preparation: reproducibility evidence and admission gates

Historical preparation report. See [the embedding/wiring deliverable](06_embedding_wiring.md)
for the second declared patch, subsequent Skill_Bank dependency installation,
smoke terminal-state repairs and direct-only execution policy. Claims below that
only one patch exists or embedding selection is unapproved are historical.

Date: 2026-09-11. Outcome: **the pinned official text environment runs; Phase 0
has not passed**. No actor, Builder, Formulator, embedding or LLM endpoint ran.
The main adaptive path is stopped at the evaluator-isolation gate described in
[the fixed-source audit](04_automanual_source_audit.md). No real adapter is claimed.

## Source and data

Official origin: https://github.com/minghchen/automanual.git.
HEAD: `aeb17e4a4fe8bb43b9eb390b7b0b94a3ca8b9324`.
Bundled `HEAD:alfworld`: `cc528106f15eaaef06f4900e78c649f9f99a5d06`.
The independently recorded ALFWorld reference HEAD was **not** installed or used.
The bundled requirements SHA-256 is
`9a277e74a0bece56afa436f79704d35e56d1f1497fa5cad6449b3de3e2d70b79`.

The existing setup command fetched and verified the pristine origin/HEAD/tree and
clean worktree before modification. The only source change is the declared
`001-lazy-text-imports.patch`; its SHA-256 is
`3c98a4bd2c164c9c60481b8a1b6c089528821a4c77e24f743d66bd12357d7512`.
Pristine verification still rejects it, intentionally. `--check-patched` checks
the same origin/HEAD/bundled tree, no staged/untracked changes, and an exact binary
diff match. `--apply-patches` first verifies pristine state, checks applicability,
applies that file and verifies the declared result. Existing unrelated changes
are refused, never reset or cleaned. Reverse applicability was also checked,
without reversing the working patch.

The commit already contains `alfworld/downloaded/json_2.1.1` and logic; no separate
dataset download was needed. The diagnostic task is the train task:

```text
pick_and_place_simple-AlarmClock-None-Desk-314/trial_T20190908_185938_027368
```

`configs/automanual_alfworld/task_data_sha256.json` inventories its game, initial
PDDL, trajectory JSON and two logic files. The runner checks this inventory before
execution and unchanged bytes afterwards. This is not a full benchmark inventory.
Cached `solvable: true` is required; no expert solvability rollout or game regeneration
is allowed by this smoke. Native train-mode expert computation remains present
inside TextWorld but its plan is neither used to choose actions nor exported.

## Environment and actual installation history

Infrastructure: reused `memory-infra`, Python 3.10.20, Ruff 0.12.0. Its dependencies
were not changed. Upstream: created `memory-automanual`, Python **3.9.16**.
Interpreter identities are `memory-infra/bin/python` and
`memory-automanual/bin/python` relative to the local conda environments directory.
Platform: Linux x86_64, WSL2 kernel 6.18.33.2, glibc 2.43. Conda 26.3.2.
No base/unrelated environment installations or deletions occurred.

Commands actually used, in order (failed attempts are deliberately retained):

```bash
conda run -n memory-infra python scripts/setup/automanual.py --fetch
conda create -y -n memory-automanual python=3.9.16
conda run -n memory-automanual bash scripts/setup/install_automanual.sh --install
# Failed: downward metadata required CMake.
conda run -n memory-automanual python -m pip install cmake==3.27.9 setuptools==65.5.0 wheel==0.38.4 pip==24.0
# Declared lazy-import patch applied and verified, then text-only installation attempted.
conda install -y -n memory-automanual gcc_linux-64=11.2.0 gxx_linux-64=11.2.0
conda run -n memory-automanual bash scripts/setup/install_automanual.sh --install-text
conda run -n memory-automanual python -m pip check
```

Text-only attempts exposed and resolved three concrete compatibility problems:

| Problem | Necessary change | Mechanism impact |
| --- | --- | --- |
| GCC 15 rejects old downward `optional.hh:2261` dependent `construct` reference | Use conda GCC/G++ 11.2.0, CMake 3.27.9 | Build tool selection only; no planner source rewrite |
| Unbounded spaCy 3.8.16 source metadata build lacked cymem/murmurhash `.pxd` files | Resolve compatible spaCy 3.7.5 wheel and record dependencies | Transitive text dependency compatibility, no language model weights downloaded |
| TextWorld cheapglk `cgfref.c:111` ignored `mkstemp` return becomes error under `-Werror` | Add `CPPFLAGS=-Wno-error=unused-result` while retaining the warning | Build warning policy only; no C/PDDL logic modification |
| Importing text environment eagerly imports Thor/Hybrid and vision dependencies | Lazy-load those two optional classes in the sole source patch | Text `AlfredTWEnv` import and implementation unchanged; Thor/Hybrid runtime untested |

Successful logs remain ignored under `.runtime/automanual-setup/text-uUf98uiM/`;
earlier `text-WmpEkfXO`, `text-Dl3fIGWX`, `text-3nHqLPag` retain the three failed
attempts. Original full setup failure is in `source-dependencies.log`. Raw logs
are local diagnostics, not portable committed records. The full upstream
requirements were **not** successfully installed; text-only `pip check` returned
`No broken requirements found.` Bundled ALFWorld is imported from source, not a
separately installed distribution, so pip check does not certify its full extras.

Resolved versions include TextWorld 1.3.2, fast-downward 20.6, Gym 0.15.4, NumPy
1.23.5, spaCy 3.7.5, pip 24.0, setuptools 65.5.0, wheel 0.38.4. The existing two
fixed source ZIPs are used, not PyPI substitutes. Installed direct-URL metadata
confirmed the source hashes now included in the setup command:

- TextWorld `634f9f91fec732a79dd9e7623675301a53f06623`, archive SHA-256
  `bc404d7c193b30fde8d9c2b4af3a9ee74d3b6bf2cc69fc5418814491a472ddd5`.
- downward `84769171b9d965bf5739eaa7cf6604b0d9697534`, archive SHA-256
  `2294c8d5e44fc8fd37d00a8956d0dab3c0dd4bed347f31934eef96245f0dd9c7`.

For a fresh Linux environment, use the sanitized resolved conda definition and
text constraints, without polluting infrastructure:

```bash
conda env create -f configs/automanual_alfworld/environment-text-linux-64.yml
conda run -n memory-infra python scripts/setup/automanual.py --fetch
conda run -n memory-infra python scripts/setup/automanual.py --apply-patches
conda run -n memory-automanual bash scripts/setup/install_automanual.sh --install-text
```

For the existing declared-patch checkout use `--check-patched`, not `--fetch` or
`--apply-patches`. These records pin resolved versions/builds and public source
archives; they are not a claim of byte-identical compiled wheels, cross-platform
support, a full LLM-stack lock, or a second clean-room reinstallation test.

## Real zero-LLM environment evidence

Default `python scripts/smoke/automanual_env.py` is plan-only. Explicit opt-in:

```bash
conda run -n memory-infra python scripts/smoke/automanual_env.py --execute
```

This succeeded with seed 42, two fresh environments and four actions each:
`look`, `inventory`, `go to desk_1`, `look`. Navigation is selected from the visible
initial text. Every step uses the official raw environment and its evaluator;
all eight results were reward 0.0, won false, done false. The task was not solved
and no success result was fabricated. Initial observation, step text, actions,
admissible-command lists and evaluator results matched across the two replays.
Raw observations include the public task instruction. Full engine-state equality,
successful task replay, other actions/tasks and remote-model determinism remain
unverified. The source audit identifies the exact evaluator implementation.

Each invocation writes a unique ignored `artifacts/automanual-env-*/` directory.
`environment_diagnostic.json` records provenance, data checksums, replay scope,
and round-trip results; generic task artifacts retain unavailable memory/update
boundaries, because no memory loop ran. Calls and cost are actual zero, memory
growth unavailable. The small `environment_smoke_evidence.json` is a portable
diagnostic evidence extract, not a scientific run or a replacement for raw logs.

The Python 3.10 parent launched the Python 3.9.16 worker and verified exact UTF-8
JSON equality for actual environment events, both complete published native
memory JSON files as raw strings, and a separate Chinese/multiline/nested probe.
Published learned memory was used only for serialization and never injected or
used to initialize an experiment. This validates this JSON boundary, not full
memory-loop integration or hidden simulator-state serialization.

The worker does not import the upstream LLM runner; a network audit guard blocks
Internet socket connections and the child inherits only operational environment
variables. No `.env` is read. This is not a sandbox for future model-generated
Python: generated-code containment remains a separate blocker. Timeouts terminate
only the worker's process group and preserve already emitted JSON events; abrupt
parent death or filesystem errors cannot guarantee complete artifacts.

Final opt-in run: `artifacts/automanual-env-c59079930e7a`, exit 0. The earlier
successful `automanual-env-74892c81ca9a` was preserved. The final run repeated the
data check and exact cross-version round trip after the last smoke-code changes.

## Admission decision, public model docs and single-task proposal

The official memory loop uses evaluator-derived `won` in Worker feedback,
success/reflection selection, skills and Builder prompts. Removing it changes
memory formation. Main no-GT admission is therefore **blocked**, not patched
around. Generated Python also has access to environment internals/files. The
[source audit](04_automanual_source_audit.md) lists paths, functions, lines, all
roles, embedding calls, unbounded merge iterations and artifact capture points.

The current single-updater artifact schema needs ordered full-state update
intervals before a faithful adapter can be written. Capturing only the last merge
or equating retrieved memory with full updater state would lose evidence. No
provider or logging patch has yet been applied; the only replayable patch is
dependency-import compatibility. Original memory algorithms remain unchanged.

Public DeepSeek documentation checked on **2026-09-11**, without credentials:
[chat completion](https://api-docs.deepseek.com/api/create-chat-completion/) and
[pricing](https://api-docs.deepseek.com/quick_start/pricing/).
The chat schema lists `deepseek-flash`; the pricing footnote explicitly says the
legacy `deepseek-v4-flash` ID is accepted but served by DeepSeek-V4.1-Flash. The
requested project ID remains unchanged; stable naming is not stable backend
identity. Non-thinking is `thinking: {type: disabled}`, temperature 0, function
tools are documented, context is 1M and maximum output 393216 tokens. This is
documentation verification, **not actual API or Assistants compatibility**.

Documented Flash peak USD/million tokens: cache hit 0.006, cache miss 0.30, output
1.20; off-peak 0.003/0.15/0.60. Peak is weekdays 01–04 and 06–10 UTC. Details are
recorded in `provider_documentation.json`. Existing telemetry's 0.44/1.32 planning
rates remain labelled estimates, not current invoices. Rates/backend must be
rechecked immediately before any authorized paid call.

`phase0_plan.json` pins the same task/seed and required model settings. Proposed
future command shape (entry point intentionally **does not exist**, not executable
until the listed gates are reviewed and implemented):

```text
conda run -n memory-infra python scripts/run/automanual_phase0.py \
  --plan configs/automanual_alfworld/phase0_plan.json --execute-one-task
```

Initial memory would be official init_rules plus an empty skill bank, not published
learned artifacts. Use the official chat path with reviewed transport interception,
not an invented Assistants emulation. Budget covers 3 Planner, 1 conclusion or
reflection, 1 optional classifier, 1 Builder, at most 3 merge generations, 1
compatibility probe, plus 2 extra transport retries: **12 attempts total**, output
cap 2000 each. Formulator is outside this building task. Stop, do not truncate or
rewrite rules, if merging still exceeds 12 rules after 3 calls.

Until a correct input bound is validated, reserve 1,048,576 input tokens per
attempt: 12,582,912 input + 24,000 output. At the existing conservative planning
rates the bound is $5.56816128; proposed hard cap **$6 is not authorization**.
A hypothetical 150k input/20k output run is $0.0924 at those rates, not a measured
forecast. Disable hidden SDK retries or instrument every transport attempt.
Embedding costs are not silently budgeted as chat: nonempty skill-bank use needs
a faithful approved embedding policy before it can proceed.

Before paid execution: resolve native success-feedback protocol conflict; isolate
generated Python; implement/review provider-only patch and ordered instrumentation;
install/audit remaining LLM dependencies and SDK retries; decide embedding policy;
acknowledge backend migration; approve diagnostic vs main status and budget.
Abort on unknown usage/interruption, hidden-input leakage, source/data/model drift,
reservation failure, 50-action cap or timeout. None of these gates is waived by
the successful environment smoke. There was no five-task calibration, mining,
H1–H4 execution, or Phase 0 completion.

## Validation record

In `memory-infra`: the original 55 tests plus 13 preparation regressions cover
pin/patch checks, default plan safety, secret-free subprocess environment, network
guard, Unicode JSON, timeout partial output and log suppression. Default tests
never load the upstream environment, contact an API or read real credentials.

```bash
conda run -n memory-infra env PYTHONPATH=src python -m unittest discover -s tests -v
conda run -n memory-infra ruff check src tests scripts
conda run -n memory-infra ruff format --check src tests scripts
conda run -n memory-infra python -m compileall -q src tests scripts
conda run -n memory-infra python scripts/smoke/offline.py
conda run -n memory-infra python scripts/setup/automanual.py
conda run -n memory-infra bash scripts/setup/install_automanual.sh
conda run -n memory-infra python scripts/smoke/automanual_env.py
bash -n scripts/setup/install_automanual.sh
git diff --check
```

Real model API and embedding calls: **0**. API cost: **$0**. No credential-bearing
file, runtime environment state or vendored upstream is included in changes. No
Git commit was created. Remaining unverified boundaries are explicitly listed
above; environment evidence is not evidence for any scientific hypothesis.

Results: **68 tests passed**; Ruff check passed; format check passed for 16 Python
files; compileall, offline fake smoke, both setup plan modes, environment plan,
shell syntax and diff whitespace checks passed. The final fake smoke wrote
`artifacts/offline-1c4c749bff37/fake_fixture/0_fixture`. Declared patch validation
and upstream `pip check` also passed. Shared schema remains 1.1; only this separate
environment diagnostic adds a sidecar JSON file. Multi-updater support is a
documented future requirement, not an incompatible schema change in this turn.
