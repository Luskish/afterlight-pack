# Plan 07 Architecture Audit

Date: 2026-08-08

Status: design gate corrected after maintenance, rollback-transaction, and final-release review. No Docker, VPS, backup, recovery, CI, Pages, Prism, or release behavior is claimed by this document.

## Scope

The launch architecture was reviewed before implementation against the exact current itzg image manifests, Packwiz installer release bytes, NeoForge installer checksum, Docker Compose behavior, GitHub Actions APIs, GitHub Pages mutability, RCON secret handling, Chunky operations, Python archive extraction safety, nested Linux lock behavior, host ingress maintenance safety, rollback channel safety, transaction continuity, and release-evidence ordering.

The initial review found nine Critical and nine Important design gaps. A completed follow-up contradiction review found seven cross-task defects in the rewritten plan: acceptance self-deadlock, unhandled Packwiz installer state, an incorrect release-candidate manual gate, nested lock reacquisition, backup exclusions that were not part of resolved Compose, client-unsafe rollback, and evidence self-reference. A subsequent pinned-source check found that online and offline backup enter different RCON and image-lock branches. The final architecture review found three additional independent failures: maintenance was prose rather than a persisted access control, rollback prepare and activate had no durable one-time binding, and tag creation did not require an external accepted-mode receipt for evidence SHA `E`. The corrected plan resolves all findings as one executable release sequence. Implementation still requires test-first development, whole-project skeptical review, two accepted clean gauntlet runs, exact-SHA CI and Pages evidence, and the deferred live-host matrix.

## Threat Model and Corrections

The maintenance finding protects against a server that is described as closed while Docker still accepts public TCP or UDP traffic, a reboot that forgets the maintenance state, a restored `/data` tree that reverts the access decision, and a protected backup that begins while a player can still write world state. The correction is one authenticated host ingress state machine outside `/data`, with exact `close`, `status`, tester-only `open`, and production `open` commands. The live kernel rules, active connections, and player count must agree with persisted state before a protected archive starts.

The rollback finding protects against time-of-check to time-of-use substitution between prepare and activate. Without a transaction, an operator or interrupted process could change the bundle, `H`, rollback commit `R`, restored data, managed ledger, Packwiz provenance, journal, quarantine, service state, or gate state, then activate under evidence produced for something else. The correction is one HMAC-authenticated prepare receipt and pending pointer outside `/data`, complete tree and state digests, revalidation under the inherited operations lock, a durable activation intent, and a consumed tombstone. Production remains inaccessible through interruption, and a completed receipt cannot be activated twice.

The evidence finding protects against tagging `E` after checking only CI and Pages, copying stale acceptance evidence from `S`, writing a post-commit fact into `E`, or making the workflow whose success is required wait for itself. The correction runs accepted mode externally only after exact `E` CI and Pages parity complete, writes canonical create-new receipt and digest files outside every worktree, and requires those exact bytes in annotated-tag and GitHub-release metadata before publication.

These controls defend against stale state, accidental or unauthorized unprivileged mutation, operator sequencing mistakes, interrupted scripts, archive substitution, mutable branch or Pages drift, and receipt replay. They do not defend against a compromised root account, a compromised GitHub or Pages trust root, theft of `${SECRETS_DIR}/receipt-auth.key`, malicious tester endpoints, or physical host compromise. Those events require credential rotation, host rebuild, and a new release acceptance cycle rather than reuse of local receipts.

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

1. `closed` drops new and established traffic to Minecraft TCP `25565` and voice UDP `24454` from external, host, loopback, and peer-container paths, leaves unpublished internal RCON control available, terminates existing game sessions, and requires zero connected players when Minecraft is running.
2. `tester-only` permits only canonical IPv4 or IPv6 CIDRs from mode `0600` `${SECRETS_DIR}/maintenance-testers.txt`. Receipts record only the allowlist SHA-256 and entry count.
3. `production-open` removes AFTERLIGHT's maintenance restriction but never broadens the baseline host firewall or bypasses the Minecraft whitelist.

`server/scripts/maintenance.sh` is the sole writer. Its public interfaces are `close --reason TOKEN`, `status --require MODE --receipt-out RECEIPT`, and `open --mode tester-only|production`. Mutating calls hold `${STATE_DIR}/ops.lock` directly or validate the inherited descriptor. The root-owned implementation atomically updates an `nftables` ingress table evaluated before Docker's published-port acceptance for IPv4 and IPv6.

`${STATE_DIR}/maintenance/state.json` stores the current canonical state. Immutable generation receipts live at `${STATE_DIR}/maintenance/receipts/<generation>.json`; immutable proofs live at `${STATE_DIR}/maintenance/proofs/<proof-id>.json`. Every local record has an HMAC-SHA-256, predecessor digest, generation, operation ID, live-rule digest, active-connection observation, service and player observation, and bound release or transaction context. Missing state, bad HMAC, stale generation, live-rule drift, wrong file ownership or mode, links, or reboot replay failure resolves to closed and blocks Compose startup.

Every transition durably creates an intent, applies live rules, proves those rules, and only then publishes the new current state and immutable receipt. Close installs drops before publishing closed. Production opening publishes no open state until all release, health, transaction, and join checks plus live-rule proof succeed. Any incomplete transition intent is interpreted as closed. Root-owned `afterlight-maintenance-gate.service` runs before and is required by root-owned `afterlight-compose.service`; Compose services have no independent restart policy that can bypass this ordering.

Protected backup always invokes close and then status under the same inherited operations lock before starting the backup image. Bundle publication rechecks the same generation and live-rule digest. A failed proof, player reconnect, or rule change produces no completed protected bundle and leaves the gate closed. Scheduled online backup is the only backup class that may run without changing an already authenticated gate mode.

No install, update, backup, rollback, recovery, health, or Chunky command can open production. Rollback activate may call tester-only open for its exact transaction. Production open is a separate operator action after the released-client join receipt exists, and it revalidates current accepted `R`, Pages parity, health, activation, join receipt, and tester-only generation before writing `production-open`.

## Lock Model

Every top-level mutating command opens and acquires `${STATE_DIR}/ops.lock` once, keeps that one Linux file descriptor open for the full operation, and exports its number as `AFTERLIGHT_OPS_LOCK_FD`. A nested maintenance command receives the inherited open descriptor and uses an internal `--lock-held` contract. It validates that the descriptor is numeric, open, and points through Linux `/proc/self/fd` to the canonical operations lock, then requires nonblocking `flock -n` on that same descriptor to succeed. The inherited locked open-file description succeeds without reacquisition; a separately opened descriptor fails while the parent lock is held.

Direct `backup.sh` calls acquire the operations lock normally. Backup calls nested beneath update, rollback, or Chunky reuse the parent's descriptor. Tests cover update-to-backup, rollback-to-backup, and pregen-to-backup execution, assert that the same descriptor remains held, and fail forged or separately opened descriptors. The normal online image branch adds `${BACKUP_DIR}/.mc-backup-lock` as a separate archive-serialization lock with the existing fixed acquisition order. The offline paused branch has no image lock and remains serialized by the inherited host operations descriptor. No nested path may reacquire the operations lock and self-deadlock.

Maintenance transitions, rollback receipt creation, activation intent, transaction consumption, join attestation, and production opening all use that same operations lock. A status proof written for a protected backup or transaction is therefore ordered with the state it authenticates rather than being a racy observation from another process.

## Update and Rollback Model

An update stages before downtime, takes a protected backup that closes and proves the gate, and activates only validated pack-managed files. Packwiz updates pack-managed paths in `/data`; the prohibition is against automatic world restore, world deletion, or rollback. Even a healthy update remains closed until the operator explicitly opens the accepted release.

An update health failure stops Minecraft, leaves the gate closed, exits with code `6`, preserves logs, candidate files, Packwiz provenance, backup, ledger, journal, quarantine state, and receipts, and writes one authenticated rollback-request receipt. It prints the fixed runbook path and exact failed bundle values. It cannot print a valid prepare command until the operator has created rollback SHA `R` and an accepted `R` receipt, and it never restores world data automatically.

Rollback remains a truthful two-phase operation, but the operator-owned Git promotion now precedes data-changing prepare so prepare can bind the exact rollback release:

1. From authenticated bundle snapshots for historical SHA `H`, the operator creates and reviews normal rollback commit `R`, pushes exact `R` through `dev`, promotes it unchanged to `main`, waits for exact-SHA CI and Pages parity, and runs accepted mode externally. Maintenance tooling never commits, reverts, pushes, mutates branches or tags, or calls a GitHub write API.
2. `rollback.sh prepare` requires the named bundle, `R`, its canonical accepted receipt, and explicit bundle confirmation. It authenticates `H`, requires raw `R` `pack.toml` and `index.toml` to be byte-identical to the bundle's authenticated historical snapshots, and rechecks current accepted `main` plus Pages before mutating data.
3. Under the inherited operations lock, prepare creates a protected backup of the failed current state, stops Minecraft and scheduled backup, proves the gate closed, restores through a sibling candidate and same-filesystem quarantine, overlays only exact raw-`R` managed files, completes the journal, marks active-release state as `lineage=rollback` with immutable transaction ID and `R`, and leaves services stopped.
4. Prepare writes one HMAC-authenticated schema `afterlight.rollback.prepare.v1` receipt beneath `${STATE_DIR}/rollback/transactions/<transaction-id>/`. It binds the bundle and all archive metadata; `H`; `R`; historical and current acceptance receipts; raw and snapshot manifest hashes; the failed-current protected bundle; pre-restore and prepared data-root identities and complete tree-inventory digests; managed ledger; active release; candidate and Packwiz provenance; pinned installer provenance; completed journal; quarantine identity and inventory; stopped service observations; closed maintenance generation, receipts, proof, and live-rule digest; tool version; and predecessor digest.
5. `${STATE_DIR}/rollback/pending.json` binds the sole pending transaction ID to that exact prepare-receipt digest. Exact transaction files are `prepare.json`, `prepare.json.sha256`, `data-before.inventory`, `data-prepared.inventory`, `quarantine.inventory`, `activation-intent.json`, `activation.json`, `join.json`, and `production-open.json`. State directories are root-owned mode `0700`, mutable state is mode `0600`, and immutable files become mode `0400` after create-new publication and flush. Everything remains outside `/data`, and quarantine remains preserved.
6. `rollback.sh activate` takes only transaction ID, exact prepare receipt, and explicit transaction confirmation. While holding the operations lock, it authenticates the receipt and pending pointer, rejects a consumed or competing transaction, rechecks current accepted `R` and Pages, and recomputes every data, ledger, release, provenance, journal, quarantine, service, and gate identity or digest. Any intervening mutation blocks server start.
7. Before server start, activate durably writes one activation intent and transitions `prepared` to `activating`. It opens only tester access for the bound allowlist, force-recreates Minecraft, verifies health at `R`, then writes the activation receipt and `${STATE_DIR}/rollback/consumed/<transaction-id>.json` tombstone before clearing the pending pointer. A completed prepare receipt cannot be activated again.
8. A signal, failed health check, interrupted write, or reboot never produces production-open. Traps stop and close where possible; an incomplete intent is treated as closed on boot. Explicit `--resume` can continue only the same intent after full revalidation and cannot create a second activation.
9. Shane joins with the released client while the gate is tester-only. `rollback.sh attest-join` records that explicit manual pass against the same consumed transaction, active `R`, client acceptance receipt, health result, and gate generation. Health alone cannot create the receipt.
10. `maintenance.sh open --mode production` is a separate command. It consumes the matching join receipt into a new gate transition only after revalidating current accepted `R`, Pages parity, health, transaction, activation, and tester-only state. No rollback phase opens production implicitly.

The operator command contract is:

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

server/scripts/rollback.sh activate \
  --transaction "${transaction_id}" \
  --receipt "${STATE_DIR}/rollback/transactions/${transaction_id}/prepare.json" \
  --confirm "${transaction_id}"

server/scripts/rollback.sh attest-join \
  --transaction "${transaction_id}" \
  --client-release-receipt "${released_client_receipt}" \
  --confirm "${transaction_id}"

server/scripts/maintenance.sh open \
  --mode production \
  --release-receipt "${r_receipt}" \
  --transaction "${transaction_id}" \
  --join-receipt "${STATE_DIR}/rollback/transactions/${transaction_id}/join.json"
```

`server/README.md` must show how each variable is obtained from a preceding receipt, print the exact expected mode after every command, and document interruption, resume, abandonment, and forensic paths. Empty-host recovery creates fresh local secrets and closed gate state, marks active release `lineage=recovery`, and cannot open production. To reopen, the operator creates accepted `R` and completes the normal local rollback prepare, activate, tester-only join, and production-open sequence, replacing recovery lineage with the bound rollback transaction. Restoring or starting a server alone is not evidence that the mutable client channel is safe.

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
10. Treat any later implementation change as a new subject and restart from skeptical review. Never patch between the final accepted gauntlets and the tag.

## Deferred Live Evidence

These checks cannot be truthfully completed by plan text or a Mac-only authoring session:

- Baseline VPS firewall exposes only Minecraft TCP and voice UDP when maintenance is production-open.
- The authenticated gate precedes Docker for IPv4 and IPv6, closes established sessions, enforces tester CIDRs, survives reboot before Compose, and fails closed on missing or divergent state.
- Host filesystem provides reliable `flock`, inherited descriptor behavior, and same-filesystem atomic rename.
- Graceful stop finishes inside two minutes without exit 137.
- Ten-gigabyte heap remains below the 13 GB container limit under gameplay and Chunky load.
- Backup throughput, restore throughput, free-space checks, and quarantine capacity fit the real world size.
- Host reboot restores the Compose stack and backup schedule without creating a new world.
- Two released clients join, whitelist works, and voice chat works over UDP.
- Installed Chunky RCON output is classified conservatively for active, paused, complete, and unknown states.
- The full pack boots and plays on arm64.
- An encrypted offsite bundle restores onto a genuinely empty replacement host.
- A real protected backup proves the closed gate before archive creation and cannot publish after gate drift or player reconnect.
- A real update failure remains closed and is followed by one authenticated, mutation-resistant, one-time rollback transaction without post-backup player writes.
- A released client joins the accepted rollback release in tester-only mode before a separate production-open command.

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
