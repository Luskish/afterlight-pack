# AFTERLIGHT Plan 07: VPS, Distribution, and v1.0 Launch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a one-command VPS deployment, safe updates and backups, final friend installation assets, release documentation, and a complete v1.0 verification gauntlet.

**Architecture:** Docker Compose runs `itzg/minecraft-server` from the same GitHub Pages Packwiz source as clients. Scripts wrap update, backup, rollback, health checks, and Chunky pregen. Release automation creates metadata-safe artifacts while friends-only archives remain local.

**Tech Stack:** Docker Compose, itzg/minecraft-server, Java 21, packwiz installer, GitHub Pages, GitHub Actions, Chunky, RCON/console commands where available.

## Global Constraints

- Server heap target is 10-12 GB, Java 21, NeoForge 21.1.248, Minecraft 1.21.1.
- No server address, credentials, RCON password, tokens, or secrets enter git.
- `main` is the stable auto-update channel; `dev` remains the working branch.
- CurseForge and current mrpack exports contain embedded third-party jars and remain friends-only.
- World-changing operations require an automatic backup first.
- v1.0 is not declared complete until the gauntlet report records every automated check and the remaining manual client check.

---

### Task 1: Docker VPS Package

**Files:**
- Create: `server/docker-compose.yml`
- Create: `server/.env.example`
- Create: `server/server.properties`
- Create: `server/README.md`
- Modify: `.packwizignore`

- [ ] Configure the itzg image with Packwiz URL, NeoForge, Java 21, 12 GB max heap, sane view/simulation distances, and health checks.
- [ ] Configure named volumes for world, config, logs, and backups.
- [ ] Document firewall ports for Minecraft and Simple Voice Chat without embedding a host address.
- [ ] Validate Compose syntax with `docker compose config` when Docker is available; otherwise use a YAML parser and document the deferred live-host check.

### Task 2: Backup, Update, Rollback, and Pregen Scripts

**Files:**
- Create: `server/scripts/backup.sh`
- Create: `server/scripts/update.sh`
- Create: `server/scripts/rollback.sh`
- Create: `server/scripts/pregen.sh`
- Create: `server/scripts/healthcheck.sh`

- [ ] Backup script pauses saves, archives world/config state, resumes saves, and prunes by retention.
- [ ] Update script creates a backup, records current Packwiz hash, restarts, and rolls back automatically on failed health.
- [ ] Rollback script restores a named backup only after confirmation through an explicit environment variable.
- [ ] Pregen script documents and issues Chunky commands for a configurable radius.
- [ ] Add shell syntax tests and dry-run modes for every script.

### Task 3: Distribution and Friend Onboarding

**Files:**
- Modify: `tools/build-prism-instance.sh`
- Modify: `docs/INSTALL.md`
- Create: `docs/TROUBLESHOOTING.md`
- Create: `docs/UPDATE_POLICY.md`

- [ ] Rebuild the Prism instance against the final Pages URL and pack version.
- [ ] Add clear RAM allocation, Java 21, import, launch, update, and recovery instructions.
- [ ] Document optional manual mrpack/zip lane and its friends-only restriction.
- [ ] Document voice chat setup, common client crashes, log collection, and clean reinstall without deleting saves.

### Task 4: Release Version and CI Hardening

**Files:**
- Modify: `pack.toml`
- Modify: `.github/workflows/pack-ci.yml`
- Create: `docs/releases/v1.0.0.md`
- Create: `tools/gauntlet.sh`

- [ ] Set pack version to `1.0.0` and refresh Packwiz metadata.
- [ ] Add quest validation, shell syntax, forbidden-punctuation scan, and distribution inspection to CI.
- [ ] Build a gauntlet script that runs manifest verification, quest validation, KubeJS log checks, server boot, exports, archive inspection, secret scan, and git hygiene checks.
- [ ] Run the gauntlet twice from a clean working tree and record exact results.

### Task 5: Final Review, Release, and Handoff

**Files:**
- Modify: `docs/HANDOFF.md`
- Create: `docs/releases/v1.0.0-gauntlet.md`

- [ ] Run a whole-branch skeptical review against the design spec and all seven plans.
- [ ] Fix every critical or important finding, rerun focused checks, then rerun the full gauntlet.
- [ ] Push `dev`, require green CI, fast-forward `main`, require green CI on `main`, and verify Pages files byte-for-byte.
- [ ] Create GitHub tag `v1.0.0` and release notes only after all automated checks pass.
- [ ] Leave exactly one explicit manual acceptance item for Shane: import the Prism instance, reach title screen, create/join a world, and verify quest UI/theme.

