# Plan 07 Architecture Audit

Date: 2026-08-08

Status: design gate corrected after round 2 crash, reboot, rollback-state, and universal-join review. No Docker, VPS, backup, recovery, CI, Pages, Prism, or release behavior is claimed by this document.

## Scope

The launch architecture was reviewed before implementation against the exact current itzg image manifests, Packwiz installer release bytes, NeoForge installer checksum, Docker Compose behavior, GitHub Actions APIs, GitHub Pages mutability, RCON secret handling, Chunky operations, Python archive extraction safety, nested Linux lock behavior, host ingress maintenance safety, untrappable kill windows, stale reboot state, rollback backup branch safety, transaction continuity, universal join evidence, and release-evidence ordering.

The initial review found nine Critical and nine Important design gaps. A completed follow-up contradiction review found seven cross-task defects in the rewritten plan: acceptance self-deadlock, unhandled Packwiz installer state, an incorrect release-candidate manual gate, nested lock reacquisition, backup exclusions that were not part of resolved Compose, client-unsafe rollback, and evidence self-reference. A subsequent pinned-source check found that online and offline backup enter different RCON and image-lock branches. Round 1 then corrected three independent failures: maintenance was prose rather than persisted access control, rollback prepare and activate lacked one-time binding, and tag creation lacked an external accepted-mode receipt for evidence SHA `E`.

Round 2 found four Critical and two Important residual gaps. Permissive rules could outlive an untrappable kill before open-state publication; boot could replay stale production-open; rollback prepare selected online backup after update failure had stopped Minecraft; prepare had no pre-mutation intent; activation had an unhandled consumed-plus-pending crash window; and install or update could open without general released-client join evidence. The corrected plan closes all six with timeout-bound permissions and an active reconciler, boot-closed epochs, stopped-service offline rollback backup, prepare intent plus resume or abandonment, finalize-only activation reconciliation, and one general join interface required by every production-open lineage. Implementation still requires test-first development, whole-project skeptical review, two accepted clean gauntlet runs, exact-SHA CI and Pages evidence, and the deferred live-host matrix.

## Threat Model and Corrections

The maintenance findings protect against Docker accepting traffic while prose says closed, an untrappable kill between permissive rule application and state publication, a dead reconciler, rule drift, a restored `/data` tree reverting access state, and reboot replaying yesterday's open decision before current release or health validation. Permanent rules now default to closed. Tester and production permissions are lease generations made only of kernel set elements with at most a 15-second timeout. A durable current-boot, current-reconciler authorization must precede any permissive lease, and an active reconciler renews at most every 5 seconds only after all state checks pass. Every reconciler process and every boot begins closed. Reopening requires fresh current-release validation, post-start closed health, tester-only authorization, tester-generation health, released-client join, and production-open actions.

The rollback findings protect against time-of-check to time-of-use substitution, wrong backup branch selection, mutation before durable intent, ambiguous crash points, receipt replay, and the consumed tombstone conflicting with a still-present pending pointer. Prepare now writes and flushes authenticated intent before any mutation, stops and proves both services stopped, invokes protected offline backup through the inherited lock, and journals every mutation with append-only progress. An incomplete prepare blocks Compose until exact resume or authenticated abandonment restores and verifies current state. Activation has distinct intent, activation, consumed, finalized, and pending states; finalize-only reconciliation can clear only an exact matching consumed-plus-pending window and cannot start or consume again.

The join finding protects normal install, update, reboot, or maintenance return from reaching production based only on server health. A general join attestation now requires tester-only access, a fresh current-container health receipt, the exact released-client artifact receipt, active release and lineage, current boot and gate generation, and explicit operator confirmation. Every production open requires fresh accepted-release revalidation, health, and join receipts. Rollback adds exact finalized transaction evidence; recovery lineage cannot open directly.

The evidence finding protects against tagging `E` after checking only CI and Pages, copying stale acceptance evidence from `S`, writing a post-commit fact into `E`, or making the workflow whose success is required wait for itself. The correction runs accepted mode externally only after exact `E` CI and Pages parity complete, writes canonical create-new receipt and digest files outside every worktree, and requires those exact bytes in annotated-tag and GitHub-release metadata before publication.

These controls defend against stale state, accidental or unauthorized unprivileged mutation, operator sequencing mistakes, interrupted or killed scripts, bounded reconciler failure, archive substitution, mutable branch or Pages drift, and receipt replay. They do not defend against a compromised root account that can replace both kernel rules and systemd units, a compromised GitHub or Pages trust root, theft of `${SECRETS_DIR}/receipt-auth.key`, a dishonest manual join attestation, malicious tester endpoints, or physical host compromise. Those events require credential rotation, host rebuild, and a new release acceptance cycle rather than reuse of local receipts.

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

Accepted mode writes schema `afterlight.release.acceptance.v1` as canonical UTF-8 JSON with sorted keys, fixed separators, and one trailing LF. The receipt binds repository, SHA, workflow, run, attempt, job, Pages deployment, immutable raw hashes, Pages hashes, clean client and server install results, and authenticated source completion times. A detached SHA-256 covers those exact bytes. Create-new and durability rules prevent silent overwrite or partial success. Local wall-clock fields are excluded, so identical remote evidence produces identical receipt bytes.

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
- Recovery regenerates operational properties plus fresh RCON and receipt-authentication secrets, starts a new closed maintenance chain, and never imports a pending or consumed rollback transaction from another host.
- Maintenance and rollback authority lives under `${STATE_DIR}`, never under `/data`, quarantine, or a backup bundle. `${SECRETS_DIR}/receipt-auth.key` authenticates local state and remains outside every archive.

Task 1 creates reviewed source file `server/backup-excludes.txt`, mounts it read-only at `/etc/afterlight-backup-excludes.txt`, sets `EXCLUDES=""` to neutralize the image default, and sets `EXCLUDES_FILE` to that exact path in the backup service. The file excludes `.rcon-cli.env`, `.rcon-cli.yaml`, `server.properties`, the host-created `.paused` marker, every JAR, cache directories, logs, and known transient files before the backup image creates an archive. There is no second inline exclusion authority.

Task 2 tests inspect canonical `docker compose config --format json` to prove the exact resolved mount and environment. Successful backup tests inspect archive membership to prove every reviewed class, including `.paused`, is absent at any depth. The archive guard remains a second boundary and rejects any forbidden member injected despite the exclusion file.

Pinned `docker-mc-backup` source has two materially different execution paths. Without `/data/.paused`, the normal branch loads RCON, performs a readiness `save-on`, acquires `${BACKUP_DIR}/.mc-backup-lock`, runs `save-off`, optional `save-all flush` and sync, creates the archive, and restores `save-on` with its own exit trap. The host wrapper validates online prerequisites but does not duplicate that RCON mutation sequence.

The pinned image enters its offline path only when `/data/.paused` exists. That paused branch bypasses both RCON and `.mc-backup-lock`. Offline backup therefore requires Minecraft and the scheduled sidecar to be stopped, retains the shared inherited host operations lock as its serialization authority, refuses a preexisting marker, creates `.paused` only after stop verification, and trap-cleans only the marker created by that invocation on every exit path. Online and offline tests assert their separate branch configuration and postconditions.

Each accepted bundle includes a checksum, authenticated release receipt, exact managed ledger, exact `pack.toml` and `index.toml` snapshots with SHA-256 values, and a completion marker. A protected bundle also includes the exact maintenance close receipt, closed-status proof, and both digests. Scheduled and protected backups have separate retention classes, protected bundles are never pruned automatically, and upstream `restore-backup` and `restore-tar-backup` helpers remain forbidden. Empty-host recovery requires an encrypted copy stored independently from the VPS.

## Maintenance Access Gate

The gate has exactly three authenticated modes:

1. `closed` has no permissive lease elements. Permanent rules drop new and established traffic to Minecraft TCP `25565` and voice UDP `24454` from external, host, loopback, and peer-container paths, leave unpublished internal RCON control available, terminate existing game sessions, and require zero connected players when Minecraft is running.
2. `tester-only` has one nonce-bound lease generation implemented only by set elements with at most 15-second kernel timeouts and permits only canonical IPv4 or IPv6 CIDRs from mode `0600` `${SECRETS_DIR}/maintenance-testers.txt`. Receipts record only the allowlist SHA-256 and entry count.
3. `production-open` has one nonce-bound lease generation whose elements have the same timeout and removes only AFTERLIGHT's maintenance restriction. It never broadens the baseline host firewall or bypasses the Minecraft whitelist.

`server/scripts/maintenance.sh` is the sole public transition authority. Its authenticated close implementation is also the only internal transition a boot gate or reconciler may invoke. `close --reason TOKEN` removes lease elements before publishing closed. `status --require MODE --receipt-out RECEIPT` validates current boot, durable state, kernel lease, reconciler heartbeat, live rules, connections, service, and players. Tester opening requires exact accepted release and current health receipts. Production opening requires those plus a general join receipt for every eligible lineage and exact finalized transaction fields for rollback.

`${STATE_DIR}/maintenance/boot.json` binds the Linux boot ID, random boot nonce, gate-service start, and mandatory boot-close receipt. `${STATE_DIR}/maintenance/state.json` is valid only for that boot. Intents and create-new open authorizations live under `${STATE_DIR}/maintenance/intents/` and `open-authorizations/`; completed transitions and proofs live under `receipts/` and `proofs/`; general join receipts live under `joins/`; health receipts live under `${STATE_DIR}/health/`. Root-owned `/run/afterlight-gate/reconciler.json` contains a random process epoch plus heartbeat and is never durable authority. Every local record has canonical JSON, HMAC-SHA-256, exact mode and ownership, predecessor digest, boot, reconciler, and container identity where applicable, state generation, active release and lineage, and bound input digests.

Opening validates inputs and freshly reruns accepted mode before writing and flushing transition intent plus one-time authorization bound to the current boot and reconciler process epoch. Only then can it install one lease generation composed solely of set elements with 15-second maximum timeouts, prove the nonce, process epoch, membership, remaining timeouts, and live-rule digest, publish completed state and receipt, start renewal, and wait for a matching reconciler heartbeat. A kill after lease installation has prior durable authorization but no unbounded permission: without completed state and same-process heartbeat, every element expires within 15 seconds and cannot renew.

Every `gate_reconciler.py` process first removes all lease elements, creates a new random runtime epoch, uses the operations lock to publish the shared authenticated close transition, and proves closed. It then checks at least every 5 seconds and renews only the exact authorized lease elements when boot ID, process epoch, HMAC, nonce, state generation, active release and lineage, health and join digests, rollback-state checks, rule digest, lease identity, and systemd dependencies all match. It never renews during unresolved rollback state. In closed mode, only an exact activating transaction whose operations lock remains held may keep Minecraft running, without any lease, while `rollback.sh activate` completes. Every other failure removes all lease elements, proves closed, and stops Compose within one interval. `afterlight-gate-reconciler.service` uses `Type=notify`, `NotifyAccess=main`, `Restart=always`, and `WatchdogSec=10s`; it accepts `READY=1` only after startup closure and `WATCHDOG=1` only after a complete successful loop, and it is required by `afterlight-compose.service`. Every restart creates a new closed epoch rather than replaying prior open authority.

Every boot ignores persisted tester-only or production-open authority. `afterlight-maintenance-gate.service` removes every lease, writes and flushes a new boot-closed receipt, and proves closed before the dependent gate reconciler and Compose units can start. When no rollback blocker exists, Minecraft starts closed. Any unresolved or inconsistent rollback state blocks startup. Reopening requires accepted release revalidation, health from that new container start, tester-only access, a released-client join receipt for that boot and container, and a separate production-open command.

`maintenance.sh attest-join` is general to install, update, reboot, protected-maintenance return, and rollback. It requires tester-only state, fresh same-container health created after tester-only opening for that exact gate generation, exact released-client artifact receipt, active SHA and lineage, explicit operator confirmation, a canonical create-new receipt output beneath `${STATE_DIR}/maintenance/joins/`, and rollback transaction fields when applicable. Health and join receipts expire after 600 seconds for use in a new transition. Production open always requires fresh accepted-release revalidation plus matching unexpired tester-generation health and join receipts at authorization. Once production-open is durably published, renewal verifies those immutable digests and current state but does not close solely because an input receipt later expires. Any opening after close, restart, or reboot requires new health and join receipts. Recovery lineage cannot open directly.

Protected backup always invokes close and then status under the same inherited operations lock before starting the backup image. Bundle publication rechecks the same generation and live-rule digest. A failed proof, player reconnect, rule change, or reconciler mismatch produces no completed protected bundle and leaves the gate closed. Scheduled online backup is the only backup class that may run without changing an already authenticated gate mode.

## Lock Model

Every top-level mutating command opens and acquires `${STATE_DIR}/ops.lock` once, keeps that one Linux file descriptor open for the full operation, and exports its number as `AFTERLIGHT_OPS_LOCK_FD`. A nested maintenance command receives the inherited open descriptor and uses an internal `--lock-held` contract. It validates that the descriptor is numeric, open, and points through Linux `/proc/self/fd` to the canonical operations lock, then requires nonblocking `flock -n` on that same descriptor to succeed. The inherited locked open-file description succeeds without reacquisition; a separately opened descriptor fails while the parent lock is held.

Direct `backup.sh` calls acquire the operations lock normally. Backup calls nested beneath update, rollback, or Chunky reuse the parent's descriptor. Tests cover update-to-backup, rollback-to-backup, and pregen-to-backup execution, assert that the same descriptor remains held, and fail forged or separately opened descriptors. The normal online image branch adds `${BACKUP_DIR}/.mc-backup-lock` as a separate archive-serialization lock with the existing fixed acquisition order. The offline paused branch has no image lock and remains serialized by the inherited host operations descriptor. No nested path may reacquire the operations lock and self-deadlock.

Maintenance transitions, open authorization, join attestation, rollback prepare intent and progress, resume, abandonment, activation intent, transaction consumption, finalize-only reconciliation, and production opening all use that same operations lock. An exact activating transaction may keep Minecraft running behind closed ingress only while that lock remains held. A status, health, or transaction proof is therefore ordered with the state it authenticates rather than being a racy observation from another process.

## Update and Rollback Model

An update stages before downtime, takes a protected backup that closes and proves the gate, and activates only validated pack-managed files. Packwiz updates pack-managed paths in `/data`; the prohibition is against automatic world restore, world deletion, or rollback. A healthy update marks `lineage=update`, starts the new container closed, and writes fresh health. The operator then opens tester-only, joins with the exact released client, records the general join receipt, and separately opens production.

An update health failure stops Minecraft, leaves the gate closed, exits with code `6`, preserves logs, candidate files, Packwiz provenance, backup, ledger, journal, quarantine state, and receipts, and writes one authenticated rollback-request receipt. It prints the fixed runbook path and exact failed bundle values. It cannot print a valid prepare command until the operator has created rollback SHA `R` and an accepted `R` receipt, and it never restores world data automatically.

Rollback remains a truthful two-phase operation, but the operator-owned Git promotion now precedes data-changing prepare so prepare can bind the exact rollback release:

1. From authenticated bundle snapshots for historical SHA `H`, the operator creates and reviews normal rollback commit `R`, pushes exact `R` through `dev`, promotes it unchanged to `main`, waits for exact-SHA CI and Pages parity, and runs accepted mode externally. Maintenance tooling never commits, reverts, pushes, mutates branches or tags, or calls a GitHub write API.
2. `rollback.sh prepare` performs read-only authentication of named bundle, `H`, `R`, canonical accepted `R` receipt, raw-`R` equality with historical snapshots, current accepted `main`, Pages, current data identity, ledger, provenance, journal, quarantine, services, gate generation, and planned paths. Before any gate, service, backup, marker, rename, extraction, activation, or data mutation, it create-new publishes and flushes schema `afterlight.rollback.prepare-intent.v1` plus digest. The intent binds the transaction ID, every input digest, root device and inode, active release and lineage, current state observations, planned paths, tool version, and predecessor digest.
3. Under the inherited operations lock, prepare closes and proves the gate, stops Minecraft and scheduled backup idempotently, and proves both stopped. It then invokes `backup.sh --class protected --reason rollback-current --offline --lock-held`. This must use the pinned image's paused branch with the host-created marker, no RCON, and no `.mc-backup-lock` assertion.
4. Prepare writes authenticated append-only progress before and after every gate close and proof, service stop, offline backup, marker lifecycle, inventory, candidate, quarantine rename, publication, raw-`R` overlay, journal, ledger, provenance, and final inventory step. Root device, inode, path, and digest checkpoints distinguish not-started, completed, and crash-between-rename states.
5. Completed prepare marks `lineage=rollback` and writes schema `afterlight.rollback.prepare.v1`, binding intent and progress-chain tips; bundle and archive metadata; `H`; `R`; release evidence; raw and historical manifests; failed-current offline bundle; pre-restore and prepared inventories; ledger; active release; candidate and installer provenance; completed journal; quarantine; stopped services; closed gate; and predecessor digests. It then writes `pending.json` with phase `prepared` and flushes every parent directory. A receipt without its exact pointer is not completed prepared state and remains blocked for exact resume.
6. Exact transaction files are `prepare-intent.json`, its digest, `prepare-progress/<sequence>.json`, `prepare.json`, its digest, all inventories, `prepare-abandoned.json`, `activation-intent.json`, `activation.json`, `activation-finalized.json`, `join.json`, and `production-open.json`. The consumed tombstone remains under `${STATE_DIR}/rollback/consumed/`. State modes and create-new durability remain unchanged.
7. `prepare --resume` accepts only the original intent and transaction. It revalidates immutable inputs and progress, reconciles exact path identities including receipt-without-pointer, and repeats only idempotent or incomplete safe steps. `rollback.sh abandon` is idempotent for the exact pre-activation transaction, restores and verifies pre-prepare data, ledger, provenance, journal, quarantine, and root identity from authenticated progress, writes abandonment, removes only a matching pending pointer, and clears the blocker only after directory-flushed proof. Failure leaves ingress closed, services stopped, and Compose blocked. A valid abandonment receipt is terminal and makes prepare resume, activate, finalize-only, and receipt reuse fail.
8. Any prepare intent blocks ordinary Compose and systemd startup until exact abandonment is fully reconciled or activation is finalized with no pending pointer. Activate authenticates prepared pending state and every bound input under the operations lock. It writes activation intent, changes pending phase to `activating`, and becomes the sole exception allowed to start Minecraft behind closed ingress while its lock remains held. It writes closed-mode health for `R`. While still closed, publication order is activation receipt, consumed tombstone, activation-finalized receipt, pending unlink, then parent-directory flush. Only after no unresolved rollback state remains may the command create a timeout-bound tester lease using closed health and then write tester-generation health.
9. Ordinary activate and resume reject consumed state. Before consumption, resume authenticates and continues only missing idempotent steps, reusing an existing health output only when it exactly matches the transaction and current container. `--finalize-only` is the sole reconciliation path for an exact matching pending pointer, activation receipt with authenticated closed health, and consumed tombstone. It revalidates exact `R` data and transaction state, then may write a missing finalized receipt and remove that exact pending pointer. It cannot start, restart, change gate mode, consume again, or alter transaction inputs, and the live service may be running closed or stopped. Finalized plus no pending is already complete and does not use finalize-only. If tester health is absent after any consumed state, the operator closes and proves the gate, starts the normal Compose unit behind closed ingress, creates new closed health, and performs explicit tester-only access plus tester health. A mismatched set fails closed.
10. SIGKILL before or after every prepare, abandonment, activation, tester-authorization, and tester-health publication boundary has one defined outcome: exact resume before consumption, idempotent abandonment, finalize-only for consumed plus pending, or explicit post-finalization closed restart and tester recovery. Unresolved state forces the gate closed, blocks unattended Compose on boot, and stops a closed activation service within 5 seconds after its lock owner dies.
11. Shane joins with the released client while tester-only. `rollback.sh attest-join` delegates to the general join interface and adds finalized activation plus consumed digests. Production open is a later command that freshly reruns accepted `R` validation and requires matching current-boot health, released-client join, transaction, activation, lineage, and tester generation. No rollback phase opens production implicitly.

The operator command contract begins with external acceptance of `R` and one prepare:

```bash
r_receipt="${STATE_DIR}/rollback/requests/${request_id}/R-acceptance.json"
python3 server/scripts/release_gate.py accept \
  --repo "${GITHUB_REPOSITORY}" \
  --sha "${R}" \
  --pages-url "${PAGES_URL}" \
  --receipt-out "${r_receipt}" \
  --digest-out "${r_receipt}.sha256"

server/scripts/rollback.sh prepare \
  --backup "${bundle}" \
  --rollback-sha "${R}" \
  --release-receipt "${r_receipt}" \
  --confirm "${bundle_id}"
```

If prepare is interrupted, choose exactly one authenticated action. Resume continues the same transaction toward prepared state:

```bash
server/scripts/rollback.sh prepare \
  --resume "${transaction_id}" \
  --intent "${STATE_DIR}/rollback/transactions/${transaction_id}/prepare-intent.json" \
  --confirm "${transaction_id}"
```

Abandon restores and verifies the pre-prepare state and ends the transaction. No activation or opening command follows a successful abandonment:

```bash
server/scripts/rollback.sh abandon \
  --transaction "${transaction_id}" \
  --intent "${STATE_DIR}/rollback/transactions/${transaction_id}/prepare-intent.json" \
  --confirm "${transaction_id}"
```

After prepare or resume returns durable prepared state, run normal activation path A:

```bash
server/scripts/rollback.sh activate \
  --transaction "${transaction_id}" \
  --receipt "${STATE_DIR}/rollback/transactions/${transaction_id}/prepare.json" \
  --confirm "${transaction_id}" \
  --closed-health-out "${closed_health_receipt}" \
  --tester-health-out "${health_receipt}"
```

If path A was killed before consumption, resume only the same activation with the same output paths. Existing output files must authenticate as exact transaction outputs:

```bash
server/scripts/rollback.sh activate \
  --transaction "${transaction_id}" \
  --receipt "${STATE_DIR}/rollback/transactions/${transaction_id}/prepare.json" \
  --confirm "${transaction_id}" \
  --closed-health-out "${closed_health_receipt}" \
  --tester-health-out "${health_receipt}" \
  --resume
```

After consumption, never run path A or activation resume. If exact matching consumed, activation, and pending state remains, first run finalize-only. If finalized state already has no pending pointer, skip this command:

```bash
server/scripts/rollback.sh activate \
  --transaction "${transaction_id}" \
  --receipt "${STATE_DIR}/rollback/transactions/${transaction_id}/prepare.json" \
  --confirm "${transaction_id}" \
  --finalize-only
```

If tester health was not returned after either consumed-state outcome, use the same explicit recovery sequence. Finalize-only never starts a service. Close and prove the gate, start the normal Compose unit behind closed ingress, and create health from the resulting current container start:

```bash
server/scripts/maintenance.sh close \
  --reason rollback-post-finalize-recovery

server/scripts/maintenance.sh status \
  --require closed \
  --receipt-out "${closed_status_after_finalize}"

systemctl start afterlight-compose.service

server/scripts/healthcheck.sh \
  --expect-sha "${R}" \
  --receipt-out "${closed_health_after_finalize}"

server/scripts/maintenance.sh open \
  --mode tester-only \
  --release-receipt "${r_receipt}" \
  --health-receipt "${closed_health_after_finalize}" \
  --transaction "${transaction_id}"

server/scripts/healthcheck.sh \
  --expect-sha "${R}" \
  --receipt-out "${health_receipt}"
```

Both activation paths continue here only after `${health_receipt}` names fresh tester-generation health for the current boot and container:

```bash
server/scripts/rollback.sh attest-join \
  --transaction "${transaction_id}" \
  --health-receipt "${health_receipt}" \
  --client-release-receipt "${released_client_receipt}" \
  --confirm "${transaction_id}"

server/scripts/maintenance.sh open \
  --mode production \
  --release-receipt "${r_receipt}" \
  --health-receipt "${health_receipt}" \
  --transaction "${transaction_id}" \
  --join-receipt "${STATE_DIR}/rollback/transactions/${transaction_id}/join.json"
```

Install, update, reboot, and return from protected maintenance use the same general opening sequence without rollback arguments:

```bash
server/scripts/healthcheck.sh \
  --expect-sha "${release_sha}" \
  --receipt-out "${closed_health_receipt}"

server/scripts/maintenance.sh open \
  --mode tester-only \
  --release-receipt "${release_receipt}" \
  --health-receipt "${closed_health_receipt}"

# Join with the released client, then capture health in tester-only mode.
server/scripts/healthcheck.sh \
  --expect-sha "${release_sha}" \
  --receipt-out "${tester_health_receipt}"

server/scripts/maintenance.sh attest-join \
  --release-receipt "${release_receipt}" \
  --health-receipt "${tester_health_receipt}" \
  --client-release-receipt "${released_client_receipt}" \
  --confirm "${release_sha}" \
  --receipt-out "${join_receipt}"

server/scripts/maintenance.sh open \
  --mode production \
  --release-receipt "${release_receipt}" \
  --health-receipt "${tester_health_receipt}" \
  --join-receipt "${join_receipt}"
```

`server/README.md` must show how each variable is obtained from a preceding receipt, mark activation path A and path B as mutually exclusive, print the exact expected mode after every command, and document lease expiry, reboot closure, interruption, resume, finalize-only, abandonment, Compose blockers, and forensic paths. Empty-host recovery creates fresh local secrets and closed gate state, marks active release `lineage=recovery`, and cannot open production. To reopen, the operator creates accepted `R` and completes the normal local rollback prepare, activate, tester-only join, and production-open sequence, replacing recovery lineage with the bound rollback transaction. Restoring or starting a server alone is not evidence that the mutable client channel is safe.

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

Only after those remote events complete does an external operator process run `release_gate.py accept` for exact `E`. The caller is outside `pack-ci.yml`, and accepted mode still rejects a selected run equal to `GITHUB_RUN_ID`. It writes create-new `${RELEASE_STATE_DIR}/v0.9.0-rc.1/E-acceptance.json` and `.sha256` files outside every worktree. The operator reparses the receipt, confirms its subject is `E`, and recomputes its detached digest before any tag command.

`tools/finalize_rc.py publish` is the sole final publication interface and is implemented before subject freeze. It rejects workflow execution, receipts inside a worktree, noncanonical or mismatched receipt bytes, wrong subject or parent, disallowed `S..E` paths, moved `main`, conflicting tags or releases, and remote evidence mismatch. Only after validation does it create and push the annotated tag, then create the GitHub prerelease. A retry after tag-push interruption may verify and reuse only the identical tag object and message to create a missing release; it can never move, delete, or recreate the tag.

```bash
e_receipt="${RELEASE_STATE_DIR}/v0.9.0-rc.1/E-acceptance.json"
python3 server/scripts/release_gate.py accept \
  --repo "${GITHUB_REPOSITORY}" \
  --sha "${E}" \
  --pages-url "${PAGES_URL}" \
  --receipt-out "${e_receipt}" \
  --digest-out "${e_receipt}.sha256"

python3 tools/finalize_rc.py publish \
  --subject "${S}" \
  --evidence "${E}" \
  --tag v0.9.0-rc.1 \
  --receipt "${e_receipt}" \
  --digest "${e_receipt}.sha256" \
  --repo "${GITHUB_REPOSITORY}"
```

The immutable annotated tag `v0.9.0-rc.1` points to `E`. Its tag message contains `S`, `E`, the exact final `E` workflow run, attempt, and job identifiers, Pages deployment identifier, parity hashes, the complete canonical `E` acceptance receipt, and its detached digest. The GitHub prerelease repeats those exact bytes and digest in release metadata or a public-safe receipt asset. Remote readback must match before announcement. This places evidence that necessarily occurs after `E` in tag and release metadata without modifying `E`, creating a child evidence commit, or moving or recreating the tag.

## Executable Release Sequence

1. Implement Tasks 1 through 5 and the Task 6 CI and gauntlet contracts.
2. Run all pre-acceptance checks without requiring accepted `main`, current Pages, or a release Prism archive.
3. Run whole-project skeptical review, fix every Critical and Important finding, rerun focused checks, and rerun the full pre-acceptance suite.
4. Freeze the final implementation commit as `S`, push exact `S` to `dev`, and require exact `S` dev CI success.
5. Promote exact `S` to `main`, wait for exact completed successful `S` main CI and Pages deployment, and run accepted mode externally.
6. Run two clean full release gauntlets at `S`, each including accepted release gating and the final Prism build.
7. Record all evidence and manual deferrals in direct child `E`, with no change outside the two named evidence documents.
8. Promote exact `E` through `dev` and `main`, then require exact completed `E` CI and Pages parity.
9. Run accepted mode externally for `E`, durably preserve and verify its canonical receipt plus digest outside the repository, then create the annotated tag and GitHub prerelease with those exact post-`E` receipts in tag and release metadata.
10. Treat release publication and server access as separate gates. The tag never reopens a host. Install, update, reboot, protected-maintenance return, and rollback all start closed and require their own current release, post-start closed health, tester-only authorization, tester-generation health, released-client join, and explicit production-open sequence. Recovery lineage remains closed until a normal accepted local rollback replaces it, then the rollback opening contract applies.
11. Treat any later implementation change as a new subject and restart from skeptical review. Never patch between the final accepted gauntlets and the tag.

## Deferred Live Evidence

These checks cannot be truthfully completed by plan text or a Mac-only authoring session:

- Baseline VPS firewall exposes only Minecraft TCP and voice UDP when maintenance is production-open.
- Permanent default-drop gate rules precede Docker for IPv4 and IPv6; every permission has a prior durable same-process authorization, expires within 15 seconds without renewal, closes into a new epoch after reconciler death or SIGKILL, and closes after watchdog stall, rule drift, missing state, or divergent state.
- Host filesystem provides reliable `flock`, inherited descriptor behavior, and same-filesystem atomic rename.
- Graceful stop finishes inside two minutes without exit 137.
- Ten-gigabyte heap remains below the 13 GB container limit under gameplay and Chunky load.
- Backup throughput, restore throughput, free-space checks, and quarantine capacity fit the real world size.
- Every host reboot ignores persisted open state, proves closed before Compose, restores the stack without creating a new world, and requires fresh current-release, post-start health, tester-only, join, and production-open evidence.
- Two released clients join, general join attestation works after install, update, reboot, and protected-maintenance return, whitelist works, and voice chat works over UDP.
- Installed Chunky RCON output is classified conservatively for active, paused, complete, and unknown states.
- The full pack boots and plays on arm64.
- An encrypted offsite bundle restores onto a genuinely empty replacement host.
- A real protected backup proves the closed gate before archive creation and cannot publish after gate drift or player reconnect.
- A real update failure remains closed and rollback prepare proves both services stopped before the pinned offline protected-backup branch, with no RCON or image-lock claim.
- SIGKILL at every rollback prepare and abandonment boundary yields exact resume or terminal authenticated abandonment. SIGKILL across activation and tester publication yields pre-consumption resume, consumed-plus-pending finalize-only, or post-finalization closed restart and tester recovery without receipt reuse.
- A released client joins the accepted rollback release in tester-only mode with fresh tester-generation health before a separate production-open command.

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
