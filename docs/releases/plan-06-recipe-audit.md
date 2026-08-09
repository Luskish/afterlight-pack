# Plan 06 Recipe Audit

Date: 2026-08-08

Status: implementation contract authenticated. No KubeJS, quest, Packwiz, or runtime file was changed by this audit.

## Verdict

The finale recipe contract is implementation-ready after the governing Plan 06 adopts five corrections:

1. Gate all three Draconic entry recipes, including Module Core.
2. Return the physical Ascendancy Seal from exact input slot 7 and set its maximum stack size to one.
3. Build Create test inputs through `GroupedItems.read(...)`, `calcStats()`, then `MechanicalCraftingInput.of(...)`.
4. Register all three Draconic replacements through `event.shaped(...)`. The resulting `kubejs:shaped` serializer is required because vanilla `minecraft:crafting_shaped` custom recipes do not apply `keepIngredient` actions.
5. Keep recipe registration in Plan 06 Task 2, then prove all eleven recipes through one source-authenticated live listener and marker. Task 1 registers items and converts quest dependencies only.

The exact patterns, keys, item IDs, recipe IDs, and Chapter 17 IDs now live in `docs/superpowers/plans/2026-08-08-afterlight-06-finale.md`.

## Installed Artifact Evidence

Every selected third-party item has an item model, localization entry, and producer recipe in its installed JAR.
The runtime audit checks exactly 30 unique non-KubeJS Gate inputs: 24 component ingredients, the three additional Gate bulk ingredients `create:iron_sheet`, `pneumaticcraft:printed_circuit_board`, and `immersiveengineering:ingot_steel`, plus the three renewable stabilizer branch items. `ae2:logic_processor` appears in both a component and the Gate core but is counted once.

| Mod | Installed JAR SHA-256 | Authenticated content |
|---|---|---|
| KubeJS 2101.7.2-build.368 | `01767bb677a9c4a8f318717c4c21bca7e7ef80995603403a551068a0e064e740` | `event.shaped`, `SlotFilter` item plus index matching, and full-stack `KeepAction` behavior |
| KubeJS Create 2101.3.1-build.18 | `9051fd08349850cb9b28845554246ef4f2c976892835a704ee27dcb7c8bfd7a1` | Mechanical crafting schema, `acceptMirrored`, and Create recipe builder integration |
| Create | `ef87fe5709f1ba1f5b8bb20a2925b5afb4669e178fd6d8bf10c167759eefe37a` | Precision mechanism, sturdy sheet, brass sheet, electron tube, railway casing, mechanical crafter, mechanical crafting schema |
| Immersive Engineering | `45942985a4a4aebf265b8e22a0c54a96208637471f36f2532ff5d4911322debc` | Heavy engineering, advanced electronic component, steel component, HV capacitor, radiator, electrum wire coil |
| Mekanism | `004dbc9f3106f4d192aeaa1ee1190dd16ec9ca8059ed3d093b80034f4c574f43` | Atomic alloy, ultimate control circuit, HDPE sheet, polonium pellet, plutonium pellet, antimatter pellet |
| Applied Energistics 2 | `460d779a0609b81409907d9956de8f6f70a1b0912257e3e5c3c7e75ac9630e95` | Logic, calculation, and engineering processors, 256K cell component, dense energy cell, quantum entangled singularity |
| PneumaticCraft | `647ce20d52cf139f3b693b9b4c4753966a95a6dafc82d9e538ae4ae5b0249f9c` | Printed circuit board producer recipe |
| Draconic Evolution | `623d7d58e58428a206015b56bf67387c79ff6d97f7221cff23b1dad0bed9544e` | Exact Draconium Core, Dislocator, and Module Core source recipes |
| FTB Quests 2101.1.30 | `7d6ee49f42716eca803f2c68e70d9fe6cb5c0ded9f629ce28c5955ded46d4d51` | Repeat cooldown units, flexible task-start behavior, and player-local reward claiming |
| Occultism 1.224.2 | `0f73d75ce41fa0e4feef8f5ec06ee59e2a5738481b1100120bdcf0065e56f823` | Spirit-Attuned Gem item, presentation, and producer recipe |
| Iron's Spells 'n Spellbooks 3.16.2 | `82b650aff7636c8fa88da0e4cfea008c229bb62843274678ee932f6b4ec74430` | Magic Cloth item, presentation, and producer recipe |
| Malum 1.8.2 | `38f4fa53e8da9e3d67aa5f54f98fd7c83cb342f0463ce5c63a6864229c88efa8` | Soul-Stained Steel Ingot item, presentation, and producer recipe |

Occultism `spirit_attuned_gem`, Iron's Spellbooks `magic_cloth`, and Malum `soul_stained_steel_ingot` also have installed producer recipes. These renewable ingredients avoid destroying branch workstations to craft the stabilizer.

## Exact Draconic Source Proof

Installed Draconic Evolution defines:

- Draconium Core: `ABA / BCB / ABA`
- Dislocator: `ABA / BCB / ABA`
- Module Core: `IRI / GDG / IRI`

The replacement changes only bottom center to the Seal, yielding `AZA`, `AZA`, and `IZI`. All original non-Seal keys remain unchanged. KubeJS `keepIngredient` uses flattened slot index 7 for bottom center. The replacement serializer intentionally changes from `minecraft:crafting_shaped` to `kubejs:shaped`; all gameplay pattern, key, and output fields remain exact.

`KeepAction` copies the complete input stack. Maximum stack size one protects valid gameplay inventory stacks, but it does not repair an invalid overstack created through operator commands or another broken source. An invalid count-two input leaves three Seals after vanilla removes one and KubeJS restores the copied two. Runtime tests must prove the supported count-one remainder and separately pin this count-two behavior without calling it supported.

## Create API Proof

The installed KubeJS Create recipe schema exposes `.acceptMirrored(...)`. The installed Create classes expose `RecipeGridHandler.GroupedItems.read`, `GroupedItems.calcStats`, `MechanicalCraftingInput.of`, and `MechanicalCraftingRecipe.acceptsMirrored()`.

`GroupedItems.read(...)` alone does not calculate dimensions. Tests that skip `calcStats()` can create invalid inputs and falsely report recipe failure.

## Custom Item Asset Proof

KubeJS automatically generates an item model with parent `minecraft:item/generated` and texture layer `kubejs:item/<id>` for each registered item. Plan 06 therefore adds the six textures and language entries but does not add redundant explicit model JSON. If a client-backed resource check later proves a custom model necessary, its exact form is `{"parent":"minecraft:item/generated","textures":{"layer0":"kubejs:item/<id>"}}`.

## Balance Note

The Isotopic Core consumes four antimatter pellets. This is intentionally the dominant automated time cost for the release candidate. The manual gameplay matrix must measure completed Supercritical Phase Shifter throughput and total wall time before `1.0.0`. Balance changes require recorded timing evidence, not intuition.

The Iron's Spellbooks stabilizer route uses Magic Cloth. Chapter 17 must name it explicitly because the existing branch does not teach that exact item directly.

Installed FTB Quests 2101.1.30 stores `repeat_cooldown` as an integer number of seconds. `TeamData.markRewardAsClaimed(...)` multiplies `Quest.getRepeatCooldown()` by 1,000 before adding it to `System.currentTimeMillis()`. The three postgame blessings therefore use `repeat_cooldown=3600` for an exact one-hour cooldown, not the tick-based value 72,000.

The same installed build treats global `progression_mode="flexible"` as permission to start tasks before dependencies complete. `TeamData.canStartTasks(...)` returns true immediately for flexible quests. Infrastructure II, Chapter 16, Act IV, and postgame therefore use explicit per-quest `progression_mode="linear"`; otherwise a checkmark could award the Gate Blueprint or Seal before its dependency chain.

## Required Headless Matrix

- Resolve and unwrap every exact recipe ID.
- Assert recipe class, output, width, height, and mirror policy.
- Assemble the exact grid and require one exact output.
- Reject horizontal mirror and 90, 180, and 270 degree rotations.
- Remove and substitute every occupied slot individually.
- Substitute every wrong schematic.
- Prove exactly one recipe produces each component output and the Gate core, exactly the three approved recipes produce the stabilizer, and exactly one recipe produces each Draconic entry output.
- Prove all three Draconic recipes fail without a Seal, succeed with one, return exactly one, and leave no other remainder.
- Prove no recipe, loot table, trade, or script grants the Seal outside the Chapter 20 reward.
