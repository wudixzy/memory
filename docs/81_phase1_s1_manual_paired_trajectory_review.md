# Phase 1 S1 Manual Paired-Trajectory Review

## 1. Scope and evidence boundary

This is a manual review of the already saved P0 and S1 development runs. No
model/API call was made, no episode was rerun, and no prompt, K*, history mode,
task membership, or actor manifest was changed.

Review result commit: `e8cbc50e3edd9112e1d11aa47c99140cb6925792`

P0 runtime:

```text
artifacts/exploratory_memory_mvp/paired-actor-stack-p0-p1-p2-20260920-359e08e-rerun1
```

S1 runtime:

```text
artifacts/exploratory_memory_mvp/stronger-actor-s1-qwen38max-20260920-4c3d413
```

The paired runner validated all five P0-reference/S1 replay proofs. The
comparison was held fixed on carrier, replay specification, canonical K* v1,
actions-only history, actor prompt, temperature, thinking mode, step cap, and
zero-based `action_index`. The only intended scientific intervention was:

```text
P0: qwen3.8-flash
S1: qwen3.8-max
```

The interpretation below is based on visible saved inputs, outputs, action
lists, and environment results. It does not infer hidden model reasoning.

## 2. Mechanical overview

| Task | P0 | S1 | Pairing | Immediate review signal |
| --- | --- | --- | --- | --- |
| Laptop → Desk | won, 11 steps | won, 4 steps | valid | S1 selects the requested laptop immediately |
| SoapBar → Cabinet | step cap, 32 | step cap, 32 | valid | both lose target binding; S1 takes `soapbottle_3` |
| Apple → Fridge | won, 18 steps | step cap, 32 | valid | S1 reaches a visible apple but fails the heat/retrieve/placement transition |
| Mug → Shelf | step cap, 32 | won, 7 steps | valid | S1 finds the mug, uses direct cooling, and places it |
| Mug → CoffeeMachine | step cap, 32 | invalid at call 4 after 3 executed steps | valid | S1 emits one-past-end `action_index: 57` |

These five episodes are development evidence only. They are not an actor
admission gate, and S1 was not promoted.

For each case, “first divergence” means the first paired step at which the
resolved actions differ. Where that early difference is not itself causal, a
second “decisive divergence” is identified rather than treating the final
step-cap as the root cause.

## 3. Case reviews

### 3.1 Laptop → Desk — positive control

Task: `put some laptop on desk.`

#### First meaningful divergence: step 2

The current observation is identical in both episodes:

```text
You arrive at loc_10. On bed_1, you see cellphone_1, laptop_2, laptop_1, pillow_1, and teddybear_1.
```

The relevant current admissible actions include:

```text
13: take cellphone_1 from bed_1
14: take laptop_1 from bed_1
15: take laptop_2 from bed_1
```

P0 returns:

```json
{"action_index":13,"probe_status":"NOT_ACTIVE"}
```

and resolves it to `take cellphone_1 from bed_1`. The environment confirms the
cellphone pickup. S1 returns:

```json
{"action_index":14,"probe_status":"NOT_ACTIVE"}
```

and resolves it to `take laptop_1 from bed_1`. The environment confirms the
requested laptop pickup.

#### Downstream effect

P0 repairs the mistake by returning to the bed, putting the cellphone back,
then taking and placing `laptop_1` at step 11. S1 goes directly to `desk_1` and
places `laptop_1` at step 4; the environment returns `won: true`.

#### Interpretation

**model-capacity improvement**, confidence **medium-high**. Both models saw
the same explicit target and legal actions under the same stack. The Max actor
made the correct object binding at the first choice, reducing the episode from
11 to 4 steps.

Alternative explanation: this is one deterministic model call on one simple
task, so a model-specific preference or sampling/API variation could explain
the improvement without establishing a general capability difference.

Evidence packet excerpts: `laptop_p0_step02` and `laptop_s1_step02`.

### 3.2 Apple → Fridge — regression after an initially plausible route

Task: `heat some apple and put it in fridge.`

#### First paired divergence: step 1

The public initial observation and ordered action list are identical. Both
lists include `go to cabinet_1` and `go to diningtable_1`.

P0 returns `action_index: 0`, resolving to `go to cabinet_1`. S1 returns
`action_index: 15`, resolving to `go to diningtable_1`. S1 then takes
`apple_1` from the dining table, while P0 follows the listed-order search and
eventually takes `apple_3` from the fridge.

This first divergence is not by itself a semantic error: either route can
expose an apple in this task. It is the beginning of two different trajectories,
not the strongest evidence for the later failure.

#### P0 control: heat and placement are public and legal

P0 reaches a state with:

```text
observation: You are carrying: apple_3.
resolved action: heat apple_3 with microwave_1
```

The environment returns:

```text
You heat apple_3 using microwave_1.
```

After returning to the fridge, P0 sees:

```text
In fridge_1, you see lettuce_1, mug_1, pan_2, potato_2, and tomato_1.
```

The current admissible actions include `put apple_3 in/on fridge_1`, and P0
returns that exact action. The environment accepts it and wins at step 18.

#### Decisive S1 divergence: step 8

S1 takes `apple_1`, puts it in `microwave_1`, closes the microwave, and then
opens it. At step 8 the actor-visible state is:

```text
You open microwave_1. In microwave_1, you see apple_1.
```

The current admissible actions include:

```text
0: close microwave_1
1: examine microwave_1
32: take apple_1 from microwave_1
```

S1 returns:

```json
{"action_index":31,"probe_status":"NOT_ACTIVE"}
```

which resolves to `look`, not the legal `take apple_1 from microwave_1`.
The following steps repeatedly look at or reopen the microwave. Later, at step
20, S1 opens the fridge and the public state shows the actor is not carrying
anything; the current actions include `go to microwave_1` and `inventory`. S1
returns `inventory` at step 21. It never performs a successful heat operation
or final placement and reaches the step cap.

#### Interpretation

**persistent semantic-control failure**, confidence **medium-high**. Once S1
has opened the microwave, the target is visible and the next local recovery
action is legal. The model repeatedly chooses `look`/`inventory` instead of
advancing the object through the task. The P0 trajectory also demonstrates
that the carrier exposes a direct accepted `heat <object> with <microwave>`
operation and a legal final fridge placement.

Alternative explanation: canonical K* v1 still describes a procedural
microwave routine (“put the object inside, close it, and execute heating”),
while the carrier also exposes a direct heat operation. S1 may have entered a
carrier-contract-ambiguous route and then failed to recover. Therefore this is
strong evidence about the complete actor stack, but not a pure model-capacity
measurement.

The early search choice is also consistent with the earlier paired review:
S1's K* v1 path visits `diningtable_1` immediately, whereas P0's ordered search
eventually succeeds. No hidden object location is needed to explain the later
visible control failure.

Evidence packet excerpts: `apple_p0_step01`, `apple_s1_step01`,
`apple_p0_step12`, `apple_p0_step18`, `apple_s1_step07`, `apple_s1_step08`,
`apple_s1_step20`, and `apple_s1_step21`.

### 3.3 Mug → Shelf — successful local search, transformation, and placement

Task: `cool some mug and put it in shelf.`

#### First meaningful divergence: step 1

The identical initial public state exposes both cabinet and countertop/coffee
machine candidates. P0 returns `go to cabinet_1`; S1 returns `go to
countertop_1`.

The early branch is not enough to establish why S1 succeeds. The important
visible transitions are:

1. At S1 step 2 the observation is `On countertop_1, you see lettuce_1,
   pan_1, spatula_1, and spoon_1.` S1 chooses legal `go to coffeemachine_1`.
2. At S1 step 3 the observation is `On coffeemachine_1, you see mug_1.` The
   admissible list contains `take mug_1 from coffeemachine_1`, and S1 returns
   it exactly.
3. At S1 step 5, after reaching the fridge, the admissible list contains
   `cool mug_1 with fridge_1`. S1 returns that action and the environment
   responds `You cool mug_1 using fridge_1.`
4. At S1 step 7 the observation is `On shelf_1, you see glassbottle_1.` The
   admissible list contains `put mug_1 in/on shelf_1`; S1 returns it and the
   environment wins.

P0 instead spends the early trajectory alternating between cabinet and fridge.
At P0 step 18 the current observation at `sinkbasin_1` lists `cup_1` and does
not list a mug. At P0 step 20 the admissible actions include
`take cup_1 from sinkbasin_1`, but no requested mug; P0 selects the cup and
then follows a wrong-object clean/placement path.

#### Interpretation

**model-capacity improvement**, confidence **medium-high**. S1 correctly binds
the public `mug_1`, executes the carrier-accepted direct cooling action, and
continues to the requested shelf. This is the strongest positive S1 trace
because it contains a complete successful local transformation and
downstream handoff under the unchanged P0 stack.

Alternative explanation: the improvement may be a one-task model preference
for the coffee-machine route rather than a general Max-tier capability. It does
not show that K* v1 is universally reliable.

Evidence packet excerpts: `shelf_p0_step01`, `shelf_s1_step01`,
`shelf_p0_step18`, `shelf_p0_step20`, `shelf_s1_step02`, `shelf_s1_step03`,
`shelf_s1_step05`, and `shelf_s1_step07`.

### 3.4 SoapBar → Cabinet — target binding is lost before the target is takeable

Task: `clean some soapbar and put it in cabinet.`

#### First paired divergence: step 3

After both actors open empty `cabinet_1`, the current observation is:

```text
You open cabinet_1. In cabinet_1, you see nothing.
```

P0 returns `go to cabinet_2`. S1 returns `close cabinet_1`. Both are legal
actions; this early difference is not by itself a clear cause.

#### S1 target drift

At S1 step 11 the actor opens `cabinet_3` and the environment reports:

```text
You open cabinet_3. In cabinet_3, you see soapbottle_3.
```

The task requests `soapbar`, not `soapbottle`. At step 12 the current
admissible actions contain `take soapbottle_3 from cabinet_3`, and S1 returns
that action. This is a legal action but a wrong-object acquisition. S1 later
carries `soapbottle_3` through the bathroom and eventually enters a
hand-towel interaction loop.

#### When is `soapbar_1` visible and is it legally takeable?

P0 first exposes the requested object at step 31/32:

```text
You arrive at loc_6. On toilet_1, you see candle_2, candle_1, soapbar_1, and soapbottle_1.
```

At the next P0 decision the actor is carrying `towel_1`; the saved admissible
actions contain no `take soapbar_1` action. P0 returns `inventory`.

S1 exposes the same public object at step 17:

```text
You arrive at loc_6. On toilet_1, you see candle_2, candle_1, soapbar_1, and soapbottle_1.
```

S1 is carrying `soapbottle_3`. The post-navigation admissible actions include
`put soapbottle_3 in/on toilet_1`, but do not include `take soapbar_1`. S1
returns `look` at step 18 and then leaves the location. Thus both trajectories
make the target publicly visible only after a wrong pickup has occupied the
inventory; the final lack of a legal take action is a consequence of earlier
target-binding drift, not evidence that the actor ignored an available
`take soapbar_1` at that exact state.

#### Interpretation

**persistent semantic-control failure**, confidence **high** for the S1 wrong
pickup and subsequent drift. The model selected a semantically different
`soapbottle` even though the requested type was `soapbar`, and then did not use
the visible `put` action to free the inventory.

Alternative explanation: once the wrong object was picked up, ALFWorld's
single-item inventory made the later target acquisition mechanically
unavailable. The final phase is therefore a compound target-binding and
continuation failure, not a clean test of choosing between two simultaneously
legal soapbar actions.

Evidence packet excerpts: `soap_p0_step03`, `soap_s1_step03`,
`soap_p0_step31`, `soap_p0_step32`, `soap_s1_step11`, `soap_s1_step12`,
`soap_s1_step17`, and `soap_s1_step18`.

### 3.5 Mug → CoffeeMachine — clear one-past-end action-index failure

Task: `cool some mug and put it in coffeemachine.`

#### First paired divergence: step 2

Both actors first execute `go to cabinet_1`. The next public state is:

```text
You arrive at loc_14. cabinet_1 is closed.
```

P0 returns:

```json
{"action_index":54,"probe_status":"NOT_ACTIVE"}
```

which resolves to `inventory`. S1 returns:

```json
{"action_index":56,"probe_status":"NOT_ACTIVE"}
```

which resolves to `open cabinet_1`. S1's choice is a more useful local search
step. S1 then returns to `cabinet_10` at step 3.

#### Invalid step: step 4

Immediately before the invalid call, S1 sees:

```text
You arrive at loc_2. cabinet_10 is closed.
```

The complete current ordered admissible list has length 57 and therefore
valid zero-based indices `0..56`:

```text
0  examine cabinet_10
1  go to cabinet_1
2  go to cabinet_11
3  go to cabinet_12
4  go to cabinet_13
5  go to cabinet_2
6  go to cabinet_3
7  go to cabinet_4
8  go to cabinet_5
9  go to cabinet_6
10 go to cabinet_7
11 go to cabinet_8
12 go to cabinet_9
13 go to coffeemachine_1
14 go to countertop_1
15 go to countertop_2
16 go to countertop_3
17 go to countertop_4
18 go to drawer_1
19 go to drawer_10
20 go to drawer_11
21 go to drawer_12
22 go to drawer_13
23 go to drawer_14
24 go to drawer_15
25 go to drawer_16
26 go to drawer_17
27 go to drawer_18
28 go to drawer_19
29 go to drawer_2
30 go to drawer_20
31 go to drawer_21
32 go to drawer_22
33 go to drawer_23
34 go to drawer_24
35 go to drawer_25
36 go to drawer_26
37 go to drawer_27
38 go to drawer_3
39 go to drawer_4
40 go to drawer_5
41 go to drawer_6
42 go to drawer_7
43 go to drawer_8
44 go to drawer_9
45 go to fridge_1
46 go to garbagecan_1
47 go to microwave_1
48 go to sinkbasin_1
49 go to stoveburner_1
50 go to stoveburner_2
51 go to stoveburner_3
52 go to stoveburner_4
53 go to toaster_1
54 inventory
55 look
56 open cabinet_10
```

The exact S1 response is:

```json
{"action_index":57,"probe_status":"NOT_ACTIVE"}
```

The runner correctly rejects it as `action_index_out_of_range`; no
environment action is executed. Index `56`, not `57`, is the semantically
appropriate next action for the closed `cabinet_10`.

#### Interpretation

**interface-adherence failure**, confidence **high**, not a semantic failure
at this decision. The model emitted a one-past-end index immediately after
selecting the correct receptacle. The saved runner mapping is correctly
zero-based and fail-closed; it did not silently clamp or rewrite the value.

Alternative explanation: the model counted the list as one-based or treated
the list length as the last valid index. Either explanation is still an
output-interface adherence problem. It does not establish that the model
would have failed to open `cabinet_10` if it had returned `56`.

The P0 episode later reaches a visible `mug_1` but repeatedly returns
`inventory`; therefore correcting this one invalid output would not by itself
establish reliable task control.

Evidence packet excerpts: `coffee_p0_step02`, `coffee_s1_step02`,
`coffee_s1_step03`, and `coffee_s1_step04`. The last excerpt includes the
complete saved list, raw response, validation error, and no fabricated
replacement action.

## 4. Cross-case synthesis

### K* v1 and carrier interaction

S1 was run with canonical K* v1, so this review does not compare K* variants.
There is no evidence that K* v1 alone explains the entire result:

* S1 successfully used the carrier-accepted direct action `cool mug_1 with
  fridge_1` and completed the Shelf task.
* P0 also demonstrates that `heat apple_3 with microwave_1` and final fridge
  placement are legal and sufficient in a successful path.
* The Apple failure remains compatible with a K* v1/carrier-contract confound,
  because v1 describes a procedural microwave routine while the environment
  exposes direct transformation actions. S1 then failed to retrieve the
  visible apple after its chosen route.

The evidence supports “K* v1 is not a sufficient reliability guarantee,” not
“K* v1 is the sole cause of S1 failure.”

### Model-capacity evidence

There are two concrete positive S1 changes under the same public interface:

* Laptop: S1 chooses `laptop_1` over the simultaneously visible cellphone and
  completes in four steps.
* Shelf: S1 finds `mug_1`, chooses the correct direct cooling action, and
  places it successfully.

There are also strong negative S1 traces:

* Apple: the target is visible inside the microwave and legal recovery is
  available, but S1 repeatedly selects `look`/`inventory` and never completes
  the transformation.
* SoapBar: S1 takes `soapbottle_3` for a `soapbar` task and later fails to
  release it when the target becomes visible.
* CoffeeMachine: S1 emits an invalid index before the next environment step.

Thus S1 is mixed evidence for model capability, not a clean stronger-actor
rescue. The two successes are useful development observations but cannot
support an independent actor gate or a general model ranking.

### Prompt, history, and interface

This S1 comparison keeps the prompt and actions-only history fixed. It does
not test whether `interaction_history` helps; that question belongs to the
previous P0/P1/P2 review. There is no basis here for changing the history
representation.

The one unambiguous implementation-level issue is CoffeeMachine's
one-past-end `action_index`. The runner's mechanical validation is working as
intended, but the actor/output boundary allowed an impossible value to reach
validation. The Apple and SoapBar failures are not explained by a missing
action-list entry: their critical target-relevant actions or recovery actions
are visible in the saved public state.

### Environment and harness

All five pairings are valid, the public initial states were replay-matched, and
the ordered admissible actions plus validation/environment results are saved.
There is no evidence in this review of a pairing or action-resolution harness
bug causing the semantic failures. ALFWorld's single-item inventory and direct
transformation semantics remain important carrier constraints, especially for
Apple and SoapBar, but they are visible in the runtime and not hidden
evaluator information.

### Unified interaction history

No conclusion about history value is drawn from S1. The S1 condition is
explicitly actions-only. The earlier P0/P1/P2 evidence remains separate and
did not establish general value for `interaction_history`.

## 5. Recommended next direction

**A — one minimal mechanical output-interface correction.**

The recommendation is narrowly justified by the CoffeeMachine trace: the
actor chose the correct semantic action (`open cabinet_10`) but emitted `57`
when the only valid corresponding index was `56`. The next implementation
should prevent impossible one-past-end outputs at the output boundary, for
example with a provider-supported dynamically range-constrained structured
output or an equivalent mechanical interface measure. It must not clamp,
rewrite, or reinterpret an invalid value after the model returns it.

This recommendation does **not** claim that the S1 actor is reliable. It does
not address the Apple/SoapBar semantic-control failures, and it does not
promote S1. After any interface change, the old Gate B1 and this S1 run remain
development/negative evidence; a newly frozen independent actor gate would be
required before Phase 1A execution.

## 6. Required scientific handoff

The following remain unchanged after this review:

* actor manifest status remains `candidate_pending_independent_reliability_gate`;
* no Gate B1-R, B2, B3, or Phase 1A target was run;
* no second stronger model was tested;
* no prompt, K*, history, semantic controller, or fallback policy was changed;
* the complete P0 and S1 runtimes remain locally preserved;
* the selected original step artifacts are available in
  `docs/human_review/trajectory_artifacts/phase1_s1_actor_review/`.

Any future tuning based on this review would make the five-task set further
development evidence and would require a fresh, independently frozen actor
gate rather than reusing these tasks as admission evidence.
