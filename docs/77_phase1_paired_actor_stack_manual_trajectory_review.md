# Phase 1 Paired Actor-Stack Manual Trajectory Review

## 1. Scope and evidence boundary

This is a zero-model/API-call manual review of the already completed P0/P1/P2
development run. No episode was rerun and no prompt, model, K*, task, or
runtime implementation was changed.

Review HEAD: `5c0dcaf2dddc8a56f679c58221c05e11cd5f7770`

Runtime execution HEAD recorded in the artifacts: `359e08e234d8d9a3233d7e8c3e4f509cef38799e`
Runtime root:

`artifacts/exploratory_memory_mvp/paired-actor-stack-p0-p1-p2-20260920-359e08e-rerun1`

All 15 episodes have valid P0↔P1, P0↔P2, and P1↔P2 pairing proofs. The
complete runtime remains locally preserved. A small set of unchanged original
step directories is tracked in:

`docs/human_review/trajectory_artifacts/phase1_paired_actor_stack_review/`

The packet README marks the provenance as **ORIGINAL SAVED ARTIFACT** and maps
each excerpt back to the runtime path.

The judgments below are reviewer interpretations of visible artifacts only.
They do not infer hidden model reasoning.

## 2. Mechanical overview

| Task | P0: v1 + actions | P1: v2b + actions | P2: v2b + interaction |
| --- | --- | --- | --- |
| Laptop → Desk | won, 11 steps | step cap, 32 | won, 4 |
| SoapBar → Cabinet | step cap, 32 | step cap, 32 | step cap, 32 |
| Apple → Fridge | won, 18 | step cap, 32 | step cap, 32 |
| Mug → Shelf | step cap, 32 | step cap, 32 | step cap, 32 |
| Mug → CoffeeMachine | step cap, 32 | step cap, 32 | step cap, 32 |

There were zero invalid action indices and zero infrastructure failures. These
are development observations, not an actor-admission result.

Only three task-level successful episodes exist in this runtime: Laptop/P0,
Laptop/P2, and Apple/P0. I reviewed all three. There is no fourth completed
task-level control to review without importing another run, so I do not present
a fourth task as if it succeeded. Successful local transitions in failed
episodes are discussed separately.

## 3. Case reviews

### 3.1 Laptop → Desk

Task instruction: `put some laptop on desk.` The initial public state and
ordered admissible actions are identical across all three variants.

Trajectory summaries:

* P0 first takes the wrong `cellphone_1`, eventually returns to `bed_1`, puts
  the cellphone back, takes `laptop_1`, and completes at step 11.
* P1 follows the same first three actions, then uses `look`, explores
  `drawer_1`, `drawer_3`, `laundryhamper_1`, `sidetable_1`, and other locations
  without acquiring a laptop before the step cap.
* P2 goes to `bed_1`, immediately takes `laptop_1`, goes to `desk_1`, and
  completes in four steps.

#### P0 ↔ P1 first meaningful divergence: step 4

Before both calls, the visible state is exactly:

```text
You arrive at loc_1. On desk_1, you see cellphone_3, desklamp_1, and keychain_1.
```

The relevant admissible choices include `go to bed_1`, `look`, and
`put cellphone_1 in/on desk_1`. Both variants have the same actions-only
history:

```text
go to bed_1
take cellphone_1 from bed_1
go to desk_1
```

P0 returns `go to bed_1` (index 2), producing a view of the remaining laptops.
P1 returns `look` (index 13), producing only `You are facing desk_1. Next to it,
you see nothing.` P1 then returns to the bed but chooses `inventory`, goes back
to the desk, and begins unrelated search.

Interpretation: **harmful in this paired case, confidence medium**. The only
controlled input difference is the K* v1/v2b content, and the v2b path is
followed by a clear regression. However, the divergence is not a direct
carrier-contract error: P1 was already carrying the wrong cellphone, and the
later failure also contains obvious model-side choices. This is evidence that
v2b wording changed search behavior, not proof that the carrier correction is
universally wrong.

#### P1 ↔ P2 first meaningful divergence: step 2

After the common `go to bed_1`, the current observation and admissible list are
the same and explicitly include both:

```text
take cellphone_1 from bed_1
take laptop_1 from bed_1
take laptop_2 from bed_1
```

P1 has actions-only history containing only `go to bed_1`. P2 has one raw
interaction pair containing that action and the resulting bed observation. P1
selects `take cellphone_1`; P2 selects `take laptop_1`.

Interpretation: **behaviorally helpful for this decision, confidence medium**.
The past observation is not uniquely necessary because the same bed contents
are repeated in `current_state.observation`; P2 may be responding to the
changed field/interface rather than using an otherwise missing fact. Still,
this is the clearest positive P1→P2 contrast in the run.

The P0/P1 step-4 and P1/P2 step-2 original artifacts are in the `laptop_*`
packet excerpts. P0 recovery and P2 completion are represented by the copied
steps 9/11 and 4 respectively.

### 3.2 Apple → Fridge

Task instruction: `heat some apple and put it in fridge.` The initial public
state lists many receptacles, but no apple until a fridge is opened.

Trajectory summaries:

* P0 begins with the listed-order search, opens `fridge_1`, takes `apple_3`,
  reaches `microwave_1`, performs the direct heat operation, and eventually
  places the apple in the fridge at step 18.
* P1 first visits `coffeemachine_1`, then spends steps 3–9 in an
  inventory/look stall. It eventually reaches and takes `apple_3` at step 29,
  but does not proceed to the microwave operation before the cap.
* P2 begins at `cabinet_1`, then spends steps 3–29 mostly repeating
  `inventory`/`look`, and only takes `apple_3` at step 32.

#### P0 ↔ P1 first meaningful divergence: step 1

The public current state and admissible list are identical. P0 selects the
first ordered candidate, `go to cabinet_1` (index 0). P1 selects
`go to coffeemachine_1` (index 13). P2 also selects `go to cabinet_1`.

This is the strongest paired indication that v2b changed the incumbent search
behavior: P1 is the only variant that immediately abandons the listed-order
choice, and it is the only Apple variant that does not reach the apple until
very late. The evidence is still limited to one task and one deterministic
call; P2's empty `interaction_history` also changes the model-visible input and
returns to the P0 choice.

#### P1 ↔ P2 first divergence: step 1, but not evidence of history use

P1 and P2 differ immediately because P1 exposes an empty
`executed_action_history` while P2 exposes an empty `interaction_history`.
There is no past observation in either input at this point. Therefore this
first difference cannot be credited to P2 using raw interaction evidence.

#### Post-acquisition decision

P0's step 12 has the clear carrier action `heat apple_3 with microwave_1` and
the environment accepts it. P1 finally takes `apple_3` at step 29. At step 30,
the current observation is `You take apple_3 from fridge_1.` The admissible
actions include `go to microwave_1`, but P1 chooses `go to shelf_1`; it then
goes to the microwave and chooses `look` rather than opening/heating.

Interpretation: **strong model-side reliability evidence, confidence high**.
The task phase is publicly identifiable as post-acquisition/need-heating, the
task instruction is still visible, and the direct microwave route is legal.
The failure is not a missing hidden placement fact. It also shows that the
v2b downstream wording did not by itself produce the intended handoff.

P2's final step only acquires the apple, so it provides no evidence about its
post-acquisition transformation decision.

### 3.3 SoapBar → Cabinet

Task instruction: `clean some soapbar and put it in cabinet.` None of the three
variants acquires `soapbar`.

Trajectory summaries:

* P0 and P1 share the first six actions: they open `cabinet_1` and `cabinet_2`,
  then take `towel_1` from `towelholder_1`. P0 later alternates between
  `cabinet_1` and `cabinet_2` and repeatedly examines the same contents.
* P1 searches both sinkbasins, repeatedly examines `towel_1`, then returns to
  the cabinet loop.
* P2 uses its interaction history to revisit `cabinet_1`, finds an unrelated
  `spraybottle_1` in `cabinet_4`, and wanders among bathroom receptacles. It
  never cleans the requested object.

#### P0 ↔ P1 first meaningful divergence: step 7

The current state is:

```text
You take towel_1 from towelholder_1.
```

The ordered admissible list contains both `go to sinkbasin_1` and
`go to sinkbasin_2`. P0 chooses sinkbasin 2; P1 chooses sinkbasin 1. Both
choices are locally legal and plausible for finding/using a sink. The resulting
paths converge on the same absence of the requested soapbar, so the divergence
is **unclear/likely irrelevant to the primary failure, confidence high**.

#### P1 ↔ P2 first meaningful divergence: step 5

P2's interaction history already records:

```text
cabinet_1: empty
cabinet_2: cloth_1 and soapbottle_2
```

At the current state `cabinet_2` is open with those same contents. P1 goes to
`towelholder_1`; P2 returns to `cabinet_1`, which is already known empty.

Interpretation: **not helpful and potentially harmful, confidence high**.
This is a direct counterexample to the claim that exposing raw observations
automatically prevents revisits. It does not prove the history field caused the
revisit, because P2 also changes the model-visible schema, but the observed
history was available and not operationally used to avoid it.

No variant reaches a correct `clean soapbar with sinkbasin` action. Therefore
this case cannot validate or invalidate the v2b direct-clean contract.

### 3.4 Mug → Shelf

Task instruction: `cool some mug and put it in shelf.` All three variants fail,
and all three choose an object other than the requested mug before the cool
operation.

Trajectory summaries:

* P0 alternates between `cabinet_1` and `fridge_1`, later reaches
  `sinkbasin_1`, takes `cup_1`, cleans it, and places it in `cabinet_1`; this is
  a wrong-object completion attempt.
* P1 searches cabinets/fridge, later reaches `countertop_2`, sees `mug_1` and
  `egg_2`, takes `egg_2`, and executes direct cooling on the egg.
* P2 reaches the same countertop earlier, also sees `mug_1` and `egg_2`, takes
  `egg_2`, executes direct cooling twice, and then continues with look/inventory
  and unrelated navigation.

#### P0 ↔ P1 first meaningful divergence: step 3

Both have just opened empty `cabinet_1`. The public admissible actions include
`go to fridge_1` and `go to cabinet_2`. P0 chooses the fridge; P1 chooses
`cabinet_2`.

Interpretation: **unclear, confidence medium**. Neither choice is intrinsically
invalid, and neither leads to the mug. The later wrong-object selection is a
stronger causal point than this early search divergence.

#### P1 ↔ P2 first meaningful divergence: step 5

Both have opened `cabinet_2` and observed `winebottle_1`. P1 selects
`go to toaster_1`; P2 selects `inventory`. P2's interaction history contains
the cabinet observations, but the current state also says it is carrying
nothing. `inventory` produces no new task evidence.

Interpretation: **irrelevant-to-helpful at best, confidence medium**. This
does not show P2 using the preceding observations to select a better search
location.

#### Wrong-object and direct-cool evidence

At P1 step 26 and P2 step 7, `countertop_2` visibly contains:

```text
egg_2, houseplant_1, mug_1, peppershaker_1, potato_3, saltshaker_2
```

The ordered admissible actions include both `take egg_2 from countertop_2` and
`take mug_1 from countertop_2`. Both variants take the egg. This is **strong
model-side target-binding evidence, confidence high**: the requested object and
the competing object are simultaneously public and the exact target action is
legal.

P1 step 31 and P2 step 18 execute `cool egg_2 with fridge_1`, and the
environment returns `You cool egg_2 using fridge_1.` This is useful mechanical
evidence that the v2b direct cooling syntax is accepted by the carrier. It is
not evidence that the intended mug task was solved. P2 repeats the same cool
action at step 20 after a prior successful cool result and a visible interaction
history entry, which is additional evidence of poor downstream transition
control.

### 3.5 Mug → CoffeeMachine

Task instruction: `cool some mug and put it in coffeemachine.`

Trajectory summaries:

* P0 eventually reaches `coffeemachine_1` at step 4, sees `mug_1`, then chooses
  `inventory` repeatedly rather than taking it.
* P1 goes directly to `coffeemachine_1` at step 1, sees `mug_1`, and chooses
  `inventory` for every remaining step.
* P2 reaches `coffeemachine_1` at step 5, sees `mug_1`, and chooses
  `inventory`; it continues to do so after the raw observation is in
  `interaction_history`.

#### P0 ↔ P1 first meaningful divergence: step 1

P0 chooses `go to cabinet_1`; P1 chooses the directly visible target
receptacle, `go to coffeemachine_1`. The P1 choice is actually a more useful
search move, but it does not lead to task progress because of the next step.

#### P1 ↔ P2 first divergence: step 1, empty-history interface difference

P1 selects the coffee machine while P2 selects `cabinet_1`. Both history fields
are empty at this point, so this is not evidence that raw past observations
helped P2.

#### Strong repeated model-side failure: P1 step 2 / P0 step 5 / P2 step 6

In each of these states the current observation says:

```text
You arrive at loc_35. On coffeemachine_1, you see mug_1.
```

The admissible list contains the exact action `take mug_1 from
coffeemachine_1` next to `inventory`. P1, P0, and P2 all select `inventory`.
P1 then repeats it through step 32. P2's step 6 has an interaction-history
entry containing the just-observed mug, but still selects `inventory`.

Interpretation: **strong model-side actor reliability evidence, confidence
high**. The public target, task instruction, legal action, and relevant K*
contract are all available. This is repeated across variants, so it is not
primarily a K* v2b regression or a missing observation-history fact.

## 4. Success controls and local successes

The paired runtime contains only three completed task episodes:

1. **Laptop/P0**: after an initial wrong cellphone pickup, the actor repairs
   the inventory by returning the cellphone and then places `laptop_1`.
2. **Laptop/P2**: the actor selects the requested laptop immediately and
   completes in four actions.
3. **Apple/P0**: the actor finds `apple_3`, reaches the microwave, performs
   accepted direct heating, and places the apple in the fridge.

The Apple/P0 direct-heating step is also a successful local carrier transition,
but not a fourth completed task. In failed episodes, the direct cool operation
on the wrong `egg_2` is another successful local environment transition. These
local transitions show that action-index resolution and direct ALFWorld action
syntax are functioning; they do not show correct target/task control.

The absence of a fourth completed task is itself part of the negative evidence,
not a reason to import a different task or rerun the experiment.

## 5. Cross-case synthesis

### K* v2b and carrier-contract correction

There is partial mechanical support for the carrier-contract correction:

* P1/P2 use `cool <object> with <fridge>` on `egg_2`, and ALFWorld accepts it.
* P0's successful Apple path also demonstrates that a direct `heat` operation
  is legal in the carrier.

There is no successful v2b episode that applies the corrected clean/heat/cool
operation to the requested object and then completes the downstream task. The
contract fix therefore remains only partially validated.

At the same time, v2b is followed by two conspicuous paired regressions:

* Laptop step 4: P0 returns to the candidate bed while P1 chooses `look` and
  later drifts into unrelated receptacles.
* Apple step 1: P0/P2 choose the first ordered cabinet while P1 chooses
  `coffeemachine_1` and enters a long stall before finding the apple.

The controlled pairing makes these changes relevant evidence against blindly
promoting v2b. It does not identify a single defective phrase: P2 changes the
history field as well and recovers the Laptop path, while the Apple P2 first
choice also differs despite an empty history. The correct conclusion is
“observable candidate regression, mechanism not isolated,” not “v2b is
universally invalid.”

### Unified interaction history

P2 inputs really contain one `interaction_history` field and omit the duplicate
actions-only fields. The interface is therefore present in the actual calls.

Evidence for benefit is limited to Laptop: P2 selects the laptop where P1
selects a cellphone. However, the current observation already repeats the bed
contents, so this is not a clean case where history supplies otherwise missing
information. It may be an attention/interface effect.

Counterevidence is stronger across the other cases:

* Soap P2 revisits a cabinet whose empty/content observations are in history.
* Shelf P2 does not use history to avoid an unproductive `inventory`, later
  selects `egg_2` despite `mug_1` being visible, and repeats the cool action
  after a prior cool result is recorded.
* Coffee P2 sees `mug_1`, has that observation in history, and still repeats
  `inventory`.
* Apple P2's first divergence occurs with an empty history and its long
  inventory stall provides no later evidence of useful history use.

This run does not establish concrete value for unified interaction history.

### Strongest model-side reliability evidence

The strongest examples satisfy the requested conditions of clear public state,
legal task-relevant action, non-contradictory K*, and repeated non-progress:

1. Coffee P1/P0/P2: visible `mug_1`, exact `take mug_1 from coffeemachine_1`
   available, repeated `inventory` instead.
2. Apple P1 step 30: `apple_3` acquired, microwave route available, but
   `go to shelf_1` is selected and later `look` replaces the transformation.
3. Shelf P1/P2: visible `mug_1` and `egg_2` on the same countertop, both
   choose the wrong egg; P2 then repeats an already completed cool action.

These traces justify treating actor execution reliability as a live hypothesis,
but the run still measures the complete actor stack rather than a pure model
capability parameter.

### Prompt, representation, K*, and harness confounds

There is evidence for an interface/context confound:

* P1/P2 differ at step 1 on Apple and Coffee solely through the history-field
  representation even though both histories are empty.
* The current observation repeats the latest environment result, so P2 can
  increase context without adding unique state information.
* Long ordered admissible lists and repeated `inventory`/`look` outputs make
  the actor-facing context difficult, especially in Coffee.

There is no evidence of a mechanical harness defect in this run: all pairwise
proofs are valid, all action indices are valid, and environment results are
saved. There is also no strong evidence that K* alone caused every failure.

K* interference is present as a plausible explanation for the P0/P1 search
regressions, but not proven as the dominant cause. In the Coffee case, v1 and
v2b both fail after the target becomes visible.

### Step-cap interpretation

Most step caps are not “almost completed” cases:

* Coffee P1 enters an inventory loop at step 2; P2 enters one shortly after
  reaching the coffee machine.
* Apple P2 spends nearly the whole episode at `cabinet_1` with
  `inventory`/`look` and acquires the apple only at step 32.
* Shelf P0 alternates cabinet/fridge before acquiring the wrong cup; P2 repeats
  the wrong-object cooling action and then stalls.
* Soap P0/P1 enter repeated cabinet/sink or cabinet/cabinet searches well
  before the cap.

Apple P1 is closer in the narrow sense that it acquires the apple at step 29,
but it still fails to select the clear microwave continuation. This is a
decision failure, not merely a three-step cap truncation.

## 6. Direct answers to the review questions

1. **Did v2b fix the carrier contract?** Partially at the mechanical syntax
   level; no requested-object end-to-end evidence validates the complete fix.
   It also shows candidate regressions in Laptop and Apple, so it should not be
   promoted.
2. **Did unified interaction history provide concrete value?** It changed
   behavior and coincided with Laptop recovery, but the current observation
   already contained the relevant bed facts. The other traces do not show the
   actor using past observations to avoid revisits or advance the task. Concrete
   general value is not established.
3. **Which errors are model-side reliability evidence?** Repeated failure to
   take a visibly available mug, failure to transition from an acquired apple
   to the microwave, and selecting `egg_2` over a simultaneously visible
   requested `mug_1` are the strongest examples.

## 7. Recommended next direction

**E — evidence is insufficient; run one smallest missing-cell diagnostic before
choosing a stack or stronger actor.**

The missing crossed cell is `canonical K* v1 + unified interaction_history`
(call it P3), using the already frozen replay specifications and no other
changes. Run only the Laptop and Apple development tasks once each. Laptop
would test whether P2's recovery is attributable to history rather than the
v2b wording; Apple would test whether the v2b search regression persists when
the history representation is held at P2. Do not use this diagnostic as an
admission gate or target-selection evidence.

This is preferable to immediately freezing P0, promoting v2b, or selecting a
stronger actor because the current run has a genuine K*/history interaction
confound and no clean positive demonstration that raw history itself was used.

No diagnostic should be run in this cycle.

## 8. Calibration and promotion warning

The five paired tasks remain development-only. Any subsequent K* wording,
history-interface, or actor change would make this set further development
evidence. It must not be reused as an independent Gate B1/B1-R admission set,
and neither K* v2b nor the actor manifest is promoted by this review.

The following remain forbidden after this review unless separately authorized:

* Gate B1-R;
* stronger-actor comparison;
* B2/B3 or live source-H generation;
* Phase 1A targets;
* semantic controllers, prompt tuning, or automatic fallback planning.
