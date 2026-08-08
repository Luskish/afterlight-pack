# Modpack Content, Configuration, And Testing

Use this reference for files that Packwiz distributes but does not semantically understand: mod configuration, KubeJS, datapacks, resource packs, quests, world templates, and server/runtime settings.

## Evidence Levels

Keep these categories distinct:

- **Loader contract:** behavior documented by Forge/NeoForge/Minecraft.
- **Mod contract:** behavior documented or implemented by one mod; do not generalize it to the loader.
- **Pack convention:** a practical repository layout or release practice recommended here.
- **Observed behavior:** generated output from the exact tested version; preserve a test and re-check on upgrades.

## Configuration Locations

### Forge 1.20.x

Forge documents three configuration types:

| Type | Physical client | Dedicated server | Synchronized |
|---|---|---|---|
| CLIENT | `.minecraft/config` | not loaded | no |
| COMMON | `.minecraft/config` | `<server>/config` | no |
| SERVER | `<world>/serverconfig` | `<server>/world/serverconfig` | yes |

Source: https://docs.minecraftforge.net/en/1.20.x/misc/config/

A common config is not automatically authoritative or synchronized merely because both sides load a file with the same name. If a common value affects registries or networking, client/server divergence may break the pack.

### NeoForge

NeoForge documentation includes STARTUP, CLIENT, COMMON, and SERVER types. Current docs and versioned docs differ in details, so use the page and source branch for the target Minecraft line.

- Current: https://docs.neoforged.net/docs/misc/config/
- Minecraft 1.21/1.21.1: https://docs.neoforged.net/docs/1.21.1/misc/config/

NeoForge warns that unsynchronized startup settings should not enable/disable content in ways that can desynchronize clients and servers. In current NeoForge, a `SERVER` config in global `config/` is the base; a same-named file under `<world>/serverconfig/` overrides it for that world and is synchronized to clients. Missing files can be seeded from `defaultconfigs/`. Verify this against the exact NeoForge branch because older Forge/NeoForge lifecycles differ.

### Fabric

Fabric Loader does not impose one universal mod configuration format/location. Individual mods may use Auto Config, Cloth Config, JSON, JSON5, TOML, properties, or custom storage. Read the exact mod's documentation/source and test server/client behavior. Do not infer semantics solely from a `config/` path.

## `config/`, `serverconfig/`, And `defaultconfigs/`

Use these pack-authoring rules:

- Put intentionally shipped instance/server configuration in `config/`.
- Treat `<world>/serverconfig/` as existing-world state unless the pack intentionally ships a world template.
- Forge 1.20.x and current NeoForge use `defaultconfigs/` as a first-creation seed for missing config files, not as an ongoing synchronization layer. Verify the exact target branch and filename.
- To change an existing Forge world's authoritative server config or an existing NeoForge world override, migrate that world's `serverconfig/` explicitly and back it up first. On current NeoForge, a world without an override continues to use the global base file.
- Test a newly created world and an upgraded copied world separately.

A safe capture workflow:

1. Launch a clean disposable instance with the exact mod set.
2. Let mods generate defaults.
3. Make one intentional setting change.
4. Diff before/after.
5. Keep the minimum needed file or keys if the format permits stable partial files.
6. Repeat on a clean dedicated server.
7. Verify client join and authoritative behavior.

Generated comments and ordering may churn between mod versions. Avoid broad formatting rewrites unless the mod's parser is known to preserve semantics.

## Runtime Files To Exclude

Normally exclude:

- `logs/`, `crash-reports/`, `debug/`, profiler output;
- worlds, region data, player data, stats, advancements, backups;
- launcher metadata, account/authentication state, cached downloads;
- `options.txt`, keybindings, screenshots, local server lists unless intentionally part of distribution;
- map/minimap/waypoint data and chat logs;
- generated recipe-viewer caches, KubeJS caches, ProbeJS output not intentionally used as source;
- secrets, API keys, private endpoints, and service credentials.

Some generated files become authored inputs only after deliberate review—for example a quest book, a configured world preset, or a ProbeJS typing snapshot used by editors. Document why each exception is shipped.

## KubeJS Placement And Lifecycle

Load the `kubejs-modding` skill before substantial scripting.

| Path | Typical purpose | Reload expectation |
|---|---|---|
| `kubejs/startup_scripts/` | registries, custom items/blocks/fluids, startup definitions | full restart |
| `kubejs/server_scripts/` | recipes, tags, loot, commands, server/player/world logic | `/reload` for supported content |
| `kubejs/client_scripts/` | tooltips, recipe-viewer/UI/client events | client resource reload when supported; otherwise restart |
| `kubejs/data/` | raw datapack data | datapack reload or restart depending on registry |
| `kubejs/assets/` | raw resource-pack assets | client resource reload or restart |

Exact event names and APIs depend on KubeJS, Minecraft, Rhino, loader, and addons. Generate and use ProbeJS typings for the current pack. Node.js APIs and npm modules are not available in normal Rhino scripts.

Progression-safe recipe editing:

- remove by stable recipe ID when possible;
- assign an explicit ID to every important replacement/custom recipe;
- use tags for intentional interchangeability;
- avoid broad output/mod removals without a generated before/after recipe inventory;
- test crafting/machine processing, not only recipe-viewer visibility;
- verify scripts on a dedicated server to catch client-class references.

## Datapacks

A Java Edition datapack is a directory or ZIP with `pack.mcmeta` and namespaced content. It can define recipes, tags, loot tables, advancements, functions, structures, and version-dependent dynamic registries/world generation.

Useful reference: https://minecraft.wiki/w/Data_pack

Rules:

- Use a pack-owned namespace; use `minecraft` only for deliberate vanilla override behavior.
- Preserve IDs after release. Renames can break advancements, recipes, functions, quest references, and existing worlds.
- Pack load order controls overriding. Tag files normally merge unless replacement semantics are requested.
- `/reload` reloads many data-driven systems, but dynamic-registry/worldgen changes generally require a world/server restart and can change world compatibility.
- Match `pack_format` to the exact Minecraft version. Pack format numbers change frequently.
- Treat malformed data as a release blocker; a single invalid file can make world loading fail or enter safe mode.
- A loose datapack under one world's `datapacks/` is world state. Do not assume a loader automatically installs an arbitrary loose datapack into every new world; use a documented global-pack mechanism, KubeJS's built-in data layer, or a small content mod when the pack requires global application.

When KubeJS generates equivalent datapack content, decide one owner. Do not define the same recipe/tag/loot ID in both raw JSON and scripts unless the override order is intentional and tested.

## Resource Packs

Use resource packs for pack-owned language, models, textures, sounds, fonts, splash/UI material, and other client resources. Keep them in a separate directory or external `.pw.toml` when that makes licensing and optionality clearer.

- Match resource-pack format to the exact Minecraft version.
- Keep namespaces and case exact; Linux dedicated/client environments expose case mistakes hidden on case-insensitive filesystems.
- Verify missing textures/models and language keys in logs and in-game.
- Optimize large textures/audio and confirm redistribution rights.
- Test with optional performance/rendering mods enabled and disabled if both combinations are supported.

## Quest And Progression Data

Quest systems are mod-specific. FTB Quests 1.20.1 releases commonly store definitions as SNBT under `config/ftbquests/quests` while team progress lives in the world's `ftbquests/`; current development has moved serialization toward JSON5. Other systems use JSON, KubeJS, databases, datapacks, or world data. Use the exact mod version's documentation/source and inspect a generated minimal quest book before editing by hand.

Treat IDs as public interfaces:

- never regenerate every chapter/quest/task/reward ID during formatting;
- preserve dependencies and hidden/optional semantics;
- test fresh profile, existing profile, team/shared progression, and dedicated server;
- verify repeatable rewards, choice rewards, commands, loot tables, and stage unlocks cannot be exploited or deadlock;
- ensure recipe and quest changes ship atomically in one release.

When possible, build a progression graph check that catches missing references and cycles. It does not replace gameplay testing.

## World Presets And Templates

Worldgen and presets are high-risk because their data may be stored in dynamic registries and `level.dat`.

- Decide whether the pack supports arbitrary worlds, only new worlds, or a distributed template save.
- Prefer a datapack/world preset to bundling a save when it can reproduce the intended start.
- If shipping a template world, scrub player UUIDs/data, inventories, advancements, server addresses, logs, maps, and accidental chunks.
- Test deterministic spawn/start conditions on client and dedicated server.
- Document whether upgrading can create chunk borders, missing biomes/dimensions, or registry remap failures.
- Never test destructive world migrations against the only copy.

## Client/Server Separation

Use both project documentation and real physical-side tests.

A dedicated server smoke test catches:

- client-only classes loaded by shared mods or KubeJS scripts;
- wrong Packwiz side metadata;
- missing server dependencies;
- configs that exist only in a client instance;
- datapack/registry failures;
- authentication/network/protocol mismatch.

A client joining the dedicated server catches:

- registry and channel mismatch;
- shared config divergence;
- server-required mods accidentally marked server-only;
- optional-mod combinations that alter protocol/content;
- missing resource/quest synchronization.

Do not substitute integrated singleplayer for either test.

## Reproducible Test Matrix

At minimum:

| Scenario | Purpose |
|---|---|
| Clean client install and title-screen launch | artifact/import, loader, client mods, resources |
| New singleplayer world | data, configs, scripts, world preset, recipes |
| Clean dedicated server start | physical-side safety, server configs, datapack load |
| Released client joins released server | protocol, registries, sides, synchronized behavior |
| Existing-world copy upgraded | migration and world compatibility |
| Optional feature combinations | only combinations promised to users |

Capture:

- Java runtime and arguments;
- Minecraft, loader, Packwiz, KubeJS, and pack versions;
- exact Git commit/artifact checksum;
- startup completion marker;
- errors/warnings from normal and KubeJS logs;
- test world provenance and backup location.

Use explicit timeouts in CI. A server process that stays alive without reaching its ready marker is not a passed smoke test.

## Git And Review

A useful `.gitignore` excludes build/export artifacts and runtime state. `.packwizignore` independently controls installation. A file may be committed but excluded from the pack, such as contributor documentation or CI scripts.

Review each change by semantic class:

- `pack.toml`/`.pw.toml`: exact versions, sources, hashes, sides, optional flags;
- `index.toml`: expected path/hash churn only;
- config: intentional settings, no machine/user data;
- KubeJS/data: stable IDs, lifecycle, server safety;
- quests: stable IDs and valid dependency graph;
- assets: namespace/case/license/size;
- world data: only if explicitly intended and scrubbed.

## Licensing And Provenance

For every included third-party artifact record:

- project and source URL;
- exact file/version ID and hash;
- loader/Minecraft version;
- required/optional dependencies;
- Packwiz side;
- license or explicit permission;
- whether distribution is by original-host download metadata or bundled override;
- local patches and their license/provenance.

Modrinth/CurseForge project presence makes discovery and platform export easier but does not automatically license copying source, configs, scripts, artwork, or binaries outside permitted platform flows. Check current platform policies before each public release.

Minecraft Usage Guidelines: https://www.minecraft.net/en-us/usage-guidelines

CurseForge non-CurseForge mod policy: https://support.curseforge.com/en/support/solutions/articles/9000197913-non-curseforge-mods

## Release Gate

Do not publish until:

- Packwiz refresh is deterministic and the worktree is clean;
- every supported export succeeds and its archive is inspected;
- clean client and dedicated server launch successfully;
- released client joins released server;
- changed gameplay is exercised;
- new-world and existing-world expectations are documented/tested;
- no secrets or personal/runtime data are present;
- redistribution/provenance inventory is complete;
- version and release notes describe incompatible config/world/progression changes;
- artifacts and checksums are retained.
