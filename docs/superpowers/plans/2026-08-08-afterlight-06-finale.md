# AFTERLIGHT Plan 06: Act IV and Gate Finale Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete story chapters 17-20, implement the Gate of Return crafting chain and all four hard gates, unlock Draconic Evolution post-story, and deliver a satisfying postgame.

**Architecture:** Gate components are KubeJS custom items with recipes that consume automated outputs from the four required technology constellations plus an Undercurrent stabilizer. Uncraftable physical schematic tokens are the enforceable recipe locks. Exact FTB Quests dependencies are authoritative progression evidence, while stages remain optional per-player recovery evidence only. Finale rewards stay per-player so late joiners and separated party members cannot deadlock shared progression. The Ascendancy Seal is a deliberately transferable physical postgame key, not an identity-bound permission. Modular Machinery Reborn is used only if its installed API is proven by a formed, processing, restart-safe test machine; otherwise the finale uses deterministic KubeJS recipes plus a multiblock-shaped in-world ritual documented by quests.

**Tech Stack:** KubeJS 7, FTB Quests, FTB XMod Compat, Create Mechanical Crafters, NeoForge 1.21.1. Modular Machinery Reborn remains installed but is not a story-critical output path.

## Global Constraints

- Exactly four hard gates remain: component recipes, Deep Vault key, finale, Draconic post-story.
- The Gate requires Mekanism, AE2, Create, IE, and one Undercurrent component.
- No hard gate blocks ordinary kitchen-sink sandbox play before the finale.
- All custom item and recipe IDs are stable under the `kubejs` namespace.
- Every KubeJS change boots with zero script errors.
- The Ascendancy Seal has no recipe, loot, trade, or scripted source. Each player may claim one from the Chapter 20 finale after their active quest team completes it.
- Seal transfer between friends is explicitly supported. Possession gates Draconic crafting, not player identity or team membership.
- KubeJS Stages alone does not gate recipes in the installed stack. Every Gate recipe consumes its matching uncraftable schematic token.
- A headless definition load is not proof that an MMR machine forms or processes safely. If a client-backed operational probe is unavailable, ship the deterministic fallback.
- No `team_reward`, `team_stage`, or authoritative `gamestage` task is permitted in the finale graph.

---

### Task 1: Gate Items, Dependencies, and Recipe Guards

**Files:**
- Modify: `kubejs/startup_scripts/afterlight/registry.js`
- Modify: `kubejs/server_scripts/afterlight/_constants.js`
- Create: `kubejs/server_scripts/afterlight/gate_components.js`
- Modify: `kubejs/server_scripts/afterlight/gate_draconic.js`
- Create: `kubejs/assets/kubejs/models/item/*.json`
- Modify: `kubejs/assets/kubejs/lang/en_us.json`

- [ ] Register `kubejs:gate_kinetic_frame`, `kubejs:gate_industrial_anchor`, `kubejs:gate_isotopic_core`, `kubejs:gate_lattice_matrix`, `kubejs:undercurrent_stabilizer`, and `kubejs:gate_of_return_core`. The Deep Vault key and schematic items already exist from Plan 05.
- [ ] Make each component recipe consume its matching uncraftable schematic. Use exact completed quest dependencies as progression evidence. Stages are never recipe or quest gates.
- [ ] Replace Chapter 16 and Infrastructure II `gamestage` tasks with exact finale dependencies and nonconsuming physical-item checks where applicable.
- [ ] Bind Infrastructure II to certification finales `5ADAE277C9FEF0F1`, `B107D8813D59B2FF`, `66CDE7B061D8DA5C`, `42EE25F560AE65CD`, `E1F5D15817ED5EFD`, and `FC9EA276C2D84333`. Bind Chapter 16 Four Keys to schematic finales `90EDD2BED35BE9E3`, `752C3E53CA89C92D`, `A1A99D99B372916F`, and `3497EFDF016FAFD7`. Bind Certified Bulk Quotas to those six plus Infrastructure II finale `E524EE78235F0942`.
- [ ] Keep the four schematics, Gate blueprint, stabilizer precursor, Gate outputs, and Seal as deliberate per-player rewards or crafts. Do not migrate them to team rewards.
- [ ] Add an operator recovery procedure that verifies the exact source quest in the current or archived team data before restoring one lost token. Record every restoration.
- [ ] Make all three Draconic entry recipes require and return an Ascendancy Seal. The physical Seal is the only enforceable recipe gate.
- [ ] Boot and verify startup/server logs before committing.

### Task 2: Gate Assembly Mechanic

**Files:**
- Create: `kubejs/server_scripts/afterlight/gate_assembly.js`
- Create: `docs/gameplay/gate-of-return.md`

- [ ] Implement four exact 5 by 5 Create Mechanical Crafting component recipes with `acceptMirrored: false`. Each consumes its matching schematic and four of each audited branch ingredient.
- [ ] Implement three exact stabilizer alternatives, each consuming the common precursor plus one approved Undercurrent branch ingredient.
- [ ] Implement one exact 7 by 7 Create Mechanical Crafting Gate recipe using the blueprint, four components, stabilizer, and certified bulk outputs. No MMR or second recipe may output the Gate core.
- [ ] Document the physical 7 by 7 Mechanical Crafter monument and require a later client visual acceptance check without making client rendering a headless claim.
- [ ] Boot twice, verify the headless recipe audit marker and zero KubeJS errors, then commit.

### Task 3: Act IV Chapters 17-20

**Files:**
- Modify: `tools/afterlight_quests/catalog.py`
- Generate: `config/ftbquests/quests/chapters/*.snbt`
- Modify: `config/ftbquests/quests/lang/en_us.snbt`

- [ ] Add Chapter 17, `Five Impossible Parts`: unlock and automate each component chain.
- [ ] Start Chapter 17 from exact Chapter 16 finale `72446D404001B38D`. Bind the four technology branches to their exact schematic finales and the stabilizer branch to Undercurrent finale `87338DE0FE8114CF`, then check the crafted physical outputs without consuming them.
- [ ] Add Chapter 18, `The Cascade Truth`: ECHO recovers the complete memory and reveals its role in the disaster.
- [ ] Add Chapter 19, `Gate of Return`: assemble, power, and activate the Gate core.
- [ ] Add Chapter 20, `Afterlight`: contact the survivors, offer three optional nonexclusive narrative responses, converge with `one_completed`, then award each eligible player one Seal.
- [ ] Build, validate, boot, and commit.

### Task 4: Postgame and Finale Verification

**Files:**
- Modify: `tools/afterlight_quests/catalog.py`
- Create: `docs/releases/plan-06-verification.md`
- Modify: `docs/HANDOFF.md`

- [ ] Add postgame Draconic chapter and repeatable creative-tier objectives that do not affect story completion.
- [ ] Verify the Seal cannot be obtained from loot, trades, ordinary recipes, or custom scripted grants.
- [ ] Verify every Gate component requires its exact schematic and every Draconic entry recipe fails without a Seal, succeeds with one, and returns exactly one Seal.
- [ ] Build Create `MechanicalCraftingInput` instances through `RecipeGridHandler.GroupedItems.read(...)`, unwrap each `RecipeHolder.value()`, and test all 5 by 5 and 7 by 7 recipes headlessly.
- [ ] Run quest validator, pack verifier, server boot, CI, and merge green `dev` to `main`.
