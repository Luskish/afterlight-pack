# Packwiz Workflows

Use this reference for commands and Packwiz-specific review points. Record how the Packwiz binary was installed and which release or commit it came from, then check `packwiz <command> --help`; generated command-reference pages track the current build more closely than old blog posts.

## Source Of Truth

- Documentation: https://packwiz.infra.link/
- CLI command reference: https://packwiz.infra.link/reference/commands/packwiz/
- Source: https://github.com/packwiz/packwiz
- Pack format specification: https://github.com/packwiz/packwiz-spec
- CC0 example pack: https://github.com/packwiz/packwiz-example-pack
- Installer: https://github.com/packwiz/packwiz-installer
- Installer bootstrap: https://github.com/packwiz/packwiz-installer-bootstrap

This reference was checked against Packwiz source commit `dfd8b68a4796c763e25bad50265ea1f1233e24f1` as well as the official documentation. Do not treat that commit as a permanent version pin; re-check current docs/source when command behavior matters.

## Initialize

Work in a source directory separate from the launcher/game instance:

```bash
mkdir my-pack
cd my-pack
git init
packwiz init
packwiz refresh
```

`pack.toml` stores pack identity, version, Minecraft and loader versions, and the index hash. `index.toml` stores indexed paths and hashes. Current Packwiz source declares pack format `packwiz:1.1.0`, but agents should preserve the format written by the installed tool and use supported migrations rather than forcing this value.

For non-interactive automation, provide exact versions rather than resolving latest during a release build:

```bash
packwiz init \
  --name "Example Pack" \
  --author "Author" \
  --version "1.0.0" \
  --mc-version "1.21.1" \
  --modloader fabric \
  --fabric-version "<exact-loader-version>"
```

Useful inspection:

```bash
packwiz list
packwiz --help
packwiz settings --help
```

## Add External Projects

```bash
packwiz modrinth add <slug-or-url>
packwiz curseforge add <slug-or-url>
```

Current generated command references use `add`; older tutorials and some binaries expose `install` or `get` aliases. Inspect `packwiz modrinth --help` and `packwiz curseforge --help` before scripting a particular binary. Packwiz also accepts exact Modrinth version URLs/IDs and CurseForge file URLs/IDs. Prefer an exact project or version URL in automation. Search-result selection may be interactive, and global `--yes` accepts defaults that may choose an unintended result.

Packwiz prompts for required dependencies that are not installed and checks Minecraft/loader compatibility. Inspect every dependency it adds. Metadata resolution does not detect all runtime incompatibilities or duplicate-function mods.

The current source supports loader compatibility aliases when resolving files—for example NeoForge may accept Forge-labelled projects in some contexts—but that does not guarantee binary compatibility. Trust project metadata plus a real launch, not the alias alone.

## Metadata Files

A typical `.pw.toml` contains:

```toml
name = "Example Mod"
filename = "example.jar"
side = "both"

[download]
hash-format = "sha512"
hash = "..."
mode = "url"
url = "https://..."

[update.modrinth]
mod-id = "..."
version = "..."
```

Packwiz source recognizes `side` values `server`, `client`, `both`, and an omitted/empty value equivalent to `both`. Optional file metadata has:

```toml
[option]
optional = true
default = false
description = "Optional client feature"
```

Do not hand-author platform update metadata when `packwiz modrinth install`, `packwiz curseforge install`, or `packwiz url add` can generate it. Hand-written external URLs must be stable direct downloads and must include a verified cryptographic hash.

## Direct URLs And Local Files

Use `packwiz url --help` for the installed syntax when a file is hosted outside supported platforms. A manually defined download requires URL, filename, hash format, and hash.

Packwiz can index local files such as configs, scripts, and permitted custom JARs. Local binaries are placed at their installed path and added by `packwiz refresh`; this is less reviewable and less Git-friendly than download metadata. Prefer an approved, stable upstream download where redistribution and host policy permit it.

## Remove, Pin, Update

```bash
packwiz remove <metadata-name>
packwiz pin <metadata-name>
packwiz unpin <metadata-name>
packwiz update <metadata-name>
packwiz update --all
```

The metadata name normally corresponds to the `.pw.toml` basename, not necessarily the display name. If Packwiz cannot find a file, refresh first and use `packwiz list`.

Pin when an update is intentionally unsafe or a pack integration depends on an exact version. Document why. Before bulk updates, commit a clean baseline; afterward inspect each metadata diff and all transitive dependency changes.

## Refresh And Ignore Rules

```bash
packwiz refresh
```

Refresh walks the pack root, applies default exclusions and `.packwizignore`, hashes internal files, rewrites `index.toml`, and updates the index hash in `pack.toml`.

Current default exclusions include Git metadata, `.DS_Store`, root CurseForge ZIP exports, `.mrpack` files, and Packwiz binaries. Use `.packwizignore` for additional project-local exclusions. It follows Gitignore-style patterns.

A deterministic check is:

```bash
packwiz refresh
git diff --exit-code -- pack.toml index.toml
```

This is only expected to be clean when all intended source changes and their refreshed index are already committed/staged in the comparison baseline.

Do not edit `index.toml` manually. If an index entry is wrong, fix the source path, metadata, or ignore rule and refresh.

## Acceptable Game Versions

Packwiz supports an `acceptable-game-versions` option for projects that legitimately publish compatible files under nearby game versions:

```toml
[options]
acceptable-game-versions = ["1.20", "1.20.1"]
```

Use it narrowly. It changes resolver acceptance, not code compatibility. Confirm each selected file's loader, API dependencies, mappings expectations, and real launch behavior.

## Import And Detection

```bash
packwiz curseforge import path/to/export.zip
packwiz curseforge detect
```

Import may overwrite current content; use a clean worktree or commit first. Detection can replace local files with CurseForge metadata when matches are found. Review hashes and exact file IDs before deleting original recovery copies.

Import/detection does not grant redistribution rights and does not automatically classify authored configs, scripts, quests, saves, or generated runtime files.

## Migrate

Inspect supported targets first:

```bash
packwiz migrate --help
packwiz migrate minecraft --help
packwiz migrate loader --help
```

The CLI currently exposes Minecraft and loader migrations. Migrations update Packwiz metadata; they cannot port KubeJS scripts, configs, datapacks, quests, worlds, or binary-incompatible mods. Treat their output as the start of a migration branch.

## Export

```bash
mkdir -p build
packwiz modrinth export -o build/my-pack.mrpack
packwiz curseforge export -o build/my-pack.zip
```

Current source performs a refresh before export. Modrinth export normally restricts external-file domains according to platform rules. CurseForge export supports side selection; inspect `packwiz curseforge export --help` and verify that client and server artifacts contain the expected overrides.

After export:

- list archive contents;
- import into a clean launcher profile;
- verify selected Minecraft/loader versions;
- verify optional and side-only files;
- launch and test;
- retain the exact artifact checksum in release automation.

## Serve And Install

Local development server:

```bash
packwiz serve
# pack available at http://localhost:8080/pack.toml by default
```

The development server refreshes the index when queried by default. It is not production hosting.

Typical installer bootstrap invocation:

```bash
java -jar packwiz-installer-bootstrap.jar \
  https://packs.example.org/my-pack/pack.toml
```

Headless dedicated server side:

```bash
java -jar packwiz-installer-bootstrap.jar -g -s server \
  https://packs.example.org/my-pack/pack.toml
```

The installer can be a launcher pre-launch step or part of server provisioning. Production automation should pin and checksum the bootstrap JAR, use HTTPS, fail closed on installer errors, and back up worlds before automatic pack updates.

## CI Pattern

A minimal Packwiz CI job should:

1. install a Packwiz binary pinned by release or source commit and verify its checksum;
2. run `packwiz refresh`;
3. fail if tracked manifest/index files changed;
4. export supported archive formats;
5. inspect or import artifacts in clean directories;
6. preserve export checksums and logs;
7. delegate actual client/server launches to integration jobs or a controlled smoke-test harness.

Do not use `packwiz serve` as the only CI validation and do not invoke bulk update commands in ordinary validation jobs.

## Troubleshooting

- **File changed but clients do not receive it:** refresh, verify it is not ignored, and inspect its index entry.
- **Packwiz cannot find a mod name:** use `packwiz list` and the `.pw.toml` basename, or use an exact platform URL for installation.
- **Wrong project selected:** remove it and reinstall with an exact project/version URL; avoid `--yes` with ambiguous search.
- **Export omits a mod:** inspect `side`, optional metadata, platform source, and export-side options.
- **Server receives client mods:** correct metadata only after dedicated-server testing confirms the project is client-only.
- **Update jumps Minecraft lines:** inspect `pack.toml`, acceptable versions, loader aliases, and the selected project version metadata.
- **Installer repeats downloads:** confirm hosted `pack.toml`/index hashes are current, stable HTTP caching is not serving mismatched files, and the installer state can be written.
