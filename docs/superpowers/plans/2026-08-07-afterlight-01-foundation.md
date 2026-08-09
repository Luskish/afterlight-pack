# AFTERLIGHT Plan 01: Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A bootable, exportable, auto-update-ready AFTERLIGHT pack skeleton: packwiz repo with the performance/ops mod baseline, verified headless NeoForge server boot, `.mrpack`/CurseForge export pipeline, CI workflow, and the friend-facing Prism auto-update instance artifact.

**Architecture:** Pack-as-code packwiz repo (this git repo is the pack source; no jars committed). Mods resolved from Modrinth/CurseForge into per-mod `.pw.toml` metadata with locked hashes. Verification = `packwiz refresh` integrity + a pure-Java headless server boot harness (no Docker dependency on this Mac; Docker enters in Plan 07 for the VPS). Distribution artifacts generated from the same source.

**Tech Stack:** packwiz (Go CLI), Temurin JDK 21, NeoForge 1.21.1 (21.1.x), Modrinth/CurseForge APIs, GitHub Actions (files authored now, activated when remote exists), Prism Launcher instance format + packwiz-installer-bootstrap.

## Global Constraints

- Minecraft **1.21.1**, loader **NeoForge 21.1.x**, **Java 21** (Temurin): from spec §3
- Pack name: **AFTERLIGHT**; pack author: **Shane + ECHO**; repo = pack root (spec §8)
- **No mod jars in git**: only packwiz TOML metadata, configs, scripts, quest files (spec §8)
- Every mod gets a correct `side` (`client`/`server`/`both`) at add time (spec §8)
- Licensing hygiene: mods fetched from official CurseForge/Modrinth only, no rehosting (spec §8)
- All shell commands run from repo root `/Users/shaneliszewski/MinecraftTest` unless stated
- Machine state discovered 2026-08-07: Homebrew 6.0.13 present; **no packwiz, no Go, no Docker, no JDK** (`/usr/bin/java` is the macOS stub). Task 1 fixes this.
- Commit after every task (and at marked mid-task points); message style: `feat(scope): what` / `chore(scope): what`, ending with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`

## The AFTERLIGHT plan suite (this is 01)

| Plan | Deliverable | Status |
|---|---|---|
| **01 Foundation (this plan)** | Bootable skeleton, exports, CI files, Prism artifact | ← executing |
| 02 Full Roster & Configs | ~320-mod manifest in category waves, config normalization, AlmostUnified | after 01 |
| 03 Integration Layer | KubeJS stages/bridges/loot, Requisition items, Gate multiblocks (MMR) | after 02 |
| 04 Quest Framework & Act I | FTB Quests skeleton, ECHO voice guide, ch 1–4, Certifications I, Depot | after 03 |
| 05 Acts II–III & Side Groups | ch 5–16, Undercurrent, Deep Vault, Atlas chapters | after 04 |
| 06 Act IV & Finale | ch 17–20, Gate of Return chain, postgame | after 05 |
| 07 VPS & Launch | Docker compose for the VPS, GitHub Pages hosting live, AutoModpack, pregen, backups, ch 1–8 launch checklist | after 04+ |

Each plan starts from a green state of the previous one and independently ends green.

---

### Task 1: Toolchain bootstrap (packwiz + JDK 21)

**Files:**
- Create: `tools/versions.env` (single source of truth for tool/loader versions)

**Interfaces:**
- Produces: working `packwiz` on PATH; `java -version` reporting Temurin 21; `tools/versions.env` defining `MC_VERSION=1.21.1`, `NEOFORGE_VERSION` (resolved in Step 4), consumed by every later task's scripts.

- [ ] **Step 1: Install JDK 21 (Temurin) via Homebrew**

```bash
brew install --cask temurin@21
```

Expected: cask installs. If it errors with "already installed", fine.

- [ ] **Step 2: Verify Java 21 resolves**

```bash
export JAVA_HOME=$(/usr/libexec/java_home -v 21)
"$JAVA_HOME/bin/java" -version
```

Expected: output contains `Temurin-21`. If `/usr/libexec/java_home -v 21` fails, run `ls /Library/Java/JavaVirtualMachines/` and use the temurin-21 path directly. Do not proceed until a real Java 21 prints a version.

- [ ] **Step 3: Install packwiz (brew first, Go fallback)**

```bash
brew install packwiz || (brew install go && go install github.com/packwiz/packwiz@latest && echo 'PATH fallback: ~/go/bin' && export PATH="$HOME/go/bin:$PATH")
packwiz --help | head -5
```

Expected: `packwiz --help` prints the command list (packwiz has no `--version` flag; help output is the health check). If the brew formula doesn't exist, the Go path must succeed; add `export PATH="$HOME/go/bin:$PATH"` to any later shell that can't find packwiz.

- [ ] **Step 4: Resolve current NeoForge 1.21.1 version and write versions.env**

```bash
curl -s https://maven.neoforged.net/api/maven/latest/version/releases/net/neoforged/neoforge?filter=21.1 > /tmp/nf_version.txt
cat /tmp/nf_version.txt
```

Expected: a version string like `21.1.209` (any `21.1.x`). Then create `tools/versions.env` with the actual value substituted:

```bash
mkdir -p tools
cat > tools/versions.env <<EOF
MC_VERSION=1.21.1
NEOFORGE_VERSION=$(cat /tmp/nf_version.txt)
EOF
cat tools/versions.env
```

Expected: file shows both values, NEOFORGE_VERSION non-empty. If the maven API call fails, fetch https://projects.neoforged.net/neoforged/neoforge in a browser-capable tool and take the latest 21.1.x release number.

- [ ] **Step 5: Commit**

```bash
git add tools/versions.env
git commit -m "chore(toolchain): pin MC/NeoForge versions, bootstrap tooling

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: packwiz pack init + repo hygiene

**Files:**
- Create: `pack.toml`, `index.toml` (via packwiz)
- Create: `.gitignore`, `.packwizignore`, `README.md`
- Create: `config/.gitkeep`, `kubejs/startup_scripts/.gitkeep`, `kubejs/server_scripts/.gitkeep`, `kubejs/client_scripts/.gitkeep`

**Interfaces:**
- Consumes: `tools/versions.env` (Task 1)
- Produces: valid packwiz pack at repo root: `pack.toml` with `[versions] minecraft="1.21.1"`, `neoforge="<21.1.x>"`; `packwiz refresh` green. All later `packwiz` commands depend on this.

- [ ] **Step 1: Initialize the pack non-interactively**

```bash
source tools/versions.env
packwiz init --name "AFTERLIGHT" --author "Shane + ECHO" --version "0.1.0" --mc-version "$MC_VERSION" --modloader neoforge --neoforge-version "$NEOFORGE_VERSION" -r .
```

Expected: `pack.toml` and `index.toml` created at repo root. If flag names differ on the installed packwiz build (check `packwiz init --help`), map them (`--fabric-version`-style flags exist per loader; NeoForge's is `--neoforge-version`): the four required outcomes are name, MC version, neoforge version, pack version in `pack.toml`.

- [ ] **Step 2: Verify pack.toml contents**

```bash
cat pack.toml
packwiz refresh
```

Expected: `pack.toml` shows `name = "AFTERLIGHT"`, `[versions]` block with `minecraft = "1.21.1"` and `neoforge = "<value from versions.env>"`. `packwiz refresh` exits 0 and rewrites `index.toml`.

- [ ] **Step 3: Write .gitignore**

```bash
cat > .gitignore <<'EOF'
# Local dev instance / runtime junk: never pack source
.DS_Store
*.log
run/
server-test/
.packwiz-cache/
EOF
```

- [ ] **Step 4: Write .packwizignore (controls what ships in exports)**

```bash
cat > .packwizignore <<'EOF'
# Repo/dev files that must not ship inside the pack export
.git/**
.gitignore
.github/**
docs/**
tools/**
README.md
skills-lock.json
.agents/**
.claude/**
server-test/**
EOF
packwiz refresh
```

Expected: refresh green; `index.toml` does NOT list docs/tools/repo files (spot-check with `grep -c "docs/" index.toml` → `0`).

- [ ] **Step 5: Write README skeleton with real content**

```bash
cat > README.md <<'EOF'
# AFTERLIGHT

A story-driven kitchen-sink modpack for Minecraft NeoForge 1.21.1.
You aren't discovering technology: you're remembering it.

- **Design spec:** docs/superpowers/specs/2026-08-07-afterlight-modpack-design.md
- **Pack source:** this repo is a [packwiz](https://packwiz.infra.link/) pack; mods are TOML metadata under `mods/`, no jars in git.
- **Players:** see docs/INSTALL.md (created in Plan 01 Task 7) for the auto-updating Prism instance.
- **Dev loop:** `packwiz serve` + a Prism dev instance; `tools/server-test.sh` for headless server verification.

## Layout
- `pack.toml` / `index.toml`: packwiz manifest
- `mods/`: one `.pw.toml` per mod
- `config/`, `defaultconfigs/`: shipped configuration
- `kubejs/`: startup/server/client scripts (integration layer)
- `config/ftbquests/`: quest book source (from Plan 04)
- `tools/`: dev/test scripts (not shipped)
- `docs/`: specs, plans, player docs (not shipped)
EOF
mkdir -p config kubejs/startup_scripts kubejs/server_scripts kubejs/client_scripts
touch config/.gitkeep kubejs/startup_scripts/.gitkeep kubejs/server_scripts/.gitkeep kubejs/client_scripts/.gitkeep
```

- [ ] **Step 6: Commit**

```bash
git add pack.toml index.toml .gitignore .packwizignore README.md config kubejs
git commit -m "feat(pack): init AFTERLIGHT packwiz pack on NeoForge 1.21.1

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: Performance & ops mod baseline

**Files:**
- Create (via packwiz): `mods/*.pw.toml` for: sodium, iris, lithium, modernfix, ferritecore, entityculling, clumps, packet-fixer, crash-assistant, spark, chunky, servercore

**Interfaces:**
- Consumes: green pack from Task 2
- Produces: 12 baseline mods with correct sides in `mods/`; `packwiz refresh` green. Task 6's server boot uses the server-side subset of exactly these.

- [ ] **Step 1: Add client-side performance mods (side=client)**

```bash
for slug in sodium iris entityculling crash-assistant; do packwiz mr add "$slug" -y || packwiz mr add "$slug"; done
```

Expected: four `mods/<slug>.pw.toml` files created, each resolving a `mc1.21.1`-compatible NeoForge file. If a slug is ambiguous/not found, run `packwiz mr add <slug>` without `-y` and select the correct project by name (project names: Sodium, Iris Shaders, Entity Culling, Crash Assistant).

- [ ] **Step 2: Mark pure-client mods as client side**

For each of `sodium`, `iris`, `entityculling`, `crash-assistant`: edit `mods/<slug>.pw.toml`, set the `side` field:

```toml
side = "client"
```

(packwiz writes `side = "both"` by default unless the platform metadata says otherwise; verify each file and correct.)

- [ ] **Step 3: Add both-sides performance/ops mods**

```bash
for slug in lithium modernfix ferritecore clumps packet-fixer spark; do packwiz mr add "$slug" -y || packwiz mr add "$slug"; done
```

Expected: six more `.pw.toml` files; these stay `side = "both"`.

- [ ] **Step 4: Add server-side ops mods (side=server)**

```bash
for slug in chunky servercore; do packwiz mr add "$slug" -y || packwiz mr add "$slug"; done
```

Then edit `mods/chunky.pw.toml` and `mods/servercore.pw.toml` to `side = "server"`. (Chunky has client builds but we ship it for VPS pregen; ServerCore is server-only by design.)

- [ ] **Step 5: Verify manifest integrity + version sanity**

```bash
packwiz refresh
ls mods/ | wc -l
grep -H "filename" mods/*.pw.toml
```

Expected: refresh exits 0; 12 files; every `filename` contains `1.21.1` or `neoforge` (eyeball for accidental Fabric files: filenames with `fabric` and no `neoforge` are wrong; re-add with explicit version selection if so).

- [ ] **Step 6: Commit**

```bash
git add mods index.toml pack.toml
git commit -m "feat(mods): performance and ops baseline (12 mods, sided)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: QoL baseline + dependency-resolution proof

**Files:**
- Create (via packwiz): `mods/*.pw.toml` for: jei, jade, journeymap, waystones, corpse, appleskin, mouse-tweaks, sophisticated-backpacks (+ auto-resolved deps, e.g. sophisticated-core, balm)

**Interfaces:**
- Consumes: Task 3 state
- Produces: ~8–11 more mods incl. transitively-resolved dependencies; proves packwiz dep resolution works before Plan 02 adds 300 more.

- [ ] **Step 1: Add the QoL set**

```bash
for slug in jei jade journeymap waystones corpse appleskin mouse-tweaks sophisticated-backpacks; do packwiz mr add "$slug" -y || packwiz mr add "$slug"; done
```

Expected: waystones pulls `balm` automatically; sophisticated-backpacks pulls `sophisticated-core`. If packwiz prompts about a required dependency, accept it.

- [ ] **Step 2: Verify dependencies landed**

```bash
ls mods/
packwiz refresh
```

Expected: `balm.pw.toml` and `sophisticated-core.pw.toml` present (names may vary slightly: any file for those projects counts). Refresh green. If deps are missing, add explicitly: `packwiz mr add balm -y`, `packwiz mr add sophisticated-core -y`.

- [ ] **Step 3: Commit**

```bash
git add mods index.toml
git commit -m "feat(mods): QoL baseline + dependency resolution proven

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: Export pipeline (.mrpack + CurseForge zip)

**Files:**
- Create: `tools/export.sh`
- Output (untracked): `dist/AFTERLIGHT-<version>.mrpack`, `dist/AFTERLIGHT-<version>-curseforge.zip`

**Interfaces:**
- Consumes: green manifest (Task 4)
- Produces: `tools/export.sh`: later plans and CI call exactly this script; emits both artifacts into `dist/` and prints their paths.

- [ ] **Step 1: Write tools/export.sh**

```bash
mkdir -p tools
cat > tools/export.sh <<'EOF'
#!/usr/bin/env bash
# Export AFTERLIGHT distribution artifacts from the packwiz source.
set -euo pipefail
cd "$(dirname "$0")/.."
VERSION=$(grep '^version' pack.toml | head -1 | sed 's/.*"\(.*\)"/\1/')
mkdir -p dist
packwiz refresh
packwiz mr export -o "dist/AFTERLIGHT-${VERSION}.mrpack"
packwiz cf export -o "dist/AFTERLIGHT-${VERSION}-curseforge.zip"
echo "Artifacts:"
ls -lh dist/
EOF
chmod +x tools/export.sh
```

- [ ] **Step 2: Add dist/ to .gitignore**

Edit `.gitignore`, append:

```
dist/
```

- [ ] **Step 3: Run the export and verify artifact structure**

```bash
./tools/export.sh
unzip -l dist/AFTERLIGHT-0.1.0.mrpack | head -20
```

Expected: both files exist and are non-trivially sized (>1 KB); mrpack listing shows `modrinth.index.json`. If `packwiz cf export` fails because some mod is Modrinth-only, that is acceptable at this stage: note which mod, and re-run with `packwiz mr export` only; the CF-lane fix (side-loading Modrinth-only files) is handled in Plan 07. The mrpack MUST succeed.

- [ ] **Step 4: Commit**

```bash
git add tools/export.sh .gitignore
git commit -m "feat(dist): mrpack + curseforge export pipeline

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 6: Headless server boot harness (the pack's integration test)

**Files:**
- Create: `tools/server-test.sh`
- Output (untracked): `server-test/` scratch server

**Interfaces:**
- Consumes: `tools/versions.env`, green manifest, packwiz-installer-bootstrap jar (downloaded by script)
- Produces: `tools/server-test.sh`: exits 0 iff a NeoForge server with the pack's server-side mods reaches "Done" within timeout. This IS the pack's smoke test forever after (CI reuses it; every later plan's definition of green includes it).

- [ ] **Step 1: Write tools/server-test.sh**

```bash
cat > tools/server-test.sh <<'EOF'
#!/usr/bin/env bash
# Headless AFTERLIGHT server boot test. Pure JVM: no Docker required.
# Exit 0 = server booted to "Done" and stopped cleanly. Nonzero = failure; see server-test/logs/.
set -euo pipefail
cd "$(dirname "$0")/.."
source tools/versions.env
JAVA_HOME=${JAVA_HOME:-$(/usr/libexec/java_home -v 21)}
JAVA="$JAVA_HOME/bin/java"
BOOTSTRAP_URL="https://github.com/packwiz/packwiz-installer-bootstrap/releases/latest/download/packwiz-installer-bootstrap.jar"
DIR=server-test
BOOT_TIMEOUT=${BOOT_TIMEOUT:-420}

rm -rf "$DIR" && mkdir -p "$DIR"

# 1) Serve the working-dir pack locally
packwiz serve --port 8199 & SERVE_PID=$!
trap 'kill $SERVE_PID 2>/dev/null || true' EXIT
sleep 2

# 2) Install NeoForge server
curl -sL -o "$DIR/neoforge-installer.jar" "https://maven.neoforged.net/releases/net/neoforged/neoforge/${NEOFORGE_VERSION}/neoforge-${NEOFORGE_VERSION}-installer.jar"
(cd "$DIR" && "$JAVA" -jar neoforge-installer.jar --install-server . > installer.log 2>&1)

# 3) Install the pack's server side via packwiz-installer
curl -sL -o "$DIR/packwiz-installer-bootstrap.jar" "$BOOTSTRAP_URL"
(cd "$DIR" && "$JAVA" -jar packwiz-installer-bootstrap.jar -g -s server "http://localhost:8199/pack.toml" > packwiz-install.log 2>&1)

# 4) Boot headless with a watchdog, EULA accepted for local test only
echo "eula=true" > "$DIR/eula.txt"
echo "level-seed=afterlight-ci" > "$DIR/server.properties"
(cd "$DIR" && (echo "stop" | timeout "$BOOT_TIMEOUT" ./run.sh nogui > boot.log 2>&1 || true))

# 5) Verdict
if grep -q 'Done (' "$DIR"/boot.log || grep -rq 'Done (' "$DIR"/logs/ 2>/dev/null; then
  echo "SERVER BOOT: OK"
  exit 0
else
  echo "SERVER BOOT: FAILED: tail of boot.log:"
  tail -50 "$DIR/boot.log" || true
  exit 1
fi
EOF
chmod +x tools/server-test.sh
```

Note on the `echo "stop" |` pipe: NeoForge's `run.sh` reads console from stdin; piping `stop` makes the server shut down immediately after finishing boot, so the test is self-terminating. `timeout` is the watchdog if boot hangs. macOS ships no `timeout`: if `command -v timeout` is empty, `brew install coreutils` and use `gtimeout` (adjust the script accordingly at execution time and keep the adjusted version).

- [ ] **Step 2: Run the harness: expect it to FAIL first on macOS timeout**

```bash
command -v timeout || echo "NO timeout binary"
```

Expected: likely `NO timeout binary` → install and patch:

```bash
brew install coreutils
sed -i '' 's/timeout "\$BOOT_TIMEOUT"/gtimeout "$BOOT_TIMEOUT"/' tools/server-test.sh
```

- [ ] **Step 3: Run the harness for real**

```bash
./tools/server-test.sh
```

Expected: `SERVER BOOT: OK`, exit 0, within ~3–7 min (first run downloads libraries). If FAILED: read `server-test/boot.log` tail printed by the script: the two likely causes at this stage are (a) a client-side mod leaked into the server install (fix: correct that mod's `side` in `mods/*.pw.toml`, refresh, rerun) or (b) NeoForge/Java mismatch (verify `java -version` is 21 and NEOFORGE_VERSION is a real 21.1.x). Iterate until OK: do not proceed on red.

- [ ] **Step 4: Commit**

```bash
git add tools/server-test.sh
git commit -m "feat(ci): headless server boot harness (pure-JVM smoke test)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 7: CI workflow + Prism auto-update instance + player docs

**Files:**
- Create: `.github/workflows/pack-ci.yml`
- Create: `tools/build-prism-instance.sh`
- Create: `docs/INSTALL.md`
- Output (untracked): `dist/AFTERLIGHT-prism-instance.zip`

**Interfaces:**
- Consumes: `tools/export.sh` (Task 5), `tools/server-test.sh` (Task 6), `tools/versions.env` (Task 1)
- Produces: CI that runs refresh-check → exports → server smoke on every push (activates once a GitHub remote exists); a Prism instance zip whose pre-launch hook auto-syncs from `PACK_URL`; `docs/INSTALL.md` for friends. **`PACK_URL` is a parameter**: set to the real GitHub Pages URL at the user checkpoint below; until then the local build uses a placeholder value the script requires explicitly.

- [ ] **Step 1: Write the CI workflow**

```bash
mkdir -p .github/workflows
cat > .github/workflows/pack-ci.yml <<'EOF'
name: pack-ci
on:
  push:
    branches: [main]
  pull_request:
jobs:
  verify-and-export:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with: { distribution: temurin, java-version: "21" }
      - uses: actions/setup-go@v5
        with: { go-version: stable }
      - name: Install packwiz
        run: go install github.com/packwiz/packwiz@latest && echo "$HOME/go/bin" >> "$GITHUB_PATH"
      - name: Manifest integrity
        run: |
          packwiz refresh
          git diff --exit-code index.toml pack.toml || (echo "::error::index.toml drifted: run packwiz refresh and commit" && exit 1)
      - name: Export artifacts
        run: ./tools/export.sh
      - name: Headless server boot smoke test
        run: BOOT_TIMEOUT=600 ./tools/server-test.sh
      - uses: actions/upload-artifact@v4
        with:
          name: afterlight-dist
          path: dist/
EOF
```

(Linux runners have real `timeout`; the harness's `gtimeout` patch from Task 6 Step 2 must therefore guard by availability. At execution time make the script use `command -v gtimeout || command -v timeout`: one line: `TIMEOUT_BIN=$(command -v gtimeout || command -v timeout)` and call `"$TIMEOUT_BIN"`. Apply this now if Task 6 hardcoded gtimeout, and re-run `./tools/server-test.sh` to confirm still OK.)

- [ ] **Step 2: Write tools/build-prism-instance.sh**

```bash
cat > tools/build-prism-instance.sh <<'EOF'
#!/usr/bin/env bash
# Build the friend-facing auto-updating Prism instance zip.
# Usage: PACK_URL=https://<user>.github.io/<repo>/pack.toml ./tools/build-prism-instance.sh
set -euo pipefail
cd "$(dirname "$0")/.."
source tools/versions.env
: "${PACK_URL:?Set PACK_URL to the hosted pack.toml URL (GitHub Pages) before building}"
BOOTSTRAP_URL="https://github.com/packwiz/packwiz-installer-bootstrap/releases/latest/download/packwiz-installer-bootstrap.jar"
STAGE=dist/prism-instance
rm -rf "$STAGE" && mkdir -p "$STAGE/.minecraft"

curl -sL -o "$STAGE/.minecraft/packwiz-installer-bootstrap.jar" "$BOOTSTRAP_URL"

cat > "$STAGE/instance.cfg" <<CFG
InstanceType=OneSix
name=AFTERLIGHT
iconKey=default
OverrideCommands=true
PreLaunchCommand="\$INST_JAVA" -jar packwiz-installer-bootstrap.jar ${PACK_URL}
CFG

cat > "$STAGE/mmc-pack.json" <<JSON
{
  "components": [
    { "uid": "net.minecraft", "version": "${MC_VERSION}", "important": true },
    { "uid": "net.neoforged", "version": "${NEOFORGE_VERSION}" }
  ],
  "formatVersion": 1
}
JSON

(cd "$STAGE" && zip -qr ../AFTERLIGHT-prism-instance.zip .)
echo "Built dist/AFTERLIGHT-prism-instance.zip (pack URL: ${PACK_URL})"
EOF
chmod +x tools/build-prism-instance.sh
```

- [ ] **Step 3: Test-build the instance zip with a placeholder URL and verify structure**

```bash
PACK_URL="https://example.invalid/pack.toml" ./tools/build-prism-instance.sh
unzip -l dist/AFTERLIGHT-prism-instance.zip
```

Expected: zip contains `instance.cfg`, `mmc-pack.json`, `.minecraft/packwiz-installer-bootstrap.jar`; `instance.cfg` shows the PreLaunchCommand line. (This placeholder build proves the tool; the shippable build happens at the checkpoint below with the real URL.)

- [ ] **Step 4: Write docs/INSTALL.md**

```bash
cat > docs/INSTALL.md <<'EOF'
# Playing AFTERLIGHT

## The recommended way (auto-updating, ~5 minutes, once)
1. Install [Prism Launcher](https://prismlauncher.org/download/) and sign in with your Microsoft account.
2. Install Java 21 (Temurin) if Prism asks for it: Prism can auto-download Java: Settings → Java → auto-detect.
3. Get `AFTERLIGHT-prism-instance.zip` from Shane.
4. Prism → Add Instance → Import → pick the zip → OK.
5. Launch. First launch downloads the whole pack (a few GB); every later launch auto-syncs to Shane's latest version. You never update manually.
6. Give the instance 8–10 GB RAM: instance → Edit → Settings → Memory → 8192–10240 MB.

## The old-school way (manual zips)
1. Get the latest `AFTERLIGHT-<version>.mrpack` from Shane.
2. Prism (or Modrinth App / any mrpack-capable launcher) → Add Instance → Import → pick the file.
3. When Shane ships an update, re-import the new file (your worlds/options survive: they live in the instance, not the pack).

## Joining the server
Server address comes from Shane. Simple Voice Chat works out of the box: press V for voice settings.

## If your game crashes
The pack includes Crash Assistant: it pops a window with the crash report. Send Shane the "Copy to clipboard" output, not a screenshot.
EOF
```

- [ ] **Step 5: Commit**

```bash
git add .github tools/build-prism-instance.sh docs/INSTALL.md
git commit -m "feat(dist): CI workflow, Prism auto-update instance builder, player install docs

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

- [ ] **Step 6: USER CHECKPOINT: GitHub remote + Pages (needs Shane's account decisions)**

Ask Shane (do not do these unilaterally):
1. Create a GitHub repo for the pack (suggested name `afterlight-pack`, private is fine: Pages on private repos requires Pro; a public repo of TOML metadata is also reasonable since no jars/copyrighted content live in git; Shane's call).
2. `git remote add origin <url> && git push -u origin main` (runs here once Shane provides the URL/auth).
3. Enable GitHub Pages (deploy from branch `main`, root): or approve adding a Pages deploy step to CI.
4. Re-build the instance zip with the real URL: `PACK_URL=https://<user>.github.io/afterlight-pack/pack.toml ./tools/build-prism-instance.sh`.

Deliverable of this checkpoint: pushing triggers `pack-ci` green on GitHub; the real instance zip exists in `dist/` ready to send to friends. If Shane defers, everything local stays green and Plan 02 proceeds: the checkpoint reopens in Plan 07.

---

## Definition of green for Plan 01 (all must hold)

1. `packwiz refresh` exits 0 with clean `git status` afterward
2. `./tools/export.sh` produces a valid `.mrpack` (CF zip allowed to be deferred with a noted cause)
3. `./tools/server-test.sh` prints `SERVER BOOT: OK`
4. `PACK_URL=… ./tools/build-prism-instance.sh` produces a structurally-verified zip
5. All work committed; ~20–23 mod TOMLs in `mods/`, all with deliberate `side` values
