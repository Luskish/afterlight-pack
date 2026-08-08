---
name: minecraft-modpack-authoring
description: Author, maintain, test, and distribute reproducible Minecraft Java modpacks with Packwiz, KubeJS, loader and mod configuration, datapacks, resource packs, quests, and dedicated-server validation. Use when creating a pack, changing its mod set or progression, classifying client/server files, preparing exports, or debugging pack configuration.
license: MIT
compatibility: Minecraft Java Edition modpacks using Packwiz with Fabric, Quilt, Forge, or NeoForge; exact commands, file formats, KubeJS APIs, loader behavior, and Java requirements are version-sensitive.
metadata:
  version: "1.0.0"
---

# Minecraft Modpack Authoring

Use this skill to treat a modpack as a reproducible software project rather than a copied game instance. Packwiz owns the manifest and downloaded-file metadata; Git owns reviewable source; KubeJS, configuration files, datapacks, resource packs, and quest data define pack behavior; client and dedicated-server launches prove that the result works.

For non-trivial KubeJS implementation or review, also load the companion `kubejs-modding` skill. This skill covers where KubeJS fits in the whole pack workflow; the companion contains the detailed script lifecycle and API guidance.

## First Checks

Before editing:

1. Locate `pack.toml` and read its Minecraft version, loader, loader version, pack format, and pack version.
2. Run `packwiz list` and inspect the `.pw.toml` metadata under `mods/`, `resourcepacks/`, and related folders.
3. Identify the real development root. Do not run Packwiz in a live `.minecraft` or launcher instance unless the repository intentionally uses that layout.
4. Inspect `config/`, `defaultconfigs/`, `kubejs/`, `global_packs/`, `resourcepacks/`, `shaderpacks/`, quest folders, and any deployment scripts.
5. Check Git status before `packwiz refresh`, imports, migrations, or bulk updates; these may rewrite many hashes or metadata files.
6. Confirm the Java version required by the selected Minecraft and loader line, and verify both client and dedicated-server launch commands.
7. Record whether the requested change affects new worlds only, existing worlds, the physical client, the dedicated server, or all four cases.

Do not infer compatibility from a mod name or a nearby Minecraft version. Resolve exact project versions against the selected Minecraft version and loader, then test the resulting pack.

## Repository Model

A typical Packwiz-authored pack contains:

```text
pack.toml                 # pack identity, versions, index reference
index.toml                # generated file inventory and hashes
.packwizignore            # files excluded from the installed pack
mods/*.pw.toml            # source, hash, side, update metadata per mod
resourcepacks/*.pw.toml   # the same model for external resource packs
config/                   # global/client/common mod configuration
 defaultconfigs/          # pack-supplied defaults for newly created worlds
kubejs/                   # startup, server, client scripts and pack resources
resourcepacks/            # bundled resource packs when redistribution permits
<quest-data>/             # mod-specific quest/progression files
```

The exact destination of a file in the repository is its destination in the installed game directory unless Packwiz metadata says otherwise. `index.toml` and the index hash in `pack.toml` are generated state: update them with Packwiz, not hand editing.

See `references/packwiz-workflows.md` for exact Packwiz operations and `references/modpack-content-and-testing.md` for configuration, data, progression, testing, and release guidance.

## Create Or Import A Pack

### New pack

Create an empty project directory, initialize Git, then run:

```bash
packwiz init
packwiz refresh
```

`packwiz init` creates `pack.toml` and `index.toml`. Keep the declared Minecraft and loader versions exact. Set a pack version before Modrinth export and use a versioning scheme that distinguishes user-facing pack releases from individual mod versions.

### Existing CurseForge pack

Import into a clean or disposable directory first:

```bash
packwiz curseforge import path/to/export.zip
packwiz refresh
```

Import can overwrite existing pack files. Commit or back up the current tree first. Importing metadata is not permission to redistribute the original pack, bundled binaries, configs, scripts, quests, artwork, or custom assets.

For an existing unmanaged launcher instance, do not blindly commit the whole instance. Separate authored inputs from generated/runtime state, then use Packwiz-supported detection/import commands where applicable and manually classify the remaining files.

## Add, Remove, Pin, And Update Files

Prefer stable project slugs, project URLs, or exact version URLs over ambiguous search terms:

```bash
packwiz modrinth add sodium
packwiz modrinth add https://modrinth.com/mod/sodium/version/<version-id>
packwiz curseforge add jei
packwiz remove sodium
packwiz pin jei
packwiz unpin jei
packwiz update jei
packwiz update --all
packwiz refresh
```

Short aliases such as `packwiz mr add` and `packwiz cf add` exist. Older tutorials and some binaries use `install` or `get` aliases; prefer the current `add` spelling and inspect the installed binary's `--help` before scripting it.

Packwiz can resolve required dependencies and reject incompatible game versions, but this does not prove that the selected combination starts or behaves correctly. After every dependency-changing operation:

1. inspect the changed `.pw.toml` files and `pack.toml`;
2. inspect unexpected transitive additions or removals;
3. run `packwiz refresh`;
4. review the Git diff;
5. launch a clean client and dedicated server.

Use `packwiz pin <name>` for a deliberately frozen file. Do not pin everything as a substitute for reviewing updates; version metadata and committed hashes already make the checked-in pack reproducible.

## Classify Client And Server Files

Each Packwiz metadata file may declare `side = "client"`, `"server"`, or `"both"`; omitted side is equivalent to both in the current Packwiz format. Treat this as deployment behavior, not an assertion that the mod's internal code is safe.

- `client`: rendering, UI, keybind, shader, menu, and other physical-client-only content.
- `server`: server administration or gameplay logic that the client does not require.
- `both`: content, registries, networking, shared gameplay, or anything whose absence causes connection or content mismatch.

When uncertain, use `both` until documentation and dedicated-server/client testing prove a narrower side. A false client-only classification can produce missing registries or rejected connections; a false both-side classification can crash a dedicated server by loading client classes.

Packwiz optional metadata can mark files optional and set their default state. Optional gameplay-changing mods need compatibility testing in every supported combination; avoid a combinatorial ecosystem of toggles.

## Configuration Strategy

Classify each setting by ownership and lifecycle before copying files:

- **Client preference:** graphics, keybinds, HUD placement, sound, local UI. Avoid forcing personal preferences unless they define the pack experience.
- **Common/startup:** loaded separately by client and server; not automatically synchronized. Keep values equal where divergence changes registries, recipes, or protocol-visible behavior.
- **Server/world:** authoritative gameplay settings, often stored per-world and synchronized by Forge/NeoForge when the mod uses their server config type.
- **Generated/runtime:** caches, logs, launcher state, player data, worlds, crash reports, backups, and transient generated files. Exclude these.

On Forge 1.20.x, typed `SERVER` configs live under the world's `serverconfig/`; files in `defaultconfigs/` seed missing world configs when the world is first created. Current NeoForge differs: the global `config/` server file is the base and a same-named world `serverconfig/` file is a per-world override. NeoForge can still seed missing files from `defaultconfigs/`. This lifecycle has changed across loader versions, so verify the exact branch and test a fresh world plus an existing world. Later changes to `defaultconfigs/` do not continuously synchronize already-created files.

Fabric has no single loader-wide configuration-file contract comparable to Forge/NeoForge config types. Follow each mod's own documentation and implementation, and test physical-side behavior.

Never copy an entire generated `config/` tree without review. Start once in a disposable instance, change one intentional setting at a time, and keep only files needed to define the pack.

## KubeJS In The Pack

Use KubeJS when JSON datapacks/configs cannot clearly express pack integration, recipe changes, custom content, or event-driven progression.

- `kubejs/startup_scripts`: registry-time content and other restart-required definitions.
- `kubejs/server_scripts`: recipes, tags, loot, commands, player/world/server events, and datapack-like logic.
- `kubejs/client_scripts`: client-only tooltips, recipe-viewer integration, colors, UI, and client events.
- `kubejs/data/<namespace>` and `kubejs/assets/<namespace>`: raw data/resource-pack content distributed with the scripts.

KubeJS APIs change substantially between Minecraft/KubeJS versions and addons. Before editing, identify exact KubeJS, Rhino, ProbeJS, and integration versions. Prefer generated ProbeJS typings and project-local helpers over snippets copied from another pack.

Assign stable IDs to important recipes, use targeted removals, keep client classes out of common/server scripts, and restart after startup-script or registry changes. Use `/reload` only for reloadable server/data content; use a client resource reload only for reloadable client resources. Inspect KubeJS logs and verify the result in a recipe viewer and through actual gameplay.

KubeJS-specific script reload commands can reevaluate top-level code, but they do not rerun registry work or replace listeners that were already registered. Do not use `/kubejs reload startup_scripts`, `/kubejs reload server_scripts`, or `/kubejs reload client_scripts` as substitutes for the real lifecycle above.

## Datapacks, Resource Packs, Quests, And World Data

Prefer standard data/resource formats when they are sufficient:

- datapacks for recipes, tags, loot, advancements, functions, structures, and supported worldgen/dynamic-registry data;
- resource packs for language, models, textures, sounds, fonts, and UI assets;
- quest-mod-native data for chapters, dependencies, rewards, and team progression;
- KubeJS for orchestration or APIs that are clearer and safer in scripts.

Use a unique namespace for authored content. Keep stable resource IDs and quest IDs across releases. Datapack load order determines replacement behavior; tags normally merge unless configured to replace. Dynamic-registry/worldgen changes often require a restart and can make existing-world migration risky.

Treat quest files as source code: review diffs, preserve IDs, verify prerequisites cannot deadlock, and test rewards on a clean profile and in multiplayer/team mode when supported.

## Migrations

Use Packwiz migration commands rather than manually changing only `pack.toml`:

```bash
packwiz migrate minecraft <target-version>
packwiz migrate loader <target-version-or-latest-or-recommended>
```

Exact subcommands and supported loaders are version-sensitive; check `packwiz migrate --help` and the installed Packwiz version.

A metadata migration is only the first step. Minecraft/loader upgrades can change Java requirements, config schemas, datapack pack formats, KubeJS events, recipe JSON, tags, worldgen, mod IDs, and saved-world data. Perform migrations on a branch, preserve a world backup, and validate a new world plus a copied existing world.

## Distribution

### Export archives

```bash
packwiz modrinth export -o build/my-pack.mrpack
packwiz curseforge export -o build/my-pack.zip
```

Packwiz refreshes before export. Review the archive, included overrides, side selection, and platform restrictions. An export succeeding does not establish redistribution rights.

### Packwiz installer

Host the pack files over HTTP(S), then use the installer bootstrap against `pack.toml`. For local development:

```bash
packwiz serve
```

For a headless server install:

```bash
java -jar packwiz-installer-bootstrap.jar -g -s server https://example.invalid/pack.toml
```

Pin the bootstrap artifact/version and verify its checksum in production automation. Do not use `example.invalid`; replace it with the actual hosted pack URL.

## Validation Loop

Use the smallest relevant loop, then complete the whole matrix before release:

1. `packwiz refresh` and require a clean second refresh.
2. Review `git diff --check` and the manifest/index diff.
3. Export every supported distribution format.
4. Install into a clean temporary client instance from the exported artifact or hosted Packwiz URL.
5. Launch the client to the title screen, create a world, join it, and exercise changed recipes/config/progression.
6. Install or export the server side into a clean directory and launch a dedicated server.
7. Join the dedicated server with the released client artifact.
8. Check `latest.log`, KubeJS logs, datapack errors, missing registry messages, recipe viewer output, quest state, and networking failures.
9. For updates, test both a new world and a backup copy of an existing world.
10. Record exact Packwiz, Java, Minecraft, loader, and pack versions in the release notes or build output.

Automate deterministic checks, but do not replace game launches with TOML/JSON syntax checks. A valid manifest can still contain incompatible mods, wrong-side files, broken recipes, or unsafe world migrations.

## Git And Release Hygiene

Commit authored source and Packwiz metadata. Exclude worlds, logs, caches, crash reports, launcher credentials, account data, backups, exported archives, and local options unless intentionally shipped. Use `.packwizignore` for files that must remain in the repository but must not be installed.

For updates, prefer focused commits:

1. mod/loader metadata change;
2. config/script migration;
3. generated index refresh;
4. release version and notes.

Never commit API tokens, CurseForge keys, launcher authentication, private server addresses, or user data. Keep large redistributed binaries out of Git when Packwiz metadata can reference an approved source.

## Licensing And Publication

Before redistributing each bundled binary, config, script, quest, texture, sound, or copied data file, confirm the author/license permits redistribution. Platform availability alone is not a blanket license. Prefer Packwiz metadata that lets clients download from the original approved host.

For CurseForge publication, verify any non-CurseForge mods against current CurseForge policy and approved lists. For Modrinth exports, obey its current archive/domain restrictions. Follow current Minecraft Usage Guidelines and clearly state that the pack is not official or endorsed when publishing.

Keep a machine-readable or documented inventory of project URL, file/version ID, license/permission status, side, and reason for inclusion.

## Common Failure Modes

- Editing a launcher instance instead of the Packwiz source tree.
- Forgetting `packwiz refresh` after changing configs, scripts, quests, or bundled files.
- Using `packwiz update --all` without reviewing transitive changes and launching the pack.
- Marking a shared-content mod client-only because a project page calls it "client friendly."
- Copying world `serverconfig/` files while expecting them to seed new worlds, or changing `defaultconfigs/` while expecting existing worlds to update.
- Treating `/reload` as sufficient for registries, startup scripts, loader configs, or dynamic-registry worldgen.
- Copying KubeJS syntax between Minecraft lines without checking exact generated typings.
- Shipping generated caches, local options, servers, maps, player data, or credentials.
- Assuming a successful export proves the pack can launch or may legally redistribute every file.
- Testing only integrated singleplayer; this hides dedicated-server classloading and side errors.

## Source References

- Packwiz documentation: `https://packwiz.infra.link/`
- Packwiz source: `https://github.com/packwiz/packwiz`
- Packwiz format specification: `https://github.com/packwiz/packwiz-spec`
- Packwiz installer: `https://github.com/packwiz/packwiz-installer`
- KubeJS documentation: `https://kubejs.com/wiki/`
- KubeJS source: `https://github.com/KubeJS-Mods/KubeJS`
- Forge 1.20 configuration: `https://docs.minecraftforge.net/en/1.20.x/misc/config/`
- NeoForge configuration: `https://docs.neoforged.net/docs/misc/config/`
- Minecraft Usage Guidelines: `https://www.minecraft.net/en-us/usage-guidelines`
