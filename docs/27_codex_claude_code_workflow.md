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

## 7. Current first work package

The first CC work package is **not** another branch experiment. It is the Stage-A candidate analysis from `docs/26_strategy_lockin_experiment_plan.md`:

1. build a reproducible AppWorld task-family census;
2. identify source/target families with multiple successful strategies and a meaningful public-API-call cost gap;
3. produce a top-10 candidate report scored by the registered rubric;
4. do not start paid model runs yet unless needed for a very small already-authorized diagnostic;
5. let Codex review the candidates before implementing explorability probes.

## 8. Secret handling

Codex may know that `.env` contains `DEEPSEEK_KEY`, but it should not read/print the key unless the local wrapper itself needs to source it. Prefer invoking the wrapper rather than extracting the value into a Codex-visible shell command.

Never run commands such as:

```text
cat .env
env
printenv
set -x
```

in a context whose output is captured into agent logs when secrets may be present.

The wrapper disables shell tracing before reading `.env`.

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
