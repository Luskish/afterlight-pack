# AFTERLIGHT Friend Release Design

**Date:** 2026-08-09

**Status:** Approved by Shane's instruction to streamline Plan 07 and defer nonessential backend hardening.

## Purpose

Ship the completed AFTERLIGHT pack in a form that Shane and a private friend group can install, update, host, back up, and recover without enterprise deployment machinery.

The release keeps the quality that players notice:

- Stable NeoForge 1.21.1 pack content
- Complete story, quest book, Gate finale, and postgame
- One-click Prism import with automatic Packwiz updates
- A reproducible dedicated server package
- Scheduled and on-demand world backups
- A safe, understandable update and rollback procedure
- CI that verifies the pack, server configuration, exports, and release artifacts
- Clear onboarding and troubleshooting documentation

## Explicitly Deferred

The following work remains preserved on `codex/plan07-task1` for a later backend-hardening project:

- Cryptographic release receipt chains
- Fifteen-second current-channel leases
- Dynamic nftables gate generations
- Crash-injected durable pointer state machines
- Multi-phase operation and rollback journals
- systemd watchdog reconciliation
- Forensic transaction archives
- Two independent full release gauntlets

These features are useful for a public or business-critical service, but they are not required for a private Minecraft server operated by Shane.

## Release Model

### Stable and Working Branches

- `dev` remains the working branch.
- `main` remains the stable Packwiz channel used by friends.
- Pack changes reach `main` only after local verification and green `pack-ci` on `dev`.
- No force push, branch deletion, or automatic mod removal is allowed.

### Versioning

- The first friend-ready artifact is `0.9.0-rc.1`.
- Shane and at least one friend can play the release candidate immediately.
- `1.0.0` requires one successful Prism import, title-screen launch, dedicated-server join, quest-book open, and voice connection check.
- Backend hardening is not a `1.0.0` requirement.

## Client Distribution

The recommended artifact is `AFTERLIGHT-prism-instance.zip`.

- It points to `https://luskish.github.io/afterlight-pack/pack.toml`.
- It pins Packwiz bootstrap `v0.0.3` and verifies SHA-256 `a8fbb24dc604278e97f4688e82d3d91a318b98efc08d5dbfcbcbcab6443d116c` before packaging.
- Repeated builds from the same repository state must be byte-identical.
- The archive must contain no mod JAR except the approved Packwiz bootstrap.
- The Prism archive is the only public-safe client artifact.
- The `.mrpack` and CurseForge ZIP embed third-party mod JARs, remain friends-only, and are never uploaded as public CI artifacts.

## Dedicated Server

### Supported Host

- Ubuntu 24.04 LTS or another current x86-64 Linux distribution
- Docker Engine with Docker Compose v2
- At least 16 GiB RAM, 4 CPU threads, and 30 GiB free storage
- TCP `25565` and UDP `24454` forwarded to the host
- RCON `25575` is never published

### Container Model

The server uses Docker Compose with two digest-pinned images:

- `itzg/minecraft-server:2026.8.0-java21@sha256:b76b9298a2a60d5cf9d223e009cd0b8ad620c2080abd83f9a1fa5084fa87f9ab`
- `itzg/mc-backup:2026.8.0@sha256:ae54d88d1a5dfbc185f1f94e50bb2e9b68484719013f4f21c573422dd4950f32`

The Minecraft container uses the official `PACKWIZ_URL` integration documented at `https://docker-minecraft-server.readthedocs.io/en/latest/mods-and-plugins/packwiz/`. Every intentional restart synchronizes server-side pack files from stable `main`.

Required server settings:

- Minecraft `1.21.1`
- NeoForge `21.1.248`
- Java 21 image
- Initial memory `4G`
- Maximum memory `10G`
- Container memory limit `13G`
- `online-mode=true`
- `white-list=true`
- `enforce-whitelist=true`
- `enforce-secure-profile=true`
- Maximum 12 players
- View distance 10 and simulation distance 8
- RCON password provided through a Compose secret file
- `restart: unless-stopped`

### Backups

The backup sidecar follows the official `itzg/docker-mc-backup` contract.

- Back up every 6 hours after the server becomes healthy.
- Run `save-all`, disable saves during the archive, call `sync`, and resume saves.
- Store zstd tar archives outside `/data`.
- Retain 14 days of backups.
- Exclude downloaded JARs, caches, logs, crash reports, and transient lock or partial files.
- Support `docker compose exec backup backup now` for an on-demand pre-update backup.
- Never automatically delete the current data directory during rollback.

## Operations

One small Bash entry point, `server/afterlight-server.sh`, provides these commands:

- `doctor`: validate dependencies, canonical host paths, secrets, Compose rendering, ports, and writable directories.
- `start`: run `doctor`, create `server.properties` only when absent, then start Minecraft and backups.
- `stop`: stop both services cleanly.
- `status`: print Compose state and Minecraft health.
- `backup`: trigger an on-demand backup and verify a new archive appears.
- `update`: require a clean backup, recreate Minecraft so Packwiz synchronizes stable `main`, and wait up to 10 minutes for health. Failure leaves the server stopped and prints the rollback command.
- `rollback BACKUP`: require explicit `--confirm`, stop services, rename the current data tree to a timestamped rescue path, restore the selected archive into a new data directory, start the server, and wait for health. Failure preserves both the rescue tree and selected archive.

The script never sources `.env`, never accepts a path outside the configured data and backup roots, never deletes a world, and never hides a failed backup or boot.

## Firewall and Access

The release documents a conventional host firewall rather than a dynamic lease gate.

- Allow the operator's SSH port.
- Allow TCP `25565`.
- Allow UDP `24454`.
- Deny unsolicited inbound traffic by default.
- Do not expose RCON.
- Use the Minecraft whitelist before sharing the server address.

Firewall setup remains an operator command because changing remote-host firewall rules automatically could lock Shane out of the VPS.

## CI and Verification

`pack-ci` must run the following on every `dev` and `main` push:

- Packwiz manifest verification and refresh idempotence
- Full repository Python tests
- Static and runtime quest validation through the existing server harness
- `VERIFY: ALL GREEN`
- `SERVER BOOT: OK`
- Docker Compose canonical render for normal and backup services
- Bash syntax and ShellCheck for server operations
- Prism artifact build and archive inspection
- `.mrpack` and friends-only CurseForge export generation
- Secret, JAR, and U+2014 scans
- Final clean-tree check

CI uploads only the public-safe Prism archive, checksums, and release metadata. It may build the `.mrpack` and CurseForge ZIP for validation, but it never uploads either friends-only archive.

## Practical Release Gauntlet

The release candidate requires one clean detached-SHA gauntlet:

1. Run all unit and contract tests.
2. Run `./tools/verify-pack.sh`.
3. Run `BOOT_TIMEOUT=600 ./tools/server-test.sh`.
4. Render both Compose profiles.
5. Build the Prism archive twice and prove byte equality.
6. Export `.mrpack` and CurseForge ZIP.
7. Inspect every artifact for secrets and disallowed JARs.
8. Push exact SHA to `dev` and require green CI.
9. Fast-forward exact SHA to `main` and require green CI.
10. Verify GitHub Pages `pack.toml` and `index.toml` byte parity.
11. Create the `v0.9.0-rc.1` prerelease with only the Prism archive, checksums, and release metadata.

## Manual Acceptance

Automated work stops short of claiming these observations:

- Microsoft-authenticated Prism launch
- Title screen in under three minutes on Shane's PC
- Quest-book rendering and theme
- Dedicated-server login by a released client
- Two-player Simple Voice Chat
- Real router forwarding and VPS firewall behavior

These checks are short and player-facing. They are not replaced by backend hardening. After they pass, the same artifact can be promoted to `1.0.0` without adding enterprise infrastructure.

## Success Criteria

The friend release is complete when:

- Stable pack content is unchanged except intentional version and release metadata.
- Client artifacts build reproducibly and contain only allowed files.
- A Linux operator can follow one README from an empty host to a healthy server.
- Backups run automatically and on demand.
- Update failure stops safely and rollback preserves the prior data tree.
- Local verification, `dev` CI, `main` CI, Pages parity, and the release candidate publication all pass.
- Remaining manual checks are listed with clear owner and commands.
