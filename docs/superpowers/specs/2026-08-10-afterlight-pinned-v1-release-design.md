# AFTERLIGHT Pinned RC2 and v1.0 Release Design

Date: 2026-08-10

Status: approved by Shane. This design extends the accepted friend-release design without reopening completed story, Gate, quest, or server architecture.

## Decision

AFTERLIGHT remains on Minecraft 1.21.1, NeoForge 21.1.248, and Java 21. The published `v0.9.0-rc.1` tag and release remain immutable.

The next candidate is `0.9.0-rc.2`. It fixes the remaining mutable client-installer lookup, keeps the streamlined friend-server package, and carries one practical manual acceptance matrix. Simple Voice Chat remains installed for compatibility, but voice chat is not a release gate because the group will use Discord.

Version `1.0.0` is published only after the required `rc.2` manual checks pass. Optional polish, exhaustive natural-progression playthroughs, AutoModpack, public distribution of friends-only archives, and enterprise host controls remain outside this release.

## Pinned Prism Client

The Prism archive contains exactly these four regular files:

```text
.minecraft/packwiz-installer-bootstrap.jar
.minecraft/packwiz-installer.jar
instance.cfg
mmc-pack.json
```

Both JARs come from exact versioned Packwiz GitHub release URLs. The build authenticates the existing bootstrap SHA-256 plus the existing main-installer size and SHA-256 from `tools/versions.env` before either file enters the archive.

The Prism prelaunch command is exact:

```text
"$INST_JAVA" -jar packwiz-installer-bootstrap.jar --bootstrap-no-update --bootstrap-main-jar packwiz-installer.jar -g https://luskish.github.io/afterlight-pack/pack.toml
```

The archive inspector rejects a missing or additional entry, either wrong JAR digest, a mutable installer command, path aliases, links, secrets, or any embedded mod JAR. Deterministic ZIP metadata and byte-for-byte repeatability remain required.

Release metadata records both installer versions, sizes, and SHA-256 values in addition to the existing pack, loader, commit, and Prism facts.

## Versioned Release Pipeline

Release tooling derives the pack version from `pack.toml` instead of hardcoding `0.9.0-rc.1`. Public output remains exactly:

```text
AFTERLIGHT-prism-instance.zip
release-metadata.json
SHA256SUMS
```

Friends-only output uses the derived version:

```text
AFTERLIGHT-<version>.mrpack
AFTERLIGHT-<version>-curseforge.zip
```

The pipeline rejects a version mismatch between `pack.toml`, metadata, filenames, release notes, tag, and requested release version.

For `rc.2`, the pack version and generated Packwiz index move together. The exact candidate runs focused tests, the complete Python suite, static and runtime quest validation, `verify-pack.sh`, a fresh headless server boot, Compose rendering, ShellCheck, two release builds, deterministic archive comparison, a clean client install from the released Prism bytes, clean-worktree checks, exact `dev` and `main` CI, and Pages parity before publication.

After manual acceptance, the `1.0.0` change is limited to release identity, generated Packwiz state, release notes, and any acceptance record. It receives the same complete gauntlet and promotion sequence. No gameplay, mod, quest, recipe, server, or configuration change may ride inside the version-only promotion.

## Streamlined Manual Acceptance

The exact published `rc.2` lineage must pass these checks:

1. Import the released Prism ZIP, select Java 21 and 8 to 10 GiB RAM, sign in through Microsoft, and reach the title screen in under three minutes after downloads finish.
2. Create a new world, open the quest book, and confirm the ECHO theme, chapter groups, text wrapping, icons, and Chapter 1 progression render correctly.
3. Join the released dedicated server from the released client, disconnect, reconnect, and confirm whitelist behavior with at least two real players.
4. In a disposable operator-assisted test world, exercise every hard gate, craft the Gate of Return, claim one Seal per eligible player, transfer one Seal, and craft the three Seal-preserving Draconic entry recipes while the transferred Seal remains exactly one.
5. Measure the completed Supercritical Phase Shifter throughput and total wall time for the four-antimatter-pellet Isotopic Core requirement. Record whether the result is acceptable before `1.0.0`.
6. On the intended VPS, create a verified backup, perform one normal update, induce one safe update failure, run the printed rollback command, and confirm the released client can rejoin.
7. Restore a verified backup into an empty replacement data directory and confirm the restored server reaches healthy state and accepts the released client.

Voice chat is not part of this matrix. Discord is the expected voice lane. UDP `24454` remains available for Simple Voice Chat, but the VPS operator may omit that firewall or provider rule when the group does not use it.

Each result is recorded as `PASS` or `FAIL` with date, tester, candidate SHA, release URL, and evidence path. No automated test substitutes for a manual result.

## VPS Handoff

The release updates `docs/SERVER.md` and the final user handoff with one ordered VPS checklist:

1. Provision a current x86-64 Ubuntu host with at least 16 GiB RAM, 4 CPU threads, 30 GiB free storage, Docker Engine, Docker Compose v2, Git, OpenSSL, and working SSH access.
2. Clone the repository as one normal operator account, switch to stable `main`, create the exact data, backup, and secret paths, and generate the mode `0600` RCON secret.
3. Run `server/afterlight-server.sh doctor`, then `start`. Do not run Compose directly for supported operations.
4. Allow the existing SSH port before enabling UFW. Allow TCP `25565`. Allow UDP `24454` only if Simple Voice Chat will be used. Never expose RCON TCP `25575`.
5. Populate the Minecraft whitelist before sharing the server address. Forward the same required ports in any provider firewall or home router.
6. Run `status`, create one verified `backup`, and record the exact rollback command before opening the server to friends.
7. Use only `update`, `backup`, `rollback`, `status`, and `stop` for routine operations. Preserve printed rescue paths after failures.

The final release response lists these prerequisites and commands directly and points to `docs/SERVER.md` for the complete operating procedure.

## Verification And Release Boundaries

- Plans 05 and 06 story, quest, Gate, postgame, and recipe identities remain unchanged.
- The friend-server Compose and operator command remain the supported host lane.
- `v0.9.0-rc.1` remains available as rollback evidence and is never moved or rewritten.
- `rc.2` and `v1.0.0` public releases contain only the three public-safe top-level assets.
- The `.mrpack` and CurseForge ZIP remain friends-only and are never attached publicly.
- Simple Voice Chat stays optional and unclaimed.
- A failed automated or manual gate fixes forward through a new candidate. Neither `main` nor a published tag is force-pushed.
