# AFTERLIGHT Friend Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship AFTERLIGHT `0.9.0-rc.1` as a safe, reproducible private-friend release with one-click Prism installation, a straightforward Docker Compose server, automatic backups, tested update and rollback commands, and a green release pipeline.

**Architecture:** Keep Packwiz and GitHub Pages as the stable content channel. Add one digest-pinned Compose stack for Minecraft plus continuous backups, one Bash operator entry point, and one deterministic Python-backed Prism builder. Validate the release through focused unit tests, the existing authenticated server harness, one detached-SHA gauntlet, branch CI, Pages parity, and a GitHub prerelease that exposes only redistribution-safe files.

**Tech Stack:** NeoForge 21.1.248, Minecraft 1.21.1, Java 21, Packwiz, Prism Launcher, Bash, Python 3 standard library, Docker Compose v2, `itzg/minecraft-server`, `itzg/mc-backup`, GitHub Actions, GitHub Pages.

## Global Constraints

- Read and follow `/Users/shaneliszewski/MinecraftTest/AGENTS.md` before every task.
- Do not introduce a U+2014 em dash character in code, prose, comments, output, or commit messages.
- The working branch is `dev`; `main` remains the stable Packwiz channel.
- Do not modify, reset, merge, or delete `codex/plan07-task1` or `/private/tmp/afterlight-plan07-task1`.
- Minecraft stays at `1.21.1`, NeoForge stays at `21.1.248`, and the runtime stays on Java 21.
- The stable Packwiz URL is `https://luskish.github.io/afterlight-pack/pack.toml`.
- Pin Packwiz bootstrap `v0.0.3` to SHA-256 `a8fbb24dc604278e97f4688e82d3d91a318b98efc08d5dbfcbcbcab6443d116c`.
- Pin `itzg/minecraft-server:2026.8.0-java21@sha256:b76b9298a2a60d5cf9d223e009cd0b8ad620c2080abd83f9a1fa5084fa87f9ab`.
- Pin `itzg/mc-backup:2026.8.0@sha256:ae54d88d1a5dfbc185f1f94e50bb2e9b68484719013f4f21c573422dd4950f32`.
- The Prism instance ZIP is the only public client artifact. The `.mrpack` and CurseForge ZIP remain friends-only because they embed third-party mod JARs.
- No JAR, secret, token, world, log, backup, launcher credential, or runtime cache enters Git.
- Every Packwiz command starts after `source tools/versions.env && export PATH="$PATH_EXTRA:$PATH"`.
- Any Packwiz-touching commit stages `pack.toml`, `index.toml`, and `mods/` together and leaves refresh output committed.
- Every changed manifest, configuration, or script must pass `./tools/verify-pack.sh` and `BOOT_TIMEOUT=600 ./tools/server-test.sh` before integration.
- Every Codex-authored commit ends with `Co-Authored-By: Codex <noreply@openai.com>`.

## File Structure

- `server/docker-compose.yml`: Defines the two pinned, continuously restarted services and their bind mounts, secret, health check, ports, Packwiz source, and backup policy.
- `server/.env.example`: Documents the only three operator-owned paths: `DATA_DIR`, `BACKUP_DIR`, and `SECRETS_DIR`.
- `server/server.properties.example`: Supplies the friend-server gameplay, whitelist, security, RCON, distance, and player-count baseline.
- `server/backup-excludes.txt`: Keeps downloaded binaries and transient runtime data out of world backups.
- `server/afterlight-server.sh`: Implements `doctor`, `start`, `stop`, `status`, `backup`, `update`, and confirmed rollback.
- `server/README.md`: Gives a Linux operator one path from an empty host to a running, backed-up server.
- `tools/tests/test_friend_server.py`: Owns the Compose and operator-command contracts with a fake Docker executable.
- `tools/release_artifacts.py`: Builds and inspects deterministic Prism archives, inspects friends-only exports, scans tracked files, and writes release metadata and checksums.
- `tools/build-prism-instance.sh`: Downloads the exact bootstrap JAR, verifies it, and delegates deterministic ZIP creation.
- `tools/build-release.sh`: Builds and inspects all release formats while copying only public-safe files into the public output set.
- `tools/tests/test_release_artifacts.py`: Proves reproducibility, checksum enforcement, path safety, artifact classification, and secret/JAR policies.
- `.github/workflows/pack-ci.yml`: Runs the complete automated release gate and uploads only the Prism ZIP, metadata, and checksums.
- `tools/release-gauntlet.sh`: Runs the complete local release matrix against a clean detached commit and exports accepted evidence.
- `tools/tests/test_release_gauntlet.py`: Proves detached-SHA enforcement, command order, byte comparison, cleanup, and fail-fast behavior.
- `docs/INSTALL.md`: Gives friends the short Prism import path and labels both embedded-JAR formats as private.
- `docs/SERVER.md`: Gives Shane host setup, firewall, backup, update, rollback, and troubleshooting commands.
- `docs/RELEASING.md`: Gives the exact `dev` CI, `main` promotion, Pages parity, tag, prerelease, and `1.0.0` manual gate procedure.
- `docs/releases/0.9.0-rc.1.md`: Records automated evidence and leaves player-facing checks explicitly unclaimed.

---

### Task 1: Friend Server Stack and Operations

**Files:**
- Create: `server/docker-compose.yml`
- Create: `server/.env.example`
- Create: `server/server.properties.example`
- Create: `server/backup-excludes.txt`
- Create: `server/afterlight-server.sh`
- Create: `server/README.md`
- Create: `docs/SERVER.md`
- Create: `tools/tests/test_friend_server.py`
- Modify: `.gitignore`
- Modify: `.packwizignore`
- Modify: `README.md`
- Modify: `tools/verify-pack.sh`

**Interfaces:**
- Consumes: `server/.env` with exact `KEY=/absolute/path` assignments for `DATA_DIR`, `BACKUP_DIR`, and `SECRETS_DIR`.
- Consumes: `${SECRETS_DIR}/rcon_password`, a regular, non-symlinked, nonempty mode `0600` file.
- Produces: `server/afterlight-server.sh doctor|start|stop|status|backup|update|rollback BACKUP --confirm`.
- Produces: services named `minecraft` and `backup`, project name `afterlight`, TCP `25565`, UDP `24454`, and no published RCON port.
- Produces: timestamped sibling rescue directories named `<data-basename>.rescue-YYYYMMDDTHHMMSSZ` during rollback.

- [ ] **Step 1: Write the failing server contract tests**

Create `tools/tests/test_friend_server.py` with temporary directories, a fake `docker` executable that records every argument, and assertions covering all of these exact facts:

```python
EXPECTED_MINECRAFT_IMAGE = (
    "itzg/minecraft-server:2026.8.0-java21@sha256:"
    "b76b9298a2a60d5cf9d223e009cd0b8ad620c2080abd83f9a1fa5084fa87f9ab"
)
EXPECTED_BACKUP_IMAGE = (
    "itzg/mc-backup:2026.8.0@sha256:"
    "ae54d88d1a5dfbc185f1f94e50bb2e9b68484719013f4f21c573422dd4950f32"
)
EXPECTED_PACK_URL = "https://luskish.github.io/afterlight-pack/pack.toml"
REQUIRED_OPERATOR_TESTS = {
    "test_unknown_command_fails_with_usage",
    "test_doctor_rejects_relative_nested_or_symlinked_paths",
    "test_start_copies_properties_once_then_starts_both_services",
    "test_backup_requires_a_new_regular_archive",
    "test_update_backs_up_before_recreating_minecraft",
    "test_failed_update_stops_services_and_prints_exact_rollback_command",
    "test_rollback_requires_confirm_and_archive_beneath_backup_root",
    "test_rollback_renames_data_restores_and_never_invokes_rm",
}
```

The Compose test must read `server/docker-compose.yml` and assert both image constants, the exact Packwiz URL, `BACKUP_INTERVAL: "6h"`, `PRUNE_BACKUPS_DAYS: "14"`, exactly two `restart: unless-stopped` values, and no published `25575`. Implement every method named in `REQUIRED_OPERATOR_TESTS`. The fake Docker command must make `docker compose config`, `ps`, `up`, `stop`, `exec`, and `logs` independently controllable through environment variables. The update and rollback tests must compare the recorded command order, not only command membership.

- [ ] **Step 2: Run the server tests and prove RED**

Run:

```bash
python3 -m unittest tools.tests.test_friend_server -v
```

Expected: failure because `server/docker-compose.yml` and `server/afterlight-server.sh` do not exist.

- [ ] **Step 3: Add the pinned Compose and operator-owned inputs**

Create `server/docker-compose.yml` with:

```yaml
name: afterlight
services:
  minecraft:
    image: itzg/minecraft-server:2026.8.0-java21@sha256:b76b9298a2a60d5cf9d223e009cd0b8ad620c2080abd83f9a1fa5084fa87f9ab
    restart: unless-stopped
    init: true
    environment:
      EULA: "TRUE"
      TYPE: NEOFORGE
      VERSION: "1.21.1"
      NEOFORGE_VERSION: "21.1.248"
      PACKWIZ_URL: https://luskish.github.io/afterlight-pack/pack.toml
      INIT_MEMORY: 4G
      MAX_MEMORY: 10G
      ENABLE_RCON: "TRUE"
      RCON_PASSWORD_FILE: /run/secrets/rcon_password
    ports:
      - "25565:25565/tcp"
      - "24454:24454/udp"
    secrets: [rcon_password]
    volumes:
      - type: bind
        source: ${DATA_DIR:?DATA_DIR must be set}
        target: /data
        bind: { create_host_path: false }
    healthcheck:
      test: ["CMD", "mc-health"]
      interval: 10s
      timeout: 5s
      retries: 48
      start_period: 2m
    mem_limit: 13G
    stop_grace_period: 2m
  backup:
    image: itzg/mc-backup:2026.8.0@sha256:ae54d88d1a5dfbc185f1f94e50bb2e9b68484719013f4f21c573422dd4950f32
    restart: unless-stopped
    init: true
    depends_on:
      minecraft: { condition: service_healthy }
    environment:
      RCON_HOST: minecraft
      RCON_PASSWORD_FILE: /run/secrets/rcon_password
      BACKUP_METHOD: tar
      TAR_COMPRESS_METHOD: zstd
      BACKUP_INTERVAL: "6h"
      INITIAL_DELAY: "0"
      BACKUP_ON_STARTUP: "true"
      ENABLE_SAVE_ALL: "true"
      ENABLE_SYNC: "true"
      EXCLUDES: ""
      EXCLUDES_FILE: /etc/afterlight-backup-excludes.txt
      PRUNE_BACKUPS_DAYS: "14"
      LINK_LATEST: "false"
    secrets: [rcon_password]
    volumes:
      - type: bind
        source: ${DATA_DIR:?DATA_DIR must be set}
        target: /data
        read_only: true
        bind: { create_host_path: false }
      - type: bind
        source: ${BACKUP_DIR:?BACKUP_DIR must be set}
        target: /backups
        bind: { create_host_path: false }
      - ./backup-excludes.txt:/etc/afterlight-backup-excludes.txt:ro
secrets:
  rcon_password:
    file: ${SECRETS_DIR:?SECRETS_DIR must be set}/rcon_password
```

Add the exact three path assignments to `.env.example`, the approved property values from the design spec to `server.properties.example`, and exclusions for JARs, caches, libraries, versions, logs, crash reports, lock files, partial files, and `server.properties` to `backup-excludes.txt`.

- [ ] **Step 4: Implement the operator command state machine**

Create executable `server/afterlight-server.sh` with `set -euo pipefail` and focused functions using these interfaces:

```bash
load_paths()              # parse exact assignments without source or eval
compose()                 # docker compose --project-name afterlight --env-file "$ENV_FILE" -f "$COMPOSE_FILE"
canonicalize_paths()      # realpath -m, absolute, non-root, pairwise nonnested
validate_writable_dirs()  # existing DATA_DIR and BACKUP_DIR are directories and writable
validate_secret()         # regular, not symlink, mode 600, exactly one nonempty line
validate_ports()          # when Minecraft is stopped, ss proves TCP 25565 and UDP 24454 are free
wait_healthy()            # poll compose ps for at most AFTERLIGHT_HEALTH_TIMEOUT=600
latest_backup_snapshot()  # sorted regular-file name, size, mtime inventory
run_doctor()
run_start()
run_stop()
run_status()
run_backup()
run_update()
run_rollback()
```

`run_doctor` must require `docker`, Compose v2, `realpath`, `tar`, `zstd`, and `ss`; validate writable directories and the secret; render Compose; and check the two public game ports when the AFTERLIGHT Minecraft service is not already running. `run_update` must call `run_backup`, stop both services, force-recreate only Minecraft, wait healthy, start backup, and print the selected backup path. If health fails, it must stop both services and run `printf "Rollback: server/afterlight-server.sh rollback '%s' --confirm\n" "$backup_path"` before returning nonzero.

`run_rollback` must reject missing `--confirm`, reject symlinks and paths outside `BACKUP_DIR`, stop both services, rename the existing `DATA_DIR` to a UTC rescue sibling, create a fresh `DATA_DIR`, extract the zstd tar with owner and permission restoration disabled, start both services, and wait healthy. It must contain no `rm` command and preserve the archive, rescue directory, and restored directory on every failure path.

- [ ] **Step 5: Add operator and firewall documentation**

Write `server/README.md` and `docs/SERVER.md` with exact commands for:

```bash
cp server/.env.example server/.env
sudo install -d -m 0750 /srv/afterlight/data /srv/afterlight/backups
sudo install -d -m 0700 /etc/afterlight/secrets
openssl rand -base64 36 | sudo tee /etc/afterlight/secrets/rcon_password >/dev/null
sudo chmod 0600 /etc/afterlight/secrets/rcon_password
server/afterlight-server.sh doctor
server/afterlight-server.sh start
server/afterlight-server.sh backup
server/afterlight-server.sh update
server/afterlight-server.sh rollback /srv/afterlight/backups/afterlight-20260809-120000.tar.zst --confirm
```

Document Ubuntu UFW rules for the operator's existing SSH port, TCP `25565`, UDP `24454`, and default deny. State that RCON `25575` must never be forwarded and that the Minecraft whitelist must be populated before the address is shared.

- [ ] **Step 6: Exclude operator files from Packwiz and runtime files from Git**

Add these exact patterns:

```text
# .gitignore
server/.env
server/data/
server/backups/
server/*.rescue-*/

# .packwizignore
server/**
```

Link `docs/SERVER.md` from `README.md`. Extend the tooling loop in `tools/verify-pack.sh` to parse and check executable status for `server/afterlight-server.sh`.

- [ ] **Step 7: Run focused and Compose validation**

Run:

```bash
python3 -m unittest tools.tests.test_friend_server -v
bash -n server/afterlight-server.sh
shellcheck server/afterlight-server.sh
tmp=$(mktemp -d)
mkdir -p "$tmp/data" "$tmp/backups" "$tmp/secrets"
printf 'test-only-rcon-password\n' > "$tmp/secrets/rcon_password"
chmod 0600 "$tmp/secrets/rcon_password"
printf 'DATA_DIR=%s\nBACKUP_DIR=%s\nSECRETS_DIR=%s\n' "$tmp/data" "$tmp/backups" "$tmp/secrets" > "$tmp/server.env"
docker compose --project-name afterlight --env-file "$tmp/server.env" -f server/docker-compose.yml config --quiet
docker compose --project-name afterlight --env-file "$tmp/server.env" -f server/docker-compose.yml config --services
```

Expected: unit tests pass, Bash and ShellCheck pass, Compose renders, and services are exactly `minecraft` and `backup`.

- [ ] **Step 8: Run the repository gates**

Run:

```bash
source tools/versions.env && export PATH="$PATH_EXTRA:$PATH"
packwiz refresh
./tools/verify-pack.sh
BOOT_TIMEOUT=600 ./tools/server-test.sh
git diff --check
```

Expected: `VERIFY: ALL GREEN`, `SERVER BOOT: OK`, and no unexpected Packwiz index entries under `server/`.

- [ ] **Step 9: Commit Task 1**

```bash
git add .gitignore .packwizignore README.md docs/SERVER.md server/ tools/tests/test_friend_server.py tools/verify-pack.sh pack.toml index.toml mods/
git commit -m "feat(server): add friend-ready operations" -m "Co-Authored-By: Codex <noreply@openai.com>"
```

---

### Task 2: Deterministic Prism Distribution

**Files:**
- Create: `tools/release_artifacts.py`
- Create: `tools/tests/test_release_artifacts.py`
- Modify: `tools/build-prism-instance.sh`
- Modify: `tools/verify-pack.sh`
- Modify: `docs/INSTALL.md`

**Interfaces:**
- Consumes: one locally downloaded bootstrap JAR whose SHA-256 matches `PACKWIZ_BOOTSTRAP_SHA256`.
- Produces: `build_prism_archive(bootstrap_path, output_path, pack_url, minecraft_version, neoforge_version) -> pathlib.Path`.
- Produces: `inspect_prism_archive(archive_path, pack_url, bootstrap_sha256) -> dict[str, object]`.
- Produces: byte-identical `dist/AFTERLIGHT-prism-instance.zip` files for identical inputs.

- [ ] **Step 1: Write failing deterministic-artifact tests**

Create `tools/tests/test_release_artifacts.py` with these exact behaviors:

```python
REQUIRED_PRISM_TESTS = {
    "test_same_inputs_produce_byte_identical_archives",
    "test_zip_entries_are_sorted_normalized_and_path_safe",
    "test_only_bootstrap_jar_is_allowed",
    "test_instance_uses_exact_pack_url_and_loader_versions",
    "test_inspection_rejects_wrong_bootstrap_digest",
    "test_inspection_rejects_duplicate_or_parent_paths",
}
```

Implement every method named in `REQUIRED_PRISM_TESTS`. Use a temporary byte fixture as the bootstrap JAR. Assert every ZIP entry has timestamp `(1980, 1, 1, 0, 0, 0)`, Unix mode `0644`, UTF-8 flag behavior, deterministic deflate settings, and one of these exact names:

```python
EXPECTED_PRISM_NAMES = (
    ".minecraft/packwiz-installer-bootstrap.jar",
    "instance.cfg",
    "mmc-pack.json",
)
```

- [ ] **Step 2: Run the Prism tests and prove RED**

Run:

```bash
python3 -m unittest tools.tests.test_release_artifacts.PrismArtifactTests -v
```

Expected: import failure because `tools/release_artifacts.py` does not exist.

- [ ] **Step 3: Implement deterministic ZIP creation and inspection**

Implement `tools/release_artifacts.py` with Python standard-library functions for SHA-256, strict archive-name validation, normalized `ZipInfo`, JSON serialization using `sort_keys=True`, and CLI subcommands `build-prism` and `inspect-prism`.

The generated `instance.cfg` must contain:

```text
InstanceType=OneSix
name=AFTERLIGHT
iconKey=default
OverrideCommands=true
PreLaunchCommand="$INST_JAVA" -jar packwiz-installer-bootstrap.jar https://luskish.github.io/afterlight-pack/pack.toml
```

The generated `mmc-pack.json` must declare only `net.minecraft` version `1.21.1` and `net.neoforged` version `21.1.248`, with `formatVersion` equal to `1`.

- [ ] **Step 4: Rewrite the Prism shell wrapper around the exact bootstrap**

Replace the mutable `latest` URL and staging directory logic in `tools/build-prism-instance.sh` with:

```bash
BOOTSTRAP_URL="https://github.com/packwiz/packwiz-installer-bootstrap/releases/download/v${PACKWIZ_BOOTSTRAP_VERSION}/packwiz-installer-bootstrap.jar"
PACK_URL=${PACK_URL:-https://luskish.github.io/afterlight-pack/pack.toml}
OUTPUT=${OUTPUT:-dist/AFTERLIGHT-prism-instance.zip}
```

Download to a `mktemp` file, trap cleanup, verify the exact SHA-256 using `shasum -a 256` or `sha256sum`, call `python3 tools/release_artifacts.py build-prism`, and immediately call `inspect-prism`. Do not create or remove a persistent staging directory.

- [ ] **Step 5: Correct friend-facing install guidance**

Update `docs/INSTALL.md` so the recommended path is the auto-updating Prism ZIP, Java 21 and 8 to 10 GiB RAM are explicit, and both manual archives are clearly marked friends-only. Add first-launch troubleshooting for Microsoft login, Java selection, memory, Packwiz download errors, and sending Crash Assistant text to Shane.

- [ ] **Step 6: Extend tooling verification**

Add `tools/build-prism-instance.sh` and `tools/release_artifacts.py` to `tools/verify-pack.sh`. Check Bash syntax and executable mode for the shell wrapper, and run `python3 -m py_compile tools/release_artifacts.py` for the Python module.

- [ ] **Step 7: Prove deterministic production builds**

Run:

```bash
python3 -m unittest tools.tests.test_release_artifacts.PrismArtifactTests -v
OUTPUT=dist/prism-a.zip ./tools/build-prism-instance.sh
OUTPUT=dist/prism-b.zip ./tools/build-prism-instance.sh
cmp dist/prism-a.zip dist/prism-b.zip
python3 tools/release_artifacts.py inspect-prism \
  --archive dist/prism-a.zip \
  --pack-url https://luskish.github.io/afterlight-pack/pack.toml \
  --bootstrap-sha256 a8fbb24dc604278e97f4688e82d3d91a318b98efc08d5dbfcbcbcab6443d116c
```

Expected: all tests pass, `cmp` exits zero, and inspection reports exactly three entries and one approved JAR.

- [ ] **Step 8: Run the repository gates and commit Task 2**

```bash
./tools/verify-pack.sh
BOOT_TIMEOUT=600 ./tools/server-test.sh
git diff --check
git add docs/INSTALL.md tools/build-prism-instance.sh tools/release_artifacts.py tools/tests/test_release_artifacts.py tools/verify-pack.sh
git commit -m "feat(dist): build deterministic Prism instance" -m "Co-Authored-By: Codex <noreply@openai.com>"
```

---

### Task 3: Release Build and CI Gate

**Files:**
- Create: `tools/build-release.sh`
- Modify: `tools/release_artifacts.py`
- Modify: `tools/tests/test_release_artifacts.py`
- Modify: `tools/export.sh`
- Modify: `tools/verify-pack.sh`
- Modify: `.github/workflows/pack-ci.yml`
- Modify: `pack.toml`
- Modify: `index.toml`
- Modify: `docs/INSTALL.md`

**Interfaces:**
- Consumes: `DIST_DIR`, defaulting to `dist`, and `GIT_SHA`, defaulting to `git rev-parse HEAD`.
- Produces: public files `AFTERLIGHT-prism-instance.zip`, `release-metadata.json`, and `SHA256SUMS`.
- Produces: private files `AFTERLIGHT-0.9.0-rc.1.mrpack` and `AFTERLIGHT-0.9.0-rc.1-curseforge.zip` for direct sharing only.
- Produces: `scan-repository`, `inspect-friends`, `write-metadata`, and `write-checksums` CLI subcommands.

- [ ] **Step 1: Extend artifact tests and prove RED**

Add exact tests for:

```python
REQUIRED_RELEASE_POLICY_TESTS = {
    "test_friends_archive_allows_mod_jars_but_rejects_secrets",
    "test_public_file_set_contains_only_prism_metadata_and_checksums",
    "test_metadata_binds_version_commit_pack_url_size_and_sha256",
    "test_checksums_are_sorted_and_cover_only_public_files",
    "test_repository_scan_rejects_tracked_jar_secret_and_u2014",
    "test_archive_scan_rejects_absolute_parent_duplicate_and_symlink_entries",
}
```

Implement every method named in `REQUIRED_RELEASE_POLICY_TESTS` with temporary Git repositories and ZIP fixtures. Each malicious fixture must violate exactly one policy so a passing test identifies the rejected condition.

Run:

```bash
python3 -m unittest tools.tests.test_release_artifacts.ReleasePolicyTests -v
```

Expected: failures because the release-policy commands do not exist.

- [ ] **Step 2: Implement release policy and metadata functions**

Extend `tools/release_artifacts.py` so every ZIP inspection rejects absolute paths, parent traversal, duplicate names, symlink entries, encrypted members, private-key headers, and filenames containing `secret`, `token`, `credential`, `.env`, or `rcon_password` as complete path components or basename markers.

`scan-repository` must operate on `git ls-files -z`, reject tracked `.jar` files, reject U+2014 bytes, reject private-key headers, and reject tracked runtime paths under `dist/`, `server-test/`, `server/data/`, or `server/backups/`.

`release-metadata.json` must use stable sorted JSON and this schema:

```json
{
  "format": 1,
  "version": "0.9.0-rc.1",
  "git_sha": "0123456789abcdef0123456789abcdef01234567",
  "minecraft": "1.21.1",
  "neoforge": "21.1.248",
  "pack_url": "https://luskish.github.io/afterlight-pack/pack.toml",
  "public_artifacts": {
    "AFTERLIGHT-prism-instance.zip": {
      "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
      "size": 1
    }
  },
  "private_artifacts": [
    "AFTERLIGHT-0.9.0-rc.1-curseforge.zip",
    "AFTERLIGHT-0.9.0-rc.1.mrpack"
  ]
}
```

The test fixture may use size `1`; production metadata records the real positive size.

- [ ] **Step 3: Make export and release output directories explicit**

Change `tools/export.sh` to honor `DIST_DIR=${DIST_DIR:-dist}` and write both private archives there. Create executable `tools/build-release.sh` that:

```text
1. runs scan-repository
2. builds and inspects the Prism ZIP
3. runs export.sh into the same output directory
4. inspects both private archives for path and secret safety
5. writes release-metadata.json
6. writes sorted SHA256SUMS for only the three public files
7. prints PUBLIC and FRIENDS-ONLY file lists separately
```

The checksum file includes the Prism ZIP and `release-metadata.json`; it must not include itself or either private archive.

- [ ] **Step 4: Set the release-candidate pack version**

Run:

```bash
source tools/versions.env && export PATH="$PATH_EXTRA:$PATH"
python3 - <<'PY'
from pathlib import Path
path = Path("pack.toml")
text = path.read_text(encoding="utf-8")
old = 'version = "0.1.0"'
new = 'version = "0.9.0-rc.1"'
if text.count(old) != 1:
    raise SystemExit("unexpected pack version")
path.write_text(text.replace(old, new), encoding="utf-8")
PY
packwiz refresh
```

Review `pack.toml`, `index.toml`, and `mods/` together. Confirm no gameplay content or mod version changed.

- [ ] **Step 5: Expand the CI workflow**

Update `.github/workflows/pack-ci.yml` to run, in this order:

```text
checkout pinned by full SHA
Temurin Java 21 setup pinned by full SHA
Go setup pinned by full SHA
Packwiz install pinned to dfd8b68a4796c763e25bad50265ea1f1233e24f1
python3 -m unittest discover -s tools/tests -p test_*.py -v
./tools/verify-pack.sh
BOOT_TIMEOUT=600 ./tools/server-test.sh
Docker Compose config with temporary data, backup, secret, and env paths
shellcheck for every tracked .sh file
./tools/build-release.sh
git diff --exit-code
git status --porcelain --untracked-files=all must be empty
upload public release files on success
upload server-test/evidence on failure
```

The success upload path must list only:

```yaml
path: |
  dist/AFTERLIGHT-prism-instance.zip
  dist/release-metadata.json
  dist/SHA256SUMS
```

Do not upload a directory wildcard.

- [ ] **Step 6: Run focused release checks**

Run:

```bash
python3 -m unittest tools.tests.test_release_artifacts -v
./tools/build-release.sh
python3 tools/release_artifacts.py scan-repository --root .
python3 tools/release_artifacts.py inspect-prism --archive dist/AFTERLIGHT-prism-instance.zip --pack-url https://luskish.github.io/afterlight-pack/pack.toml --bootstrap-sha256 "$PACKWIZ_BOOTSTRAP_SHA256"
python3 tools/release_artifacts.py inspect-friends --archive dist/AFTERLIGHT-0.9.0-rc.1.mrpack
python3 tools/release_artifacts.py inspect-friends --archive dist/AFTERLIGHT-0.9.0-rc.1-curseforge.zip
```

Expected: tests and inspections pass, public output is exactly three files, and both embedded-JAR archives are explicitly reported friends-only.

- [ ] **Step 7: Run full gates and commit Task 3**

```bash
python3 -m unittest discover -s tools/tests -p 'test_*.py' -v
./tools/verify-pack.sh
BOOT_TIMEOUT=600 ./tools/server-test.sh
git diff --check
git add .github/workflows/pack-ci.yml docs/INSTALL.md pack.toml index.toml mods/ tools/build-release.sh tools/export.sh tools/release_artifacts.py tools/tests/test_release_artifacts.py tools/verify-pack.sh
git commit -m "feat(release): add friend release pipeline" -m "Co-Authored-By: Codex <noreply@openai.com>"
```

---

### Task 4: Practical Gauntlet and Prerelease

**Files:**
- Create: `tools/release-gauntlet.sh`
- Create: `tools/tests/test_release_gauntlet.py`
- Create: `docs/RELEASING.md`
- Create: `docs/releases/0.9.0-rc.1.md`
- Modify: `tools/verify-pack.sh`

**Interfaces:**
- Consumes: one exact 40-character commit SHA reachable from the local repository.
- Produces: `dist/gauntlet/$SHA/public/` for the three public files, `dist/gauntlet/$SHA/friends-only/` for the two private archives, and `dist/gauntlet/$SHA/gauntlet.txt` for the command transcript and SHA-256 evidence.
- Produces: a public GitHub prerelease `v0.9.0-rc.1` containing only the Prism ZIP, `release-metadata.json`, and `SHA256SUMS`.

- [ ] **Step 1: Write failing gauntlet contract tests**

Create `tools/tests/test_release_gauntlet.py` with fake executables and exact tests:

```python
REQUIRED_GAUNTLET_TESTS = {
    "test_rejects_dirty_tree_noncommit_and_nonhead_sha",
    "test_creates_detached_worktree_for_exact_sha",
    "test_runs_tests_verify_boot_compose_shellcheck_and_two_builds_in_order",
    "test_compares_two_prism_archives_byte_for_byte",
    "test_failure_stops_before_copying_accepted_artifacts",
    "test_success_copies_public_and_private_outputs_with_transcript",
    "test_cleanup_removes_only_the_temporary_worktree",
}
```

Implement every method named in `REQUIRED_GAUNTLET_TESTS`. Each fake command must append one canonical line to a shared log so tests can compare the complete execution order.

Run:

```bash
python3 -m unittest tools.tests.test_release_gauntlet -v
```

Expected: failure because `tools/release-gauntlet.sh` does not exist.

- [ ] **Step 2: Implement the detached-SHA gauntlet**

Create executable `tools/release-gauntlet.sh` with an outer controller and an `AFTERLIGHT_GAUNTLET_INNER=1` worker path.

The outer controller must require a clean tree and exact `HEAD`, create a temporary detached worktree at the requested SHA, set a cleanup trap scoped to that temporary path, and invoke the inner worker. The inner worker must run:

```bash
python3 -m unittest discover -s tools/tests -p 'test_*.py' -v
./tools/verify-pack.sh
BOOT_TIMEOUT=600 ./tools/server-test.sh
docker compose --project-name afterlight-gauntlet --env-file "$GAUNTLET_ENV" -f server/docker-compose.yml config --quiet
shellcheck $(git ls-files '*.sh')
DIST_DIR="$FIRST" GIT_SHA="$SHA" ./tools/build-release.sh
DIST_DIR="$SECOND" GIT_SHA="$SHA" ./tools/build-release.sh
cmp "$FIRST/AFTERLIGHT-prism-instance.zip" "$SECOND/AFTERLIGHT-prism-instance.zip"
git diff --exit-code
test -z "$(git status --porcelain --untracked-files=all)"
```

Only after every command passes may it copy the Prism ZIP, metadata, and checksums into `dist/gauntlet/$SHA/public/`; copy the `.mrpack` and CurseForge ZIP into `dist/gauntlet/$SHA/friends-only/`; and write `dist/gauntlet/$SHA/gauntlet.txt`. The transcript must state the exact SHA, UTC start and finish times, Java version, Packwiz version, pack version, Minecraft version, NeoForge version, Prism SHA-256, pack SHA-256, and index SHA-256.

- [ ] **Step 3: Document exact promotion and rollback commands**

Write `docs/RELEASING.md` with these checked transitions:

```bash
SHA=$(git rev-parse HEAD)
./tools/release-gauntlet.sh "$SHA"
git push origin dev
DEV_RUN_ID=$(gh run list --workflow pack-ci --branch dev --commit "$SHA" --limit 1 --json databaseId --jq '.[0].databaseId')
gh run watch "$DEV_RUN_ID" --exit-status
git switch main
git merge --ff-only "$SHA"
git push origin main
MAIN_RUN_ID=$(gh run list --workflow pack-ci --branch main --commit "$SHA" --limit 1 --json databaseId --jq '.[0].databaseId')
gh run watch "$MAIN_RUN_ID" --exit-status
curl -fsSL https://luskish.github.io/afterlight-pack/pack.toml | shasum -a 256
curl -fsSL https://luskish.github.io/afterlight-pack/index.toml | shasum -a 256
git tag -a v0.9.0-rc.1 "$SHA" -m "AFTERLIGHT 0.9.0-rc.1"
git push origin v0.9.0-rc.1
gh release create v0.9.0-rc.1 --prerelease --title "AFTERLIGHT 0.9.0-rc.1" --notes-file docs/releases/0.9.0-rc.1.md dist/gauntlet/$SHA/public/AFTERLIGHT-prism-instance.zip dist/gauntlet/$SHA/public/release-metadata.json dist/gauntlet/$SHA/public/SHA256SUMS
git switch dev
```

Add recovery instructions that never force-push: if `main` CI fails, leave the tag unpublished, switch back to `dev`, fix forward, rerun the gauntlet, and promote a new SHA.

- [ ] **Step 4: Create the release evidence template with factual boundaries**

Write `docs/releases/0.9.0-rc.1.md` with sections for delivered pack content, exact automated commands, local gauntlet SHA, `dev` CI URL, `main` CI URL, Pages hashes, public artifacts, friends-only artifacts, known boundaries, and manual acceptance. Mark each manual item `NOT RUN` until observed:

```text
Microsoft-authenticated Prism launch
title screen under three minutes on Shane's PC
quest-book rendering and theme
dedicated-server login from the released Prism artifact
two-player Simple Voice Chat
router forwarding and host firewall
backup restore on the real host
```

- [ ] **Step 5: Extend verification and run focused tests**

Add `tools/release-gauntlet.sh` to the Bash syntax and executable checks in `tools/verify-pack.sh`, then run:

```bash
python3 -m unittest tools.tests.test_release_gauntlet -v
bash -n tools/release-gauntlet.sh
shellcheck tools/release-gauntlet.sh
python3 -m unittest discover -s tools/tests -p 'test_*.py' -v
```

Expected: all focused and repository tests pass.

- [ ] **Step 6: Commit Task 4 and request fresh review**

```bash
git add docs/RELEASING.md docs/releases/0.9.0-rc.1.md tools/release-gauntlet.sh tools/tests/test_release_gauntlet.py tools/verify-pack.sh
git commit -m "feat(release): add practical release gauntlet" -m "Co-Authored-By: Codex <noreply@openai.com>"
```

Use `superpowers:requesting-code-review` against the complete Task 1 through Task 4 diff. Fix every confirmed Critical or Important finding through `superpowers:receiving-code-review`, rerun focused tests, and commit corrections before the final gate.

- [ ] **Step 7: Run the final local release gauntlet**

Run:

```bash
SHA=$(git rev-parse HEAD)
./tools/release-gauntlet.sh "$SHA"
```

Expected: the detached worker completes every test, prints `VERIFY: ALL GREEN` and `SERVER BOOT: OK`, proves byte-identical Prism archives, leaves the controller tree clean, and writes accepted output under `dist/gauntlet/$SHA/`.

- [ ] **Step 8: Promote exact SHA and require both CI runs**

Push exact `SHA` to `dev`, wait for green `pack-ci`, fast-forward `main` to that same `SHA`, push, and wait for green `pack-ci` on `main`. Do not merge a different commit and do not accept a rerun from a different SHA.

- [ ] **Step 9: Verify Pages parity and publish the prerelease**

Compare local and GitHub Pages bytes for `pack.toml` and `index.toml`. After exact parity, create and push annotated tag `v0.9.0-rc.1`, then create the GitHub prerelease with only the three public files. Query the published release assets and fail if either `.mrpack` or `curseforge.zip` appears.

- [ ] **Step 10: Record evidence and return to dev**

Fill only the automated evidence fields in `docs/releases/0.9.0-rc.1.md`, leave all player-facing observations `NOT RUN`, commit the evidence on `dev`, push `dev`, and require green docs-only CI. End on `dev` with a clean tree, `main` and the tag on the accepted release SHA, and the deferred hardening worktree untouched.

```bash
git add docs/releases/0.9.0-rc.1.md
git commit -m "docs(release): record 0.9.0-rc.1 evidence" -m "Co-Authored-By: Codex <noreply@openai.com>"
git push origin dev
```
