# Plan 06 Recipe Audit

Date: 2026-08-08

Status: implementation contract authenticated. No KubeJS, quest, Packwiz, or runtime file was changed by this audit.

## Verdict

The finale recipe contract is implementation-ready after the governing Plan 06 adopts three corrections:

1. Gate all three Draconic entry recipes, including Module Core.
2. Return the physical Ascendancy Seal from exact input slot 7 and set its maximum stack size to one.
3. Build Create test inputs through `GroupedItems.read(...)`, `calcStats()`, then `MechanicalCraftingInput.of(...)`.

The exact patterns, keys, item IDs, recipe IDs, and Chapter 17 IDs now live in `docs/superpowers/plans/2026-08-08-afterlight-06-finale.md`.

## Installed Artifact Evidence

Every selected third-party item has an item model, localization entry, and producer recipe in its installed JAR.

| Mod | Installed JAR SHA-256 | Authenticated content |
|---|---|---|
| Create | `ef87fe5709f1ba1f5b8bb20a2925b5afb4669e178fd6d8bf10c167759eefe37a` | Precision mechanism, sturdy sheet, brass sheet, electron tube, railway casing, mechanical crafter, mechanical crafting schema |
| Immersive Engineering | `45942985a4a4aebf265b8e22a0c54a96208637471f36f2532ff5d4911322debc` | Heavy engineering, advanced electronic component, steel component, HV capacitor, radiator, electrum wire coil |
| Mekanism | `004dbc9f3106f4d192aeaa1ee1190dd16ec9ca8059ed3d093b80034f4c574f43` | Atomic alloy, ultimate control circuit, HDPE sheet, polonium pellet, plutonium pellet, antimatter pellet |
| Applied Energistics 2 | `460d779a0609b81409907d9956de8f6f70a1b0912257e3e5c3c7e75ac9630e95` | Logic, calculation, and engineering processors, 256K cell component, dense energy cell, quantum entangled singularity |
| PneumaticCraft | `647ce20d52cf139f3b693b9b4c4753966a95a6dafc82d9e538ae4ae5b0249f9c` | Printed circuit board producer recipe |
| Draconic Evolution | `623d7d58e58428a206015b56bf67387c79ff6d97f7221cff23b1dad0bed9544e` | Exact Draconium Core, Dislocator, and Module Core source recipes |

Occultism `spirit_attuned_gem`, Iron's Spellbooks `magic_cloth`, and Malum `soul_stained_steel_ingot` also have installed producer recipes. These renewable ingredients avoid destroying branch workstations to craft the stabilizer.

## Exact Draconic Source Proof

Installed Draconic Evolution defines:

- Draconium Core: `ABA / BCB / ABA`
- Dislocator: `ABA / BCB / ABA`
- Module Core: `IRI / GDG / IRI`

The replacement changes only bottom center to the Seal, yielding `AZA`, `AZA`, and `IZI`. All original non-Seal keys remain unchanged. KubeJS `keepIngredient` uses flattened slot index 7 for bottom center.

## Create API Proof

The installed KubeJS Create recipe schema exposes `.acceptMirrored(...)`. The installed Create classes expose `RecipeGridHandler.GroupedItems.read`, `GroupedItems.calcStats`, `MechanicalCraftingInput.of`, and `MechanicalCraftingRecipe.acceptsMirrored()`.

`GroupedItems.read(...)` alone does not calculate dimensions. Tests that skip `calcStats()` can create invalid inputs and falsely report recipe failure.

## Balance Note

The Isotopic Core consumes four antimatter pellets. This is intentionally the dominant automated time cost for the release candidate. The manual gameplay matrix must measure completed Supercritical Phase Shifter throughput and total wall time before `1.0.0`. Balance changes require recorded timing evidence, not intuition.

The Iron's Spellbooks stabilizer route uses Magic Cloth. Chapter 17 must name it explicitly because the existing branch does not teach that exact item directly.

## Required Headless Matrix

- Resolve and unwrap every exact recipe ID.
- Assert recipe class, output, width, height, and mirror policy.
- Assemble the exact grid and require one exact output.
- Reject horizontal mirror and 90-degree rotation.
- Remove and substitute every occupied slot individually.
- Substitute every wrong schematic.
- Prove exactly one recipe produces every Gate output.
- Prove all three Draconic recipes fail without a Seal, succeed with one, return exactly one, and leave no other remainder.
- Prove no recipe, loot table, trade, or script grants the Seal outside the Chapter 20 reward.
