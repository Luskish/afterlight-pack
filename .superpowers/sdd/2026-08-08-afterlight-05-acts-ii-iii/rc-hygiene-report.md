# AFTERLIGHT Release-Candidate Hygiene Round 1 Report

Date: 2026-08-08
Branch: `dev`
Parent commit: `f5ce641`

## Result

RC hygiene review findings are repaired in the shared working tree. The final clean-world dedicated-server harness printed `SERVER BOOT: OK`. The authoritative current `latest.log` contains 16 fully classified ERROR records, zero FATAL records, and 39 exact known residual WARN records. Every repaired signature is zero. The final pack verifier printed `VERIFY: ALL GREEN`.

No push was performed. Lithostitched client launch remains a manual release item and is not claimed here.

## Corrected Root Causes

### Create Enchantment Industry

The first implementation replaced CEI's stale `enderio:xpjuice` key with `enderio:xp_juice`. That replacement is not registered by the installed EnderIO artifact. EnderCore 8.2.11-beta registers the source fluid as `enderio:fluid_xp_juice_still`, and EnderIO's own fluid tag uses the same ID.

The corrected override preserves the complete source data map and changes only the stale EnderIO key to `enderio:fluid_xp_juice_still`. The preserved value is `20`, and the preserved condition remains `neoforge:mod_loaded` for `enderio`. The clean boot has zero data-map errors for all three IDs:

- `enderio:xpjuice`
- `enderio:xp_juice`
- `enderio:fluid_xp_juice_still`

NeoForge data maps inspect resource stacks, so a higher loose resource alone cannot suppress the lower stale source. The one-file filter pack remains necessary. Its regexes are now anchored and its exact authenticated blocked resource set is only:

`create-enchantment-industry-2.5.1.jar:data/create_enchantment_industry/data_maps/fluid/unit/experience.json`

### IDAS

An authenticated scan of every `data/idas/worldgen/structure/*.json` resource found three structure-referenced biome tags absent from the installed IDAS jar:

- `idas:has_structure/bygredwood_biomes`
- `idas:has_structure/bygmahogany_biomes`
- `idas:has_structure/bopmahogany_biomes`

The source jar contains similarly named compatibility tags with spelling differences, but its structures reference the three IDs above. Exact optional empty definitions were added for those three IDs. The four source compatibility tags remain source-preserving, `replace = true`, and non-required. The final log contains zero IDAS missing-tag errors and zero IDAS missing-tag warnings.

No IDAS structure NBT was modified, copied, filtered, or redistributed. The two remaining air ItemStack errors are bound to authenticated source resource `data/idas/structure/underground_camp/underground_camp1.nbt`, SHA-256 `0d7ecc5059d0d94d8cde9621d5358df1a9b89bf7dc27e93fd564668064aceb8a`. Binary NBT parsing proves the exact two `id = minecraft:air` paths:

- `blocks/92/nbt/Filter`
- `blocks/95/nbt/Inventory/Compartments/0`

These are the empty Create saw filter and empty toolbox compartment already identified in the source audit.

### Just Dire Things

The reviewed source-level conclusion in `jdt-lifecycle-research.md` is adopted. The warning is an upstream early generic Supplementaries pancake candidate scan false positive, not a lost fuel-canister dispenser integration.

The installed bytecode flow is:

1. Supplementaries scans every registered item during an early `TagsUpdatedEvent`.
2. `ModBlockProperties$Topping.fromItem` asks Moonlight for a crafting remainder.
3. `FuelCanister.getCraftingRemainingItem` reaches the Just Dire Things server config before NeoForge has loaded that config.
4. `ModConfigSpec.ConfigValue.get` throws `IllegalStateException: Cannot get config value before config is loaded.`
5. Supplementaries catches that per-item exception and continues scanning.
6. A successful post-config scan still returns `Topping.NONE`, registers no custom behavior, and leaves vanilla dispenser ejection intact.

No compensation was added. Pancakes and Supplementaries dispenser behaviors remain enabled. No custom compatibility mod or KubeJS dispenser registration was added. The tracked Just Dire Things config remains because it supplies normal eventual values, not because it prevents the early warning.

The one allowed warning is exact:

- Level: `WARN`
- Logger: `Supplementaries/`
- Message: `Error white registering dispenser behavior for item justdirethings:fuel_canister: java.lang.IllegalStateException: Cannot get config value before config is loaded.`
- Count: `1`

Any changed item, logger, message, exception, count, artifact, config, or relevant class bytes fails. The allowance is bound to these SHA-256 values:

| Evidence | SHA-256 |
|---|---|
| Just Dire Things 1.5.7 jar | `6e5f7dd7091cc271fee66b0df62bde2250e8b52397b51dd911f79c088eb22d2f` |
| Supplementaries 3.8.8 jar | `cdd3d67b510f20f386690a2cbdbe63fd1ae9c8a620861738b6b80b1fa5c996f9` |
| Moonlight 3.3.2 jar | `e64737a18c934fe1fac2c4bf3ea1e997012d06ab67e2a06635def5968edb4474` |
| KubeJS 7.2 build 368 jar | `01767bb677a9c4a8f318717c4c21bca7e7ef80995603403a551068a0e064e740` |
| NeoForge 21.1.248 universal jar | `90a56f70425711b4e1a4b94ff0c2904ae9f6d74ca6478b3b2152ac794a07b8e5` |
| Patched Minecraft server jar | `26ca9c40d7e1681190b428583c38816852218e78df3f8bdb60a59a78503aec71` |
| Tracked and installed JDT config | `1585ad9a8fe3627f4858968de254f17dce69b73607940ca81e99d17a62289fe2` |
| Supplementaries `DispenserBehaviorsManager.class` | `55d5096f83b294f4c6830bcde99b8e3c3a0f9d18f101c60cccc7c88828c2e70a` |
| Supplementaries `ModBlockProperties$Topping.class` | `4637feea2f739e9169b3a615b705b0dfa2d65755c33e784bb00d1592caca041f` |
| Just Dire Things `FuelCanister.class` | `ff6b13094a4b1cacd6a3a0dc155aee7e6cb4fa4fe1d948549858b9e6b8e55b28` |

## Approved Scope Clarification

The implementation prompt explicitly approved the Oritech, Industrial Foregoing, and Cataclysm repairs. The brief now records those additions so future reviews have the complete scope.

- Oritech changes only the turbofuel ingredient serializer from `fluid_stack` to `neoforge:single`.
- Industrial Foregoing removes only the invalid Curios slot string `example`.
- Cataclysm adds only the two valid empty block tags `needs_black_steel_tool` and `needs_monstrosity_tool`.

## Config Provenance

The seven reviewed configs remain the only generated configs copied for this hygiene work. A separate clean server generation ran with those seven files absent. `tools/fixtures/rc-hygiene/generated-configs.json` records independent normalized SHA-256 fingerprints.

The fixture reverses every approved Quark and Alex's Mobs edit in memory, then requires byte-level equality to those generated fingerprints after removing only one final LF. This proves all non-approved generated bytes are preserved.

- Quark keeps Foxhound, Stoneling, and Toretoise modules enabled. Foxhound, lesser Foxhound, Stoneling, and Toretoise whitelist tags and biomes are empty.
- Alex's Mobs has `skreecherSpawnWeight = 0` and `skreecherSpawnRolls = 1`.
- The Just Dire Things config is retained for normal loaded values and is not described as warning prevention.

## Fixture Provenance

Every source jar fixture now starts from an exact `.pw.toml` path. Before any jar resource is read, the verifier checks:

1. Current `pack.toml` and `index.toml` coherence.
2. Every indexed file hash.
3. Exact metadata path, filename, side, and declared download hash.
4. Current installer `packwiz.json` pack and index provenance.
5. Installer metadata hash, linked artifact hash, enabled side, and cached path.
6. Installed artifact bytes against the declared hash.

Negative tests prove that manifest drift, stale installer provenance, metadata fragments, client-only sources, and modified jars fail. Standalone fixtures therefore cannot silently use a similarly named, modified, or stale jar.

## Filter ZIP Evidence

`tools/build-rc-hygiene-filter.py` deterministically rebuilds `kubejs/data/afterlight_rc_hygiene.zip` from `tools/rc_hygiene.py`.

- Archive SHA-256: `414a79bb450bdfb11fb18e51808c7baba2d87c0197d938ed82c7442b94746262`
- Member set: only `pack.mcmeta`
- Member timestamp: `1980-01-01 00:00:00`
- Compression: stored
- Unix mode: `100644`
- ZIP extra fields: empty
- Entry comment: empty
- Archive comment: empty
- Namespace regex: `^create_enchantment_industry$`
- Path regex: `^data_maps/fluid/unit/experience\.json$`

The test compares generated bytes with the checked archive, asserts the literal hash and normalized ZIP metadata, and scans every authenticated installed server artifact for the exact blocked resource set.

## Harness Hardening

`tools/server-test.sh` now:

- sources `tools/versions.env` and prepends `PATH_EXTRA` before Packwiz use;
- verifies the manifest before serving;
- records exact starting hashes for `pack.toml` and `index.toml` and rechecks them throughout the run;
- serves with `packwiz serve --refresh=false`;
- pins `packwiz-installer-bootstrap` v0.0.3 and verifies SHA-256 `a8fbb24dc604278e97f4688e82d3d91a318b98efc08d5dbfcbcbcab6443d116c` before execution;
- verifies installer provenance before boot;
- preserves the real server pipeline status in `afterlight-server-exit-status.txt`;
- accepts only graceful status `0`;
- reads only the current `server-test/logs/latest.log` as the authoritative log;
- requires one exact `DedicatedServer` Done record, the fresh nonce audit record, and all clean shutdown markers;
- parses every ERROR and FATAL record and rejects every unmatched record;
- runs the reliability probes and authenticated fixtures before printing success.

No server execution path uses `|| true`.

## Exact Known Residuals

The final clean log preserves these exact source-bound residual families:

| Level | Logger | Stable identity | Count |
|---|---|---|---:|
| WARN | `KubeJS Server/` | Exact 27 Kaleidoscope stockpot carrier recipe IDs | 27 |
| WARN | `KubeJS Server/` | `incendium:upgrade_elytra[minecraft:smithing_transform]` | 1 |
| WARN | `net.minecraft.world.item.crafting.RecipeManager/` | Exact nine Malum node-smelting recipe IDs | 9 |
| WARN | `net.neoforged.neoforge.registries.DataMapLoader/` | `apothic_enchanting:enchantment_info` | 1 |
| WARN | `Supplementaries/` | Exact JDT early pancake candidate scan message | 1 |
| ERROR | `net.neoforged.fml.common.asm.RuntimeDistCleaner/DISTXFORM` | Exact `ClientLevel` dedicated-server message | 12 |
| ERROR | `Moonlight/` | Exact Fabric API message plus bundled artifact context | 1 |
| ERROR | `net.minecraft.server.packs.AbstractPackResources/` | Fabric overlay message plus Tectonic and stack context | 1 |
| ERROR | `net.minecraft.world.item.ItemStack/` | Exact authenticated IDAS underground-camp air slots | 2 |

Totals are 39 known residual WARN records and 16 allowed ERROR records. FATAL count is zero. Same-count source substitution fails because logger, message, resource or stack context, source artifacts, and count are all checked.

## Test-Led Evidence

The reliability suite was added before the verifier and harness repairs. Its first run reported 13 tests with 12 import errors and one harness assertion failure. After implementation, the expanded suite contains 18 negative and integrity probes, all passing.

The first post-repair clean harness reached `BOOT ORACLE: OK errors=16 known-warnings=39`, then failed because the filter fixture attempted to authenticate installer entries marked `onlyOtherSide` for disabled client artifacts. The fixture was narrowed to installer-enabled server artifacts. A focused rerun passed, followed by a new clean-world harness run that completed with `SERVER BOOT: OK`.

## Final Verification Evidence

- Python compilation for verifier, generator, and both hygiene suites: passed.
- Shell syntax for `tools/server-test.sh`: passed.
- False-green and reliability probes: `Ran 18 tests`, `OK`.
- Authenticated config, override, metadata, JDT, filter, and boot fixtures: `Ran 22 tests`, `OK`.
- Full quest tests: `Ran 47 tests`, `OK`.
- Static quest validation: `VALIDATE QUESTS: OK (41 chapters, 283 quests, 307 tasks, 393 rewards)`.
- Clean command: `BOOT_TIMEOUT=1200 ./tools/server-test.sh`.
- Dedicated server marker: `Done (27.969s)! For help, type "help"` from logger `net.minecraft.server.dedicated.DedicatedServer/`.
- Fresh nonce: `1786217903-94191-1220`.
- Runtime item audit: `OK 4e1670d897a02c35bfae380d1863597f46d8307c3c375e69f6454ce3204a4511 219 1786217903-94191-1220`.
- Preserved server exit status: `0`.
- Shutdown markers: `Stopping server`, `Saving players`, `Saving worlds`, and `ThreadedAnvilChunkStorage: All dimensions are saved`.
- Boot oracle: `BOOT ORACLE: OK errors=16 known-warnings=39`.
- Clean harness result: `SERVER BOOT: OK`.
- Runtime quest validation: `VALIDATE QUESTS: OK (41 chapters, 283 quests, 307 tasks, 393 rewards)`.
- Packwiz refresh idempotence: `OK: refresh idempotent`.
- Pack verifier result: `VERIFY: ALL GREEN`.
- Final `pack.toml` SHA-256: `20c5522286afba71b5aa7da77671c4bf71a8a562e801a79909f4e3f8b59fb15c`.
- Final `index.toml` SHA-256: `3a5fc2cfd7102ede80a6b7c59da73e39008d6b3d8fe1d822e515e4dce2b64710`.

## Concerns and Manual Items

- Lithostitched is proven on the dedicated server and remains `side = both`, but no client launch was performed. Client launch remains an explicit manual release item.
- The exact upstream residuals in the table remain visible and source-bound. They are not masked or described as repairs.
- No multiplayer acceptance run, CI run, push, or public artifact publication occurred in this work.
- Any update to Just Dire Things, Supplementaries, Moonlight, KubeJS, NeoForge, or the patched server invalidates the JDT evidence binding and requires reinvestigation.
