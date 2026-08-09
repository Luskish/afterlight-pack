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
- `kubejs:ascendancy_seal` has maximum stack size one. Every gated Draconic recipe keeps the Seal in exact input slot 7 and leaves no other remainder.

## Authenticated Recipe Contract

All four 5 by 5 component recipes use `event.recipes.create.mechanical_crafting(...).acceptMirrored(false)` and this exact asymmetric pattern:

```text
ABCDF
EFABC
DASBE
CDEFA
FBCDE
```

The pattern consumes four of every branch ingredient and one matching schematic.

| Recipe ID | Output | A | B | C | D | E | F | S |
|---|---|---|---|---|---|---|---|---|
| `kubejs:gate/component/kinetic_frame` | `kubejs:gate_kinetic_frame` | `create:precision_mechanism` | `create:sturdy_sheet` | `create:brass_sheet` | `create:electron_tube` | `create:railway_casing` | `create:mechanical_crafter` | `kubejs:schematic_kinetic_frame` |
| `kubejs:gate/component/industrial_anchor` | `kubejs:gate_industrial_anchor` | `immersiveengineering:heavy_engineering` | `immersiveengineering:component_electronic_adv` | `immersiveengineering:component_steel` | `immersiveengineering:capacitor_hv` | `immersiveengineering:radiator` | `immersiveengineering:wirecoil_electrum` | `kubejs:schematic_industrial_anchor` |
| `kubejs:gate/component/isotopic_core` | `kubejs:gate_isotopic_core` | `mekanism:alloy_atomic` | `mekanism:ultimate_control_circuit` | `mekanism:hdpe_sheet` | `mekanism:pellet_polonium` | `mekanism:pellet_plutonium` | `mekanism:pellet_antimatter` | `kubejs:schematic_isotopic_core` |
| `kubejs:gate/component/lattice_matrix` | `kubejs:gate_lattice_matrix` | `ae2:logic_processor` | `ae2:calculation_processor` | `ae2:engineering_processor` | `ae2:cell_component_256k` | `ae2:dense_energy_cell` | `ae2:quantum_entangled_singularity` | `kubejs:schematic_lattice_matrix` |

The three exact shapeless stabilizer recipes each consume one `kubejs:undercurrent_stabilizer_precursor` and one renewable branch item:

| Recipe ID | Branch item |
|---|---|
| `kubejs:gate/stabilizer/occultism` | `occultism:spirit_attuned_gem` |
| `kubejs:gate/stabilizer/irons_spellbooks` | `irons_spellbooks:magic_cloth` |
| `kubejs:gate/stabilizer/malum` | `malum:soul_stained_steel_ingot` |

The exact 7 by 7 recipe ID is `kubejs:gate/gate_of_return_core`. It uses `.acceptMirrored(false)` and this pattern:

```text
CCAAPPS
CC B AA
A PKS S
P IUO S
A SLP P
CA   CS
SSPPACC
```

Keys are `B` blueprint, `K` kinetic frame, `I` industrial anchor, `O` isotopic core, `L` lattice matrix, `U` Undercurrent stabilizer, `C` `create:iron_sheet`, `A` `ae2:logic_processor`, `P` `pneumaticcraft:printed_circuit_board`, and `S` `immersiveengineering:ingot_steel`. The recipe consumes eight of each certified bulk output and one of every unique Gate item.

The exact Draconic replacements remove `draconicevolution:components/draconium_core`, `draconicevolution:tools/dislocator`, and `draconicevolution:modules/module_core`; emit recipe IDs `kubejs:gated/draconium_core`, `kubejs:gated/dislocator`, and `kubejs:gated/module_core`; preserve each installed source recipe's keys; replace bottom-center input with `Z: AFTERLIGHT.SEAL`; and call `.keepIngredient({ item: AFTERLIGHT.SEAL, index: 7 })`. Patterns are `ABA / BCB / AZA`, `ABA / BCB / AZA`, and `IRI / GDG / IZI` respectively.

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
- [ ] Change `kubejs:ascendancy_seal` to maximum stack size one so the installed `KeepAction` cannot return a multi-Seal input stack.
- [ ] Make each component recipe consume its matching uncraftable schematic. Use exact completed quest dependencies as progression evidence. Stages are never recipe or quest gates.
- [ ] Replace Chapter 16 and Infrastructure II `gamestage` tasks with exact finale dependencies and nonconsuming physical-item checks where applicable.
- [ ] Bind Infrastructure II to certification finales `5ADAE277C9FEF0F1`, `B107D8813D59B2FF`, `66CDE7B061D8DA5C`, `42EE25F560AE65CD`, `E1F5D15817ED5EFD`, and `FC9EA276C2D84333`. Bind Chapter 16 Four Keys to schematic finales `90EDD2BED35BE9E3`, `752C3E53CA89C92D`, `A1A99D99B372916F`, and `3497EFDF016FAFD7`. Bind Certified Bulk Quotas to those six plus Infrastructure II finale `E524EE78235F0942`.
- [ ] Keep the four schematics, Gate blueprint, stabilizer precursor, Gate outputs, and Seal as deliberate per-player rewards or crafts. Do not migrate them to team rewards.
- [ ] Add an operator recovery procedure that verifies the exact source quest in the current or archived team data before restoring one lost token. Record every restoration.
- [ ] Replace all three authenticated Draconic entry recipes, including `module_core`, and require plus return exactly one Ascendancy Seal from slot 7. The physical Seal is the only enforceable recipe gate.
- [ ] Boot and verify startup/server logs before committing.

### Task 2: Gate Assembly Mechanic

**Files:**
- Create: `kubejs/server_scripts/afterlight/gate_assembly.js`
- Create: `docs/gameplay/gate-of-return.md`

- [ ] Implement the four exact 5 by 5 component recipes from the authenticated contract with `.acceptMirrored(false)`. Each consumes its matching schematic and four of every listed branch ingredient.
- [ ] Implement the three exact shapeless stabilizer alternatives from the authenticated contract. Each consumes the common precursor plus one renewable approved Undercurrent branch item.
- [ ] Implement the exact 7 by 7 Gate recipe from the authenticated contract with `.acceptMirrored(false)`. No MMR or second recipe may output the Gate core.
- [ ] Document the physical 7 by 7 Mechanical Crafter monument and require a later client visual acceptance check without making client rendering a headless claim.
- [ ] Boot twice, verify the headless recipe audit marker and zero KubeJS errors, then commit.

### Task 3: Act IV Chapters 17-20

**Files:**
- Modify: `tools/afterlight_quests/catalog.py`
- Generate: `config/ftbquests/quests/chapters/*.snbt`
- Modify: `config/ftbquests/quests/lang/en_us.snbt`

- [ ] Add Chapter 17, `Five Impossible Parts`: unlock and automate each component chain.
- [ ] Create Chapter 17 slug `story/17-five-impossible-parts`, stable chapter ID `FE9B015A32C6D980`. Start all five branches from exact Chapter 16 finale `72446D404001B38D`; bind Kinetic Frame quest `8055C66103106D86` to `90EDD2BED35BE9E3`, Industrial Anchor `D2FE1624DCCE878F` to `752C3E53CA89C92D`, Isotopic Core `50775CE87FAA4EB7` to `A1A99D99B372916F`, Lattice Matrix `FF064705A3CAB2E6` to `3497EFDF016FAFD7`, and Undercurrent Stabilizer `39C1F24EABBB34A3` to `87338DE0FE8114CF`. Check every crafted physical output without consuming it.
- [ ] Converge Chapter 17 at quest `144473B8267DBC28`, slug `story/17-five-impossible-parts/five-impossible-parts`, after all five item quests. Use checkmark task slug ending `/task/checkmark`, stable task ID `42F99C5AFE250994`.
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
- [ ] Resolve every Gate recipe by exact ID and unwrap `RecipeHolder.value()`. Build row-zero-at-highest-Y Grid NBT, call `RecipeGridHandler.GroupedItems.read(...)`, then `calcStats()`, then `MechanicalCraftingInput.of(...)`. Assert exact dimensions, output, and `acceptsMirrored() == false` for all 5 by 5 and 7 by 7 recipes.
- [ ] For every occupied Gate recipe slot, prove removal and substitution fail. Prove horizontal mirrors and 90-degree rotations fail, wrong schematics fail, and exactly one recipe produces each Gate output.
- [ ] For all three Draconic recipes, prove no-Seal failure, one-Seal success, exactly one Seal remainder, no other remainder, and maximum Seal stack size one.
- [ ] Run quest validator, pack verifier, server boot, CI, and merge green `dev` to `main`.
