# Plan 07 Architecture Audit

Date: 2026-08-08

Status: design gate corrected after follow-up contradiction review. No Docker, VPS, backup, recovery, CI, Pages, Prism, or release behavior is claimed by this document.

## Scope

The launch architecture was reviewed before implementation against the exact current itzg image manifests, Packwiz installer release bytes, NeoForge installer checksum, Docker Compose behavior, GitHub Actions APIs, GitHub Pages mutability, RCON secret handling, Chunky operations, Python archive extraction safety, nested Linux lock behavior, rollback channel safety, and release-evidence ordering.

The initial review found nine Critical and nine Important design gaps. A completed follow-up contradiction review found seven cross-task defects in the rewritten plan: acceptance self-deadlock, unhandled Packwiz installer state, an incorrect release-candidate manual gate, nested lock reacquisition, backup exclusions that were not part of resolved Compose, client-unsafe rollback, and evidence self-reference. A subsequent pinned-source check found that online and offline backup enter different RCON and image-lock branches. The corrected plan resolves all of these findings as one executable release sequence. Implementation still requires test-first development, whole-project skeptical review, two accepted clean gauntlet runs, exact-SHA CI and Pages evidence, and the deferred live-host matrix.

## Exact External Pins

| Component | Exact reference | Additional evidence |
|---|---|---|
| Minecraft server image | `itzg/minecraft-server:2026.8.0-java21@sha256:b76b9298a2a60d5cf9d223e009cd0b8ad620c2080abd83f9a1fa5084fa87f9ab` | Source revision `1e2d375dba72a0730365c29dd5f1990f9764da5a` |
| Backup image | `itzg/mc-backup:2026.8.0@sha256:ae54d88d1a5dfbc185f1f94e50bb2e9b68484719013f4f21c573422dd4950f32` | Source revision `438b97f9d520b93a29f586f33dbd29a3adb372ca` |
| Packwiz bootstrap | `v0.0.3` | SHA-256 `a8fbb24dc604278e97f4688e82d3d91a318b98efc08d5dbfcbcbcab6443d116c`, 98,989 bytes |
| Packwiz installer | `v0.5.14` | SHA-256 `c9f646908d340d84773948a9a7d98bc1dae250d35e1016dc6e2b8459760b5598`, 4,378,828 bytes |
| NeoForge installer | `21.1.248` | SHA-256 `68eeab77059ba53df1812f1afa5bf530ab2566a3cdcd5f924aa6e71be42e410c` |

The OCI index digests were verified against registry response bodies. Both server-image child manifests report Java `jdk-21.0.11+10`. Native image children exist for `linux/amd64` and `linux/arm64`, but only `linux/amd64` is launch-supported until the complete arm64 pack matrix passes.

## Acceptance and Release Subjects

The corrected trust model separates pre-acceptance checks from release acceptance:

1. Pre-acceptance checks validate the checked-out full SHA, immutable inputs, tests, server boot, exports, archive behavior, and distribution fixtures. They do not require current `main`, current Pages, `release_gate.py accept`, or a final Prism release archive.
2. The `pack-ci.yml` `verify-and-export` job is pre-acceptance only. The workflow run whose completed success is required for acceptance must never invoke accepted mode, wait for its own run, or depend on a job that does so.
3. Whole-project skeptical review runs after implementation and pre-acceptance checks. Every Critical and Important finding is fixed before the final implementation commit is frozen as tested subject SHA `S`.
4. Exact `S` is pushed through `dev`, then promoted unchanged to `main`. Acceptance waits for the exact `S` `main` push workflow and its exact job attempt to complete successfully, followed by the exact `S` Pages deployment and byte parity.
5. Only after those remote events complete may an external caller run `release_gate.py accept` for `S`.
6. Two full release gauntlets run at `S` from separate fresh worktrees. Each gauntlet independently includes accepted-mode release gating, clean client and server installs, and the final Prism build.
7. Any required implementation fix invalidates `S`. The process returns to skeptical review, freezes a new subject, promotes it, and starts both accepted gauntlets again.

Accepted mode resolves one exact 40-character lowercase Git SHA, requires that SHA to equal current remote `main`, selects only a completed successful `push` run with `head_branch=main` and exact `head_sha`, authenticates the exact run attempt's `verify-and-export` job, and rejects a selected run whose ID equals the caller's `GITHUB_RUN_ID`. Check names alone never establish acceptance because duplicate names can exist for one SHA.

Pages remains a mutable parity gate. Accepted mode compares public `pack.toml` and `index.toml` byte-for-byte with immutable raw full-SHA files, performs clean pinned-bootstrap installs, and stages production only from raw full-SHA URLs. Historical mode can authenticate an earlier completed `main` workflow and immutable raw bytes for backup, rollback preparation, or recovery, but historical evidence alone never authorizes reopening against a different current Pages channel.

## Installer and Candidate Model

Every server consumer verifies both Packwiz JAR hashes and runs:

```sh
java -jar packwiz-installer-bootstrap.jar \
  --bootstrap-no-update \
  --bootstrap-main-jar /trusted/packwiz-installer-v0.5.14.jar \
  -g -s server \
  "https://raw.githubusercontent.com/OWNER/REPO/SHA/pack.toml"
```

Verifying only bootstrap `v0.0.3` is insufficient because its default behavior downloads a mutable latest main installer without an independent digest. The server invocation includes `-s server`. Prism omits the side flag because installed Packwiz installer `v0.5.14` defaults to `client`; its prelaunch still includes `-g` for noninteractive progress.

Packwiz installer `v0.5.14` writes a root `packwiz.json`. Server staging requires exactly one regular file at that path, parses and validates its installer-state structure and paths, records its SHA-256 in the candidate receipt, and moves it into `${STATE_DIR}/candidates/<candidate-id>/packwiz.json` before candidate closure. Installer provenance never enters the managed ledger or activated `/data`.

After that move, every remaining candidate file must be indexed beneath `config`, `global_packs`, `kubejs`, or `mods`. Candidate closure rejects every other unindexed file, unexpected root, noncanonical path, duplicate location, link, or hardlink. Activation may add or replace current managed files and remove only paths from the prior NUL-delimited ledger. Untracked runtime state is preserved, and every mutation is journaled while the server is stopped.

## Data, Secrets, and Backup Input

- The Minecraft service receives one read-write `/data` bind.
- The backup service receives `/data` read-only and `/backups` read-write.
- Bind sources use long syntax with `create_host_path: false`.
- Data, backups, state, quarantine, and secrets are canonical, pairwise nonnested paths.
- Data and quarantine share a local filesystem so publication and quarantine use atomic rename.
- RCON uses a Compose secret outside `/data`. Port `25575` is never published.
- Recovery regenerates operational properties and a fresh RCON secret.

Task 1 creates reviewed source file `server/backup-excludes.txt`, mounts it read-only at `/etc/afterlight-backup-excludes.txt`, sets `EXCLUDES=""` to neutralize the image default, and sets `EXCLUDES_FILE` to that exact path in the backup service. The file excludes `.rcon-cli.env`, `.rcon-cli.yaml`, `server.properties`, the host-created `.paused` marker, every JAR, cache directories, logs, and known transient files before the backup image creates an archive. There is no second inline exclusion authority.

Task 2 tests inspect canonical `docker compose config --format json` to prove the exact resolved mount and environment. Successful backup tests inspect archive membership to prove every reviewed class, including `.paused`, is absent at any depth. The archive guard remains a second boundary and rejects any forbidden member injected despite the exclusion file.

Pinned `docker-mc-backup` source has two materially different execution paths. Without `/data/.paused`, the normal branch loads RCON, performs a readiness `save-on`, acquires `${BACKUP_DIR}/.mc-backup-lock`, runs `save-off`, optional `save-all flush` and sync, creates the archive, and restores `save-on` with its own exit trap. The host wrapper validates online prerequisites but does not duplicate that RCON mutation sequence.

The pinned image enters its offline path only when `/data/.paused` exists. That paused branch bypasses both RCON and `.mc-backup-lock`. Offline backup therefore requires Minecraft and the scheduled sidecar to be stopped, retains the shared inherited host operations lock as its serialization authority, refuses a preexisting marker, creates `.paused` only after stop verification, and trap-cleans only the marker created by that invocation on every exit path. Online and offline tests assert their separate branch configuration and postconditions.

Each accepted bundle includes a checksum, authenticated release receipt, exact managed ledger, exact `pack.toml` and `index.toml` snapshots with SHA-256 values, and a completion marker. Scheduled and protected backups have separate retention classes, protected bundles are never pruned automatically, and upstream `restore-backup` and `restore-tar-backup` helpers remain forbidden. Empty-host recovery requires an encrypted copy stored independently from the VPS.

## Lock Model

Every top-level mutating command opens and acquires `${STATE_DIR}/ops.lock` once, keeps that one Linux file descriptor open for the full operation, and exports its number as `AFTERLIGHT_OPS_LOCK_FD`. A nested maintenance command receives the inherited open descriptor and uses an internal `--lock-held` contract. It validates that the descriptor is numeric, open, and points through Linux `/proc/self/fd` to the canonical operations lock, then requires nonblocking `flock -n` on that same descriptor to succeed. The inherited locked open-file description succeeds without reacquisition; a separately opened descriptor fails while the parent lock is held.

Direct `backup.sh` calls acquire the operations lock normally. Backup calls nested beneath update, rollback, or Chunky reuse the parent's descriptor. Tests cover update-to-backup, rollback-to-backup, and pregen-to-backup execution, assert that the same descriptor remains held, and fail forged or separately opened descriptors. The normal online image branch adds `${BACKUP_DIR}/.mc-backup-lock` as a separate archive-serialization lock with the existing fixed acquisition order. The offline paused branch has no image lock and remains serialized by the inherited host operations descriptor. No nested path may reacquire the operations lock and self-deadlock.

## Update and Rollback Model

An update stages before downtime, closes maintenance, takes a protected backup through the inherited lock, and activates only validated pack-managed files. Packwiz updates pack-managed paths in `/data`; the prohibition is against automatic world restore, world deletion, or rollback.

An update health failure stops Minecraft, leaves maintenance closed, exits with code `6`, preserves logs, candidate files, Packwiz provenance, backup, ledger, journal, quarantine state, and receipts, and prints one exact `rollback.sh prepare` command. It never restores world data automatically.

Rollback is a truthful two-phase operation:

1. `rollback.sh prepare` authenticates the named bundle's historical SHA `H`, creates a protected backup of the failed current state, validates and installs the historical restore through a sibling candidate and same-filesystem quarantine, and leaves Minecraft stopped with maintenance closed.
2. The operator creates and reviews a normal rollback commit `R` through `dev` and `main`. Maintenance tooling never commits, reverts, pushes, mutates branches or tags, or calls a GitHub write API.
3. `rollback.sh activate` requires `R` to be current accepted `main`, requires raw `R` `pack.toml` and `index.toml` to be byte-identical to the authenticated historical snapshots for `H`, and requires Pages to match `R`.
4. Activation stages from raw `R`, starts the restored server, verifies health, and preserves receipts for both `H` and `R` while the announced maintenance window remains in effect.
5. A released-client dedicated-server join remains manual. Shane explicitly reopens production only after that join passes. Neither rollback phase declares or performs production reopening.

A historical empty-host recovery intended to become production follows the same current rollback-commit, Pages-parity, and manual-join gate. Restoring a server alone is not evidence that the mutable client channel is safe.

## Distribution and Release Boundary

Prism plus Packwiz remains the only complete supported client lane. A release Prism build requires an already accepted SHA and current Pages parity, so CI and pre-acceptance checks use fixture or immutable-local builder tests instead of requiring the final archive.

AutoModpack is disabled because the licensing inventory currently contains 13 denied, 13 manual-review, and 7 unknown client entries. The release candidate does not add, host, test, or advertise AutoModpack. The mrpack and CurseForge ZIP remain optional friends-only lanes because they can contain embedded third-party JARs.

Two accepted full gauntlets at `S` plus an explicit passed, failed, or deferred record for every manual item permit the correctly labeled `v0.9.0-rc.1` prerelease. Shane's manual matrix gates only `1.0.0` and any claim that production is open. Automated evidence must never convert a deferred manual check into a pass.

## Evidence and Tag Model

After both accepted full gauntlets at `S`, create evidence SHA `E` as the direct child of `S`. The only permitted changed paths are:

- `docs/releases/v0.9.0-rc.1.md`
- `docs/releases/v0.9.0-rc.1-gauntlet.md`

The committed reports record `S`, its accepted workflow and Pages receipt, both full gauntlet receipts, release Prism hashes, exact commands, and explicit manual deferrals. They state that `E` acceptance occurs later and do not claim an `E` workflow receipt, `E` Pages deployment receipt, or final `E` parity evidence.

Before promotion, verify that `E` has parent exactly `S` and that `git diff S..E` contains no executable, manifest, config, quest, pack, workflow, generated Packwiz state, or path outside the two evidence documents. Promote exact `E` through `dev` and `main` without creating another commit. Require exact completed successful `E` workflows on both branches, followed by exact `E` Pages deployment and parity on `main`.

The immutable annotated tag `v0.9.0-rc.1` points to `E`. Its tag message and the GitHub release metadata hold the final `E` workflow run, attempt, and job identifiers, Pages deployment identifier, parity hashes, and acceptance receipt digest. This places evidence that necessarily occurs after `E` in immutable release metadata without moving or recreating the tag.

## Executable Release Sequence

1. Implement Tasks 1 through 5 and the Task 6 CI and gauntlet contracts.
2. Run all pre-acceptance checks without requiring accepted `main`, current Pages, or a release Prism archive.
3. Run whole-project skeptical review, fix every Critical and Important finding, rerun focused checks, and rerun the full pre-acceptance suite.
4. Freeze the final implementation commit as `S`, push exact `S` to `dev`, and require exact `S` dev CI success.
5. Promote exact `S` to `main`, wait for exact completed successful `S` main CI and Pages deployment, and accept parity externally.
6. Run two clean full release gauntlets at `S`, each including accepted release gating and the final Prism build.
7. Record all evidence and manual deferrals in direct child `E`, with no change outside the two named evidence documents.
8. Promote exact `E` through `dev` and `main`, require exact `E` CI and Pages parity, then create the annotated tag at `E` with final remote evidence in the tag and release metadata.
9. Treat any later implementation change as a new subject and restart from skeptical review. Never patch between the final accepted gauntlets and the tag.

## Deferred Live Evidence

These checks cannot be truthfully completed by plan text or a Mac-only authoring session:

- VPS firewall exposes only Minecraft TCP and voice UDP.
- Host filesystem provides reliable `flock`, inherited descriptor behavior, and same-filesystem atomic rename.
- Graceful stop finishes inside two minutes without exit 137.
- Ten-gigabyte heap remains below the 13 GB container limit under gameplay and Chunky load.
- Backup throughput, restore throughput, free-space checks, and quarantine capacity fit the real world size.
- Host reboot restores the Compose stack and backup schedule without creating a new world.
- Two released clients join, whitelist works, and voice chat works over UDP.
- Installed Chunky RCON output is classified conservatively for active, paused, complete, and unknown states.
- The full pack boots and plays on arm64.
- An encrypted offsite bundle restores onto a genuinely empty replacement host.
- A real update failure remains closed and is followed by explicit two-phase rollback without post-backup player writes.
- A released client joins the accepted rollback release before production reopening.

## Primary References

- Docker Registry API: `https://distribution.github.io/distribution/spec/api/`
- itzg server documentation: `https://docker-minecraft-server.readthedocs.io/`
- Docker Compose services: `https://docs.docker.com/reference/compose-file/services/`
- Python tar extraction filters: `https://docs.python.org/3/library/tarfile.html#tarfile-extraction-filter`
- GitHub workflow runs API: `https://docs.github.com/en/rest/actions/workflow-runs`
- GitHub Pages publishing: `https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site`
- Packwiz bootstrap `v0.0.3`: `https://github.com/packwiz/packwiz-installer-bootstrap/releases/tag/v0.0.3`
- Packwiz installer `v0.5.14`: `https://github.com/packwiz/packwiz-installer/releases/tag/v0.5.14`
- Pinned backup branch logic: `https://github.com/itzg/docker-mc-backup/blob/2026.8.0/scripts/opt/backup-loop.sh`
