# Plan 07 Architecture Audit

Date: 2026-08-09

Status: design gate corrected after round 4 cross-boot continuity, atomic-bootstrap, reconciliation-transaction, channel-freshness, promotion-closure, and offline-marker review. No Docker, VPS, backup, recovery, CI, Pages, Prism, or release behavior is claimed by this document.

## Scope

The launch architecture was reviewed before implementation against the exact current itzg image manifests, Packwiz installer release bytes, NeoForge installer checksum, Docker Compose behavior, GitHub Actions APIs, GitHub Pages mutability, RCON secret handling, Chunky operations, Python archive extraction safety, nested Linux lock behavior, host ingress maintenance safety, renewal-versus-close concurrency, untrappable kill windows, stale reboot state, cross-boot and cross-container transaction continuity, atomic first publication, maintenance reconciliation continuity, normal update promotion closure, offline marker identity, general mutation transaction continuity, rollback backup branch safety, universal join evidence, exact client lineage, and release-evidence ordering.

The initial review found nine Critical and nine Important design gaps. A completed follow-up contradiction review found seven cross-task defects in the rewritten plan: acceptance self-deadlock, unhandled Packwiz installer state, an incorrect release-candidate manual gate, nested lock reacquisition, backup exclusions that were not part of resolved Compose, client-unsafe rollback, and evidence self-reference. A subsequent pinned-source check found that online and offline backup enter different RCON and image-lock branches. Round 1 then corrected three independent failures: maintenance was prose rather than persisted access control, rollback prepare and activate lacked one-time binding, and tag creation lacked an external accepted-mode receipt for evidence SHA `E`.

Round 2 found four Critical and two Important residual gaps. Permissive rules could outlive an untrappable kill before open-state publication; boot could replay stale production-open; rollback prepare selected online backup after update failure had stopped Minecraft; prepare had no pre-mutation intent; activation had an unhandled consumed-plus-pending crash window; and install or update could open without general released-client join evidence. That correction added timeout-bound permissions and an active reconciler, boot-closed epochs, stopped-service offline rollback backup, prepare intent plus resume or abandonment, finalize-only activation reconciliation, and one general join interface required by every production-open lineage.

Round 3 found three Critical and one Important residual gaps. Renewal could validate an old authorization and republish its lease after close removed it; install, update, and recovery lacked rollback-grade crash transactions; the final tag target `E` lacked an exact client release receipt; and a killed maintenance intent had no authenticated terminal reconciliation. The corrected plan serializes every gate observation and transition, gives every data or active-release mutation pre-mutation intent plus boot blocking and exact recovery, creates an `E` client receipt by read-only authentication of both byte-identical `S` Prism artifacts, and requires every killed maintenance transition to end in a proved-closed terminal before another transition. Implementation still requires test-first development, whole-project skeptical review, two accepted clean gauntlet runs, exact-SHA CI and Pages evidence, and the deferred live-host matrix.

Round 4 found one Critical and four Important residual gaps. A boot-bound health receipt could strand an otherwise resumable operation after reboot; separate intent, digest, and pending publications left unrecoverable bootstrap gaps; maintenance reconciliation was neither crash-resumable nor consistently automatic or manual; open-rule renewal stopped checking current `main` and Pages after authorization; and a killed public offline backup could leave `.paused` selecting the RCON-free branch after services restarted. The corrected plan gives only the exact active transaction chained boot-continuation and health-supersession authority, makes one self-contained pending envelope the atomic first durable operation publication, makes startup and manual maintenance recovery two entry points to one durable reconciliation transaction, requires every rule renewal to refresh a 15-second authenticated current-channel lease, adds a maintenance-closure guard before normal update promotion, and makes offline backup an internal rollback child whose marker lifecycle is authenticated in parent progress. Implementation still requires test-first development, whole-project skeptical review, two accepted clean gauntlet runs, exact-SHA CI and Pages evidence, and the deferred live-host matrix.

## Threat Model and Corrections

The maintenance findings protect against Docker accepting traffic while prose says closed, an untrappable kill between permissive rule application and state publication, a dead reconciler, rule drift, a restored `/data` tree reverting access state, reboot replaying yesterday's open decision, a paused renewal restoring old permissions after close begins, and an open host remaining authorized after `main` or Pages moves. Permanent rules default to closed. Tester and production permissions are lease generations made only of kernel set elements with at most a 15-second timeout. A durable current-boot, current-reconciler authorization and a current channel-freshness record whose `CLOCK_BOOTTIME` expiry is exactly 15,000,000,000 nanoseconds after issue must precede any permissive lease. Every renewal takes a gate-locked snapshot, releases the lock for a bounded current-`main` and Pages probe, then retakes the lock and completely revalidates before publishing a new freshness generation or replacing rules. The kernel timeout is rounded down to the remaining freshness lifetime. Close owns new logical and kernel generations, removes all leases, then re-proves zero permissive elements before releasing that lock. Probe failure or drift closes immediately and stops Compose. Every reconciler process and boot begins closed. Reopening requires fresh current-release validation, post-start closed health, tester-only authorization, tester-generation health, released-client join, and production-open actions.

The general-operation findings protect against SIGKILL leaving a candidate, secret, protected backup, service, data tree, ledger, provenance, journal, quarantine, active-release record, or health receipt in a combination that ordinary boot mistakes for complete, including a kill between separate intent, digest, and pointer writes. Install, update, and recovery now authenticate read-only inputs first, atomically publish one self-contained authenticated pending bootstrap as their first durable authority, journal before and after every mutation boundary, block ordinary Compose while unresolved, and finish through exact resume, authenticated safe abandonment, or durable success. A resume on another boot publishes a same-transaction boot continuation before service start. If prior health names another boot or container, new health plus a chained supersession record must become durable before success, and every old receipt remains immutable. An update that has crossed its irreversible publication boundary may instead terminalize rollback-required failure with a persistent blocker bound into rollback prepare and cleared only by successful activation finalization.

The rollback findings protect against time-of-check to time-of-use substitution, wrong backup branch selection, mutation before durable authority, ambiguous crash points, receipt replay, orphan offline markers, and the consumed tombstone conflicting with a still-present pending pointer. Prepare atomically publishes one complete phase-`preparing` pending envelope before any mutation, stops and proves both services stopped, and invokes the offline backup interface only as its authenticated child. The parent progress chain records marker intent, exact HMAC marker bytes and identity, both directory flushes, backup observations, and marker removal before prepare can terminalize. An incomplete prepare blocks Compose and both backup modes until exact resume or authenticated abandonment restores and verifies current state. Activation atomically moves the same pointer to `activating` with the complete activation intent before start. Before consumption it may use the same boot-continuation and health-supersession protocol; after consumption only finalize-only can clear an exact matching residual and cannot start, continue, supersede, or consume again.

The join finding protects normal install, update, reboot, or maintenance return from reaching production based only on server health. A general join attestation now requires tester-only access, a fresh current-container health receipt, the exact released-client artifact receipt, active release and lineage, current boot plus logical and kernel gate generations, and explicit operator confirmation. Every production open requires fresh accepted-release revalidation, health, and join receipts. Rollback adds exact finalized transaction evidence; recovery lineage cannot open directly.

The evidence findings protect against tagging `E` after checking only CI and Pages, copying stale acceptance or client evidence from `S`, silently rebuilding the gauntleted client, writing a post-commit fact into `E`, or making the workflow whose success is required wait for itself. The correction runs accepted mode externally only after exact `E` CI and Pages parity complete, then creates an exact `afterlight.client.release.v1` receipt for `E` by read-only authentication of both preserved byte-identical `S` gauntlet archives and their receipts. Both canonical receipts and detached digests live outside every worktree and must appear in annotated-tag and GitHub-release metadata before publication.

The maintenance-terminal findings protect against an intent surviving a kill with no truthful committed or abandoned outcome and against reconciliation itself being killed. Every transition publishes exactly one authenticated `committed` or `abandoned-closed` terminal. Reconciliation first atomically publishes a self-contained pending bootstrap, then records create-new progress generations across authorization invalidation, lease removal, generation ownership, close state, receipt, proof, original terminal, and reconciliation terminal. Its final cleanup intent and `terminalizing-cleanup` pending generation precede pending unlink and parent `fsync`, which are the last writes. `maintenance.sh reconcile` and the internal startup entry point run this same engine and can only close. Startup may force kernel rules closed before the bootstrap as an emergency safety action, but it records one deterministic detection and cannot start Compose until the durable protocol finishes. A repeated invocation reuses detection-only state or resumes or verifies the exact reconciliation ID and bytes. Until both terminals exist and the pending pointer is absent, every later transition and ordinary Compose start is blocked.

The promotion-closure finding protects a currently open production host from learning that its mutable channel moved only after the push. Before a normal post-launch update, an atomic promotion guard is published, maintenance closes and proves zero leases and players, and the guard blocks every reopening. The operator still performs the Git push manually. The host must observe the exact candidate as remote `main` while that guard remains current and prove no intervening tester or production transition, then the update operation bootstrap binds and consumes the guard. Cancellation is authenticated and legal only before observation while remote `main` remains the predecessor. A bypassed or different channel move is independently caught by freshness renewal and cannot produce a supported update start.

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
- Empty-host install or recovery first completes the one-time `operation_state.py init-host` trust bootstrap. Recovery creates its fresh RCON secret only after atomic operation pending-bootstrap publication, starts a new closed maintenance chain, and never imports operation or rollback authority from another host.
- Maintenance, operation, and rollback authority lives under `${STATE_DIR}`, never under `/data`, quarantine, or a backup bundle. `${SECRETS_DIR}/receipt-auth.key` authenticates local state and remains outside every archive.

Task 1 creates reviewed source file `server/backup-excludes.txt`, mounts it read-only at `/etc/afterlight-backup-excludes.txt`, sets `EXCLUDES=""` to neutralize the image default, and sets `EXCLUDES_FILE` to that exact path in the backup service. The file excludes `.rcon-cli.env`, `.rcon-cli.yaml`, `server.properties`, the host-created `.paused` marker, every JAR, cache directories, logs, and known transient files before the backup image creates an archive. There is no second inline exclusion authority.

Task 2 tests inspect canonical `docker compose config --format json` to prove the exact resolved mount and environment. Successful backup tests inspect archive membership to prove every reviewed class, including `.paused`, is absent at any depth. The archive guard remains a second boundary and rejects any forbidden member injected despite the exclusion file.

Pinned `docker-mc-backup` source has two materially different execution paths. Without `/data/.paused`, the normal branch loads RCON, performs a readiness `save-on`, acquires `${BACKUP_DIR}/.mc-backup-lock`, runs `save-off`, optional `save-all flush` and sync, creates the archive, and restores `save-on` with its own exit trap. The host wrapper validates online prerequisites but does not duplicate that RCON mutation sequence.

The pinned image enters its offline path only when `/data/.paused` exists. That paused branch bypasses both RCON and `.mc-backup-lock`, so marker presence can never be a public mode selector. Public scheduled and protected backup commands are online only and reject offline or marker arguments. The sole offline entry point requires an active authenticated rollback prepare envelope, the inherited parent operations-lock descriptor, stopped Minecraft and scheduled sidecar proofs, and the exact next marker-intent progress receipt. The marker is a mode `0600` regular canonical HMAC record binding transaction, pending bootstrap, nonce, data-root identity, boot continuation, and planned output. Its file and `/data` directory are flushed before post-create progress. Its authenticated unlink and second directory flush precede post-remove progress and every prepare terminal. Traps are best effort only. After SIGKILL or reboot, boot-check blocks Minecraft and both backup modes; only exact parent resume or abandonment may continue or remove a matching marker. A marker without one matching active parent is a forensic blocker, never permission to enter the RCON-free branch.

Each accepted bundle includes a checksum, authenticated release receipt, exact managed ledger, exact `pack.toml` and `index.toml` snapshots with SHA-256 values, and a completion marker. A protected bundle also includes the exact maintenance close intent, `committed` terminal, close receipt, gate-locked zero-lease status proof, and every detached digest. Scheduled and protected backups have separate retention classes, protected bundles are never pruned automatically, and upstream `restore-backup` and `restore-tar-backup` helpers remain forbidden. Empty-host recovery requires an encrypted copy stored independently from the VPS.

## Durable State Layout

All state roots are canonical, root-owned, and outside `/data`. Directories are mode `0700`; locks and mutable records are mode `0600`; immutable receipts, terminals, digests, and inventories become mode `0400`. Create-new publication, file `fsync`, atomic rename when replacement is required, and parent-directory `fsync` apply to maintenance, operation, rollback, and release records. Links, wrong owner or mode, noncanonical paths, state beneath `/data`, duplicate IDs, incomplete temporary publications, invalid HMACs, and broken predecessor or progress chains fail closed.

- `${STATE_DIR}/ops.lock` serializes top-level operations. `${STATE_DIR}/maintenance/gate.lock` separately serializes every gate and live-kernel observation or mutation. The only legal nested order is operations lock first, gate lock second. Reconciler renewal and emergency closure take only the gate lock and never wait for operations while holding it.
- `${STATE_DIR}/host-bootstrap.json` authenticates the one-time local receipt-key initialization. `${SECRETS_DIR}/receipt-auth.key` and `${SECRETS_DIR}/maintenance-testers.txt` remain mode `0600`, outside state receipts and every backup.
- `${STATE_DIR}/maintenance/boot.json` binds boot ID, boot nonce, gate-service start, and mandatory boot close. `state.json` binds the last completed current-boot mode plus logical and kernel generations. `intents/`, `open-authorizations/`, `terminals/`, `receipts/`, `proofs/`, and `joins/` hold create-new transition records. Every transition intent has exactly one terminal outcome, `committed` or `abandoned-closed`. `${STATE_DIR}/health/` holds immutable current-container health receipts. Transaction health IDs are deterministic `<kind>-<transaction-id>-<health-sequence>` values, starting at zero and increasing for each replacement container. Health binds current boot, container start, release and lineage, state digests, gate generations, freshness digest or authenticated null, transaction, continuation, superseded-health digest, and predecessor supersession tip or authenticated nulls. The later supersession record cites new health and becomes the active pending or consumed tip. `/run/afterlight-gate/reconciler.json` is a root-owned runtime epoch and heartbeat, never durable authority.
- `${STATE_DIR}/maintenance/detections/<detection-id>.json` stores create-new `afterlight.maintenance.reconcile.detection.v1` records after startup emergency closure. The ID is the SHA-256 of canonical interrupted transition ID and intent digest, so detection-only recovery reuses one exact record and different bytes at that path block. It binds entry point, current and prior boot, interrupted transition and intent, authorization and terminal observations, live-rule and lease digests, emergency-close result, and issue times. `${STATE_DIR}/maintenance/reconcile-pending.json` is one complete `afterlight.maintenance.reconcile.pending.v1` bootstrap and active pointer. It binds reconciliation ID, detection digest or authenticated null, interrupted transition and intent digest, authorization digest or authenticated null, prior boot and generations, observed live rules and leases, entry point, pending generation, phase exactly `reconciling` or `terminalizing-cleanup`, progress generation and tip, transaction path, and HMAC. `${STATE_DIR}/maintenance/reconciliations/<reconciliation-id>/` retains exact `bootstrap.json`, byte-identical later pending generations at `pending-generations/<generation>.json`, append-only `afterlight.maintenance.reconcile.progress.v1` records at `progress/<generation>.json`, close evidence, and one `afterlight.maintenance.reconcile.terminal.v1` with outcome `committed-closed`. Progress binds sequence, predecessor, step, before and after observations, owned generations, and expected next step. The original transition terminal becomes durable before the reconciliation terminal. A final cleanup-intent progress record binds both terminals and expected pending bytes, pending advances to `terminalizing-cleanup`, then pending unlink and parent-directory `fsync` are the last writes. If pending survives, replay repeats only cleanup. If it is absent, the matching terminal and cleanup intent prove completion. Detection remains immutable and is resolved only by that terminal.
- `${STATE_DIR}/maintenance/channel-freshness/leases/<generation>.json` contains immutable `afterlight.maintenance.channel-freshness.v1` records. Each binds repository, active SHA and lineage, accepted-receipt digest, current remote `main`, immutable raw hashes, current Pages deployment and hashes, boot, reconciler epoch, authorization nonce, predecessor freshness digest, `issued_boottime_ns`, `expires_boottime_ns` exactly 15,000,000,000 greater, and informational UTC issue time. Issuance occurs under the gate lock after remote success and complete local revalidation. `current.json` is an atomically replaced authenticated pointer. Open transition, health, join, status, rule, and heartbeat evidence binds the applicable freshness digest. Another boot, unavailable `CLOCK_BOOTTIME`, nonpositive remaining lifetime, or an expiry mismatch fails closed.
- `${STATE_DIR}/operations/pending.json` is one complete `afterlight.operation.pending.v1` bootstrap and pointer for at most one install, update, or recovery operation. It includes the full immutable intent payload, operation identity and kind, pending generation, phase `bootstrapped`, `mutating`, `health`, `terminalizing-success`, `terminalizing-failure`, or `terminalizing-abandonment`, transaction path, predecessor pending and terminal digests, progress tip, boot-continuation tip, health-supersession tip, promotion-closure and promotion-observation digests or authenticated nulls, publication nonce, and HMAC. `${STATE_DIR}/operations/transactions/<operation-id>/` retains the exact first envelope as `bootstrap.json`, byte-identical later pointer archives in `pending-generations/`, append-only progress, `boot-continuations/`, `health-supersessions/`, full prestate and current inventories, and exactly one applicable success, abandonment, or failure record. `${STATE_DIR}/operations/blockers/` contains persistent unsafe-failure blockers; `${STATE_DIR}/operations/resolved/` contains immutable resolution tombstones.
- `${STATE_DIR}/operations/promotions/pending.json` is one atomic `afterlight.update.promotion.pending.v1` guard with pending generation; phase `closing`, `closed-authorized`, `observed`, or `transferring`; promotion ID; candidate and predecessor SHAs; active-release and current-acceptance digests; boot and gate generations; transaction path; predecessor pending digest; close and observation digests when applicable; and HMAC. `${STATE_DIR}/operations/promotions/transactions/<promotion-id>/` retains `bootstrap.json`, byte-identical later pointer archives in `pending-generations/`, maintenance close and proof, `closure.json`, optional `observed.json`, and exactly one `consumed.json` or `abandoned.json`. While pending it blocks tester-only, production-open, another promotion, and unrelated operations. The exact update bootstrap must bind it before its consumed tombstone and pointer cleanup.
- `${STATE_DIR}/rollback/pending.json` is one complete `afterlight.rollback.pending.v1` bootstrap and pointer with pending generation and phase exactly `preparing`, `prepared`, or `activating`. It embeds full prepare intent, progress tip, prepare receipt digest or authenticated null, activation intent or authenticated null, boot-continuation tip or authenticated null, health-supersession tip or authenticated null, predecessor pending digest, and HMAC. `${STATE_DIR}/rollback/transactions/<transaction-id>/` retains exact `bootstrap.json`, byte-identical later pointer archives in `pending-generations/`, append-only prepare progress, `boot-continuations/`, `health-supersessions/`, prepare receipt and digest, full inventories, abandonment, archived activation intent, activation, activation-finalized, join, and production-open records. `${STATE_DIR}/rollback/consumed/` holds one-time tombstones that prevent prepare receipt reuse. Prepare progress authenticates offline marker intent, marker bytes and identity, both data-directory flushes, and marker removal.
- The first authoritative operation, rollback, promotion, or reconciliation publication is pending generation zero and uses a same-directory unnamed `O_TMPFILE`: write canonical bytes, file `fsync`, create-new `linkat(AT_EMPTY_PATH)` to the final pending path, then parent-directory `fsync` before any protected mutation. A kill before link leaves no named state. A kill before the parent flush yields either no authoritative envelope and no mutation or the complete self-contained envelope. Host preflight rejects filesystems without the required semantics. Afterward the owner creates and flushes the transaction directory and byte-identical create-new `bootstrap.json`; if killed first, only the matching pending envelope can reconstruct those exact embedded bytes. Every later pending generation increments by one, binds the prior pending digest, is first create-new and flushed in transaction `pending-generations/`, then replaces the top-level pointer with byte-identical file-flushed same-directory temporary, atomic rename, and parent flush. Exactly one matching archived generation ahead of the pointer may be adopted after full revalidation. A later pointer without its archive, a skipped generation, or multiple next archives blocks. Immutable records use create-new, file flush, and parent flush.
- `afterlight.transaction.boot-continuation.v1` records bind exact active transaction, prior continuation, old boot, container and health values or authenticated nulls, new boot and mandatory boot-close evidence, current full transaction state, stopped-service observation, and next phase. The immutable record is flushed, then pending advances to a generation binding it and the predecessor pending digest, and that pointer is flushed before a new-boot service or container start. `afterlight.transaction.health-supersession.v1` records bind old and new immutable health receipts, both boot and container identities, continuation and progress tips, active release, state digests, gate generations, and predecessor supersession tip. The record is flushed, then pending advances to bind its digest before operation success, a not-yet-published rollback activation, or consumption. Exactly one valid next immutable record beyond either pending tip may be adopted by exact resume; a second, skipped, or mismatched record blocks. An already durable pre-consumption activation stays immutable and the consumed tombstone binds it plus the later chain tips. Same-boot container replacement still requires supersession. No terminal or consumed transaction can create either record.
- `${RELEASE_STATE_DIR}/v0.9.0-rc.1/` is outside every Git worktree and stores public-safe `E-acceptance.json`, `E-acceptance.json.sha256`, `E-client-release.json`, and `E-client-release.json.sha256`. These are not VPS HMAC records and cannot be committed into `E`.

## Maintenance Access Gate

The gate has exactly three authenticated modes:

1. `closed` has no permissive lease elements. Permanent rules drop new and established traffic to Minecraft TCP `25565` and voice UDP `24454` from external, host, loopback, and peer-container paths, leave unpublished internal RCON control available, terminate existing game sessions, and require zero connected players when Minecraft is running.
2. `tester-only` has one nonce-bound lease generation implemented only by set elements with at most 15-second kernel timeouts and permits only canonical IPv4 or IPv6 CIDRs from mode `0600` `${SECRETS_DIR}/maintenance-testers.txt`. Receipts record only the allowlist SHA-256 and entry count. Every renewal requires a newly published 15-second current-channel freshness record for the same SHA.
3. `production-open` has one nonce-bound lease generation whose elements have the same timeout and removes only AFTERLIGHT's maintenance restriction. It never broadens the baseline host firewall or bypasses the Minecraft whitelist. Its kernel timeout can never extend past the current freshness expiry.

`server/scripts/maintenance.sh` is the sole public transition authority. Every public transition first takes `${STATE_DIR}/ops.lock`, then the short root-owned `${STATE_DIR}/maintenance/gate.lock` when local gate work begins. All remote accepted-mode and Pages checks finish before the gate lock, then every local receipt, predecessor, generation, boot, service, promotion guard, reconciliation, blocker, authorization, freshness, and live-rule fact is revalidated while it is held. `close --reason TOKEN` owns new logical and kernel generations, atomically removes every permissive element, unlinks only the matching current freshness pointer and flushes its parent, terminates sessions, proves zero players, re-reads the live table, and proves zero lease elements for the owned generation before publishing closed. A stale nonmatching pointer blocks rather than being deleted. `status --require MODE --receipt-out RECEIPT` holds the gate lock while authenticating durable state, current freshness when open, kernel lease, reconciler heartbeat, live rules, connections, service, players, and unresolved state. Tester opening requires exact accepted release and current health receipts. Production opening requires those plus a general join receipt for every eligible lineage and exact finalized transaction fields for rollback.

Every ordinary transition create-new publishes authenticated intent before its first gate or kernel mutation and exactly one terminal before another transition may begin. Normal completion publishes `committed`. A killed transition without terminal blocks every later transition and ordinary Compose. Reconciliation is itself a transaction. Its first durable authority is an atomic self-contained pending envelope that names the exact interrupted intent and all observed predecessor, authorization, boot, generation, and live-rule facts. Create-new progress generations surround authorization invalidation, lease removal or expiry, new generation ownership, closed state, receipt, proof, original `abandoned-closed` terminal, and reconciliation terminal. If one progress or archived pending generation is ahead of the active pointer, replay may adopt only that exact next generation; only generation zero can reconstruct missing `bootstrap.json` from identical pending bytes. After both terminals, one final cleanup-intent record is flushed, the next pending generation is archived, pending advances to `terminalizing-cleanup`, then unlink and parent `fsync` are the last writes. No post-unlink record exists. A surviving pointer repeats only cleanup; absence plus the matching terminal and cleanup intent is complete. A kill after the original terminal therefore resumes reconciliation cleanup rather than rejecting an already terminalized transition.

`maintenance.sh reconcile --intent INTENT --confirm TRANSITION_ID` and internal startup `--auto-detected DETECTION --lock-held` are the only entry points and run the same engine. Manual invocation starts or resumes it when the services are disabled or have stopped on a trust failure, derives the deterministic detection path, and must bind an existing matching startup detection rather than substitute null. Boot-gate and reconciler startup always force live rules closed first, create or authenticate the deterministic detection ID derived from transition ID and intent digest, then automatically start or resume it before Compose. A kill after detection but before pending publication can only reuse those exact bytes. A completed repeated invocation verifies the same reconciliation terminal and returns without mutation. Neither entry point continues an interrupted open. No new transition is legal until the interrupted transition and reconciliation terminals are durable and `reconcile-pending.json` is absent.

Opening writes and flushes transition intent plus one-time authorization bound to current boot, reconciler process epoch, expected predecessor, expected kernel generation, health, join when required, release, lineage, and blocker-free state. After complete local revalidation it samples `CLOCK_BOOTTIME`, writes and flushes the first immutable current-channel freshness record with expiry exactly 15,000,000,000 nanoseconds later, and atomically replaces the freshness pointer. Only then can it install one lease generation composed solely of set elements. Immediately before atomic replacement it recomputes positive remaining lifetime and rounds the kernel timeout down to supported resolution. While still holding the gate lock it proves nonce, process epoch, membership, remaining timeout, freshness digest, kernel generation, and live-rule digest, publishes completed state, receipt, and `committed` terminal, then waits for a matching reconciler heartbeat. A kill after lease installation has prior durable authorization and freshness but no unbounded permission: without matching completed state, terminal, and same-process heartbeat, every element expires within 15 seconds and cannot renew.

Every `gate_reconciler.py` startup first takes the operations lock then gate lock, forces live rules closed, creates or authenticates unresolved detection, runs or resumes the shared reconciliation transaction, publishes and flushes a startup-close intent, creates a new random runtime epoch and kernel generation, publishes a `committed` authenticated close, and proves zero permissive elements. It then releases the operations lock. Each loop checks at least every 5 seconds. In an open mode it first takes the gate lock to snapshot boot, process epoch, authorization, completed state and terminal, logical and kernel generations, active release and lineage, health and join digests, current freshness tip, blockers, rule digest, and lease identity, then releases the lock. It runs `release_gate.py current-channel` with a four-second overall deadline and no lock held. It then retakes only the gate lock and completely revalidates the snapshot. A matching successful probe samples `CLOCK_BOOTTIME`, creates and flushes the next record and pointer, recomputes positive remaining lifetime, rounds the kernel timeout down, and atomically replaces the lease before kernel proof and heartbeat. A failed probe, timeout, changed `main`, changed Pages deployment or bytes, malformed response, invalid clock, or expired candidate freshness creates a fail-closed intent for the still-matching generation, removes all leases immediately, invalidates matching freshness, owns new generations, proves closed, terminalizes if uninterrupted, and stops Compose. If intent publication or another durable close write fails, it still removes every lease under the gate lock as an emergency safety action, stops Compose, records no invented terminal, and leaves startup detection plus the same reconciliation protocol to classify durable state. A changed local snapshot discards the remote result. It never waits for the operations lock while holding the gate lock. Therefore close or drift cannot be undone by an old authorization or stale probe.

In closed mode, only the exact authenticated install, update, recovery, or pre-consumption rollback activation owner whose operations lock remains held may keep Minecraft running without a lease for its bound setup, staging, protected-backup, activation, or health phase. On a new boot it must first publish its matching continuation. A promotion guard permits no open mode and no unrelated operation. No exception permits an unjournaled restart. Every other failure removes all lease elements, proves closed, and stops Compose within one interval. `afterlight-gate-reconciler.service` uses `Type=notify`, `NotifyAccess=main`, `Restart=always`, and `WatchdogSec=10s`; it accepts `READY=1` only after startup closure and `WATCHDOG=1` only after a complete successful loop, and it is required by `afterlight-compose.service`. Every restart creates a new terminalized closed epoch rather than replaying prior open authority.

Every boot ignores persisted tester-only or production-open authority. `afterlight-maintenance-gate.service` takes operations then gate lock, force-removes every lease as an emergency safety action, records unresolved detection, and runs or resumes the same reconciliation transaction as the manual command. Only after both reconciliation terminals and pending cleanup may it publish and flush a boot-close intent, write and flush a new boot-closed receipt and `committed` terminal, and prove zero permissive elements. `operation_state.py boot-check` then requires complete host bootstrap and rejects every unresolved, partial, inconsistent, or unsafe reconciliation, promotion, operation, rollback, continuation, supersession, or offline-marker state. Only blocker-free state permits ordinary Minecraft startup behind closed ingress. An exact active transaction may instead be resumed manually while ordinary startup remains blocked. Reopening requires accepted release revalidation, health from the new container start, tester-only access, an exact current-release client receipt and join for that boot and container, and a separate production-open command.

`maintenance.sh attest-join` is general to install, update, reboot, protected-maintenance return, and rollback. It requires tester-only state, fresh same-container health created after tester-only opening for those exact logical and kernel gate generations and a valid freshness generation, exact released-client artifact receipt, active SHA and lineage, explicit operator confirmation, a canonical create-new receipt output beneath `${STATE_DIR}/maintenance/joins/`, and rollback transaction fields when applicable. Health and join receipts expire after 600 seconds for use in a new transition. Production open always requires fresh accepted-release revalidation plus matching unexpired tester-generation health and join receipts bound to both gate generations and their freshness lineage at authorization. Once production-open is durably published, later health or join expiry alone does not close it, but every kernel renewal requires a new current-channel freshness generation. Any opening after close, restart, or reboot requires new health and join receipts. Recovery lineage cannot open directly.

Protected backup always invokes close and then status under the same inherited operations lock before starting the backup image. It requires the close intent, `committed` terminal, owned logical and kernel generations, and gate-locked zero-lease proof. Bundle publication rechecks those generations, terminal, and live-rule digest under the gate lock. A failed or unterminated close, player reconnect, renewal race, rule change, or reconciler mismatch produces no completed protected bundle and leaves the gate closed. Scheduled online backup is the only backup class that may run without changing an already authenticated gate mode. The offline protected branch is internal to rollback prepare and additionally requires its pending bootstrap and marker progress lineage.

Startup and manual maintenance recovery are explicit entry points to one protocol, not competing contracts. Startup always force-closes and attempts exact automatic reconciliation before Compose. The manual form is used when startup is disabled or stopped on a trust failure, and it starts or resumes the same pending reconciliation:

```bash
server/scripts/maintenance.sh status --require closed

server/scripts/maintenance.sh reconcile \
  --intent "${STATE_DIR}/maintenance/intents/${transition_id}.json" \
  --confirm "${transition_id}"

server/scripts/maintenance.sh status \
  --require closed \
  --receipt-out "${STATE_DIR}/maintenance/proofs/${proof_id}.json"
```

The first status may fail while reporting the blocker. If startup already created `reconcile-pending.json`, the manual command must resume that exact ID and cannot create another. If startup completed, the same command only verifies the terminal. The final status must prove the new closed generations, absent reconciliation pointer, and both terminals before any later transition or backup.

Tests place deterministic barriers during the unlocked remote refresh, after renewal revalidates old open state, and after close owns its new generation. Every legal lock schedule must end with the close-owned generation and zero permissive elements, and no stale probe may publish. SIGKILL before every maintenance terminal requires exact `abandoned-closed` reconciliation. SIGKILL during reconciliation covers pending link and parent flush, each progress generation, original terminal, reconciliation terminal, pointer unlink, and final directory flush; startup and manual entry must converge on one ID and byte lineage. SIGKILL after a durable ordinary `committed` terminal with no reconciliation pending requires status verification and makes a new reconciliation reject it as already resolved. Tests also cover freshness receipt and pointer publication, remote timeout and drift, authorization, rule publication, state, receipt, heartbeat, and each file and parent-directory flush.

## Lock Model

Every top-level mutating command opens and acquires `${STATE_DIR}/ops.lock` once, keeps that one Linux file descriptor open for the full operation, and exports its number as `AFTERLIGHT_OPS_LOCK_FD`. A nested maintenance command receives the inherited open descriptor and uses an internal `--lock-held` contract. It validates that the descriptor is numeric, open, and points through Linux `/proc/self/fd` to the canonical operations lock, then requires nonblocking `flock -n` on that same descriptor to succeed. The inherited locked open-file description succeeds without reacquisition; a separately opened descriptor fails while the parent lock is held. Any command that also needs `${STATE_DIR}/maintenance/gate.lock` takes it only after the operations lock and releases it before releasing operations. No path may invert this order.

Direct `backup.sh` calls acquire the operations lock normally. Backup calls nested beneath update, rollback, or Chunky reuse the parent's descriptor. Tests cover update-to-backup, rollback-to-backup, and pregen-to-backup execution, assert that the same descriptor remains held, and fail forged or separately opened descriptors. The normal online image branch adds `${BACKUP_DIR}/.mc-backup-lock` as a separate archive-serialization lock with the existing fixed acquisition order. The offline paused branch has no image lock and remains serialized by the inherited host operations descriptor. No nested path may reacquire the operations lock and self-deadlock.

Maintenance transitions, durable maintenance reconciliation, open authorization, join attestation, promotion guards, install, update, recovery, rollback bootstrap and progress, resume, abandonment, activation, boot continuation, health supersession, transaction consumption, finalize-only reconciliation, and production opening all use that same operations lock. Gate validation and publication additionally use the gate lock. Reconciler renewal and emergency fail-closed mutation are deliberate exceptions: renewal takes one gate-locked snapshot, performs remote work with no lock, retakes only the gate lock, and never waits for operations. A matching refresh then holds the gate lock continuously across complete local revalidation, freshness publication, rule replacement, proof, and heartbeat. Failure holds it across fail-closed intent publication and immediate lease removal. An exact authenticated operation or pre-consumption activating rollback transaction may keep Minecraft running behind closed ingress only while its operations lock remains held. Status, health, continuation, supersession, and transaction proofs are therefore ordered with the state and kernel generation they authenticate rather than being racy observations.

## Install, Update, and Recovery Transactions

Install, update, and recovery share `afterlight.operation.*.v1` records and one atomic bootstrap protocol. Each start performs read-only authentication first. Its first authoritative state mutation writes complete canonical `afterlight.operation.pending.v1` bytes to an unnamed same-directory `O_TMPFILE`, file-flushes them, links create-new to `${STATE_DIR}/operations/pending.json`, and parent-directory-flushes that link. Only then may it create the transaction directory, candidate, protected backup, RCON secret, service state, `/data` object, managed ledger, provenance, journal, quarantine object, active-release record, container, or health receipt. A kill before link leaves no named authority and no protected mutation. A kill before the parent flush yields either no envelope and no mutation or the complete envelope. Unsupported filesystem semantics fail host preflight.

The self-contained pending bootstrap records operation kind and ID, phase, exact command, tool version, accepted release and bundle evidence, initial boot plus logical and kernel gate generations, service state, complete data inventory or authenticated empty observation, root identity, ledger, provenance, journal, quarantine, active release and lineage, planned paths, expected mutations, predecessor terminal, progress tip, boot-continuation tip, health-supersession tip, promotion closure and observation or authenticated nulls, transaction path, publication nonce, and HMAC. Its exact first bytes are retained as transaction `bootstrap.json`; if killed before that copy, resume reconstructs only identical embedded bytes. Append-only authenticated progress is flushed before and after each mutation boundary and binds expected and observed device, inode, inventory, digest, service, gate, container, continuation, supersession, and receipt state. An unexplained transaction record, progress gap, extra envelope, wrong terminal, or mismatched digest blocks ordinary Compose instead of being cleaned heuristically.

Exact resume holds the operations lock and revalidates every input, receipt, progress link, path identity, full inventory, state digest, service, gate, and container before repeating only an idempotent check or provably incomplete step. If the current boot differs, it first publishes `afterlight.transaction.boot-continuation.v1`, binding the bootstrap, previous continuation, old boot, container and health values or authenticated nulls, new boot and mandatory boot-close evidence, complete transaction state, stopped service, and exact next phase. That immutable record and parent are flushed, then pending atomically advances to bind its digest and predecessor pending generation and its parent is flushed before any transaction-owned service or container start. Exactly one matching record ahead of pending may be adopted after a kill. Same-boot container replacement performs the same state validation but needs no boot continuation.

After resumed health succeeds, every old health receipt remains immutable. If the prior health names another boot or container start, the transaction publishes fresh health binding its predecessor health and predecessor supersession tip, then `afterlight.transaction.health-supersession.v1` binding old and new receipts, both boot and container identities, continuation and progress tips, release, lineage, state digests, gate generations, and predecessor supersession. Both immutable records are flushed, pending atomically advances to bind the new supersession tip, and its parent is flushed before success. Exactly one matching supersession ahead of pending may be adopted after a kill; competing, skipped, or mismatched records block. Only the exact active pending envelope and operations-lock owner can advance this chain. Authenticated abandonment is available only while the original prestate can be restored exactly with ingress closed and services stopped. Install and recovery abandonment ends before the first Minecraft world start and verifies the original empty prestate. Update abandonment ends before first `/data` publication and verifies the full original inventory and state. Later abandonment rejects.

Every operation terminal uses one ordering. After all terminal preconditions, the next archived pending generation embeds complete canonical terminal bytes, target path, digest, and exact blocker or rollback-request bytes when applicable. Pending atomically advances to `terminalizing-success`, `terminalizing-failure`, or `terminalizing-abandonment`, and its parent flush is the irrevocable terminal decision. The exact embedded outputs are then create-new and parent-flushed. Only then is the matching pending envelope unlinked and its parent flushed. Success binds final inventory, ledger, provenance, completed journal, quarantine disposition, active release, service, closed gate, latest health, and every bootstrap, progress, continuation, and supersession digest. Because health and supersession were current before the decision, a kill after that pointer flush resumes only terminal materialization or cleanup, even on another boot, without a continuation or service start. A kill before it remains an active transaction and must use cross-boot continuation before another start or success decision.

`operation_state.py boot-check` runs before ordinary Compose and scans complete maintenance transition and reconciliation, freshness, promotion, operation, rollback, continuation, supersession, and `.paused` marker state. An unresolved operation, promotion guard, offline marker, or unsafe failure stops Minecraft and keeps ingress closed. The only service-start exception is the exact operation or pre-consumption activating rollback owner holding the operations lock while its authenticated phase permits setup or health behind closed ingress. Update health failure terminalizes `failed.json`, a persistent operation blocker, and the rollback request, then removes the matching pending envelope. Rollback prepare must bind those exact failure records and their continuation and supersession tips. Only successful rollback activation finalization may write the resolution tombstone and remove the blocker. A kill during failure or blocker publication can only resume those same records.

A normal post-launch update must close before its candidate is promoted to `main`. `update.sh authorize-promotion` atomically publishes `afterlight.update.promotion.pending.v1` in phase `closing`, then closes maintenance and records the exact close intent, `committed` terminal, closed proof, zero leases, and zero players. It advances the guard to `closed-authorized`, binding candidate, predecessor `main`, active release, boot and reconciler epochs, logical and kernel generations, issue time, and closed-state predecessor digest. The guard blocks every open transition, unrelated operation, and second promotion. A killed authorization resumes only this guard's missing close and proof steps. The operator performs the Git push manually. `observe-promotion` must see exact remote `main` and prove the guard close remains in the current closed predecessor chain with no intervening tester or production transition before it creates immutable `observed.json`. Update start atomically publishes its operation envelope binding closure and observation while the guard still exists, then writes the promotion consumed tombstone, removes only that guard, and flushes its parent. A kill during transfer leaves both blockers for exact update resume. Cancellation is authenticated and legal only before observation while remote `main` remains the predecessor.

```bash
server/scripts/update.sh authorize-promotion \
  --sha "${release_sha}" \
  --predecessor "${current_main}" \
  --confirm "${release_sha}"

# The operator performs the reviewed exact-SHA promotion. No maintenance script pushes Git.
git push origin "${release_sha}:refs/heads/main"

server/scripts/update.sh observe-promotion \
  --promotion "${promotion_id}" \
  --pending "${STATE_DIR}/operations/promotions/pending.json" \
  --confirm "${release_sha}"
```

If authorization is killed, resume only its exact guard:

```bash
server/scripts/update.sh authorize-promotion \
  --resume "${promotion_id}" \
  --pending "${STATE_DIR}/operations/promotions/pending.json" \
  --confirm "${promotion_id}"
```

If the operator abandons before observation and remote `main` still equals `${current_main}`, cancel without reopening:

```bash
server/scripts/update.sh cancel-promotion \
  --promotion "${promotion_id}" \
  --pending "${STATE_DIR}/operations/promotions/pending.json" \
  --confirm "${promotion_id}"
```

Initial empty-host publication is outside this post-launch guard because its preconditions reject any installed data or active release. Rollback after update failure is already bound to the authenticated failure blocker and closed proof, so it follows the rollback contract instead of creating a normal update guard. A deliberate rollback without that blocker is not a normal update: current-channel renewal closes any open host as soon as `main` moves, and prepare independently closes and proves zero leases and players before protected mutation. Neither exception can satisfy normal `update.sh start`.

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
  --pending "${STATE_DIR}/operations/pending.json" \
  --confirm "${operation_id}"

server/scripts/install.sh abandon \
  --operation "${operation_id}" \
  --pending "${STATE_DIR}/operations/pending.json" \
  --confirm "${operation_id}"
```

Update uses the same identity contract. Abandon succeeds only before first managed-data publication. After an authenticated rollback-required failure, neither update resume nor abandon may restore world data:

```bash
server/scripts/update.sh start \
  --sha "${release_sha}" \
  --release-receipt "${release_receipt}" \
  --promotion-closure "${STATE_DIR}/operations/promotions/transactions/${promotion_id}/closure.json" \
  --promotion-observation "${STATE_DIR}/operations/promotions/transactions/${promotion_id}/observed.json"

server/scripts/update.sh resume \
  --operation "${operation_id}" \
  --pending "${STATE_DIR}/operations/pending.json" \
  --confirm "${operation_id}"

server/scripts/update.sh abandon \
  --operation "${operation_id}" \
  --pending "${STATE_DIR}/operations/pending.json" \
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
  --pending "${STATE_DIR}/operations/pending.json" \
  --confirm "${operation_id}"

server/scripts/recover.sh abandon \
  --operation "${operation_id}" \
  --pending "${STATE_DIR}/operations/pending.json" \
  --confirm "${operation_id}"
```

The implementation tests SIGKILL before and after unnamed bootstrap file flush, pending link and parent flush, archival bootstrap, every pointer generation, progress receipt, boot continuation, candidate, backup, stop, secret, setup, rename or managed publication, ledger, provenance, journal, quarantine, active release, container start, stale-health observation, fresh health, health supersession, terminal, blocker, pointer unlink, and every parent-directory flush. It reboots after boot-bound health and before success. Promotion tests cover guard bootstrap, close, closure, manual-ref observation, transfer to update, consumption, cancellation, and every flush. Each resulting state has exactly one authenticated next action, with no stale-health acceptance or mixed-data ordinary restart path.

## Update and Rollback Model

After its authenticated promotion guard has closed the host and observed the exact candidate at remote `main`, an update authenticates remaining staging inputs read-only and atomically transfers that guard into its operation bootstrap before candidate creation. It takes a protected backup that closes and proves the gate, and activates only validated pack-managed files. Packwiz updates pack-managed paths in `/data`; the prohibition is against automatic world restore, world deletion, or rollback. A healthy update marks `lineage=update`, starts the new container closed, writes fresh health, publishes success, and clears its exact pending envelope. If killed after health and rebooted before success, only that active update may publish a boot continuation, start the same release closed, create new health, and supersede the stale receipt before success. The operator then opens tester-only, joins with the exact released client, records the general join receipt, and separately opens production.

An update health failure stops Minecraft, leaves the gate closed, exits with code `6`, preserves logs, candidate files, Packwiz provenance, backup, ledger, journal, quarantine state, progress, continuation and supersession records, and receipts, and writes one authenticated failure terminal, persistent operation blocker, and rollback-request receipt in durable order. All three bind the same bootstrap, promotion closure and observation, progress, continuation, and supersession tips, latest health lineage, failed data inventory, active release, backup, and state digests. It prints the fixed runbook path and exact failed bundle values. It cannot print a valid prepare command until the operator has created rollback SHA `R` and an accepted `R` receipt, and it never restores world data automatically. A kill during failure publication remains blocked and may only finish those exact records.

Rollback remains a truthful two-phase operation, but the operator-owned Git promotion now precedes data-changing prepare so prepare can bind the exact rollback release:

1. From authenticated bundle snapshots for historical SHA `H`, the operator creates and reviews normal rollback commit `R`, pushes exact `R` through `dev`, promotes it unchanged to `main`, waits for exact-SHA CI and Pages parity, and runs accepted mode externally. Maintenance tooling never commits, reverts, pushes, mutates branches or tags, or calls a GitHub write API.
2. `rollback.sh prepare` performs read-only authentication of named bundle, `H`, `R`, canonical accepted `R` receipt, raw-`R` equality with historical snapshots, current accepted `main`, Pages, current data identity, ledger, provenance, journal, quarantine, services, logical and kernel gate generations, and planned paths. When entered from update failure, it also requires the exact paired rollback request and operation blocker and authenticates their bootstrap, progress, continuation, supersession, failed inventory, active release, and backup digests. Before any gate, service, backup, marker, rename, extraction, activation, or data mutation, it atomically publishes complete schema `afterlight.rollback.pending.v1` in phase `preparing`. The embedded bootstrap binds transaction ID, every input digest, root device and inode, active release and lineage, initial boot and current state observations, operation blocker when present, planned paths and marker nonce, tool version, predecessor, progress tip, and authenticated null activation, continuation, and supersession fields. No separate prepare-intent or detached-digest window exists.
3. Under the inherited operations lock, prepare closes and proves the gate, stops Minecraft and scheduled backup idempotently, and proves both stopped. It publishes marker-intent progress, then invokes only `backup.sh --class protected --reason rollback-current --offline-parent TRANSACTION_ID --pending ROLLBACK_PENDING --marker-intent PROGRESS --lock-held`. The child authenticates the parent and exact HMAC marker identity before using the pinned image's paused branch, with no RCON and no `.mc-backup-lock` assertion.
4. Prepare writes authenticated append-only progress before and after every gate close and proof, service stop, marker intent, marker create, marker file and data-directory flush, offline backup, marker unlink and second directory flush, inventory, candidate, quarantine rename, publication, raw-`R` overlay, journal, ledger, provenance, and final inventory step. Root device, inode, path, digest, boot-continuation, pending generation, marker bytes, and marker identity checkpoints distinguish not-started, completed, and crash-between-syscall states. Prepare cannot mark the release or terminalize while its marker remains.
5. Completed prepare removes and flushes its exact marker, marks `lineage=rollback`, and writes schema `afterlight.rollback.prepare.v1`, binding bootstrap and progress-chain tips; bundle and archive metadata; `H`; `R`; release evidence; raw and historical manifests; failed-current offline bundle; pre-restore and prepared inventories; ledger; active release; candidate and installer provenance; completed journal; quarantine; stopped services; closed gate; marker creation and removal evidence; and predecessor digests. It then creates and flushes the complete phase-`prepared` pending-generation archive before atomically replacing `pending.json` with those identical bytes and flushing its parent. The generation carries immutable bootstrap, prepare receipt, progress tip, and predecessor pending digest. A receipt with phase still `preparing` or exactly that archive one generation ahead remains blocked but has one exact repair.
6. Exact transaction files are `bootstrap.json`, `prepare-progress/<sequence>.json`, `boot-continuations/<sequence>.json`, `health-supersessions/<sequence>.json`, `prepare.json`, its digest, all inventories, `prepare-abandoned.json`, archived activation intent, `activation.json`, `activation-finalized.json`, `join.json`, and `production-open.json`. The consumed tombstone remains under `${STATE_DIR}/rollback/consumed/`. Every stale health receipt and every continuation or supersession predecessor remains immutable.
7. `prepare --resume` accepts only the original pending bootstrap and transaction. It revalidates immutable inputs and progress, reconciles exact root and marker identities including marker-without-post-progress, unlink-without-post-progress, and receipt-before-phase-replacement, and repeats only idempotent or incomplete safe steps. `rollback.sh abandon` is idempotent for the exact pre-activation transaction, authenticates and removes only its own marker, restores and verifies pre-prepare data, ledger, provenance, journal, quarantine, and root identity from authenticated progress, writes abandonment, removes only the matching pending envelope, and clears only the rollback prepare blocker after directory-flushed proof. It never clears a failed-update operation blocker. Failure leaves ingress closed, services stopped, backup modes blocked, and Compose blocked. A valid abandonment receipt is terminal and makes prepare resume, activate, finalize-only, and receipt reuse fail.
8. Any rollback pending envelope blocks ordinary Compose and systemd startup until exact abandonment is fully reconciled or activation is finalized with no pointer. Activate authenticates phase `prepared` and every bound input under the operations lock. Before start it atomically replaces pending with phase `activating` and the complete activation intent, flushes the parent, then archives those identical intent bytes. It becomes the sole exception allowed to start Minecraft behind closed ingress while its lock remains held. It writes deterministic sequence-zero closed health for `R`. While still closed, it publishes `activation.json` once, binding the current continuation and supersession tips. Publication then continues with consumed tombstone, activation-finalized receipt, pending unlink, and parent-directory flush. If prepare bound an update blocker, the next order is operation resolution tombstone, blocker unlink, and parent-directory flush. Only after no unresolved rollback or operation state remains may the command create a timeout-bound tester lease using the latest current-container closed health and then write tester-generation health.
9. Ordinary activate and resume reject consumed state. Before consumption, resume authenticates phase `activating` and continues only missing idempotent steps. On another boot it publishes and flushes the exact boot continuation including the next deterministic health path, advances and flushes pending to bind it, then starts. An existing current-container health output may be reused only when it exactly matches. Stale health is retained; `--superseding-closed-health-out` must name the new sequence path, new health and its supersession are flushed, and pending advances and flushes the new tip before activation or consumption. If `activation.json` already exists, it remains immutable. The consumed tombstone binds its digest plus the latest continuation, supersession, and fresh-health digests. `--finalize-only` is the sole consumed-state reconciliation path for an exact matching pending pointer or bound operation blocker plus activation receipt, latest chain tips, and consumed tombstone. It revalidates exact `R` data and transaction state, then may write a missing finalized receipt, remove that exact pointer, write a missing operation resolution tombstone, and remove only the exact bound blocker in prescribed order. It cannot start, restart, continue a boot, supersede health, change gate mode, consume again, or alter transaction inputs, and the live service may be running closed or stopped. Finalized plus no pending or blocker is already complete and does not use finalize-only. If tester health is absent after any consumed state, the operator closes and proves the gate, starts the normal Compose unit behind closed ingress, creates new closed health, and performs explicit tester-only access plus tester health. A mismatched set fails closed.
10. SIGKILL before or after every pending bootstrap, marker, prepare, abandonment, activating-phase replacement, boot continuation, old and new health, health supersession, activation, operation-blocker resolution, tester-authorization, and tester-health publication boundary has one defined outcome: exact resume with same-transaction continuation before consumption, idempotent abandonment, finalize-only for consumed plus any exact residual, or explicit post-finalization closed restart and tester recovery. Reboot after closed health but before activation or consumption is mandatory coverage. Unresolved state forces the gate closed, blocks unattended Compose and backup on boot, and stops a closed activation service within 5 seconds after its lock owner dies.
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
  --pending "${STATE_DIR}/rollback/pending.json" \
  --confirm "${transaction_id}"
```

Abandon restores and verifies the pre-prepare state and ends the transaction. No activation or opening command follows a successful abandonment:

```bash
server/scripts/rollback.sh abandon \
  --transaction "${transaction_id}" \
  --pending "${STATE_DIR}/rollback/pending.json" \
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

If path A was killed before consumption on the same boot and container, resume only the same activation with the same output paths. Existing output files must authenticate as exact transaction outputs:

```bash
server/scripts/rollback.sh activate \
  --transaction "${transaction_id}" \
  --receipt "${STATE_DIR}/rollback/transactions/${transaction_id}/prepare.json" \
  --confirm "${transaction_id}" \
  --closed-health-out "${closed_health_receipt}" \
  --tester-health-out "${health_receipt}" \
  --resume
```

If the boot or container changed and prior closed health exists, retain that path and resume with the next deterministic output. The command publishes the boot continuation before start, writes the new receipt, then publishes health supersession. This remains legal even when `activation.json` already exists, because consumption binds its immutable digest plus the extended chain:

```bash
server/scripts/rollback.sh activate \
  --transaction "${transaction_id}" \
  --receipt "${STATE_DIR}/rollback/transactions/${transaction_id}/prepare.json" \
  --confirm "${transaction_id}" \
  --closed-health-out "${closed_health_receipt}" \
  --superseding-closed-health-out "${next_closed_health_receipt}" \
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

`server/README.md` must show how each variable is obtained from a preceding receipt, mark activation path A and path B as mutually exclusive, print the exact expected mode after every command, and document host bootstrap, atomic pending bootstrap, promotion closure, status, exact same-boot and cross-boot resume, health supersession, safe abandonment limits, failure blockers, automatic and manual maintenance reconciliation, channel-freshness and kernel-lease expiry, reboot closure, offline marker recovery, rollback finalize-only, Compose blockers, and forensic paths. Empty-host recovery uses a completed local trust bootstrap, creates its fresh RCON secret only after atomic operation bootstrap, creates closed gate state, marks active release `lineage=recovery`, and cannot open production. To reopen, the operator creates accepted `R` and completes the normal local rollback prepare, activate, tester-only join, and production-open sequence, replacing recovery lineage with the bound rollback transaction. Restoring or starting a server alone is not evidence that the mutable client channel is safe.

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
10. Treat release publication and server access as separate gates. The tag never reopens a host. Install, update, reboot, protected-maintenance return, and rollback all start closed and require their own current release, post-start closed health, tester-only authorization, tester-generation health, released-client join, and explicit production-open sequence. Every open rule renewal then refreshes a 15-second current-`main` and Pages lease. A later channel move closes instead of extending stale authority. Recovery lineage remains closed until a normal accepted local rollback replaces it, then the rollback opening contract applies.
11. Treat any later implementation change as a new subject and restart from skeptical review. Never patch between the final accepted gauntlets and the tag.

## Deferred Live Evidence

These checks cannot be truthfully completed by plan text or a Mac-only authoring session:

- Baseline VPS firewall exposes only Minecraft TCP and voice UDP when maintenance is production-open.
- Permanent default-drop gate rules precede Docker for IPv4 and IPv6; every permission has prior durable same-process authorization and a current authenticated channel-freshness generation, expires within 15 seconds without renewal, and closes immediately after current `main` drift, Pages drift, refresh failure, reconciler death, watchdog stall, rule drift, missing state, or divergent state. Deterministic close-versus-renewal and remote-probe barriers prove every schedule ends in the close-owned generation with zero permissive elements and no old authorization or stale probe republished.
- Host filesystem provides reliable `flock`, inherited descriptor behavior, and same-filesystem atomic rename.
- Graceful stop finishes inside two minutes without exit 137.
- Ten-gigabyte heap remains below the 13 GB container limit under gameplay and Chunky load.
- Backup throughput, restore throughput, free-space checks, and quarantine capacity fit the real world size.
- Every host reboot ignores persisted open state, proves closed before Compose, automatically runs or resumes the same durable maintenance reconciliation used manually, and never starts ordinary Compose with an unresolved promotion, operation, rollback, continuation, supersession, or offline marker. A blocker-free reboot restores the stack without creating a new world and requires fresh current-release, post-start health, tester-only, join, and production-open evidence.
- Two released clients join, general join attestation works after install, update, reboot, and protected-maintenance return, whitelist works, and voice chat works over UDP.
- Installed Chunky RCON output is classified conservatively for active, paused, complete, and unknown states.
- The full pack boots and plays on arm64.
- An encrypted offsite bundle restores onto a genuinely empty replacement host after one-time local trust bootstrap, and every interrupted bootstrap or recovery phase remains boot-blocked until exact resume or safe abandonment. A kill after recovery health and reboot before success retains old health, publishes a same-transaction boot continuation, creates new-container health, and durably supersedes the old receipt before success.
- A real protected backup proves the closed gate before archive creation and cannot publish after gate drift or player reconnect.
- A normal update first publishes an authenticated promotion guard, closes and proves maintenance, prevents reopening while the operator moves exact `main`, observes that exact candidate with an uninterrupted closed predecessor chain, and transfers the guard into the update bootstrap. A bypassed, different, or canceled promotion cannot start update and current-channel drift closes any open host.
- A real update failure remains closed and rollback prepare proves both services stopped before the pinned parent-authenticated offline protected-backup branch, with no RCON or image-lock claim. SIGKILL or reboot at every marker boundary leaves a marker that only the exact active parent can authenticate, continue, or remove; no public or scheduled backup can select offline mode from presence alone.
- SIGKILL at every install, update, and recovery boundary yields exact resume, authenticated safe abandonment, durable success cleanup, or update rollback-required failure, with no mixed-data ordinary restart. Reboot after boot-bound health proves same-transaction continuation and health supersession before success. SIGKILL at every maintenance and reconciliation boundary yields committed completion or one exact crash-resumable `abandoned-closed` reconciliation before another transition.
- SIGKILL at every rollback prepare and abandonment boundary yields exact resume or terminal authenticated abandonment. SIGKILL and reboot across pre-consumption activation health prove continuation and supersession without receipt reuse. SIGKILL across consumption, operation-blocker resolution, and tester publication yields consumed-plus-pending finalize-only or post-finalization closed restart and tester recovery without ordinary activation resume.
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
