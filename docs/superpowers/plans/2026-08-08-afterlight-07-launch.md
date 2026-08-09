# AFTERLIGHT Plan 07: VPS, Distribution, and Release Candidate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a reproducible VPS deployment, fail-closed maintenance tooling, friend installation assets, and a fully automated `0.9.0-rc.1` release candidate. Version `1.0.0` remains blocked until Shane completes the manual acceptance matrix.

**Architecture:** Docker Compose runs exact OCI-index digests for `itzg/minecraft-server` and `itzg/mc-backup` against one bind-mounted `/data` tree. Operator scripts accept only an immutable 40-character Git SHA whose exact `main` push workflow succeeded, verify mutable Pages only for byte parity, then stage production from raw full-SHA URLs with two checksum-pinned Packwiz installer JARs. Python 3.12 helpers authenticate archives, release metadata, and pack-managed file transactions. Every maintenance command shares one host lock, preserves evidence on failure, and never restores world data automatically after an update failure. Prism plus Packwiz is the only complete supported client lane. AutoModpack remains disabled because the complete client payload is not redistributable.

**Tech Stack:** Docker Compose, digest-pinned itzg images, Java 21, NeoForge 21.1.248, Packwiz installer bootstrap 0.0.3, Packwiz installer 0.5.14, Python 3.12 standard library, Bash, GitHub Actions, GitHub Pages, Chunky, and RCON.

## Global Constraints

- Minecraft is `1.21.1`; NeoForge is `21.1.248`; the container Java major is exactly 21.
- Default server memory is `INIT_MEMORY=4G`, `MAX_MEMORY=10G`, and `mem_limit: 13G`.
- Launch support is `linux/amd64`. OCI support for `linux/arm64` is recorded, but pack support remains unclaimed until its complete live matrix passes.
- No server address, credentials, RCON password, tokens, secrets, or generated RCON client files enter git or backup archives.
- `main` is the stable channel and `dev` is the working branch. Production staging uses raw full-SHA URLs, never mutable branch URLs.
- Pages is a parity gate only. The production container never sets `PACKWIZ_URL` and never downloads pack files at startup.
- Current mrpack and CurseForge exports contain embedded third-party JARs and remain friends-only.
- AutoModpack is disabled. It is neither a launch dependency nor a manual acceptance item while any exact artifact lacks affirmative redistribution permission.
- `${DATA_DIR}`, `${BACKUP_DIR}`, `${STATE_DIR}`, `${QUARANTINE_DIR}`, and `${SECRETS_DIR}` must be canonical, non-symlinked, pairwise nonnested paths. Data and quarantine must share a local filesystem for atomic rename.
- Every operator script uses `#!/usr/bin/env bash`, `set -Eeuo pipefail`, `umask 077`, `LC_ALL=C`, and the same Linux `flock` file.
- Common exit codes are `0` success, `2` usage or configuration, `3` live precondition, `4` trust or integrity, `5` operational failure, and `6` update stopped with an explicit rollback required.
- World mutation, update, rollback, recovery, and Chunky start or continue require a protected backup first. Protected backups are never pruned automatically.
- Update health failure stops the server, preserves all evidence, and prints the exact rollback command. It never restores world data automatically.
- Release claims require two clean gauntlet runs from separate fresh worktrees plus the manual items explicitly listed in Task 7.

---

### Task 1: Release Trust and Compose Foundation

**Files:**
- Create: `server/docker-compose.yml`
- Create: `server/.env.example`
- Create: `server/server.properties.example`
- Create: `server/README.md`
- Create: `server/scripts/lib.sh`
- Create: `server/scripts/release_gate.py`
- Create: `server/tests/test_release_gate.py`
- Create: `server/tests/test_compose_contract.py`
- Modify: `.gitignore`
- Modify: `.packwizignore`

**Interfaces:**
- `release_gate.py accept --repo OWNER/REPO --sha SHA --pages-url URL [--historical]` prints one authenticated JSON receipt and exits `0`, or exits `4` without a partial receipt.
- `lib.sh` exposes fixed Compose invocation, canonical path checks, dependency checks, the shared `flock`, HTTPS download with SHA-256 verification, RCON execution, and guarded temporary-directory cleanup.

- [ ] Write failing tests for malformed SHAs, wrong repository refs, PR-only success, workflow-dispatch-only success, failed newest reruns, duplicate check names, malformed API JSON, rate limits, Pages lag, and a `main` ref that moves during staging.
- [ ] Implement the GitHub acceptance source as `GET /actions/workflows/pack-ci.yml/runs` filtered to `branch=main`, `event=push`, `status=completed`, and exact `head_sha`. Send `Accept: application/vnd.github+json` and `X-GitHub-Api-Version: 2026-03-10`. Require the selected run and its exact attempt's `verify-and-export` job to be completed successfully. Check runs may corroborate but never establish acceptance.
- [ ] Compare Pages `pack.toml` and `index.toml` byte-for-byte with raw full-SHA files using a cache-busting query. Install Pages into scratch only to verify every indexed hash, then discard it. Emit production URLs rooted at `https://raw.githubusercontent.com/OWNER/REPO/SHA/`.
- [ ] Pin `itzg/minecraft-server:2026.8.0-java21@sha256:b76b9298a2a60d5cf9d223e009cd0b8ad620c2080abd83f9a1fa5084fa87f9ab` and `itzg/mc-backup:2026.8.0@sha256:ae54d88d1a5dfbc185f1f94e50bb2e9b68484719013f4f21c573422dd4950f32`.
- [ ] Do not set Compose `platform`. Document `linux/amd64` as the supported launch architecture and retain the native `linux/arm64` pull as a deferred matrix item.
- [ ] Configure `EULA=TRUE`, `TYPE=NEOFORGE`, `VERSION=1.21.1`, `NEOFORGE_VERSION=21.1.248`, `NEOFORGE_INSTALLER=/data/.afterlight/cache/neoforge-21.1.248-installer.jar`, `INIT_MEMORY=4G`, `MAX_MEMORY=10G`, `STOP_DURATION=90`, `UMASK=0077`, `ENABLE_RCON=TRUE`, and `RCON_PASSWORD_FILE=/run/secrets/rcon_password`.
- [ ] Publish only Minecraft TCP `25565` and Simple Voice Chat UDP `24454`. Never publish RCON `25575`.
- [ ] Use long bind syntax with `create_host_path: false`. Mount `/data` read-write in Minecraft, `/data` read-only in the one-shot backup service, and `/backups` read-write in the backup service. Set `stop_grace_period: 2m`.
- [ ] Use a Compose secret outside `/data` for RCON. Never source `.env` from shell, never use Bash `UID`, and unset conflicting Compose interpolation variables before every fixed invocation.
- [ ] Validate exact image references, mounts, healthcheck, secrets, ports, memory, stop timing, and absence of `PACKWIZ_URL` through both source tests and `docker compose config` when Docker is available.
- [ ] Commit only after the focused tests pass and a no-secret scan is clean.

### Task 2: Authenticated Backup Bundles and Archive Guard

**Files:**
- Create: `server/scripts/archive_guard.py`
- Create: `server/scripts/backup.sh`
- Create: `server/tests/test_archive_guard.py`
- Create: `server/tests/test_backup_contract.py`
- Create: `server/tests/fixtures/archives/`
- Modify: `server/README.md`

**Interfaces:**
- `archive_guard.py verify ARCHIVE --release RECEIPT --ledger LEDGER` prints exact member count, expanded bytes, and SHA-256 only after full validation.
- `archive_guard.py extract ARCHIVE EMPTY_DESTINATION` accepts only a fresh empty sibling directory and uses Python 3.12 `tarfile` data filtering after independent member validation.
- `backup.sh --class scheduled|protected --reason TOKEN [--offline] [--dry-run]` publishes one immutable bundle directory only after every check passes.

- [ ] Write failing fixtures for absolute paths, parent traversal, symlinks, hardlinks, devices, FIFOs, duplicate names, control characters, missing `world/level.dat`, secret files, unexpected JARs, decompression-bomb metadata, partial gzip, bad checksums, and expanded-size or member-count overflow.
- [ ] Accept only regular files and directories. Reject `.rcon-cli.env`, `.rcon-cli.yaml`, `server.properties`, secrets, links, devices, duplicate members, control characters, absolute paths, and `..` traversal before extraction.
- [ ] Require `world/level.dat`, an authenticated release receipt, the exact managed-file ledger, bounded member count, bounded expanded bytes, archive SHA-256, and a completion marker.
- [ ] Run the pinned backup image only into `incoming/<run-id>`, set `POST_BACKUP_SCRIPT='exit "$1"'`, require the image's `.mc-backup-lock`, and independently validate output before atomic publication.
- [ ] For online backup, require healthy RCON, issue `save-off`, `save-all flush`, and always attempt `save-on` from the host trap. For offline backup, require the Minecraft container to be fully stopped.
- [ ] Store `scheduled` and `protected` bundles separately. Prune scheduled bundles only, and never infer a restore target from "latest".
- [ ] Prove failure behavior for every RCON command, tar exits 1 and 2, killed backup, lock contention, partial output, secret inclusion, and retention attempting to touch protected data.
- [ ] Document the encrypted offsite copy requirement. Local `/backups` alone is not empty-host recovery.
- [ ] Commit only after focused tests pass and two deterministic fixture runs produce identical validation results.

### Task 3: Transactional Pack Activation and Maintenance

**Files:**
- Create: `server/scripts/pack_activation.py`
- Create: `server/scripts/install.sh`
- Create: `server/scripts/update.sh`
- Create: `server/scripts/rollback.sh`
- Create: `server/scripts/recover.sh`
- Create: `server/tests/test_pack_activation.py`
- Create: `server/tests/test_maintenance_contract.py`
- Modify: `server/README.md`

**Interfaces:**
- `pack_activation.py stage --sha SHA --destination EMPTY_DIR --receipt RECEIPT` installs and validates exact pack-managed files and writes a NUL-delimited ledger.
- `pack_activation.py activate --candidate DIR --data DIR --state DIR` journals every managed-file mutation and changes only current or previously managed paths.
- `install.sh [--sha SHA] [--dry-run]`, `update.sh [--sha SHA] [--dry-run]`, `rollback.sh --backup BUNDLE --sha SHA --confirm BUNDLE_ID [--dry-run]`, and `recover.sh --backup BUNDLE --sha SHA --confirm BUNDLE_ID [--dry-run]` use the shared trust, backup, activation, and health interfaces.

- [ ] Write failing tests for added, changed, and removed managed files, duplicate Packwiz locations, stale mod removal, untracked runtime file preservation, interrupted journal steps, symlinked paths, missing bind sources, nonempty recovery targets including one dotfile, low disk, wrong recorded SHA, missing ledger, setup failure, and health failure.
- [ ] Permit only indexed files beneath `config`, `global_packs`, `kubejs`, and `mods`. Reject noncanonical paths, links, hardlinks, duplicate locations, unexpected roots, and unindexed files in the candidate.
- [ ] Pin bootstrap `v0.0.3` SHA-256 `a8fbb24dc604278e97f4688e82d3d91a318b98efc08d5dbfcbcbcab6443d116c`, 98,989 bytes, and installer `v0.5.14` SHA-256 `c9f646908d340d84773948a9a7d98bc1dae250d35e1016dc6e2b8459760b5598`, 4,378,828 bytes.
- [ ] Invoke `java -jar packwiz-installer-bootstrap.jar --bootstrap-no-update --bootstrap-main-jar /trusted/packwiz-installer-v0.5.14.jar -g -s server RAW_FULL_SHA_PACK_TOML` in every server consumer. The client defaults to side `client` and must not receive `-s server`.
- [ ] Authenticate NeoForge installer `21.1.248` with SHA-256 `68eeab77059ba53df1812f1afa5bf530ab2566a3cdcd5f924aa6e71be42e410c` before cache publication or setup.
- [ ] `install.sh` requires absent or completely empty data, creates a secret without printing it, stages and validates into a sibling candidate, runs `SETUP_ONLY=true`, atomically publishes, force-creates the container, and verifies health.
- [ ] `update.sh` stages before downtime, rejects active or unknown Chunky work, rechecks current `main`, creates a protected pre-update backup, stops gracefully, activates only managed files, and uses `docker compose up -d --no-deps --force-recreate minecraft`.
- [ ] On update health failure, stop the server, preserve candidate, journal, backup, and logs, return exit `6`, and print one exact `rollback.sh` command. Do not mutate world data again.
- [ ] `rollback.sh` requires an explicit bundle ID and matching recorded SHA, creates a protected backup of current state, validates a sibling restore tree, quarantines current data, atomically installs the candidate, force-recreates, and never deletes quarantine.
- [ ] `recover.sh` requires an empty data path including dotfiles, validates the offsite-retrieved bundle and historical CI receipt, creates a fresh RCON secret, restores to a sibling candidate, overlays the exact Packwiz SHA, rebuilds runtime files, atomically publishes, and verifies health.
- [ ] Explicitly forbid upstream `restore-backup` and `restore-tar-backup` helpers in source tests and operator documentation.
- [ ] Commit only after focused adversarial tests pass and every shell wrapper passes `bash -n`.

### Task 4: Health, Chunky, and Live-Host Contracts

**Files:**
- Create: `server/scripts/healthcheck.sh`
- Create: `server/scripts/pregen.sh`
- Create: `server/tests/test_health_contract.py`
- Create: `server/tests/test_pregen_contract.py`
- Modify: `server/README.md`

**Interfaces:**
- `healthcheck.sh [--timeout 720] [--expect-sha SHA]` prints exactly one `HEALTH: OK` only after every deep check succeeds.
- `pregen.sh start|status|pause|continue|cancel` uses RCON through `lib.sh` and the shared maintenance lock.

- [ ] Make health verify one container ID, running state, exact mounted data source, exact pinned image reference, required environment, no `PACKWIZ_URL`, container health, `mc-health`, RCON `list`, Java major 21, NeoForge version, current-start readiness log, active release SHA, and managed-ledger digest.
- [ ] Reject stale readiness lines by binding success to the current container start and expected SHA.
- [ ] Implement Chunky `start` with explicit world, `circle|square` shape, integer center, and radius. Default radius is 10,000 and documented maximum is 20,000. Do not implement trim.
- [ ] Use exact commands `chunky start`, `chunky progress`, `chunky pause [world]`, `chunky continue [world]`, and `chunky cancel [world]`.
- [ ] Require a protected backup before `start` and `continue`. Update, rollback, and recovery fail closed while Chunky is active or its state cannot be classified.
- [ ] Add source and fake-command tests for healthy, unhealthy, stale, duplicate-container, wrong-mount, wrong-image, wrong-Java, wrong-SHA, RCON failure, and every conservative Chunky state.
- [ ] Record live-host-only checks separately: firewall, `flock`, same-filesystem rename, two-minute graceful stop, memory headroom, host reboot, backup throughput, disk headroom, native image pull, arm64 pack boot, whitelist, voice UDP, and encrypted empty-host recovery.
- [ ] Commit only after focused tests pass. Never label a fake-command test as a live Docker or live-host proof.

### Task 5: Distribution and Friend Onboarding

**Files:**
- Modify: `tools/build-prism-instance.sh`
- Modify: `docs/INSTALL.md`
- Create: `docs/TROUBLESHOOTING.md`
- Create: `docs/UPDATE_POLICY.md`
- Create: `server/automodpack/README.md`
- Create: `server/automodpack/licensing-inventory.json`
- Create: `tools/tests/test_distribution.py`

- [ ] Require an explicit accepted release SHA and HTTPS Pages pack URL. Run `release_gate.py`, verify both Packwiz JAR hashes, and embed only those two installer JARs.
- [ ] Set Prism prelaunch to `java -jar packwiz-installer-bootstrap.jar --bootstrap-no-update --bootstrap-main-jar packwiz-installer.jar -g ACCEPTED_PAGES_PACK_TOML`. The installer defaults to side `client`; do not pass `-s server`. Build in a fresh temporary directory and inspect the final ZIP entry-by-entry.
- [ ] Reject stale archive entries, path traversal, links, unexpected JARs, mutable release URLs, embedded mod JARs, secrets, and a pack URL whose Pages bytes do not match the accepted SHA.
- [ ] Record the Prism ZIP SHA-256 and exact release receipt. Verify import structure without claiming client launch success.
- [ ] Keep Prism plus Packwiz as the only complete supported installation lane. Document RAM allocation, Java 21, import, launch, update, recovery, voice chat, log collection, common crashes, and clean reinstall without deleting saves.
- [ ] Commit the exact AutoModpack licensing inventory: 13 denied, 13 manual-review, and 7 unknown client entries. Do not add, configure, host, test, or advertise AutoModpack while any blocker remains.
- [ ] Document mrpack and CurseForge ZIP as optional friends-only lanes because they can contain embedded third-party JARs.
- [ ] Commit only after distribution tests pass and archive inspection proves that no mod JAR or secret is embedded.

### Task 6: CI and Reproducible Gauntlet

**Files:**
- Modify: `pack.toml`
- Modify: `index.toml`
- Modify: `.github/workflows/pack-ci.yml`
- Create: `tools/gauntlet.sh`
- Create: `tools/tests/test_gauntlet_contract.py`
- Create: `docs/releases/v0.9.0-rc.1.md`
- Create: `docs/releases/v0.9.0-rc.1-gauntlet.md`

- [ ] Set pack version to `0.9.0-rc.1`, source `tools/versions.env`, run Packwiz refresh, and commit `pack.toml`, `index.toml`, and any Packwiz-managed metadata together.
- [ ] Extend CI with Python unit tests, static and runtime quest validation, `verify-pack.sh`, shell syntax, forbidden U+2014 scan, server boot, exports, distribution inspection, archive fixture tests, secret scan, and final git cleanliness.
- [ ] Upload logs only from the current failed run. Remove stale evidence before execution and include every relevant log and command transcript on failure.
- [ ] Require `tools/gauntlet.sh` to run from a clean detached full-SHA worktree and record SHA, operating system, architecture, Java, Go, Packwiz, Python, Docker, and Compose versions.
- [ ] Run unit tests, static quest validation, manifest verification, server boot, runtime quest validation, KubeJS error checks, exports, Prism build, archive inspection, secret scan, forbidden-punctuation scan, shell syntax, and final git cleanliness. Capture every command and exit code.
- [ ] Ensure every gauntlet run starts from a fresh `server-test` runtime so the second run cannot reuse the first run's boot, nonce, logs, installed files, or generated evidence.
- [ ] Run the full gauntlet twice from two separate clean worktrees. Record exact SHA-256 values and elapsed time for both runs.
- [ ] Push `dev`, require the exact-SHA `pack-ci` workflow run and job to succeed, fast-forward `main`, require the exact main push run to succeed, and verify Pages parity byte-for-byte.
- [ ] Commit the gauntlet report only with exact command output and explicit deferred live-host or client checks.

### Task 7: Skeptical Review, Release Candidate, and Handoff

**Files:**
- Modify: `docs/HANDOFF.md`
- Modify: `docs/releases/v0.9.0-rc.1.md`
- Modify: `docs/releases/v0.9.0-rc.1-gauntlet.md`

- [ ] Run a whole-project skeptical review against the design spec and all seven plans. Fix every Critical and Important finding, rerun focused checks, then rerun the complete gauntlet twice.
- [ ] Verify branch history, commit trailers, no JARs or secrets in git, no U+2014 in tracked authored content, exact release version, exact Pages parity, and exact accepted GitHub workflow run.
- [ ] Create immutable annotated tag `v0.9.0-rc.1` only after automated checks and remote parity are green. Do not create `v1.0.0` in this autonomous run.
- [ ] Leave these manual acceptance items explicit for Shane: Prism import and sub-three-minute title screen; new-world quest UI and theme; chapters 1 through 8 playthrough; every Certification and hard gate; released-client dedicated-server join; two-user voice test; whitelist and firewall; update drill; induced update failure plus explicit rollback; and encrypted offsite empty-host restore on a replacement host.
- [ ] Add `linux/arm64` support only after native pull, Java 21, NeoForge setup, complete pack boot, Chunky smoke, and gameplay checks pass on that architecture.
- [ ] Promote to `1.0.0` only after every manual acceptance item is recorded as passed against the exact release candidate lineage.
