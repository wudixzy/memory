# Research Brief: Closed-Loop Reliability of Persistent Agent Memory

> Status: working research definition for phenomenon validation.  
> Date: 2026-09-11.  
> This document defines the current story and novelty boundary. It does **not** assume the target failure has already been experimentally established.

## 1. Background: why persistent memory exists

Sequential agents repeatedly pay for search, interaction, tool use, reasoning, and trial-and-error. Persistent memory is valuable because it can amortize those costs across tasks:

\[
\text{past costly experience}
\rightarrow
\text{persistent reusable knowledge}
\rightarrow
\text{cheaper / better future decisions}.
\]

A useful memory system must therefore create persistent behavioral bias. If the agent treated every future possibility exactly as if no history existed, memory would not amortize experience.

This project calls the high-level objective **cross-task experience amortization**.

## 2. The closed loop that creates the research problem

Persistent memory is not only a passive store. In an online agent it participates in generating the future data from which it will later learn:

\[
K_t
\rightarrow
\pi_{t+1}
\rightarrow
E^{obs}_{t+1}
\rightarrow
\tau_{t+1}
\rightarrow
U
\rightarrow
K_{t+1}.
\]

Where:

- `K_t`: persistent memory / reusable commitment at time `t`;
- `pi_{t+1}`: future policy conditioned on the current task and memory;
- `E_obs`: observations/evidence the policy actually acquires;
- `tau`: resulting trajectory;
- `U`: memory formation / revision procedure.

The key point is that `E_obs` is **endogenous**:

\[
E^{obs}_{t+1} \sim D_E(\pi(\cdot\mid K_t)).
\]

The memory helps decide what the agent will look at, which means the memory also helps decide what evidence will later be available to revise that memory.

## 3. Representative related work and what each line already solves

The purpose of this section is to avoid overclaiming novelty. The project is **not** claiming that memory formation, revision, uncertainty, exploration, path dependence, or memory–experience feedback are individually new topics.

### 3.1 Experience -> reusable memory

**ExpeL (AAAI 2024)** learns natural-language insights from trial-and-error across tasks and reuses both insights and past successful experiences. It establishes a representative `experience -> reusable knowledge` paradigm.

- Contribution relevant here: cross-task experience extraction and reuse.
- Remaining gap relative to us: its main framing does not study whether memory-shaped future data make the long-run update loop self-correcting or self-reinforcing.
- Source: https://arxiv.org/abs/2308.10144

**AutoGuide** learns context-aware guidelines rather than globally applying undifferentiated rules.

- Contribution relevant here: reusable knowledge needs scope/context, not only content.
- Remaining gap: scope-aware guidance does not by itself guarantee that future behavior will acquire evidence capable of correcting the learned scope.
- Source: https://arxiv.org/search/?query=AutoGuide+context-aware+guidelines+agents&searchtype=all

**AutoManual (NeurIPS 2024)** constructs and updates a structured rule/manual system online. A Planner uses rules to act; a Builder adds/updates rules with case-conditioned prompting and validation records.

- Contribution relevant here: online rule formation, revision, essential-detail retention, and explicit reuse in behavior.
- Remaining gap: it does not make the long-run question `rule -> evidence acquisition -> next rule update` the main object of evaluation.
- Paper: https://proceedings.neurips.cc/paper_files/paper/2024/hash/0142921fad7ef9192bd87229cdafa9d4-Abstract-Conference.html
- Code: https://github.com/minghchen/automanual

**Agent Workflow Memory / AWM (ICML 2025)** induces reusable workflows from trajectories and supports both offline and online induction. On WebArena, online AWM can update workflows from test-time trajectories and reuse them in later tasks.

- Contribution relevant here: a real online `memory -> behavior -> trajectory -> updated memory` loop.
- Remaining gap: the method is evaluated mainly for success, efficiency, and transfer; it does not explicitly test whether workflow reuse suppresses the evidence needed to correct or improve the workflow itself.
- Paper: https://proceedings.mlr.press/v267/wang25bx.html
- Code: https://github.com/zorazrw/agent-workflow-memory

### 3.2 Persistent memory evolution and abstraction quality

**Dynamic Cheatsheet** and related evolving-context work treat long-lived textual context as an adaptively revised persistent state.

- Contribution relevant here: persistent knowledge can be revised instead of simply appended.
- Remaining gap: many such evaluations emphasize prediction/task accuracy rather than behaviorally acquired evidence in interactive environments.

**Agentic Context Engineering / ACE (ICLR 2026)** uses Generator–Reflector–Curator roles and incremental delta updates to grow/refine a playbook while mitigating brevity bias and context collapse.

- Contribution relevant here: strong treatment of iterative memory/context degradation; online adaptation is supported.
- Remaining gap: preventing destructive rewriting is not equivalent to proving that the content, scope, and strength of each persistent commitment are calibrated to behaviorally collected evidence, nor that future evidence needed for revision remains reachable.
- Paper: https://arxiv.org/abs/2510.04618
- Code: https://github.com/ace-agent/ace
- AppWorld integration: https://github.com/ace-agent/ace-appworld

**Useful Memories Become Faulty When Continuously Updated by LLMs (2026)** provides direct evidence that repeated memory consolidation can degrade memory utility even when the underlying experiences are useful, and analyzes failures such as condition loss / over-generalization / redundant accumulation.

- Contribution relevant here: strong empirical evidence that Problem A is real and not solved by merely having an update operation.
- Remaining gap: the work primarily isolates consolidation quality; it does not by itself establish the full endogenous `A -> B -> A` harmful feedback loop.
- Source: https://arxiv.org/abs/2605.12978

### 3.3 Uncertainty and correction-like self-reinforcement

**Belief Memory / BeliefMem (2026)** represents multiple hypotheses and evidence strengths instead of collapsing partial observations into a single deterministic conclusion.

- Contribution relevant here: explicitly recognizes premature certainty and self-reinforcing errors under partial observability; preserves alternative hypotheses.
- Remaining gap: keeping alternatives represented in memory (**epistemic optionality**) does not guarantee that the agent will take actions that acquire evidence capable of distinguishing those alternatives (**evidential reachability**).
- Source: https://arxiv.org/abs/2605.05583

### 3.4 Exploration and improvement lock-in

**APEX (2026)** studies memory-induced exploration collapse in self-evolving agents and introduces a strategy map, Fork Discovery, and policy selection to keep underexplored alternatives active.

- Contribution relevant here: directly overlaps with our `known-good != known-optimal` / improvement-lock-in intuition.
- Remaining gap: its exploration machinery is strongest for alternatives that have already been observed, exposed, or represented in the strategy map. It does not establish a general solution for evidence/regions that prior memory commitments prevent from entering the observed trajectory in the first place.
- Source: https://arxiv.org/abs/2605.21240

### 3.5 Positive memory–experience feedback loops

**ReasoningBank (ICLR 2026)** induces reasoning memories from successful and failed trajectories and couples memory with memory-aware test-time scaling.

- Contribution relevant here: memory–experience feedback itself is not new; the paper explicitly studies a positive/virtuous interaction between better memory and better/more diverse trajectories.
- Remaining gap: it does not center harmful self-reinforcement, evidential suppression, or recoverability as the target phenomenon.
- Paper: https://openreview.net/forum?id=jL7fwchScm
- Code: https://github.com/google-research/reasoning-bank

### 3.6 Structured knowledge/skill evolution

**WikiSkill (2026)** separates accumulated experience/knowledge from evolved executable skills.

- Contribution relevant here: experience, persistent knowledge, and behavioral skill can be different layers.
- Remaining gap: the long-run effect of skill authority on which future evidence enters the update stream is not its central evaluation target.
- Source: https://arxiv.org/abs/2608.27454

**Procedural Graphs (2026)** represents procedural knowledge as graphs, revises graph structure from trajectories, and uses validation to gate candidate changes.

- Contribution relevant here: structured revision, bad-prior repair, and external validation can make memory updates safer.
- Remaining gap: a fixed/externally covered validation distribution is a materially different setting from a pure online agent whose future evidence is generated by its own memory-conditioned behavior. Whether the latter remains recoverable is still open.
- Source: https://arxiv.org/abs/2609.09153

## 4. What is already known vs. what remains open

### Already known / not our novelty

We must **not** claim any of the following as firsts:

- persistent memory can be built from trajectories;
- persistent memory can be revised online;
- repeated consolidation can lose useful information;
- memory needs scope/context;
- memory can preserve uncertainty;
- memory can cause path dependence or exploration collapse;
- agents can deliberately re-explore underused alternatives;
- memory and new experience can form a positive feedback loop.

### Remaining open problem we target

The missing link is **endogenous evidence acquisition**:

> The learned persistent commitment helps determine which future evidence is observed, while that observed evidence determines how the commitment will evolve next.

We therefore study the **closed-loop reliability** of experience-derived persistent memory.

The target failure is not merely `K_t is wrong` or `K_t changes behavior`. It is:

\[
K_t \neq K^*
\quad\land\quad
K_t\text{ reduces access to evidence needed to revise }K_t.
\]

The same mechanism can occur when `K_t` is correct but suboptimal.

## 5. Problem A: Evidence-Calibrated Persistent Abstraction

### Definition

> Given finite and behaviorally collected historical trajectories, how should an agent form and revise reusable persistent knowledge such that the abstraction's content, scope, and commitment strength do not exceed what the accumulated evidence actually justifies, while preserving distinctions that may remain decision-relevant for future tasks?

Formally:

\[
\tau^{obs}_{1:t} \rightarrow K_t.
\]

The phrase **behaviorally collected** is essential. The trajectory set is not assumed to be an unbiased sample of the environment; earlier memory may already have shaped it.

### Core tension

\[
\text{abstraction / reuse}
\quad\text{vs.}\quad
\text{decision-relevant fidelity}.
\]

A does not ask the system to preserve all details. It asks whether the distinctions that are discarded are justified to be discarded for future decisions.

## 6. Problem B: Memory-Induced Evidential Reachability

### Definition

> Given persistent knowledge used to amortize future decisions, how does that knowledge alter which actions, observations, counterexamples, and alternative strategies remain behaviorally reachable; and when does useful reuse prematurely eliminate evidence that would be necessary to correct or improve the memory itself?

Formally:

\[
K_t \rightarrow \pi_{t+1} \rightarrow E^{obs}_{t+1}.
\]

The key quantity is not generic exploration entropy. It is the reachability of **decision-relevant evidence**:

\[
P(E^*_{decision-relevant}\mid K_t).
\]

### Core tension

\[
\text{experience amortization}
\quad\text{vs.}\quad
\text{evidential optionality}.
\]

## 7. A+B: Closed-Loop Reliability

A and B are not two independent modules. Their coupling is the research target:

\[
\underbrace{\tau^{obs}_{1:t}\rightarrow K_t}_{A}
\rightarrow
\underbrace{\pi_{t+1}\rightarrow E^{obs}_{t+1}}_{B}
\rightarrow
\tau_{t+1}
\rightarrow
K_{t+1}.
\]

The central question is:

> **Can a persistent-memory agent remain reliably self-correcting when the memory it learns also controls the evidence from which it will learn next?**

Equivalent internal shorthand:

> **The memory decides which evidence will be observed, and that evidence decides how the memory evolves.**

## 8. Unified failure: self-reinforcing memory commitment

A harmful loop can take the form:

```text
limited / local historical evidence
        ↓
persistent commitment
        ↓
future behavior follows that commitment
        ↓
discriminative evidence is less likely to be acquired
        ↓
future updates receive less reason to revise the commitment
        ↓
commitment persists or strengthens
```

This is stronger than an ordinary wrong-memory example because the memory itself contributes to the absence of corrective data.

## 9. Correction lock-in and improvement lock-in

These are two instances of one mechanism.

### Correction lock-in

`K_t` is wrong, incomplete, or over-generalized. Correcting it requires counterevidence `E_counter`, but memory reuse makes:

\[
P(E_{counter}\mid K_t)\downarrow.
\]

### Improvement lock-in

`K_t` is valid and useful but not optimal. Improving it requires comparative evidence `E_comp` showing that another strategy is better, but memory reuse makes:

\[
P(E_{comp}\mid K_t)\downarrow.
\]

Unified statement:

> **Current memory suppresses the evidence required to justify changing current memory.**

This also preserves an important distinction:

\[
\text{evidence that a chosen strategy works}
\neq
\text{evidence that alternatives are inferior}.
\]

## 10. Current hypotheses for phenomenon validation

These hypotheses are deliberately ordered from weak to strong.

### H1 — Memory-induced distribution shift

Persistent memory materially changes future behavior/observation/trajectory distribution:

\[
P(\tau\mid K_t) \neq P(\tau\mid \varnothing).
\]

H1 alone is expected and does **not** establish a problem.

### H2 — Evidential suppression

There exists a naturally learned memory commitment `m_i` and decision-relevant evidence `E*` such that:

\[
P(E^*\mid K_t) < P(E^*\mid K_t \setminus \{m_i\}).
\]

The comparison must be made with a controlled branch, not by comparing unrelated tasks.

### H3 — Self-reinforcement

The trajectory distribution shaped by `K_t` is then used by the baseline's own updater and tends to preserve or strengthen the suspect commitment:

\[
K_t \rightarrow D_\tau(K_t) \rightarrow U \rightarrow K_{t+1}.
\]

H3 is the minimum evidence for the actual A+B coupling rather than a one-off harmful memory effect.

### H4 — Recoverability gap

The intact system fails to reopen a still-valid correction/improvement path over continued online operation, while a targeted intervention that reduces the suspect memory authority restores access:

\[
P(E^*\text{ or }\tau^*\mid do(m_i\downarrow))
>
P(E^*\text{ or }\tau^*\mid K_t).
\]

H4 is the strongest evidence that the closed loop itself creates a recoverability problem.

## 11. Falsification criteria

The direction should be weakened or abandoned if strong baselines show that:

- memory changes behavior (H1) but does not systematically reduce access to decision-relevant evidence (H2 fails);
- apparent harmful memories are rapidly revised once later tasks arrive (H3/H4 fail);
- failures occur only in FIFO/naive memory but disappear in stronger online memory systems such as AWM/ACE;
- the effect disappears when controlling for model stochasticity, environment state, task ordering, or evaluator leakage;
- the only way to demonstrate lock-in is to inject an artificial wrong memory or manually hide counterevidence.

## 12. Novelty boundary for future writing

The strongest currently defensible positioning is **not** “we discovered persistent-memory path dependence.”

The target contribution, if validated, is closer to:

> **Endogenous evidence acquisition is a missing link between persistent memory formation and long-run behavior. Existing methods improve memory construction, revision, uncertainty, and exploration locally, but do not systematically evaluate whether memory-conditioned data collection makes the long-run learning loop self-correcting or self-reinforcing.**

Method design is intentionally postponed until real H2–H4 failures are observed in credible systems.