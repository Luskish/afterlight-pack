# AFTERLIGHT Gate Expedition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend `AFTERLIGHT Signal` with a physical eleven-second Gate of Return and the additive Far Relay expedition dimension.

**Architecture:** A pure gate domain defines the exact 7 by 9 ring, activation state, deadline recovery, and return safety. NeoForge block entities, data-driven worldgen, player attachments, and server-side FTB adapters apply that domain without changing existing world chunks or existing Gate recipes.

**Tech Stack:** Java 21, NeoForge 21.1.248, FTB Quests 2101.1.30, NeoForge GameTests, data-driven dimensions, world `SavedData`, player data attachments, custom block entities and payloads.

## Global Constraints

- Implement in `/Users/shaneliszewski/afterlight-signal` after companion `v0.1.0` is green.
- Minecraft stays exactly `1.21.1`; NeoForge stays exactly `21.1.248`.
- The existing `kubejs:gate_of_return_core` recipe, item, quest IDs, and four hard-gate policy remain intact.
- The Gate opens for exactly `220` server ticks.
- The Far Relay is additive and never rewrites existing dimensions or chunks.
- Only players entering the field are teleported.
- Return always has a shared-spawn fallback.
- No ordinary hostile mobs spawn in the Far Relay.
- Every task updates `ReleaseJarContractTest` with the exact newly added JAR inventory in the same commit. The authenticated release contract must stay green throughout development, not only in Task 6.
- No U+2014 em dash appears anywhere.
- No JAR or secret is committed.
- Every Gradle command supplies `-PafterlightLockContext=macos` on Shane's Mac or `-PafterlightLockContext=linux` on Linux CI.
- Every commit ends with `Co-Authored-By: Codex <noreply@openai.com>`.

## File Structure

```text
src/main/java/org/rllabs/afterlight/gate/
  GateLocalPos.java                       plane-relative coordinate
  GatePattern.java                        exact expected ring
  GatePatternMatcher.java                 loaded-world validation
  GateState.java                          IDLE, OPEN, FAULT
  GateActivationService.java              pure prerequisite and deadline policy
  GateProgressGateway.java                FTB-neutral server interface
  FtbGateProgressGateway.java             exact task completion adapter
  GateControllerBlock.java                insert, remove, activate interaction
  GateControllerBlockEntity.java          core, orientation, deadline, owner state
  GateFieldBlock.java                     collision entry and safe closure
  GateReturnTarget.java                   persisted per-player return vector
  GateTravelService.java                  cross-dimension transfer and fallback
src/main/java/org/rllabs/afterlight/relay/
  FarRelayKeys.java                       dimension and advancement resource keys
  FarRelaySavedData.java                  schema and site initialization bits
  FarRelayInitializer.java                deterministic central and satellite builds
  RelaySite.java                          CENTRAL, EAST, WEST, NORTH, SOUTH
  ReturnTerminalBlock.java                player return interaction
  FutureConsoleBlock.java                 recovered transmission interaction
src/main/java/org/rllabs/afterlight/client/
  FarRelayEffects.java                    custom sky and fog registration
  GateRenderer.java                       controller and field visuals
src/main/resources/data/afterlight/
  dimension/far_relay.json                fixed biome and custom noise settings
  dimension_type/far_relay.json           logical dimension contract
  worldgen/biome/far_relay.json           colors, particles, no mob spawns
  worldgen/noise_settings/far_relay.json  pinned End-island router with relay stone
  recipe/gate_frame.json                  postgame frame recipe
  recipe/signal_glass.json                postgame stabilizer recipe
  recipe/gate_controller.json             postgame controller recipe
  advancement/gate_opened.json            physical activation criterion
  advancement/far_relay_arrival.json      first destination entry criterion
  loot_table/chests/far_relay.json        progression-safe expedition loot
src/main/resources/assets/afterlight/
  blockstates/                             gate and relay block states
  models/block/                            gate and relay models
  models/item/                             item forms
  textures/block/                          original Signal Reliquary textures
  sounds.json                              gate open, close, and fault events
src/test/java/org/rllabs/afterlight/gate/   pure and GameTest coverage
src/test/java/org/rllabs/afterlight/relay/  worldgen and safety coverage
```

---

### Task 1: Gate Geometry and Registry

**Files:**
- Create: `src/main/java/org/rllabs/afterlight/gate/GateLocalPos.java`
- Create: `src/main/java/org/rllabs/afterlight/gate/GatePattern.java`
- Create: `src/main/java/org/rllabs/afterlight/gate/GatePatternMatcher.java`
- Create: `src/main/java/org/rllabs/afterlight/gate/GateState.java`
- Modify: `src/main/java/org/rllabs/afterlight/EchoContent.java`
- Create: gate block classes and block entity listed in File Structure
- Create: three recipe JSON files
- Test: `src/test/java/org/rllabs/afterlight/gate/GatePatternTest.java`
- Test: `src/test/java/org/rllabs/afterlight/gate/GatePatternMatcherTest.java`
- Modify: `src/test/java/org/rllabs/afterlight/ReleaseJarContractTest.java`

**Interfaces:**
- Consumes: controller world position and horizontal facing.
- Produces: `GatePattern.expected(Direction)`, `GatePattern.interior(Direction)`, and `GatePatternMatcher.match(...)` returning exact mismatch details.

- [ ] **Step 1: Write failing geometry tests**

The local plane uses `u` from `-3` through `3`, `v` from `0` through `8`, and controller `(0, 0)`.

The exact signal-glass set is:

```java
Set.of(
    pos(-2, 0), pos(2, 0), pos(-3, 1), pos(3, 1),
    pos(-3, 7), pos(3, 7), pos(-2, 8), pos(2, 8)
)
```

All other perimeter positions except controller are gate frames. Tests require 8 glass, 19 frame, 1 controller, and 35 interior positions. Test north, south, east, and west transforms.

- [ ] **Step 2: Run geometry tests and verify RED**

Run: `gradle test --tests 'org.rllabs.afterlight.gate.GatePattern*Test' -PafterlightLockContext=macos --no-daemon`

Expected: FAIL because pattern classes are missing.

- [ ] **Step 3: Implement the pure pattern and matcher**

Use immutable maps from `GateLocalPos` to `GatePart`. The matcher rejects unloaded chunks, wrong block IDs, occupied non-replaceable interior cells, missing controller, and any second controller. Return every mismatch for precise ECHO feedback.

- [ ] **Step 4: Register blocks and recipes**

Register:

- `afterlight:gate_frame`
- `afterlight:signal_glass`
- `afterlight:gate_controller`
- `afterlight:gate_field`
- `afterlight:relay_stone`
- `afterlight:return_terminal`
- `afterlight:future_console`

`gate_field` has no item, no loot, no collision, maximum light, and can be replaced only by its owning controller close path.

Use exact recipe ingredients:

- Gate Frame, output 2: crying obsidian corners, Immersive Engineering steel edges, one Mekanism refined obsidian ingot center.
- Signal Glass, output 2: tinted glass corners, AE2 fluix crystals on edges, one echo shard center.
- Gate Controller, output 1: lodestone center, four PneumaticCraft printed circuit boards, two AE2 logic processors, and two Undercurrent stabilizers.

Each recipe declares NeoForge mod-loaded conditions for every external namespace it references. This keeps standalone companion GameTests free of missing-registry recipe errors while loading all three recipes in the full pack. Static tests require the exact conditions and ingredients, including `kubejs:undercurrent_stabilizer` for the controller.

- [ ] **Step 5: Run unit tests and registry boot**

Run:

```bash
gradle test --tests 'org.rllabs.afterlight.gate.GatePattern*Test' -PafterlightLockContext=macos --no-daemon
gradle runGameTestServer -PafterlightLockContext=macos --no-daemon
```

Expected: pattern tests pass and all seven blocks register.

- [ ] **Step 6: Commit**

```bash
git add src
git commit -m "feat: register the physical Gate structure" \
  -m "Co-Authored-By: Codex <noreply@openai.com>"
```

---

### Task 2: Activation, FTB Prerequisites, and Restart Safety

**Files:**
- Create: `src/main/java/org/rllabs/afterlight/gate/GateActivationService.java`
- Create: `src/main/java/org/rllabs/afterlight/gate/GateProgressGateway.java`
- Create: `src/main/java/org/rllabs/afterlight/gate/FtbGateProgressGateway.java`
- Modify: `src/main/java/org/rllabs/afterlight/gate/GateControllerBlock.java`
- Modify: `src/main/java/org/rllabs/afterlight/gate/GateControllerBlockEntity.java`
- Test: `src/test/java/org/rllabs/afterlight/gate/GateActivationServiceTest.java`
- Test: `src/test/java/org/rllabs/afterlight/gate/GateControllerGameTests.java`
- Modify: `src/test/java/org/rllabs/afterlight/ReleaseJarContractTest.java`

**Interfaces:**
- Consumes: matched pattern, inserted core count, activating player, FTB task state, destination availability, current game time.
- Produces: `ActivationDecision`, open deadline `now + 220`, linked field placement, safe close, and restart recovery.

- [ ] **Step 1: Write failing activation tests**

Test exact rejection codes:

```java
MALFORMED_STRUCTURE
INTERIOR_BLOCKED
MISSING_CORE
WRONG_CORE_COUNT
ENERGY_PROOF_INCOMPLETE
GATE_CORE_PROOF_INCOMPLETE
DESTINATION_UNAVAILABLE
ALREADY_OPEN
```

Test success deadline `220`, stale saved deadline closes on load, future saved deadline resumes only until its original deadline, and core insertion/removal never changes count.

- [ ] **Step 2: Run tests and verify RED**

Run: `gradle test --tests '*GateActivationServiceTest' -PafterlightLockContext=macos --no-daemon`

Expected: FAIL because activation types are missing.

- [ ] **Step 3: Implement the pure activation service**

Use exact task IDs:

- Energy proof: `6E494144394F75AF`
- Gate Core proof: `568026383F54186C`

`GateProgressGateway.completed(ServerPlayer, long taskId)` reads the player's current FTB team data. No client packet can assert completion.

- [ ] **Step 4: Implement block entity persistence and field ownership**

Persist orientation, core stack, state, deadline, and a random field UUID. Opening writes field blocks only after all prerequisites pass. Every field stores or resolves the owning controller position and UUID. Close removes only matching field blocks.

On load:

- Deadline at or before current game time closes immediately.
- Valid future deadline resumes ticking.
- Missing controller, mismatched UUID, or malformed frame closes and enters fault state.

- [ ] **Step 5: Run unit and GameTests**

Run:

```bash
gradle test --tests '*GateActivationServiceTest' -PafterlightLockContext=macos --no-daemon
gradle runGameTestServer -PafterlightLockContext=macos --no-daemon
```

Expected: activation tests and restart GameTests pass.

- [ ] **Step 6: Commit**

```bash
git add src/main/java/org/rllabs/afterlight/gate src/test/java/org/rllabs/afterlight/gate
git commit -m "feat: open the Gate for eleven seconds" \
  -m "Co-Authored-By: Codex <noreply@openai.com>"
```

---

### Task 3: Far Relay Worldgen and Idempotent Sites

**Files:**
- Create: all Far Relay dimension, dimension type, biome, noise settings, and loot JSON files
- Create: `src/main/java/org/rllabs/afterlight/relay/FarRelayKeys.java`
- Create: `src/main/java/org/rllabs/afterlight/relay/FarRelaySavedData.java`
- Create: `src/main/java/org/rllabs/afterlight/relay/RelaySite.java`
- Create: `src/main/java/org/rllabs/afterlight/relay/FarRelayInitializer.java`
- Test: `src/test/java/org/rllabs/afterlight/relay/FarRelayDataContractTest.java`
- Test: `src/test/java/org/rllabs/afterlight/relay/FarRelayInitializerTest.java`
- Test: `src/test/java/org/rllabs/afterlight/relay/FarRelayGameTests.java`
- Modify: `src/test/java/org/rllabs/afterlight/ReleaseJarContractTest.java`

**Interfaces:**
- Consumes: Far Relay `ServerLevel` and world saved data.
- Produces: registered `afterlight:far_relay`, central arrival site, four satellite sites, and idempotent schema-1 initialization.

- [ ] **Step 1: Write failing data contracts**

Require:

- Dimension uses `minecraft:noise`, fixed biome `afterlight:far_relay`, and settings `afterlight:far_relay`.
- Noise settings match vanilla 1.21.1 End router fields but use `afterlight:relay_stone` as default and surface block.
- Biome contains empty spawn lists and no End spike or platform feature.
- Dimension type fixed time is 6000, skylight false, bed false, respawn anchor false, coordinate scale 1.0.

- [ ] **Step 2: Run data tests and verify RED**

Run: `gradle test --tests '*FarRelayDataContractTest' -PafterlightLockContext=macos --no-daemon`

Expected: FAIL because Far Relay data is missing.

- [ ] **Step 3: Add pinned worldgen resources**

Copy the vanilla 1.21.1 End noise router exactly from the authenticated Minecraft client artifact, changing only default block and surface result to `afterlight:relay_stone`. Set custom biome fog, water, sky, and white-ash particle values. Register custom client effects under `afterlight:far_relay` in Task 5.

- [ ] **Step 4: Write failing initializer tests**

Use sites:

```text
CENTRAL  (0, 0)
EAST     (256, 0)
WEST     (-256, 0)
SOUTH    (0, 256)
NORTH    (0, -256)
```

Tests require a safe 11 by 11 platform at each site, central return terminal, central future console, one loot chest per site, and no mutation on second initialization.

- [ ] **Step 5: Implement schema-1 SavedData and deterministic builds**

`FarRelaySavedData` stores schema and an enum set of initialized sites. `FarRelayInitializer.ensureAll` obtains each site chunk, finds the first safe surface near Y 64, or builds at Y 72 when none exists. It sets the saved bit only after all required blocks and loot-table references are present.

Do not overwrite non-replaceable player blocks after a site's bit is set. A partial site with no bit is validated and repaired only inside its fixed 15 by 15 construction box.

- [ ] **Step 6: Run unit and GameTests**

Run:

```bash
gradle test --tests 'org.rllabs.afterlight.relay.*' -PafterlightLockContext=macos --no-daemon
gradle runGameTestServer -PafterlightLockContext=macos --no-daemon
```

Expected: worldgen loads, all five sites initialize once, and no mobs are configured.

- [ ] **Step 7: Commit**

```bash
git add src/main/java/org/rllabs/afterlight/relay \
  src/main/resources/data/afterlight src/test/java/org/rllabs/afterlight/relay
git commit -m "feat: create the Far Relay expedition" \
  -m "Co-Authored-By: Codex <noreply@openai.com>"
```

---

### Task 4: Travel and Guaranteed Return

**Files:**
- Create: `src/main/java/org/rllabs/afterlight/gate/GateReturnTarget.java`
- Create: `src/main/java/org/rllabs/afterlight/gate/GateTravelService.java`
- Modify: `src/main/java/org/rllabs/afterlight/EchoContent.java`
- Modify: `src/main/java/org/rllabs/afterlight/gate/GateFieldBlock.java`
- Create: `src/main/java/org/rllabs/afterlight/relay/ReturnTerminalBlock.java`
- Create: `src/main/resources/data/afterlight/advancement/gate_opened.json`
- Create: `src/main/resources/data/afterlight/advancement/far_relay_arrival.json`
- Test: `src/test/java/org/rllabs/afterlight/gate/GateTravelServiceTest.java`
- Test: `src/test/java/org/rllabs/afterlight/gate/GateTravelGameTests.java`
- Modify: `src/test/java/org/rllabs/afterlight/ReleaseJarContractTest.java`

**Interfaces:**
- Consumes: entering `ServerPlayer`, source controller position, destination level, and optional stored return target.
- Produces: persisted return target, safe destination transfer, advancement grant, exact return, and shared-spawn fallback.

- [ ] **Step 1: Write failing travel tests**

Cover:

- Source overworld position is stored before transfer.
- Far Relay arrival uses central safe platform.
- Exact source return is used when safe.
- Obstructed source searches a 5-block radius and 6-block vertical range.
- Missing source level or no safe source uses overworld shared spawn.
- Return clears the stored target only after successful transfer.
- Restart preserves the target.
- Two players retain independent targets.

- [ ] **Step 2: Run tests and verify RED**

Run: `gradle test --tests '*GateTravel*Test' -PafterlightLockContext=macos --no-daemon`

Expected: FAIL because travel types are missing.

- [ ] **Step 3: Register and persist the return attachment**

Use a codec-backed player attachment with dimension resource key, block position, yaw, and pitch. Enable copy-on-death so a player who dies during an expedition does not corrupt the stored route. Clear stale targets after safe return.

- [ ] **Step 4: Implement server-only travel**

`GateFieldBlock.entityInside` acts only for `ServerPlayer`, only on the server, and rate-limits repeated collision ticks. Before transfer, ensure the Far Relay and central site exist. Use `DimensionTransition` with safe coordinates and preserve player velocity as zero.

`ReturnTerminalBlock` invokes the same service in reverse. Shared-spawn fallback uses `server.overworld().getSharedSpawnPos()` plus safe-position search.

- [ ] **Step 5: Run unit and GameTests**

Run:

```bash
gradle test --tests '*GateTravel*Test' -PafterlightLockContext=macos --no-daemon
gradle runGameTestServer -PafterlightLockContext=macos --no-daemon
```

Expected: all travel, fallback, restart, and multiplayer isolation tests pass.

- [ ] **Step 6: Commit**

```bash
git add src
git commit -m "feat: guarantee Gate expedition return" \
  -m "Co-Authored-By: Codex <noreply@openai.com>"
```

---

### Task 5: Gate and Relay Presentation

**Files:**
- Create: `src/main/java/org/rllabs/afterlight/client/FarRelayEffects.java`
- Create: `src/main/java/org/rllabs/afterlight/client/GateRenderer.java`
- Modify: `src/main/java/org/rllabs/afterlight/client/AfterlightClient.java`
- Create: blockstates, models, item models, textures, and `sounds.json` listed in File Structure
- Test: `src/test/java/org/rllabs/afterlight/client/GateAssetContractTest.java`
- Modify: `src/test/java/org/rllabs/afterlight/ReleaseJarContractTest.java`

**Interfaces:**
- Consumes: registered Gate blocks, block entity state, and Far Relay dimension type.
- Produces: custom fog and sky, animated opening field, original block textures, and state-specific sounds.

- [ ] **Step 1: Write failing asset contracts**

Require every registered block to have a blockstate, block model, item model where applicable, loot table where applicable, translation, and PNG. Require field animation metadata and three sound events: `gate_open`, `gate_close`, `gate_fault`.

- [ ] **Step 2: Run asset tests and verify RED**

Run: `gradle test --tests '*GateAssetContractTest' -PafterlightLockContext=macos --no-daemon`

Expected: FAIL with the missing asset inventory.

- [ ] **Step 3: Generate and author original assets**

Use the Signal Reliquary material language: basalt-black frame, smoked signal glass, cyan safe-state trace, amber memory trace, and fault red only in the fault model. Generate source concepts, then hand-author tileable block textures and model JSON.

- [ ] **Step 4: Register dimension effects and renderer**

Use `RegisterDimensionSpecialEffectsEvent` for `afterlight:far_relay`. Render a dark fixed sky without vanilla End stars, use biome fog, and preserve weather-free visibility. The Gate renderer interpolates from controller state and never reads server classes on the client.

- [ ] **Step 5: Run tests and client visual acceptance**

Run:

```bash
gradle test --tests '*GateAssetContractTest' -PafterlightLockContext=macos --no-daemon
gradle runClient -PafterlightLockContext=macos --no-daemon
```

Build a Gate, capture idle, open, fault, Far Relay arrival, central relay, each satellite direction, and return screenshots. Confirm frame readability without shaders and with the pack's default renderer.

- [ ] **Step 6: Commit**

```bash
git add src/main/java/org/rllabs/afterlight/client src/main/resources/assets src/test
git commit -m "feat: render the Signal Reliquary Gate" \
  -m "Co-Authored-By: Codex <noreply@openai.com>"
```

---

### Task 6: Gate Release v0.2.0

**Files:**
- Modify: `gradle.properties`
- Modify: `README.md`
- Modify: `src/test/java/org/rllabs/afterlight/ReleaseJarContractTest.java`
- Create: `docs/releases/0.2.0.md`

**Interfaces:**
- Consumes: Tasks 1 through 5 and companion release gates.
- Produces: immutable `v0.2.0` asset `afterlight-signal-0.2.0+1.21.1.jar` and checksums for final pack integration.

- [ ] **Step 1: Expand the release contract**

Require every Gate and Far Relay class, data file, asset, translation, recipe, advancement, and loot table in the exact JAR inventory. Reject any vanilla namespace override.

- [ ] **Step 2: Run two clean release builds**

Run twice:

```bash
gradle clean test runGameTestServer build verifyReleaseJar \
  -PafterlightRelease=true -PafterlightLockContext=macos \
  --no-daemon --no-build-cache --rerun-tasks
```

Expected: both runs pass and JAR SHA-256 values match.

- [ ] **Step 3: Run dedicated server and development client acceptance**

The dedicated server must register `afterlight:far_relay`, load FTB dependencies, and complete GameTests. The development client must complete one open, travel, return, restart, and second-open sequence in a disposable world.

- [ ] **Step 4: Commit the version and release record**

```bash
git add gradle.properties README.md src/test docs/releases/0.2.0.md
git commit -m "release: prepare Signal 0.2.0" \
  -m "Co-Authored-By: Codex <noreply@openai.com>"
```

- [ ] **Step 5: Push, require exact CI, and publish**

Push `main`, require green CI at exact HEAD, create annotated tag `v0.2.0`, and publish only the JAR plus checksums. Download the public asset and prove byte equality with the locally accepted JAR.

## Completion Gate

The plan is complete only when the physical structure rejects every malformed variant, opens for exactly 220 ticks, survives restart safely, the Far Relay loads without ordinary mobs, all five sites initialize idempotently, two players retain independent return routes, and public `v0.2.0` bytes match the accepted build.
