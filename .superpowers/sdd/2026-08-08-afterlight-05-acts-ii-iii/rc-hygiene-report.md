# AFTERLIGHT Release-Candidate Hygiene Report

Date: 2026-08-08
Branch: `dev`
Base commit: `1ce304f`

## Result

Release-candidate hygiene is implemented in the shared working tree. The final clean-world dedicated-server run completed with `SERVER BOOT: OK`. All 18 hygiene fixture tests pass, every repaired signature is absent, and every documented residual has an exact asserted count. No push was performed.

## Root-Cause Evidence

- Oritech ships `data/oritech/recipe/mixing/compat/create/turbofuel.json` with ingredient type `fluid_stack`. The installed NeoForge recipe serializer accepts `neoforge:single`, so the override changes that type only.
- Industrial Foregoing ships `data/industrialforegoing/curios/entities/entities.json` with the invalid Curios slot string `example`. The override removes only that string.
- Cataclysm logs both missing tool tags against the `minecraft:block` registry. The valid repairs are therefore empty block tags at `data/cataclysm/tags/block/needs_black_steel_tool.json` and `needs_monstrosity_tool.json`, despite the brief's informal item-tag wording.
- Four advancement resources point to missing parents. Each override preserves its source resource and changes only `parent` to the installed root advancement.
- The installed Malum codec requires `validItems`, nested `regex`, and namespaced spirit types. Four regex recipes also need nonempty `validItems` for KubeJS schema parsing. Their exact installed Undergarden repairable item sets are supplied while the source regex values remain unchanged.
- Malum's grim talc Create recipe uses obsolete result key `item`. The override changes each result key to `id` only.
- Create Enchantment Industry's experience data map contains stale `enderio:xpjuice`. The reviewed map preserves every conditional source value, replaces only that value key with `enderio:xp_juice` at 20, and uses NeoForge replacement controls.
- NeoForge data maps inspect resource stacks rather than ordinary winner-only resources. A deterministic one-file KubeJS datapack filter blocks only CEI's lower stale experience-map resource, allowing the reviewed replacement to load without the obsolete signature.
- EnderCore 8.2.11-beta bytecode registers XP Juice source fluid as `fluid_xp_juice_still`, and EnderIO's own fluid tag uses `enderio:fluid_xp_juice_still`. The mandated `enderio:xp_juice` entry therefore remains one visible upstream mismatch.
- Four IDAS optional-biome tags merged with their lower source definitions while `replace` was false. Setting `replace` true keeps the same biome IDs, marks them non-required, and eliminates all four load failures. No IDAS structure NBT was touched or redistributed.
- Preseeding Just Dire Things config does not fix its dispenser registration warning. The warning occurs because registration reads the config before the loader lifecycle completes, so it is preserved as an exact residual.

## Reviewed Configs

Only these generated server-test configs were copied into tracked `config/`:

- `jupiter.json`
- `iceandfire/iaf-common.json`
- `justdirethings-server.toml`
- `mcjtylib-server.toml`
- `create_enchantment_industry-server.toml`
- `quark-common.toml`
- `alexsmobs-common.toml`

Generated values are preserved except for the approved spawn mitigations:

- Quark modules remain enabled. Stoneling, Toretoise, Foxhound, and lesser Foxhound whitelist tag and biome arrays are empty.
- Alex's Mobs has `skreecherSpawnWeight = 0` and `skreecherSpawnRolls = 1`.

Whole-file SHA-256 fixtures lock all seven reviewed configs after normalizing only a final newline.

## Data Repairs

- Oritech turbofuel serializer: one field changed.
- Industrial Foregoing Curios entity slots: only `example` removed.
- Cataclysm tool requirements: two empty block tags added.
- Advancements: four missing parents corrected.
- Malum: nine spirit-repair recipes and one Create milling recipe corrected against installed schemas.
- Create Enchantment Industry: complete source map preserved with the single EnderIO key replacement and an exact lower-resource filter.
- Loot tables: sixteen Create Connected tables, one ExtendedAE table, and one Iron's Spells test table replaced with valid empty tables.
- IDAS: four optional-biome tags made non-required with source IDs preserved.

## Mod Metadata

- Terralith is pinned to Modrinth version `IY93YaEe`, version number `2.6.2`, filename `Terralith_1.21.1_v2.6.2_Neoforge.jar`, SHA-512 `35298f1682567f63dc16658b04cee5498b30819f1c05f9712b4480d7f5eb17059db3b13ab14f81a05fe257149d11ced2cce2030d3727c1747edd8657c53e2a85`, and side `both`.
- Lithostitched is side `both`.
- `pack.toml`, `index.toml`, and both mod metadata files were refreshed together. The index delta contains only intended configs, KubeJS data, the hygiene filter pack, and mod metadata hashes.

## Fixture Coverage

`tools/tests/test_rc_hygiene.py` compares every JSON override semantically with its source jar resource and applies only approved transformations. It also asserts:

- exact whole-config hashes and approved spawn values;
- exact Terralith and Lithostitched metadata;
- absence of redistributed IDAS NBT;
- exact CEI filter-pack metadata and archive contents;
- zero occurrences for every repaired boot signature;
- exact counts for every documented residual.

`tools/server-test.sh` runs the hygiene fixture suite after quest auditing and before it prints `SERVER BOOT: OK`.

## Test-Led Repair Evidence

- The initial fixture run failed with 78 assertion failures before the repairs existed.
- The first clean boot reached Minecraft's `Done` marker, then failed seven signature checks: one Just Dire lifecycle check, one aggregate Malum check covering four recipes, one stale CEI check, and four IDAS tag checks.
- Just Dire was reclassified only after its preseeded config proved the warning is lifecycle-driven.
- Fixture expectations were changed before adding Malum `validItems`, IDAS replacement controls, and CEI data-map controls.
- A later clean boot exposed four KubeJS Malum fallbacks that the Minecraft serializer did not report. A new zero-signature assertion failed first, then exact repairable item lists corrected the schema without changing regex behavior.
- CEI replacement and removal controls could not suppress the lower resource because NeoForge inspects stacked data-map resources. The first last-stage replay doubled both errors and was removed. A fixture-led one-file pack filter then reduced stale `xpjuice` to zero while preserving the single `xp_juice` upstream mismatch.

## Clean-Boot Residuals

The final clean log asserts these exact residual counts:

| Residual family | Count |
|---|---:|
| Kaleidoscope carrier warnings | 27 |
| Incendium smithing fallback | 1 |
| EnderIO Malum inheritance warnings | 9 |
| IDAS air ItemStack errors | 2 |
| Just Dire Things config lifecycle warning | 1 |
| EnderIO XP Juice registry mismatch | 1 |
| Apothic Enchanting stale data-map type | 1 |
| IDAS empty optional-tag registry warnings | 2 |
| RuntimeDistCleaner client-class errors | 12 |
| Moonlight Fabric API detection error | 1 |
| Fabric overlay metadata error | 1 |

Repaired signatures are all exactly zero, including stale CEI `enderio:xpjuice`, both Malum parse families, all four IDAS load failures, both Cataclysm missing tags, invalid loot tables, advancement parents, config races, and approved spawn warnings.

## Verification Evidence

- Focused config, jar-override, and metadata fixtures: 18 tests, `OK`.
- Full quest tests: 47 tests, `OK`.
- Static quest validation: `VALIDATE QUESTS: OK (41 chapters, 283 quests, 307 tasks, 393 rewards)`.
- Clean-world command: `BOOT_TIMEOUT=1200 ./tools/server-test.sh`.
- Clean-world result: `SERVER BOOT: OK`.
- Integrated clean-boot hygiene suite: 18 tests, `OK`.
- Runtime item audit: `OK 4e1670d897a02c35bfae380d1863597f46d8307c3c375e69f6454ce3204a4511 219` with the fresh boot nonce.
- Default quest validation: `VALIDATE QUESTS: OK (41 chapters, 283 quests, 307 tasks, 393 rewards)`.
- Pack verification: refresh idempotent, manifest verified, tooling sanity passed, and `VERIFY: ALL GREEN`.

## Concerns and Follow-Up

- CEI's mandated `enderio:xp_juice` does not match EnderCore's installed fluid registry ID `enderio:fluid_xp_juice_still`. The stale key is repaired, but the replacement remains one asserted upstream error. Changing the mandated value or registering an alias would mask the mismatch and was not done.
- Just Dire Things still emits one config lifecycle warning even with the reviewed generated config present.
- IDAS still emits two registry warnings for optional tags that resolve empty. The prior eight load-error occurrences are gone, and its two benign air ItemStack errors remain unchanged.
- RuntimeDistCleaner, Moonlight, Fabric overlay, and Apothic diagnostics are existing upstream compatibility residuals, now count-locked rather than hidden.
- No client launch, multiplayer acceptance run, or CI push was performed in this task.
