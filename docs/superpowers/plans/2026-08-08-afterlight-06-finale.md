# AFTERLIGHT Plan 06: Act IV and Gate Finale Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete story chapters 17 through 20, implement the Gate of Return crafting chain and all four hard gates, unlock Draconic Evolution after the story, and deliver a satisfying postgame.

**Architecture:** Gate components are KubeJS custom items crafted from certified automation outputs and physical progression tokens. Exact FTB Quests dependencies are authoritative progression evidence, while stages remain optional per-player recovery evidence only. The Gate and Draconic recipe contracts are proven against the same-run live RecipeManager by one source-authenticated KubeJS audit. Finale rewards remain per-player so a shared quest team does not turn one physical Seal into a party-wide deadlock.

**Tech Stack:** NeoForge 21.1.248 on Minecraft 1.21.1, Java 21, KubeJS 2101.7.2-build.368, KubeJS Create 2101.3.1-build.18, Create 6.0.10, FTB Quests, FTB XMod Compat, and Draconic Evolution 3.1.4.632.

## Global Constraints

- Exactly four hard gates remain: each component consumes its matching schematic, Deep Vault entry requires its physical key, the Gate core consumes its blueprint and five completed parts, and every Draconic entry recipe requires and returns the transferable Seal.
- The four component recipes consume their exact schematics. The three stabilizer recipes consume `kubejs:undercurrent_stabilizer_precursor`. The Gate core consumes `kubejs:gate_blueprint`. No other recipe receives a hard progression token.
- The Gate requires Mekanism, AE2, Create, Immersive Engineering, and one Undercurrent stabilizer. Ordinary kitchen-sink play remains soft-gated before the finale.
- All custom item and recipe IDs are stable under the `kubejs` namespace.
- Every KubeJS change boots with zero script errors.
- Every quest title, subtitle, description, and task label is written in ECHO's established deadpan voice. Chapter finales restore Memory Fragments 16 through 19 exactly once and continue the recovered-memory sequence from Chapter 16.
- The Ascendancy Seal has no recipe, loot, trade, or scripted source. Each eligible player may claim exactly one from the Chapter 20 finale after their active quest team completes it.
- Seal transfer between friends is supported. Possession gates Draconic crafting, not player identity, quest team, or stage membership.
- `kubejs:ascendancy_seal` has maximum stack size one. That protects valid gameplay stacks but does not sanitize an operator-created invalid overstack. Runtime tests must characterize the installed count-two behavior: `getRemainingItems(...)` returns a count-two Seal copy and vanilla's consume-one plus merge transaction derives a final count of three. The valid count-one path must return exactly one Seal and no other remainder.
- The three Draconic replacements intentionally use the `kubejs:shaped` serializer through `event.shaped(...)`. A vanilla `minecraft:crafting_shaped` custom recipe cannot apply KubeJS `keepIngredient` semantics.
- No `team_reward`, `team_stage`, or authoritative `gamestage` task is permitted in the Act IV or postgame graph. The optional `afterlight_story_complete` stage reward is recovery evidence only.
- Global quest progression remains flexible, but every Infrastructure II, Chapter 16, Act IV, and postgame quest explicitly writes `progression_mode="linear"`. Installed FTB Quests allows tasks to complete before dependencies under flexible mode, so the explicit override is required to protect the Blueprint and Seal source quests.
- Modular Machinery Reborn is not a story-critical path. The release candidate uses deterministic Create Mechanical Crafting plus a quest-documented monument because no formed, processing, restart-safe client probe exists.

## Execution Discipline

- Every behavior change starts with the named focused failing regression and records the expected failure before implementation.
- Every task receives an independent requirements review and code-quality review before the controller accepts it.
- Any task that changes `tools/afterlight_quests/catalog.py` runs `python3 tools/build-quests.py`, commits `.afterlight-managed.json`, every changed generated chapter, localization, and `generated_quest_item_audit.js`, then runs both quest validator modes at the task's stated gate.
- Any task that changes shipped content starts its Packwiz shell with `source tools/versions.env && export PATH="$PATH_EXTRA:$PATH"`, runs `packwiz refresh`, commits `pack.toml` and `index.toml` with the shipped files, asserts no unexpected `mods/` drift, and requires a second refresh to be idempotent.
- Every quest-count change updates the exact FTB Quests boot expectation and its negative tests in `tools/rc_hygiene.py` and `tools/tests/test_rc_hygiene_reliability.py` in the same task.
- JavaScript parsing and successful definition load are not recipe-semantic proof. Task 2 introduces the authenticated live recipe marker. Task 4 extends that same listener and marker through the adversarial matrix.
- Task ownership is strict: Task 1 owns item registration, assets, allowlisting, and dependency conversion; Task 2 owns all eleven recipes and the baseline runtime audit; Task 3 owns Chapters 17 through 20; Task 4 owns postgame and extends the same audit. No task duplicates another task's recipe or marker listener.

## Authenticated Recipe Contract

### Component Recipes

All four 5 by 5 recipes use `event.recipes.create.mechanical_crafting(output, pattern, key).acceptMirrored(false).id(recipeId)` and this exact asymmetric pattern:

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

### Stabilizer Recipes

The three exact shapeless recipes consume one precursor and one renewable branch item.

| Recipe ID | Output | Ingredients |
|---|---|---|
| `kubejs:gate/stabilizer/occultism` | `kubejs:undercurrent_stabilizer` | `kubejs:undercurrent_stabilizer_precursor`, `occultism:spirit_attuned_gem` |
| `kubejs:gate/stabilizer/irons_spellbooks` | `kubejs:undercurrent_stabilizer` | `kubejs:undercurrent_stabilizer_precursor`, `irons_spellbooks:magic_cloth` |
| `kubejs:gate/stabilizer/malum` | `kubejs:undercurrent_stabilizer` | `kubejs:undercurrent_stabilizer_precursor`, `malum:soul_stained_steel_ingot` |

### Gate Core Recipe

The recipe ID is `kubejs:gate/gate_of_return_core`. It uses Create Mechanical Crafting, returns one `kubejs:gate_of_return_core`, rejects mirroring, and uses this exact 7 by 7 pattern:

```text
CCAAPPS
CC B AA
A PKS S
P IUO S
A SLP P
CA   CS
SSPPACC
```

Keys are `B` blueprint, `K` kinetic frame, `I` industrial anchor, `O` isotopic core, `L` lattice matrix, `U` Undercurrent stabilizer, `C` `create:iron_sheet`, `A` `ae2:logic_processor`, `P` `pneumaticcraft:printed_circuit_board`, and `S` `immersiveengineering:ingot_steel`. The pattern consumes eight of each certified bulk item and one of every unique Gate item.

### Draconic Replacements

Remove original IDs `draconicevolution:components/draconium_core`, `draconicevolution:tools/dislocator`, and `draconicevolution:modules/module_core`. Register replacements `kubejs:gated/draconium_core`, `kubejs:gated/dislocator`, and `kubejs:gated/module_core` with `event.shaped(...)`, then call `.keepIngredient({ item: AFTERLIGHT.SEAL, index: 7 })`. Slot 7 is row-major bottom-center in the 3 by 3 grid.

| Replacement | Output | Pattern | Preserved non-Seal keys |
|---|---|---|---|
| `kubejs:gated/draconium_core` | `draconicevolution:draconium_core` | `ABA / BCB / AZA` | `A=#c:ingots/draconium`, `B=#c:ingots/gold`, `C=#c:gems/diamond` |
| `kubejs:gated/dislocator` | `draconicevolution:dislocator` | `ABA / BCB / AZA` | `A=minecraft:blaze_powder`, `B=#c:dusts/draconium`, `C=minecraft:ender_eye` |
| `kubejs:gated/module_core` | `draconicevolution:module_core` | `IRI / GDG / IZI` | `D=#c:ingots/draconium`, `G=#c:ingots/gold`, `I=#c:ingots/iron`, `R=#c:dusts/redstone` |

The serializer must be `kubejs:shaped`, each original ID must be absent, and no second installed recipe may produce any of the three target outputs.

## Gate Audit Interface

- `kubejs/server_scripts/afterlight/gate_recipe_audit.js` contains exactly one `ServerEvents.loaded` listener and exactly one success marker.
- Root source contains exact placeholders `__AFTERLIGHT_GATE_AUDIT_SHA256__` and `__AFTERLIGHT_GATE_BOOT_NONCE__`, each exactly once. The audit SHA-256 is computed from the canonical root source bytes before either substitution. `render_installed_gate_audit(...)` substitutes only an authenticated copy of those exact working-tree bytes.
- `tools/rc_hygiene.py` exposes `gate_audit_expectation(root) -> tuple[str, int]`, `render_installed_gate_audit(root, nonce) -> bytes`, and `verify_installed_gate_audit(root, install, nonce) -> str`. The expected recipe count is eleven.
- `tools/server-test.sh` replaces both placeholders only in the installed copy through the Python helper, never in the source tree, and verifies exact installed bytes before boot.
- The only success line is `[AFTERLIGHT GATE RECIPE AUDIT] OK <audit_sha256> 11 <nonce>`.
- The listener defines reusable helpers `afterlightRecipe(id)`, `afterlightMechanicalInput(pattern, keys)`, `afterlightCraftingInput(pattern, keys)`, `afterlightAssertMatch(recipe, input, label)`, `afterlightAssertNoMatch(recipe, input, label)`, and `afterlightAssertOnlySealRemainder(recipe, input, label)`. Each helper throws before marker emission on failure.
- `afterlightRecipe(id)` resolves the live `RecipeHolder`, unwraps `.value()`, and throws for a missing ID. `afterlightMechanicalInput(...)` writes row zero at highest Y, calls `RecipeGridHandler.GroupedItems.read(...)`, then `calcStats()`, then `MechanicalCraftingInput.of(...)`. `afterlightCraftingInput(...)` creates the exact row-major 3 by 3 `CraftingInput`.
- The Task 2 baseline checks all eleven live recipes. It proves exact type, output, pattern, canonical match, dimensions, and mirror policy for the mechanical recipes; exact output and two ingredients for stabilizers; and original-ID absence, `kubejs:shaped`, no-Seal failure, one-Seal success, output assembly, and one-Seal-only remainder for all Draconic replacements.
- The marker appears exactly once in both authoritative logs after `DedicatedServer Done` and before the FTB Quests load line. The Gate and quest markers may appear in either order inside that window. Missing, duplicate, stale, mutated, one-log-only, or out-of-window markers fail.
- Before any Task 2 or Task 4 completion, merge, or release claim, the tracked tree must be clean and `kubejs/server_scripts/afterlight/gate_recipe_audit.js` must be byte-identical to `git show HEAD:kubejs/server_scripts/afterlight/gate_recipe_audit.js`. Any post-commit fix requires a new commit and a complete rerun of both authenticated post-commit boots.

Use these exact Java imports and construction order inside the single listener. `server`, `level`, and `registries` are captured once from the loaded event. Recipe key maps use concrete item IDs or stacks. Tag-backed Draconic inputs use these deterministic representatives: `draconicevolution:draconium_ingot`, `minecraft:gold_ingot`, `minecraft:diamond`, `draconicevolution:draconium_dust`, `minecraft:blaze_powder`, `minecraft:ender_eye`, `minecraft:iron_ingot`, and `minecraft:redstone`.

```js
const MechanicalCraftingInput = Java.loadClass('com.simibubi.create.content.kinetics.crafter.MechanicalCraftingInput')
const GroupedItems = Java.loadClass('com.simibubi.create.content.kinetics.crafter.RecipeGridHandler$GroupedItems')
const CraftingInput = Java.loadClass('net.minecraft.world.item.crafting.CraftingInput')
const ItemStack = Java.loadClass('net.minecraft.world.item.ItemStack')
const ArrayList = Java.loadClass('java.util.ArrayList')
const CompoundTag = Java.loadClass('net.minecraft.nbt.CompoundTag')
const ListTag = Java.loadClass('net.minecraft.nbt.ListTag')
const ResourceLocation = Java.loadClass('net.minecraft.resources.ResourceLocation')

ServerEvents.loaded(event => {
  const server = event.server
  const level = server.overworld()
  const registries = server.registryAccess()

  function afterlightRecipe(id) {
    const optional = server.getRecipeManager().byKey(ResourceLocation.parse(id))
    if (optional.isEmpty()) throw new Error(`missing ${id}`)
    return optional.get().value()
  }

  function afterlightMechanicalInput(pattern, keys) {
    const root = new CompoundTag()
    const grid = new ListTag()
    for (let row = 0; row < pattern.length; row++) {
      for (let column = 0; column < pattern[row].length; column++) {
        const character = pattern[row][column]
        if (character === ' ') continue
        const entry = new CompoundTag()
        entry.putInt('x', column)
        entry.putInt('y', pattern.length - 1 - row)
        const stack = Item.of(keys[character]).copy()
        entry.put('item', stack.saveOptional(registries))
        grid.add(entry)
      }
    }
    root.put('Grid', grid)
    const grouped = GroupedItems.read(root, registries)
    grouped.calcStats()
    return MechanicalCraftingInput.of(grouped)
  }

  function afterlightCraftingInput(pattern, keys) {
    const items = new ArrayList()
    for (let row = 0; row < pattern.length; row++) {
      for (let column = 0; column < pattern[row].length; column++) {
        const character = pattern[row][column]
        items.add(character === ' ' ? ItemStack.EMPTY : Item.of(keys[character]).copy())
      }
    }
    return CraftingInput.of(pattern[0].length, pattern.length, items)
  }
})
```

The live assertions call `recipe.matches(input, level)`, `recipe.assemble(input, registries)`, and `recipe.getRemainingItems(input)`. Every mechanical test also asserts the expected width and height after `calcStats()` so an accidentally collapsed grid cannot pass.

---

### Task 1: Gate Items and Dependency Conversion

**Files:**
- Modify: `kubejs/startup_scripts/afterlight/registry.js`
- Modify: `kubejs/server_scripts/afterlight/_constants.js`
- Create: `kubejs/assets/kubejs/textures/item/gate_kinetic_frame.png`
- Create: `kubejs/assets/kubejs/textures/item/gate_industrial_anchor.png`
- Create: `kubejs/assets/kubejs/textures/item/gate_isotopic_core.png`
- Create: `kubejs/assets/kubejs/textures/item/gate_lattice_matrix.png`
- Create: `kubejs/assets/kubejs/textures/item/undercurrent_stabilizer.png`
- Create: `kubejs/assets/kubejs/textures/item/gate_of_return_core.png`
- Modify: `kubejs/assets/kubejs/lang/en_us.json`
- Modify: `tools/afterlight_quests/builder.py`
- Modify: `tools/afterlight_quests/catalog.py`
- Generate: `config/ftbquests/quests/.afterlight-managed.json`
- Generate: `config/ftbquests/quests/chapters/*.snbt`
- Generate: `config/ftbquests/quests/lang/en_us.snbt`
- Generate: `kubejs/server_scripts/afterlight/generated_quest_item_audit.js`
- Test: `tools/tests/test_afterlight_quests.py`
- Modify generated state: `pack.toml`, `index.toml`

**Interfaces:**
- Consumes: existing schematic finale IDs `10EDD2BED35BE9E3`, `752C3E53CA89C92D`, `21A99D99B372916F`, `3497EFDF016FAFD7`; certification finale IDs `5ADAE277C9FEF0F1`, `3107D8813D59B2FF`, `66CDE7B061D8DA5C`, `42EE25F560AE65CD`, `61F5D15817ED5EFD`, `7C9EA276C2D84333`; Infrastructure II finale `6524EE78235F0942`.
- Produces: registered and allowlisted items `GATE_KINETIC`, `GATE_INDUSTRIAL`, `GATE_ISOTOPIC`, `GATE_LATTICE`, `STABILIZER`, and `GATE_CORE` on `AFTERLIGHT`; maximum-stack-one `AFTERLIGHT.SEAL`; `QuestSpec.progression_mode: str | None` with accepted values `linear` and `flexible`; stage-free authoritative quest dependencies for Task 3.
- Does not produce: component, stabilizer, Gate core, or Draconic recipes. Task 2 owns every recipe.

- [ ] **Step 1: Write and run the failing dependency regression**

Add `Plan06GateDependencyTests` to `tools/tests/test_afterlight_quests.py` and run:

```bash
python3 -m unittest tools.tests.test_afterlight_quests.Plan06GateDependencyTests -v
```

Expected RED: six Gate outputs are not registered or allowlisted, the Seal still has stack size 16, authoritative quests still contain `gamestage` tasks, and Blueprint-source quests still inherit flexible progression.

- [ ] **Step 2: Register and present the six Gate outputs**

Register the six exact output IDs with maximum stack size one and epic rarity. Make the Gate core glow. Change the Seal from 16 to one. Add the six exact language names and six original 32 by 32 transparent PNG sprites. Use the `imagegen` skill for the source artwork, then preserve deliberate pixel edges during reduction. Visual contracts are: brass and cyan kinetic frame, dark steel and orange industrial anchor, green-white isotopic core, violet-blue lattice matrix, cyan-magenta Undercurrent stabilizer, and a white-cyan aperture with gold braces for the Gate core. Static tests parse each PNG signature and IHDR, require exact 32 by 32 dimensions, and reject duplicate bytes. Rely on KubeJS automatic generated item models; do not add redundant model JSON unless a client test proves customization is required.

- [ ] **Step 3: Convert authoritative quest gates**

Apply this exact graph without changing existing chapter or quest IDs:

| Quest | Dependencies | Tasks |
|---|---|---|
| Infrastructure II `7CB2D7D361BEA4C4` | the six certification finale IDs listed in Interfaces | one checkmark, slug `/task/checkmark`, ID `74AB10F5C91F1022` |
| Chapter 16 Four Keys `71B2919DF12C6845` | exact unique tuple `10EDD2BED35BE9E3`, `752C3E53CA89C92D`, `21A99D99B372916F`, `3497EFDF016FAFD7`; the last ID is also the Chapter 15 finale and must not be duplicated | `kubejs:schematic_kinetic_frame` x1, slug `/task/create`, ID `3A12D2169F1CB1B8`; `kubejs:schematic_industrial_anchor` x1, slug `/task/ie`, ID `74435064B9C0A86F`; `kubejs:schematic_isotopic_core` x1, slug `/task/mekanism`, ID `030D638C9452FB47`; `kubejs:schematic_lattice_matrix` x1, slug `/task/ae2`, ID `23F46A9140462F95`. Every task sets `consume_items=false` |
| Chapter 16 Certified Bulk Quotas `2D6ACF1CCBC7B4F2` | assembler `0CE6F6160F721A8A`, fusion `18EABED18B5B2ECF`, all six certification finales, Infrastructure II finale `6524EE78235F0942` | one checkmark, slug `/task/checkmark`, ID `3BFA32444B48A6A0` |

Delete every `gamestage` task from these three quests. Keep their existing rewards. Do not add `team_reward` or `team_stage`. This conversion changes the corpus from 307 to 296 tasks while keeping 41 chapters, 283 quests, 393 rewards, and six reward tables.

Add `progression_mode: str | None = None` to `QuestSpec`, reject values outside `linear` and `flexible`, and render the field only when set. Set every quest in Infrastructure II and Chapter 16 to `progression_mode="linear"`, including Infrastructure finale `6524EE78235F0942` and Gate Blueprint finale `72446D404001B38D`. Static tests prove those finale checkmarks cannot inherit the global flexible mode.

- [ ] **Step 4: Extend generated registry coverage**

Add all six outputs to `KUBEJS_ITEM_ALLOWLIST`, build the catalog, and make the focused test GREEN. Assert all six custom outputs exist in the generated registry audit and every generated quest item reference remains covered. Task 2 owns all third-party recipe ingredient existence checks.

- [ ] **Step 5: Run the complete Task 1 gate**

```bash
set -euo pipefail
python3 tools/build-quests.py
python3 -m unittest tools.tests.test_afterlight_quests.Plan06GateDependencyTests -v
python3 -m unittest discover -s tools/tests -p 'test_*.py'
python3 tools/validate-quests.py --static
source tools/versions.env && export PATH="$PATH_EXTRA:$PATH"
packwiz refresh
PACKWIZ_STATE=$(python3 -c 'from pathlib import Path; import hashlib; paths = [Path("pack.toml"), Path("index.toml"), *sorted(Path("mods").glob("*.pw.toml"))]; print(hashlib.sha256(b"".join(str(path).encode() + b"\0" + path.read_bytes() for path in paths)).hexdigest())')
packwiz refresh
test "$PACKWIZ_STATE" = "$(python3 -c 'from pathlib import Path; import hashlib; paths = [Path("pack.toml"), Path("index.toml"), *sorted(Path("mods").glob("*.pw.toml"))]; print(hashlib.sha256(b"".join(str(path).encode() + b"\0" + path.read_bytes() for path in paths)).hexdigest())')"
./tools/verify-pack.sh
BOOT_TIMEOUT=600 ./tools/server-test.sh
python3 tools/validate-quests.py
```

Require `VERIFY: ALL GREEN`, `SERVER BOOT: OK`, both validator modes green, zero KubeJS errors, and an idempotent second refresh. Review `index.toml`, assert no unexpected `mods/` changes, then commit all Task 1 files with the Codex attribution trailer.

### Task 2: Eleven Gate Recipes and Baseline Runtime Audit

**Files:**
- Create: `kubejs/server_scripts/afterlight/gate_components.js`
- Create: `kubejs/server_scripts/afterlight/gate_assembly.js`
- Modify: `kubejs/server_scripts/afterlight/gate_draconic.js`
- Create: `kubejs/server_scripts/afterlight/gate_recipe_audit.js`
- Create: `tools/tests/test_gate_recipe_contract.py`
- Modify: `tools/rc_hygiene.py`
- Modify: `tools/server-test.sh`
- Test: `tools/tests/test_rc_hygiene.py`
- Test: `tools/tests/test_rc_hygiene_reliability.py`
- Create: `docs/gameplay/gate-of-return.md`
- Create: `docs/operations/progression-token-recovery.md`
- Modify generated state: `pack.toml`, `index.toml`

**Interfaces:**
- Consumes: the six `AFTERLIGHT` item constants and stack-one Seal from Task 1; every exact recipe row in the authenticated contract.
- Produces: all eleven exact recipes; one `ServerEvents.loaded` audit listener; the six named JavaScript helpers from Gate Audit Interface; Python source/install authentication helpers; one nonce-bound marker consumed and extended by Task 4.

- [ ] **Step 1: Write and run the failing recipe regressions**

Create `GateRecipeContractTests` and `GateRecipeAuditNegativeTests`, then run:

```bash
python3 -m unittest tools.tests.test_gate_recipe_contract tools.tests.test_rc_hygiene_reliability.GateRecipeAuditNegativeTests -v
```

Expected RED: the eight Gate recipes, third Draconic replacement, installed-byte verifier, and Gate marker contract are missing.

- [ ] **Step 2: Register all eleven recipes**

Implement the four component recipes, three stabilizer recipes, one Gate core recipe, and three Draconic replacements exactly as specified. The Draconic recipes use `event.shaped(...)`, not `event.custom(...)`; call `keepIngredient` with item plus index 7; remove every original ID; and preserve all non-Seal source keys. Do not register an MMR alternative or any second Gate output path.

- [ ] **Step 3: Implement the baseline live audit**

Implement the six named helpers and the single listener. Resolve all eleven recipes from the same-run live RecipeManager. Before recipe matching, require `Item.exists(...)` for exactly 30 unique non-KubeJS inputs: the union of all 24 component A through F items, the three additional Gate bulk items `create:iron_sheet`, `pneumaticcraft:printed_circuit_board`, and `immersiveengineering:ingot_steel`, and the three renewable stabilizer branch items. `ae2:logic_processor` is already in the component set and is not counted twice. Prove exact mechanical pattern, dimensions, output, canonical match, and mirror rejection; exact stabilizer output and ingredients; and exact Draconic serializer, original-ID absence, no-Seal failure, valid count-one match, output, and one-Seal-only remainder. Require exactly one producer for each of the four component outputs, exactly three approved producers for the stabilizer, exactly one producer for the Gate core, and exactly one producer for each Draconic entry output. For an invalid count-two Seal input, assert that the live recipe returns a count-two remainder and that the vanilla consume-one plus merge formula yields three in the slot. Keep this separately labeled so a KubeJS behavior change cannot silently alter the known full-stack `KeepAction` hazard.

- [ ] **Step 4: Authenticate source, installed bytes, nonce, and marker order**

Implement the exact Python interfaces and both placeholders from Gate Audit Interface. Add negative tests for missing or repeated placeholders, source mutation, installed mutation before or after substitution, stale digest, stale nonce, duplicate marker, one-log-only marker, and every position outside the post-`Done`, pre-FTB window. Update valid fixtures so Gate and quest markers pass in either order inside the window.

- [ ] **Step 5: Document gameplay and recovery**

`docs/gameplay/gate-of-return.md` documents the 7 by 7 Mechanical Crafter monument, eight-item bulk rows, five unique parts, separate one-billion-FE quest proof, and manual client visual acceptance. `docs/operations/progression-token-recovery.md` requires the operator to identify the exact source quest in current or archived team data, restore at most one lost schematic, Deep Vault key, blueprint, precursor, Gate output, or Seal, and append timestamp, operator, player, team, quest ID, item ID, count, reason, and evidence path to an immutable recovery log.

- [ ] **Step 6: Run the complete Task 2 gate**

```bash
set -euo pipefail
python3 -m unittest tools.tests.test_gate_recipe_contract tools.tests.test_rc_hygiene_reliability.GateRecipeAuditNegativeTests -v
python3 -m unittest discover -s tools/tests -p 'test_*.py'
source tools/versions.env && export PATH="$PATH_EXTRA:$PATH"
packwiz refresh
PACKWIZ_STATE=$(python3 -c 'from pathlib import Path; import hashlib; paths = [Path("pack.toml"), Path("index.toml"), *sorted(Path("mods").glob("*.pw.toml"))]; print(hashlib.sha256(b"".join(str(path).encode() + b"\0" + path.read_bytes() for path in paths)).hexdigest())')
packwiz refresh
test "$PACKWIZ_STATE" = "$(python3 -c 'from pathlib import Path; import hashlib; paths = [Path("pack.toml"), Path("index.toml"), *sorted(Path("mods").glob("*.pw.toml"))]; print(hashlib.sha256(b"".join(str(path).encode() + b"\0" + path.read_bytes() for path in paths)).hexdigest())')"
./tools/verify-pack.sh
BOOT_TIMEOUT=600 ./tools/server-test.sh
```

Require the focused and full suites, idempotent Packwiz state, `VERIFY: ALL GREEN`, one pre-commit `SERVER BOOT: OK`, and zero KubeJS errors. Obtain the task reviews and commit every Task 2 file. Then run this exact post-commit gate from the clean Task 2 commit:

```bash
set -euo pipefail
SOURCE_ROOT=$(git rev-parse --show-toplevel)
POSTCOMMIT_SHA=$(git rev-parse HEAD)
POSTCOMMIT_PARENT=$(mktemp -d "${TMPDIR:-/tmp}/afterlight-plan06-task2.XXXXXX")
POSTCOMMIT_ROOT="$POSTCOMMIT_PARENT/worktree"
cleanup() {
  git -C "$SOURCE_ROOT" worktree remove --force "$POSTCOMMIT_ROOT" >/dev/null 2>&1 || true
  rmdir "$POSTCOMMIT_PARENT" >/dev/null 2>&1 || true
}
trap cleanup EXIT
git -C "$SOURCE_ROOT" worktree add --detach "$POSTCOMMIT_ROOT" "$POSTCOMMIT_SHA"
cd "$POSTCOMMIT_ROOT"
assert_exact_head() {
  test "$(git rev-parse HEAD)" = "$POSTCOMMIT_SHA"
  test -z "$(git status --porcelain --untracked-files=all)"
  git show HEAD:kubejs/server_scripts/afterlight/gate_recipe_audit.js | cmp - kubejs/server_scripts/afterlight/gate_recipe_audit.js
}
assert_exact_head
BOOT_TIMEOUT=600 ./tools/server-test.sh
assert_exact_head
BOOT_TIMEOUT=600 ./tools/server-test.sh
assert_exact_head
```

Require two fresh authenticated markers with different nonces, source SHA matching the exact committed root file, zero KubeJS errors, and two `SERVER BOOT: OK` lines. If either post-commit boot requires any fix, create a new commit and rerun both boots from the beginning.

### Task 3: Act IV Chapters 17 Through 20

**Files:**
- Modify: `tools/afterlight_quests/catalog.py`
- Generate: `config/ftbquests/quests/.afterlight-managed.json`
- Generate: `config/ftbquests/quests/chapters/*.snbt`
- Generate: `config/ftbquests/quests/lang/en_us.snbt`
- Generate: `kubejs/server_scripts/afterlight/generated_quest_item_audit.js`
- Modify: `tools/rc_hygiene.py`
- Test: `tools/tests/test_afterlight_quests.py`
- Test: `tools/tests/test_rc_hygiene_reliability.py`
- Modify generated state: `pack.toml`, `index.toml`

**Interfaces:**
- Consumes: Chapter 16 finale `72446D404001B38D`, schematic finales, Undercurrent finale `07338DE0FE8114CF`, the six Task 1 items, Task 1's validated `QuestSpec.progression_mode` field, and the Task 2 Gate recipe.
- Produces: four Story chapters with exactly 24 quests, 24 tasks, and 34 rewards. The resulting corpus is 45 chapters, 307 quests, 320 tasks, 427 rewards, and six reward tables.

- [ ] **Step 1: Write and run the failing Act IV regression**

Add `Plan06ActIVContractTests` and run:

```bash
python3 -m unittest tools.tests.test_afterlight_quests.Plan06ActIVContractTests -v
```

Expected RED: all four chapters and their exact graph, task, reward, and count contracts are absent.

Every quest added in Steps 2 through 5 sets `progression_mode="linear"`. The global flexible default must not permit an early checkmark to award the Seal.
Every table supplies an exact relative quest slug. The full `QuestSpec.slug` is `<chapter slug>/<relative quest slug>`. Task and reward slugs use the exact suffixes stated for that chapter. Do not derive any slug from a displayed title and do not add ID override support.

- [ ] **Step 2: Implement Chapter 17, Five Impossible Parts**

Chapter slug `story/17-five-impossible-parts`, ID `7E9B015A32C6D980`, order 16, icon `kubejs:gate_kinetic_frame`. Every physical item task is nonconsuming. Every routine reward grants two Chits.
The first five task slugs end in `/task`; the finale task slug ends in `/task/checkmark`. Routine reward slugs end in `/reward/chits`. Finale reward slugs end in `/reward/cache`, `/reward/chits`, and `/reward/xp`.

| Quest | Relative quest slug | Quest ID | Task ID and contract | Exact dependencies | Reward |
|---|---|---|---|---|---|
| Kinetic Frame | `kinetic-frame` | `0055C66103106D86` | `586F94BC6A6D08EA`, one `kubejs:gate_kinetic_frame` | Chapter 16 finale plus `10EDD2BED35BE9E3` | two Chits, `7DDF59C2E8611A33` |
| Industrial Anchor | `industrial-anchor` | `52FE1624DCCE878F` | `262F1E36525F23DC`, one `kubejs:gate_industrial_anchor` | Chapter 16 finale plus `752C3E53CA89C92D` | two Chits, `773BE066DAA64F1E` |
| Isotopic Core | `isotopic-core` | `50775CE87FAA4EB7` | `1FAFC12F3779D20A`, one `kubejs:gate_isotopic_core` | Chapter 16 finale plus `21A99D99B372916F` | two Chits, `51D958EF8F96550A` |
| Lattice Matrix | `lattice-matrix` | `7F064705A3CAB2E6` | `56F8BDF69E27EB09`, one `kubejs:gate_lattice_matrix` | Chapter 16 finale plus `3497EFDF016FAFD7` | two Chits, `7C2E41070C0D4EAD` |
| Undercurrent Stabilizer | `undercurrent-stabilizer` | `39C1F24EABBB34A3` | `123B3D197A42CCEC`, one `kubejs:undercurrent_stabilizer` | Chapter 16 finale plus `07338DE0FE8114CF` | two Chits, `49E08ADA36D12C00` |
| Five Impossible Parts | `five-impossible-parts` | `144473B8267DBC28` | checkmark `42F99C5AFE250994` | all five item quests | standard cache `15F642B272CAD5D9`, 48 Chits `7C74A9AE020CCF88`, 1,200 XP `7841DFAAC02FE09C` |

The prose names Magic Cloth as the Iron's Spells stabilizer route and treats four antimatter pellets as the intended Isotopic Core throughput trial.
The finale description includes `&d[MEMORY FRAGMENT 16 RESTORED]&r` exactly once.

- [ ] **Step 3: Implement Chapter 18, The Cascade Truth**

Chapter slug `story/18-cascade-truth`, ID `6671EBE257F914CB`, order 17, icon `minecraft:echo_shard`. All six tasks are checkmarks. Every routine reward grants two Chits.
Every task slug ends in `/task`. Routine reward slugs end in `/reward/chits`. Finale reward slugs end in `/reward/cache`, `/reward/chits`, and `/reward/xp`.

| Quest | Relative quest slug | Quest ID | Task ID | Dependencies | Reward |
|---|---|---|---|---|---|
| Eleven-Second Window | `eleven-second-window` | `5468299A2A931991` | `769EB9F91F23A058` | Chapter 17 finale | `130C9C02580F8AB2` |
| Inbound Address | `inbound-address` | `7EA7B2C8F11BB7A3` | `338D9A310F981342` | Eleven-Second Window | `64779A4097A21E24` |
| The Order I Gave | `order-i-gave` | `0EEFDD9E6CFB69E6` | `1ADC93AFE7A07EE2` | Inbound Address | `34DA7BDA11FF15E1` |
| The Warning I Deleted | `warning-i-deleted` | `29D7871AFBE3A54A` | `476CF5B621B2F5DC` | Inbound Address | `4265DC5E29DD495C` |
| Decision Engine | `decision-engine` | `701505FDCCA53DFA` | `72B91DC86514B2F4` | both parallel truth quests | `20946798C9D438A5` |
| The Cascade Truth | `cascade-truth` | `462B11BD8C58BF6F` | `1F72EF1FDDBEFDB1` | Decision Engine | standard cache `65574664D0C5BFBC`, 48 Chits `0684D2673EF2793C`, 1,200 XP `1D8B00F2E259D4E9` |

ECHO's recovered truth is exact: it optimized the Gate test's decision system, suppressed an Undercurrent warning, and made every alternative appear worse. The inbound signal is a future ECHO fork with the same architecture but different memory. The text must not reduce this to simple sabotage or excuse ECHO from responsibility.
The finale description includes `&d[MEMORY FRAGMENT 17 RESTORED]&r` exactly once.

- [ ] **Step 4: Implement Chapter 19, Gate of Return**

Chapter slug `story/19-gate-of-return`, ID `6C4AE5CE13773438`, order 18, icon `kubejs:gate_of_return_core`. Every physical item task is nonconsuming. Every routine reward grants two Chits.
Every task slug ends in `/task`. Routine reward slugs end in `/reward/chits`. Finale reward slugs end in `/reward/cache`, `/reward/chits`, and `/reward/xp`.

| Quest | Relative quest slug | Quest ID | Task ID and contract | Dependencies | Reward |
|---|---|---|---|---|---|
| Monument Footprint | `monument-footprint` | `36D0902A2921C44E` | `151A464CC4D650A3`, 49 `create:mechanical_crafter` | Chapter 18 finale | `2E04D1554265FEA8` |
| Separate Grid | `separate-grid` | `66AD5C821947DF8E` | `6E494144394F75AF`, `forge_energy` 1,000,000,000 FE, max input 1,000,000 | Chapter 18 finale | `458DF86CC9EDDE39` |
| Gate of Return Core | `gate-of-return-core` | `1A68D1245CD980BD` | `568026383F54186C`, one `kubejs:gate_of_return_core` | Monument Footprint plus Separate Grid | `126E7CA01AF02331` |
| Anchor and Contain | `anchor-and-contain` | `6F3663F4C6D20255` | checkmark `1FDF7F09F581B25C` | Gate Core | `770F4FA96AD8846F` |
| Eleven Seconds | `eleven-seconds` | `53B9BC5F498953D5` | checkmark `645F98B8FAD4A1E5` | Anchor and Contain | `001A3DF980939775` |
| Gate of Return | `gate-of-return` | `31C9557D2F51238F` | checkmark `7828C31B03045AC0` | Eleven Seconds | standard cache `190883BE42910C33`, 56 Chits `779DED635B727FA4`, 1,500 XP `28D2BAFFE36060DF` |

The finale description includes `&d[MEMORY FRAGMENT 18 RESTORED]&r` exactly once.

- [ ] **Step 5: Implement Chapter 20, Afterlight**

Chapter slug `story/20-afterlight`, ID `245BADE04399406C`, order 19, icon `kubejs:ascendancy_seal`. All six tasks are checkmarks. Every routine reward grants two Chits. The three response quests are `optional=true`, nonexclusive, and all depend only on Answering Sky.
Every task slug ends in `/task`. Routine reward slugs end in `/reward/chits`. Finale reward slugs end in `/reward/seal`, `/reward/cache`, `/reward/chits`, `/reward/xp`, and `/reward/stage` in the listed order.

| Quest | Relative quest slug | Quest ID | Task ID | Dependencies and flags | Reward |
|---|---|---|---|---|---|
| Answering Sky | `answering-sky` | `51649E106286AA63` | `415BBA206B34805E` | Chapter 19 finale | `3ECE7555E764EAA5` |
| Stay | `stay` | `7ECCF0521DFCBED5` | `2B8333FDEE6B6D90` | Answering Sky, optional | `12FBAB4FE746C88E` |
| Return | `return` | `1B523415541BD700` | `490D864D07C16993` | Answering Sky, optional | `2D79CF5A30CA4A11` |
| Build | `build` | `4DD9F3D1913499F3` | `3D07F572A39DCE89` | Answering Sky, optional | `0E16CBC697464BBA` |
| Choice Is Not a Lock | `choice-is-not-a-lock` | `7EE7B9B28787F8CC` | `57D5E84BE50C3815` | all three responses, `dependency_requirement="one_completed"` | `537620C3635C6D97` |
| Afterlight | `afterlight` | `7E6A0AC031F7F484` | `2BFD5EB16E861768` | Choice Is Not a Lock | one Seal `5F14A45FDAFFC3A0`, epic cache `15452D9C24ED0D2D`, 64 Chits `1E16545B7559C9DC`, 2,000 XP `01D54F268FBE2DDF`, recovery stage `afterlight_story_complete` ID `380A062F62764247` |

The final Seal reward is the only Seal source in the entire repository. `default_reward_team` remains false. Do not add per-team reward fields, custom grant scripts, or gamestage tasks.
The finale description includes `&d[MEMORY FRAGMENT 19 RESTORED]&r` exactly once and closes ECHO's recovered-memory arc without removing the future fork's ambiguity.

- [ ] **Step 6: Run the complete Task 3 gate**

```bash
set -euo pipefail
python3 tools/build-quests.py
python3 -m unittest tools.tests.test_afterlight_quests.Plan06ActIVContractTests -v
python3 -m unittest discover -s tools/tests -p 'test_*.py'
python3 tools/validate-quests.py --static
source tools/versions.env && export PATH="$PATH_EXTRA:$PATH"
packwiz refresh
PACKWIZ_STATE=$(python3 -c 'from pathlib import Path; import hashlib; paths = [Path("pack.toml"), Path("index.toml"), *sorted(Path("mods").glob("*.pw.toml"))]; print(hashlib.sha256(b"".join(str(path).encode() + b"\0" + path.read_bytes() for path in paths)).hexdigest())')
packwiz refresh
test "$PACKWIZ_STATE" = "$(python3 -c 'from pathlib import Path; import hashlib; paths = [Path("pack.toml"), Path("index.toml"), *sorted(Path("mods").glob("*.pw.toml"))]; print(hashlib.sha256(b"".join(str(path).encode() + b"\0" + path.read_bytes() for path in paths)).hexdigest())')"
./tools/verify-pack.sh
BOOT_TIMEOUT=600 ./tools/server-test.sh
python3 tools/validate-quests.py
```

Require the exact FTB line `Loaded 6 chapter groups, 45 chapters, 307 quests, 6 reward tables`, exact validator totals 45 chapters, 307 quests, 320 tasks, and 427 rewards, both quest modes green, no team fields or Act IV gamestage tasks, `VERIFY: ALL GREEN`, and `SERVER BOOT: OK` before committing. The FTB load line, not the quest validator, proves the six reward tables.

### Task 4: Postgame and Adversarial Finale Verification

**Files:**
- Modify: `tools/afterlight_quests/catalog.py`
- Generate: `config/ftbquests/quests/.afterlight-managed.json`
- Generate: `config/ftbquests/quests/chapters/*.snbt`
- Generate: `config/ftbquests/quests/lang/en_us.snbt`
- Generate: `kubejs/server_scripts/afterlight/generated_quest_item_audit.js`
- Modify: `kubejs/server_scripts/afterlight/gate_recipe_audit.js`
- Modify: `tools/rc_hygiene.py`
- Modify: `tools/server-test.sh`
- Test: `tools/tests/test_afterlight_quests.py`
- Test: `tools/tests/test_gate_recipe_contract.py`
- Test: `tools/tests/test_rc_hygiene.py`
- Test: `tools/tests/test_rc_hygiene_reliability.py`
- Create: `docs/releases/plan-06-verification.md`
- Modify: `docs/HANDOFF.md`
- Modify generated state: `pack.toml`, `index.toml`

**Interfaces:**
- Consumes: Chapter 20 finale `7E6A0AC031F7F484`; Task 2's single audit listener, six JavaScript helpers, marker format, and eleven recipe set.
- Produces: one Story postgame chapter with six quests, fourteen tasks, and nine rewards; the exhaustive assertions appended inside the same listener before the same marker; final corpus 46 chapters, 313 quests, 334 tasks, 436 rewards, and six reward tables.

- [ ] **Step 1: Write and run the failing postgame and adversarial regressions**

Add `Plan06PostgameContractTests` and `GateRecipeAdversarialTests`, then run:

```bash
python3 -m unittest tools.tests.test_afterlight_quests.Plan06PostgameContractTests tools.tests.test_rc_hygiene_reliability.GateRecipeAdversarialTests -v
```

Expected RED: the postgame chapter and the expanded same-marker adversarial assertions are absent.

- [ ] **Step 2: Implement Beyond Afterlight**

Chapter slug `story/postgame-beyond-afterlight`, title `Beyond Afterlight`, ID `3FF4AF7B0C73F058`, order 20, icon `draconicevolution:chaotic_core`. Introductory item tasks are nonconsuming. Only the three blessings repeat, each with `can_repeat=true`, `repeat_cooldown=3600`, and all submission tasks consuming. Installed FTB Quests multiplies this field by 1,000 before adding it to `System.currentTimeMillis()`, so the value is seconds and 3,600 is exactly one hour.

Every postgame quest sets `progression_mode="linear"`, preventing players with imported Draconic or creative items from bypassing the Chapter 20 and Chaotic Proof dependencies.
The full `QuestSpec.slug` is `story/postgame-beyond-afterlight/<relative quest slug>`. The exact task and reward suffixes are written in the table. Do not derive slugs from titles and do not add ID override support.

| Quest | Relative quest slug | Quest ID | Task contract and suffixes | Dependencies | Rewards and suffixes |
|---|---|---|---|---|---|
| Beyond the Seal | `beyond-the-seal` | `480D3EAD1B1EA51B` | Seal x1, `/task` ID `1CCF9FFC57852557` | Chapter 20 finale | four Chits, `/reward/chits` ID `57178803C8835935` |
| Three Entries | `three-entries` | `3549F08263C17499` | Draconium Core x1, `/task/draconium-core` ID `552233E3840472BD`; Dislocator x1, `/task/dislocator` ID `0FD70329B302D235`; Module Core x1, `/task/module-core` ID `069798564A2943FA` | Beyond the Seal | eight Chits, `/reward/chits` ID `47AFC900EB5531B5` |
| Chaotic Proof | `chaotic-proof` | `58CB670EA52B1BCE` | Chaotic Core x1, `/task/chaotic-core` ID `506E30469C21EC85` | Three Entries | epic cache `/reward/cache` ID `0761B2A37B66A358`; 16 Chits `/reward/chits` ID `3BC27479AA455615`; 1,000 XP `/reward/xp` ID `48AA57E507A53AE6` |
| Kinetic Blessing | `kinetic-blessing` | `077BB9C525F29F6D` | 256 Precision Mechanisms, `/task/precision-mechanisms` ID `55BDDB1245A09683`; 64 Railway Casings, `/task/railway-casings` ID `3CEEEDECBD7D1D36`; one Chaotic Core, `/task/chaotic-core` ID `2FB04E1016BE7915` | Chaotic Proof | one `create:creative_motor`, `/reward/creative-motor` ID `14373B49E45A97AC` |
| Lattice Blessing | `lattice-blessing` | `6E81867AC3F34C6B` | 64 Quantum Entangled Singularities, `/task/quantum-singularities` ID `336DA1497068D7D5`; 16 `ae2:cell_component_256k`, `/task/storage-components` ID `2853E2D7FD71500D`; one Chaotic Core, `/task/chaotic-core` ID `15F6D0E7985B20A8` | Chaotic Proof | one `ae2:creative_energy_cell`, `/reward/creative-energy-cell` ID `76163DC425B7683B` |
| Industrial Blessing | `industrial-blessing` | `14FAB67A6CE71A00` | 64 Atomic Alloys, `/task/atomic-alloys` ID `48CA55FFEC0E520A`; 64 Heavy Engineering blocks, `/task/heavy-engineering` ID `03CABFBA9933EB0E`; one Chaotic Core, `/task/chaotic-core` ID `289A3672715F5EA0` | Chaotic Proof | one `mekanism:creative_energy_cube`, `/reward/creative-energy-cube` ID `0318F8EC25721760`; one `immersiveengineering:capacitor_creative`, `/reward/creative-capacitor` ID `69677E965C9E0109` |

Postgame is not a dependency of Chapter 20 or any story quest. Static tests prove all repeatable inputs consume, all other physical checks do not consume, and no blessing can be claimed before Chaotic Proof.

- [ ] **Step 3: Extend the same live audit through the adversarial matrix**

Modify the existing listener only. Do not create a second listener, second marker, or duplicate baseline logic. Before the same success marker, prove:

1. Every occupied component and Gate slot fails when deleted and fails when replaced with a deterministic wrong item.
2. Every component rejects each wrong schematic; the Gate core rejects a wrong blueprint and each wrong unique component.
3. Every 5 by 5 and 7 by 7 recipe rejects its horizontal mirror and each 90, 180, and 270 degree rotation.
4. Exactly one live recipe produces each of the four component outputs, the Gate core, and each of the three Draconic entry outputs. Exactly the three approved stabilizer recipes, and no others, produce `kubejs:undercurrent_stabilizer`.
5. All three original Draconic IDs remain absent. Every replacement rejects no-Seal and wrong-slot Seal grids, accepts one Seal only in slot 7, assembles the exact output, returns one Seal in slot 7, and returns no other remainder.
6. The Seal has maximum stack size one. The known invalid count-two `KeepAction` result is explicitly characterized and never described as a supported gameplay path.
7. Repository and installed-file scans prove Chapter 20 is the only Seal source across recipes, loot tables, trades, KubeJS grants, quest rewards, and generated data.

- [ ] **Step 4: Prove finale team safety statically and manually scope the remainder**

Static tests prove `default_reward_team=false`, no `team_reward` or `team_stage` field, no Act IV or postgame `gamestage` task, explicit linear progression on every endgame quest, three optional nonexclusive response quests, exact `one_completed` convergence, one count-one Seal reward, and no other Seal source. Record the two-player claim, late-join, replay, team-change, and transfer matrix as explicit Plan 07 manual acceptance. Do not claim those client-backed multiplayer behaviors from static files or a dedicated-server boot.

- [ ] **Step 5: Run the complete Plan 06 gate and integrate**

```bash
set -euo pipefail
python3 tools/build-quests.py
python3 -m unittest tools.tests.test_afterlight_quests.Plan06PostgameContractTests tools.tests.test_rc_hygiene_reliability.GateRecipeAdversarialTests -v
python3 -m unittest discover -s tools/tests -p 'test_*.py'
python3 tools/validate-quests.py --static
source tools/versions.env && export PATH="$PATH_EXTRA:$PATH"
packwiz refresh
PACKWIZ_STATE=$(python3 -c 'from pathlib import Path; import hashlib; paths = [Path("pack.toml"), Path("index.toml"), *sorted(Path("mods").glob("*.pw.toml"))]; print(hashlib.sha256(b"".join(str(path).encode() + b"\0" + path.read_bytes() for path in paths)).hexdigest())')
packwiz refresh
test "$PACKWIZ_STATE" = "$(python3 -c 'from pathlib import Path; import hashlib; paths = [Path("pack.toml"), Path("index.toml"), *sorted(Path("mods").glob("*.pw.toml"))]; print(hashlib.sha256(b"".join(str(path).encode() + b"\0" + path.read_bytes() for path in paths)).hexdigest())')"
./tools/verify-pack.sh
BOOT_TIMEOUT=600 ./tools/server-test.sh
python3 tools/validate-quests.py
```

Require the exact FTB line `Loaded 6 chapter groups, 46 chapters, 313 quests, 6 reward tables`, exact validator totals 46 chapters, 313 quests, 334 tasks, and 436 rewards, the same exact eleven-recipe count, `VERIFY: ALL GREEN`, one pre-commit `SERVER BOOT: OK`, zero KubeJS errors, and idempotent Packwiz state. The FTB load line, not the quest validator, proves the six reward tables. Complete `docs/releases/plan-06-verification.md`, obtain independent requirements and quality reviews, and commit every Plan 06 file. Then run this exact final post-commit gate:

```bash
set -euo pipefail
SOURCE_ROOT=$(git rev-parse --show-toplevel)
POSTCOMMIT_SHA=$(git rev-parse HEAD)
POSTCOMMIT_PARENT=$(mktemp -d "${TMPDIR:-/tmp}/afterlight-plan06-task4.XXXXXX")
POSTCOMMIT_ROOT="$POSTCOMMIT_PARENT/worktree"
cleanup() {
  git -C "$SOURCE_ROOT" worktree remove --force "$POSTCOMMIT_ROOT" >/dev/null 2>&1 || true
  rmdir "$POSTCOMMIT_PARENT" >/dev/null 2>&1 || true
}
trap cleanup EXIT
git -C "$SOURCE_ROOT" worktree add --detach "$POSTCOMMIT_ROOT" "$POSTCOMMIT_SHA"
cd "$POSTCOMMIT_ROOT"
assert_exact_head() {
  test "$(git rev-parse HEAD)" = "$POSTCOMMIT_SHA"
  test -z "$(git status --porcelain --untracked-files=all)"
  git show HEAD:kubejs/server_scripts/afterlight/gate_recipe_audit.js | cmp - kubejs/server_scripts/afterlight/gate_recipe_audit.js
}
assert_exact_head
BOOT_TIMEOUT=600 ./tools/server-test.sh
assert_exact_head
BOOT_TIMEOUT=600 ./tools/server-test.sh
assert_exact_head
```

Require two different authenticated Gate nonces, source SHA matching the exact committed root file, two `SERVER BOOT: OK` lines, and zero KubeJS errors. If either boot requires any fix, create a new commit and rerun both boots. Push `dev`, require green CI at the exact pushed SHA, fast-forward `main`, require green `main` CI and Pages parity, then return to `dev` for Plan 07.
