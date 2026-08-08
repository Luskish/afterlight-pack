# AFTERLIGHT Plan 07: VPS, Distribution, and v1.0 Launch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a one-command VPS deployment, safe updates and backups, final friend installation assets, release documentation, and a complete v1.0 verification gauntlet.

**Architecture:** Docker Compose runs `itzg/minecraft-server` from the same GitHub Pages Packwiz source as clients. A single bind-mounted `/data` tree preserves the image's expected filesystem contract, with backups stored separately. Scripts wrap update, backup, explicit rollback, empty-host recovery, health checks, AutoModpack payload generation, and Chunky pregen. Release automation creates metadata-safe artifacts while friends-only archives remain local.

**Tech Stack:** Docker Compose, itzg/minecraft-server, Java 21, packwiz installer, GitHub Pages, GitHub Actions, Chunky, RCON/console commands where available.

## Global Constraints

- Server heap target is 10-12 GB, Java 21, NeoForge 21.1.248, Minecraft 1.21.1.
- No server address, credentials, RCON password, tokens, or secrets enter git.
- `main` is the stable auto-update channel; `dev` remains the working branch.
- CurseForge and current mrpack exports contain embedded third-party jars and remain friends-only.
- World-changing operations require an automatic backup first.
- v1.0 is not declared complete until the gauntlet report records every automated check and the required manual client, multiplayer, voice, AutoModpack, and gameplay checks.

---

### Task 1: Docker VPS Package

**Files:**
- Create: `server/docker-compose.yml`
- Create: `server/.env.example`
- Create: `server/server.properties`
- Create: `server/README.md`
- Modify: `.packwizignore`

- [ ] Pin `itzg/minecraft-server:java21` and `itzg/mc-backup` by tested image digests.
- [ ] Configure the itzg image with Packwiz URL, NeoForge, Java 21, 10 GB max heap by default, sane view/simulation distances, and health checks.
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

- [ ] Backup script pauses saves, archives world/config state, resumes saves, and prunes by retention.
- [ ] Update script acquires a lock, verifies green `main` and Pages parity, creates a checksummed backup, stages the AutoModpack client payload, restarts, and stops with an explicit rollback command on failed health. It never overwrites data automatically.
- [ ] Rollback script requires a named backup, recorded Git SHA, and `CONFIRM_ROLLBACK=yes`; quarantines current data; restores without deleting evidence; serves the matching immutable Packwiz revision; and reminds the operator to revert through `dev` and `main`.
- [ ] Recovery script restores a checksummed archive into an empty data tree, recovers the recorded Packwiz revision, rebuilds runtime jars and AutoModpack payload, starts, and verifies health.
- [ ] Pregen script documents and issues Chunky commands for a configurable radius.
- [ ] Add shell syntax tests and dry-run modes for every script.

### Task 3: Distribution and Friend Onboarding

**Files:**
- Modify: `tools/build-prism-instance.sh`
- Modify: `docs/INSTALL.md`
- Create: `docs/TROUBLESHOOTING.md`
- Create: `docs/UPDATE_POLICY.md`
- Add: `mods/automodpack.pw.toml`
- Create: `server/automodpack/README.md`

- [ ] Rebuild the Prism instance against the final Pages URL and pack version.
- [ ] Add AutoModpack 4.0.5, exact Modrinth version `ET2mE920`, as `side = "server"`; set `requireAutoModpackOnClient=false` and `selfUpdater=false`.
- [ ] Build AutoModpack's host payload from a pinned Packwiz client-side install; keep `syncedFiles=[]` and document private certificate-fingerprint distribution.
- [ ] Add clear RAM allocation, Java 21, import, launch, update, and recovery instructions.
- [ ] Document optional manual mrpack/zip lane and its friends-only restriction.
- [ ] Document voice chat setup, common client crashes, log collection, and clean reinstall without deleting saves.

### Task 4: Release Candidate Version and CI Hardening

**Files:**
- Modify: `pack.toml`
- Modify: `.github/workflows/pack-ci.yml`
- Create: `docs/releases/v1.0.0.md`
- Create: `tools/gauntlet.sh`

- [ ] Set pack version to `0.9.0` for the automated release candidate and refresh Packwiz metadata. Promote to `1.0.0` only after manual acceptance.
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
- [ ] Create GitHub tag `v0.9.0-rc1` after automated checks. Create `v1.0.0` only after the complete manual matrix passes.
- [ ] Leave explicit manual acceptance items for Shane: Prism import and sub-three-minute title screen; new-world quest UI/theme; chapters 1-8 playthrough; all Certifications and hard gates; released-client dedicated-server join; one-jar AutoModpack download/join; two-user voice test; whitelist/firewall check; offsite restore drill.
