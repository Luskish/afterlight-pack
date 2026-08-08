# AFTERLIGHT Release-Candidate Hygiene Round 2 Report

Date: 2026-08-08
Branch: `dev`
Parent commit: `47f1aed`

## Result

RC hygiene reliability findings are repaired in the shared working tree. The final architecture removes the generic IDAS allowance, eliminates all generic ItemStack air errors, and consumes all 12 RuntimeDistCleaner records through a dedicated Sable source verifier. The authoritative current `latest.log` contains 14 fully classified ERROR records, zero FATAL records, and 39 exact known residual WARN records. Every repaired signature is zero. The final clean-world harness printed `SERVER BOOT: OK`, and the final pack verifier printed `VERIFY: ALL GREEN`.

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

The prior count-two ItemStack allowance could not prove runtime source attribution. The generic records had no structure ID, path, block position, or stack. It was removed instead of broadened.

The production repair is the original MIT-licensed NeoForge mod `afterlight_idas_compat` version `0.1.0+1.21.1`:

| Evidence | Value |
|---|---|
| Public source | `https://github.com/Luskish/afterlight-idas-compat` |
| Source commit | `5afbdcb` |
| Immutable tag and release | `v0.1.0`, `https://github.com/Luskish/afterlight-idas-compat/releases/tag/v0.1.0` |
| Release asset SHA-256 | `458bbaeb5d93923d24b18d69ed7f60dbf3bab9854d50a02671f6ecb7a0338b1b` |
| Release asset SHA-512 | `26a490e6f4e2bde870ada10325dc8f7cad2774b96fa1c35e11a709010de50d126e0ffb33853a8b5f8fcfa1ced28e2d377b7603ddae056c634e959b760be82c54` |
| Packwiz side | `both` |
| Authenticated IDAS artifact SHA-256 | `7f5031dd90ae0b32d7fe5c6c47c877cac1eb95a178bc78d196cb24c17ce82522` |

The mod injects only at `StructureTemplateManager.loadFromResource(ResourceLocation)` return. It retains the source ID and traverses parsed block and entity NBT in memory. Mutation is limited to the `idas` namespace and direct compounds with `id = minecraft:air`, numeric `count`, and exactly one of `{count,id}`, `{count,id,tag}`, or `{ForgeCaps,count,id}`. A matching compound field is removed. A matching list entry becomes an empty `CompoundTag`, preserving list cardinality. Artifact mismatch or an unreviewed air shape performs no mutation, emits a dedicated ERROR, and fails the release oracle.

The authenticated fixture scans all 259 IDAS structure NBT resources without checking any NBT into either repository. It proves 100 affected templates and 1,684 exact candidates, with key-set counts 1,444, 214, and 26. Parent placement is 1,570 compound fields and 114 list entries. Pure transformation, list preservation, namespace exclusion, deterministic digest, exhaustive inventory, and real `StructureTemplateManager#get` mixin integration use original synthetic fixtures. Dedicated-server archive checks reject client references, nested jars, IDAS NBT, and `data/idas` resources.

No IDAS structure NBT was modified, copied, filtered, redistributed, or committed. The release asset is referenced only through direct-download metadata and remains out of Git. The final fixed-seed boot requires the exact READY record and this exact ordered SANITIZED sequence:

| Template | Replacements | Digest |
|---|---:|---|
| `idas:underground_camp/underground_camp_deep1` | 1 | `79fe677f9e4c30ea95806383468977e42b46e79dd2f47a7748d089ceacec29b5` |
| `idas:underground_camp/underground_camp1` | 2 | `772fe478261727163979ddd04ae3d69220c35b02c09c7046974f96d99d5b0b06` |
| `idas:tudor_pub/tudor_pub` | 8 | `9e9afaf0cdd2470ef45319d2f18f7205d1939a3165f57daa6c2927f9633fd9d1` |
| `idas:tudor_pub/tudor_pub_bottom` | 9 | `4dfd6abd605d244e35aa8be0235746a2e48cbf3e9d5e133553810750c2af0cc0` |

The READY record authenticates IDAS version `1.13.7+1.21.1-neoforge`, the exact artifact hash, 1,684 known compounds, and 100 known templates. The final logs contain zero generic ItemStack air errors.

### Sable RuntimeDistCleaner

All 12 RuntimeDistCleaner records are produced by three Sable common `@Pseudo` mixins that directly target both `ServerLevel` and `ClientLevel`. They are no longer accepted by `project_error_allowances()`.

The dedicated verifier authenticates current Packwiz and installer provenance, Sable artifact SHA-256 `da6c3b66238586603d1dcaa2afb012d36815fbce0a2d5938fbb2936701d42279`, `sable.mixins.json` SHA-256 `02dd86d2bd0ed6bef4841b1ae4ac8579edeb33fe0134f2060191b49102c4878d`, loader SHA-256 `ba406038d0ce8242391bb23b9974648748d217b67332c0db620fcabf50edbc37`, and Mixin runtime SHA-256 `1d45cfe3ae4a2eab38dc74276803748cf799088986260d6d912e50ddb35d15c5`.

| Sable common mixin | Index | Class SHA-256 |
|---|---:|---|
| `entity.entity_aabb_lookup.LevelsMixin` | 40 | `0b6d6e637410852d131f2178c53a454bdd506555e509c5aea2ce3127d01070c0` |
| `plot.LevelsMixin` | 100 | `660410f918f5676d49e734028cb2e74967a622746cc7c7f22ff805016c476bda` |
| `water_occlusion.LevelsMixin` | 132 | `f5cecf91372f08ef0b5b9bc36f609b6f2df726dc3612731d9e0a5a56460b647c` |

The exhaustive final scan covers 158 enabled metadata records, 157 unique top-level artifacts, 305 archive scopes, 255 mixin configs, and 2,258 common mixin entries. Ten common mixins directly target `ClientLevel`; only the three authenticated Sable classes are common `@Pseudo` candidates. The research report's earlier 2,221 aggregate was corrected by an independent full rescan to 2,256 entries before this compatibility mod. The compatibility mod contributes two common mixins, producing the final exact count of 2,258.

The runtime verifier binds the prepare phase to the three exact `Skipping virtual target` records and stack hash `87df768dd4921f00d5b8c13e02beeb365885f0708d0216a58dfc961ba443192d`. It binds the paired validation phases to named P1, P2, and P3 windows and stack hashes `40c05a51c8a02d94692457d73ec3414e456a22dccdc04cbc59d308e8abd29f87` and `c1e2e1e8d01e33eebbc20cd18f868bbe28447ccecaa6958f3a527377750320ec`. The final three records require immediately adjacent Sable `Mixing` application lines for `ServerLevel`. Latest and debug logs must share boot markers, nonce, shutdown markers, and the exact ordered ERROR/FATAL projection. Any source substitution, stack mutation, window relocation, candidate-set change, logger change, message change, exception change, or count change fails.

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
| ERROR | `net.neoforged.fml.common.asm.RuntimeDistCleaner/DISTXFORM` | Dedicated Sable source, stack, phase, and window proof | 12 |
| ERROR | `Moonlight/` | Exact Fabric API message plus bundled artifact context | 1 |
| ERROR | `net.minecraft.server.packs.AbstractPackResources/` | Fabric overlay message plus Tectonic and stack context | 1 |

Totals are 39 known residual WARN records and 14 allowed ERROR records. FATAL count is zero. IDAS contributes no residual ERROR. Same-count source substitution fails because logger, message, source or stack context, source artifacts, phase, and count are all checked.

## Test-Led Evidence

The new project-allowance probes first proved that the old count-only entries could consume relocated RuntimeDistCleaner and ItemStack records. Additional red probes moved a Sable record between named windows, changed prepare and application source lines, changed stack source, injected a fourth common `@Pseudo` `ClientLevel` candidate, substituted debug-log boot identity, changed the compatibility audit digest at the same count, and reintroduced a generic air error. The repaired suite rejects every probe.

The first clean compatibility boot reached `BOOT ORACLE: OK errors=14 known-warnings=39`, then correctly failed the fixture because the initial expectation allowed one sanitized template while the fixed seed loaded four. Runtime evidence identified the exact ordered four-template sequence. The oracle and fixture now require all four exact messages, replacement counts, and digests rather than broadening the count.

The next clean harness passed, but separate runtime quest validation rejected the old generated item-audit digest. Root-cause tracing showed that `quest_item_audit_digest()` includes every mod metadata file in its registry-input fingerprint, so adding the compatibility metadata correctly changed the expected digest. `tools/build-quests.py` changed only the generated audit digest from `4e1670d897a02c35bfae380d1863597f46d8307c3c375e69f6454ce3204a4511` to `d409acfd46bd377e637604cd522582ca4b71456751938cd6dc43fef027d32a8c`. No quest SNBT changed. Packwiz was refreshed once for that indexed generated file, the index leak scan passed, and a replacement genuinely clean harness plus runtime validation passed.

## Final Verification Evidence

- Python compilation for verifier, generator, and both hygiene suites: passed.
- Shell syntax for `tools/server-test.sh`: passed.
- Focused boot-oracle negative probes: `Ran 20 tests`, `OK`.
- Full reliability and false-green suite: `Ran 34 tests`, `OK`.
- Authenticated config, override, metadata, Sable, IDAS compatibility, JDT, filter, and boot fixtures: `Ran 24 tests`, `OK`.
- Compatibility source test and build command: `gradle clean test build verifyDedicatedServerSafety --rerun-tasks --no-daemon`, `BUILD SUCCESSFUL`, 12 tasks executed.
- Compatibility build runtime: Temurin Java `21.0.12`; official Gradle `9.2.1` distribution SHA-256 `72f44c9f8ebcb1af43838f45ee5c4aa9c5444898b3468ab3f4af7b6076c5bc3f`.
- Compatibility source CI: successful for source commit `5afbdcb` on `main` and immutable tag `v0.1.0`.
- Full quest tests: `Ran 47 tests`, `OK`.
- Static quest validation: `VALIDATE QUESTS: OK (41 chapters, 283 quests, 307 tasks, 393 rewards)`.
- Clean command: `BOOT_TIMEOUT=1200 ./tools/server-test.sh`.
- Dedicated server marker: `Done (28.587s)! For help, type "help"` from logger `net.minecraft.server.dedicated.DedicatedServer/`.
- Fresh nonce: `1786224585-35451-9436`.
- Runtime item audit: `OK d409acfd46bd377e637604cd522582ca4b71456751938cd6dc43fef027d32a8c 219 1786224585-35451-9436`.
- Preserved server exit status: `0`.
- Shutdown markers: `Stopping server`, `Saving players`, `Saving worlds`, and `ThreadedAnvilChunkStorage: All dimensions are saved`.
- Boot oracle: `BOOT ORACLE: OK errors=14 known-warnings=39`.
- Clean harness result: `SERVER BOOT: OK`.
- Runtime quest validation: `VALIDATE QUESTS: OK (41 chapters, 283 quests, 307 tasks, 393 rewards)`.
- Packwiz refresh idempotence: `OK: refresh idempotent`.
- Pack verifier result: `VERIFY: ALL GREEN`.
- Authoritative `latest.log` SHA-256: `b3e95753212939182ff2e2f56b93037bfc0c8faa6f610bf02911b3d339bbae4c`.
- Same-run `debug.log` SHA-256: `1d12a7b4845dc4e4f06ecf05d8b2f4cc55fc2301b9e93223f76ea485140f89cd`.
- Final `pack.toml` SHA-256: `9eb7905a8be75748d4e7919c02c6906d91f22f6d984632652fff7b22524d405c`.
- Final `index.toml` SHA-256: `9539fcf54efd250dd3965c74e9d5f917191e5bf82bef8ebf7a425c1ea8d5ff9e`.
- Index leak scan: no server-test, research, Git, source-tree, JAR, or NBT entries.

## Concerns and Manual Items

- Lithostitched is proven on the dedicated server and remains `side = both`, but no client launch was performed. Client launch remains an explicit manual release item.
- The exact upstream residuals in the table remain visible and source-bound. They are not masked or described as repairs.
- No multiplayer acceptance run or AFTERLIGHT push occurred in this work. The compatibility source and immutable release asset were published publicly as required.
- Any update to Just Dire Things, Supplementaries, Moonlight, KubeJS, NeoForge, or the patched server invalidates the JDT evidence binding and requires reinvestigation.
- Any IDAS or compatibility artifact update requires a new authenticated inventory, compatibility release, and boot-oracle binding.
