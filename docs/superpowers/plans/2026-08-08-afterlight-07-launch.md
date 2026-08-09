# AFTERLIGHT Plan 07: VPS, Distribution, and Release Candidate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a reproducible VPS deployment, fail-closed maintenance tooling, friend installation assets, and a fully evidenced `0.9.0-rc.1` release candidate. Version `1.0.0` remains blocked until Shane completes the manual acceptance matrix.

**Architecture:** Docker Compose runs exact OCI-index digests for `itzg/minecraft-server` and `itzg/mc-backup` against one bind-mounted `/data` tree. A host ingress gate persists authenticated `closed`, `tester-only`, or `production-open` state outside `/data`; protected backup, update, rollback, and recovery fail closed through that gate. Rollback prepare and activate are bound by one authenticated, one-time transaction receipt that records the exact restored state and rollback release. Pre-acceptance checks validate immutable inputs without requiring accepted `main`, current Pages, or a release Prism build; after skeptical review and all fixes, the final implementation commit becomes release subject SHA `S`, exact `S` is promoted to `main`, its completed successful `main` push workflow and Pages parity are accepted, and two fresh full release gauntlets run at `S`. The direct child evidence SHA `E` may change only the named release evidence documents, is promoted unchanged through `dev` and `main`, then receives a separate external accepted-mode receipt before the annotated tag and GitHub release are created.

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
- `${DATA_DIR}`, `${BACKUP_DIR}`, `${STATE_DIR}`, `${QUARANTINE_DIR}`, and `${SECRETS_DIR}` must be canonical, non-symlinked, pairwise nonnested paths. Data and quarantine must share a local filesystem for atomic rename. Maintenance and rollback authority must never live beneath `${DATA_DIR}` or inside a backup bundle.
- Every Bash operator script uses `#!/usr/bin/env bash`, `set -Eeuo pipefail`, `umask 077`, `LC_ALL=C`, and the same Linux operations lock at `${STATE_DIR}/ops.lock`.
- A top-level mutating command acquires the operations lock once, keeps one file descriptor open for its full lifetime, and exports that inherited descriptor to nested maintenance commands. An internal `--lock-held` path validates and reuses that descriptor instead of reacquiring the lock.
- The host ingress gate is the only authority that can expose Minecraft TCP `25565` or voice UDP `24454`. Missing, malformed, unauthenticated, stale, or live-rule-divergent gate state means `closed`. No install, update, backup, rollback, recovery, health, or Chunky command may infer or perform `production-open`.
- Common exit codes are `0` success, `2` usage or configuration, `3` live precondition, `4` trust or integrity, `5` operational failure, and `6` update stopped with an explicit rollback required.
- World mutation, update, rollback, recovery, and Chunky start or continue require a protected backup first. Every protected backup closes and proves the host ingress gate before archive creation, records the exact close and status receipt digests, leaves the gate closed, and is never pruned automatically.
- Update health failure stops the server, leaves maintenance closed, preserves all evidence, writes one immutable rollback-request receipt containing the exact failed-state backup and bundle identity, and prints the exact operator runbook path. It never restores world data automatically or invents rollback SHA `R` before the operator creates and accepts it.
- Rollback activation may expose only the authenticated tester allowlist. Production opening is a later explicit command that requires the released-client join receipt for the same consumed rollback transaction and a fresh accepted release receipt for the same rollback SHA.
- Pre-acceptance CI on `dev` or `main` must not require an already accepted `main` SHA, current Pages parity, `release_gate.py accept`, or a release Prism archive. The workflow run whose success establishes acceptance must never invoke accepted mode, gate itself, or wait for itself.
- Freeze release subject SHA `S` only after the whole-project skeptical review and every resulting fix. Promote exact `S` to `main`, accept its completed successful exact-SHA `main` push workflow and Pages parity, then run two clean full release gauntlets from separate fresh worktrees at `S`, each including `release_gate.py accept` and the release Prism build.
- Two accepted full gauntlets at `S` plus an explicit record of every deferred manual item permit `v0.9.0-rc.1`. Shane's manual matrix gates only `1.0.0` and claims that production is open.
- Evidence SHA `E` must be the direct child of `S` and may change only `docs/releases/v0.9.0-rc.1.md` and `docs/releases/v0.9.0-rc.1-gauntlet.md`. No executable, manifest, config, quest, pack, or workflow change is permitted from `S` to `E`.
- After exact `E` CI and Pages parity complete, an external operator process must run `release_gate.py accept` for `E`, durably preserve its canonical receipt and detached SHA-256 outside the repository, and only then create the annotated tag and GitHub release. Neither `E` nor the workflow being accepted may contain or generate that post-`E` receipt.

## Durable State Layout

- `${STATE_DIR}/maintenance/state.json` is the authenticated current gate state. `${STATE_DIR}/maintenance/receipts/<generation>.json` stores immutable transition receipts, and `${STATE_DIR}/maintenance/proofs/<proof-id>.json` stores immutable status proofs. Every record uses canonical UTF-8 JSON and HMAC-SHA-256 with `${SECRETS_DIR}/receipt-auth.key`; the key is mode `0600`, never logged, and never copied into `/data`, git, or backups.
- `${SECRETS_DIR}/maintenance-testers.txt` is the canonical mode `0600` tester CIDR allowlist. Gate receipts record only its SHA-256 and entry count, never its addresses.
- `${STATE_DIR}/rollback/pending.json` identifies at most one prepared transaction by ID and prepare-receipt digest. `${STATE_DIR}/rollback/transactions/<transaction-id>/` contains `prepare.json`, `prepare.json.sha256`, `data-before.inventory`, `data-prepared.inventory`, `quarantine.inventory`, `activation-intent.json`, `activation.json`, `join.json`, and `production-open.json`. `${STATE_DIR}/rollback/consumed/<transaction-id>.json` is the durable one-time tombstone that prevents a completed prepare receipt from being reused.
- State directories are root-owned mode `0700`; mutable state is root-owned mode `0600`; immutable receipt, proof, digest, and inventory files become root-owned mode `0400` after durable publication. Gate and rollback records are written with create-new semantics, file `fsync`, atomic rename where replacement is required, and parent-directory `fsync`. They reject links, noncanonical paths, wrong ownership or mode, duplicate transaction IDs, rollback state beneath `/data`, and any receipt whose schema, HMAC, predecessor digest, or generation does not validate.
- Final release acceptance uses a separate canonical, remotely authenticated receipt. The external release operator stores `E-acceptance.json` and `E-acceptance.json.sha256` beneath a canonical `${RELEASE_STATE_DIR}/v0.9.0-rc.1/` outside every Git worktree. These files are public-safe evidence, not VPS HMAC records, and are copied into annotated-tag and GitHub-release metadata rather than committed.

---

### Task 1: Release Trust and Compose Foundation

**Files:**
- Create: `server/docker-compose.yml`
- Create: `server/.env.example`
- Create: `server/server.properties.example`
- Create: `server/backup-excludes.txt`
- Create: `server/README.md`
- Create: `server/scripts/lib.sh`
- Create: `server/scripts/maintenance.sh`
- Create: `server/scripts/release_gate.py`
- Create: `server/systemd/afterlight-compose.service`
- Create: `server/systemd/afterlight-maintenance-gate.service`
- Create: `server/tests/test_maintenance_gate.py`
- Create: `server/tests/test_release_gate.py`
- Create: `server/tests/test_compose_contract.py`
- Modify: `.gitignore`
- Modify: `.packwizignore`

**Interfaces:**
- `release_gate.py preaccept --repo OWNER/REPO --sha SHA` validates the immutable subject and repository inputs without requiring current `main`, Pages, a completed acceptance workflow, or Prism. It prints a mode-labeled JSON result and never prints an acceptance receipt.
- `release_gate.py accept --repo OWNER/REPO --sha SHA --pages-url URL --receipt-out RECEIPT --digest-out DIGEST` requires current `main`, the already completed successful exact-SHA `main` push workflow and job, the exact Pages deployment, Pages byte parity, and clean client and server installs. It creates one canonical authenticated JSON receipt plus its detached SHA-256 with create-new, flush, and parent-directory durability, then exits `0`; any failure exits `4` without either final file.
- `release_gate.py historical --repo OWNER/REPO --sha SHA` authenticates an earlier completed successful `main` push workflow and immutable raw release bytes for backup validation, rollback preparation, or recovery. It never treats historical evidence as permission to reopen against a different current client channel.
- `lib.sh` exposes fixed Compose invocation, canonical path checks, dependency checks, one inherited Linux operations-lock file descriptor, HTTPS download with SHA-256 verification, RCON execution, and guarded temporary-directory cleanup.
- `maintenance.sh close --reason TOKEN [--lock-held]`, `maintenance.sh status [--require closed|tester-only|production-open] [--receipt-out RECEIPT] [--lock-held]`, and `maintenance.sh open --mode tester-only|production --release-receipt RECEIPT [--transaction TRANSACTION] [--join-receipt RECEIPT] [--lock-held]` are the only gate interfaces. `open --mode production` emits `production-open` state and never accepts a rollback or recovery lineage without matching transaction and join receipts.

- [ ] Write failing tests for malformed SHAs, wrong repository refs, PR-only success, workflow-dispatch-only success, failed newest reruns, duplicate check names, malformed API JSON, rate limits, Pages lag, a `main` ref that moves during staging, attempts to accept the workflow run identified by the current `GITHUB_RUN_ID`, noncanonical receipt JSON, preexisting output paths, partial output, and receipt or detached-digest mismatch.
- [ ] Make pre-acceptance mode independent of branch acceptance and Pages. Source-test `.github/workflows/pack-ci.yml` so the required `verify-and-export` job cannot call `release_gate.py accept`, poll its own run, require a release Prism archive, or depend on a job that does so.
- [ ] Implement the GitHub acceptance source as `GET /actions/workflows/pack-ci.yml/runs` filtered to `branch=main`, `event=push`, `status=completed`, and exact `head_sha`. Send `Accept: application/vnd.github+json` and `X-GitHub-Api-Version: 2026-03-10`. Require the selected run and its exact attempt's `verify-and-export` job to be completed successfully. Check runs may corroborate but never establish acceptance.
- [ ] Make accepted mode fail immediately if the selected workflow run is the caller's own `GITHUB_RUN_ID`. Accepted mode runs only after that workflow has completed and never from a job whose success it is trying to establish.
- [ ] Define accepted-receipt schema `afterlight.release.acceptance.v1` with repository, exact SHA, workflow ID, run ID, attempt, job ID, Pages deployment ID, immutable raw and Pages hashes, clean client and server install results, and source completion timestamps. Serialize sorted keys with fixed separators and one trailing LF, derive the detached SHA-256 from those exact bytes, and omit local wall-clock fields so identical authenticated evidence produces identical receipt bytes.
- [ ] Compare Pages `pack.toml` and `index.toml` byte-for-byte with raw full-SHA files using a cache-busting query. Install Pages into scratch only to verify every indexed hash, then discard it. Emit production URLs rooted at `https://raw.githubusercontent.com/OWNER/REPO/SHA/`.
- [ ] Pin `itzg/minecraft-server:2026.8.0-java21@sha256:b76b9298a2a60d5cf9d223e009cd0b8ad620c2080abd83f9a1fa5084fa87f9ab` and `itzg/mc-backup:2026.8.0@sha256:ae54d88d1a5dfbc185f1f94e50bb2e9b68484719013f4f21c573422dd4950f32`.
- [ ] Do not set Compose `platform`. Document `linux/amd64` as the supported launch architecture and retain the native `linux/arm64` pull as a deferred matrix item.
- [ ] Configure `EULA=TRUE`, `TYPE=NEOFORGE`, `VERSION=1.21.1`, `NEOFORGE_VERSION=21.1.248`, `NEOFORGE_INSTALLER=/data/.afterlight/cache/neoforge-21.1.248-installer.jar`, `INIT_MEMORY=4G`, `MAX_MEMORY=10G`, `STOP_DURATION=90`, `UMASK=0077`, `ENABLE_RCON=TRUE`, and `RCON_PASSWORD_FILE=/run/secrets/rcon_password`.
- [ ] Publish only Minecraft TCP `25565` and Simple Voice Chat UDP `24454`. Never publish RCON `25575`.
- [ ] Use long bind syntax with `create_host_path: false`. Mount `/data` read-write in Minecraft, `/data` read-only in the one-shot backup service, `/backups` read-write in the backup service, and `server/backup-excludes.txt` read-only at `/etc/afterlight-backup-excludes.txt` in the backup service. Set `BACKUP_METHOD=tar`, `TAR_COMPRESS_METHOD=zstd`, `ENABLE_SAVE_ALL=true`, `ENABLE_SYNC=true`, `SKIP_LOCKING=false`, `PAUSE_IF_NO_PLAYERS=false`, `BACKUP_ON_STARTUP=false`, `EXCLUDES=""`, `EXCLUDES_FILE=/etc/afterlight-backup-excludes.txt`, and `stop_grace_period: 2m`.
- [ ] Make `server/backup-excludes.txt` the reviewed source for recursive exclusions of `.rcon-cli.env`, `.rcon-cli.yaml`, `server.properties`, the host-created `.paused` marker, every JAR, cache directories, logs, and known transient runtime files including `session.lock`, `*.tmp`, `*.part`, and `*.partial`. Do not configure a second conflicting inline exclusion list.
- [ ] Use a Compose secret outside `/data` for RCON. Never source `.env` from shell, never use Bash `UID`, and unset conflicting Compose interpolation variables before every fixed invocation.
- [ ] Define `lib.sh` lock ownership so the top-level command opens and locks `${STATE_DIR}/ops.lock` once, exports the numeric descriptor as `AFTERLIGHT_OPS_LOCK_FD`, and retains it until exit. Internal `--lock-held` use must reject a missing, closed, nonnumeric, or wrong-target descriptor through Linux `/proc/self/fd`, then require nonblocking `flock -n` on that same descriptor to succeed. The inherited locked open-file description succeeds without reacquisition; a separately opened descriptor fails while the parent lock is held.
- [ ] Implement the maintenance enforcer as one root-owned atomic `nftables` ingress table evaluated before every Docker published-port accept path for IPv4 and IPv6. `closed` drops new and established TCP `25565` and UDP `24454` traffic from external, host, loopback, and peer-container sources while leaving unpublished internal RCON control available; `tester-only` permits only canonical CIDRs from `${SECRETS_DIR}/maintenance-testers.txt`; `production-open` removes only AFTERLIGHT's maintenance restriction and never widens the baseline host firewall. `close` must terminate existing game sessions, require RCON player count zero when Minecraft is running, and persist the authenticated transition before reporting success.
- [ ] Make `status` compare authenticated state, predecessor chain, state generation, tester-allowlist digest, live kernel rules, published ports, active connections, and RCON player count. A proof receipt binds all observations and the operations-lock identity. Any mismatch reports `closed` for safety and exits nonzero when `--require` was supplied.
- [ ] Implement every gate transition as create and flush intent, apply the restrictive or permissive live rules, prove the exact live rules, then publish the new state and immutable transition receipt. Any incomplete intent, including one for production opening, is interpreted as closed by status and boot replay. Closing applies live drops before publishing closed; production opening publishes no open state until all release, health, transaction, and join checks plus live-rule proof succeed.
- [ ] Install `afterlight-maintenance-gate.service` before root-owned `afterlight-compose.service` at boot. The gate unit applies closed before Docker can expose the game when state or HMAC validation fails, reapplies an authenticated persisted mode only when no transition or rollback intent is incomplete, and prevents Compose startup when live rules cannot be proven equal to persisted state. The Compose unit requires the gate unit, and Compose services must not use an independent restart policy that bypasses this ordering.
- [ ] Test all three modes in isolated Linux network namespaces with real `nft`, IPv4 and IPv6 probes, established-connection closure, tester allowlist changes, host, loopback, peer-container, and direct Docker published-port bypass attempts, continued internal RCON control, interruption at every transition write and rule-application boundary, reboot replay, missing or replaced state, invalid HMAC, stale generation, live-rule drift, player-count races, forged status receipts, and lock contention. Fake-command tests alone cannot satisfy the live ingress acceptance clause.
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
- `backup.sh --class scheduled|protected --reason TOKEN [--offline] [--dry-run]` acquires the operations lock when called directly and publishes one immutable bundle directory only after every check passes. A protected bundle includes the exact authenticated maintenance close receipt and closed-status proof plus both detached digests.
- `backup.sh ... --lock-held` is internal only. It validates `AFTERLIGHT_OPS_LOCK_FD`, reuses that inherited descriptor, and never tries to acquire `${STATE_DIR}/ops.lock` again.

- [ ] Write failing fixtures for absolute paths, parent traversal, symlinks, hardlinks, devices, FIFOs, duplicate names, control characters, missing `world/level.dat`, secret files, excluded RCON files, `server.properties`, leaked `.paused`, JARs, cache members, logs, transient files, decompression-bomb metadata, partial gzip, bad checksums, and expanded-size or member-count overflow.
- [ ] Accept only regular files and directories. Reject `.rcon-cli.env`, `.rcon-cli.yaml`, `server.properties`, `.paused`, secrets, links, devices, duplicate members, control characters, absolute paths, `..` traversal, JARs, caches, logs, and transient members before extraction.
- [ ] Require `world/level.dat`, an authenticated release receipt, the exact managed-file ledger, exact `pack.toml` and `index.toml` snapshots with SHA-256 values, bounded member count, bounded expanded bytes, archive SHA-256, and a completion marker.
- [ ] Before any protected archive command starts, invoke `maintenance.sh close` and `maintenance.sh status --require closed --receipt-out` through the inherited operations-lock descriptor. Bind the close generation, close receipt digest, status proof digest, live-rule digest, zero-player observation, and backup operation ID into bundle metadata. Recheck the same generation and live-rule digest before atomic publication. Failure or drift creates no completed bundle and never restores the prior gate mode.
- [ ] Run the pinned backup image only into `incoming/<run-id>` and set `POST_BACKUP_SCRIPT='exit "$1"'`. In online mode, require absence of `/data/.paused`, enter the image's normal branch, and require its `.mc-backup-lock`. In offline mode, enter the pinned image's paused branch and explicitly do not require an image lock that this branch never acquires. Independently validate output before atomic publication in both modes.
- [ ] Prove that exclusions happen before archive validation. Tests must inspect resolved Compose JSON for the exact read-only exclusion mount and `EXCLUDES_FILE`, inspect successful archive membership to prove every reviewed class including `.paused` is absent at any depth, then inject each forbidden class directly to prove the archive guard still rejects it.
- [ ] For online backup, require healthy RCON and no `.paused` marker. Let the pinned image's normal branch exclusively perform its readiness `save-on`, acquire `.mc-backup-lock`, run `save-off`, optional `save-all flush` and sync, create the archive, and restore `save-on` with its own exit trap. The host wrapper must not duplicate that RCON mutation sequence.
- [ ] For offline backup, require Minecraft and the scheduled backup sidecar to be fully stopped while the shared host operations lock remains held. Refuse a preexisting `${DATA_DIR}/.paused`, create that regular marker only after stop verification, record its identity, and trap-clean only the marker created by this invocation on success, failure, signal, or cancellation. The marker selects the pinned image's RCON-free, image-lock-free paused branch and must be excluded from the archive.
- [ ] Test online and offline configuration separately against the pinned `scripts/opt/backup-loop.sh` branch contract. Online tests require RCON configuration, no marker, the normal save sequence, and `.mc-backup-lock`; offline tests require stopped services, the inherited host descriptor, marker creation and cleanup, no RCON call, and no assertion that `.mc-backup-lock` exists.
- [ ] Store `scheduled` and `protected` bundles separately. Prune scheduled bundles only, and never infer a restore target from "latest".
- [ ] Test direct lock acquisition and inherited `--lock-held` use. Prove a nested child receives the same open file descriptor and completes without self-deadlock, while forged or separately opened descriptors fail closed. Prove the offline paused branch remains serialized by that host descriptor even though the image lock is absent.
- [ ] Prove failure behavior for every online RCON phase, tar exits 1 and 2, killed backup, lock contention, partial output, secret inclusion, exclusion failure, preexisting or replaced `.paused`, marker cleanup after every exit path, maintenance close failure, forged or stale closed proof, player reconnect race, live-rule mutation before publication, and retention attempting to touch protected data. Assert that no protected archive process starts until the gate proof succeeds and that every failure remains closed.
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
- `install.sh [--sha SHA] [--dry-run]`, `update.sh [--sha SHA] [--dry-run]`, and `recover.sh --backup BUNDLE --sha SHA --confirm BUNDLE_ID [--dry-run]` use the shared trust, gate, backup, activation, and health interfaces. Successful mutation never implies `production-open`.
- `rollback.sh prepare --backup BUNDLE --rollback-sha R --release-receipt R_RECEIPT --confirm BUNDLE_ID [--dry-run]` authenticates the historical bundle SHA `H` and already accepted rollback release `R`, restores the named historical state while the gate remains closed, and creates exactly one pending transaction receipt outside `/data`.
- `rollback.sh activate --transaction TRANSACTION_ID --receipt PREPARE_RECEIPT --confirm TRANSACTION_ID [--resume] [--dry-run]` consumes only that exact pending receipt while holding the operations lock, revalidates every bound input, transitions the gate to tester-only, starts and health-checks the restored server, and never declares production reopened.
- `rollback.sh attest-join --transaction TRANSACTION_ID --client-release-receipt RECEIPT --confirm TRANSACTION_ID` records one explicit manual released-client join pass for the activated transaction. It cannot run from health output alone and writes an authenticated join receipt required by `maintenance.sh open --mode production`.

- [ ] Write failing tests for added, changed, and removed managed files, duplicate Packwiz locations, stale mod removal, untracked runtime file preservation, interrupted journal steps, symlinked paths, missing bind sources, nonempty recovery targets including one dotfile, low disk, wrong recorded SHA, missing ledger, malformed or missing root `packwiz.json`, extra unindexed candidate files, setup failure, health failure, missing or forged rollback receipts, transaction reuse, and every bound-state mutation between rollback prepare and activate.
- [ ] Pin bootstrap `v0.0.3` SHA-256 `a8fbb24dc604278e97f4688e82d3d91a318b98efc08d5dbfcbcbcab6443d116c`, 98,989 bytes, and installer `v0.5.14` SHA-256 `c9f646908d340d84773948a9a7d98bc1dae250d35e1016dc6e2b8459760b5598`, 4,378,828 bytes.
- [ ] Invoke `java -jar packwiz-installer-bootstrap.jar --bootstrap-no-update --bootstrap-main-jar /trusted/packwiz-installer-v0.5.14.jar -g -s server RAW_FULL_SHA_PACK_TOML` in every server consumer. The client defaults to side `client` and must not receive `-s server`.
- [ ] Account for Packwiz installer `v0.5.14` writing one root `packwiz.json`. Require it to be a regular file, parse and validate its expected installer-state structure and paths as provenance, bind its SHA-256 to the candidate receipt, and move it to `${STATE_DIR}/candidates/<candidate-id>/packwiz.json` before candidate closure.
- [ ] After moving `packwiz.json`, permit only indexed files beneath `config`, `global_packs`, `kubejs`, and `mods`. Exclude installer provenance from the managed ledger and activated `/data`, and reject every other unindexed candidate file, unexpected root, noncanonical path, link, hardlink, or duplicate location.
- [ ] Authenticate NeoForge installer `21.1.248` with SHA-256 `68eeab77059ba53df1812f1afa5bf530ab2566a3cdcd5f924aa6e71be42e410c` before cache publication or setup.
- [ ] `install.sh` requires absent or completely empty data, creates the RCON secret and `${SECRETS_DIR}/receipt-auth.key` without printing either, initializes authenticated maintenance state as closed, stages and validates into a sibling candidate, runs `SETUP_ONLY=true`, atomically publishes, force-creates the container, and verifies health while ingress remains closed. Opening production is an explicit later maintenance command.
- [ ] `update.sh` stages before downtime, rejects active or unknown Chunky work, rechecks current `main`, acquires the operations lock once, invokes the protected pre-update backup through inherited `--lock-held`, proves the gate still closed, stops gracefully, activates only managed files, and uses `docker compose up -d --no-deps --force-recreate minecraft`. A successful update remains closed until the operator explicitly opens the accepted release.
- [ ] On update health failure, stop the server, leave maintenance closed, preserve candidate, Packwiz provenance, journal, backup, quarantine state, logs, and receipts, return exit `6`, write a canonical authenticated rollback-request receipt under `${STATE_DIR}/rollback/requests/<request-id>/`, and print the exact `server/README.md` recovery sequence plus fixed request and bundle values. Do not mutate world data again or print a prepare command that omits the not-yet-created accepted `R` receipt.
- [ ] Test update-to-backup and rollback-to-backup nesting with the same inherited `AFTERLIGHT_OPS_LOCK_FD`. Assert that each parent retains the lock for the complete operation, each child skips acquisition only after validation, and neither path self-deadlocks.
- [ ] After an update failure, the operator, never a script, creates and reviews normal rollback commit `R`, pushes exact `R` through `dev`, promotes it unchanged to `main`, waits for exact-SHA CI and Pages parity, and runs external accepted mode to a create-new `R` receipt. Only then may prepare begin. Source tests must forbid `git commit`, `git revert`, `git push`, branch mutation, tag mutation, and GitHub write APIs from maintenance tooling.
- [ ] `rollback.sh prepare` requires explicit bundle ID, `R`, and canonical accepted `R` receipt. It authenticates bundle completion and archive digests, derives and authenticates historical SHA `H`, requires raw `R` `pack.toml` and `index.toml` to be byte-identical to the authenticated historical snapshots for `H`, and rechecks that `R` is current accepted `main` with Pages parity before mutating data.
- [ ] While retaining the operations lock, prepare creates a protected backup of the failed current state, stops Minecraft and the scheduled backup service, proves the gate closed, validates a sibling restore, quarantines current data, atomically installs the historical candidate, overlays only the exact managed files from raw `R`, completes the activation journal, marks active-release state as `lineage=rollback` with immutable `R` and transaction ID, and leaves services stopped. It never deletes or reuses quarantine.
- [ ] Prepare writes `${STATE_DIR}/rollback/transactions/<transaction-id>/prepare.json` with schema `afterlight.rollback.prepare.v1`. The authenticated canonical receipt must bind transaction ID; canonical bundle path and ID; bundle archive, completion, historical-release, ledger, `pack.toml`, and `index.toml` digests; `H`; `R`; accepted `R` receipt and digest; raw `R` manifest digests; failed-current protected bundle ID and digest; pre-restore and prepared `${DATA_DIR}` device, inode, and full canonical tree-inventory digests; current managed-ledger bytes and digest; active-release state; candidate receipt; Packwiz, bootstrap, installer, and NeoForge provenance digests; completed journal path, state, and digest; quarantine path, device, inode, and full inventory digest; stopped container IDs and inspect digest; maintenance generation, close receipt, status proof, and live-rule digests; tool version; and predecessor receipt digest.
- [ ] The canonical tree inventory covers every relative path, object type, mode, owner, size, and regular-file SHA-256 beneath the bound root, rejects links and unsupported objects, and excludes no mutable world or runtime path. Prepare writes the inventory files beside the receipt, binds their digests, creates `${STATE_DIR}/rollback/pending.json` with the transaction ID and prepare-receipt digest, and durably flushes all files and directories before returning the exact activate command.
- [ ] Activate acquires or validates the one inherited operations-lock descriptor before reading the transaction. It requires the supplied receipt path to resolve beneath the named transaction directory, verifies its HMAC and detached digest against `pending.json`, rejects a consumed or second pending transaction, then revalidates every bundle, `H`, `R`, accepted-main, Pages, data-tree, ledger, active-release, provenance, journal, quarantine, stopped-service, closed-gate, and live-rule field. Any intervening byte, metadata, path identity, service, channel, gate, journal, or receipt mutation exits without starting Minecraft.
- [ ] Before any server start, activate creates and flushes one authenticated `activation-intent.json` with create-new semantics and atomically changes the transaction state from `prepared` to `activating`. It moves the gate from closed to tester-only using the exact tester-allowlist digest, force-recreates Minecraft, verifies health for `R`, and writes `activation.json` plus `${STATE_DIR}/rollback/consumed/<transaction-id>.json` before removing `pending.json`. A completed transaction can never activate again.
- [ ] Interruption, signal, failed health, or failed durable write must never produce `production-open`. Traps stop Minecraft and close the gate when possible; an incomplete activation intent remains durable, boot replay treats it as closed, and ordinary activate refuses it. `--resume` is allowed only for the same incomplete transaction after complete revalidation, preserves the original one-time intent, and cannot create a second activation or bypass a failed receipt check.
- [ ] After healthy tester-only activation, `rollback.sh attest-join` requires the same consumed transaction, active `R`, tester-only status proof, current health, and a released-client acceptance receipt for `R`, then records Shane's explicit pass with create-new semantics. `maintenance.sh open --mode production` must revalidate current accepted `R`, Pages parity, health, transaction, activation, join receipt, and tester-only generation while holding the operations lock, consume the join receipt into the production-open transition, and write the final gate and transaction receipts. No other command may perform this transition.
- [ ] Add integration tests for the exact operator sequence and commands in `server/README.md`: accepted `R` through `dev` and `main`, prepare, attempted mutation rejection, activate to tester-only, manual join attestation, and separate production open. Prove omitted, reordered, duplicated, interrupted, stale, cross-transaction, cross-bundle, cross-SHA, and cross-gate steps fail closed and leave durable forensic records.
- [ ] `recover.sh` requires empty data and state paths including dotfiles, validates the offsite-retrieved bundle and historical CI receipt, creates fresh RCON and receipt-authentication secrets, starts a new maintenance receipt chain in closed mode, restores to a sibling candidate, overlays the exact Packwiz SHA, rebuilds excluded runtime files, atomically publishes, marks active-release state as `lineage=recovery`, and verifies health while closed. It never imports a pending or consumed transaction from another host and can never open recovery lineage. Production reopening requires the operator to create accepted `R` and complete the normal local rollback prepare, activate, tester-only join, and production-open sequence, which replaces recovery lineage with the bound rollback transaction.
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

- [ ] Make health verify one container ID, running state, exact mounted data source, exact pinned image reference, required environment, no `PACKWIZ_URL`, container health, `mc-health`, RCON `list`, Java major 21, NeoForge version, current-start readiness log, active release SHA, managed-ledger digest, preserved Packwiz provenance digest in `${STATE_DIR}`, and an authenticated maintenance mode whose live-rule digest matches persisted state. Health reports gate mode but never changes it.
- [ ] Reject stale readiness lines by binding success to the current container start and expected SHA.
- [ ] Implement Chunky `start` with explicit world, `circle|square` shape, integer center, and radius. Default radius is 10,000 and documented maximum is 20,000. Do not implement trim.
- [ ] Use exact commands `chunky start`, `chunky progress`, `chunky pause [world]`, `chunky continue [world]`, and `chunky cancel [world]`.
- [ ] Require a protected backup before `start` and `continue`. Acquire the operations lock once, invoke backup with internal `--lock-held`, prove the gate remains closed, and keep the inherited descriptor open through completion, pause, or cancellation. Update, rollback, and recovery fail closed while Chunky is active or its state cannot be classified. Chunky tooling never reopens production.
- [ ] Add a pregen-to-backup test that proves the child receives the same inherited file descriptor and completes without self-deadlock. Add source and fake-command tests for healthy, unhealthy, stale, duplicate-container, wrong-mount, wrong-image, wrong-Java, wrong-SHA, RCON failure, and every conservative Chunky state.
- [ ] Record live-host-only checks separately: baseline firewall; gate precedence over Docker for IPv4 and IPv6; closed, tester-only, and production-open probes from allowed and denied external sources; established-session closure; authenticated reboot replay before Compose; `flock`; inherited descriptor behavior; same-filesystem rename; two-minute graceful stop; memory headroom; backup throughput; disk headroom; native image pull; arm64 pack boot; whitelist; voice UDP; encrypted empty-host recovery; rollback transaction interruption; released-client tester-only join; and separate production opening.
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

- [ ] Require an explicit accepted release SHA, HTTPS Pages pack URL, canonical acceptance receipt, and matching detached digest for a release Prism build. Run `release_gate.py accept` to create new receipt outputs, verify both Packwiz JAR hashes, and embed only those two installer JARs. Never embed the acceptance receipt, repository credentials, or release-state path.
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
- Create: `tools/finalize_rc.py`
- Create: `tools/tests/test_gauntlet_contract.py`
- Create: `tools/tests/test_finalize_rc.py`
- Modify: `docs/HANDOFF.md`

- [ ] Set pack version to `0.9.0-rc.1`, source `tools/versions.env`, run Packwiz refresh, and commit `pack.toml`, `index.toml`, and any Packwiz-managed metadata together.
- [ ] Pin every GitHub Action to a full commit SHA and pin an exact Go version. Extend CI with Python unit tests, static and runtime quest validation, `verify-pack.sh`, shell syntax, forbidden U+2014 scan, server boot, exports, distribution fixture inspection, archive fixture tests, secret scan, and final git cleanliness.
- [ ] Make the required `verify-and-export` job a pre-acceptance job. It may validate the checked-out SHA, immutable raw inputs, release tooling, and fixture Prism behavior, but it must not require current `main`, Pages parity, `release_gate.py accept`, or a release Prism build. Add a contract test that prevents self-waiting acceptance from entering the workflow.
- [ ] Upload logs only from the current failed run. Remove stale evidence before execution and include every relevant log and command transcript on failure.
- [ ] Give `tools/gauntlet.sh` explicit `preaccept` and `release` modes. Both require a clean detached full-SHA worktree and record SHA, operating system, architecture, Java, Go, Packwiz, Python, Docker, and Compose versions.
- [ ] Give `tools/finalize_rc.py publish --subject S --evidence E --tag v0.9.0-rc.1 --receipt RECEIPT --digest DIGEST --repo OWNER/REPO` sole authority for the final annotated tag and GitHub prerelease. It must reject `GITHUB_ACTIONS=true`, missing or noncanonical external receipt paths, any receipt subject other than `E`, digest mismatch, an unaccepted workflow or Pages identity, a non-direct-child `E`, a changed path outside the two evidence documents, noncurrent remote `main`, a dirty tree, a conflicting tag, or a conflicting release.
- [ ] Make the finalizer create and push the annotated tag only after all receipt checks, then create the prerelease from that exact tag with the complete canonical receipt and digest. If tag push succeeds but release creation is interrupted, a retry may only verify and reuse the identical existing tag object and message before creating the missing release. It must never move, delete, or recreate a remote tag, create a child evidence commit, wait for a workflow, or print credentials.
- [ ] Test the finalizer with fake Git and GitHub endpoints for tag-before-receipt attempts, stale `S` receipts, forged `E` receipts, digest mismatch, receipt files inside a worktree, workflow environment, moved `main`, Pages mismatch, disallowed `S..E` paths, preexisting lightweight or divergent tags, partial tag-push success, safe release-only resume, release metadata mismatch, API failure, and remote readback mismatch. Source-test `pack-ci.yml` to forbid any finalizer invocation.
- [ ] In pre-acceptance mode, run every acceptance-independent unit, static, manifest, server, Compose, maintenance-gate, backup, lock, rollback-transaction, recovery, distribution-fixture, export, secret, punctuation, shell, and cleanliness check. Do not query current Pages or build the final Prism archive.
- [ ] In full release mode, first require an external accepted receipt for the already completed exact-SHA `main` push workflow and Pages deployment, rerun the complete pre-acceptance suite, then run `release_gate.py accept` to new canonical receipt outputs, exact Pages and raw installs, the final Prism build and archive inspection, protected-backup gate proofs, backup and restore drills, failed-update closure, one-time two-phase rollback tests through tester-only mode, nested-lock tests, and final git cleanliness. Capture every command, receipt digest, and exit code.
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
- [ ] After exact `E` CI and Pages parity complete, run accepted mode from an external operator process, never from `pack-ci.yml` or any workflow whose success it authenticates:

  ```bash
  receipt="${RELEASE_STATE_DIR}/v0.9.0-rc.1/E-acceptance.json"
  python3 server/scripts/release_gate.py accept \
    --repo "${GITHUB_REPOSITORY}" \
    --sha "${E}" \
    --pages-url "${PAGES_URL}" \
    --receipt-out "${receipt}" \
    --digest-out "${receipt}.sha256"
  ```

  Require create-new outputs, reparse the canonical receipt, verify its exact SHA is `E`, recompute and compare the detached digest, and preserve both files outside every worktree. Failure, partial output, a moved `main`, changed Pages, or a selected run equal to `GITHUB_RUN_ID` blocks tagging.
- [ ] Run `tools/finalize_rc.py publish` only after the external `E` accepted-mode command succeeds. The finalizer puts `S`, `E`, the exact final `E` workflow run, attempt, and job identifiers, the exact Pages deployment identifier, parity hashes, the complete canonical `E` acceptance receipt, and its detached digest in immutable annotated tag `v0.9.0-rc.1`; pushes that tag; creates the GitHub prerelease from it; places the same receipt bytes and digest in release metadata or a public-safe receipt asset; and reads both remote objects back before success. Never commit the post-`E` receipt, create a child evidence commit, move or recreate the tag, or let a workflow wait for itself.
- [ ] Publish no restricted archives. Do not create `v1.0.0` in this autonomous run.
- [ ] Leave these manual acceptance items explicit for Shane: Prism import and sub-three-minute title screen; new-world quest UI and theme; chapters 1 through 8 playthrough; every Certification and hard gate; released-client dedicated-server join; two-user voice test; whitelist and firewall; update drill; induced update failure plus explicit rollback; and encrypted offsite empty-host restore on a replacement host.
- [ ] Shane measures the completed Supercritical Phase Shifter throughput and total wall time for the four-antimatter-pellet Isotopic Core requirement against the exact release candidate, records the evidence path, and decides whether balance changes are required before `1.0.0`. Automated agents leave this item unchecked and never infer the result.
- [ ] Shane manually records the exact multiplayer Seal matrix with two real accounts on the released client and server: two eligible players on one quest team each claim exactly one Seal; replay or repeated reward interaction cannot duplicate either Seal; a late joiner can claim after joining a team that already completed the finale; leaving, rejoining, and changing teams neither duplicates nor deadlocks the reward; one Seal can transfer to another player; and the recipient crafts Draconium Core, Dislocator, and Module Core while the transferred Seal remains exactly one. Automated agents leave this item unchecked and never claim it from static or headless evidence.
- [ ] Treat every deferred manual item as a blocker for `1.0.0` and for any claim that production is open, but not as a blocker for the correctly labeled `v0.9.0-rc.1` prerelease.
- [ ] Add `linux/arm64` support only after native pull, Java 21, NeoForge setup, complete pack boot, Chunky smoke, and gameplay checks pass on that architecture.
- [ ] Promote to `1.0.0` only after every manual acceptance item is recorded as passed against the exact release candidate lineage.
