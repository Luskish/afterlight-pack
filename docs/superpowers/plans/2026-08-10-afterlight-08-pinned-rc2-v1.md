# AFTERLIGHT Pinned rc2 and v1 Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a reproducible `0.9.0-rc.2` friend release with fully pinned Prism installation, verified clean client and server paths, clear Prism and CurseForge instructions, and a safe path to a version-only `1.0.0` after manual acceptance.

**Architecture:** Keep Packwiz and GitHub Pages as the stable update channel while bundling exact bootstrap and main Packwiz installer JARs inside the deterministic Prism archive. Extend the existing release artifact library and detached-SHA gauntlet instead of creating a second build path, add an end-to-end clean client installer test, and make publication fail closed on every version and artifact mismatch. Preserve the existing Docker Compose friend server and make Discord the documented voice path while leaving Simple Voice Chat available but optional.

**Tech Stack:** Minecraft 1.21.1, NeoForge 21.1.248, Java 21, Packwiz, Prism Launcher, CurseForge App, Python 3 standard library, Bash, Docker Compose v2, GitHub Actions, GitHub Pages, GitHub CLI.

## Global Constraints

- Read and follow `/Users/shaneliszewski/MinecraftTest/AGENTS.md` before every task.
- Do not introduce a U+2014 em dash character in code, prose, comments, output, or commit messages.
- Work on `dev`; `main` remains the stable Packwiz channel.
- The published `v0.9.0-rc.1` tag, release, and commit remain immutable.
- Do not modify, reset, merge, or delete `codex/plan07-task1` or `/private/tmp/afterlight-plan07-task1`.
- Minecraft remains `1.21.1`, NeoForge remains `21.1.248`, and the runtime remains Java 21.
- The stable Packwiz URL is `https://luskish.github.io/afterlight-pack/pack.toml`.
- Pin bootstrap `v0.0.3`, size `98989`, SHA-256 `a8fbb24dc604278e97f4688e82d3d91a318b98efc08d5dbfcbcbcab6443d116c`.
- Pin main installer `v0.5.14`, size `4378828`, SHA-256 `c9f646908d340d84773948a9a7d98bc1dae250d35e1016dc6e2b8459760b5598`.
- Public release output remains exactly `AFTERLIGHT-prism-instance.zip`, `release-metadata.json`, and `SHA256SUMS`.
- `AFTERLIGHT-<version>.mrpack` and `AFTERLIGHT-<version>-curseforge.zip` remain friends-only and never enter a public artifact or release.
- Simple Voice Chat remains installed, but Discord is the expected voice path and UDP `24454` is optional.
- Every Packwiz command starts after `source tools/versions.env && export PATH="$PATH_EXTRA:$PATH"`.
- Every Packwiz-touching commit stages `pack.toml`, `index.toml`, and `mods/` together and leaves refresh output committed.
- Manifest, configuration, and script changes require `./tools/verify-pack.sh` and `BOOT_TIMEOUT=600 ./tools/server-test.sh` before promotion.
- Every Codex-authored commit ends with `Co-Authored-By: Codex <noreply@openai.com>`.
- `1.0.0` contains only release identity, generated Packwiz state, release notes, and the completed acceptance record.

## File Structure

- `tools/release_artifacts.py`: Owns deterministic Prism construction, archive inspection, release metadata, checksums, repository safety, and private archive inspection.
- `tools/build-prism-instance.sh`: Downloads and authenticates both exact installer JARs before invoking the Python builder.
- `tools/client_install_support.py`: Computes expected client and server-only mod inventories from Packwiz metadata and validates an installed client.
- `tools/client-install-test.sh`: Installs from the released Prism bytes through the bundled installers, repeats the update, and proves mod-set idempotence.
- `tools/release-gauntlet.sh`: Adds the clean client install to the exact detached-SHA release matrix.
- `tools/publish-release.sh`: Validates version, tag, notes, metadata, checksums, and public inventory before creating a GitHub release.
- `tools/tests/test_release_artifacts.py`: Covers dual-installer archive and metadata behavior.
- `tools/tests/test_client_install.py`: Covers client inventory classification and shell harness contracts.
- `tools/tests/test_release_gauntlet.py`: Covers client-install ordering and accepted artifact capture.
- `tools/tests/test_release_publication.py`: Covers publication mismatch and public-only policies using a fake `gh` executable.
- `tools/versions.env`: Stores both immutable installer versions, sizes, and SHA-256 values.
- `docs/INSTALL.md`: Gives separate Prism and CurseForge import and update instructions.
- `docs/SERVER.md`: Gives the complete VPS checklist and marks UDP `24454` optional when Discord is used.
- `docs/RELEASING.md`: Uses derived version variables and the fail-closed publication command.
- `docs/releases/0.9.0-rc.2.md`: Records candidate evidence and unresolved manual acceptance without claiming it passed.
- `docs/releases/1.0.0-acceptance.md`: Records the seven required manual checks with exact candidate identity and evidence.

---

### Task 1: Dual-Installer Prism Artifact

**Files:**
- Modify: `tools/tests/test_release_artifacts.py`
- Modify: `tools/release_artifacts.py`
- Modify: `tools/build-prism-instance.sh`
- Modify: `tools/build-release.sh`
- Modify: `tools/versions.env`

**Interfaces:**
- Consumes: authenticated bootstrap and main installer regular files.
- Produces: `build_prism_archive(bootstrap_path, installer_path, output_path, pack_url, minecraft_version, neoforge_version) -> pathlib.Path`.
- Produces: `inspect_prism_archive(archive_path, pack_url, bootstrap_sha256, installer_sha256, installer_size) -> dict[str, object]`.
- Produces: release metadata containing `packwiz.bootstrap` and `packwiz.installer`, each with exact `version`, `size`, and `sha256` values.

- [ ] **Step 1: Write failing archive tests**

Add tests that require these sorted entries and exact command:

```python
EXPECTED_PRISM_NAMES = (
    ".minecraft/packwiz-installer-bootstrap.jar",
    ".minecraft/packwiz-installer.jar",
    "instance.cfg",
    "mmc-pack.json",
)
EXPECTED_PRELAUNCH = (
    'PreLaunchCommand="$INST_JAVA" -jar packwiz-installer-bootstrap.jar '
    '--bootstrap-no-update --bootstrap-main-jar packwiz-installer.jar -g '
    'https://luskish.github.io/afterlight-pack/pack.toml\n'
)
```

Cover byte-identical builds, both correct digests, exact main-installer size, missing or extra entries, renamed JAR aliases, mutable prelaunch commands, links, and embedded mod JARs. Update metadata tests to require both installer records.

- [ ] **Step 2: Run focused tests and prove RED**

Run:

```bash
python3 -m unittest \
  tools.tests.test_release_artifacts.PrismArtifactTests \
  tools.tests.test_release_artifacts.ReleasePolicyTests -v
```

Expected: failures because only the bootstrap is accepted and metadata has no `packwiz` object.

- [ ] **Step 3: Implement dual-installer construction and inspection**

Add separate constants for `.minecraft/packwiz-installer-bootstrap.jar` and `.minecraft/packwiz-installer.jar`. Make `_instance_config()` emit the exact no-update command. Validate the bootstrap SHA-256, main-installer SHA-256, and main-installer positive integer size before replacing the destination archive. Return both installer facts in the inspection summary.

- [ ] **Step 4: Authenticate both downloads in Bash**

Add `PACKWIZ_BOOTSTRAP_SIZE=98989` to `tools/versions.env`. Update `tools/build-prism-instance.sh` to download both exact GitHub release URLs into separate temporary files, verify each size and SHA-256, pass both paths to `build-prism`, and pass both expected hashes plus main-installer size to `inspect-prism`. Extend `tools/build-release.sh` immutable pin checks to both versions, sizes, and hashes.

- [ ] **Step 5: Record both installer identities in metadata**

Extend `write_release_metadata()` and its CLI with these required values:

```text
--bootstrap-version
--bootstrap-size
--bootstrap-sha256
--installer-version
--installer-size
--installer-sha256
```

Write schema `format: 2` with exact `packwiz.bootstrap` and `packwiz.installer` records. Make checksum classification reject malformed or missing installer metadata.

- [ ] **Step 6: Run focused tests and prove GREEN**

Run:

```bash
python3 -m unittest \
  tools.tests.test_release_artifacts.PrismArtifactTests \
  tools.tests.test_release_artifacts.ReleasePolicyTests -v
bash -n tools/build-prism-instance.sh tools/build-release.sh
shellcheck -x tools/build-prism-instance.sh tools/build-release.sh
```

Expected: all focused tests pass and both scripts pass syntax and ShellCheck.

- [ ] **Step 7: Commit Task 1**

```bash
git add tools/tests/test_release_artifacts.py tools/release_artifacts.py tools/build-prism-instance.sh tools/build-release.sh tools/versions.env
git commit -m "fix(release): pin both Prism installers" -m "Co-Authored-By: Codex <noreply@openai.com>"
```

---

### Task 2: Clean Client Install Gate

**Files:**
- Create: `tools/client_install_support.py`
- Create: `tools/client-install-test.sh`
- Create: `tools/tests/test_client_install.py`
- Modify: `tools/release-gauntlet.sh`
- Modify: `tools/tests/test_release_gauntlet.py`
- Modify: `tools/verify-pack.sh`
- Modify: `.github/workflows/pack-ci.yml`

**Interfaces:**
- Consumes: one built `AFTERLIGHT-prism-instance.zip`, a clean Packwiz source root, Java 21, and network access to pinned mod files.
- Produces: `expected_mod_inventory(mods_dir: pathlib.Path) -> tuple[set[str], set[str]]`, where the first set is every `side != "server"` filename and the second set is every `side == "server"` filename.
- Produces: `validate_client_install(instance_dir: pathlib.Path, mods_dir: pathlib.Path) -> dict[str, object]` with `client_mod_count`, `server_only_count`, and deterministic `modset_sha256`.
- Produces: `tools/client-install-test.sh PRISM_ZIP`, which prints `CLIENT INSTALL: OK` only after a clean install and idempotent second update.

- [ ] **Step 1: Write failing client inventory tests**

Use temporary `.pw.toml` fixtures with `client`, `both`, and `server` sides. Require missing side, duplicate filename, absent expected JAR, unexpected JAR, and present server-only JAR to fail. Require the current repository inventory to report exactly `152` client-required filenames and `15` server-only filenames.

- [ ] **Step 2: Write failing shell contract tests**

Read `tools/client-install-test.sh` and require it to extract both approved JARs from the supplied Prism ZIP, serve the current Packwiz source over loopback HTTP, invoke:

```text
java -jar packwiz-installer-bootstrap.jar --bootstrap-no-update --bootstrap-main-jar packwiz-installer.jar -g <loopback-pack-url>
```

Require two installer invocations, Java 21 validation, trap-based server and temporary-directory cleanup, a first and second modset digest comparison, and the exact success marker.

- [ ] **Step 3: Run client tests and prove RED**

Run:

```bash
python3 -m unittest tools.tests.test_client_install -v
```

Expected: import and file-not-found failures because the support module and harness do not exist.

- [ ] **Step 4: Implement inventory validation**

Parse every `mods/*.pw.toml` with `tomllib`, require a deliberate side, require a unique nonempty filename, and compare exact filenames against `<instance>/mods/*.jar`. Compute the digest from sorted lines in the form `<sha256>  <filename>\n`, not filesystem order or timestamps.

- [ ] **Step 5: Implement the client install harness**

Create a temporary instance and local HTTP server, verify the Prism archive through `release_artifacts.py`, extract only its two installer JARs, run the exact pinned no-update command from the temporary `.minecraft` directory, validate the installed mod inventory, rerun the same command, validate again, compare digests, and clean all owned processes and paths on success or failure.

- [ ] **Step 6: Add the client gate to verification and CI**

Run `tools/client-install-test.sh "$FIRST/AFTERLIGHT-prism-instance.zip"` after the two deterministic release builds in `tools/release-gauntlet.sh`. Extend `tools/verify-pack.sh` to parse and require executable status for the new shell script and compile the new Python module. Keep CI's ordinary push path on the existing server gate; the exact client download gate runs inside the release gauntlet to avoid duplicating a large install on every documentation push.

- [ ] **Step 7: Run focused tests and prove GREEN**

Run:

```bash
python3 -m unittest tools.tests.test_client_install tools.tests.test_release_gauntlet -v
bash -n tools/client-install-test.sh tools/release-gauntlet.sh tools/verify-pack.sh
shellcheck -x tools/client-install-test.sh tools/release-gauntlet.sh tools/verify-pack.sh
```

Expected: all focused tests pass, scripts parse, and ShellCheck reports no findings.

- [ ] **Step 8: Commit Task 2**

```bash
git add .github/workflows/pack-ci.yml tools/client_install_support.py tools/client-install-test.sh tools/tests/test_client_install.py tools/release-gauntlet.sh tools/tests/test_release_gauntlet.py tools/verify-pack.sh
git commit -m "test(release): prove clean client installs" -m "Co-Authored-By: Codex <noreply@openai.com>"
```

---

### Task 3: Versioned Publication and Friend Documentation

**Files:**
- Create: `tools/publish-release.sh`
- Create: `tools/tests/test_release_publication.py`
- Create: `docs/releases/0.9.0-rc.2.md`
- Create: `docs/releases/1.0.0-acceptance.md`
- Modify: `pack.toml`
- Modify: `index.toml`
- Modify: `docs/INSTALL.md`
- Modify: `docs/SERVER.md`
- Modify: `docs/RELEASING.md`
- Modify: `tools/verify-pack.sh`

**Interfaces:**
- Consumes: `tools/publish-release.sh SHA VERSION --prerelease --confirm` for rc2 or `tools/publish-release.sh SHA VERSION --confirm` for v1.
- Produces: one GitHub release whose tag is `v<VERSION>` and whose assets are exactly the three public-safe files from `dist/gauntlet/<SHA>/public/`.
- Produces: friends-only files named from the exact `pack.toml` version for direct sharing through a private channel.

- [ ] **Step 1: Write failing publication tests**

Use a temporary Git repository, accepted artifact fixtures, and a fake `gh` executable. Require rejection for a pack version mismatch, requested version mismatch, metadata version or SHA mismatch, missing or extra public assets, missing private files, release-note title mismatch, automated `NOT RUN` evidence, absent or moved tag, and a pre-existing release. Require `--prerelease` for versions containing `rc` and forbid it for `1.0.0`.

- [ ] **Step 2: Run publication tests and prove RED**

Run:

```bash
python3 -m unittest tools.tests.test_release_publication -v
```

Expected: failure because `tools/publish-release.sh` does not exist.

- [ ] **Step 3: Implement fail-closed publication**

Read `pack.toml`, `release-metadata.json`, `SHA256SUMS`, the annotated remote tag, and `docs/releases/<VERSION>.md`. Require all identities to match `SHA` and `VERSION`, require checksum verification, reject automated `NOT RUN` values before `Known Boundaries`, and invoke `gh release create` with only the three public paths. Query the created release and reject any asset inventory other than:

```text
AFTERLIGHT-prism-instance.zip
SHA256SUMS
release-metadata.json
```

- [ ] **Step 4: Move the pack to rc2 as one Packwiz change**

Set `pack.toml` version to `0.9.0-rc.2`, then run:

```bash
source tools/versions.env && export PATH="$PATH_EXTRA:$PATH"
packwiz refresh
```

Stage `pack.toml`, `index.toml`, and `mods/` together even if the mod metadata is unchanged.

- [ ] **Step 5: Write rc2, launcher, and VPS documentation**

Document Prism as the recommended auto-updating path. Document CurseForge App import as `My Modpacks`, `Create Custom Profile`, `Import`, then select `AFTERLIGHT-0.9.0-rc.2-curseforge.zip`; state that this file is friends-only, may show the manual non-CurseForge-file acknowledgement, and requires a newly shared ZIP for updates. State that Discord is expected and UDP `24454` can stay closed unless Simple Voice Chat is used.

Create the rc2 evidence record with exact automated evidence fields and honest manual `NOT RUN` entries. Create the v1 acceptance record with seven rows for Prism launch, quest book, two-player server reconnect and whitelist, all hard gates and Seal preservation, Supercritical Phase Shifter timing, VPS update failure and rollback, and empty-directory backup restore. Each row requires `PASS` or `FAIL`, UTC date, tester, rc2 SHA, release URL, and evidence path.

- [ ] **Step 6: Make release instructions version-derived**

Replace rc1 literals in `docs/RELEASING.md` commands with:

```bash
VERSION=$(python3 -c 'import tomllib; print(tomllib.load(open("pack.toml", "rb"))["version"])')
TAG="v$VERSION"
RELEASE_DOC="docs/releases/$VERSION.md"
SHA=$(git rev-parse HEAD)
```

Use `tools/promote-release.sh "$SHA" --confirm` and the new publication command. Keep `v0.9.0-rc.1` documented as immutable rollback evidence.

- [ ] **Step 7: Run focused tests and repository gates**

Run:

```bash
python3 -m unittest tools.tests.test_release_publication tools.tests.test_rc_hygiene tools.tests.test_rc_hygiene_reliability -v
bash -n tools/publish-release.sh
shellcheck -x tools/publish-release.sh
./tools/verify-pack.sh
BOOT_TIMEOUT=600 ./tools/server-test.sh
git diff --check
```

Expected: tests pass, `VERIFY: ALL GREEN`, `SERVER BOOT: OK`, and no U+2014 or whitespace errors are present.

- [ ] **Step 8: Commit Task 3**

```bash
git add pack.toml index.toml mods/ docs/INSTALL.md docs/SERVER.md docs/RELEASING.md docs/releases/0.9.0-rc.2.md docs/releases/1.0.0-acceptance.md tools/publish-release.sh tools/tests/test_release_publication.py tools/verify-pack.sh
git commit -m "release: prepare AFTERLIGHT 0.9.0 rc2" -m "Co-Authored-By: Codex <noreply@openai.com>"
```

---

### Task 4: Verify, Promote, and Publish rc2

**Files:**
- Modify: `docs/releases/0.9.0-rc.2.md`
- Modify: `docs/HANDOFF.md`

**Interfaces:**
- Consumes: the exact clean `dev` HEAD and its accepted gauntlet directory.
- Produces: immutable tag `v0.9.0-rc.2`, stable `main` and Pages parity at the accepted SHA, a public GitHub prerelease with three safe assets, and local friends-only Prism alternative archives for direct sharing.

- [ ] **Step 1: Run the complete local suite**

Run:

```bash
python3 -m unittest discover -s tools/tests -p 'test_*.py' -v
source tools/versions.env && export PATH="$PATH_EXTRA:$PATH"
./tools/verify-pack.sh
BOOT_TIMEOUT=600 ./tools/server-test.sh
tmp=$(mktemp -d)
mkdir -p "$tmp/data" "$tmp/backups" "$tmp/secrets"
printf 'test-only-rcon-password\n' > "$tmp/secrets/rcon_password"
chmod 0600 "$tmp/secrets/rcon_password"
printf 'DATA_DIR=%s\nBACKUP_DIR=%s\nSECRETS_DIR=%s\n' "$tmp/data" "$tmp/backups" "$tmp/secrets" > "$tmp/server.env"
docker compose --project-name afterlight --env-file "$tmp/server.env" -f server/docker-compose.yml config --quiet
shellcheck -x $(git ls-files '*.sh')
git diff --check
git status --short
```

Expected: full Python suite passes, `VERIFY: ALL GREEN`, `SERVER BOOT: OK`, Compose and ShellCheck pass, and the tree is clean.

- [ ] **Step 2: Run the exact detached-SHA gauntlet**

```bash
SHA=$(git rev-parse HEAD)
./tools/release-gauntlet.sh "$SHA"
```

Expected: two release builds are byte-identical, the clean client install prints `CLIENT INSTALL: OK`, and the command ends with `GAUNTLET: ACCEPTED $SHA`.

- [ ] **Step 3: Promote through exact CI and Pages parity**

```bash
tools/promote-release.sh "$SHA" --confirm
```

Expected: exact `dev` CI passes, `main` fast-forwards to `SHA`, exact `main` CI passes, Pages matches local `pack.toml` and `index.toml`, tag `v0.9.0-rc.2` is pushed, and the command returns to `dev`.

- [ ] **Step 4: Populate automated evidence**

Record the gauntlet transcript path, both CI URLs, Pages hashes, Java and Packwiz versions, public and friends-only SHA-256 values, exact candidate SHA, and known boundaries in `docs/releases/0.9.0-rc.2.md`. Leave every unperformed manual result as `NOT RUN`.

- [ ] **Step 5: Verify and push the evidence commit**

```bash
git add docs/releases/0.9.0-rc.2.md docs/HANDOFF.md
git commit -m "docs(release): record 0.9.0 rc2 evidence" -m "Co-Authored-By: Codex <noreply@openai.com>"
git push origin dev
gh run watch --repo Luskish/afterlight-pack --exit-status
```

Expected: the exact evidence commit's `pack-ci` push run succeeds.

- [ ] **Step 6: Publish the prerelease**

```bash
tools/publish-release.sh "$SHA" 0.9.0-rc.2 --prerelease --confirm
```

Expected: GitHub release `v0.9.0-rc.2` exists with exactly three public-safe assets. The `.mrpack` and CurseForge ZIP remain only under `dist/gauntlet/$SHA/friends-only/`.

- [ ] **Step 7: Record friend and VPS handoff facts**

Update `docs/HANDOFF.md` with the release URL, accepted SHA, Prism ZIP checksum, private archive paths and checksums, manual acceptance status, and the exact ordered VPS setup commands from `docs/SERVER.md`.

---

### Task 5: Manual Acceptance and Version-Only v1

**Files:**
- Modify: `docs/releases/1.0.0-acceptance.md`
- Create: `docs/releases/1.0.0.md`
- Modify: `pack.toml`
- Modify: `index.toml`
- Modify: `docs/HANDOFF.md`

**Interfaces:**
- Consumes: seven real `PASS` results from the exact published rc2 lineage.
- Produces: immutable tag and release `v1.0.0` only when all manual and automated evidence is complete.

- [ ] **Step 1: Complete the manual matrix without substitution**

Use the released rc2 Prism bytes and released server lineage. Record real evidence for all seven checks. Any `FAIL` produces a new release candidate and stops this task. Automated tests cannot replace a row.

- [ ] **Step 2: Write the v1 release identity test**

Add a temporary comparison in `tools/tests/test_release_publication.py` that permits only these tracked changes between the accepted rc2 SHA and the proposed v1 SHA:

```text
pack.toml
index.toml
docs/releases/1.0.0.md
docs/releases/1.0.0-acceptance.md
docs/HANDOFF.md
```

Require `mods/`, configs, quests, KubeJS, recipes, and server files to remain byte-identical.

- [ ] **Step 3: Move to v1 as one version-only Packwiz change**

Set `pack.toml` version to `1.0.0`, create `docs/releases/1.0.0.md` from completed rc2 evidence, then run:

```bash
source tools/versions.env && export PATH="$PATH_EXTRA:$PATH"
packwiz refresh
```

Review `git diff --name-status` and stop if any gameplay, mod, quest, recipe, configuration, or server file changed.

- [ ] **Step 4: Commit the v1 identity**

```bash
git add pack.toml index.toml mods/ docs/releases/1.0.0.md docs/releases/1.0.0-acceptance.md docs/HANDOFF.md
git commit -m "release: prepare AFTERLIGHT 1.0.0" -m "Co-Authored-By: Codex <noreply@openai.com>"
```

- [ ] **Step 5: Repeat the full gauntlet and promotion**

Run the complete Task 4 local suite, then:

```bash
SHA=$(git rev-parse HEAD)
./tools/release-gauntlet.sh "$SHA"
tools/promote-release.sh "$SHA" --confirm
```

Expected: the exact v1 SHA passes local gauntlet, exact `dev` and `main` CI, Pages parity, and receives tag `v1.0.0`.

- [ ] **Step 6: Record evidence and publish v1**

Populate `docs/releases/1.0.0.md`, commit and push the evidence to `dev`, require exact CI success, then run:

```bash
tools/publish-release.sh "$SHA" 1.0.0 --confirm
```

Expected: final GitHub release `v1.0.0` contains exactly the three public-safe assets and no private archive.

- [ ] **Step 7: Run the final repository gauntlet**

Run the complete Python suite, Packwiz verification, fresh server boot, client installation, Compose rendering, ShellCheck, repository secret and U+2014 scan, clean-tree check, exact CI inspection, release asset inspection, tag ancestry check, and Pages byte parity. Record every command and result in `docs/HANDOFF.md` before claiming completion.

