# AFTERLIGHT Signal Companion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and publish the NeoForge 1.21.1 `AFTERLIGHT Signal` companion mod with the physical ECHO, safe recovery, FTB-backed guided interface, and Signal Reliquary title screen.

**Architecture:** A separate public repository, `Luskish/afterlight-signal`, owns the Java mod and immutable release JAR. Pure domain services define bond, recovery, route, and screen state; thin NeoForge and FTB adapters connect those services to persisted player attachments, item data components, network payloads, and FTB Quests' server-authoritative messages.

**Tech Stack:** Java 21, NeoForge 21.1.248, ModDevGradle 2.0.143, Gradle 9.2.1, JUnit 5.11.4, FTB Quests 2101.1.30, FTB Library 2101.1.35, FTB Teams 2101.1.10, GitHub Actions.

## Global Constraints

- Minecraft stays exactly `1.21.1` and NeoForge stays exactly `21.1.248`.
- Java stays exactly `21`.
- Mod ID is `afterlight`; display name is `AFTERLIGHT Signal`.
- ECHO means `Emergency Continuity Heuristic Orchestrator`.
- No U+2014 em dash appears in source, resources, commits, or documentation.
- FTB Quests remains authoritative for progress, submission, and claims.
- No JAR, token, credential, or private key is committed to source control.
- Client-only classes remain unreachable from dedicated-server entry paths.
- Release artifacts are deterministic and record exact source provenance.
- Every commit ends with `Co-Authored-By: Codex <noreply@openai.com>`.

## File Structure

Create the repository at `/Users/shaneliszewski/afterlight-signal` with these responsibility boundaries:

```text
AGENTS.md                                      repository guardrails
build.gradle                                  pinned build, test, provenance, release verification
gradle.properties                             exact versions and mod identity
settings.gradle                               repositories and dependency verification
gradle/verification-metadata.xml              authenticated dependency metadata
.github/workflows/build.yml                   clean test and reproducible build gate
src/main/java/org/rllabs/afterlight/
  Afterlight.java                             mod bootstrap only
  EchoContent.java                            item, component, attachment, and creative-tab registration
  echo/EchoBond.java                          persisted player bond value
  echo/EchoIdentity.java                      item owner and generation value
  echo/EchoRecoveryService.java               pure transactional issue and recovery logic
  echo/EchoRuntimeService.java                ServerPlayer and ItemStack adapter
  echo/EchoItem.java                          server-approved use request
  echo/EchoCommands.java                      recover and inspect commands
  echo/EchoPlayerEvents.java                  first-login issue and clone handling
  network/AfterlightPayloads.java              payload registration
  network/OpenEchoRequest.java                client-to-server open request
  network/OpenEchoScreen.java                 server-to-client open approval
  route/EchoRoute.java                        validated route schema
  route/EchoRouteLoader.java                  config JSON loading
  route/EchoQuestSnapshot.java                FTB-neutral quest projection
  route/EchoRecommendation.java               resolver output
  route/EchoRouteResolver.java                deterministic next-step policy
  client/integration/FtbQuestGateway.java     physically client-only exact FTB Quests adapter
src/main/java/org/rllabs/afterlight/client/
  AfterlightClient.java                       client event registration
  EchoScreenModel.java                        pure screen state and action eligibility
  EchoScreen.java                             Signal Reliquary rendering and input
  SignalTitleScreen.java                      custom title destination routing
  SignalTitleScreenHook.java                  safe vanilla-screen replacement
  SignalClientConfig.java                     vanilla-title troubleshooting option
src/main/resources/
  META-INF/neoforge.mods.toml                  exact dependency contract
  assets/afterlight/lang/en_us.json            item, UI, command, and failure copy
  assets/afterlight/models/item/echo.json      three-dimensional handheld model
  assets/afterlight/textures/item/echo.png     original 64 by 64 pixel texture
  assets/afterlight/textures/gui/title.png     original 1920 by 1080 title artwork
  assets/afterlight/textures/gui/echo_panel.png original UI panel texture
  pack.mcmeta                                  resource metadata
src/test/java/org/rllabs/afterlight/           unit and metadata contract tests
src/test/resources/routes/                     valid and adversarial route fixtures
```

---

### Task 1: Repository and Dependency Contract

**Files:**
- Create: `/Users/shaneliszewski/afterlight-signal/AGENTS.md`
- Create: `/Users/shaneliszewski/afterlight-signal/build.gradle`
- Create: `/Users/shaneliszewski/afterlight-signal/gradle.properties`
- Create: `/Users/shaneliszewski/afterlight-signal/settings.gradle`
- Create: `/Users/shaneliszewski/afterlight-signal/src/main/java/org/rllabs/afterlight/Afterlight.java`
- Create: `/Users/shaneliszewski/afterlight-signal/src/main/java/org/rllabs/afterlight/EchoContent.java`
- Create: `/Users/shaneliszewski/afterlight-signal/src/main/resources/META-INF/neoforge.mods.toml`
- Create: `/Users/shaneliszewski/afterlight-signal/src/main/resources/pack.mcmeta`
- Test: `/Users/shaneliszewski/afterlight-signal/src/test/java/org/rllabs/afterlight/ModMetadataTest.java`

**Interfaces:**
- Consumes: NeoForge `IEventBus` supplied to the mod constructor.
- Produces: `Afterlight.MOD_ID`, exact Gradle properties, exact loader dependencies, and a runnable empty mod used by every later task.

- [ ] **Step 1: Create the repository and guardrails**

Run:

```bash
gh repo create Luskish/afterlight-signal --public \
  --description "AFTERLIGHT Signal companion for NeoForge 1.21.1"
git clone https://github.com/Luskish/afterlight-signal.git /Users/shaneliszewski/afterlight-signal
```

Write `AGENTS.md` with the pack's no-em-dash, skills-first, TDD, verification, no-JAR, no-secret, exact-version, and commit-trailer rules. Add a rule that releases are immutable and never overwritten.

- [ ] **Step 2: Write the failing metadata contract test**

```java
@Test
void pinsThePackRuntimeContract() throws Exception {
    var properties = new Properties();
    try (var input = Files.newInputStream(Path.of("gradle.properties"))) {
        properties.load(input);
    }
    assertEquals("1.21.1", properties.getProperty("minecraft_version"));
    assertEquals("21.1.248", properties.getProperty("neo_version"));
    assertEquals("2101.1.30", properties.getProperty("ftb_quests_version"));
    assertEquals("afterlight", properties.getProperty("mod_id"));
}
```

- [ ] **Step 3: Run the test and verify RED**

Run: `gradle test --tests org.rllabs.afterlight.ModMetadataTest --no-daemon`

Expected: FAIL because the project and pinned properties do not exist.

- [ ] **Step 4: Implement the minimal ModDevGradle project**

Use `net.neoforged.moddev` version `2.0.143`, Java toolchain 21, JUnit 5.11.4, and these exact dependencies:

```groovy
repositories {
    mavenCentral()
    maven { url = "https://maven.ftb.dev/releases" }
}

neoForge {
    version = project.neo_version
    mods { afterlight { sourceSet sourceSets.main } }
    unitTest { enable(); testedMod = mods.afterlight }
}

dependencies {
    implementation("dev.ftb.mods:ftb-quests-neoforge:${ftb_quests_version}") { transitive false }
    implementation("dev.ftb.mods:ftb-library-neoforge:${ftb_library_version}") { transitive false }
    implementation("dev.ftb.mods:ftb-teams-neoforge:${ftb_teams_version}") { transitive false }
    testImplementation "org.junit.jupiter:junit-jupiter:5.11.4"
    testRuntimeOnly "org.junit.platform:junit-platform-launcher"
}
```

Add exact `neoforge.mods.toml` dependency ranges for NeoForge, Minecraft, FTB Quests, FTB Library, and FTB Teams. Use a one-class bootstrap:

```java
@Mod(Afterlight.MOD_ID)
public final class Afterlight {
    public static final String MOD_ID = "afterlight";

    public Afterlight(IEventBus modBus) {
        EchoContent.register(modBus);
    }
}
```

Task 1 may temporarily register an empty `EchoContent.register` method so the bootstrap compiles.

- [ ] **Step 5: Lock dependencies and verify GREEN**

Run:

```bash
gradle dependencies --write-locks --no-daemon
gradle --write-verification-metadata sha256 help --no-daemon
gradle clean test build --no-daemon
```

Expected: `BUILD SUCCESSFUL` and `ModMetadataTest` passes.

- [ ] **Step 6: Commit**

```bash
git add .
git commit -m "build: scaffold AFTERLIGHT Signal" \
  -m "Co-Authored-By: Codex <noreply@openai.com>"
```

---

### Task 2: Bond and Transactional Recovery Domain

**Files:**
- Create: `src/main/java/org/rllabs/afterlight/echo/EchoBond.java`
- Create: `src/main/java/org/rllabs/afterlight/echo/EchoIdentity.java`
- Create: `src/main/java/org/rllabs/afterlight/echo/EchoInventory.java`
- Create: `src/main/java/org/rllabs/afterlight/echo/EchoRecoveryService.java`
- Test: `src/test/java/org/rllabs/afterlight/echo/EchoRecoveryServiceTest.java`

**Interfaces:**
- Consumes: `UUID playerId`, current `EchoBond`, epoch seconds, and `EchoInventory`.
- Produces: `EchoRecoveryService.issueFirst(...)`, `EchoRecoveryService.recover(...)`, `EchoRecoveryService.isValid(...)`, `RecoveryResult`, `EchoBond.CODEC`, and `EchoIdentity.CODEC` for runtime registration.

- [ ] **Step 1: Write failing recovery tests**

Cover these exact cases:

```java
@Test void firstIssueCreatesGenerationOne();
@Test void recoveryIncrementsGenerationOnce();
@Test void fullInventoryLeavesBondUnchanged();
@Test void staleGenerationIsInvalid();
@Test void foreignOwnerIsInvalid();
@Test void generationMustStayPositive();
@Test void bondCodecRoundTrips();
@Test void identityCodecRoundTrips();
@Test void generationExhaustionLeavesBondUnchanged();
@Test void noSpaceWinsBeforeGenerationExhaustion();
@Test void malformedOwnerReturnsCodecError();
```

The no-space assertion is exact:

```java
var result = service.recover(playerId, originalBond, 10L, inventoryWithoutSpace);
assertEquals(RecoveryStatus.NO_SPACE, result.status());
assertEquals(originalBond, result.bond());
assertTrue(result.identity().isEmpty());
assertEquals(0, inventoryWithoutSpace.insertCalls());
```

- [ ] **Step 2: Run tests and verify RED**

Run: `gradle test --tests 'org.rllabs.afterlight.echo.*' --no-daemon`

Expected: FAIL with missing bond and recovery classes.

- [ ] **Step 3: Implement immutable domain values**

Use these signatures:

```java
public record EchoBond(boolean issued, int generation, long issuedAtEpochSecond) {
    public static final EchoBond UNISSUED = new EchoBond(false, 0, 0L);
}

public record EchoIdentity(UUID owner, int generation) {}

public interface EchoInventory {
    boolean hasFreeSlot();
    boolean insert(EchoIdentity identity);
}

public enum RecoveryStatus { ISSUED, NO_SPACE, INSERT_FAILED, GENERATION_EXHAUSTED }

public record RecoveryResult(
        RecoveryStatus status,
        EchoBond bond,
        Optional<EchoIdentity> identity) {}
```

`EchoBond` and `EchoIdentity` each expose a `public static final Codec<...> CODEC` using stable snake_case field names. The codec tests round-trip representative values through `JsonOps.INSTANCE` and assert exact equality. Malformed UUID text must return a codec error instead of throwing.

`EchoRecoveryService` checks capacity before incrementing. If the current generation is `Integer.MAX_VALUE`, it returns `GENERATION_EXHAUSTED` with the original bond and no insertion call. If insertion fails after the capacity check, it returns `INSERT_FAILED` with the original bond. Tests record inventory calls and prove `hasFreeSlot` precedes `insert`. `isValid` requires owner equality, issued state, positive generation, and exact generation equality.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `gradle test --tests 'org.rllabs.afterlight.echo.*' --no-daemon`

Expected: all eleven tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/main/java/org/rllabs/afterlight/echo src/test/java/org/rllabs/afterlight/echo
git commit -m "feat: define ECHO bond recovery" \
  -m "Co-Authored-By: Codex <noreply@openai.com>"
```

---

### Task 3: Runtime Item, Payloads, and Commands

**Files:**
- Modify: `src/main/java/org/rllabs/afterlight/Afterlight.java`
- Modify: `src/main/java/org/rllabs/afterlight/EchoContent.java`
- Create: `src/main/java/org/rllabs/afterlight/echo/EchoItem.java`
- Create: `src/main/java/org/rllabs/afterlight/echo/EchoRuntimeService.java`
- Create: `src/main/java/org/rllabs/afterlight/echo/EchoCommands.java`
- Create: `src/main/java/org/rllabs/afterlight/echo/EchoPlayerEvents.java`
- Create: `src/main/java/org/rllabs/afterlight/network/AfterlightPayloads.java`
- Create: `src/main/java/org/rllabs/afterlight/network/OpenEchoRequest.java`
- Create: `src/main/java/org/rllabs/afterlight/network/OpenEchoScreen.java`
- Create: `src/main/java/org/rllabs/afterlight/client/AfterlightClient.java`
- Create: `src/main/resources/assets/afterlight/lang/en_us.json`
- Test: `src/test/java/org/rllabs/afterlight/echo/EchoRuntimeContractTest.java`
- Test: `src/test/java/org/rllabs/afterlight/echo/EchoGameTests.java`

**Interfaces:**
- Consumes: Task 2 domain services.
- Produces: registered `afterlight:echo`, `afterlight:echo_identity`, `afterlight:echo_bond`, `/echo recover`, `/echo inspect`, and server-approved screen opening.

- [ ] **Step 1: Write failing runtime contract tests**

Assert registry IDs against literal required resource locations, translation keys, payload IDs and directions, constructed Brigadier permission behavior, and that every compiled common production class remains free of client dependencies.

Add GameTests for exact one-tick first issue, no second login issue, recovery generation increment, full-inventory refusal, foreign item refusal, stale item refusal, valid-item approval, logout cancellation, and reconnect delay reset. Rejection tests assert the exact translated rejection state and recipient.

- [ ] **Step 2: Run focused tests and verify RED**

Run:

```bash
gradle test --tests '*EchoRuntimeContractTest' --no-daemon
gradle runGameTestServer --no-daemon
```

Expected: FAIL because runtime registrations and GameTests are absent.

- [ ] **Step 3: Register component, attachment, and item**

Register `DataComponentType<EchoIdentity>` with disk and network codecs. Register `AttachmentType<EchoBond>` with a codec and `copyOnDeath`. Register `EchoItem` at `afterlight:echo` with stack size one and epic rarity.

The item use flow is exact:

1. Client sends `OpenEchoRequest` for the held hand.
2. Server resolves the current held stack again.
3. Server validates identity against the player's attachment.
4. Server sends `OpenEchoScreen` only on success.
5. Client opens a minimal Signal Reliquary placeholder only from that approval payload through the physically client-only `AfterlightClient` entrypoint. Task 5 replaces the placeholder with the guided screen without changing the authorization path.

- [ ] **Step 4: Implement runtime recovery and first issue**

`EchoRuntimeService` adapts `ServerPlayer.getInventory()` to `EchoInventory`, creates the stack, sets the identity component, inserts the item, and updates the attachment only after insertion succeeds.

`EchoPlayerEvents` issues on first login after exactly one scheduled server post-tick. Pending work is bound to the concrete login session through a `WeakReference<ServerPlayer>`, so the static scheduler cannot retain a stopped server graph. Logout cancels that session's work, and reconnect replaces the pending entry with a fresh one-tick delay. A contract test verifies the pending value has no strong `ServerPlayer` field. It does not scan containers or replace an already issued bond.

`/echo recover` runs at permission zero through the shared service. `/echo inspect <player>` requires permission two and prints issued state, generation, and issue time without modifying data.

- [ ] **Step 5: Add exact failure copy**

Add translation keys for no-space, insertion-failed, generation-exhausted, foreign-unit, superseded-unit, recovery-success, first-issue, inspect, signal-not-acquired, and placeholder-screen states. All narrative copy uses ECHO's concise voice.

- [ ] **Step 6: Run focused tests and verify GREEN**

Run:

```bash
gradle test --tests '*EchoRuntimeContractTest' --no-daemon
gradle runGameTestServer --no-daemon
```

Expected: all runtime contracts and GameTests pass.

- [ ] **Step 7: Commit**

```bash
git add src
git commit -m "feat: issue and recover physical ECHO units" \
  -m "Co-Authored-By: Codex <noreply@openai.com>"
```

---

### Task 4: Route Schema and FTB Gateway

**Files:**
- Create: `src/main/java/org/rllabs/afterlight/route/EchoRoute.java`
- Create: `src/main/java/org/rllabs/afterlight/route/EchoRouteLoader.java`
- Create: `src/main/java/org/rllabs/afterlight/route/EchoQuestSnapshot.java`
- Create: `src/main/java/org/rllabs/afterlight/route/EchoRecommendation.java`
- Create: `src/main/java/org/rllabs/afterlight/route/EchoRouteResolver.java`
- Create: `src/main/java/org/rllabs/afterlight/integration/EchoQuestGateway.java`
- Create: `src/main/java/org/rllabs/afterlight/client/integration/FtbQuestGateway.java`
- Test: `src/test/java/org/rllabs/afterlight/route/EchoRouteLoaderTest.java`
- Test: `src/test/java/org/rllabs/afterlight/route/EchoRouteResolverTest.java`
- Test: `src/test/resources/routes/valid.json`
- Test: `src/test/resources/routes/duplicate.json`
- Test: `src/test/resources/routes/cycle.json`
- Test: `src/test/resources/routes/unknown-state.json`

**Interfaces:**
- Consumes: `config/afterlight/echo_route.json` and synchronized FTB client data.
- Produces: validated `EchoRoute`, `EchoRecommendation resolve(EchoRoute, Map<Long, EchoQuestSnapshot>)`, and `EchoQuestGateway` actions.

- [ ] **Step 1: Write failing schema tests**

Use a schema with hexadecimal FTB IDs:

```json
{
  "schema": 1,
  "terminal_quest": "31C9557D2F51238F",
  "segments": [
    {"id": "cold_boot", "after": [], "quests": ["01", "02"]}
  ]
}
```

Each segment has an `after` array of segment IDs, which may be empty. Tests reject non-schema-1 files, empty segments, duplicate quest IDs within or across segments, invalid hexadecimal IDs, duplicate segment IDs, unknown segment dependencies, dependency cycles, segments unreachable from every zero-dependency root, and a terminal quest absent from the route.

- [ ] **Step 2: Write failing resolver tests**

Cover exact precedence:

1. Earliest unclaimed reward.
2. Earliest startable incomplete quest.
3. Earliest locked quest with unmet dependency copy.
4. Route complete.

Also prove optional side quests do not displace the configured route and team-complete state is respected.

- [ ] **Step 3: Run tests and verify RED**

Run: `gradle test --tests 'org.rllabs.afterlight.route.*' --no-daemon`

Expected: FAIL because route types and resolver are missing.

- [ ] **Step 4: Implement pure route types and loader**

Use immutable records and return all validation errors in one `RouteValidationException`. Convert FTB hexadecimal IDs with `Long.parseUnsignedLong(value, 16)` and render them back as 16 uppercase digits.

`EchoQuestSnapshot` is FTB-neutral and contains quest ID, title, subtitle, team-complete state, startable state, unmet dependency IDs, task snapshots, and reward snapshots. Nested task snapshots contain ID, title, current value, required value, complete state, actual manual-submit state, direct-interaction support, and live submit eligibility. Nested reward snapshots contain ID, title, claimed state, choice state, direct-interaction support, and live claim eligibility. Interaction support and live eligibility are separate values.

`EchoRecommendation` has exactly five kinds: `SIGNAL_UNAVAILABLE`, `CLAIM_REWARD`, `SUBMIT_TASK`, `LOCKED`, and `ROUTE_COMPLETE`. It carries the selected quest ID plus an optional task ID, reward ID, or earliest unmet dependency ID. If any configured route quest lacks a synchronized snapshot, resolution stops with `SIGNAL_UNAVAILABLE`; it never reports completion or a later action from partial data. Choice or otherwise unsupported rewards select the quest with `requiresArchive=true` and never expose direct claim eligibility. Supported but currently ineligible rewards are skipped so they cannot displace a later claimable reward.

- [ ] **Step 5: Implement the FTB-neutral gateway**

Use these methods:

```java
public interface EchoQuestGateway {
    Map<Long, EchoQuestSnapshot> snapshots(EchoRoute route);
    void submit(long taskId);
    void claim(long rewardId);
    void openArchive(long questId);
}
```

The physically client-only `FtbQuestGateway` reads `ClientQuestFile.INSTANCE.selfTeamData`. It submits with `new SubmitTaskMessage(taskId)`, claims with `new ClaimRewardMessage(rewardId, true)`, and opens the exact quest through FTB's supported quest-book message or screen API. Choice rewards expose `requiresArchive=true` and never claim from the compact screen. Missing synchronized data returns an empty snapshot map, which resolves to `SIGNAL_UNAVAILABLE` and disables mutation actions. Add a narrow injectable client-state and dispatch seam so focused tests cover projection of IDs, titles, progress, startability, dependencies, completion, interaction support, and claim state plus submit, claim, and exact-object Archive safety without launching a broad client.

The scheduler regression contract mechanically discovers every GameTest bytecode method that invokes the manual global tick helper. Each discovered caller must use a unique nondefault batch whose name occurs exactly once across every registered AFTERLIGHT GameTest.

- [ ] **Step 6: Run tests and verify GREEN**

Run: `gradle test --tests 'org.rllabs.afterlight.route.*' --no-daemon`

Expected: all schema and precedence tests pass.

- [ ] **Step 7: Commit**

```bash
git add src/main/java/org/rllabs/afterlight/route \
  src/main/java/org/rllabs/afterlight/integration \
  src/main/java/org/rllabs/afterlight/client/integration \
  src/test/java/org/rllabs/afterlight/route src/test/resources/routes
git commit -m "feat: mirror the authoritative ECHO route" \
  -m "Co-Authored-By: Codex <noreply@openai.com>"
```

---

### Task 5: Guided ECHO Screen

**Files:**
- Create: `src/main/java/org/rllabs/afterlight/client/EchoScreenModel.java`
- Create: `src/main/java/org/rllabs/afterlight/client/EchoScreenLayout.java`
- Create: `src/main/java/org/rllabs/afterlight/client/EchoScreen.java`
- Modify: `src/main/java/org/rllabs/afterlight/client/AfterlightClient.java`
- Modify: `src/main/java/org/rllabs/afterlight/integration/EchoQuestGateway.java`
- Modify: `src/main/java/org/rllabs/afterlight/client/integration/FtbQuestGateway.java`
- Modify: `src/main/resources/assets/afterlight/lang/en_us.json`
- Create: `src/main/resources/assets/afterlight/textures/gui/echo_panel.png`
- Test: `src/test/java/org/rllabs/afterlight/client/EchoScreenModelTest.java`
- Test: `src/test/java/org/rllabs/afterlight/client/EchoScreenLayoutTest.java`
- Modify: `src/test/java/org/rllabs/afterlight/client/integration/FtbQuestGatewayTest.java`

**Interfaces:**
- Consumes: Task 4 `EchoRecommendation` and `EchoQuestGateway`.
- Produces: responsive custom screen with Submit, Claim, Pin, Archive, narration, and keyboard focus.

- [ ] **Step 1: Write failing screen-model tests**

Test exact action states:

```java
@Test void enablesSubmitOnlyForManualStartableTask();
@Test void enablesClaimOnlyForUnclaimedNonChoiceReward();
@Test void sendsChoiceRewardToArchive();
@Test void signalMissingDisablesMutationActions();
@Test void escapeClosesWithoutChangingProgress();
```

Test layouts at 854 by 480, 1280 by 720, 1920 by 1080, and GUI scales 2 through 4. Every action hit box must be at least 20 logical pixels high and remain on screen.

- [ ] **Step 2: Run tests and verify RED**

Run: `gradle test --tests 'org.rllabs.afterlight.client.EchoScreen*Test' --no-daemon`

Expected: FAIL because screen model and layout are missing.

- [ ] **Step 3: Implement view model and layout**

`EchoScreenModel` contains only display components, progress values, selected quest, task, or reward IDs, pinned state, and action eligibility. It handles all five Task 4 recommendation kinds. `SIGNAL_UNAVAILABLE` disables Submit, Claim, and Pin. Pin and Archive are enabled only when the selected quest exists in synchronized FTB data. A choice or unsupported interaction disables direct mutation and highlights Archive. Route completion never exposes a mutation action. The screen normalizes a null snapshot map, null entries, or a gateway snapshot exception to `SIGNAL_UNAVAILABLE` instead of throwing.

`EchoScreenLayout.compute(framebufferWidth, framebufferHeight, guiScale)` returns immutable logical-pixel rectangles for header, transcript, route, progress, and action rail. Wide mode uses a vertical right action rail. Standard and compact modes use a horizontal bottom rail. All panes remain on screen without overlap at every tested resolution and scale, with at least two logical pixels between interactive regions. Dimensions below the supported 96 by 80 logical minimum return a non-throwing `MINIMAL` layout. Minimal mode hides panes and actions and renders only a clipped ECHO fault line inside the viewport.

- [ ] **Step 4: Implement rendering and actions**

Render Signal Reliquary colors from constants: cyan `0x43E0D2`, amber `0xE7A64A`, fault red `0xD44045`, bone `0xD8D4C7`, and vault black `0x030506`.

Use native `Button` widgets for narration and focus. Submit and Claim delegate only to the gateway and disable immediately until the specific action target's synchronized fingerprint changes or the bounded cooldown expires. Track every outstanding mutation independently by action and exact target ID; one action never overwrites another, and switching targets cannot discard an earlier cooldown. Unrelated quest or reward changes never clear a pending Submit, Claim, or Pin. A transient null, malformed, throwing, or partially unavailable snapshot is untrusted: it disables current actions but preserves and ages pending mutations until trusted synchronized data returns or their cooldowns expire. Extend `EchoQuestGateway` with `togglePin(long questId)`. The exact FTB adapter rechecks synchronized state and sends `new TogglePinnedMessage(questId)`; snapshots expose current pinned state so the button reads Pin or Unpin truthfully. Archive opens the selected exact quest and remains available whenever that quest exists in synchronized FTB data.

`AfterlightClient` replaces the placeholder only after the existing server approval payload. It loads the default route through `EchoRouteLoader`, constructs `FtbQuestGateway`, and opens `EchoScreen`. Missing or invalid route data opens the screen in a non-mutating signal-unavailable state with concise ECHO diagnostics, never a crash.

Visual structure is exact: `E.C.H.O // SIGNAL RELIQUARY` header, recovered-terminal transcript rail, central route and progress panes, and blackbox-cathedral action rail. Use the approved 70 percent Recovered Terminal and 30 percent Blackbox Cathedral direction. Keep the generated panel text-free; all text, focus states, and progress indicators render in code with the vanilla font.

Every pane label is scissored to its pane. Compact mode uses short labels `LOG`, `ROUTE`, and `STATE` so the required 214 by 120 logical layout cannot overlap neighboring panes. Body lines are clipped or elided when vertical space cannot contain them.

Zero-area rectangles are sentinel geometry only and never overlap any rectangle, including another zero-area sentinel.

- [ ] **Step 5: Generate and verify the original panel texture**

Use the approved original source at `/private/tmp/afterlight-echo-panel-source.png`, generated through the built-in image workflow from the Signal Reliquary design. Reduce it to exactly 256 by 256 with nearest-neighbor sampling and no smoothing. Add an opaque alpha channel if needed. Verify PNG signature, dimensions, RGBA mode, and that its SHA-256 differs from the source and every supplied reference image.

- [ ] **Step 6: Run tests and a development client**

Run:

```bash
gradle test --tests 'org.rllabs.afterlight.client.EchoScreen*Test' --no-daemon
gradle runClient --no-daemon
```

In the dev client, give the item, right-click it, resize the window, exercise keyboard focus, and capture screenshots at standard and large GUI scale.

- [ ] **Step 7: Commit**

```bash
git add src/main/java/org/rllabs/afterlight/client \
  src/main/resources/assets/afterlight/textures/gui \
  src/test/java/org/rllabs/afterlight/client
git commit -m "feat: add the guided ECHO interface" \
  -m "Co-Authored-By: Codex <noreply@openai.com>"
```

---

### Task 6: Signal Reliquary Title and Physical Model

**Files:**
- Create: `src/main/java/org/rllabs/afterlight/client/SignalTitleScreen.java`
- Create: `src/main/java/org/rllabs/afterlight/client/SignalTitleScreenHook.java`
- Create: `src/main/java/org/rllabs/afterlight/client/SignalClientConfig.java`
- Modify: `src/main/java/org/rllabs/afterlight/client/AfterlightClient.java`
- Create: `src/main/resources/assets/afterlight/models/item/echo.json`
- Create: `src/main/resources/assets/afterlight/textures/item/echo.png`
- Create: `src/main/resources/assets/afterlight/textures/gui/title.png`
- Test: `src/test/java/org/rllabs/afterlight/client/SignalTitleContractTest.java`
- Test: `src/test/java/org/rllabs/afterlight/client/EchoModelContractTest.java`

**Interfaces:**
- Consumes: registered ECHO item and client mod lifecycle.
- Produces: original title screen, vanilla fallback config, and three-dimensional handheld model.

- [ ] **Step 1: Write failing title and model contracts**

Assert exactly five destinations: Solo Expedition, Join Expedition, Configuration, Mods, Disconnect. Assert replacement ignores an existing `SignalTitleScreen`, yields when disabled, and never replaces non-title screens.

Inspect `echo.json` to require at least six cuboid elements, third-person and first-person transforms, and only `afterlight` texture references. Inspect `echo.png` as exact 64 by 64 RGBA.

- [ ] **Step 2: Run tests and verify RED**

Run: `gradle test --tests '*SignalTitleContractTest' --tests '*EchoModelContractTest' --no-daemon`

Expected: FAIL because title and model assets are missing.

- [ ] **Step 3: Implement safe title replacement**

Subscribe to `ScreenEvent.Opening`. Replace only vanilla `TitleScreen`, only when the client config is enabled, and never replace `SignalTitleScreen` itself. Preserve vanilla screen construction destinations and accessibility narration.

- [ ] **Step 4: Generate the original title artwork and ECHO texture**

Use image generation for an original broken Ascendancy relay at dawn with dark cathedral silhouettes and restrained cyan telemetry. No text is baked into the background. Generate a separate orthographic ECHO material reference, then hand-author the item texture and JSON cuboids from that reference.

- [ ] **Step 5: Run tests and capture client screenshots**

Run:

```bash
gradle test --tests '*SignalTitleContractTest' --tests '*EchoModelContractTest' --no-daemon
gradle runClient --no-daemon
```

Capture title screen, inventory icon, first-person hold, third-person hold, dropped item, and vanilla-fallback screenshots. Check 16:9, ultrawide crop, and 854 by 480 minimum size.

- [ ] **Step 6: Commit**

```bash
git add src/main/java/org/rllabs/afterlight/client \
  src/main/resources/assets/afterlight src/test/java/org/rllabs/afterlight/client
git commit -m "feat: establish Signal Reliquary presentation" \
  -m "Co-Authored-By: Codex <noreply@openai.com>"
```

---

### Task 7: Reproducible CI and Companion Release

**Files:**
- Modify: `build.gradle`
- Create: `.github/workflows/build.yml`
- Create: `tools/ReleaseSourcePolicy.java`
- Create: `README.md`
- Test: `src/test/java/org/rllabs/afterlight/ReleaseJarContractTest.java`

**Interfaces:**
- Consumes: Tasks 1 through 6.
- Produces: immutable `v0.1.0` release asset `afterlight-signal-0.1.0+1.21.1.jar` and its SHA-512 for pack integration.

- [ ] **Step 1: Write the failing release JAR contract**

Require reproducible timestamps and order, exact metadata entries, provenance JSON with 40-character source SHA and 64-character source-tree SHA-256, no private keys or token families in any regular source file or JAR entry, no U+2014 in any UTF-8 source, and no project or external client-class reference reachable from common entry classes.

- [ ] **Step 2: Run release tests and verify RED**

Run: `gradle clean test build --no-daemon --rerun-tasks`

Expected: FAIL because provenance and release verification are absent.

- [ ] **Step 3: Implement provenance and deterministic build gates**

Follow the proven `afterlight-idas-compat` source-policy pattern, but scope the exact JAR inventory to this mod. Set `preserveFileTimestamps=false` and `reproducibleFileOrder=true`. A release build fails on dirty source, untracked source, symlink, hardlink alias, secret marker, U+2014, unsupported Git object or mode, or source digest mismatch. Before any release compilation, materialize main Java and resources from verified HEAD Git blobs into a private staging tree. Release compilation and packaging consume only that immutable staged snapshot, while developer builds continue using the ordinary working tree.

- [ ] **Step 4: Add pinned GitHub Actions CI**

Use immutable action SHAs for checkout, Temurin 21.0.12, and Gradle 9.2.1. Run:

```bash
gradle clean test runGameTestServer build verifyReleaseJar \
  -PafterlightRelease=true --no-daemon --no-build-cache --rerun-tasks
```

Build twice from the same SHA in two fresh checkout directories with separate `GRADLE_USER_HOME` locations, then compare JAR bytes and SHA-256. The workflow uses no release, publication, secret, or artifact-upload step.

- [ ] **Step 5: Commit the release machinery**

```bash
git add .github build.gradle tools README.md src/test/java/org/rllabs/afterlight/ReleaseJarContractTest.java
git commit -m "ci: authenticate companion releases" \
  -m "Co-Authored-By: Codex <noreply@openai.com>"
```

- [ ] **Step 6: Verify locally and push**

Run the exact CI command twice, compare artifacts, scan the repository for U+2014 and secrets, and require a clean tree. Push `main` only after local success and require green CI at the exact SHA.

- [ ] **Step 7: Publish immutable v0.1.0**

Create annotated tag `v0.1.0`, push it, and attach only `afterlight-signal-0.1.0+1.21.1.jar` plus checksums. Record SHA-256, SHA-512, size, source SHA, and CI URL in the release notes.

## Completion Gate

The plan is complete only when `v0.1.0` is downloadable, its bytes match the locally verified artifact, dedicated-server tests contain no client leak, the development client displays both custom screens and the physical item, and every test and CI run is green at the published source SHA.
