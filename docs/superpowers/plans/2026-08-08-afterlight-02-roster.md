# AFTERLIGHT Plan 02: Full Roster and Configs Implementation Plan

> **For agentic workers:** Execute tasks in order. The Wave Pattern below is the per-task recipe; each wave task lists only its mods. Any agent (Claude or Codex) can resume at the first wave not marked complete in docs/HANDOFF.md's live progress table. AGENTS.md guardrails are binding.

**Goal:** Grow the pack from the 22-mod baseline to the full kitchen-sink roster (target 280-340 mods including libraries) per spec section 5, then normalize configs and wire AlmostUnified.

**Architecture:** Mods land in dependency-sensible category waves. Every wave independently leaves the repo green (refresh idempotent, verify-pack ALL GREEN, committed, CI green on dev). Server boot test runs at milestones and always before any dev to main merge. Modrinth is the primary source (`packwiz mr add`); CurseForge (`packwiz cf add`) is the fallback for Modrinth-absent mods; mods that block third-party CF downloads get flagged in HANDOFF.md rather than worked around.

**Tech Stack:** packwiz, Modrinth/CurseForge APIs, tools/verify-pack.sh, tools/server-test.sh, GitHub Actions.

## Global Constraints

- Everything in AGENTS.md (no em dashes, skills-first, verification before claims, packwiz discipline, sides, branch model).
- MC 1.21.1, NeoForge 21.1.x. Every mod add must resolve a NeoForge 1.21.1 build.
- Taste calibration from the spec: Create moderate, magic compact (4 mods only), GregTech optional side content, generous wow-factor elsewhere.
- Every packwiz-touching commit includes pack.toml + index.toml + mods/ together.
- Commit style `feat(mods): wave N <name>` with the authoring agent's attribution trailer.
- Wave order below is deliberate (libraries and APIs arrive with their dependents; worldgen before dimensions; story tooling last so its deps exist). Do not reorder without reason.

## The Wave Pattern (the recipe every wave task follows)

1. `source tools/versions.env && export PATH="$PATH_EXTRA:$PATH"`
2. For each mod: `packwiz mr add <slug>` (accept dependency prompts). On slug miss: `packwiz mr add <display name>` and pick by name. On Modrinth-absent: `packwiz cf add <cf-slug>`; if CF also misses, record in HANDOFF.md and continue (do not substitute a different mod silently).
3. Side check: `grep -H '^side' mods/<new>.pw.toml` for each addition; correct any wrong side (client-only render/UI mods must be `side = "client"`).
4. `packwiz refresh` then `./tools/verify-pack.sh` (expect ALL GREEN; CF-sourced mods show SKIP lines, acceptable).
5. Commit (pack.toml + index.toml + mods/), push dev, confirm CI green (`gh run list --repo Luskish/afterlight-pack --branch dev --limit 1`).
6. Update the live progress table in docs/HANDOFF.md (wave, status, mod count, anything flagged) and include it in the commit or a follow-up docs commit.
7. At milestone waves (marked MILESTONE below): `BOOT_TIMEOUT=900 ./tools/server-test.sh` locally must print SERVER BOOT: OK before proceeding.

### Task 0: Hardening commits (mandated by Plan 01 final review)

- [ ] `touch .nojekyll` at repo root; add `.nojekyll` to `.packwizignore`; refresh; verify index clean; commit `fix(pages): disable Jekyll processing for served pack files`.
- [ ] Edit `.github/workflows/pack-ci.yml`: add top-level `permissions: {contents: read}`; `concurrency: {group: pack-ci-${{ github.ref }}, cancel-in-progress: true}`; `timeout-minutes: 30` on the job; `workflow_dispatch:` trigger. Commit `fix(ci): permissions, concurrency, timeout, manual dispatch`.
- [ ] Pin packwiz: replace `@latest` in the go install line with a commit hash (resolve current: `git ls-remote https://github.com/packwiz/packwiz HEAD`). Commit `fix(ci): pin packwiz version`.
- [ ] Push dev, CI green, merge to main (ff), push, verify `curl -fsSL https://luskish.github.io/afterlight-pack/pack.toml` still HTTP 200 after Pages redeploys (the .nojekyll deploy is the risk being verified).

### Task 1, Wave 1: Tech spine A (Mekanism, IE, AE2 core)
mekanism, mekanism-generators, mekanism-additions, mekanism-tools, immersiveengineering, ae2, extendedae, mega-cells (name: MEGA Cells), applied-mekanistics, applied-flux

### Task 2, Wave 2: Tech spine B (MILESTONE: server-test after)
ender-io (name: EnderIO), industrial-foregoing, pneumaticcraft-repressurized, powah, oritech, extreme-reactors, mystical-agriculture, mystical-agradditions, compact-machines, modular-machinery-reborn, pipez, flux-networks, just-dire-things, hostile-neural-networks; CF fallbacks likely: laserio, rftools-base, rftools-utility, rftools-power

### Task 3, Wave 3: Create set (moderate, per taste calibration)
create, createaddition (name: Create Crafts and Additions), create-connected, copycats (name: Copycats+), slice-and-dice, create-enchantment-industry, create-aeronautics

### Task 4, Wave 4: Deep Vault (MILESTONE: server-test after)
gregtechceu-modern (GTCEu Modern; verify it boots alongside AlmostUnified later; its config wave comes in Task 15)

### Task 5, Wave 5: The Undercurrent (magic, compact: exactly these four)
ars-nouveau, occultism, irons-spells-n-spellbooks, malum

### Task 6, Wave 6: Dangerous world (combat, bosses) (MILESTONE: server-test after)
l-enders-cataclysm, bosses-of-mass-destruction, mowzies-mobs, apotheosis (plus apothic-attributes and other apothic deps it pulls), better-combat, artifacts, iceandfire-ce (Ice and Fire: Community Edition); CF fallback likely: alexs-mobs-1-21-1-port (unofficial port, CF only)

### Task 7, Wave 7: Worldgen and structures
terralith, tectonic, nullscape, incendium, yungs-api, yungs-better-dungeons, yungs-better-mineshafts, yungs-better-strongholds, yungs-better-desert-temples, yungs-better-witch-huts, yungs-better-ocean-monuments, yungs-better-nether-fortresses, yungs-better-jungle-temples, yungs-better-end-island, when-dungeons-arise, integrated-dungeons-and-structures, structory, structory-towers, dungeons-and-taverns

### Task 8, Wave 8: Dimensions (MILESTONE: server-test after; worldgen-heavy boot will be slower, use BOOT_TIMEOUT=900)
aether, deep-aether, the-undergarden, eternal-starlight, deeper-and-darker; CF-primary fallback: the-twilight-forest (try mr first, then cf)

### Task 9, Wave 9: Storage and QoL round 2
functional-storage, toms-storage, quark (accepts zeta dep), curios, natures-compass, advanced-loot-info, inventorysorter, veinminer-client (name: VeinMiner Hotkey; verify side, likely client), trashcans, cooking-for-blockheads? NO: not in spec, skip. End of list: exactly the spec section 5 QoL row minus already-added.

### Task 10, Wave 10: Food
farmers-delight, kaleidoscope-cookery, plus up to two Farmer's Delight addons that resolve on NeoForge 1.21.1 (candidates: mynethersdelight, endersdelight); skip any that do not resolve cleanly.

### Task 11, Wave 11: Multiplayer and server
ftb-teams, ftb-chunks, ftb-essentials, ftb-ranks (ftb-library arrives as dependency), simple-voice-chat, luckperms

### Task 12, Wave 12: Story delivery and scripting (MILESTONE: server-test after)
ftb-quests, ftb-xmod-compat, modonomicon, kubejs, lootjs, kubejs-create, almost-unified (name: AlmostUnified), probejs (side note: probejs is a dev tool, keep side both but plan to disable in release config later); CF fallbacks likely: immersive-messages-api, global-packs

### Task 13, Wave 13: Endgame and perf round 2
CF fallback likely: draconic-evolution (1.21.1 beta, post-story gated later in Plan 03). Perf: ixeris, asyncparticles, better-block-entities? (verify exact slug by search), gpu-memory-leak-fix? (CF fallback gpumemleakfix), entity-model-features? NO: not in spec, skip. Only spec-listed perf additions.

### Task 14: Full-roster verification sweep
- [ ] `./tools/verify-pack.sh` ALL GREEN; count mods (`ls mods/ | wc -l`) and record in HANDOFF.md
- [ ] `BOOT_TIMEOUT=900 ./tools/server-test.sh` SERVER BOOT: OK
- [ ] `./tools/export.sh` both artifacts build; mrpack file count matches mods count
- [ ] Client-side leak audit: `grep -l 'side = "client"' mods/*.pw.toml` list is sane (render/UI only)
- [ ] Push dev, CI green

### Task 15: Config normalization pass 1
- [ ] Boot a dev client once OR rely on server-test's generated `server-test/config/` to harvest default configs for server-relevant mods; copy the configs the spec calls out for tuning into `config/` (tracked): FTB Chunks claims limits, FTB Essentials homes/tpa, Quark tuning (disable anything overlapping other mods), JourneyMap defaults, AlmostUnified target-mod priority order (prefer: mekanism > enderio > immersiveengineering > create > oritech for material families), server.properties template documented in HANDOFF.md for the VPS (Plan 07 consumes it)
- [ ] `packwiz refresh` (configs enter the pack index intentionally: verify index.toml picked them up), verify-pack, server-test, commit
- [ ] Merge dev to main when CI green (this publishes the full roster to friends' auto-update channel: confirm with Shane BEFORE this specific merge)

## Definition of green for Plan 02
1. verify-pack ALL GREEN at final state; server-test OK at final state; CI green on dev and main
2. Mod count within 240-340 range with every spec section 5 row represented (except explicitly-flagged unavailable mods recorded in HANDOFF.md)
3. All waves logged in HANDOFF.md live progress table
4. Task 15 merge to main explicitly approved by Shane
