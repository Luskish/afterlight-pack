# AFTERLIGHT Public Delivery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate `AFTERLIGHT Signal`, add ECHO and Gate quest bridges, publish canonical Prism and CurseForge downloads, launch `rl-labs.org/afterlight`, and deploy the verified candidate safely to the existing VPS.

**Architecture:** The pack references one immutable companion-mod release by URL and SHA-512, keeps FTB Quests authoritative, and validates route plus recovery data in the existing Python suite. Release tooling emits one canonical public inventory, while the Astro portal discovers the newest complete GitHub release and explains launcher-specific update behavior.

**Tech Stack:** Packwiz, NeoForge 1.21.1, FTB Quests SNBT compiler, Python `unittest`, Bash, GitHub Actions and Releases, Astro 5, Vue 3, Netlify, Docker Compose, systemd, Ubuntu VPS.

## Global Constraints

- Work from the stable `7630bccff75b9faeb1415db3070d8f6b9e2aa88e` lineage or a newer verified main SHA.
- Preserve the dirty `/Users/shaneliszewski/MinecraftTest` checkout unchanged.
- Use isolated worktrees or fresh clones for every edit and release operation.
- Source `tools/versions.env` and export `PATH_EXTRA` before every Packwiz command.
- No U+2014 em dash appears in changed pack or website files.
- No JAR, token, credential, world, backup, or secret is committed.
- Every Packwiz commit contains `pack.toml`, `index.toml`, and `mods/` together.
- `./tools/verify-pack.sh` must print `VERIFY: ALL GREEN` after pack changes.
- `BOOT_TIMEOUT=600 ./tools/server-test.sh` must print `SERVER BOOT: OK` after mod, config, quest, or script changes.
- Exact branch CI must be green before merge; exact main CI and Pages parity must be green after merge.
- Public release assets are immutable after publication.
- The live server updates only with zero players and a verified pre-update backup.
- Chunky pre-generation remains disabled until Shane separately approves it.
- Every commit ends with `Co-Authored-By: Codex <noreply@openai.com>`.

## File Structure

Pack repository changes:

```text
AGENTS.md                                      public artifact policy and current guardrails
mods/afterlight-signal.pw.toml                 immutable v0.2.0 URL and SHA-512
config/afterlight/echo_route.json              versioned route policy
config/afterlight/pack_version.txt             launcher-neutral title identity
config/ftbquests/quests/                       recovery and Far Relay quest data
tools/afterlight_quests/echo_route.py           deterministic route builder and validator
tools/build-echo-route.py                      route generation entry point
tools/release_artifacts.py                     canonical public artifact metadata
tools/build-release.sh                         canonical public output
tools/release-gauntlet.sh                      accepted public staging
tools/promote-release.sh                       public inventory promotion checks
tools/publish-release.sh                       five-asset publication
tools/tests/                                   route, quest, artifact, promotion, publication tests
docs/INSTALL.md                                Prism and CurseForge instructions
docs/RELEASING.md                              current public policy
docs/HANDOFF.md                                exact implementation and recovery state
docs/releases/1.0.0-rc.1.md                    candidate evidence
```

Website repository changes:

```text
src/pages/afterlight.astro                     Signal Reliquary portal page
src/lib/afterlight-releases.mjs                pure GitHub release selection
src/components/AfterlightDownloads.vue         live release state and copy actions
public/afterlight/                              original portal artwork
tests/afterlight-releases.test.mjs              API selection and fallback tests
package.json                                   node:test command
src/pages/projects.astro                       AFTERLIGHT project card
```

---

### Task 1: Public Artifact Policy and Release Contracts

**Files:**
- Modify: `AGENTS.md`
- Modify: `docs/INSTALL.md`
- Modify: `docs/RELEASING.md`
- Modify: `docs/superpowers/specs/2026-08-09-afterlight-friend-release-design.md`
- Modify: `docs/superpowers/specs/2026-08-10-afterlight-pinned-v1-release-design.md`
- Modify: `tools/release_artifacts.py`
- Modify: `tools/build-release.sh`
- Modify: `tools/release-gauntlet.sh`
- Modify: `tools/promote-release.sh`
- Modify: `tools/publish-release.sh`
- Test: `tools/tests/test_release_artifacts.py`
- Test: `tools/tests/test_release_gauntlet.py`
- Test: `tools/tests/test_release_promotion.py`
- Test: `tools/tests/test_release_publication.py`

**Interfaces:**
- Consumes: current versioned `.mrpack` and CurseForge exports.
- Produces: canonical public inventory and metadata format 3.

- [ ] **Step 1: Write failing public inventory tests**

The only accepted release directory inventory is:

```text
AFTERLIGHT-prism-instance.zip
AFTERLIGHT-curseforge.zip
AFTERLIGHT.mrpack
SHA256SUMS
release-metadata.json
```

Update tests to reject `friends-only/`, versioned archive names, missing public checksums, extra files, links, traversal, secrets, malformed ZIPs, and metadata that classifies either launcher archive as private.

Metadata format 3 contains:

```json
{
  "format": 3,
  "version": "1.0.0-rc.1",
  "git_sha": "40 lowercase hex",
  "public_artifacts": {
    "AFTERLIGHT-prism-instance.zip": {"sha256": "64 hex", "size": 1},
    "AFTERLIGHT-curseforge.zip": {"sha256": "64 hex", "size": 1},
    "AFTERLIGHT.mrpack": {"sha256": "64 hex", "size": 1}
  }
}
```

- [ ] **Step 2: Run focused tests and verify RED**

Run:

```bash
python3 -m unittest \
  tools.tests.test_release_artifacts \
  tools.tests.test_release_gauntlet \
  tools.tests.test_release_promotion \
  tools.tests.test_release_publication -v
```

Expected: failures show the old private inventory and versioned names.

- [ ] **Step 3: Implement canonical build output**

`tools/export.sh` may keep versioned temporary names internally. `build-release.sh` moves validated exports into canonical names before metadata and checksums are written. It prints one `PUBLIC:` section and no friends-only section.

`release-gauntlet.sh` stages one flat `public/` directory containing all five files. Promotion and publication require that exact inventory. Publication attaches all five files to GitHub.

- [ ] **Step 4: Update the authorized policy**

Record Shane's explicit authorization to publish the CurseForge archive and `.mrpack`. Mark the old friends-only statements as superseded on 2026-08-11. Keep the no-secret, no-unclassified-file, immutable-release, and archive-inspection rules.

- [ ] **Step 5: Run focused tests and verify GREEN**

Run the Step 2 command.

Expected: all release tests pass with metadata format 3 and canonical names.

- [ ] **Step 6: Commit**

```bash
git add AGENTS.md docs tools
git commit -m "feat(release): publish canonical launcher assets" \
  -m "Co-Authored-By: Codex <noreply@openai.com>"
```

---

### Task 2: Companion Mod, Route, and Recovery Quest

**Files:**
- Create: `mods/afterlight-signal.pw.toml`
- Create: `config/afterlight/echo_route.json`
- Create: `config/afterlight/pack_version.txt`
- Create: `tools/afterlight_quests/echo_route.py`
- Create: `tools/build-echo-route.py`
- Modify: `tools/afterlight_quests/catalog.py`
- Modify: `tools/build-quests.py`
- Modify: `config/ftbquests/quests/chapters/`
- Modify: `config/ftbquests/quests/lang/en_us.snbt`
- Modify: `config/ftbquests/quests/.afterlight-managed.json`
- Modify: `pack.toml`
- Modify: `index.toml`
- Test: `tools/tests/test_afterlight_quests.py`
- Test: `tools/tests/test_rc_hygiene_reliability.py`

**Interfaces:**
- Consumes: public `afterlight-signal-0.2.0+1.21.1.jar` and exact checksums from the Gate plan.
- Produces: Packwiz mod descriptor, validated route schema, and repeatable FTB command reward.

- [ ] **Step 1: Authenticate the companion release**

Download the public v0.2.0 JAR, verify byte equality with the accepted mod build, and compute SHA-512:

```bash
curl -fL --proto '=https' --tlsv1.2 \
  -o /tmp/afterlight-signal-0.2.0+1.21.1.jar \
  'https://github.com/Luskish/afterlight-signal/releases/download/v0.2.0/afterlight-signal-0.2.0%2B1.21.1.jar'
shasum -a 512 /tmp/afterlight-signal-0.2.0+1.21.1.jar
```

Write the literal resulting SHA-512 into a `side = "both"` Packwiz descriptor. The descriptor filename and URL are immutable.

- [ ] **Step 2: Write failing route and recovery tests**

Reserve these exact FTB IDs after proving they do not collide:

```text
ECHO Protocols chapter  6C40000000000001
Recover ECHO quest      6C40000000000002
Checkmark task          6C40000000000003
Command reward          6C40000000000004
```

Tests require repeatable true, cooldown 5 seconds, permission level 0, silent command `echo recover`, no item reward, no dependency, and icon `afterlight:echo`.

Route tests require schema 1, 16-digit uppercase IDs, no duplicates, all IDs present in managed quest data, terminal quest `31C9557D2F51238F`, and deterministic output.

Pack identity tests require `config/afterlight/pack_version.txt` to contain exactly one trimmed UTF-8 line equal to the current `pack.toml` `version` value. Blank, extra-line, or mismatched identity fails verification.

- [ ] **Step 3: Run tests and verify RED**

Run:

```bash
python3 -m unittest tools.tests.test_afterlight_quests -v
python3 -m unittest tools.tests.test_rc_hygiene_reliability -v
```

Expected: recovery IDs and route output are missing.

- [ ] **Step 4: Implement the recovery chapter and route builder**

Add `ECHO Protocols` as an always-visible Story-group support chapter. Use ECHO copy:

```text
Title: Recover ECHO
Subtitle: Continuity requires a reachable interface.
Description: If your continuity node is lost, authorize a replacement here. The previous signal will be superseded. Nothing else will be duplicated.
```

`echo_route.py` consumes the compiler-managed catalog, produces ordered Story quest IDs, preserves explicit branch priority, excludes the recovery quest from normal recommendation, and includes postgame as a final optional segment.

Write the current `pack.toml` version to `config/afterlight/pack_version.txt`. This file is the launcher-neutral runtime source for the custom title's `PACK VERSION` field and must remain Packwiz-managed for both Prism and CurseForge installs.

- [ ] **Step 5: Regenerate, refresh, and run focused checks**

Run:

```bash
python3 tools/build-quests.py
python3 tools/build-echo-route.py
source tools/versions.env && export PATH="$PATH_EXTRA:$PATH"
packwiz refresh
python3 -m unittest tools.tests.test_afterlight_quests -v
python3 -m unittest tools.tests.test_rc_hygiene_reliability -v
```

Expected: quest counts increase by one chapter, one quest, one task, and one reward; route validation passes; Packwiz index includes the descriptor, route config, and exact pack-version file.

- [ ] **Step 6: Run pack and server gates**

Run:

```bash
./tools/verify-pack.sh
BOOT_TIMEOUT=600 ./tools/server-test.sh
```

Expected: `VERIFY: ALL GREEN` and `SERVER BOOT: OK`, with `AFTERLIGHT Signal` plus FTB Quests loaded.

- [ ] **Step 7: Commit without a final refresh**

```bash
git add pack.toml index.toml mods config tools
git commit -m "feat(pack): integrate physical ECHO guidance" \
  -m "Co-Authored-By: Codex <noreply@openai.com>"
```

Do not run `packwiz refresh` after this commit.

---

### Task 3: Gate Quest Bridge and Far Relay Epilogue

**Files:**
- Modify: `tools/afterlight_quests/catalog.py`
- Modify: existing Gate and postgame chapter output under `config/ftbquests/quests/chapters/`
- Modify: `config/ftbquests/quests/lang/en_us.snbt`
- Modify: `config/afterlight/echo_route.json`
- Modify: `index.toml`
- Modify: `pack.toml`
- Test: `tools/tests/test_afterlight_quests.py`
- Test: `tools/tests/test_gate_recipe_contract.py`

**Interfaces:**
- Consumes: advancements `afterlight:gate_opened` and `afterlight:far_relay_arrival` from companion v0.2.0.
- Produces: physical activation proof and one additive Far Relay epilogue quest without resetting existing teams.

- [ ] **Step 1: Write failing Gate bridge tests**

Preserve existing task ID `645F98B8FAD4A1E5` but change its task type from checkmark to advancement `afterlight:gate_opened`.

Reserve these exact new IDs after collision check:

```text
Far Relay quest          6C40000000000101
Arrival advancement task 6C40000000000102
Chit reward              6C40000000000103
XP reward                6C40000000000104
```

The new quest depends on existing finale quest `31C9557D2F51238F`, uses advancement `afterlight:far_relay_arrival`, grants 16 Chits and 500 XP, and does not gate the Ascendancy Seal.

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
python3 -m unittest tools.tests.test_afterlight_quests -v
python3 -m unittest tools.tests.test_gate_recipe_contract -v
```

Expected: physical advancement task and Far Relay quest are missing.

- [ ] **Step 3: Implement the additive quest bridge**

Use ECHO copy:

```text
Title: The Far Relay
Subtitle: The inbound signal has a location now.
Description: Cross the physical Gate and reach the receiving relay. Familiar architecture remains evidence, not trust.
```

Keep all existing quest and reward IDs unchanged. Existing teams that already completed `645F98B8FAD4A1E5` retain completion because the task ID is stable. New teams must physically open the Gate.

- [ ] **Step 4: Regenerate, refresh, and run gates**

Run:

```bash
python3 tools/build-quests.py
python3 tools/build-echo-route.py
source tools/versions.env && export PATH="$PATH_EXTRA:$PATH"
packwiz refresh
python3 -m unittest tools.tests.test_afterlight_quests tools.tests.test_gate_recipe_contract -v
./tools/verify-pack.sh
BOOT_TIMEOUT=600 ./tools/server-test.sh
```

Expected: all tests pass, `VERIFY: ALL GREEN`, and `SERVER BOOT: OK`.

- [ ] **Step 5: Commit without a final refresh**

```bash
git add pack.toml index.toml mods config tools
git commit -m "feat(quests): enter the physical Gate" \
  -m "Co-Authored-By: Codex <noreply@openai.com>"
```

---

### Task 4: R&L Labs Download Portal

**Files:**
- Create: `src/pages/afterlight.astro`
- Create: `src/lib/afterlight-releases.mjs`
- Create: `src/components/AfterlightDownloads.vue`
- Create: `tests/afterlight-releases.test.mjs`
- Create: `public/afterlight/signal-reliquary.webp`
- Create: `public/afterlight/echo-device.png`
- Modify: `src/pages/projects.astro`
- Modify: `package.json`

**Interfaces:**
- Consumes: GitHub Releases API response for `Luskish/afterlight-pack`.
- Produces: `https://rl-labs.org/afterlight`, current canonical downloads, server-address copy, and API fallback.

- [ ] **Step 1: Create an isolated website branch**

Clone a fresh working copy, read its repository instructions, and create `codex/afterlight-portal` from current `R-L-Labs/Website/main`. Do not modify the read-only discovery clone.

- [ ] **Step 2: Write failing release-selection tests**

`selectAfterlightRelease(releases, fallback)` must:

1. Ignore drafts.
2. Sort by `published_at` descending.
3. Accept prereleases but expose `prerelease: true` for labeling.
4. Require all three canonical client assets.
5. Return the fallback when fetch fails or no complete release exists.

Run: `node --test tests/afterlight-releases.test.mjs`

Expected: FAIL because selector is missing.

- [ ] **Step 3: Implement the pure selector and Vue download component**

Fetch `https://api.github.com/repos/Luskish/afterlight-pack/releases?per_page=20` with an abort timeout. Display version, publication date, prerelease status, SHA256SUMS link, and direct asset buttons. On failure, display a restrained amber offline notice and use the pinned known-good fallback.

Prism copy states that Packwiz checks GitHub Pages every launch. CurseForge copy states that updates require importing the newest profile as a separate instance. Include server address `104.128.55.166` with a copy button.

- [ ] **Step 4: Build the Signal Reliquary page**

Use frontend-design guidance. Keep the rest of the company site unchanged. The page uses the approved cyan, amber, red, bone, and vault-black rules, original AFTERLIGHT artwork, responsive cards, visible focus states, reduced-motion support, semantic headings, and no copied reference composition.

- [ ] **Step 5: Run website tests and production build**

Run:

```bash
npm ci
npm test
npm run build
```

Inspect the built page at desktop and mobile widths, test API success and forced failure, validate all links, and scan changed files for U+2014.

- [ ] **Step 6: Commit, push, and merge**

```bash
git add src public tests package.json package-lock.json
git commit -m "feat: launch the AFTERLIGHT download portal" \
  -m "Co-Authored-By: Codex <noreply@openai.com>"
git push -u origin codex/afterlight-portal
```

Open a PR to `main`, require Netlify and repository checks, review the deployed preview, merge, then verify `https://rl-labs.org/afterlight` returns 200 and resolves canonical assets.

---

### Task 5: Candidate Identity and Full Release Gauntlet

**Files:**
- Modify: `pack.toml`
- Modify: `index.toml`
- Modify: `config/afterlight/pack_version.txt`
- Create: `docs/releases/1.0.0-rc.1.md`
- Modify: `docs/HANDOFF.md`
- Modify: `README.md`
- Modify: `docs/INSTALL.md`

**Interfaces:**
- Consumes: Tasks 1 through 4 and published companion v0.2.0.
- Produces: accepted SHA, exact dev and main CI, Pages parity, and public `v1.0.0-rc.1` release.

- [ ] **Step 1: Write candidate notes and bump identity**

Set `pack.toml` version and the single line in `config/afterlight/pack_version.txt` to `1.0.0-rc.1`. Release notes describe physical ECHO, recovery, guided UI, Signal Reliquary title, physical Gate, Far Relay, public portal, launcher update behavior, additive-world safety, and manual checks still required before final 1.0.0.

- [ ] **Step 2: Refresh once and run focused tests**

Run:

```bash
source tools/versions.env && export PATH="$PATH_EXTRA:$PATH"
packwiz refresh
python3 -m unittest discover -s tools/tests -v
```

Expected: complete Python suite passes and index identity matches 1.0.0-rc.1.

- [ ] **Step 3: Run the full local release gauntlet**

Commit the candidate identity with trailer, require a clean tree, then run:

```bash
SHA=$(git rev-parse HEAD)
./tools/release-gauntlet.sh "$SHA"
```

Expected: unit suite, `VERIFY: ALL GREEN`, `SERVER BOOT: OK`, Compose render, ShellCheck, two deterministic builds, client two-pass install, archive inspection, and clean-tree checks all pass.

- [ ] **Step 4: Merge exact work into dev and promote**

Push the feature branch and open a PR to `dev`. Require `pack-ci` green at exact head, merge without deleting `dev`, then use a fresh clean clone with local branch `dev` to run:

```bash
tools/promote-release.sh "$SHA" --confirm
```

The promoter must push exact dev, fast-forward exact main, require both exact CI runs, require GitHub Pages byte parity, tag `v1.0.0-rc.1`, and return to dev.

- [ ] **Step 5: Publish all canonical assets**

Run from the clean release clone:

```bash
tools/publish-release.sh "$SHA" 1.0.0-rc.1 --prerelease --confirm
```

Download all five assets, verify SHA256SUMS, and compare each with accepted gauntlet bytes. Confirm the portal selects this release and labels it release candidate.

- [ ] **Step 6: Record evidence and commit**

Record exact SHAs, CI URLs, Pages hashes, release URL, companion release digest, five artifact digests, and portal URL. Commit evidence with trailer, push dev, and require the documentation commit's exact CI.

---

### Task 6: Safe VPS Deployment

**Files:**
- Modify on VPS only: `/opt/afterlight` checked-out source
- Modify on VPS only: `/srv/afterlight/data/.afterlight-pack-sha`
- Create on VPS only: verified backup under `/srv/afterlight/backups/`

**Interfaces:**
- Consumes: exact verified candidate main SHA and current persistent SSH alias `afterlight-vps`.
- Produces: healthy candidate server with preserved world, whitelist, memory budget, daily restart timer, and rollback archive.

- [ ] **Step 1: Prove safe deployment conditions**

Over persistent SSH, verify:

- Current source and data markers.
- Clean `/opt/afterlight` tree.
- Zero online players through RCON.
- At least 30 GiB free storage.
- Existing daily timer active.
- No Chunky pre-generation running.

If any player is online, wait and recheck. Do not kick active players for this feature deployment.

- [ ] **Step 2: Create and authenticate a backup**

Run the supported backup command, require a new zstd archive, run `zstd -t`, list its world metadata, compute SHA-256, and record its absolute path. Do not continue on any backup warning or missing verification.

- [ ] **Step 3: Deploy exact main and update**

Fetch without force, check out exact accepted main SHA, and run the supported `server/afterlight-server.sh update`. Require Packwiz to install `AFTERLIGHT Signal`, preserve whitelist entries NRNJ, Liszewski, ZSmitt, and DylnDark, and preserve 6G initial, 14G max, 17G container limit.

- [ ] **Step 4: Verify health and additive registration**

Require:

- Container healthy.
- `Done` line in the current boot.
- AFTERLIGHT Signal loaded.
- FTB Quests expected counts loaded.
- `afterlight:far_relay` registered.
- Lootr, SmartBrainLib, FTB Ultimine, Controlling, and Searchables loaded.
- Daily restart timer active with next 4:45 AM America/New_York trigger.
- TCP 25565 listening publicly.
- Source and data marker equal the accepted SHA.

- [ ] **Step 5: Preserve rollback evidence**

Print the exact supported rollback command using the new backup, record it in the release handoff, and leave the persistent SSH configuration intact. Do not delete prior backups or rescue paths.

## Completion Gate

This plan is complete when public policy and tests agree, both launchers have canonical release assets, the portal is live, the companion descriptor and route are Packwiz-managed, recovery and Gate quests load, the full release gauntlet passes at one exact SHA, dev and main CI are green, Pages bytes match, the prerelease is published, and the VPS runs the exact candidate from a verified backup.
