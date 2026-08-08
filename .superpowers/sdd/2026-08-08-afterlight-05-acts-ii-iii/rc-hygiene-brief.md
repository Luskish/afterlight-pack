# RC Hygiene Brief

Run this after Plan 05 Task 6 and before Plan 05 final verification. The release gate must distinguish repaired defects from source-bound upstream residuals and must fail closed when logs, artifacts, or process state change.

## Approved Scope

The controller explicitly approved the following additions to the original hygiene scope:

1. Oritech turbofuel fluid ingredient serializer repair.
2. Industrial Foregoing Curios entity-slot repair.
3. Cataclysm empty tool-requirement block tags.
4. A dedicated Sable RuntimeDistCleaner provenance verifier.
5. An original IDAS in-memory structure compatibility mod.

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
15. Never modify, copy, filter, or redistribute IDAS structure NBT. Eliminate the generic `minecraft:air` ItemStack errors with the original MIT-licensed `afterlight_idas_compat` mod version `0.1.1+1.21.1`, source commit `02c0254513afdcaff65af0c50f8339013f0cc045`, and annotated tag `v0.1.1`. Install the immutable release asset through exact direct-download Packwiz metadata with side `both`, SHA-256 `086ac4a56becba5ec2e7708855f09eef74613300f235601c18e033a35adac324`, and SHA-512 `af39e726630f7fbfd2465cdb0dc6001e3ab7ea3f9180192e999530a8f9ed4afb35410b7707eea4d3d967ae68314229418d0ee7d18ce5dfb8cf0e946ae12beb43`.
16. Authenticate IDAS version `1.13.7+1.21.1-neoforge` and artifact SHA-256 `7f5031dd90ae0b32d7fe5c6c47c877cac1eb95a178bc78d196cb24c17ce82522`. Inject only at `StructureTemplateManager.loadFromResource(ResourceLocation)` return and retain the selected source ID and bytes. Sanitize only direct compounds under the `idas` namespace with `id = minecraft:air`, numeric `count`, and one of the three exact reviewed key sets.
17. Approve only the four fixed-seed loaded template IDs. Before any mutation, require the exact template ID, selected loaded resource SHA-256, candidate count, and pre-mutation audit digest. A source override, missing candidate, same-count relocation, candidate in an unapproved template, or unreviewed air shape must perform no mutation, emit a dedicated ERROR, and fail the release gate. Each resource load is evaluated fresh, with no second-pass exception.
18. Remove matching compound-field entries. Replace matching list entries with an empty `CompoundTag` so list cardinality is preserved. Require exact positive READY and ordered per-template SANITIZED audits, zero generic ItemStack air errors, and no written or embedded IDAS NBT.
19. Pin every compatibility GitHub Action to a full commit SHA, use exact Gradle `9.2.1`, and enforce dependency locking plus Gradle verification metadata without committing a wrapper JAR. The released JAR must embed the exact source commit, reviewed template allowlist, and negative-test source hashes.
20. Pin Terralith to Modrinth version `IY93YaEe`, version `2.6.2`, filename `Terralith_1.21.1_v2.6.2_Neoforge.jar`, SHA-512 `35298f1682567f63dc16658b04cee5498b30819f1c05f9712b4480d7f5eb17059db3b13ab14f81a05fe257149d11ced2cce2030d3727c1747edd8657c53e2a85`, and side `both`. Set Lithostitched side to `both`.

The exact v0.1.1 loaded-resource approvals are:

| Template | Selected resource SHA-256 | Candidates | Audit digest |
|---|---|---:|---|
| `idas:underground_camp/underground_camp_deep1` | `652e2bbac736f171c102342547538430a2f5327de38319503fc4bd323e7ee7da` | 1 | `79fe677f9e4c30ea95806383468977e42b46e79dd2f47a7748d089ceacec29b5` |
| `idas:underground_camp/underground_camp1` | `0d7ecc5059d0d94d8cde9621d5358df1a9b89bf7dc27e93fd564668064aceb8a` | 2 | `772fe478261727163979ddd04ae3d69220c35b02c09c7046974f96d99d5b0b06` |
| `idas:tudor_pub/tudor_pub` | `36e2bbc9ae46052b84d97819a50a65c1233064af4708a724e94ebaffdb424c3f` | 8 | `9e9afaf0cdd2470ef45319d2f18f7205d1939a3165f57daa6c2927f9633fd9d1` |
| `idas:tudor_pub/tudor_pub_bottom` | `67a0d8447e8ec42c1eef447111bc3d40bd71e089395fa5472ae754ed88052bd2` | 9 | `4dfd6abd605d244e35aa8be0235746a2e48cbf3e9d5e133553810750c2af0cc0` |

## Just Dire Things Determination

The Just Dire Things warning is an upstream false positive from Supplementaries' early generic pancake candidate scan. The initial scan reaches `FuelCanister.getCraftingRemainingItem` before NeoForge loads server configs. A successful post-config scan still classifies the fuel canister as `Topping.NONE`, registers no custom behavior, and leaves vanilla dispenser ejection intact.

Do not add compensation, disable pancakes, disable Supplementaries dispenser behavior, or ship a custom compatibility mod. Allow exactly one full-message WARN from logger `Supplementaries` for `justdirethings:fuel_canister` and the exact `IllegalStateException`. Bind that allowance to the reviewed Just Dire Things, Supplementaries, Moonlight, KubeJS, NeoForge, patched server, config, and relevant class hashes. Any changed item, logger, message, exception, artifact, or count must fail.

## Verification Requirements

1. Resolve every source fixture from its exact `.pw.toml` path. Verify the current pack and index, declared filename, side, download hash, installer provenance, installed path, and installed bytes before reading jar resources.
2. Compare every override with its authenticated source resource and assert only approved differences.
3. Rebuild the filter ZIP deterministically. Assert byte identity, SHA-256, fixed timestamp, mode, compression, empty metadata fields, anchored regexes, and the exact blocked resource set across authenticated server artifacts.
4. Pin `packwiz-installer-bootstrap` v0.0.3 and verify SHA-256 `a8fbb24dc604278e97f4688e82d3d91a318b98efc08d5dbfcbcbcab6443d116c` before execution.
5. Run `packwiz serve --refresh=false`. Verify manifest and index coherence before install and fail if `pack.toml` or `index.toml` changes at any phase.
6. Strip ANSI and parse every log line with a strict anchored grammar. Reject any line that appears to declare ERROR or FATAL but is not a valid header. Preserve exact thread, logger, level, message, and every continuation line in canonical normalized records. Normalize only enumerated volatile fields.
7. Compare exact full-record fingerprints and cardinalities between current `latest.log` and `debug.log` for every accepted ERROR, FATAL, and WARN record. Any added cause, frame, thread change, logger change, continuation mutation, same-count substitution, or cross-log disagreement must fail. Require zero repaired signatures, zero IDAS missing-tag records, and zero generic ItemStack air errors.
8. Verify all 12 RuntimeDistCleaner records through a dedicated Sable verifier, not generic allowance matching. Authenticate Sable, loader, and Mixin runtime artifacts, exact mixin JSON and class hashes, normalized stack hashes, named P1 through P3 windows, application adjacency, and same-run latest/debug projection. Key every mixin config by authenticated artifact plus resource path, process every archive scope, parse both `@Mixin.value` and `@Mixin.targets`, and reject malformed declarations. Require the exact real corpus of 305 archive scopes, 261 mixin configs, 2,286 common mixins, and three annotation-derived common `ClientLevel` targets, all three the authenticated Sable `@Pseudo` candidates.
9. Derive the quest audit digest from the indexed generated KubeJS script. Preserve server process status and require graceful status `0`. Enforce an explicit ordered state machine with exact cardinalities for one READY, four SANITIZED records, one anchored `DedicatedServer` Done, the fresh nonce audit, FTB load, stopping, player save, world save, and final clean save. Reordered, missing, duplicate, stale, or post-shutdown boot markers must fail.
10. Preserve exact known residuals: 27 Kaleidoscope carrier warnings, one Incendium smithing fallback, nine EnderIO Malum inheritance warnings, one Apothic Enchanting stale data-map warning, one source-bound Just Dire Things early scan warning, 12 dedicated Sable RuntimeDistCleaner errors, one Moonlight Fabric API error, and one Fabric overlay metadata error.
11. Run focused negative tests, all fixtures, compatibility Gradle tests and dedicated-server safety checks, full quest tests, static and runtime quest validation, a genuinely clean-world `BOOT_TIMEOUT=1200 ./tools/server-test.sh`, and `./tools/verify-pack.sh`. Require `SERVER BOOT: OK` and `VERIFY: ALL GREEN`.
12. Inspect the Packwiz index for leaks. Do not run `packwiz refresh` after the final commit.
13. Lithostitched client launch remains a manual release item. Do not claim client proof from dedicated-server verification.
