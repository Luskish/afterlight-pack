# AFTERLIGHT Plan 06: Act IV and Gate Finale Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete story chapters 17-20, implement the Gate of Return crafting chain and all four hard gates, unlock Draconic Evolution post-story, and deliver a satisfying postgame.

**Architecture:** Gate components are KubeJS custom items with recipes that consume automated outputs from the four required technology constellations plus an Undercurrent stabilizer. Uncraftable physical schematic tokens are the enforceable recipe locks; FTB Quests stages provide progression state and recovery evidence. Modular Machinery Reborn is used only if its installed API is proven by a formed, processing, restart-safe test machine; otherwise the finale uses deterministic KubeJS recipes plus a multiblock-shaped in-world ritual documented by quests.

**Tech Stack:** KubeJS 7, FTB Quests stages, FTB XMod Compat, Modular Machinery Reborn when proven, NeoForge 1.21.1.

## Global Constraints

- Exactly four hard gates remain: component recipes, Deep Vault key, finale, Draconic post-story.
- The Gate requires Mekanism, AE2, Create, IE, and one Undercurrent component.
- No hard gate blocks ordinary kitchen-sink sandbox play before the finale.
- All custom item and recipe IDs are stable under the `kubejs` namespace.
- Every KubeJS change boots with zero script errors.
- The Ascendancy Seal is awarded only after Chapter 20 completion.
- KubeJS Stages alone does not gate recipes in the installed stack. Every Gate recipe consumes its matching uncraftable schematic token.
- A headless definition load is not proof that an MMR machine forms or processes safely. If a client-backed operational probe is unavailable, ship the deterministic fallback.

---

### Task 1: Gate Items, Stages, and Recipe Guards

**Files:**
- Modify: `kubejs/startup_scripts/afterlight/registry.js`
- Modify: `kubejs/server_scripts/afterlight/_constants.js`
- Create: `kubejs/server_scripts/afterlight/gate_components.js`
- Modify: `kubejs/server_scripts/afterlight/gate_draconic.js`
- Create: `kubejs/assets/kubejs/models/item/*.json`
- Modify: `kubejs/assets/kubejs/lang/en_us.json`

- [ ] Register `kubejs:gate_kinetic_frame`, `kubejs:gate_industrial_anchor`, `kubejs:gate_isotopic_core`, `kubejs:gate_lattice_matrix`, `kubejs:undercurrent_stabilizer`, and `kubejs:gate_of_return_core`. The Deep Vault key and schematic items already exist from Plan 05.
- [ ] Make each component recipe consume its matching uncraftable schematic. Use stages for recovery evidence, not as the sole enforcement mechanism.
- [ ] Add an operator recovery procedure that checks `/kubejs stages list <player>` before restoring a lost one-time schematic.
- [ ] Make Draconic entry require both story completion stage and an Ascendancy Seal where the installed API permits; keep the Seal recipe gate as the fail-safe.
- [ ] Boot and verify startup/server logs before committing.

### Task 2: Gate Assembly Mechanic

**Files:**
- Create or modify only after jar/API proof: `kubejs/server_scripts/afterlight/gate_machine.js`
- Create as fallback: `kubejs/server_scripts/afterlight/gate_assembly.js`
- Create: `docs/gameplay/gate-of-return.md`

- [ ] Use the audited MMR 3.0.22 raw machine JSON path `kubejs/data/afterlight/machines/` and KubeJS `machine_recipe` API to build a disposable minimal test machine.
- [ ] Use MMR only if a real client proves formation, one-input/one-output processing, energy use, output-full safety, FE-starved safety, JEI visibility, and persistence across restart.
- [ ] When that operational probe cannot run during the automated release, implement a deterministic KubeJS final assembly recipe using the five components plus certified bulk outputs, document the 7 by 7 Gate monument, and remove disposable probe definitions.
- [ ] Boot twice, verify zero MMR/KubeJS errors, and commit the proven path only.

### Task 3: Act IV Chapters 17-20

**Files:**
- Modify: `tools/afterlight_quests/catalog.py`
- Generate: `config/ftbquests/quests/chapters/*.snbt`
- Modify: `config/ftbquests/quests/lang/en_us.snbt`

- [ ] Add Chapter 17, `Five Impossible Parts`: unlock and automate each component chain.
- [ ] Add Chapter 18, `The Cascade Truth`: ECHO recovers the complete memory and reveals its role in the disaster.
- [ ] Add Chapter 19, `Gate of Return`: assemble, power, and activate the Gate core.
- [ ] Add Chapter 20, `Afterlight`: contact the survivors, choose the future, award the Seal and postgame stage.
- [ ] Build, validate, boot, and commit.

### Task 4: Postgame and Finale Verification

**Files:**
- Modify: `tools/afterlight_quests/catalog.py`
- Create: `docs/releases/plan-06-verification.md`
- Modify: `docs/HANDOFF.md`

- [ ] Add postgame Draconic chapter and repeatable creative-tier objectives that do not affect story completion.
- [ ] Verify the Seal cannot be obtained from loot or ordinary recipes.
- [ ] Verify every Gate recipe is absent or unusable before its stage and usable after its stage using logs or a scripted integration test.
- [ ] Run quest validator, pack verifier, server boot, CI, and merge green `dev` to `main`.
