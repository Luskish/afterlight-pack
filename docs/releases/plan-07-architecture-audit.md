# Plan 07 Architecture Audit

Date: 2026-08-09

Status: design gate corrected after round 3 serialization, general-operation recovery, exact-client-lineage, and maintenance-terminal review. No Docker, VPS, backup, recovery, CI, Pages, Prism, or release behavior is claimed by this document.

## Scope

The launch architecture was reviewed before implementation against the exact current itzg image manifests, Packwiz installer release bytes, NeoForge installer checksum, Docker Compose behavior, GitHub Actions APIs, GitHub Pages mutability, RCON secret handling, Chunky operations, Python archive extraction safety, nested Linux lock behavior, host ingress maintenance safety, renewal-versus-close concurrency, untrappable kill windows, stale reboot state, general mutation transaction continuity, rollback backup branch safety, universal join evidence, exact client lineage, and release-evidence ordering.

The initial review found nine Critical and nine Important design gaps. A completed follow-up contradiction review found seven cross-task defects in the rewritten plan: acceptance self-deadlock, unhandled Packwiz installer state, an incorrect release-candidate manual gate, nested lock reacquisition, backup exclusions that were not part of resolved Compose, client-unsafe rollback, and evidence self-reference. A subsequent pinned-source check found that online and offline backup enter different RCON and image-lock branches. Round 1 then corrected three independent failures: maintenance was prose rather than persisted access control, rollback prepare and activate lacked one-time binding, and tag creation lacked an external accepted-mode receipt for evidence SHA `E`.

Round 2 found four Critical and two Important residual gaps. Permissive rules could outlive an untrappable kill before open-state publication; boot could replay stale production-open; rollback prepare selected online backup after update failure had stopped Minecraft; prepare had no pre-mutation intent; activation had an unhandled consumed-plus-pending crash window; and install or update could open without general released-client join evidence. That correction added timeout-bound permissions and an active reconciler, boot-closed epochs, stopped-service offline rollback backup, prepare intent plus resume or abandonment, finalize-only activation reconciliation, and one general join interface required by every production-open lineage.

Round 3 found three Critical and one Important residual gaps. Renewal could validate an old authorization and republish its lease after close removed it; install, update, and recovery lacked rollback-grade crash transactions; the final tag target `E` lacked an exact client release receipt; and a killed maintenance intent had no authenticated terminal reconciliation. The corrected plan serializes every gate observation and transition, gives every data or active-release mutation pre-mutation intent plus boot blocking and exact recovery, creates an `E` client receipt by read-only authentication of both byte-identical `S` Prism artifacts, and requires every killed maintenance transition to end in a proved-closed terminal before another transition. Implementation still requires test-first development, whole-project skeptical review, two accepted clean gauntlet runs, exact-SHA CI and Pages evidence, and the deferred live-host matrix.

## Threat Model and Corrections

The maintenance findings protect against Docker accepting traffic while prose says closed, an untrappable kill between permissive rule application and state publication, a dead reconciler, rule drift, a restored `/data` tree reverting access state, reboot replaying yesterday's open decision, and a paused renewal restoring old permissions after close begins. Permanent rules default to closed. Tester and production permissions are lease generations made only of kernel set elements with at most a 15-second timeout. A durable current-boot, current-reconciler authorization must precede any permissive lease. A dedicated gate-transition lock serializes validation, renewal, close, status, reconciliation, and live-rule publication. Close owns new logical and kernel generations, removes all leases, then re-proves zero permissive elements before releasing that lock. Every reconciler process and boot begins closed. Reopening requires fresh current-release validation, post-start closed health, tester-only authorization, tester-generation health, released-client join, and production-open actions.

The general-operation finding protects against SIGKILL leaving a candidate, secret, protected backup, service, data tree, ledger, provenance, journal, quarantine, active-release record, or health receipt in a combination that ordinary boot mistakes for complete. Install, update, and recovery now authenticate read-only inputs first, publish one intent and pending pointer before their first mutation, journal before and after every mutation boundary, block ordinary Compose while unresolved, and finish through exact resume, authenticated safe abandonment, or durable success. An update that has crossed its irreversible publication boundary may instead terminalize rollback-required failure with a persistent blocker bound into rollback prepare and cleared only by successful activation finalization.

The rollback findings protect against time-of-check to time-of-use substitution, wrong backup branch selection, mutation before durable intent, ambiguous crash points, receipt replay, and the consumed tombstone conflicting with a still-present pending pointer. Prepare now writes and flushes authenticated intent before any mutation, stops and proves both services stopped, invokes protected offline backup through the inherited lock, and journals every mutation with append-only progress. An incomplete prepare blocks Compose until exact resume or authenticated abandonment restores and verifies current state. Activation has distinct intent, activation, consumed, finalized, and pending states; finalize-only reconciliation can clear only an exact matching consumed-plus-pending window and cannot start or consume again.

The join finding protects normal install, update, reboot, or maintenance return from reaching production based only on server health. A general join attestation now requires tester-only access, a fresh current-container health receipt, the exact released-client artifact receipt, active release and lineage, current boot plus logical and kernel gate generations, and explicit operator confirmation. Every production open requires fresh accepted-release revalidation, health, and join receipts. Rollback adds exact finalized transaction evidence; recovery lineage cannot open directly.

The evidence findings protect against tagging `E` after checking only CI and Pages, copying stale acceptance or client evidence from `S`, silently rebuilding the gauntleted client, writing a post-commit fact into `E`, or making the workflow whose success is required wait for itself. The correction runs accepted mode externally only after exact `E` CI and Pages parity complete, then creates an exact `afterlight.client.release.v1` receipt for `E` by read-only authentication of both preserved byte-identical `S` gauntlet archives and their receipts. Both canonical receipts and detached digests live outside every worktree and must appear in annotated-tag and GitHub-release metadata before publication.

The maintenance-terminal finding protects against an intent surviving a kill with no truthful committed or abandoned outcome. Every transition now publishes exactly one authenticated `committed` or `abandoned-closed` terminal. `maintenance.sh reconcile` can only invalidate the interrupted authorization, close into new logical and kernel generations, prove zero permissive elements, and record the prior intent and observed rule state. It cannot resume an interrupted open. Until this terminal exists, every later transition and ordinary Compose start is blocked.

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
6. Two full release gauntlets run at `S` from separate fresh worktrees. Each gauntlet independently includes accepted-mode release gating, clean client and server installs, and the final Prism build. Their external archives and client receipts must prove identical bytes.
7. Any required implementation fix or archive difference invalidates `S`. The process returns to skeptical review, freezes a new subject, promotes it, and starts both accepted gauntlets again.
8. Evidence SHA `E` is the direct child of `S` and changes only the two named evidence documents. Exact `E` is promoted unchanged through `dev` and `main`, then reaches exact-SHA CI and Pages parity.
9. An external process runs accepted mode for `E`, preserves its canonical receipt and digest, and then creates the exact `E` client receipt by authenticating both unchanged `S` gauntlet artifacts. No workflow being accepted performs or waits for either action.
10. The annotated tag and GitHub prerelease are created only after both `E` receipts verify, and their immutable metadata preserves both canonical receipts and detached digests.

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
- Empty-host install or recovery first completes the one-time `operation_state.py init-host` trust bootstrap. Recovery creates its fresh RCON secret only after durable operation intent, starts a new closed maintenance chain, and never imports operation or rollback authority from another host.
- Maintenance, operation, and rollback authority lives under `${STATE_DIR}`, never under `/data`, quarantine, or a backup bundle. `${SECRETS_DIR}/receipt-auth.key` authenticates local state and remains outside every archive.

Task 1 creates reviewed source file `server/backup-excludes.txt`, mounts it read-only at `/etc/afterlight-backup-excludes.txt`, sets `EXCLUDES=""` to neutralize the image default, and sets `EXCLUDES_FILE` to that exact path in the backup service. The file excludes `.rcon-cli.env`, `.rcon-cli.yaml`, `server.properties`, the host-created `.paused` marker, every JAR, cache directories, logs, and known transient files before the backup image creates an archive. There is no second inline exclusion authority.

Task 2 tests inspect canonical `docker compose config --format json` to prove the exact resolved mount and environment. Successful backup tests inspect archive membership to prove every reviewed class, including `.paused`, is absent at any depth. The archive guard remains a second boundary and rejects any forbidden member injected despite the exclusion file.

Pinned `docker-mc-backup` source has two materially different execution paths. Without `/data/.paused`, the normal branch loads RCON, performs a readiness `save-on`, acquires `${BACKUP_DIR}/.mc-backup-lock`, runs `save-off`, optional `save-all flush` and sync, creates the archive, and restores `save-on` with its own exit trap. The host wrapper validates online prerequisites but does not duplicate that RCON mutation sequence.

The pinned image enters its offline path only when `/data/.paused` exists. That paused branch bypasses both RCON and `.mc-backup-lock`. Offline backup therefore requires Minecraft and the scheduled sidecar to be stopped, retains the shared inherited host operations lock as its serialization authority, refuses a preexisting marker, creates `.paused` only after stop verification, and trap-cleans only the marker created by that invocation on every exit path. Online and offline tests assert their separate branch configuration and postconditions.

Each accepted bundle includes a checksum, authenticated release receipt, exact managed ledger, exact `pack.toml` and `index.toml` snapshots with SHA-256 values, and a completion marker. A protected bundle also includes the exact maintenance close intent, `committed` terminal, close receipt, gate-locked zero-lease status proof, and every detached digest. Scheduled and protected backups have separate retention classes, protected bundles are never pruned automatically, and upstream `restore-backup` and `restore-tar-backup` helpers remain forbidden. Empty-host recovery requires an encrypted copy stored independently from the VPS.

## Durable State Layout

All state roots are canonical, root-owned, and outside `/data`. Directories are mode `0700`; locks and mutable records are mode `0600`; immutable receipts, terminals, digests, and inventories become mode `0400`. Create-new publication, file `fsync`, atomic rename when replacement is required, and parent-directory `fsync` apply to maintenance, operation, rollback, and release records. Links, wrong owner or mode, noncanonical paths, state beneath `/data`, duplicate IDs, incomplete temporary publications, invalid HMACs, and broken predecessor or progress chains fail closed.

- `${STATE_DIR}/ops.lock` serializes top-level operations. `${STATE_DIR}/maintenance/gate.lock` separately serializes every gate and live-kernel observation or mutation. The only legal nested order is operations lock first, gate lock second.
- `${STATE_DIR}/host-bootstrap.json` authenticates the one-time local receipt-key initialization. `${SECRETS_DIR}/receipt-auth.key` and `${SECRETS_DIR}/maintenance-testers.txt` remain mode `0600`, outside state receipts and every backup.
- `${STATE_DIR}/maintenance/boot.json` binds boot ID, boot nonce, gate-service start, and mandatory boot close. `state.json` binds the last completed current-boot mode plus logical and kernel generations. `intents/`, `open-authorizations/`, `terminals/`, `receipts/`, `proofs/`, and `joins/` hold create-new transition records. Every intent has exactly one terminal outcome, `committed` or `abandoned-closed`. `${STATE_DIR}/health/` holds current-container health receipts. `/run/afterlight-gate/reconciler.json` is a root-owned runtime epoch and heartbeat, never durable authority.
- `${STATE_DIR}/operations/pending.json` names at most one install, update, or recovery operation and its intent and progress digests. `${STATE_DIR}/operations/transactions/<operation-id>/` contains intent, detached digest, append-only progress, full prestate and current inventories, and exactly one applicable success, abandonment, or failure record. `${STATE_DIR}/operations/blockers/` contains persistent unsafe-failure blockers; `${STATE_DIR}/operations/resolved/` contains immutable resolution tombstones. An extra transaction directory or temporary publication is itself a blocker until authenticated reconciliation.
- `${STATE_DIR}/rollback/pending.json` names at most one prepare or activation transaction. `${STATE_DIR}/rollback/transactions/<transaction-id>/` contains prepare intent and digest, append-only prepare progress, prepare receipt and digest, full inventories, abandonment, activation intent, activation, activation-finalized, join, and production-open records. `${STATE_DIR}/rollback/consumed/` holds one-time tombstones that prevent prepare receipt reuse.
- `${RELEASE_STATE_DIR}/v0.9.0-rc.1/` is outside every Git worktree and stores public-safe `E-acceptance.json`, `E-acceptance.json.sha256`, `E-client-release.json`, and `E-client-release.json.sha256`. These are not VPS HMAC records and cannot be committed into `E`.

## Maintenance Access Gate

The gate has exactly three authenticated modes:

1. `closed` has no permissive lease elements. Permanent rules drop new and established traffic to Minecraft TCP `25565` and voice UDP `24454` from external, host, loopback, and peer-container paths, leave unpublished internal RCON control available, terminate existing game sessions, and require zero connected players when Minecraft is running.
2. `tester-only` has one nonce-bound lease generation implemented only by set elements with at most 15-second kernel timeouts and permits only canonical IPv4 or IPv6 CIDRs from mode `0600` `${SECRETS_DIR}/maintenance-testers.txt`. Receipts record only the allowlist SHA-256 and entry count.
3. `production-open` has one nonce-bound lease generation whose elements have the same timeout and removes only AFTERLIGHT's maintenance restriction. It never broadens the baseline host firewall or bypasses the Minecraft whitelist.

`server/scripts/maintenance.sh` is the sole public transition authority. Every public transition first takes `${STATE_DIR}/ops.lock`, then the short root-owned `${STATE_DIR}/maintenance/gate.lock` when local gate work begins. All remote accepted-mode and Pages checks finish before the gate lock, then every local receipt, predecessor, generation, boot, service, blocker, authorization, and live-rule fact is revalidated while it is held. `close --reason TOKEN` owns new logical and kernel generations, atomically removes every permissive element, terminates sessions, proves zero players, re-reads the live table, and proves zero lease elements for the owned generation before publishing closed. `status --require MODE --receipt-out RECEIPT` holds the gate lock while authenticating durable state, kernel lease, reconciler heartbeat, live rules, connections, service, players, and unresolved intents. Tester opening requires exact accepted release and current health receipts. Production opening requires those plus a general join receipt for every eligible lineage and exact finalized transaction fields for rollback.

Every transition create-new publishes authenticated intent before its first gate or kernel mutation and exactly one terminal before another transition may begin. Normal completion publishes `committed`. A killed transition without terminal blocks every later open or close and ordinary Compose. `maintenance.sh reconcile --intent INTENT --confirm TRANSITION_ID` is the only recovery path. Under operations then gate lock, it authenticates the exact prior intent and observed predecessor and kernel generation, invalidates any authorization, removes or waits out every lease, closes into new logical and kernel generations, proves zero permissive elements, and publishes `abandoned-closed`. The terminal binds intent digest, prior and resulting generations, boot and reconciler epochs, lease observations, close receipt, status proof, and live-rule digest. Reconciliation never finishes or recreates an interrupted open, and repeating it can only verify the same terminal.

Opening writes and flushes transition intent plus one-time authorization bound to current boot, reconciler process epoch, expected predecessor, expected kernel generation, health, join when required, release, lineage, and blocker-free state. Only then can it atomically install one lease generation composed solely of set elements with 15-second maximum timeouts. While still holding the gate lock it proves nonce, process epoch, membership, remaining timeouts, kernel generation, and live-rule digest, publishes completed state, receipt, and `committed` terminal, then waits for a matching reconciler heartbeat. A kill after lease installation has prior durable authorization but no unbounded permission: without matching completed state, terminal, and same-process heartbeat, every element expires within 15 seconds and cannot renew.

Every `gate_reconciler.py` startup first takes the operations lock then gate lock, reconciles any prior unterminated maintenance intent to `abandoned-closed`, publishes and flushes a startup-close intent, removes all lease elements, creates a new random runtime epoch and kernel generation, publishes a `committed` authenticated close, and proves zero permissive elements. It then releases the operations lock. Each loop checks at least every 5 seconds. Renewal takes only the gate lock and holds it continuously from old-state and authorization validation through atomic lease replacement, kernel-generation proof, and heartbeat publication. It validates maintenance, operation, and rollback blockers plus boot, process epoch, HMAC, nonce, completed state and terminal, logical and kernel generations, active release and lineage, health and join digests, rule digest, lease identity, and systemd dependencies. It never waits for the operations lock while holding the gate lock. Therefore renewal either finishes before close owns its generation and close then removes it, or close finishes first and renewal rejects the old generation. No old authorization can republish after close begins.

In closed mode, only the exact authenticated install, update, recovery, or rollback activation owner whose operations lock remains held may keep Minecraft running without a lease for its bound setup, staging, protected-backup, activation, or health phase. No exception permits an unjournaled restart. Every other failure removes all lease elements, proves closed, and stops Compose within one interval. `afterlight-gate-reconciler.service` uses `Type=notify`, `NotifyAccess=main`, `Restart=always`, and `WatchdogSec=10s`; it accepts `READY=1` only after startup closure and `WATCHDOG=1` only after a complete successful loop, and it is required by `afterlight-compose.service`. Every restart creates a new terminalized closed epoch rather than replaying prior open authority.

Every boot ignores persisted tester-only or production-open authority. `afterlight-maintenance-gate.service` takes operations then gate lock, reconciles any prior unterminated maintenance intent to `abandoned-closed`, publishes and flushes a boot-close intent, removes every lease, writes and flushes a new boot-closed receipt and `committed` terminal, and proves zero permissive elements before dependent units can start. `operation_state.py boot-check` then requires complete host bootstrap and rejects every unresolved, partial, inconsistent, or unsafe maintenance, operation, or rollback state. Only blocker-free state permits ordinary Minecraft startup behind closed ingress. Reopening requires accepted release revalidation, health from that new container start, tester-only access, an exact current-release client receipt and join for that boot and container, and a separate production-open command.

`maintenance.sh attest-join` is general to install, update, reboot, protected-maintenance return, and rollback. It requires tester-only state, fresh same-container health created after tester-only opening for those exact logical and kernel gate generations, exact released-client artifact receipt, active SHA and lineage, explicit operator confirmation, a canonical create-new receipt output beneath `${STATE_DIR}/maintenance/joins/`, and rollback transaction fields when applicable. Health and join receipts expire after 600 seconds for use in a new transition. Production open always requires fresh accepted-release revalidation plus matching unexpired tester-generation health and join receipts bound to both generations at authorization. Once production-open is durably published, renewal verifies those immutable digests and current state but does not close solely because an input receipt later expires. Any opening after close, restart, or reboot requires new health and join receipts. Recovery lineage cannot open directly.

Protected backup always invokes close and then status under the same inherited operations lock before starting the backup image. It requires the close intent, `committed` terminal, owned logical and kernel generations, and gate-locked zero-lease proof. Bundle publication rechecks those generations, terminal, and live-rule digest under the gate lock. A failed or unterminated close, player reconnect, renewal race, rule change, or reconciler mismatch produces no completed protected bundle and leaves the gate closed. Scheduled online backup is the only backup class that may run without changing an already authenticated gate mode.

Interrupted maintenance is an explicit operator action, never an inferred retry:

```bash
server/scripts/maintenance.sh status --require closed

server/scripts/maintenance.sh reconcile \
  --intent "${STATE_DIR}/maintenance/intents/${transition_id}.json" \
  --confirm "${transition_id}"

server/scripts/maintenance.sh status \
  --require closed \
  --receipt-out "${STATE_DIR}/maintenance/proofs/${proof_id}.json"
```

The first status may fail while reporting the blocker. Only the exact reconcile command may terminalize it, and the final status must prove the new closed generations before any later transition or backup.

Tests place deterministic barriers after renewal validates old open state and after close owns its new generation. Both legal lock schedules must end with the close-owned generation and zero permissive elements. SIGKILL before every maintenance terminal requires exact `abandoned-closed` reconciliation; SIGKILL after a durable `committed` terminal requires status verification and makes reconcile reject the already resolved intent. Tests also cover intent, authorization, rule publication, state, receipt, terminal, heartbeat, and each file and parent-directory flush.

## Lock Model

Every top-level mutating command opens and acquires `${STATE_DIR}/ops.lock` once, keeps that one Linux file descriptor open for the full operation, and exports its number as `AFTERLIGHT_OPS_LOCK_FD`. A nested maintenance command receives the inherited open descriptor and uses an internal `--lock-held` contract. It validates that the descriptor is numeric, open, and points through Linux `/proc/self/fd` to the canonical operations lock, then requires nonblocking `flock -n` on that same descriptor to succeed. The inherited locked open-file description succeeds without reacquisition; a separately opened descriptor fails while the parent lock is held. Any command that also needs `${STATE_DIR}/maintenance/gate.lock` takes it only after the operations lock and releases it before releasing operations. No path may invert this order.

Direct `backup.sh` calls acquire the operations lock normally. Backup calls nested beneath update, rollback, or Chunky reuse the parent's descriptor. Tests cover update-to-backup, rollback-to-backup, and pregen-to-backup execution, assert that the same descriptor remains held, and fail forged or separately opened descriptors. The normal online image branch adds `${BACKUP_DIR}/.mc-backup-lock` as a separate archive-serialization lock with the existing fixed acquisition order. The offline paused branch has no image lock and remains serialized by the inherited host operations descriptor. No nested path may reacquire the operations lock and self-deadlock.

Maintenance transitions, open authorization, join attestation, install, update, recovery, rollback prepare intent and progress, resume, abandonment, activation intent, transaction consumption, finalize-only reconciliation, and production opening all use that same operations lock. Gate validation and publication additionally use the gate lock. Reconciler renewal is the deliberate exception: it takes only the gate lock, performs no remote work, and never waits for operations. An exact authenticated operation or activating rollback transaction may keep Minecraft running behind closed ingress only while its operations lock remains held. Status, health, and transaction proofs are therefore ordered with the state and kernel generation they authenticate rather than being racy observations.

## Install, Update, and Recovery Transactions

Install, update, and recovery share `afterlight.operation.*.v1` records and one publication protocol. Each start performs read-only authentication first. Its first permitted state mutation is create-new intent plus detached digest, both flushed. It next create-new publishes and flushes the one pending pointer. Only then may it create a candidate, protected backup, RCON secret, service state, `/data` object, managed ledger, provenance, journal, quarantine object, active-release record, container, or health receipt. Append-only authenticated progress is flushed before and after each mutation boundary and binds expected and observed device, inode, inventory, digest, service, gate, container, and receipt state.

The intent records operation kind and ID, exact command, tool version, accepted release and bundle evidence, boot plus logical and kernel gate generations, service state, complete data inventory or authenticated empty observation, root identity, ledger, provenance, journal, quarantine, active release and lineage, planned paths, expected mutations, and predecessor digest. Fields that do not apply are authenticated nulls. Temporary publication paths and candidates are intent-bound. An unexplained transaction directory, temporary publication, progress gap, extra pointer, wrong terminal, or mismatched digest blocks ordinary Compose instead of being cleaned heuristically.

Exact resume holds the operations lock and revalidates every input, receipt, progress link, path identity, full inventory, state digest, service, gate, and container before repeating only an idempotent check or provably incomplete step. It cannot select new inputs or a new ID. Authenticated abandonment is available only while the original prestate can be restored exactly with ingress closed and services stopped. Install and recovery abandonment ends before the first Minecraft world start and verifies the original empty prestate. Update abandonment ends before first `/data` publication and verifies the full original inventory and state. Later abandonment rejects. Success binds final inventory, ledger, provenance, completed journal, quarantine disposition, active release, service, closed gate, and fresh closed health before `success.json`, then removes and flushes only the matching pointer. A kill after success publication but before pointer cleanup resumes only that cleanup.

`operation_state.py boot-check` runs before ordinary Compose and scans the complete maintenance, operation, and rollback trees. An unresolved operation or unsafe failure stops Minecraft and keeps ingress closed. The only service-start exception is the exact operation owner holding the operations lock while its authenticated phase permits setup or health behind closed ingress. Update health failure terminalizes `failed.json`, a persistent operation blocker, and the rollback request, then removes the matching pending pointer. Rollback prepare must bind those exact failure records. Only successful rollback activation finalization may write the resolution tombstone and remove the blocker. A kill during failure or blocker publication can only resume those same records.

One-time empty-host trust bootstrap precedes install or recovery and never mutates `/data`:

```bash
python3 server/scripts/operation_state.py init-host \
  --state "${STATE_DIR}" \
  --secrets "${SECRETS_DIR}"
```

If killed after key creation, the only permitted retry is the exact `init-host --resume`; it validates the existing key path, owner, mode, inode, and otherwise empty host state before publishing the authenticated bootstrap. It never replaces a key.

Install start, diagnosis, exact resume, and safe abandonment are separate commands:

```bash
server/scripts/install.sh start \
  --sha "${release_sha}" \
  --release-receipt "${release_receipt}"

python3 server/scripts/operation_state.py status \
  --state "${STATE_DIR}" \
  --operation "${operation_id}"

server/scripts/install.sh resume \
  --operation "${operation_id}" \
  --intent "${STATE_DIR}/operations/transactions/${operation_id}/intent.json" \
  --confirm "${operation_id}"

server/scripts/install.sh abandon \
  --operation "${operation_id}" \
  --intent "${STATE_DIR}/operations/transactions/${operation_id}/intent.json" \
  --confirm "${operation_id}"
```

Update uses the same identity contract. Abandon succeeds only before first managed-data publication. After an authenticated rollback-required failure, neither update resume nor abandon may restore world data:

```bash
server/scripts/update.sh start \
  --sha "${release_sha}" \
  --release-receipt "${release_receipt}"

server/scripts/update.sh resume \
  --operation "${operation_id}" \
  --intent "${STATE_DIR}/operations/transactions/${operation_id}/intent.json" \
  --confirm "${operation_id}"

server/scripts/update.sh abandon \
  --operation "${operation_id}" \
  --intent "${STATE_DIR}/operations/transactions/${operation_id}/intent.json" \
  --confirm "${operation_id}"
```

Recovery requires the completed local bootstrap, an empty data root, and no operational state beyond bootstrap and its new transaction. It authenticates but never imports remote host authority:

```bash
server/scripts/recover.sh start \
  --backup "${bundle}" \
  --sha "${historical_sha}" \
  --release-receipt "${historical_receipt}" \
  --confirm "${bundle_id}"

server/scripts/recover.sh resume \
  --operation "${operation_id}" \
  --intent "${STATE_DIR}/operations/transactions/${operation_id}/intent.json" \
  --confirm "${operation_id}"

server/scripts/recover.sh abandon \
  --operation "${operation_id}" \
  --intent "${STATE_DIR}/operations/transactions/${operation_id}/intent.json" \
  --confirm "${operation_id}"
```

The implementation tests SIGKILL before and after intent, digest, pending, every progress receipt, candidate, backup, stop, secret, setup, rename or managed publication, ledger, provenance, journal, quarantine, active release, container start, health, terminal, blocker, pointer unlink, and every parent-directory flush. Each resulting state has exactly one authenticated next action, with no mixed-data ordinary restart path.

## Update and Rollback Model

An update authenticates staging inputs before intent, then creates its candidate under the durable operation transaction before downtime. It takes a protected backup that closes and proves the gate, and activates only validated pack-managed files. Packwiz updates pack-managed paths in `/data`; the prohibition is against automatic world restore, world deletion, or rollback. A healthy update marks `lineage=update`, starts the new container closed, writes fresh health, publishes success, and clears its exact pending pointer. The operator then opens tester-only, joins with the exact released client, records the general join receipt, and separately opens production.

An update health failure stops Minecraft, leaves the gate closed, exits with code `6`, preserves logs, candidate files, Packwiz provenance, backup, ledger, journal, quarantine state, progress, and receipts, and writes one authenticated failure terminal, persistent operation blocker, and rollback-request receipt in durable order. All three bind the same intent, progress tip, failed data inventory, active release, backup, and state digests. It prints the fixed runbook path and exact failed bundle values. It cannot print a valid prepare command until the operator has created rollback SHA `R` and an accepted `R` receipt, and it never restores world data automatically. A kill during failure publication remains blocked and may only finish those exact records.

Rollback remains a truthful two-phase operation, but the operator-owned Git promotion now precedes data-changing prepare so prepare can bind the exact rollback release:

1. From authenticated bundle snapshots for historical SHA `H`, the operator creates and reviews normal rollback commit `R`, pushes exact `R` through `dev`, promotes it unchanged to `main`, waits for exact-SHA CI and Pages parity, and runs accepted mode externally. Maintenance tooling never commits, reverts, pushes, mutates branches or tags, or calls a GitHub write API.
2. `rollback.sh prepare` performs read-only authentication of named bundle, `H`, `R`, canonical accepted `R` receipt, raw-`R` equality with historical snapshots, current accepted `main`, Pages, current data identity, ledger, provenance, journal, quarantine, services, logical and kernel gate generations, and planned paths. When entered from update failure, it also requires the exact paired rollback request and operation blocker and authenticates their intent, progress, failed inventory, active release, and backup digests. Before any gate, service, backup, marker, rename, extraction, activation, or data mutation, it create-new publishes and flushes schema `afterlight.rollback.prepare-intent.v1` plus digest. The intent binds the transaction ID, every input digest, root device and inode, active release and lineage, current state observations, operation blocker when present, planned paths, tool version, and predecessor digest.
3. Under the inherited operations lock, prepare closes and proves the gate, stops Minecraft and scheduled backup idempotently, and proves both stopped. It then invokes `backup.sh --class protected --reason rollback-current --offline --lock-held`. This must use the pinned image's paused branch with the host-created marker, no RCON, and no `.mc-backup-lock` assertion.
4. Prepare writes authenticated append-only progress before and after every gate close and proof, service stop, offline backup, marker lifecycle, inventory, candidate, quarantine rename, publication, raw-`R` overlay, journal, ledger, provenance, and final inventory step. Root device, inode, path, and digest checkpoints distinguish not-started, completed, and crash-between-rename states.
5. Completed prepare marks `lineage=rollback` and writes schema `afterlight.rollback.prepare.v1`, binding intent and progress-chain tips; bundle and archive metadata; `H`; `R`; release evidence; raw and historical manifests; failed-current offline bundle; pre-restore and prepared inventories; ledger; active release; candidate and installer provenance; completed journal; quarantine; stopped services; closed gate; and predecessor digests. It then writes `pending.json` with phase `prepared` and flushes every parent directory. A receipt without its exact pointer is not completed prepared state and remains blocked for exact resume.
6. Exact transaction files are `prepare-intent.json`, its digest, `prepare-progress/<sequence>.json`, `prepare.json`, its digest, all inventories, `prepare-abandoned.json`, `activation-intent.json`, `activation.json`, `activation-finalized.json`, `join.json`, and `production-open.json`. The consumed tombstone remains under `${STATE_DIR}/rollback/consumed/`. State modes and create-new durability remain unchanged.
7. `prepare --resume` accepts only the original intent and transaction. It revalidates immutable inputs and progress, reconciles exact path identities including receipt-without-pointer, and repeats only idempotent or incomplete safe steps. `rollback.sh abandon` is idempotent for the exact pre-activation transaction, restores and verifies pre-prepare data, ledger, provenance, journal, quarantine, and root identity from authenticated progress, writes abandonment, removes only a matching pending pointer, and clears only the rollback prepare blocker after directory-flushed proof. It never clears a failed-update operation blocker. Failure leaves ingress closed, services stopped, and Compose blocked. A valid abandonment receipt is terminal and makes prepare resume, activate, finalize-only, and receipt reuse fail.
8. Any prepare intent blocks ordinary Compose and systemd startup until exact abandonment is fully reconciled or activation is finalized with no pending pointer. Activate authenticates prepared pending state and every bound input under the operations lock. It writes activation intent, changes pending phase to `activating`, and becomes the sole exception allowed to start Minecraft behind closed ingress while its lock remains held. It writes closed-mode health for `R`. While still closed, publication order is activation receipt, consumed tombstone, activation-finalized receipt, pending unlink, then parent-directory flush. If prepare bound an update blocker, the next order is operation resolution tombstone, blocker unlink, and parent-directory flush. Only after no unresolved rollback or operation state remains may the command create a timeout-bound tester lease using closed health and then write tester-generation health.
9. Ordinary activate and resume reject consumed state. Before consumption, resume authenticates and continues only missing idempotent steps, reusing an existing health output only when it exactly matches the transaction and current container. `--finalize-only` is the sole reconciliation path for an exact matching pending pointer or bound operation blocker plus activation receipt with authenticated closed health and consumed tombstone. It revalidates exact `R` data and transaction state, then may write a missing finalized receipt, remove that exact pending pointer, write a missing operation resolution tombstone, and remove only the exact bound blocker in prescribed order. It cannot start, restart, change gate mode, consume again, or alter transaction inputs, and the live service may be running closed or stopped. Finalized plus no pending or blocker is already complete and does not use finalize-only. If tester health is absent after any consumed state, the operator closes and proves the gate, starts the normal Compose unit behind closed ingress, creates new closed health, and performs explicit tester-only access plus tester health. A mismatched set fails closed.
10. SIGKILL before or after every prepare, abandonment, activation, operation-blocker resolution, tester-authorization, and tester-health publication boundary has one defined outcome: exact resume before consumption, idempotent abandonment, finalize-only for consumed plus any exact residual, or explicit post-finalization closed restart and tester recovery. Unresolved state forces the gate closed, blocks unattended Compose on boot, and stops a closed activation service within 5 seconds after its lock owner dies.
11. Shane joins with the released client while tester-only. `rollback.sh attest-join` delegates to the general join interface and adds finalized activation plus consumed digests. Production open is a later command that freshly reruns accepted `R` validation and requires matching current-boot health, released-client join, transaction, activation, lineage, and tester logical and kernel generations. No rollback phase opens production implicitly.

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
  --request "${STATE_DIR}/rollback/requests/${request_id}/request.json" \
  --operation-blocker "${STATE_DIR}/operations/blockers/${operation_id}.json" \
  --confirm "${bundle_id}"
```

The request and operation-blocker arguments are a mandatory pair when prepare follows an update failure. A deliberate rollback not originating from update failure omits both, and prepare rejects one without the other.

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

After consumption, never run path A or activation resume. If exact matching consumed and activation state retains either the rollback pending pointer or a bound operation blocker, first run finalize-only. If finalized state has neither residual, skip this command:

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

`server/README.md` must show how each variable is obtained from a preceding receipt, mark activation path A and path B as mutually exclusive, print the exact expected mode after every command, and document host bootstrap, operation intent, status, exact resume, safe abandonment limits, failure blockers, maintenance reconciliation, lease expiry, reboot closure, rollback finalize-only, Compose blockers, and forensic paths. Empty-host recovery uses a completed local trust bootstrap, creates its fresh RCON secret only after operation intent, creates closed gate state, marks active release `lineage=recovery`, and cannot open production. To reopen, the operator creates accepted `R` and completes the normal local rollback prepare, activate, tester-only join, and production-open sequence, replacing recovery lineage with the bound rollback transaction. Restoring or starting a server alone is not evidence that the mutable client channel is safe.

## Distribution and Release Boundary

Prism plus Packwiz remains the only complete supported client lane. A release Prism build requires an already accepted SHA and current Pages parity, so CI and pre-acceptance checks use fixture or immutable-local builder tests instead of requiring the final archive. The release ZIP is deterministic and contains no acceptance receipt, subject SHA, client receipt, local path, build timestamp, or credential. Release identity lives in the external canonical `afterlight.client.release.v1` receipt rather than mutable archive bytes.

AutoModpack is disabled because the licensing inventory currently contains 13 denied, 13 manual-review, and 7 unknown client entries. The release candidate does not add, host, test, or advertise AutoModpack. The mrpack and CurseForge ZIP remain optional friends-only lanes because they can contain embedded third-party JARs.

Two accepted full gauntlets at `S` preserve separate Prism archives, `S` client receipts, detached digests, and builder receipts outside both worktrees. Equal lengths and SHA-256 values are necessary but not sufficient; a byte-for-byte comparison must also pass. Any difference invalidates `S`. These gauntlets plus an explicit passed, failed, or deferred record for every manual item permit the correctly labeled `v0.9.0-rc.1` prerelease. Shane's manual matrix gates only `1.0.0` and any claim that production is open. Automated evidence must never convert a deferred manual check into a pass.

## Evidence and Tag Model

After both accepted full gauntlets at `S`, create evidence SHA `E` as the direct child of `S`. The only permitted changed paths are:

- `docs/releases/v0.9.0-rc.1.md`
- `docs/releases/v0.9.0-rc.1-gauntlet.md`

The committed reports record `S`, its accepted workflow and Pages receipt, both full gauntlet and `S` client receipts, byte-identical release Prism proof, exact commands, and explicit manual deferrals. They state that `E` acceptance and client rebinding occur later and do not claim an `E` workflow receipt, `E` Pages deployment receipt, final `E` parity evidence, or `E` client receipt.

Before promotion, verify that `E` has parent exactly `S` and that `git diff S..E` contains no executable, manifest, config, quest, pack, workflow, generated Packwiz state, or path outside the two evidence documents. Promote exact `E` through `dev` and `main` without creating another commit. Require exact completed successful `E` workflows on both branches, followed by exact `E` Pages deployment and parity on `main`.

Only after those remote events complete does an external operator process run `release_gate.py accept` for exact `E`. The caller is outside `pack-ci.yml`, and accepted mode still rejects a selected run equal to `GITHUB_RUN_ID`. It writes create-new `${RELEASE_STATE_DIR}/v0.9.0-rc.1/E-acceptance.json` and `.sha256` files outside every worktree. The operator reparses the receipt, confirms its subject is `E`, and recomputes its detached digest before client receipt creation.

`tools/client_release_receipt.py rebind-evidence` next authenticates both preserved archives and `S` client receipts through read-only file descriptors. It verifies both detached digests, equal archive lengths, digests, and bytes, canonical `S` and `E` acceptance, `E` as the direct child of `S`, exact evidence-document blob hashes, the two-document diff allowlist, the `S` receipt and archive facts committed in those documents, equal raw and Pages `pack.toml` and `index.toml` hashes at both subjects, and equal installer and builder facts. It never rebuilds, copies, normalizes, renames, chmods, or writes either archive, and rejects inode, mode, size, mtime, or content change during authentication. Create-new `E-client-release.json` and its detached digest use schema `afterlight.client.release.v1`, subject `E`, source subject `S`, and the already gauntleted archive identity. An `S`-subject client receipt is no longer sufficient for a release join after `E` becomes current `main`.

`tools/finalize_rc.py publish` is the sole final publication interface and is implemented before subject freeze. It requires both `E` receipts and digests, and rejects workflow execution, receipts inside a worktree, noncanonical or mismatched bytes, wrong acceptance or client subject, wrong client source, evidence-document blob mismatch, predecessor receipt or archive facts that differ from committed `E` gauntlet evidence, wrong parent, disallowed `S..E` paths, moved `main`, conflicting tags or releases, and remote evidence mismatch. Only after validation does it create and push the annotated tag, then create the GitHub prerelease. A retry after tag-push interruption may verify and reuse only the identical tag object and message to create a missing release; it can never move, delete, or recreate the tag.

```bash
e_receipt="${RELEASE_STATE_DIR}/v0.9.0-rc.1/E-acceptance.json"
e_client_receipt="${RELEASE_STATE_DIR}/v0.9.0-rc.1/E-client-release.json"
python3 server/scripts/release_gate.py accept \
  --repo "${GITHUB_REPOSITORY}" \
  --sha "${E}" \
  --pages-url "${PAGES_URL}" \
  --receipt-out "${e_receipt}" \
  --digest-out "${e_receipt}.sha256"

python3 tools/client_release_receipt.py rebind-evidence \
  --subject "${S}" \
  --evidence "${E}" \
  --subject-acceptance "${S_ACCEPTANCE_RECEIPT}" \
  --evidence-acceptance "${e_receipt}" \
  --gauntlet-a-receipt "${S_CLIENT_RECEIPT_A}" \
  --gauntlet-b-receipt "${S_CLIENT_RECEIPT_B}" \
  --gauntlet-a-archive "${S_PRISM_ARCHIVE_A}" \
  --gauntlet-b-archive "${S_PRISM_ARCHIVE_B}" \
  --receipt-out "${e_client_receipt}" \
  --digest-out "${e_client_receipt}.sha256"

python3 tools/finalize_rc.py publish \
  --subject "${S}" \
  --evidence "${E}" \
  --tag v0.9.0-rc.1 \
  --receipt "${e_receipt}" \
  --digest "${e_receipt}.sha256" \
  --client-receipt "${e_client_receipt}" \
  --client-digest "${e_client_receipt}.sha256" \
  --repo "${GITHUB_REPOSITORY}"
```

The immutable annotated tag `v0.9.0-rc.1` points to `E`. Its tag message contains `S`, `E`, the exact final `E` workflow run, attempt, and job identifiers, Pages deployment identifier, parity hashes, the complete canonical `E` acceptance and client receipts, both detached digests, and the authenticated Prism archive identity. The GitHub prerelease repeats those exact bytes and digests in release metadata or public-safe receipt assets. Remote readback must match before announcement. This places evidence that necessarily occurs after `E` in tag and release metadata without modifying `E`, creating a child evidence commit, rebuilding the client, or moving or recreating the tag.

## Executable Release Sequence

1. Implement Tasks 1 through 5 and the Task 6 CI and gauntlet contracts.
2. Run all pre-acceptance checks without requiring accepted `main`, current Pages, or a release Prism archive.
3. Run whole-project skeptical review, fix every Critical and Important finding, rerun focused checks, and rerun the full pre-acceptance suite.
4. Freeze the final implementation commit as `S`, push exact `S` to `dev`, and require exact `S` dev CI success.
5. Promote exact `S` to `main`, wait for exact completed successful `S` main CI and Pages deployment, and run accepted mode externally.
6. Run two clean full release gauntlets at `S`, each including accepted release gating and the final Prism build. Preserve both archives and receipts externally, then prove equal length, SHA-256, and bytes before creating `E`.
7. Record all evidence and manual deferrals in direct child `E`, with no change outside the two named evidence documents.
8. Promote exact `E` through `dev` and `main`, then require exact completed `E` CI and Pages parity.
9. Run accepted mode externally for `E`, durably preserve and verify its canonical receipt plus digest, then create and verify the exact `E` client receipt from both unchanged `S` gauntlet artifacts. Only then create the annotated tag and GitHub prerelease with both exact post-`E` receipts and digests in tag and release metadata.
10. Treat release publication and server access as separate gates. The tag never reopens a host. Install, update, reboot, protected-maintenance return, and rollback all start closed and require their own current release, post-start closed health, tester-only authorization, tester-generation health, released-client join, and explicit production-open sequence. Recovery lineage remains closed until a normal accepted local rollback replaces it, then the rollback opening contract applies.
11. Treat any later implementation change as a new subject and restart from skeptical review. Never patch between the final accepted gauntlets and the tag.

## Deferred Live Evidence

These checks cannot be truthfully completed by plan text or a Mac-only authoring session:

- Baseline VPS firewall exposes only Minecraft TCP and voice UDP when maintenance is production-open.
- Permanent default-drop gate rules precede Docker for IPv4 and IPv6; every permission has a prior durable same-process authorization, expires within 15 seconds without renewal, and closes after reconciler death, watchdog stall, rule drift, missing state, or divergent state. Deterministic close-versus-renewal barriers prove both lock schedules end in the close-owned generation with zero permissive elements and no old authorization republished.
- Host filesystem provides reliable `flock`, inherited descriptor behavior, and same-filesystem atomic rename.
- Graceful stop finishes inside two minutes without exit 137.
- Ten-gigabyte heap remains below the 13 GB container limit under gameplay and Chunky load.
- Backup throughput, restore throughput, free-space checks, and quarantine capacity fit the real world size.
- Every host reboot ignores persisted open state, proves closed before Compose, restores the stack without creating a new world, and requires fresh current-release, post-start health, tester-only, join, and production-open evidence.
- Two released clients join, general join attestation works after install, update, reboot, and protected-maintenance return, whitelist works, and voice chat works over UDP.
- Installed Chunky RCON output is classified conservatively for active, paused, complete, and unknown states.
- The full pack boots and plays on arm64.
- An encrypted offsite bundle restores onto a genuinely empty replacement host after one-time local trust bootstrap, and every interrupted bootstrap or recovery phase remains boot-blocked until exact resume or safe abandonment.
- A real protected backup proves the closed gate before archive creation and cannot publish after gate drift or player reconnect.
- A real update failure remains closed and rollback prepare proves both services stopped before the pinned offline protected-backup branch, with no RCON or image-lock claim.
- SIGKILL at every install, update, and recovery boundary yields exact resume, authenticated safe abandonment, durable success cleanup, or update rollback-required failure, with no mixed-data ordinary restart. SIGKILL at every maintenance boundary yields committed completion or exact `abandoned-closed` reconciliation before another transition.
- SIGKILL at every rollback prepare and abandonment boundary yields exact resume or terminal authenticated abandonment. SIGKILL across activation, operation-blocker resolution, and tester publication yields pre-consumption resume, consumed-plus-pending finalize-only, or post-finalization closed restart and tester recovery without receipt reuse.
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
