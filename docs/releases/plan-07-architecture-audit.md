# Plan 07 Architecture Audit

Date: 2026-08-09

Status: design gate corrected after round 5 universal atomic-publication, failed-promotion, bounded-freshness, and external-receipt-pair review. No Docker, VPS, backup, recovery, CI, Pages, Prism, or release behavior is claimed by this document.

## Scope

The launch architecture was reviewed before implementation against the exact current itzg image manifests, Packwiz installer release bytes, NeoForge installer checksum, Docker Compose behavior, GitHub Actions APIs, GitHub Pages mutability, RCON secret handling, Chunky operations, Python archive extraction safety, nested Linux lock behavior, host ingress maintenance safety, renewal-versus-close concurrency, untrappable kill windows, stale reboot state, cross-boot and cross-container transaction continuity, atomic first publication, atomic publication of every later immutable record, maintenance reconciliation continuity, bounded freshness retention, normal and failed update promotion closure, fast-forward successor transfer, offline marker identity, general mutation transaction continuity, rollback backup branch safety, universal join evidence, exact client lineage, idempotent external receipt pairs, and release-evidence ordering.

The initial review found nine Critical and nine Important design gaps. A completed follow-up contradiction review found seven cross-task defects in the rewritten plan: acceptance self-deadlock, unhandled Packwiz installer state, an incorrect release-candidate manual gate, nested lock reacquisition, backup exclusions that were not part of resolved Compose, client-unsafe rollback, and evidence self-reference. A subsequent pinned-source check found that online and offline backup enter different RCON and image-lock branches. Round 1 then corrected three independent failures: maintenance was prose rather than persisted access control, rollback prepare and activate lacked one-time binding, and tag creation lacked an external accepted-mode receipt for evidence SHA `E`.

Round 2 found four Critical and two Important residual gaps. Permissive rules could outlive an untrappable kill before open-state publication; boot could replay stale production-open; rollback prepare selected online backup after update failure had stopped Minecraft; prepare had no pre-mutation intent; activation had an unhandled consumed-plus-pending crash window; and install or update could open without general released-client join evidence. That correction added timeout-bound permissions and an active reconciler, boot-closed epochs, stopped-service offline rollback backup, prepare intent plus resume or abandonment, finalize-only activation reconciliation, and one general join interface required by every production-open lineage.

Round 3 found three Critical and one Important residual gaps. Renewal could validate an old authorization and republish its lease after close removed it; install, update, and recovery lacked rollback-grade crash transactions; the final tag target `E` lacked an exact client release receipt; and a killed maintenance intent had no authenticated terminal reconciliation. The corrected plan serializes every gate observation and transition, gives every data or active-release mutation pre-mutation intent plus boot blocking and exact recovery, creates an `E` client receipt by read-only authentication of both byte-identical `S` Prism artifacts, and requires every killed maintenance transition to end in a proved-closed terminal before another transition. Implementation still requires test-first development, whole-project skeptical review, two accepted clean gauntlet runs, exact-SHA CI and Pages evidence, and the deferred live-host matrix.

Round 4 found one Critical and four Important residual gaps. A boot-bound health receipt could strand an otherwise resumable operation after reboot; separate intent, digest, and pending publications left unrecoverable bootstrap gaps; maintenance reconciliation was neither crash-resumable nor consistently automatic or manual; open-rule renewal stopped checking current `main` and Pages after authorization; and a killed public offline backup could leave `.paused` selecting the RCON-free branch after services restarted. The corrected plan gives only the exact active transaction chained boot-continuation and health-supersession authority, makes one self-contained pending envelope the atomic first durable operation publication, makes startup and manual maintenance recovery two entry points to one durable reconciliation transaction, requires every rule renewal to refresh a 15-second authenticated current-channel lease, adds a maintenance-closure guard before normal update promotion, and makes offline backup an internal rollback child whose marker lifecycle is authenticated in parent progress. Implementation still requires test-first development, whole-project skeptical review, two accepted clean gauntlet runs, exact-SHA CI and Pages evidence, and the deferred live-host matrix.

Round 5 found one Critical and three Important residual gaps. Later immutable records could expose partial final bytes because only pending generation zero used unnamed atomic staging; a promotion guard had no legal outcome after `main` moved but CI, Pages, or ref acceptance failed; five-second freshness generations accumulated without a retention owner or hard bound; and each external receipt plus detached digest pair could be stranded after the receipt became durable. The corrected plan routes every immutable record and mutable pointer through one no-clobber publication engine, retains deterministic adoption and authenticated replacement cleanup, adds a stable closed failed-candidate terminal plus same-authority fast-forward successor retarget, compacts authenticated freshness epochs under exact file and byte bounds without deleting live or unexpired references, and makes both `E` evidence pairs idempotently resumable from a valid receipt-only state. Implementation still requires test-first development, whole-project skeptical review, two accepted clean gauntlet runs, exact-SHA CI and Pages evidence, and the deferred live-host matrix.

## Threat Model and Corrections

The maintenance findings protect against Docker accepting traffic while prose says closed, an untrappable kill between permissive rule application and state publication, a dead reconciler, rule drift, a restored `/data` tree reverting access state, reboot replaying yesterday's open decision, a paused renewal restoring old permissions after close begins, an open host remaining authorized after `main` or Pages moves, and renewal storage growing until safety writes fail. Permanent rules default to closed. Tester and production permissions are lease generations made only of kernel set elements with at most a 15-second timeout. A durable current-boot, current-reconciler authorization and a current channel-freshness record whose `CLOCK_BOOTTIME` expiry is exactly 15,000,000,000 nanoseconds after issue must precede any permissive lease. Every renewal takes a gate-locked snapshot, releases the lock for a bounded current-`main` and Pages probe, then retakes the lock and completely revalidates before the sole freshness store publishes a new generation or replaces rules. Issuance is globally limited to one generation per five seconds. The 600-second evidence window can therefore cite at most 121 finite-window generations, and one current open lineage can retain only one older live-until-close anchor. Authenticated epoch compaction retains every such generation, limits leases to 8192 bytes and checkpoints to 262,144 bytes, and keeps accepted freshness state within 160 lease files, 168 total regular files, and 2 MiB. The kernel timeout is rounded down to the remaining freshness lifetime. Close owns new logical and kernel generations, removes all leases, then re-proves zero permissive elements before releasing that lock. Probe, compaction, bound, or drift failure closes immediately and stops Compose. Every reconciler process and boot begins closed. Reopening requires fresh current-release validation, post-start closed health, tester-only authorization, tester-generation health, released-client join, and production-open actions.

The general-operation findings protect against SIGKILL leaving a candidate, secret, protected backup, service, data tree, ledger, provenance, journal, quarantine, active-release record, or health receipt in a combination that ordinary boot mistakes for complete, including a kill between separate intent, digest, and pointer writes. Install, update, and recovery now authenticate read-only inputs first, atomically publish one self-contained authenticated pending bootstrap as their first durable authority, journal before and after every mutation boundary, block ordinary Compose while unresolved, and finish through exact resume, authenticated safe abandonment, or durable success. A resume on another boot publishes a same-transaction boot continuation before service start. If prior health names another boot or container, new health plus a chained supersession record must become durable before success, and every old receipt remains immutable. An update that has crossed its irreversible publication boundary may instead terminalize rollback-required failure with a persistent blocker bound into rollback prepare and cleared only by successful activation finalization.

The rollback findings protect against time-of-check to time-of-use substitution, wrong backup branch selection, mutation before durable authority, ambiguous crash points, receipt replay, orphan offline markers, and the consumed tombstone conflicting with a still-present pending pointer. Prepare atomically publishes one complete phase-`preparing` pending envelope before any mutation, stops and proves both services stopped, and invokes the offline backup interface only as its authenticated child. The parent progress chain records marker intent, exact HMAC marker bytes and identity, both directory flushes, backup observations, and marker removal before prepare can terminalize. An incomplete prepare blocks Compose and both backup modes until exact resume or authenticated abandonment restores and verifies current state. Activation atomically moves the same pointer to `activating` with the complete activation intent before start. Before consumption it may use the same boot-continuation and health-supersession protocol; after consumption only finalize-only can clear an exact matching residual and cannot start, continue, supersede, or consume again.

The join finding protects normal install, update, reboot, or maintenance return from reaching production based only on server health. A general join attestation now requires tester-only access, a fresh current-container health receipt, the exact released-client artifact receipt, active release and lineage, current boot plus logical and kernel gate generations, and explicit operator confirmation. Every production open requires fresh accepted-release revalidation, health, and join receipts. Rollback adds exact finalized transaction evidence; recovery lineage cannot open directly.

The evidence findings protect against tagging `E` after checking only CI and Pages, copying stale acceptance or client evidence from `S`, silently rebuilding the gauntleted client, writing a post-commit fact into `E`, making the workflow whose success is required wait for itself, or losing a detached digest after its fixed canonical receipt became durable. The correction runs accepted mode externally only after exact `E` CI and Pages parity complete, then creates an exact `afterlight.client.release.v1` receipt for `E` by read-only authentication of both preserved byte-identical `S` gauntlet archives and their receipts. Each receipt and deterministic digest pair has one idempotent state machine. Neither exists, exact receipt-only, or exact pair are the only nonblocking states. Receipt-only recovery reauthenticates every source and writes only the missing digest without changing valid evidence. Both canonical pairs live outside every workflow and worktree and must appear in annotated-tag and GitHub-release metadata before publication.

The maintenance-terminal findings protect against an intent surviving a kill with no truthful committed or abandoned outcome and against reconciliation itself being killed. Every transition publishes exactly one authenticated `committed` or `abandoned-closed` terminal. Reconciliation first atomically publishes a self-contained pending bootstrap, then records create-new progress generations across authorization invalidation, lease removal, generation ownership, close state, receipt, proof, original terminal, and reconciliation terminal. Its final cleanup intent and `terminalizing-cleanup` pending generation precede pending unlink and parent `fsync`, which are the last writes. `maintenance.sh reconcile` and the internal startup entry point run this same engine and can only close. Startup may force kernel rules closed before the bootstrap as an emergency safety action, but it records one deterministic detection and cannot start Compose until the durable protocol finishes. A repeated invocation reuses detection-only state or resumes or verifies the exact reconciliation ID and bytes. Until both terminals exist and the pending pointer is absent, every later transition and ordinary Compose start is blocked.

The promotion findings protect a currently open production host from learning that its mutable channel moved only after the push and protect a closed host from being stranded when the moved candidate cannot be accepted. Before a normal post-launch update, one atomic promotion authority is published, maintenance closes and proves zero leases and players, and that authority blocks every reopening. The operator still performs each Git push manually. The host must observe the exact target as remote `main` while the authority remains current and prove no intervening tester or production transition, then the update operation bootstrap binds and consumes it. Failed CI, failed or deadline-stale Pages, and unexpected ref each produce an immutable `failed-closed` attempt record under the same promotion ID. That stable terminal keeps Compose stopped and preserves all observations. The same pointer may transfer only to an explicitly confirmed successor proven to be a strict fast-forward descendant of the exact current remote object. It never creates a second authority, force-pushes, reopens, or discards a failed attempt. Cancellation is authenticated and legal only before any ref movement while remote `main` remains the original predecessor.

The record-publication finding protects every recovery protocol from a kill after a final immutable pathname exists but before its canonical bytes, authentication, owner, or mode are complete. `record_io.py` is the sole publication engine for operation, rollback, promotion, maintenance, reconciliation, freshness, health, continuation, supersession, receipt, detached digest, proof, terminal, inventory, backup, client, and release evidence. It writes complete bytes to an unnamed same-directory inode, establishes exact ownership and final mode, file-flushes, create-new links the final immutable name, and parent-flushes. Mutable pointers first have one immutable generation archive, then use one deterministic, fully flushed replacement link, atomic rename, and parent flush. Recovery has finite absent, exact-adoptable, already-current, or exact redundant-replacement-cleanup outcomes. No valid immutable final is replaced or touched, and every partial, conflicting, extra, or unauthenticated named state blocks.

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

Accepted mode writes schema `afterlight.release.acceptance.v1` as canonical UTF-8 JSON with sorted keys, fixed separators, and one trailing LF. The receipt binds repository, SHA, workflow, run, attempt, job, Pages deployment, immutable raw hashes, Pages hashes, clean client and server install results, and authenticated source completion times. A deterministic detached SHA-256 file covers those exact bytes at exactly `<receipt>.sha256` in the same canonical parent. Local wall-clock, random, inode, and worktree fields are excluded, so identical remote evidence produces identical pair bytes. Both files use the common immutable protocol. A retry always reauthenticates remote sources. When neither output exists, it creates the receipt and then the digest. A valid receipt alone re-fsyncs the parent and creates only its missing digest without replacing or changing the receipt, and a valid pair re-fsyncs the parent and returns without file mutation. Digest-only or any malformed, noncanonical, conflicting, linked, wrongly owned, or stale state blocks.

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

All state roots are canonical, root-owned, and outside `/data`. Directories are mode `0700`; locks and mutable records are mode `0600`; immutable records are already mode `0400` before a final name can become visible. `record_io.py` applies one descriptor-relative atomic protocol to every maintenance, operation, rollback, promotion, reconciliation, freshness, health, continuation, supersession, receipt, detached digest, proof, terminal, inventory, backup, client, and release-evidence writer. Final immutable names are never opened for writing. Complete canonical bytes go to a same-directory unnamed `O_TMPFILE`; exact UID, GID, final mode, size, and regular zero-link inode are established; the file is `fsync`ed; `linkat(AT_EMPTY_PATH)` creates the final name without clobber; and the parent is `fsync`ed. A kill before link leaves no named state. A kill after link leaves either no final after crash or one complete final that only the same authority can adopt after exact no-follow path, one-link, owner, mode, canonical, schema, HMAC or digest, identity, predecessor, and semantic source reauthentication. Adoption flushes the parent and changes no inode metadata or bytes. Links, wrong owner or mode, noncanonical paths, state beneath `/data`, duplicate IDs, malformed finals, invalid HMACs, and broken predecessor or progress chains fail closed.

Mutable pointer replacement uses the same staged-inode preparation only after the exact target bytes are durable in an immutable generation archive. The staged inode is linked create-new as `.<pointer>.replace.<authority-id>.<generation>.<payload-sha256>`, the parent is flushed, the predecessor pointer and target archive are reauthenticated under the owner locks, the one replacement is atomically renamed over the pointer, and the parent is flushed again. Recovery allows only absent replacement plus predecessor recreation, exact replacement plus predecessor adoption, exact target with no replacement completion, or exact target plus authenticated redundant-replacement cleanup. Cleanup verifies exact owner, mode, one-link inode, bytes, HMAC, authority, generation, predecessor, archive, and target digest before unlink and parent flush. A partial, differently named, duplicate, stale, conflicting, archive-less, or unauthenticated replacement blocks. Host and external release-state preflight reject unsupported unnamed files, final linking, atomic rename, file flush, or directory flush.

- `${STATE_DIR}/ops.lock` serializes top-level operations. `${STATE_DIR}/maintenance/gate.lock` separately serializes every gate and live-kernel observation or mutation. The only legal nested order is operations lock first, gate lock second. Reconciler renewal and emergency closure take only the gate lock and never wait for operations while holding it.
- `${STATE_DIR}/host-bootstrap.json` authenticates the one-time local receipt-key initialization. `${SECRETS_DIR}/receipt-auth.key` and `${SECRETS_DIR}/maintenance-testers.txt` remain mode `0600`, outside state receipts and every backup.
- `${STATE_DIR}/maintenance/boots/<boot-id>.json` and `${STATE_DIR}/maintenance/states/<logical-generation>.json` are immutable target archives. Byte-identical `boot.json` and `state.json` pointers advance through the common pointer protocol and bind boot ID, boot nonce, gate-service start, mandatory boot close, and the last completed current-boot mode plus logical and kernel generations. `intents/`, `open-authorizations/`, `terminals/`, `receipts/`, `proofs/`, and `joins/` hold atomically create-new transition records. Every transition intent has exactly one terminal outcome, `committed` or `abandoned-closed`. Health, join, status, and noncurrent transition evidence has at most a 600-second authorization and freshness-retention interval. Its historical bytes remain afterward but cannot use a retired lease. The exact current open authorization, state, terminal, and completed receipt share one live-until-close anchor. `${STATE_DIR}/health/` holds immutable current-container health receipts. Transaction health IDs are deterministic `<kind>-<transaction-id>-<health-sequence>` values, starting at zero and increasing for each replacement container. Health binds current boot, container start, release and lineage, state digests, gate generations, freshness digest or authenticated null, exact `freshness_retain_until_boottime_ns`, transaction, continuation, superseded-health digest, and predecessor supersession tip or authenticated nulls. The later supersession record cites new health and becomes the active pending or consumed tip. `/run/afterlight-gate/reconciler.json` is a root-owned runtime epoch and heartbeat, never durable authority.
- `${STATE_DIR}/maintenance/detections/<detection-id>.json` stores create-new `afterlight.maintenance.reconcile.detection.v1` records after startup emergency closure. The ID is the SHA-256 of canonical interrupted transition ID and intent digest, so detection-only recovery reuses one exact record and different bytes at that path block. It binds entry point, current and prior boot, interrupted transition and intent, authorization and terminal observations, live-rule and lease digests, emergency-close result, and issue times. `${STATE_DIR}/maintenance/reconcile-pending.json` is one complete `afterlight.maintenance.reconcile.pending.v1` bootstrap and active pointer. It binds reconciliation ID, detection digest or authenticated null, interrupted transition and intent digest, authorization digest or authenticated null, prior boot and generations, observed live rules and leases, entry point, pending generation, phase exactly `reconciling` or `terminalizing-cleanup`, progress generation and tip, transaction path, and HMAC. `${STATE_DIR}/maintenance/reconciliations/<reconciliation-id>/` retains exact `bootstrap.json`, byte-identical later pending generations at `pending-generations/<generation>.json`, append-only `afterlight.maintenance.reconcile.progress.v1` records at `progress/<generation>.json`, close evidence, and one `afterlight.maintenance.reconcile.terminal.v1` with outcome `committed-closed`. Progress binds sequence, predecessor, step, before and after observations, owned generations, and expected next step. The original transition terminal becomes durable before the reconciliation terminal. A final cleanup-intent progress record binds both terminals and expected pending bytes, pending advances to `terminalizing-cleanup`, then pending unlink and parent-directory `fsync` are the last writes. If pending survives, replay repeats only cleanup. If it is absent, the matching terminal and cleanup intent prove completion. Detection remains immutable and is resolved only by that terminal.
- `${STATE_DIR}/maintenance/channel-freshness/leases/<epoch>-<generation>.json` contains immutable, at-most-8192-byte `afterlight.maintenance.channel-freshness.v1` records. Each binds repository, active SHA and lineage, accepted-receipt digest, current remote `main`, immutable raw hashes, current Pages deployment and hashes, boot, reconciler epoch, authorization nonce, freshness epoch and generation, predecessor freshness or checkpoint digest, `issued_boottime_ns`, `expires_boottime_ns` exactly 15,000,000,000 greater, and informational UTC issue time. The shared freshness store is the sole writer, retention owner, and compactor, and it accepts only a caller that proves ownership of the canonical gate-lock descriptor. Issuance occurs no more than once per 5,000,000,000 `CLOCK_BOOTTIME` nanoseconds after remote success and complete local revalidation. `current.json` is an authenticated pointer to its exact immutable lease. Immutable `checkpoints/<checkpoint-generation>-deleting.json` and `-steady.json` files are target archives for the atomically replaced, at-most-262,144-byte HMAC `checkpoint.json` pointer. They bind previous checkpoint digest, cumulative ordered root, closed epoch range, next epoch, exact retained-reference manifest, and exact lease and predecessor-checkpoint victims; the steady archive additionally names the deleting archive as its sole post-replacement cleanup victim. Current authorization, state, terminal, rule, heartbeat, transition, health, join, status, and proof evidence binds a freshness digest and finite retain-until or live-until-close marker. Every live or unexpired reference remains a file. Expired historical evidence cannot authorize and may rely on the checkpoint root. Another boot, unavailable `CLOCK_BOOTTIME`, nonpositive remaining lifetime, expiry mismatch, missing retained generation, or checkpoint mismatch fails closed.
- `${STATE_DIR}/operations/pending.json` is one complete `afterlight.operation.pending.v1` bootstrap and pointer for at most one install, update, or recovery operation. It includes the full immutable intent payload, operation identity and kind, pending generation, phase `bootstrapped`, `mutating`, `health`, `terminalizing-success`, `terminalizing-failure`, or `terminalizing-abandonment`, transaction path, predecessor pending and terminal digests, progress tip, boot-continuation tip, health-supersession tip, promotion authority ID, closure, latest observation, failed-attempt chain root, and retarget tip or authenticated nulls, publication nonce, and HMAC. `${STATE_DIR}/operations/transactions/<operation-id>/` retains the exact first envelope as `bootstrap.json`, byte-identical later pointer archives in `pending-generations/`, append-only progress, `boot-continuations/`, `health-supersessions/`, full prestate and current inventories, and exactly one applicable success, abandonment, or failure record. `${STATE_DIR}/operations/blockers/` contains persistent unsafe-failure blockers; `${STATE_DIR}/operations/resolved/` contains immutable resolution tombstones.
- `${STATE_DIR}/operations/promotions/pending.json` is the one atomic `afterlight.update.promotion.pending.v1` authority with pending generation; phase `closing`, `closed-authorized`, `observed`, `failed-closed`, `successor-authorized`, or `transferring`; promotion ID and attempt sequence; target, original predecessor, and exact current remote SHAs; active-release and current-acceptance digests; boot and gate generations; transaction path; predecessor pending digest; and closure, observation, failure, and retarget tips when applicable. `${STATE_DIR}/operations/promotions/transactions/<promotion-id>/` retains `bootstrap.json`, byte-identical later pointer archives, maintenance close and proof, `closure.json`, immutable `attempts/<sequence>/authorized.json`, optional `attempts/<sequence>/observed.json`, exactly one `attempts/<sequence>/failed-closed.json` for each failed attempt, `retargets/<sequence>.json`, and exactly one final `consumed.json` after accepted update transfer. `failed-closed` is terminal for its candidate attempt and remains the sole stable authority. It preserves CI, Pages, deadline, ref, graph, and closed-lineage evidence and blocks Compose, every open, another promotion, and unrelated operations. Only the same pointer can transfer to an explicitly confirmed strict fast-forward successor from the recorded exact current remote object. The exact accepted update bootstrap binds the entire attempt chain before its consumed tombstone and pointer cleanup.
- `${STATE_DIR}/rollback/pending.json` is one complete `afterlight.rollback.pending.v1` bootstrap and pointer with pending generation and phase exactly `preparing`, `prepared`, or `activating`. It embeds full prepare intent, progress tip, prepare receipt digest or authenticated null, activation intent or authenticated null, boot-continuation tip or authenticated null, health-supersession tip or authenticated null, predecessor pending digest, and HMAC. `${STATE_DIR}/rollback/transactions/<transaction-id>/` retains exact `bootstrap.json`, byte-identical later pointer archives in `pending-generations/`, append-only prepare progress, `boot-continuations/`, `health-supersessions/`, prepare receipt and digest, full inventories, abandonment, archived activation intent, activation, activation-finalized, join, and production-open records. `${STATE_DIR}/rollback/consumed/` holds one-time tombstones that prevent prepare receipt reuse. Prepare progress authenticates offline marker intent, marker bytes and identity, both data-directory flushes, and marker removal.
- The first authoritative operation, rollback, promotion, or reconciliation publication is pending generation zero and uses common immutable publication before any protected mutation. Afterward the owner creates the transaction directory and publishes byte-identical `bootstrap.json` through the same engine; if killed first, only the matching pending envelope can reconstruct those exact embedded bytes. Every later pending generation increments by one, binds the prior pending digest, is first atomically create-new published in transaction `pending-generations/`, then replaces the top-level pointer through the deterministic common replacement protocol. Exactly one matching archived generation or semantic immutable record ahead of the pointer may be adopted after full revalidation. A later pointer without its archive, a skipped generation, multiple next archives, a malformed final, or an unexplained replacement blocks.
- `afterlight.transaction.boot-continuation.v1` records bind exact active transaction, prior continuation, old boot, container and health values or authenticated nulls, new boot and mandatory boot-close evidence, current full transaction state, stopped-service observation, and next phase. The immutable record uses common no-clobber publication, then pending advances through common pointer replacement to bind it and the predecessor pending digest before a new-boot service or container start. `afterlight.transaction.health-supersession.v1` records bind old and new immutable health receipts, both boot and container identities, continuation and progress tips, active release, state digests, gate generations, and predecessor supersession tip. The record uses common no-clobber publication, then pending advances through common pointer replacement to bind its digest before operation success, a not-yet-published rollback activation, or consumption. Exactly one valid next immutable record beyond either pending tip may be adopted by exact resume; a second, skipped, malformed, or mismatched record blocks. An already durable pre-consumption activation stays immutable and the consumed tombstone binds it plus the later chain tips. Same-boot container replacement still requires supersession. No terminal or consumed transaction can create either record.
- `${RELEASE_STATE_DIR}/v0.9.0-rc.1/` is outside every Git workflow and worktree and stores mode `0400`, external-operator-owned public-safe `E-acceptance.json`, `E-acceptance.json.sha256`, `E-client-release.json`, and `E-client-release.json.sha256`. These are not VPS HMAC records and cannot be committed into `E`. Each receipt is deterministic from reauthenticated sources and precedes its deterministic sibling digest at exactly `<receipt>.sha256`. Exact receipt-only retry re-fsyncs the parent and publishes only the missing digest through the common immutable protocol; exact pair retry re-fsyncs the parent without file mutation; every other partial or conflict blocks.

## Maintenance Access Gate

The gate has exactly three authenticated modes:

1. `closed` has no permissive lease elements. Permanent rules drop new and established traffic to Minecraft TCP `25565` and voice UDP `24454` from external, host, loopback, and peer-container paths, leave unpublished internal RCON control available, terminate existing game sessions, and require zero connected players when Minecraft is running.
2. `tester-only` has one nonce-bound lease generation implemented only by set elements with at most 15-second kernel timeouts and permits only canonical IPv4 or IPv6 CIDRs from mode `0600` `${SECRETS_DIR}/maintenance-testers.txt`. Receipts record only the allowlist SHA-256 and entry count. Every renewal requires a newly published 15-second current-channel freshness record for the same SHA.
3. `production-open` has one nonce-bound lease generation whose elements have the same timeout and removes only AFTERLIGHT's maintenance restriction. It never broadens the baseline host firewall or bypasses the Minecraft whitelist. Its kernel timeout can never extend past the current freshness expiry.

`server/scripts/maintenance.sh` is the sole public transition authority. Every public transition first takes `${STATE_DIR}/ops.lock`, then the short root-owned `${STATE_DIR}/maintenance/gate.lock` when local gate work begins. All remote accepted-mode and Pages checks finish before the gate lock, then every local receipt, predecessor, generation, boot, service, promotion authority, reconciliation, blocker, authorization, freshness checkpoint, and live-rule fact is revalidated while it is held. `close --reason TOKEN` owns new logical and kernel generations, atomically removes every permissive element, asks the sole freshness store to invalidate only the matching current pointer and flush its parent, terminates sessions, proves zero players, re-reads the live table, and proves zero lease elements for the owned generation before publishing closed. A stale nonmatching pointer blocks rather than being deleted. `status --require MODE --receipt-out RECEIPT` holds the gate lock while authenticating durable state, current freshness and checkpoint when open, kernel lease, reconciler heartbeat, live rules, connections, service, players, and unresolved state. Tester opening requires exact accepted release and current health receipts. Production opening requires those plus a general join receipt for every eligible lineage and exact finalized transaction fields for rollback. Every immutable output uses common no-clobber publication.

Every ordinary transition atomically create-new publishes authenticated intent through `record_io.py` before its first gate or kernel mutation and exactly one terminal before another transition may begin. Normal completion publishes `committed` through the same engine. A killed transition without terminal blocks every later transition and ordinary Compose. Reconciliation is itself a transaction. Its first durable authority is an atomic self-contained pending envelope that names the exact interrupted intent and all observed predecessor, authorization, boot, generation, and live-rule facts. Atomically published progress generations surround authorization invalidation, lease removal or expiry, new generation ownership, closed state, receipt, proof, original `abandoned-closed` terminal, and reconciliation terminal. If one complete valid progress or archived pending generation is ahead of the active pointer, replay may adopt only that exact next generation; only generation zero can reconstruct missing `bootstrap.json` from identical pending bytes. After both terminals, one final cleanup-intent record is atomically published, the next pending generation is atomically archived, pending advances through the common pointer protocol to `terminalizing-cleanup`, then unlink and parent `fsync` are the last writes. No post-unlink record exists. A surviving pointer repeats only cleanup; absence plus the matching terminal and cleanup intent is complete. A kill after the original terminal therefore resumes reconciliation cleanup rather than rejecting an already terminalized transition.

`maintenance.sh reconcile --intent INTENT --confirm TRANSITION_ID` and internal startup `--auto-detected DETECTION --lock-held` are the only entry points and run the same engine. Manual invocation starts or resumes it when the services are disabled or have stopped on a trust failure, derives the deterministic detection path, and must bind an existing matching startup detection rather than substitute null. Boot-gate and reconciler startup always force live rules closed first, create or authenticate the deterministic detection ID derived from transition ID and intent digest, then automatically start or resume it before Compose. A kill after detection but before pending publication can only reuse those exact bytes. A completed repeated invocation verifies the same reconciliation terminal and returns without mutation. Neither entry point continues an interrupted open. No new transition is legal until the interrupted transition and reconciliation terminals are durable and `reconcile-pending.json` is absent.

Opening atomically publishes transition intent plus one-time authorization bound to current boot, reconciler process epoch, expected predecessor, expected kernel generation, health, join when required, release, lineage, and blocker-free state. After complete local revalidation it samples `CLOCK_BOOTTIME` and calls the sole freshness store with the inherited gate-lock descriptor. The store first completes any checkpoint deletion, compacts before a soft limit, enforces the global five-second issuance slot, atomically publishes the first immutable current-channel freshness record with expiry exactly 15,000,000,000 nanoseconds later, and replaces the freshness pointer through the common pointer protocol. Only then can opening install one lease generation composed solely of set elements. Immediately before atomic replacement it recomputes positive remaining lifetime and rounds the kernel timeout down to supported resolution. While still holding the gate lock it proves nonce, process epoch, membership, remaining timeout, freshness digest, kernel generation, and live-rule digest, atomically publishes completed state, receipt, and `committed` terminal, then waits for a matching reconciler heartbeat. A kill after lease installation has prior durable authorization and freshness but no unbounded permission: without matching completed state, terminal, and same-process heartbeat, every element expires within 15 seconds and cannot renew.

Every `gate_reconciler.py` startup first takes the operations lock then gate lock, forces live rules closed, resolves or blocks any common pointer replacement and freshness checkpoint deletion, creates or authenticates unresolved detection, runs or resumes the shared reconciliation transaction, atomically publishes a startup-close intent, creates a new random runtime epoch and kernel generation, publishes a `committed` authenticated close, and proves zero permissive elements. It then releases the operations lock. Each loop checks at least every 5 seconds. In an open mode it first takes the gate lock to snapshot boot, process epoch, authorization, completed state and terminal, logical and kernel generations, active release and lineage, health and join digests, current freshness tip and checkpoint, blockers, rule digest, and lease identity, then releases the lock. It runs `release_gate.py current-channel` with a four-second overall deadline and no lock held. It then retakes only the gate lock and completely revalidates the snapshot. A matching successful probe samples `CLOCK_BOOTTIME` and asks the freshness store to recover, compact if needed, and publish the next rate-limited record and pointer. It recomputes positive remaining lifetime, rounds the kernel timeout down, and atomically replaces the lease before kernel proof and heartbeat. A failed probe, timeout, changed `main`, changed Pages deployment or bytes, malformed response, invalid clock, expired candidate freshness, checkpoint mismatch, retention conflict, compaction failure, or prospective bound overflow creates a fail-closed intent for the still-matching generation when possible, removes all leases immediately, invalidates matching freshness, owns new generations, proves closed, terminalizes if uninterrupted, and stops Compose. If intent publication or another durable close write fails, it still removes every lease under the gate lock as an emergency safety action, stops Compose, records no invented terminal, and leaves startup detection plus the same reconciliation protocol to classify durable state. A changed local snapshot discards the remote result. It never waits for the operations lock while holding the gate lock. Therefore close or drift cannot be undone by an old authorization or stale probe.

Freshness epoch compaction is a closed finite transaction inside `channel_freshness.py`, not an independent daemon. While the caller owns the gate lock, it securely scans and authenticates current pointer, open authorization, current state and terminal, live kernel proof, heartbeat, transition receipts, unexpired health, join, status, and proof records. Every referenced distinct generation is retained, including a live-until-close anchor and every finite `freshness_retain_until_boottime_ns` that has not expired. It first atomically publishes the next bounded deleting archive with a domain-separated cumulative ordered digest of the closing epoch, prior checkpoint, exact retained-reference record and generation manifest, exact lease and predecessor-checkpoint victim paths and digests, and next epoch. The checkpoint pointer then advances to those bytes through the common protocol. Only then are exact victims unlinked and both the leases and checkpoints directories flushed. It next atomically publishes the matching steady archive, whose cleanup manifest names the deleting archive, and advances the pointer to steady. Only then is the deleting archive unlinked and its parent flushed. No freshness issue occurs between those writes. The first next-epoch lease binds the steady checkpoint digest and retained predecessor. A checkpoint never stands in for a current 15-second lease and never extends a kernel timeout.

Compaction starts before either 128 lease files or 1 MiB and finishes below both. Canonical lease records are at most 8192 bytes. At most the predecessor steady archive and one next deleting or steady archive coexist before prescribed cleanup. Prepublication accounting includes both pointers, those at-most-two checkpoint archives, and one deterministic linked replacement, and proves accepted state never exceeds 160 lease files, 168 total regular files, or 2 MiB in the freshness tree. If all retained generations cannot fit, the store creates no new generation, removes live leases, stops Compose, and preserves every reference. Recovery first closes. A durable `deleting` checkpoint allows only authentication and idempotent unlink of listed surviving lease and predecessor-checkpoint victims, both directory flushes, deterministic steady-archive publication and pointer replacement, and deleting-archive cleanup. Already absent listed victims are covered by that checkpoint. A `steady` checkpoint plus its exact deleting archive permits only that authenticated cleanup. Any other second archive, missing target archive, missing retained generation, unlisted missing or extra file, bad cumulative root, changed referring record, duplicate replacement, or bound violation blocks. This preserves fail-closed renewal while bounding years of five-second operation.

In closed mode, only the exact authenticated install, update, recovery, or pre-consumption rollback activation owner whose operations lock remains held may keep Minecraft running without a lease for its bound setup, staging, protected-backup, activation, or health phase. On a new boot it must first atomically publish its matching continuation and advance its pending pointer. A promotion authority, including stable `failed-closed`, permits no open mode and no unrelated operation. No exception permits an unjournaled restart. Every other failure removes all lease elements, proves closed, and stops Compose within one interval. `afterlight-gate-reconciler.service` uses `Type=notify`, `NotifyAccess=main`, `Restart=always`, and `WatchdogSec=10s`; it accepts `READY=1` only after startup closure and `WATCHDOG=1` only after a complete successful loop, and it is required by `afterlight-compose.service`. Every restart creates a new terminalized closed epoch rather than replaying prior open authority.

Every boot ignores persisted tester-only or production-open authority. `afterlight-maintenance-gate.service` takes operations then gate lock, force-removes every lease as an emergency safety action, resolves or blocks deterministic record replacements and freshness checkpoint deletion, records unresolved detection, and runs or resumes the same reconciliation transaction as the manual command. Only after both reconciliation terminals and pending cleanup may it atomically publish a boot-close intent, a new boot-closed receipt, and `committed` terminal, then prove zero permissive elements. `operation_state.py boot-check` requires complete host bootstrap and rejects every unresolved, partial, inconsistent, or unsafe reconciliation, promotion authority, operation, rollback, continuation, supersession, freshness checkpoint, or offline-marker state. Only blocker-free state permits ordinary Minecraft startup behind closed ingress. An exact active transaction may instead be resumed manually while ordinary startup remains blocked. Reopening requires accepted release revalidation, health from the new container start, tester-only access, an exact current-release client receipt and join for that boot and container, and a separate production-open command.

`maintenance.sh attest-join` is general to install, update, reboot, protected-maintenance return, and rollback. It requires tester-only state, fresh same-container health created after tester-only opening for those exact logical and kernel gate generations and a valid retained freshness generation, exact released-client artifact receipt, active SHA and lineage, explicit operator confirmation, an atomically create-new receipt output beneath `${STATE_DIR}/maintenance/joins/`, and rollback transaction fields when applicable. Health and join receipts expire after 600 seconds for use in a new transition and carry their exact freshness retain-until time. Production open always requires fresh accepted-release revalidation plus matching unexpired tester-generation health and join receipts bound to both gate generations and their retained freshness lineage at authorization. Once production-open is durably published, later health or join expiry alone does not close it, but every kernel renewal requires a new current-channel freshness generation. Any opening after close, restart, or reboot requires new health and join receipts. Recovery lineage cannot open directly.

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

Tests place deterministic barriers during the unlocked remote refresh, after renewal revalidates old open state, and after close owns its new generation. Every legal lock schedule must end with the close-owned generation and zero permissive elements, and no stale probe may publish. SIGKILL before every maintenance terminal requires exact `abandoned-closed` reconciliation. SIGKILL during reconciliation covers pending link and parent flush, each progress generation, original terminal, reconciliation terminal, pointer unlink, and final directory flush; startup and manual entry must converge on one ID and byte lineage. SIGKILL after a durable ordinary `committed` terminal with no reconciliation pending requires status verification and makes a new reconciliation reject it as already resolved. Freshness tests kill after deleting-archive publication, each pointer replacement boundary, each lease or predecessor-checkpoint victim unlink, both directory flushes, steady-archive publication, deleting-archive cleanup, freshness final link, current-pointer rename, rule publication, and final parent flush. Event-driven fake time covers at least ten years of five-second slots, repeated epochs, 600-second expiry edges, and a live anchor retained across compactions. A real filesystem loop covers at least 1,000 compactions. Every observation proves exact live and unexpired references, cumulative roots, unique recovery, current 15-second freshness, at most two checkpoint archives, and all hard bounds. An injected uncompactable reference set must close and stop Compose without deleting a reference or renewing.

## Lock Model

Every top-level mutating command opens and acquires `${STATE_DIR}/ops.lock` once, keeps that one Linux file descriptor open for the full operation, and exports its number as `AFTERLIGHT_OPS_LOCK_FD`. A nested maintenance command receives the inherited open descriptor and uses an internal `--lock-held` contract. It validates that the descriptor is numeric, open, and points through Linux `/proc/self/fd` to the canonical operations lock, then requires nonblocking `flock -n` on that same descriptor to succeed. The inherited locked open-file description succeeds without reacquisition; a separately opened descriptor fails while the parent lock is held. Any command that also needs `${STATE_DIR}/maintenance/gate.lock` takes it only after the operations lock and releases it before releasing operations. No path may invert this order.

Direct `backup.sh` calls acquire the operations lock normally. Backup calls nested beneath update, rollback, or Chunky reuse the parent's descriptor. Tests cover update-to-backup, rollback-to-backup, and pregen-to-backup execution, assert that the same descriptor remains held, and fail forged or separately opened descriptors. The normal online image branch adds `${BACKUP_DIR}/.mc-backup-lock` as a separate archive-serialization lock with the existing fixed acquisition order. The offline paused branch has no image lock and remains serialized by the inherited host operations descriptor. No nested path may reacquire the operations lock and self-deadlock.

Maintenance transitions, durable maintenance reconciliation, open authorization, join attestation, promotion authority and retarget, install, update, recovery, rollback bootstrap and progress, resume, abandonment, activation, boot continuation, health supersession, transaction consumption, finalize-only reconciliation, and production opening all use that same operations lock. Gate validation, freshness store calls, and publication additionally use the gate lock. Reconciler renewal and emergency fail-closed mutation are deliberate exceptions: renewal takes one gate-locked snapshot, performs remote work with no lock, retakes only the gate lock, and never waits for operations. A matching refresh then holds the gate lock continuously across complete local revalidation, freshness recovery or compaction, new-generation publication, rule replacement, proof, and heartbeat. Failure holds it across fail-closed intent publication and immediate lease removal. An exact authenticated operation or pre-consumption activating rollback transaction may keep Minecraft running behind closed ingress only while its operations lock remains held. Status, health, continuation, supersession, and transaction proofs are therefore ordered with the state and kernel generation they authenticate rather than being racy observations.

## Install, Update, and Recovery Transactions

Install, update, and recovery share `afterlight.operation.*.v1` records and one atomic bootstrap protocol. Each start performs read-only authentication first. Its first authoritative state mutation gives complete canonical `afterlight.operation.pending.v1` bytes to `record_io.py`, which prepares owner, mode, bytes, and file durability on an unnamed same-directory inode, links create-new to `${STATE_DIR}/operations/pending.json`, and parent-flushes that link. Only then may it create the transaction directory, candidate, protected backup, RCON secret, service state, `/data` object, managed ledger, provenance, journal, quarantine object, active-release record, container, or health receipt. A kill before link leaves no named authority and no protected mutation. A kill before the parent flush yields either no envelope and no mutation or one complete adoptable envelope. Unsupported filesystem semantics fail host preflight.

The self-contained pending bootstrap records operation kind and ID, phase, exact command, tool version, accepted release and bundle evidence, initial boot plus logical and kernel gate generations, service state, complete data inventory or authenticated empty observation, root identity, ledger, provenance, journal, quarantine, active release and lineage, planned paths, expected mutations, predecessor terminal, progress tip, boot-continuation tip, health-supersession tip, complete promotion attempt and retarget chain or authenticated nulls, transaction path, publication nonce, and HMAC. Its exact first bytes are retained as transaction `bootstrap.json`; if killed before that copy, resume reconstructs only identical embedded bytes through common no-clobber publication. Every append-only authenticated progress record, inventory, receipt, proof, continuation, supersession, and terminal uses that engine before and after its mutation boundary and binds expected and observed device, inode, inventory, digest, service, gate, container, continuation, supersession, and receipt state. An unexplained transaction record, progress gap, extra envelope, wrong terminal, malformed final, direct-final write, or mismatched digest blocks ordinary Compose instead of being cleaned heuristically.

Exact resume holds the operations lock and revalidates every input, receipt, progress link, path identity, full inventory, state digest, service, gate, and container before repeating only an idempotent check or provably incomplete step. If the current boot differs, it first atomically publishes `afterlight.transaction.boot-continuation.v1`, binding the bootstrap, previous continuation, old boot, container and health values or authenticated nulls, new boot and mandatory boot-close evidence, complete transaction state, stopped service, and exact next phase. Pending then advances through the common pointer protocol to bind its digest and predecessor pending generation before any transaction-owned service or container start. Exactly one matching complete record ahead of pending may be semantically adopted after a kill. Same-boot container replacement performs the same state validation but needs no boot continuation.

After resumed health succeeds, every old health receipt remains immutable. If the prior health names another boot or container start, the transaction atomically publishes fresh health binding its predecessor health and predecessor supersession tip, then atomically publishes `afterlight.transaction.health-supersession.v1` binding old and new receipts, both boot and container identities, continuation and progress tips, release, lineage, state digests, gate generations, and predecessor supersession. Pending advances through the common pointer protocol to bind the new supersession tip before success. Exactly one matching complete supersession ahead of pending may be adopted after a kill; competing, skipped, malformed, or mismatched records block. Only the exact active pending envelope and operations-lock owner can advance this chain. Authenticated abandonment is available only while the original prestate can be restored exactly with ingress closed and services stopped. Install and recovery abandonment ends before the first Minecraft world start and verifies the original empty prestate. Update abandonment ends before first `/data` publication and verifies the full original inventory and state. Later abandonment rejects.

Every operation terminal uses one ordering. After all terminal preconditions, the next immutable archived pending generation embeds complete canonical terminal bytes, target path, digest, and exact blocker or rollback-request bytes when applicable. Pending advances through the common pointer protocol to `terminalizing-success`, `terminalizing-failure`, or `terminalizing-abandonment`, and its parent flush is the irrevocable terminal decision. The exact embedded outputs are then atomically create-new published through `record_io.py`. Only then is the matching pending envelope unlinked and its parent flushed. Success binds final inventory, ledger, provenance, completed journal, quarantine disposition, active release, service, closed gate, latest health, and every bootstrap, progress, continuation, and supersession digest. Because health and supersession were current before the decision, a kill after that pointer flush resumes only terminal materialization or cleanup, even on another boot, without a continuation or service start. A kill before it remains an active transaction and must use cross-boot continuation before another start or success decision.

`operation_state.py boot-check` runs before ordinary Compose and scans complete maintenance transition and reconciliation, freshness checkpoint, promotion authority, operation, rollback, continuation, supersession, deterministic replacement, and `.paused` marker state. An unresolved operation, stable failed-closed promotion authority, offline marker, or unsafe failure stops Minecraft and keeps ingress closed. The only service-start exception is the exact operation or pre-consumption activating rollback owner holding the operations lock while its authenticated phase permits setup or health behind closed ingress. Update health failure atomically publishes `failed.json`, a persistent operation blocker, and the rollback request, then removes the matching pending envelope. Rollback prepare must bind those exact failure records and their continuation and supersession tips. Only successful rollback activation finalization may atomically publish the resolution tombstone and remove the blocker. A kill during failure or blocker publication can only adopt or finish those same records.

A normal post-launch update must close before its target is promoted to `main`. `update.sh authorize-promotion` atomically publishes `afterlight.update.promotion.pending.v1` in phase `closing`, then closes maintenance and records the exact close intent, `committed` terminal, closed proof, zero leases, and zero players. It advances the one authority through the common pointer protocol to `closed-authorized`, binding target, original predecessor `main`, active release, boot and reconciler epochs, logical and kernel generations, issue time, a fixed two-hour acceptance-observation deadline, and closed-state predecessor digest. The authority blocks every open transition, unrelated operation, and second promotion. A killed authorization resumes only this authority's missing close and proof steps. The operator performs the normal fast-forward Git push manually. `observe-promotion` must see exact target at remote `main` and prove the original close remains in the current closed predecessor chain with no intervening tester or production transition before it atomically publishes `observed.json` and advances the pointer. Update start atomically publishes its operation envelope binding closure, latest observation, and the complete attempt chain while the authority still exists, then atomically publishes the promotion consumed tombstone, removes only that authority, and flushes its parent. A kill during transfer leaves both blockers for exact update resume. Cancellation is authenticated and legal only before any ref movement while remote `main` remains the original predecessor.

If the target cannot become accepted, `update.sh fail-promotion` is the only legal classifier. It accepts only `closed-authorized`, `successor-authorized`, or `observed`; holds the operations lock; proves uninterrupted closed lineage; takes a gate-locked snapshot; queries remote ref, exact workflow attempt and job, and Pages outside the gate lock with bounded deadlines; then retakes the gate lock and revalidates everything. `failed-ci` requires an exact completed non-success target `main` run or job. `failed-pages` requires a failed deployment or absence of matching deployment and parity through the bound deadline. `unexpected-ref` requires current remote `main` to differ from the target and records exact compare facts. The immutable `attempts/<sequence>/failed-closed.json` binds reason, target, base and actual refs, CI and Pages observations or authenticated nulls, deadline, graph facts, close and proof, boot, gate and reconciler epochs, zero leases and players, prior attempt and retarget tips, and exact next commands. Only after common no-clobber publication does the pointer advance to `failed-closed`. A valid record one generation ahead can be adopted. This state is terminal for that candidate, keeps Compose stopped, remains the one authority, and permits no opening or unrelated operation.

`update.sh retarget-promotion` transfers that same authority only from `failed-closed`. Its `--from` must equal both the failure record's actual remote object and unchanged current remote `main`. It authenticates the proposed successor from an immutable remote ref and exact commit-graph evidence proves the successor is a strict fast-forward descendant of `--from`. Equality, ancestry reversal, unknown commits, merge-base ambiguity, ref movement during validation, a second pointer, a second authority, and force semantics reject. After a gate-locked proof of uninterrupted closure, the command atomically publishes `retargets/<next-sequence>.json` and the next `authorized.json`, then advances the same pointer to `successor-authorized` with incremented attempt and complete failure chain before the operator may push. All failed target evidence remains immutable. The successor can fail through the same state machine or transfer into update after exact observation and acceptance. If no successor is authorized, `failed-closed` is a stable boot-blocking terminal, not an unresolved write window.

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

If CI, Pages, or the ref observation fails after `main` moved, terminalize that target while remaining closed:

```bash
server/scripts/update.sh fail-promotion \
  --promotion "${promotion_id}" \
  --pending "${STATE_DIR}/operations/promotions/pending.json" \
  --reason "${failed_ci_failed_pages_or_unexpected_ref}" \
  --confirm "${release_sha}"
```

The failed-closed authority may remain as the safe terminal. To continue, first authorize one strict fast-forward successor while remote `main` still equals the failure record's exact current object, then perform only the normal fast-forward push and observe it:

```bash
server/scripts/update.sh retarget-promotion \
  --promotion "${promotion_id}" \
  --pending "${STATE_DIR}/operations/promotions/pending.json" \
  --successor "${successor_sha}" \
  --from "${failed_current_main}" \
  --confirm "${successor_sha}"

git push origin "${successor_sha}:refs/heads/main"

server/scripts/update.sh observe-promotion \
  --promotion "${promotion_id}" \
  --pending "${STATE_DIR}/operations/promotions/pending.json" \
  --confirm "${successor_sha}"
```

If authorization is killed, resume only its exact authority:

```bash
server/scripts/update.sh authorize-promotion \
  --resume "${promotion_id}" \
  --pending "${STATE_DIR}/operations/promotions/pending.json" \
  --confirm "${promotion_id}"
```

If the operator abandons before any ref movement and remote `main` still equals `${current_main}`, cancel without reopening:

```bash
server/scripts/update.sh cancel-promotion \
  --promotion "${promotion_id}" \
  --pending "${STATE_DIR}/operations/promotions/pending.json" \
  --confirm "${promotion_id}"
```

Initial empty-host publication is outside this post-launch authority because its preconditions reject any installed data or active release. Rollback after update failure is already bound to the authenticated failure blocker and closed proof, so it follows the rollback contract instead of creating a normal update authority. A deliberate rollback without that blocker is not a normal update: current-channel renewal closes any open host as soon as `main` moves, and prepare independently closes and proves zero leases and players before protected mutation. Neither exception can satisfy normal `update.sh start`.

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

The implementation tests SIGKILL before and after every common unnamed create, partial write class, ownership and mode assignment, file flush, immutable final link, replacement link, replacement-parent flush, pointer rename, and final parent flush for bootstrap, progress, continuation, supersession, health, inventory, receipt, proof, terminal, blocker, and pointer records. It also covers candidate, backup, stop, secret, setup, data rename or managed publication, ledger, provenance, journal, quarantine, active release, container start, stale-health observation, pointer unlink, and every directory flush, then reboots after boot-bound health and before success. Promotion tests are finite: authority bootstrap, close, closure, target observation, failed CI, failed Pages, deadline-stale Pages, unexpected ref, failure terminal publication and pointer advance, stable failed-closed reboot, strict fast-forward retarget publication and pointer advance, successor observation, transfer, consumption, pre-movement cancellation, and every common publication boundary. One stable no-successor case and one accepted successor case run for each failure class. Every resulting state has exactly one authority and one authenticated next action, with no force-push, reopening, stale-health acceptance, evidence replacement, or mixed-data ordinary restart path.

## Update and Rollback Model

After its authenticated promotion authority has closed the host, preserved any failed attempts, and observed the exact accepted target at remote `main`, an update authenticates remaining staging inputs read-only and atomically transfers that one authority and complete attempt chain into its operation bootstrap before candidate creation. It takes a protected backup that closes and proves the gate, and activates only validated pack-managed files. Packwiz updates pack-managed paths in `/data`; the prohibition is against automatic world restore, world deletion, or rollback. A healthy update marks `lineage=update`, starts the new container closed, atomically publishes fresh health and success, and clears its exact pending envelope. If killed after health and rebooted before success, only that active update may atomically publish a boot continuation, advance pending, start the same release closed, create new health, and supersede the stale receipt before success. The operator then opens tester-only, joins with the exact released client, records the general join receipt, and separately opens production.

An update health failure stops Minecraft, leaves the gate closed, exits with code `6`, preserves logs, candidate files, Packwiz provenance, backup, ledger, journal, quarantine state, progress, continuation and supersession records, and receipts, and writes one authenticated failure terminal, persistent operation blocker, and rollback-request receipt in durable order. All three bind the same bootstrap, promotion closure and observation, progress, continuation, and supersession tips, latest health lineage, failed data inventory, active release, backup, and state digests. It prints the fixed runbook path and exact failed bundle values. It cannot print a valid prepare command until the operator has created rollback SHA `R` and an accepted `R` receipt, and it never restores world data automatically. A kill during failure publication remains blocked and may only finish those exact records.

Rollback remains a truthful two-phase operation, but the operator-owned Git promotion now precedes data-changing prepare so prepare can bind the exact rollback release:

1. From authenticated bundle snapshots for historical SHA `H`, the operator creates and reviews normal rollback commit `R`, pushes exact `R` through `dev`, promotes it unchanged to `main`, waits for exact-SHA CI and Pages parity, and runs accepted mode externally. Maintenance tooling never commits, reverts, pushes, mutates branches or tags, or calls a GitHub write API.
2. `rollback.sh prepare` performs read-only authentication of named bundle, `H`, `R`, canonical accepted `R` receipt, raw-`R` equality with historical snapshots, current accepted `main`, Pages, current data identity, ledger, provenance, journal, quarantine, services, logical and kernel gate generations, and planned paths. When entered from update failure, it also requires the exact paired rollback request and operation blocker and authenticates their bootstrap, progress, continuation, supersession, failed inventory, active release, and backup digests. Before any gate, service, backup, marker, rename, extraction, activation, or data mutation, it atomically publishes complete schema `afterlight.rollback.pending.v1` in phase `preparing`. The embedded bootstrap binds transaction ID, every input digest, root device and inode, active release and lineage, initial boot and current state observations, operation blocker when present, planned paths and marker nonce, tool version, predecessor, progress tip, and authenticated null activation, continuation, and supersession fields. No separate prepare-intent or detached-digest window exists.
3. Under the inherited operations lock, prepare closes and proves the gate, stops Minecraft and scheduled backup idempotently, and proves both stopped. It publishes marker-intent progress, then invokes only `backup.sh --class protected --reason rollback-current --offline-parent TRANSACTION_ID --pending ROLLBACK_PENDING --marker-intent PROGRESS --lock-held`. The child authenticates the parent and exact HMAC marker identity before using the pinned image's paused branch, with no RCON and no `.mc-backup-lock` assertion.
4. Prepare writes authenticated append-only progress before and after every gate close and proof, service stop, marker intent, marker create, marker file and data-directory flush, offline backup, marker unlink and second directory flush, inventory, candidate, quarantine rename, publication, raw-`R` overlay, journal, ledger, provenance, and final inventory step. Root device, inode, path, digest, boot-continuation, pending generation, marker bytes, and marker identity checkpoints distinguish not-started, completed, and crash-between-syscall states. Prepare cannot mark the release or terminalize while its marker remains.
5. Completed prepare removes and flushes its exact marker, marks `lineage=rollback`, and atomically publishes schema `afterlight.rollback.prepare.v1` plus its detached digest through `record_io.py`, binding bootstrap and progress-chain tips; bundle and archive metadata; `H`; `R`; release evidence; raw and historical manifests; failed-current offline bundle; pre-restore and prepared inventories; ledger; active release; candidate and installer provenance; completed journal; quarantine; stopped services; closed gate; marker creation and removal evidence; and predecessor digests. It then atomically publishes the complete phase-`prepared` pending-generation archive before replacing `pending.json` with those identical bytes through the common pointer protocol. The generation carries immutable bootstrap, prepare receipt, progress tip, and predecessor pending digest. A receipt with phase still `preparing` or exactly that archive one generation ahead remains blocked but has one exact repair.
6. Exact transaction files are `bootstrap.json`, `prepare-progress/<sequence>.json`, `boot-continuations/<sequence>.json`, `health-supersessions/<sequence>.json`, `prepare.json`, its digest, all inventories, `prepare-abandoned.json`, archived activation intent, `activation.json`, `activation-finalized.json`, `join.json`, and `production-open.json`. The consumed tombstone remains under `${STATE_DIR}/rollback/consumed/`. Every stale health receipt and every continuation or supersession predecessor remains immutable.
7. `prepare --resume` accepts only the original pending bootstrap and transaction. It revalidates immutable inputs and progress, reconciles exact root and marker identities including marker-without-post-progress, unlink-without-post-progress, and receipt-before-phase-replacement, and repeats only idempotent or incomplete safe steps. `rollback.sh abandon` is idempotent for the exact pre-activation transaction, authenticates and removes only its own marker, restores and verifies pre-prepare data, ledger, provenance, journal, quarantine, and root identity from authenticated progress, writes abandonment, removes only the matching pending envelope, and clears only the rollback prepare blocker after directory-flushed proof. It never clears a failed-update operation blocker. Failure leaves ingress closed, services stopped, backup modes blocked, and Compose blocked. A valid abandonment receipt is terminal and makes prepare resume, activate, finalize-only, and receipt reuse fail.
8. Any rollback pending envelope blocks ordinary Compose and systemd startup until exact abandonment is fully reconciled or activation is finalized with no pointer. Activate authenticates phase `prepared` and every bound input under the operations lock. Before start it atomically publishes the complete phase-`activating` pending-generation archive, then replaces `pending.json` with those identical bytes through the common pointer protocol. It becomes the sole exception allowed to start Minecraft behind closed ingress while its lock remains held. It writes deterministic sequence-zero closed health for `R`. While still closed, it publishes `activation.json` once, binding the current continuation and supersession tips. Publication then continues with consumed tombstone, activation-finalized receipt, pending unlink, and parent-directory flush. If prepare bound an update blocker, the next order is operation resolution tombstone, blocker unlink, and parent-directory flush. Only after no unresolved rollback or operation state remains may the command create a timeout-bound tester lease using the latest current-container closed health and then write tester-generation health.
9. Ordinary activate and resume reject consumed state. Before consumption, resume authenticates phase `activating` and continues only missing idempotent steps. On another boot it atomically publishes the exact boot continuation including the next deterministic health path, advances pending through the common pointer protocol to bind it, then starts. An existing current-container health output may be adopted only when its complete final exactly authenticates. Stale health is retained; `--superseding-closed-health-out` must name the new sequence path, new health and its supersession use common immutable publication, and pending advances through the common pointer protocol to bind the new tip before activation or consumption. If `activation.json` already exists, it remains immutable. The consumed tombstone binds its digest plus the latest continuation, supersession, and fresh-health digests. `--finalize-only` is the sole consumed-state reconciliation path for an exact matching pending pointer or bound operation blocker plus activation receipt, latest chain tips, and consumed tombstone. It revalidates exact `R` data and transaction state, then may atomically publish a missing finalized receipt, remove that exact pointer, atomically publish a missing operation resolution tombstone, and remove only the exact bound blocker in prescribed order. It cannot start, restart, continue a boot, supersede health, change gate mode, consume again, or alter transaction inputs, and the live service may be running closed or stopped. Finalized plus no pending or blocker is already complete and does not use finalize-only. If tester health is absent after any consumed state, the operator closes and proves the gate, starts the normal Compose unit behind closed ingress, creates new closed health, and performs explicit tester-only access plus tester health. A mismatched set fails closed.
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

Only after those remote events complete does an external operator process run `release_gate.py accept` for exact `E`. The caller is outside every workflow and worktree, and accepted mode still rejects a selected run equal to `GITHUB_RUN_ID`. On every invocation it reauthenticates exact remote `main`, completed workflow and job, Pages deployment and parity, and clean installs, then derives deterministic receipt and digest-file bytes. Neither final exists means atomically publish `E-acceptance.json` and then its digest through `record_io.py`. Exact valid receipt-only means preserve its inode, mode, mtime, and bytes, re-fsync the canonical parent, and publish only the missing digest. Exact pair means re-fsync the canonical parent and succeed without file mutation. Digest-only, malformed, noncanonical, conflicting, linked, wrongly owned, stale, in-worktree, or replacement-temporary state blocks. The operator reparses the receipt, confirms its subject is `E`, and recomputes its detached digest before client receipt creation.

`tools/client_release_receipt.py rebind-evidence` next authenticates both preserved archives and `S` client receipts through read-only file descriptors. It verifies both detached digests, equal archive lengths, digests, and bytes, canonical `S` and `E` acceptance, `E` as the direct child of `S`, exact evidence-document blob hashes, the two-document diff allowlist, the `S` receipt and archive facts committed in those documents, equal raw and Pages `pack.toml` and `index.toml` hashes at both subjects, and equal installer and builder facts. It never rebuilds, copies, normalizes, renames, chmods, or writes either archive, and rejects inode, mode, size, mtime, or content change during authentication. Deterministic `E-client-release.json` and digest-file bytes use schema `afterlight.client.release.v1`, subject `E`, source subject `S`, and the already gauntleted archive identity, with no local time, random, inode, or worktree field. The same pair state machine applies. Exact receipt-only recovery repeats every read-only authentication, re-fsyncs the canonical parent, and creates only its deterministic missing digest without changing the receipt or archives; exact pair recovery re-fsyncs that parent and succeeds without file mutation; every other partial or conflict blocks. An `S`-subject client receipt is no longer sufficient for a release join after `E` becomes current `main`.

`tools/finalize_rc.py publish` is the sole final publication interface and is implemented before subject freeze. It requires both complete `E` pairs, reauthenticates them, and rejects workflow execution, receipts inside a worktree, receipt-only or digest-only state, noncanonical or mismatched bytes, wrong acceptance or client subject, wrong client source, evidence-document blob mismatch, predecessor receipt or archive facts that differ from committed `E` gauntlet evidence, wrong parent, disallowed `S..E` paths, moved `main`, conflicting tags or releases, and remote evidence mismatch. Only after validation does it create and push the annotated tag, then create the GitHub prerelease. A retry after tag-push interruption may verify and reuse only the identical tag object and message to create a missing release; it can never move, delete, or recreate the tag.

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
9. Run accepted mode externally for `E` through its idempotent pair protocol, durably preserve and verify its canonical receipt plus digest, then create and verify the exact `E` client pair from both unchanged `S` gauntlet artifacts through the same protocol. A valid receipt-only crash state is completed only by exact source reauthentication and missing-digest publication, never receipt replacement. Every other partial blocks. Only then create the annotated tag and GitHub prerelease with both exact post-`E` pairs in tag and release metadata.
10. Treat release publication and server access as separate gates. The tag never reopens a host. Install, update, reboot, protected-maintenance return, and rollback all start closed and require their own current release, post-start closed health, tester-only authorization, tester-generation health, released-client join, and explicit production-open sequence. Every open rule renewal then refreshes a 15-second current-`main` and Pages lease. A later channel move closes instead of extending stale authority. Recovery lineage remains closed until a normal accepted local rollback replaces it, then the rollback opening contract applies.
11. Treat any later implementation change as a new subject and restart from skeptical review. Never patch between the final accepted gauntlets and the tag.

## Deferred Live Evidence

These checks cannot be truthfully completed by plan text or a Mac-only authoring session:

- Baseline VPS firewall exposes only Minecraft TCP and voice UDP when maintenance is production-open.
- Permanent default-drop gate rules precede Docker for IPv4 and IPv6; every permission has prior durable same-process authorization and a current authenticated channel-freshness generation, expires within 15 seconds without renewal, and closes immediately after current `main` drift, Pages drift, refresh failure, reconciler death, watchdog stall, rule drift, checkpoint mismatch, compaction failure, bound exhaustion, missing state, or divergent state. Deterministic close-versus-renewal and remote-probe barriers prove every schedule ends in the close-owned generation with zero permissive elements and no old authorization or stale probe republished. Ten-year event-driven and 1,000-compaction filesystem tests prove every live or unexpired freshness reference remains, every expired reference loses authority, crash recovery is unique, and 160 lease files, 168 total regular files, and 2 MiB are hard accepted-state bounds.
- Host and external release-state filesystems provide reliable `flock` where required, inherited descriptor behavior, same-filesystem atomic rename, unnamed `O_TMPFILE`, `linkat(AT_EMPTY_PATH)`, file `fsync`, and directory `fsync`. Finite kill tests after unnamed create, partial write, owner and mode assignment, file flush, immutable final link, replacement link, rename, and parent flush prove final immutable paths never expose partial bytes and every valid replacement is adopted or authentically cleaned by one owner.
- Graceful stop finishes inside two minutes without exit 137.
- Ten-gigabyte heap remains below the 13 GB container limit under gameplay and Chunky load.
- Backup throughput, restore throughput, free-space checks, and quarantine capacity fit the real world size.
- Every host reboot ignores persisted open state, proves closed before Compose, automatically runs or resumes the same durable maintenance reconciliation used manually, and never starts ordinary Compose with an unresolved promotion, operation, rollback, continuation, supersession, or offline marker. A blocker-free reboot restores the stack without creating a new world and requires fresh current-release, post-start health, tester-only, join, and production-open evidence.
- Two released clients join, general join attestation works after install, update, reboot, and protected-maintenance return, whitelist works, and voice chat works over UDP.
- Installed Chunky RCON output is classified conservatively for active, paused, complete, and unknown states.
- The full pack boots and plays on arm64.
- An encrypted offsite bundle restores onto a genuinely empty replacement host after one-time local trust bootstrap, and every interrupted bootstrap or recovery phase remains boot-blocked until exact resume or safe abandonment. A kill after recovery health and reboot before success retains old health, publishes a same-transaction boot continuation, creates new-container health, and durably supersedes the old receipt before success.
- A real protected backup proves the closed gate before archive creation and cannot publish after gate drift or player reconnect.
- A normal update first publishes one authenticated promotion authority, closes and proves maintenance, prevents reopening while the operator moves exact `main`, observes that exact target with an uninterrupted closed predecessor chain, and transfers the authority into the update bootstrap. Failed CI, failed or deadline-stale Pages, and unexpected refs each terminalize one immutable failed-closed attempt without reopening or losing ownership. An explicitly confirmed strict fast-forward successor can inherit only that same authority before its manual normal push. A bypassed, non-fast-forward, second-owner, different, or pre-movement-canceled promotion cannot start update and current-channel drift closes any open host.
- A real update failure remains closed and rollback prepare proves both services stopped before the pinned parent-authenticated offline protected-backup branch, with no RCON or image-lock claim. SIGKILL or reboot at every marker boundary leaves a marker that only the exact active parent can authenticate, continue, or remove; no public or scheduled backup can select offline mode from presence alone.
- SIGKILL at every install, update, and recovery boundary yields exact resume, authenticated safe abandonment, durable success cleanup, stable failed-promotion closure, authorized successor transfer, or update rollback-required failure, with no mixed-data ordinary restart. Reboot after boot-bound health proves same-transaction continuation and health supersession before success. SIGKILL at every maintenance, record-publication, freshness-compaction, and reconciliation boundary yields exact adoption or cleanup, committed completion, fail-closed stop, or one exact crash-resumable `abandoned-closed` reconciliation before another transition.
- SIGKILL at every boundary between each external post-`E` receipt and digest leaves either neither, exact receipt-only, or exact pair. Exact receipt-only retry reauthenticates every remote or archive source and publishes only the missing deterministic digest without changing valid evidence. Digest-only and every malformed, conflicting, noncanonical, in-worktree, or in-workflow state block release publication.
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
