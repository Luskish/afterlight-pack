# Plan 07 Architecture Audit

Date: 2026-08-08

Status: design gate corrected. No Docker, VPS, backup, or recovery behavior is claimed by this document.

## Scope

The launch architecture was reviewed before implementation against the exact current itzg image manifests, Packwiz installer release bytes, NeoForge installer checksum, Docker Compose behavior, GitHub Actions APIs, GitHub Pages mutability, RCON secret handling, Chunky operations, and Python archive extraction safety.

The review found nine Critical and nine Important design gaps in the earlier Plan 07. The rewritten plan closes them at the contract level. Implementation still requires test-first development, independent review, two clean gauntlet runs, and the live-host matrix.

## Exact External Pins

| Component | Exact reference | Additional evidence |
|---|---|---|
| Minecraft server image | `itzg/minecraft-server:2026.8.0-java21@sha256:b76b9298a2a60d5cf9d223e009cd0b8ad620c2080abd83f9a1fa5084fa87f9ab` | Source revision `1e2d375dba72a0730365c29dd5f1990f9764da5a` |
| Backup image | `itzg/mc-backup:2026.8.0@sha256:ae54d88d1a5dfbc185f1f94e50bb2e9b68484719013f4f21c573422dd4950f32` | Source revision `438b97f9d520b93a29f586f33dbd29a3adb372ca` |
| Packwiz bootstrap | `v0.0.3` | SHA-256 `a8fbb24dc604278e97f4688e82d3d91a318b98efc08d5dbfcbcbcab6443d116c`, 98,989 bytes |
| Packwiz installer | `v0.5.14` | SHA-256 `c9f646908d340d84773948a9a7d98bc1dae250d35e1016dc6e2b8459760b5598`, 4,378,828 bytes |
| NeoForge installer | `21.1.248` | SHA-256 `68eeab77059ba53df1812f1afa5bf530ab2566a3cdcd5f924aa6e71be42e410c` |

The OCI index digests were verified against registry response bodies. Both server-image child manifests report Java `jdk-21.0.11+10`. Native image children exist for `linux/amd64` and `linux/arm64`, but only `linux/amd64` is launch-supported until the complete arm64 pack matrix passes.

## Corrected Trust Model

1. Resolve and validate one exact 40-character lowercase Git SHA.
2. Require that SHA to be the exact `head_sha` of a completed successful `main` push run for `.github/workflows/pack-ci.yml`.
3. Require the exact run attempt's `verify-and-export` job to be completed successfully.
4. Compare Pages `pack.toml` and `index.toml` byte-for-byte with raw full-SHA files.
5. Install Pages into scratch only to validate the mutable public update lane.
6. Stage production only from raw full-SHA URLs.
7. Recheck `main` immediately before stopping the live server.
8. Use historical accepted workflow evidence and raw SHA bytes for rollback and recovery. Historical operations do not depend on current Pages state.

Check names alone are not acceptance evidence because duplicate check names can exist for one SHA. Pages is not an immutable deployment source.

## Corrected Installer Model

Every consumer must verify both Packwiz JAR hashes and run:

```sh
java -jar packwiz-installer-bootstrap.jar \
  --bootstrap-no-update \
  --bootstrap-main-jar /trusted/packwiz-installer-v0.5.14.jar \
  -g -s server \
  "https://raw.githubusercontent.com/OWNER/REPO/SHA/pack.toml"
```

Verifying only bootstrap `v0.0.3` is insufficient because its default behavior downloads a mutable latest main installer without an independent digest.

The server invocation includes `-s server`. Prism omits the side flag because installed Packwiz installer `v0.5.14` defaults to `client`; its prelaunch still includes `-g` for noninteractive progress.

## Corrected Data and Secret Model

- The Minecraft service receives one read-write `/data` bind.
- The backup service receives `/data` read-only and `/backups` read-write.
- Bind sources use long syntax with `create_host_path: false`.
- Data, backups, state, quarantine, and secrets are canonical, pairwise nonnested paths.
- Data and quarantine share a local filesystem so publication and quarantine use atomic rename.
- RCON uses a Compose secret outside `/data`. Port `25575` is never published.
- Backup archives reject `.rcon-cli.env`, `.rcon-cli.yaml`, `server.properties`, and every configured secret path.
- Recovery regenerates operational properties and a fresh RCON secret.

## Corrected Backup and Restore Model

- Every maintenance operation shares one host `flock`.
- Online backup requires healthy RCON, performs `save-off` and `save-all flush`, and attempts `save-on` from a host trap.
- The backup image writes only into a unique incoming directory and propagates tar status through the post-backup hook.
- A Python 3.12 archive guard rejects absolute paths, parent traversal, links, devices, FIFOs, duplicate names, control characters, unexpected JARs, secrets, missing `world/level.dat`, excessive member counts, and excessive expanded bytes.
- Only a fully validated bundle with checksum, release receipt, managed ledger, and completion marker is atomically published.
- Scheduled and protected backups have separate retention classes. Protected bundles are never pruned automatically.
- Upstream `restore-backup` and `restore-tar-backup` helpers are explicitly forbidden.
- Empty-host recovery requires an encrypted copy stored independently from the VPS.

## Corrected Activation Model

Pack ownership is limited to current indexed files beneath `config`, `global_packs`, `kubejs`, and `mods`. Each release stores a NUL-delimited managed ledger. Activation may add or replace current managed files and remove only paths from the prior ledger. Untracked runtime state is preserved. Every mutation is journaled while the server is stopped.

An update health failure stops the server, preserves logs, candidate files, backup, ledger, and journal, exits with the rollback-required code, and prints one exact rollback command. It never restores world data automatically.

## Distribution Decision

Prism plus Packwiz remains the only complete supported client lane. AutoModpack is disabled because the licensing inventory currently contains 13 denied, 13 manual-review, and 7 unknown client entries. The release candidate does not add, host, test, or advertise AutoModpack.

## Deferred Live Evidence

These checks cannot be truthfully completed on the current Mac-only authoring session:

- VPS firewall exposes only Minecraft TCP and voice UDP.
- Host filesystem provides reliable `flock` and same-filesystem atomic rename.
- Graceful stop finishes inside two minutes without exit 137.
- Ten-gigabyte heap remains below the 13 GB container limit under gameplay and Chunky load.
- Backup throughput, restore throughput, free-space checks, and quarantine capacity fit the real world size.
- Host reboot restores the Compose stack and backup schedule without creating a new world.
- Two released clients join, whitelist works, and voice chat works over UDP.
- Installed Chunky RCON output is classified conservatively for active, paused, complete, and unknown states.
- The full pack boots and plays on arm64.
- An encrypted offsite bundle restores onto a genuinely empty replacement host.
- A real update failure is followed by explicit rollback without post-backup player writes.

## Primary References

- Docker Registry API: `https://distribution.github.io/distribution/spec/api/`
- itzg server documentation: `https://docker-minecraft-server.readthedocs.io/`
- Docker Compose services: `https://docs.docker.com/reference/compose-file/services/`
- Python tar extraction filters: `https://docs.python.org/3/library/tarfile.html#tarfile-extraction-filter`
- GitHub workflow runs API: `https://docs.github.com/en/rest/actions/workflow-runs`
- GitHub Pages publishing: `https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site`
- Packwiz bootstrap `v0.0.3`: `https://github.com/packwiz/packwiz-installer-bootstrap/releases/tag/v0.0.3`
- Packwiz installer `v0.5.14`: `https://github.com/packwiz/packwiz-installer/releases/tag/v0.5.14`
