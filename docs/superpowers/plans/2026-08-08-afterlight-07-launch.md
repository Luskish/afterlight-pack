# AFTERLIGHT Plan 07: VPS, Distribution, and Release Candidate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a reproducible VPS deployment, fail-closed maintenance tooling, friend installation assets, and a fully evidenced `0.9.0-rc.1` release candidate. Version `1.0.0` remains blocked until Shane completes the manual acceptance matrix.

**Architecture:** Docker Compose runs exact OCI-index digests for `itzg/minecraft-server` and `itzg/mc-backup` against one bind-mounted `/data` tree. Pre-acceptance checks validate immutable inputs without requiring accepted `main`, current Pages, or a release Prism build; after skeptical review and all fixes, the final implementation commit becomes release subject SHA `S`, exact `S` is promoted to `main`, its completed successful `main` push workflow and Pages parity are accepted, and two fresh full release gauntlets run at `S`. The direct child evidence SHA `E` may change only the named release evidence documents, is promoted unchanged through `dev` and `main`, receives its own exact CI and Pages acceptance, and is tagged without making its committed report claim later evidence about itself.

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
- Every operator script uses `#!/usr/bin/env bash`, `set -Eeuo pipefail`, `umask 077`, `LC_ALL=C`, and the same Linux operations lock at `${STATE_DIR}/ops.lock`.
- A top-level mutating command acquires the operations lock once, keeps one file descriptor open for its full lifetime, and exports that inherited descriptor to nested maintenance commands. An internal `--lock-held` path validates and reuses that descriptor instead of reacquiring the lock.
- Common exit codes are `0` success, `2` usage or configuration, `3` live precondition, `4` trust or integrity, `5` operational failure, and `6` update stopped with an explicit rollback required.
- World mutation, update, rollback, recovery, and Chunky start or continue require a protected backup first. Protected backups are never pruned automatically.
- Update health failure stops the server, leaves maintenance closed, preserves all evidence, and prints the exact rollback command. It never restores world data automatically.
- Pre-acceptance CI on `dev` or `main` must not require an already accepted `main` SHA, current Pages parity, `release_gate.py accept`, or a release Prism archive. The workflow run whose success establishes acceptance must never invoke accepted mode, gate itself, or wait for itself.
- Freeze release subject SHA `S` only after the whole-project skeptical review and every resulting fix. Promote exact `S` to `main`, accept its completed successful exact-SHA `main` push workflow and Pages parity, then run two clean full release gauntlets from separate fresh worktrees at `S`, each including `release_gate.py accept` and the release Prism build.
- Two accepted full gauntlets at `S` plus an explicit record of every deferred manual item permit `v0.9.0-rc.1`. Shane's manual matrix gates only `1.0.0` and claims that production is open.
- Evidence SHA `E` must be the direct child of `S` and may change only `docs/releases/v0.9.0-rc.1.md` and `docs/releases/v0.9.0-rc.1-gauntlet.md`. No executable, manifest, config, quest, pack, or workflow change is permitted from `S` to `E`.

---

### Task 1: Release Trust and Compose Foundation

**Files:**
- Create: `server/docker-compose.yml`
- Create: `server/.env.example`
- Create: `server/server.properties.example`
- Create: `server/backup-excludes.txt`
- Create: `server/README.md`
- Create: `server/scripts/lib.sh`
- Create: `server/scripts/release_gate.py`
- Create: `server/tests/test_release_gate.py`
- Create: `server/tests/test_compose_contract.py`
- Modify: `.gitignore`
- Modify: `.packwizignore`

**Interfaces:**
- `release_gate.py preaccept --repo OWNER/REPO --sha SHA` validates the immutable subject and repository inputs without requiring current `main`, Pages, a completed acceptance workflow, or Prism. It prints a mode-labeled JSON result and never prints an acceptance receipt.
- `release_gate.py accept --repo OWNER/REPO --sha SHA --pages-url URL` requires current `main`, the already completed successful exact-SHA `main` push workflow and job, the exact Pages deployment, Pages byte parity, and clean client and server installs. It prints one authenticated JSON receipt and exits `0`, or exits `4` without a partial receipt.
- `release_gate.py historical --repo OWNER/REPO --sha SHA` authenticates an earlier completed successful `main` push workflow and immutable raw release bytes for backup validation, rollback preparation, or recovery. It never treats historical evidence as permission to reopen against a different current client channel.
- `lib.sh` exposes fixed Compose invocation, canonical path checks, dependency checks, one inherited Linux operations-lock file descriptor, HTTPS download with SHA-256 verification, RCON execution, and guarded temporary-directory cleanup.

- [ ] Write failing tests for malformed SHAs, wrong repository refs, PR-only success, workflow-dispatch-only success, failed newest reruns, duplicate check names, malformed API JSON, rate limits, Pages lag, a `main` ref that moves during staging, and attempts to accept the workflow run identified by the current `GITHUB_RUN_ID`.
- [ ] Make pre-acceptance mode independent of branch acceptance and Pages. Source-test `.github/workflows/pack-ci.yml` so the required `verify-and-export` job cannot call `release_gate.py accept`, poll its own run, require a release Prism archive, or depend on a job that does so.
- [ ] Implement the GitHub acceptance source as `GET /actions/workflows/pack-ci.yml/runs` filtered to `branch=main`, `event=push`, `status=completed`, and exact `head_sha`. Send `Accept: application/vnd.github+json` and `X-GitHub-Api-Version: 2026-03-10`. Require the selected run and its exact attempt's `verify-and-export` job to be completed successfully. Check runs may corroborate but never establish acceptance.
- [ ] Make accepted mode fail immediately if the selected workflow run is the caller's own `GITHUB_RUN_ID`. Accepted mode runs only after that workflow has completed and never from a job whose success it is trying to establish.
- [ ] Compare Pages `pack.toml` and `index.toml` byte-for-byte with raw full-SHA files using a cache-busting query. Install Pages into scratch only to verify every indexed hash, then discard it. Emit production URLs rooted at `https://raw.githubusercontent.com/OWNER/REPO/SHA/`.
- [ ] Pin `itzg/minecraft-server:2026.8.0-java21@sha256:b76b9298a2a60d5cf9d223e009cd0b8ad620c2080abd83f9a1fa5084fa87f9ab` and `itzg/mc-backup:2026.8.0@sha256:ae54d88d1a5dfbc185f1f94e50bb2e9b68484719013f4f21c573422dd4950f32`.
- [ ] Do not set Compose `platform`. Document `linux/amd64` as the supported launch architecture and retain the native `linux/arm64` pull as a deferred matrix item.
- [ ] Configure `EULA=TRUE`, `TYPE=NEOFORGE`, `VERSION=1.21.1`, `NEOFORGE_VERSION=21.1.248`, `NEOFORGE_INSTALLER=/data/.afterlight/cache/neoforge-21.1.248-installer.jar`, `INIT_MEMORY=4G`, `MAX_MEMORY=10G`, `STOP_DURATION=90`, `UMASK=0077`, `ENABLE_RCON=TRUE`, and `RCON_PASSWORD_FILE=/run/secrets/rcon_password`.
- [ ] Publish only Minecraft TCP `25565` and Simple Voice Chat UDP `24454`. Never publish RCON `25575`.
- [ ] Use long bind syntax with `create_host_path: false`. Mount `/data` read-write in Minecraft, `/data` read-only in the one-shot backup service, `/backups` read-write in the backup service, and `server/backup-excludes.txt` read-only at `/etc/afterlight-backup-excludes.txt` in the backup service. Set `BACKUP_METHOD=tar`, `TAR_COMPRESS_METHOD=zstd`, `ENABLE_SAVE_ALL=true`, `ENABLE_SYNC=true`, `SKIP_LOCKING=false`, `PAUSE_IF_NO_PLAYERS=false`, `BACKUP_ON_STARTUP=false`, `EXCLUDES=""`, `EXCLUDES_FILE=/etc/afterlight-backup-excludes.txt`, and `stop_grace_period: 2m`.
- [ ] Make `server/backup-excludes.txt` the reviewed source for recursive exclusions of `.rcon-cli.env`, `.rcon-cli.yaml`, `server.properties`, the host-created `.paused` marker, every JAR, cache directories, logs, and known transient runtime files including `session.lock`, `*.tmp`, `*.part`, and `*.partial`. Do not configure a second conflicting inline exclusion list.
- [ ] Use a Compose secret outside `/data` for RCON. Never source `.env` from shell, never use Bash `UID`, and unset conflicting Compose interpolation variables before every fixed invocation.
- [ ] Define `lib.sh` lock ownership so the top-level command opens and locks `${STATE_DIR}/ops.lock` once, exports the numeric descriptor as `AFTERLIGHT_OPS_LOCK_FD`, and retains it until exit. Internal `--lock-held` use must reject a missing, closed, nonnumeric, or wrong-target descriptor through Linux `/proc/self/fd`, then require nonblocking `flock -n` on that same descriptor to succeed. The inherited locked open-file description succeeds without reacquisition; a separately opened descriptor fails while the parent lock is held.
- [ ] Validate exact image references, mounts, healthcheck, secrets, ports, memory, stop timing, `EXCLUDES_FILE`, the read-only exclusion-file bind, and absence of `PACKWIZ_URL` through both source tests and canonical `docker compose config --format json` on Linux.
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
- `backup.sh --class scheduled|protected --reason TOKEN [--offline] [--dry-run]` acquires the operations lock when called directly and publishes one immutable bundle directory only after every check passes.
- `backup.sh ... --lock-held` is internal only. It validates `AFTERLIGHT_OPS_LOCK_FD`, reuses that inherited descriptor, and never tries to acquire `${STATE_DIR}/ops.lock` again.

- [ ] Write failing fixtures for absolute paths, parent traversal, symlinks, hardlinks, devices, FIFOs, duplicate names, control characters, missing `world/level.dat`, secret files, excluded RCON files, `server.properties`, leaked `.paused`, JARs, cache members, logs, transient files, decompression-bomb metadata, partial gzip, bad checksums, and expanded-size or member-count overflow.
- [ ] Accept only regular files and directories. Reject `.rcon-cli.env`, `.rcon-cli.yaml`, `server.properties`, `.paused`, secrets, links, devices, duplicate members, control characters, absolute paths, `..` traversal, JARs, caches, logs, and transient members before extraction.
- [ ] Require `world/level.dat`, an authenticated release receipt, the exact managed-file ledger, exact `pack.toml` and `index.toml` snapshots with SHA-256 values, bounded member count, bounded expanded bytes, archive SHA-256, and a completion marker.
- [ ] Run the pinned backup image only into `incoming/<run-id>` and set `POST_BACKUP_SCRIPT='exit "$1"'`. In online mode, require absence of `/data/.paused`, enter the image's normal branch, and require its `.mc-backup-lock`. In offline mode, enter the pinned image's paused branch and explicitly do not require an image lock that this branch never acquires. Independently validate output before atomic publication in both modes.
- [ ] Prove that exclusions happen before archive validation. Tests must inspect resolved Compose JSON for the exact read-only exclusion mount and `EXCLUDES_FILE`, inspect successful archive membership to prove every reviewed class including `.paused` is absent at any depth, then inject each forbidden class directly to prove the archive guard still rejects it.
- [ ] For online backup, require healthy RCON and no `.paused` marker. Let the pinned image's normal branch exclusively perform its readiness `save-on`, acquire `.mc-backup-lock`, run `save-off`, optional `save-all flush` and sync, create the archive, and restore `save-on` with its own exit trap. The host wrapper must not duplicate that RCON mutation sequence.
- [ ] For offline backup, require Minecraft and the scheduled backup sidecar to be fully stopped while the shared host operations lock remains held. Refuse a preexisting `${DATA_DIR}/.paused`, create that regular marker only after stop verification, record its identity, and trap-clean only the marker created by this invocation on success, failure, signal, or cancellation. The marker selects the pinned image's RCON-free, image-lock-free paused branch and must be excluded from the archive.
- [ ] Test online and offline configuration separately against the pinned `scripts/opt/backup-loop.sh` branch contract. Online tests require RCON configuration, no marker, the normal save sequence, and `.mc-backup-lock`; offline tests require stopped services, the inherited host descriptor, marker creation and cleanup, no RCON call, and no assertion that `.mc-backup-lock` exists.
- [ ] Store `scheduled` and `protected` bundles separately. Prune scheduled bundles only, and never infer a restore target from "latest".
- [ ] Test direct lock acquisition and inherited `--lock-held` use. Prove a nested child receives the same open file descriptor and completes without self-deadlock, while forged or separately opened descriptors fail closed. Prove the offline paused branch remains serialized by that host descriptor even though the image lock is absent.
- [ ] Prove failure behavior for every online RCON phase, tar exits 1 and 2, killed backup, lock contention, partial output, secret inclusion, exclusion failure, preexisting or replaced `.paused`, marker cleanup after every exit path, and retention attempting to touch protected data.
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
- `pack_activation.py stage --sha SHA --destination EMPTY_DIR --state STATE_DIR --receipt RECEIPT` installs and validates exact pack-managed files, moves validated Packwiz installer provenance into state, and writes a NUL-delimited managed ledger.
- `pack_activation.py activate --candidate DIR --data DIR --state DIR` journals every managed-file mutation and changes only current or previously managed paths.
- `install.sh [--sha SHA] [--dry-run]`, `update.sh [--sha SHA] [--dry-run]`, and `recover.sh --backup BUNDLE --sha SHA --confirm BUNDLE_ID [--dry-run]` use the shared trust, backup, activation, and health interfaces.
- `rollback.sh prepare --backup BUNDLE --confirm BUNDLE_ID [--dry-run]` restores the named historical server state while maintenance remains closed. `rollback.sh activate --backup BUNDLE --rollback-sha SHA --confirm BUNDLE_ID [--dry-run]` accepts the new current rollback commit, proves channel parity, starts the restored server for health and manual released-client joining, and never declares production reopened.

- [ ] Write failing tests for added, changed, and removed managed files, duplicate Packwiz locations, stale mod removal, untracked runtime file preservation, interrupted journal steps, symlinked paths, missing bind sources, nonempty recovery targets including one dotfile, low disk, wrong recorded SHA, missing ledger, malformed or missing root `packwiz.json`, extra unindexed candidate files, setup failure, and health failure.
- [ ] Pin bootstrap `v0.0.3` SHA-256 `a8fbb24dc604278e97f4688e82d3d91a318b98efc08d5dbfcbcbcab6443d116c`, 98,989 bytes, and installer `v0.5.14` SHA-256 `c9f646908d340d84773948a9a7d98bc1dae250d35e1016dc6e2b8459760b5598`, 4,378,828 bytes.
- [ ] Invoke `java -jar packwiz-installer-bootstrap.jar --bootstrap-no-update --bootstrap-main-jar /trusted/packwiz-installer-v0.5.14.jar -g -s server RAW_FULL_SHA_PACK_TOML` in every server consumer. The client defaults to side `client` and must not receive `-s server`.
- [ ] Account for Packwiz installer `v0.5.14` writing one root `packwiz.json`. Require it to be a regular file, parse and validate its expected installer-state structure and paths as provenance, bind its SHA-256 to the candidate receipt, and move it to `${STATE_DIR}/candidates/<candidate-id>/packwiz.json` before candidate closure.
- [ ] After moving `packwiz.json`, permit only indexed files beneath `config`, `global_packs`, `kubejs`, and `mods`. Exclude installer provenance from the managed ledger and activated `/data`, and reject every other unindexed candidate file, unexpected root, noncanonical path, link, hardlink, or duplicate location.
- [ ] Authenticate NeoForge installer `21.1.248` with SHA-256 `68eeab77059ba53df1812f1afa5bf530ab2566a3cdcd5f924aa6e71be42e410c` before cache publication or setup.
- [ ] `install.sh` requires absent or completely empty data, creates a secret without printing it, stages and validates into a sibling candidate, runs `SETUP_ONLY=true`, atomically publishes, force-creates the container, and verifies health.
- [ ] `update.sh` stages before downtime, rejects active or unknown Chunky work, rechecks current `main`, closes maintenance, acquires the operations lock once, invokes the protected pre-update backup through inherited `--lock-held`, stops gracefully, activates only managed files, and uses `docker compose up -d --no-deps --force-recreate minecraft`.
- [ ] On update health failure, stop the server, leave maintenance closed, preserve candidate, Packwiz provenance, journal, backup, quarantine state, logs, and receipts, return exit `6`, and print one exact `rollback.sh prepare` command. Do not mutate world data again.
- [ ] Test update-to-backup and rollback-to-backup nesting with the same inherited `AFTERLIGHT_OPS_LOCK_FD`. Assert that each parent retains the lock for the complete operation, each child skips acquisition only after validation, and neither path self-deadlocks.
- [ ] `rollback.sh prepare` requires an explicit bundle ID, derives and authenticates historical SHA `H` from the bundle, creates a protected backup of current state through the inherited lock, validates a sibling restore tree, quarantines current data, atomically installs the historical candidate, and leaves Minecraft stopped and maintenance closed. It never deletes quarantine.
- [ ] The operator, never a script, creates and reviews a normal rollback commit `R` through `dev` and `main`. Source tests must forbid `git commit`, `git revert`, `git push`, branch mutation, tag mutation, and GitHub write APIs from maintenance tooling.
- [ ] `rollback.sh activate` requires `R` to be current remote `main` with a completed successful exact-SHA `main` push workflow. Require raw `R` `pack.toml` and `index.toml` to be byte-identical to the authenticated historical snapshots for `H`, require Pages to match `R`, stage from raw `R`, and preserve receipts for both `H` and `R`.
- [ ] After rollback activation, force-recreate and verify health while the announced maintenance window remains in effect. Record the released-client join as a manual item and require Shane to reopen production explicitly only after that join passes. Neither rollback phase may open production or claim that it is open.
- [ ] `recover.sh` requires an empty data path including dotfiles, validates the offsite-retrieved bundle and historical CI receipt, creates a fresh RCON secret, restores to a sibling candidate, overlays the exact Packwiz SHA, rebuilds excluded runtime files, atomically publishes, and verifies health. A historical recovery intended for production reopening must satisfy the same current rollback-commit, Pages, and manual-join gate.
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

- [ ] Make health verify one container ID, running state, exact mounted data source, exact pinned image reference, required environment, no `PACKWIZ_URL`, container health, `mc-health`, RCON `list`, Java major 21, NeoForge version, current-start readiness log, active release SHA, managed-ledger digest, and preserved Packwiz provenance digest in `${STATE_DIR}`.
- [ ] Reject stale readiness lines by binding success to the current container start and expected SHA.
- [ ] Implement Chunky `start` with explicit world, `circle|square` shape, integer center, and radius. Default radius is 10,000 and documented maximum is 20,000. Do not implement trim.
- [ ] Use exact commands `chunky start`, `chunky progress`, `chunky pause [world]`, `chunky continue [world]`, and `chunky cancel [world]`.
- [ ] Require a protected backup before `start` and `continue`. Acquire the operations lock once, invoke backup with internal `--lock-held`, and keep the inherited descriptor open through completion, pause, or cancellation. Update, rollback, and recovery fail closed while Chunky is active or its state cannot be classified.
- [ ] Add a pregen-to-backup test that proves the child receives the same inherited file descriptor and completes without self-deadlock. Add source and fake-command tests for healthy, unhealthy, stale, duplicate-container, wrong-mount, wrong-image, wrong-Java, wrong-SHA, RCON failure, and every conservative Chunky state.
- [ ] Record live-host-only checks separately: firewall, `flock`, inherited descriptor behavior, same-filesystem rename, two-minute graceful stop, memory headroom, host reboot, backup throughput, disk headroom, native image pull, arm64 pack boot, whitelist, voice UDP, encrypted empty-host recovery, rollback maintenance closure, and released-client join before production reopening.
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

- [ ] Require an explicit accepted release SHA and HTTPS Pages pack URL for a release Prism build. Run `release_gate.py accept`, verify both Packwiz JAR hashes, and embed only those two installer JARs.
- [ ] Keep CI and pre-acceptance distribution tests independent of accepted `main` and current Pages. They may test builders with fixtures and immutable local inputs, but they must not claim or require the final release Prism archive.
- [ ] Set Prism prelaunch to `java -jar packwiz-installer-bootstrap.jar --bootstrap-no-update --bootstrap-main-jar packwiz-installer.jar -g ACCEPTED_PAGES_PACK_TOML`. The installer defaults to side `client`; do not pass `-s server`. Build in a fresh temporary directory and inspect the final ZIP entry-by-entry.
- [ ] Reject stale archive entries, path traversal, links, unexpected JARs, mutable release URLs, embedded mod JARs, secrets, and a pack URL whose Pages bytes do not match the accepted SHA.
- [ ] Record the Prism ZIP SHA-256 and exact release receipt. Verify import structure without claiming client launch success.
- [ ] Keep Prism plus Packwiz as the only complete supported installation lane. Document RAM allocation, Java 21, import, launch, update, recovery, voice chat, log collection, common crashes, and clean reinstall without deleting saves.
- [ ] Commit the exact AutoModpack licensing inventory: 13 denied, 13 manual-review, and 7 unknown client entries. Do not add, configure, host, test, or advertise AutoModpack while any blocker remains.
- [ ] Document mrpack and CurseForge ZIP as optional friends-only lanes because they can contain embedded third-party JARs.
- [ ] Commit only after distribution tests pass and archive inspection proves that no mod JAR or secret is embedded.

### Task 6: CI Hardening, Skeptical Review, and Subject Freeze

**Files:**
- Modify: `pack.toml`
- Modify: `index.toml`
- Modify: `.github/workflows/pack-ci.yml`
- Create: `tools/gauntlet.sh`
- Create: `tools/tests/test_gauntlet_contract.py`
- Modify: `docs/HANDOFF.md`

- [ ] Set pack version to `0.9.0-rc.1`, source `tools/versions.env`, run Packwiz refresh, and commit `pack.toml`, `index.toml`, and any Packwiz-managed metadata together.
- [ ] Pin every GitHub Action to a full commit SHA and pin an exact Go version. Extend CI with Python unit tests, static and runtime quest validation, `verify-pack.sh`, shell syntax, forbidden U+2014 scan, server boot, exports, distribution fixture inspection, archive fixture tests, secret scan, and final git cleanliness.
- [ ] Make the required `verify-and-export` job a pre-acceptance job. It may validate the checked-out SHA, immutable raw inputs, release tooling, and fixture Prism behavior, but it must not require current `main`, Pages parity, `release_gate.py accept`, or a release Prism build. Add a contract test that prevents self-waiting acceptance from entering the workflow.
- [ ] Upload logs only from the current failed run. Remove stale evidence before execution and include every relevant log and command transcript on failure.
- [ ] Give `tools/gauntlet.sh` explicit `preaccept` and `release` modes. Both require a clean detached full-SHA worktree and record SHA, operating system, architecture, Java, Go, Packwiz, Python, Docker, and Compose versions.
- [ ] In pre-acceptance mode, run every acceptance-independent unit, static, manifest, server, Compose, backup, lock, rollback, recovery, distribution-fixture, export, secret, punctuation, shell, and cleanliness check. Do not query current Pages or build the final Prism archive.
- [ ] In full release mode, first require an external accepted receipt for the already completed exact-SHA `main` push workflow and Pages deployment, rerun the complete pre-acceptance suite, then run `release_gate.py accept`, exact Pages and raw installs, the final Prism build and archive inspection, backup and restore drills, failed-update closure, two-phase rollback tests, nested-lock tests, and final git cleanliness. Capture every command and exit code.
- [ ] Ensure every gauntlet run starts from a fresh `server-test` runtime so a later run cannot reuse an earlier boot, nonce, logs, installed files, Prism archive, backup, or generated evidence.
- [ ] Run a whole-project skeptical review against the design spec and all seven plans after implementation and pre-acceptance checks are complete. Fix every Critical and Important finding, rerun focused checks, then rerun the complete pre-acceptance suite.
- [ ] Before freezing `S`, verify branch history, required commit attribution trailers, absence of JARs and secrets in git, no U+2014 in tracked authored content, exact `0.9.0-rc.1` identity, and a clean tree.
- [ ] Update `docs/HANDOFF.md` before the subject freeze. After the skeptical review, all fixes, and all acceptance-independent checks pass, create the final implementation commit and designate its full SHA as `S`.
- [ ] Push exact `S` to `dev` and require its exact completed successful `dev` push workflow. Any implementation, manifest, config, quest, pack, workflow, or non-evidence documentation change after this point invalidates `S` and requires a new skeptical review, new subject SHA, and restart from this task.

### Task 7: Accepted Gauntlets, Evidence Commit, and Release Candidate

**Files:**
- Create: `docs/releases/v0.9.0-rc.1.md`
- Create: `docs/releases/v0.9.0-rc.1-gauntlet.md`

- [ ] Promote exact `S` from `dev` to `main` without creating a different commit. Require the exact `S` `main` push workflow and its `verify-and-export` job to reach completed success, then require the exact `S` Pages deployment and byte parity. Only after both complete may an external process run `release_gate.py accept` for `S`.
- [ ] Run the full release gauntlet twice at `S` from two separate fresh clean worktrees. Each run must independently include `release_gate.py accept`, clean client and server installs, the release Prism build, all release-mode checks, exact SHA-256 values, and elapsed time.
- [ ] If either release gauntlet exposes a required implementation fix, do not patch after the gauntlets. Invalidate `S`, return to Task 6, repeat skeptical review and subject freeze, promote the new `S`, and run two new accepted full gauntlets.
- [ ] Record every existing manual item explicitly as passed, failed, or deferred with owner and evidence path. Two accepted full gauntlets plus an explicit deferred record make `0.9.0-rc.1` eligible even when Shane's manual matrix remains deferred.
- [ ] Create evidence commit `E` directly on `S`. Its only changed paths must be `docs/releases/v0.9.0-rc.1.md` and `docs/releases/v0.9.0-rc.1-gauntlet.md`; the reports record `S`, its accepted workflow and Pages receipt, both gauntlet receipts, Prism SHA-256 values, exact command output, and deferred live-host or client checks.
- [ ] Make the evidence reports state that their own commit's workflow and Pages acceptance occur later. They must not contain or claim an `E` workflow receipt, an `E` Pages deployment receipt, or final `E` parity evidence.
- [ ] Prove `E` has parent exactly `S` and inspect `git diff S..E` with a strict path allowlist. Fail if any executable, manifest, config, quest, pack, workflow, generated Packwiz state, or file outside the two named evidence documents changed.
- [ ] Promote exact `E` through `dev` and then `main` without merge, squash, or fixup commits. Require exact completed successful `E` push workflows on both branches, then require the exact `E` Pages deployment and byte parity on `main`.
- [ ] Create immutable annotated tag `v0.9.0-rc.1` at `E` only after exact `E` CI and Pages acceptance. Put `S`, `E`, the exact final `E` workflow run, attempt, and job identifiers, the exact Pages deployment identifier, parity hashes, and the final acceptance receipt digest in the annotated tag message and GitHub release metadata. Never move or recreate the tag to add evidence.
- [ ] Publish no restricted archives. Do not create `v1.0.0` in this autonomous run.
- [ ] Leave these manual acceptance items explicit for Shane: Prism import and sub-three-minute title screen; new-world quest UI and theme; chapters 1 through 8 playthrough; every Certification and hard gate; released-client dedicated-server join; two-user voice test; whitelist and firewall; update drill; induced update failure plus explicit rollback; and encrypted offsite empty-host restore on a replacement host.
- [ ] Shane measures the completed Supercritical Phase Shifter throughput and total wall time for the four-antimatter-pellet Isotopic Core requirement against the exact release candidate, records the evidence path, and decides whether balance changes are required before `1.0.0`. Automated agents leave this item unchecked and never infer the result.
- [ ] Shane manually records the exact multiplayer Seal matrix with two real accounts on the released client and server: two eligible players on one quest team each claim exactly one Seal; replay or repeated reward interaction cannot duplicate either Seal; a late joiner can claim after joining a team that already completed the finale; leaving, rejoining, and changing teams neither duplicates nor deadlocks the reward; one Seal can transfer to another player; and the recipient crafts Draconium Core, Dislocator, and Module Core while the transferred Seal remains exactly one. Automated agents leave this item unchecked and never claim it from static or headless evidence.
- [ ] Treat every deferred manual item as a blocker for `1.0.0` and for any claim that production is open, but not as a blocker for the correctly labeled `v0.9.0-rc.1` prerelease.
- [ ] Add `linux/arm64` support only after native pull, Java 21, NeoForge setup, complete pack boot, Chunky smoke, and gameplay checks pass on that architecture.
- [ ] Promote to `1.0.0` only after every manual acceptance item is recorded as passed against the exact release candidate lineage.
