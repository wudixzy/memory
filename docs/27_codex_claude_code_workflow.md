# Codex CLI + Claude Code worker workflow

2026-09-13. This repository uses a two-agent local workflow for the next implementation cycle:

- **Codex CLI**: orchestrator, reviewer, test runner, final integrator, committer/pusher.
- **Claude Code CLI (CC)**: implementation worker, configured to use DeepSeek Flash through DeepSeek's Anthropic-compatible endpoint.

The goal is separation of duties: CC does most coding/analysis work; Codex reads the diff and evidence, tests it, requests revisions when needed, and owns the final repository state.

## 1. Expected local directory layout

Codex is launched from the outer workspace:

```text
/home/coolboy/projects/memory
```

The Git repository is the nested directory:

```text
/home/coolboy/projects/memory/memory
```

Claude Code must run with the **inner Git repository** as its working directory.

Codex may inspect the outer workspace when useful, but all repository reads/writes, tests, commits and pushes for this project must target the inner repository unless the user explicitly changes the layout.

## 2. Current DeepSeek Claude Code configuration

DeepSeek's Anthropic-compatible endpoint is:

```text
https://api.deepseek.com/anthropic
```

For Claude Code, the current model name used by this project is:

```text
deepseek-flash[1m]
```

All Claude Code model roles/subagents are mapped to this same 1M-context Flash model.

The local `.env` inside the Git repository contains:

```text
DEEPSEEK_KEY=...
```

Do **not** copy the key into prompts, tracked files, shell history, logs, Codex messages, or Claude Code transcripts. The wrapper loads it locally and exports only `ANTHROPIC_AUTH_TOKEN` to the Claude Code child process.

The repository must continue to commit only `.env.example`, never `.env`.

## 3. Wrapper command

Use:

```bash
bash /home/coolboy/projects/memory/memory/scripts/agents/run_cc_deepseek.sh [claude arguments...]
```

The wrapper:

1. resolves the inner repository root from its own location;
2. reads `DEEPSEEK_KEY` from the inner repository `.env`;
3. refuses to run if the key or `claude` executable is unavailable;
4. changes directory to the inner repository;
5. configures the DeepSeek Anthropic endpoint and maps all Claude roles to `deepseek-flash[1m]`;
6. invokes `claude` without printing the secret.

For a non-interactive worker task Codex can use Claude Code print mode, for example:

```bash
bash memory/scripts/agents/run_cc_deepseek.sh -p "<implementation task>"
```

when Codex itself is currently at `/home/coolboy/projects/memory`.

Claude Code supports `-p/--print` for non-interactive execution. Codex may pass additional permission/tool flags as appropriate for the reviewed task. Do not blindly use permission-bypass flags.

## 4. Network/sandbox requirement

Claude Code must reach `https://api.deepseek.com`.

If the Codex execution sandbox blocks outbound network access, the nested `claude` command will fail even though the configuration is correct. Codex must distinguish a sandbox/network-policy failure from a DeepSeek/Claude Code configuration failure.

Use a Codex execution mode/approval that permits the reviewed Claude Code invocation to access the DeepSeek endpoint. Do not weaken unrelated filesystem or host protections merely to solve network access.

## 5. Division of responsibilities

### Claude Code worker

CC may:

- inspect the repository and existing reports;
- implement focused analysis/candidate-mining code;
- run local/offline tests;
- run explicitly authorized low-cost experiments within existing budget controls;
- update documentation describing its implementation and results.

CC should not:

- change the scientific question to make a positive result easier;
- hand-write a favorable memory or alter benchmark semantics;
- bypass ground-truth/evaluator isolation;
- silently add a new baseline or large framework;
- commit or push by default;
- expose secrets.

### Codex reviewer/orchestrator

Codex should:

1. pull/update the inner repository and read `AGENTS.md` plus the newest progress/plan docs;
2. define a narrow work package for CC;
3. invoke CC from the inner repository through the wrapper;
4. inspect `git diff`, new artifacts/reports and tests itself;
5. run independent tests/checks where possible;
6. reject or request revision of unsupported scientific claims;
7. invoke CC again with precise review feedback if needed;
8. only after review, commit and push accepted work to the configured upstream;
9. update `AGENTS.md`/relevant docs when durable workflow or scientific priorities change.

Codex is not meant to reimplement everything after CC. Its value here is planning, critical review, scientific boundary checking and final integration.

## 6. Review loop

Recommended loop:

```text
Codex: inspect current state + define task
        |
        v
Claude Code: implement/analyze/test
        |
        v
Codex: review diff + scientific evidence + tests
        |
   revision needed? ---- yes ---> Claude Code revision pass
        |
        no
        v
Codex: final tests -> docs/status update -> commit -> push
```

Keep CC tasks coherent and medium-sized. Prefer one complete candidate-mining deliverable over many tiny prompt/commit cycles.

## 7. Historical first work package

The initial delegated package was the Stage-A AppWorld census from `docs/26_strategy_lockin_experiment_plan.md`. It is now complete in `docs/28_appworld_family_census.md` and produced 26 reserve families.

Do not repeat that census as the main task except to regenerate its ignored machine-readable artifacts when needed.

## 8. Secret handling

Codex may know that `.env` contains `DEEPSEEK_KEY`, but it should not read/print the key unless a local wrapper or purpose-built reviewer process needs to source it. Prefer process-local loading rather than extracting the value into a Codex-visible shell command.

Never run commands such as:

```text
cat .env
env
printenv
set -x
```

in a context whose output is captured into agent logs when secrets may be present.

The CC wrapper disables shell tracing before reading `.env`.

## 9. Final integration discipline

Before Codex commits/pushes:

- inspect `git status` and `git diff`;
- confirm no `.env`, credentials, decrypted benchmark data, raw private artifacts, or large runtime state are staged;
- run relevant tests/lint/format checks, not necessarily the entire historical suite if the change is analysis-only;
- verify claims against actual code/output rather than CC prose;
- preserve negative results and failed gates;
- use `git pull --ff-only`/equivalent safe synchronization before push when remote state may have moved;
- never force-push to make the workflow succeed.

## 10. Model note

For the **coding worker**, the configured Claude Code model is `deepseek-flash[1m]` with `CLAUDE_CODE_EFFORT_LEVEL=max`. This coding-agent setting is independent of the scientific experiment model policy. Scientific experiments remain governed by `AGENTS.md` and their registered configs. Do not silently rewrite historical experiment manifests merely because the Claude Code worker model name changed.

## 11. Current work package — parallel reserve review

The current workflow is defined in `docs/29_parallel_candidate_review_plan.md` and overrides any earlier instruction that Codex or a human manually review only the top few census candidates.

### Phase 1: CC prepares IDs/evidence packets

Ask Claude Code to:

1. regenerate the Stage-A census if the ignored artifacts are unavailable;
2. return all reserve family IDs (currently ~26), their proposed source/target task IDs and candidate-record paths;
3. implement or help implement a bounded packet builder that extracts only the relevant instructions, state differences, reference-route snippets, API-doc excerpts, current B hypotheses, gate outputs and provenance;
4. test packet generation locally;
5. stop without doing the final semantic admission review itself.

### Phase 2: Codex owns the reviewer ensemble

Codex should write a small standalone reviewer script and a fixed prompt/schema, then call DeepSeek Flash concurrently over all reserve packets.

Default review design:

- 2 independent reviews per family;
- all ~26 reserve families, not only the old top-10;
- concurrency around 8-12 unless provider/runtime limits require lower;
- strict JSON output;
- no chain-of-thought requirement;
- one automatic retry for malformed/unsupported output;
- third independent review only for substantive disagreements.

The reviewer model for the Anthropic-compatible path is `deepseek-flash[1m]`.

Reviewer calls are **research-side candidate triage**, not ACE trajectories and not evidence that B succeeds. Keep their artifacts separate from the adaptive loop.

### Phase 3: deterministic aggregation

Codex validates reviewer outputs against the packets before ranking:

- IDs must match;
- named APIs/evidence references must exist;
- proposed B may not depend on evaluator/setup-only values during execution;
- route scope and task semantics must be preserved;
- predicted savings remain hypotheses until benchmark execution;
- reviewers may not label B success or measured cost as established.

Promote at most 3-5 families after agreement/adjudication.

### Phase 4: CC implements scripted-B diagnostics

Only after the ensemble promotes a family should CC implement the research-side AppWorld diagnostic B route. Codex reviews and runs the diagnostic.

The next scientific gate is real benchmark evidence:

```text
success(B) = true
cost(B) < cost(C)
```

Only then does the project spend model calls on K0 explorability.

This work package deliberately removes manual per-sample review while preserving independent review: CC prepares/implements, a separate DeepSeek reviewer ensemble judges candidate semantics, and Codex controls validation/aggregation/final integration.