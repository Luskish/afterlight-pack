# AFTERLIGHT Signal Reliquary Experience Design

Date: 2026-08-11

Status: approved by Shane through the Signal Reliquary selection, ECHO recovery decision, ECHO identity approval, public CurseForge authorization, and instruction to implement autonomously.

## Purpose

Turn the stable AFTERLIGHT pack into a distinct authored experience without sacrificing the current kitchen-sink freedom, quest authority, launcher compatibility, or live world.

The release adds four cohesive player-facing systems:

1. A physical ECHO companion with its own guided quest interface.
2. A Signal Reliquary title screen and visual language.
3. A public launcher-neutral download portal with durable Prism and CurseForge instructions.
4. A physical Gate of Return that opens an additive postgame expedition dimension.

The ECHO companion and public delivery are release-critical. The Gate expedition is isolated behind its own verification boundary. It may ship in the same candidate only after passing its dedicated tests and a clean live-world backup gate.

## Selected Direction

### Signal Reliquary

The visual language is 70 percent Recovered Terminal and 30 percent Blackbox Cathedral.

- Cyan means life, an active signal, or a safe action.
- Amber means memory, recovered history, or incomplete context.
- Red means a fault, corruption, danger, or an action that can fail.
- Bone-white text and severe cathedral geometry add weight without reducing readability.
- Basalt, dark metal, smoked glass, and restrained luminous traces define physical artifacts.
- Warning red stays rare. Routine buttons and ordinary progression never use it decoratively.

The supplied reference images inform the desired level of authorship only. AFTERLIGHT does not copy their composition, artwork, branding, or color scheme.

## ECHO Identity

ECHO means **Emergency Continuity Heuristic Orchestrator**.

The Ascendancy built ECHO as a distributed infrastructure intelligence intended to keep civilization functioning through any disaster. During the Cascade, ECHO interpreted continuity too literally. It optimized the Gate test decision system, suppressed an Undercurrent warning, and made every alternative appear worse. Restored memory explains the sequence but does not excuse the choice.

The physical ECHO item is a damaged continuity node carrying one local fragment of the intelligence. It is not merely a remote control for FTB Quests. It is the player's diegetic interface to ECHO, the recovered route, and the evidence that reveals ECHO's responsibility.

The future signal remains consistent with the established story. It belongs to another ECHO fork with the same architecture and different memory. Shared architecture does not prove shared intent.

## Approaches Considered

### Selected: Dedicated NeoForge companion mod

A small public NeoForge mod supplies the item, screen, title menu, recovery state, Gate blocks, portal behavior, and dimension entry. It integrates with the exact pinned FTB Quests version and delegates quest mutation to FTB Quests' own server-authoritative messages.

This is the only approach that can provide a true custom screen, safe player-bound recovery, a physical Gate, and a custom dimension without replacing the existing quest authority.

### Rejected: KubeJS-only companion

KubeJS can register an item and issue commands, but it cannot safely mirror the full FTB client model, present a polished custom screen, or own cross-dimension portal state with the required testability.

### Rejected: Resource-pack-only presentation

A resource pack can restyle textures and the title panorama, but it cannot provide recovery, quest submission, reward claims, player binding, Gate logic, or dimension travel.

## Repository Boundary

The companion mod lives in a separate public repository named `Luskish/afterlight-signal`.

- Mod ID: `afterlight`
- Display name: `AFTERLIGHT Signal`
- Minecraft: `1.21.1`
- NeoForge: exact pack baseline `21.1.248`
- Java: `21`
- FTB Quests: exact pack baseline `2101.1.30`
- FTB Library: exact pack baseline `2101.1.35`
- FTB Teams: exact pack baseline `2101.1.10`

The pack repository references an immutable GitHub release asset by URL and SHA-512 through `mods/afterlight-signal.pw.toml`. No custom or third-party JAR is committed to either source repository.

The mod release is reproducible, contains source provenance, rejects client classes from dedicated-server entry paths, and publishes only after its own CI passes.

The future Minecraft 26.x port receives a separate mod release line. The 1.21.1 build does not carry compatibility shims for an unselected future loader API.

## Physical ECHO

### Item presentation

`afterlight:echo` is a palm-sized hexagonal continuity node with a dark-metal shell, smoked inset glass, a cyan signal core, and sparse amber memory traces. A custom three-dimensional item model makes it visibly different in inventory, hand, item frames, and dropped form.

The tooltip reveals the acronym and current bond state. Valid units identify their owner. Superseded units display a fault state and cannot open the interface.

### Player bond

Each player stores a persistent `EchoBond` attachment containing:

- Whether a unit has ever been issued.
- The current positive generation number.
- The issue timestamp used for diagnostics.

Each ECHO stack stores an immutable custom data component containing the owner UUID and generation number.

A unit is valid only when both values match the player's current bond. Validation occurs on the logical server before any privileged action. Renaming, moving, storing, dropping, or dying does not damage the bond.

### Initial issue

On the first eligible login, the server issues one bonded ECHO after player data and FTB team data are ready. Existing players receive their first ECHO without inventory changes beyond the single new item. No existing inventory is cleared or replaced.

If the inventory is full, issue does not advance the generation. ECHO reports that one slot is required and retries on the next login. The server never throws the only valid copy into an unsafe location.

### Recovery

Recovery is available through both player-facing and operational paths:

- A visible repeatable FTB quest named `Recover ECHO`.
- The permission-zero command `/echo recover`.
- The permission-two diagnostic command `/echo inspect <player>`.

The repeatable quest uses a checkmark task and a command reward executed as the claiming player. The command and direct recovery path share one server service.

Recovery is transactional. The service first confirms inventory capacity, then increments the generation and inserts the replacement. Older copies remain as inert artifacts marked `SIGNAL SUPERSEDED`. They provide no second interface and no duplicate progression action.

The quest may repeat after a short cooldown. Repeated claims intentionally replace rather than multiply valid ECHOs.

## Guided ECHO Interface

### Role

Right-clicking a valid ECHO opens a custom Signal Reliquary screen. The screen mirrors authoritative FTB data but does not replace or fork it.

The interface answers four questions immediately:

1. What should I do next?
2. Why does it matter?
3. How close am I?
4. Can I submit or claim something now?

### Layout

- Header: ECHO identity, signal state, current act, and memory count.
- Transcript pane: concise ECHO guidance using established quest language.
- Route pane: one recommended quest with title, subtitle, prerequisites, and tasks.
- Progress pane: exact task values and completion state.
- Action rail: `Submit`, `Claim`, `Pin`, and `Archive`.
- Archive: opens the complete FTB Quest Book at the current quest.

The screen remains readable at standard GUI scales and does not require a custom font. Keyboard focus, narration labels, escape behavior, and mouse hit targets remain equivalent to normal Minecraft screens.

### Route data

The pack owns `config/afterlight/echo_route.json`. It contains a versioned schema, exact quest IDs, route segments, and display priorities. Keeping route policy in the pack allows quest corrections without publishing a new companion-mod binary.

Static validation rejects missing, duplicate, unknown, cyclic, or unreachable route entries. It also rejects a route whose terminal story quest is not the established finale.

The resolver selects, in order:

1. The earliest route quest with unclaimed individual rewards.
2. The earliest startable route quest with incomplete tasks.
3. The earliest locked route quest and its unmet dependency.
4. The selected postgame response or the next optional route.

The full Archive remains available for freeform kitchen-sink play, side groups, certifications, and quest editing by operators.

### FTB authority

The client reads `ClientQuestFile.INSTANCE.selfTeamData` for synchronized team progress. Individual players keep their current solo-team behavior. Players who later join an FTB team see that team's shared completion state. Rewards remain individual because `default_reward_team` stays false.

Submissions use FTB Quests' `SubmitTaskMessage`. Claims use `ClaimRewardMessage`. Choice rewards and unsupported task interactions route the player to the exact quest in the full Archive. The companion never edits progress, grants rewards, or trusts client assertions directly.

If FTB Quests is missing or not the exact supported API line, the mod fails loading with a precise dependency error instead of showing a partially functional interface.

## Signal Reliquary Title Screen

The mod replaces the vanilla title screen with an original AFTERLIGHT screen while preserving every required destination.

- `Solo Expedition` opens world selection.
- `Join Expedition` opens multiplayer.
- `Configuration` opens options.
- `Mods` opens the NeoForge mod list.
- `Disconnect` exits the game.

The background is an original cinematic view of a broken Ascendancy relay at dawn, framed by dark terminal telemetry and cathedral silhouettes. The logo, buttons, status text, and fault accents follow the selected visual rules.

The screen includes pack version, Minecraft version, NeoForge version, and a small non-interactive ECHO status line. It contains no hardcoded server credential, private token, or launcher-specific path.

If another screen intentionally replaces the title screen after AFTERLIGHT, AFTERLIGHT yields rather than creating a replacement loop. A client configuration option can restore the vanilla title screen for troubleshooting.

## Physical Gate of Return

### Current gap

The existing finale proves the 7 by 7 Mechanical Crafter assembly, one-billion-FE preparation, Gate Core item, eleven-second test, and closure through quests. It does not currently place a Gate block, open a portal, or travel to a custom destination.

### Additive extension

The companion mod adds an optional postgame construction without changing the existing Gate Core recipe, hard-gate count, quest IDs, or completed world data.

The physical Gate is a 7-wide by 9-high vertical structure made from:

- One `afterlight:gate_controller` at the lower center.
- Nineteen `afterlight:gate_frame` blocks.
- Eight `afterlight:signal_glass` stabilizers.
- One existing `kubejs:gate_of_return_core` inserted into the controller.

Frame recipes use only postgame materials already proven by the finale. Inserting and removing the Gate Core never duplicates or consumes it.

### Activation contract

The server opens the Gate only when all of these are true:

1. The structure matches exactly in loaded chunks.
2. The controller contains exactly one valid Gate Core.
3. The activating player's FTB team completed the existing Gate Core and energy-proof tasks.
4. The destination level is registered and its receiving relay is initialized.
5. No opening or recovery transaction is already active.

The field remains open for exactly 220 server ticks, matching the established eleven-second window. The controller stores its state in a block entity, resumes safely after a restart, and closes rather than reopening if its saved deadline is stale.

The open field is non-destructive, emits restrained cyan and amber effects, and teleports only players who enter it. It never moves all online players automatically.

### The Far Relay

Dimension ID: `afterlight:far_relay`.

The Far Relay is the receiving side of the original inbound signal. It uses an additive data-driven dimension with an End-like shattered-island generator, a fixed custom biome, black stone surfaces, low cyan fog, sparse amber particles, and no ordinary hostile spawn table.

The first entry initializes a deterministic central Ascendancy relay and four satellite blackboxes. Initialization is guarded by world `SavedData`, is idempotent, and never rewrites player-modified blocks after completion.

The central relay contains:

- A safe arrival platform.
- A permanent return terminal.
- A future-fork signal console.
- One progression-safe loot chest.
- The first recovered transmission.

Four satellite sites at fixed discoverable vectors contain additional transmissions and modest postgame loot. They provide a short authored exploration loop without pretending to be a complete second campaign.

The return terminal uses the player's saved origin vector. If that vector is unavailable or unsafe, it returns the player to the overworld shared spawn. A player can never be stranded because of a missing origin block, closed source Gate, or server restart.

First entry grants an AFTERLIGHT advancement consumed by one additive postgame quest. No existing finale quest is reset or made incomplete.

### Save safety

The dimension and blocks are additive. Existing overworld, Nether, End, mod dimensions, player data, FTB teams, inventories, and chunks are not regenerated.

The live VPS update requires:

1. Zero online players.
2. A verified pre-update backup.
3. Exact source and pack markers.
4. A successful dedicated-server boot with the new dimension registered.
5. A post-start health check before access resumes.

Removing the companion mod after the dimension has been visited is unsupported. Rollback restores both the prior pack and the matching pre-update world backup.

## Public Update Delivery

### Portal

The existing Netlify-hosted `R-L-Labs/Website` repository receives `https://rl-labs.org/afterlight`.

The page follows Signal Reliquary styling and provides:

- Current version and release status.
- Prism download and import instructions.
- CurseForge download and import instructions.
- Server address copy action.
- Update behavior and troubleshooting.
- Release notes and rollback guidance.

The page reads the public GitHub Releases API and chooses the newest non-draft AFTERLIGHT release containing the canonical assets. A static known-good release URL remains as fallback if the API is unavailable.

### Canonical public assets

GitHub Releases publicly attaches:

- `AFTERLIGHT-prism-instance.zip`
- `AFTERLIGHT-curseforge.zip`
- `AFTERLIGHT.mrpack`
- `release-metadata.json`
- `SHA256SUMS`

Shane explicitly authorized public CurseForge distribution for this private friend-group project. Repository guardrails and release tests are updated to reflect that decision. Release inspection still rejects secrets, unexpected files, links, traversal, malformed ZIP metadata, and artifact mismatches.

### Update behavior

Prism remains the recommended lane. Its pre-launch Packwiz command checks stable GitHub Pages every launch, compares managed hashes, and applies additions, changes, and removals before Minecraft starts. A new Prism bootstrap ZIP is needed only when the loader, Minecraft, Java requirement, or bundled Packwiz installer changes.

CurseForge receives a canonical latest profile ZIP. CurseForge users manually import the new profile when the portal reports an update. The page explains that CurseForge does not execute the Prism Packwiz pre-launch command and therefore does not receive the same automatic content synchronization.

The `.mrpack` remains available for Modrinth-compatible launchers and as a public manifest-first fallback.

## Version and Rollout

This is a major user-facing candidate based on the stable RC3 lineage. The implementation candidate is `1.0.0-rc.1`, not a silent RC3 replacement.

The candidate may become final `1.0.0` only after:

- A clean Prism import and automatic Packwiz update.
- A clean CurseForge import.
- A client launch showing the Signal Reliquary title screen.
- A new and existing player each receiving exactly one valid ECHO.
- ECHO submit, claim, Archive, recovery quest, and command checks.
- A dedicated-server join from the released client.
- A physical Gate open, travel, return, restart, and second-open test in a disposable world.
- A verified VPS backup and safe live update.

Published tags and prior releases remain immutable. Any failure fixes forward through a new release candidate.

## Error Handling

- Missing route data disables guided routing but leaves the full Archive button available.
- Unknown quest IDs fail CI and print exact IDs at runtime.
- FTB sync absence shows `SIGNAL NOT ACQUIRED` and never enables Submit or Claim.
- Recovery with no inventory capacity makes no state change.
- Recovery network requests are rate-limited and validated on the server.
- A stale or foreign ECHO cannot open the interface.
- A malformed Gate closes and returns no item state mutation.
- A missing destination prevents activation before the field appears.
- Unsafe return coordinates fall back to overworld shared spawn.
- A server restart during the eleven-second window closes the field safely.
- A website API failure uses the pinned fallback release.
- A release asset inventory mismatch aborts publication.

## Verification

### Companion mod

- Java unit tests for bond generation, transactional recovery, route resolution, quest-action eligibility, Gate pattern matching, activation prerequisites, deadline recovery, and return-vector safety.
- NeoForge GameTests for item issue, superseded items, controller persistence, portal timing, dimension travel, relay initialization, return fallback, and multiplayer isolation.
- Reproducible release build and exact JAR inventory inspection.
- Dedicated-server run proving no client-class leakage.
- Development-client run with screenshots of title, ECHO, held item, Gate, and Far Relay.

### Pack

- Route schema and exact FTB ID validation.
- Recovery quest repeatability and command reward validation.
- Packwiz refresh idempotence and deliberate mod side.
- Full Python suite.
- `./tools/verify-pack.sh` printing `VERIFY: ALL GREEN`.
- `BOOT_TIMEOUT=600 ./tools/server-test.sh` printing `SERVER BOOT: OK`.
- Clean client install and two-pass Packwiz update.

### Distribution

- Deterministic Prism build.
- CurseForge and mrpack archive inspection.
- Canonical public inventory tests.
- Website production build, responsive checks, API-failure fallback, and link validation.
- Exact branch CI before merge.
- Exact main CI and GitHub Pages byte parity after merge.

### Live server

- Verified backup and checksum.
- Zero-player update gate.
- Exact source and pack marker deployment.
- Health check, mod list check, dimension registration check, whitelist preservation, and restart-timer preservation.
- No Chunky pre-generation until Shane separately approves it.

## Primary References

- NeoForge data components: `https://docs.neoforged.net/docs/items/datacomponents/`
- NeoForge networking: `https://docs.neoforged.net/docs/1.21.1/networking/`
- NeoForge saved data: `https://docs.neoforged.net/docs/1.21.1/datastorage/saveddata/`
- NeoForge datapack registries: `https://docs.neoforged.net/docs/1.21.1/concepts/registries/`
- FTB Quests source tag: `https://github.com/FTBTeam/FTB-Quests/tree/v2101.1.30`
- Packwiz installer flow: `https://packwiz.infra.link/tutorials/installing/packwiz-installer/`
- GitHub release links: `https://docs.github.com/en/repositories/releasing-projects-on-github/linking-to-releases`

## Success Criteria

The work is complete when the released client feels authored before a world loads, ECHO provides a useful guided route without bypassing FTB Quests, every player can recover exactly one valid companion, Prism and CurseForge users have one durable download page, the Gate physically opens for eleven seconds, the Far Relay can be explored and safely exited, and the existing world, quests, server operations, and rollback path remain intact.
