# RC Hygiene Brief

Run this after Plan 05 Task 6 and before Plan 05 final verification. The release gate must distinguish repaired defects from source-bound upstream residuals and must fail closed when logs, artifacts, or process state change.

## Approved Scope

The controller explicitly approved the following additions to the original hygiene scope:

1. Oritech turbofuel fluid ingredient serializer repair.
2. Industrial Foregoing Curios entity-slot repair.
3. Cataclysm empty tool-requirement block tags.

These are authorized release-candidate repairs, not scope violations.

## Data and Config Requirements

1. Copy only the seven reviewed generated configs for Jupiter, Ice and Fire, Just Dire Things, McJtyLib, Create Enchantment Industry, Quark, and Alex's Mobs. Preserve generated values except the approved Quark and Alex's Mobs spawn changes. The Just Dire Things file establishes normal eventual config values but does not prevent its early lifecycle warning.
2. Keep Quark's Foxhound, Stoneling, and Toretoise modules enabled. Empty the tag and biome whitelists for Stoneling, Toretoise, Foxhound, and lesser Foxhound.
3. Set Alex's Mobs `skreecherSpawnWeight = 0` and `skreecherSpawnRolls = 1`.
4. Change only Oritech's turbofuel fluid ingredient type from `fluid_stack` to `neoforge:single`.
5. Remove only the invalid Industrial Foregoing Curios slot string `example`.
6. Add valid empty Cataclysm block tags `needs_black_steel_tool` and `needs_monstrosity_tool`.
7. Override `minecraft:wander_add_map` and `minecraft:give_quest_trader_trade`, changing only their missing parent to `nova_structures:root`.
8. Override `dungeons_arise:find_fishing_hut` and `dungeons_arise:find_thornborn_towers`, changing only their missing parent to `dungeons_arise:wda_root`.
9. Repair the nine loaded Malum spirit-repair compatibility recipes against the installed schema, and change only Create result keys from `item` to `id` in `malum:create/milling/grim_talc`.
10. Preserve the complete Create Enchantment Industry experience map. Replace only `enderio:xpjuice` with the installed fluid registry ID `enderio:fluid_xp_juice_still`, preserving value `20` and the original EnderIO condition. Require zero errors for the stale ID, the rejected intermediate ID `enderio:xp_juice`, and the final replacement ID.
11. Use a deterministic one-file data-pack filter with anchored namespace and path expressions to block only CEI's lower stale map resource.
12. Replace the sixteen invalid Create Connected Dye Depot catalyst loot tables, `extendedae:blocks/ex_emc_interface`, and `irons_spellbooks:test/ring_gen_break_me` with valid empty loot tables.
13. Make the four source IDAS compatibility tags non-required while preserving their source IDs: `byg_redwood_biomes`, `bygmohogany_biomes`, `bopredwood_biomes`, and `bopmohogany_biomes`.
14. Add exact optional empty definitions for every structure-referenced IDAS tag absent from the source jar: `idas:has_structure/bygredwood_biomes`, `idas:has_structure/bygmahogany_biomes`, and `idas:has_structure/bopmahogany_biomes`.
15. Never modify or redistribute IDAS structure NBT. Bind the two benign `minecraft:air` ItemStack errors to the exact source `underground_camp1.nbt` bytes and its Create saw filter and toolbox compartment paths.
16. Pin Terralith to Modrinth version `IY93YaEe`, version `2.6.2`, filename `Terralith_1.21.1_v2.6.2_Neoforge.jar`, SHA-512 `35298f1682567f63dc16658b04cee5498b30819f1c05f9712b4480d7f5eb17059db3b13ab14f81a05fe257149d11ced2cce2030d3727c1747edd8657c53e2a85`, and side `both`. Set Lithostitched side to `both`.

## Just Dire Things Determination

The Just Dire Things warning is an upstream false positive from Supplementaries' early generic pancake candidate scan. The initial scan reaches `FuelCanister.getCraftingRemainingItem` before NeoForge loads server configs. A successful post-config scan still classifies the fuel canister as `Topping.NONE`, registers no custom behavior, and leaves vanilla dispenser ejection intact.

Do not add compensation, disable pancakes, disable Supplementaries dispenser behavior, or ship a custom compatibility mod. Allow exactly one full-message WARN from logger `Supplementaries` for `justdirethings:fuel_canister` and the exact `IllegalStateException`. Bind that allowance to the reviewed Just Dire Things, Supplementaries, Moonlight, KubeJS, NeoForge, patched server, config, and relevant class hashes. Any changed item, logger, message, exception, artifact, or count must fail.

## Verification Requirements

1. Resolve every source fixture from its exact `.pw.toml` path. Verify the current pack and index, declared filename, side, download hash, installer provenance, installed path, and installed bytes before reading jar resources.
2. Compare every override with its authenticated source resource and assert only approved differences.
3. Rebuild the filter ZIP deterministically. Assert byte identity, SHA-256, fixed timestamp, mode, compression, empty metadata fields, anchored regexes, and the exact blocked resource set across authenticated server artifacts.
4. Pin `packwiz-installer-bootstrap` v0.0.3 and verify SHA-256 `a8fbb24dc604278e97f4688e82d3d91a318b98efc08d5dbfcbcbcab6443d116c` before execution.
5. Run `packwiz serve --refresh=false`. Verify manifest and index coherence before install and fail if `pack.toml` or `index.toml` changes at any phase.
6. Preserve the server process status. Require status `0`, one anchored `DedicatedServer` Done record in the authoritative current `latest.log`, the fresh nonce in that log, and all clean shutdown markers.
7. Parse every ERROR and FATAL record from the authoritative log. Reject every unmatched record. Bind every allowed residual to exact logger, full stable message, resource or stack context where available, current source evidence, and exact count. Require zero repaired signatures and zero IDAS missing-tag records.
8. Preserve exact known residuals: 27 Kaleidoscope carrier warnings, one Incendium smithing fallback, nine EnderIO Malum inheritance warnings, exactly two source-bound IDAS air ItemStack errors, one Apothic Enchanting stale data-map warning, one source-bound Just Dire Things early scan warning, 12 RuntimeDistCleaner errors, one Moonlight Fabric API error, and one Fabric overlay metadata error.
9. Run focused negative tests, all fixtures, full quest tests, static and runtime quest validation, a genuinely clean-world `BOOT_TIMEOUT=1200 ./tools/server-test.sh`, and `./tools/verify-pack.sh`. Require `SERVER BOOT: OK` and `VERIFY: ALL GREEN`.
10. Inspect the Packwiz index for leaks. Do not run `packwiz refresh` after the final commit.
11. Lithostitched client launch remains a manual release item. Do not claim client proof from dedicated-server verification.
