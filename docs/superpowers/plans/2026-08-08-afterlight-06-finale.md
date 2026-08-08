# AFTERLIGHT Plan 06: Act IV and Gate Finale Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete story chapters 17-20, implement the Gate of Return crafting chain and all four hard gates, unlock Draconic Evolution post-story, and deliver a satisfying postgame.

**Architecture:** Gate components are KubeJS custom items with recipes that consume automated outputs from the four required technology constellations plus an Undercurrent stabilizer. FTB Quests stage rewards unlock each component recipe. Modular Machinery Reborn is used only if its installed API is proven by a boot-tested minimal machine; otherwise the finale uses deterministic KubeJS recipes plus a multiblock-shaped in-world ritual documented by quests.

**Tech Stack:** KubeJS 7, FTB Quests stages, FTB XMod Compat, Modular Machinery Reborn when proven, NeoForge 1.21.1.

## Global Constraints

- Exactly four hard gates remain: component recipes, Deep Vault key, finale, Draconic post-story.
- The Gate requires Mekanism, AE2, Create, IE, and one Undercurrent component.
- No hard gate blocks ordinary kitchen-sink sandbox play before the finale.
- All custom item and recipe IDs are stable under the `kubejs` namespace.
- Every KubeJS change boots with zero script errors.
- The Ascendancy Seal is awarded only after Chapter 20 completion.

---

### Task 1: Gate Items, Stages, and Recipe Guards

**Files:**
- Modify: `kubejs/startup_scripts/afterlight/registry.js`
- Modify: `kubejs/server_scripts/afterlight/_constants.js`
- Create: `kubejs/server_scripts/afterlight/gate_components.js`
- Modify: `kubejs/server_scripts/afterlight/gate_draconic.js`
- Create: `kubejs/assets/kubejs/models/item/*.json`
- Modify: `kubejs/assets/kubejs/lang/en_us.json`

- [ ] Register four Gate component items, the Undercurrent stabilizer, Deep Vault key, and completed Gate core.
- [ ] Add stage-aware component recipe guards using `player.stages` or FTB stage ingredients supported by the installed integration.
- [ ] Make Draconic entry require both story completion stage and an Ascendancy Seal where the installed API permits; keep the Seal recipe gate as the fail-safe.
- [ ] Boot and verify startup/server logs before committing.

### Task 2: Gate Assembly Mechanic

**Files:**
- Create or modify only after jar/API proof: `kubejs/server_scripts/afterlight/gate_machine.js`
- Create as fallback: `kubejs/server_scripts/afterlight/gate_assembly.js`
- Create: `docs/gameplay/gate-of-return.md`

- [ ] Inspect installed MMR jar classes/resources and build a minimal test machine definition.
- [ ] If the test machine loads and accepts a recipe, implement the Gate multiblock and final recipe through MMR.
- [ ] If not, implement a KubeJS shaped final assembly recipe using the five components plus certified bulk outputs, and document the physical monument players build around it.
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

