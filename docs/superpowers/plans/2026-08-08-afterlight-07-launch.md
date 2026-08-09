# AFTERLIGHT Plan 07: VPS, Distribution, and v1.0 Launch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a one-command VPS deployment, safe updates and backups, final friend installation assets, release documentation, and a complete v1.0 verification gauntlet.

**Architecture:** Docker Compose runs digest-pinned `itzg/minecraft-server` against a single bind-mounted `/data` tree, with backups stored separately. Pack files are staged only by explicit operator scripts using checksum-pinned packwiz-installer-bootstrap v0.0.3 and an immutable Git commit URL. Container restarts never consume mutable Pages state. Scripts wrap install, update, backup, explicit rollback, empty-host recovery, health checks, and Chunky pregen. Prism plus Packwiz is the complete friend installation lane. AutoModpack hosting remains disabled because the exact client payload is not fully redistributable.

**Tech Stack:** Docker Compose, itzg/minecraft-server, Java 21, packwiz installer, GitHub Pages, GitHub Actions, Chunky, RCON/console commands where available.

## Global Constraints

- Server heap target is 10-12 GB, Java 21, NeoForge 21.1.248, Minecraft 1.21.1.
- No server address, credentials, RCON password, tokens, or secrets enter git.
- `main` is the stable auto-update channel; `dev` remains the working branch.
- CurseForge and current mrpack exports contain embedded third-party jars and remain friends-only.
- World-changing operations require an automatic backup first.
- AutoModpack must not stage or host any artifact classified denied, unknown, or manual review. The full one-JAR lane is blocked until all exact files have affirmative redistribution permission.
- v1.0 is not declared complete until the gauntlet report records every automated check and the required manual client, multiplayer, voice, gameplay, update, and restore checks. AutoModpack is required only if its licensing blocker is later resolved.

---

### Task 1: Docker VPS Package

**Files:**
- Create: `server/docker-compose.yml`
- Create: `server/.env.example`
- Create: `server/server.properties`
- Create: `server/README.md`
- Modify: `.packwizignore`

- [ ] Pin `itzg/minecraft-server:java21` and `itzg/mc-backup` by tested image digests.
- [ ] Configure the itzg image for NeoForge, Java 21, 10 GB max heap by default, sane view/simulation distances, and health checks. Do not set `PACKWIZ_URL` on the production container.
- [ ] Bind `${DATA_DIR:-./data}:/data` and `${BACKUP_DIR:-./backups}:/backups`; do not split the image's `/data` tree across volumes.
- [ ] Document firewall ports for Minecraft and Simple Voice Chat without embedding a host address.
- [ ] Validate Compose syntax with `docker compose config` when Docker is available; otherwise use a YAML parser and document the deferred live-host check.

### Task 2: Backup, Update, Rollback, Recovery, and Pregen Scripts

**Files:**
- Create: `server/scripts/backup.sh`
- Create: `server/scripts/update.sh`
- Create: `server/scripts/rollback.sh`
- Create: `server/scripts/recover.sh`
- Create: `server/scripts/pregen.sh`
- Create: `server/scripts/healthcheck.sh`
- Create: `server/scripts/install.sh`
- Create: `server/scripts/lib.sh`

- [ ] Backup script pauses saves, archives world/config state, resumes saves, and prunes by retention.
- [ ] Install and update scripts acquire a lock, resolve an accepted immutable Git SHA, verify exact-SHA CI and Pages parity, authenticate bootstrap v0.0.3, stage Packwiz into a scratch tree, create a checksummed backup before live mutation, activate only validated pack-managed files, restart, and stop with an explicit rollback command on failed health. They never restore or delete world data automatically.
- [ ] Rollback script requires a named backup, recorded Git SHA, and `CONFIRM_ROLLBACK=yes`; quarantines current data; restores without deleting evidence; serves the matching immutable Packwiz revision; and reminds the operator to revert through `dev` and `main`.
- [ ] Recovery script restores a checksummed archive into an empty data tree, recovers the recorded immutable Packwiz revision, rebuilds runtime jars, preserves any dormant AutoModpack identity material without hosting it, starts, and verifies health.
- [ ] Pregen script documents and issues Chunky commands for a configurable radius.
- [ ] Add shell syntax tests and dry-run modes for every script.

### Task 3: Distribution and Friend Onboarding

**Files:**
- Modify: `tools/build-prism-instance.sh`
- Modify: `docs/INSTALL.md`
- Create: `docs/TROUBLESHOOTING.md`
- Create: `docs/UPDATE_POLICY.md`
- Create: `server/automodpack/README.md`

- [ ] Rebuild the Prism instance against the final Pages URL and pack version.
- [ ] Keep Prism plus Packwiz as the only complete supported installation lane. Verify the instance bootstraps from the accepted release and updates without embedding restricted JARs.
- [ ] Commit the exact AutoModpack licensing inventory and document why complete hosting is blocked: 13 denied, 13 manual-review, and 7 unknown client entries. Do not add or enable AutoModpack while that blocker remains.
- [ ] If every blocked artifact later receives affirmative permission, add AutoModpack 4.0.5 version `ET2mE920`, disable self-update, rebuild the inventory, stage only permitted exact hashes, and complete a separate client/server acceptance gate before support is advertised.
- [ ] Add clear RAM allocation, Java 21, import, launch, update, and recovery instructions.
- [ ] Document optional manual mrpack/zip lane and its friends-only restriction.
- [ ] Document voice chat setup, common client crashes, log collection, and clean reinstall without deleting saves.

### Task 4: Release Candidate Version and CI Hardening

**Files:**
- Modify: `pack.toml`
- Modify: `.github/workflows/pack-ci.yml`
- Create: `docs/releases/v1.0.0.md`
- Create: `tools/gauntlet.sh`

- [ ] Set pack version to `0.9.0-rc.1` for the automated release candidate and refresh Packwiz metadata. Promote to `1.0.0` only after manual acceptance.
- [ ] Add quest validation, shell syntax, forbidden-punctuation scan, and distribution inspection to CI.
- [ ] Build a gauntlet script that runs manifest verification, quest validation, KubeJS log checks, server boot, exports, archive inspection, secret scan, and git hygiene checks.
- [ ] Pin packwiz-installer-bootstrap `v0.0.3` in every consumer and verify SHA-256 `a8fbb24dc604278e97f4688e82d3d91a318b98efc08d5dbfcbcbcab6443d116c` before execution.
- [ ] Run the gauntlet twice from a clean working tree and record exact results.

### Task 5: Final Review, Release, and Handoff

**Files:**
- Modify: `docs/HANDOFF.md`
- Create: `docs/releases/v1.0.0-gauntlet.md`

- [ ] Run a whole-branch skeptical review against the design spec and all seven plans.
- [ ] Fix every critical or important finding, rerun focused checks, then rerun the full gauntlet.
- [ ] Push `dev`, require green CI, fast-forward `main`, require green CI on `main`, and verify Pages files byte-for-byte.
- [ ] Create immutable annotated GitHub tag `v0.9.0-rc.1` after automated checks. Create `v1.0.0` only after the complete manual matrix passes.
- [ ] Leave explicit manual acceptance items for Shane: Prism import and sub-three-minute title screen; new-world quest UI/theme; chapters 1-8 playthrough; all Certifications and hard gates; released-client dedicated-server join; two-user voice test; whitelist/firewall check; update drill; and encrypted offsite empty-host restore drill. Add AutoModpack download/join only if its licensing blocker is resolved.
