# AFTERLIGHT Plan 05 Verification

Date: 2026-08-09

Candidate implementation commit: `b7d30074ed97756bd2f4960f6ba797626b70cded`

Status: Local automated verification and independent review passed. Exact-SHA CI remains required before the Plan 05 merge.

## Delivered Scope

- Story chapters 6 through 16 complete Acts II and III.
- Six new automation certifications plus Kinetics I award the seven stable certification finales required by Chapter 16.
- Three repeatable Requisition Depot chapters exchange Chits for progression-safe choices.
- The Undercurrent, Deep Vault, and Atlas side groups contain their planned chapters and preserve the intended optional progression boundaries.
- The quest corpus contains 41 chapters, 283 quests, 307 tasks, 393 quest rewards, and 6 reward tables.
- The runtime registry audit covers all 219 quest item and icon references.
- The release-candidate oracle authenticates accepted server log residuals, the installed artifact inventory, the full Mixin corpus, every common-list client target, generated quest audit code, runtime versions, and fresh-run evidence.
- Immutable `afterlight_idas_compat` version `0.1.2+1.21.1` authenticates IDAS 1.13.7 and sanitizes only four reviewed structure templates. It does not copy, embed, write, or redistribute IDAS structure NBT.

## Immutable Compatibility Release

- Release: `https://github.com/Luskish/afterlight-idas-compat/releases/tag/v0.1.2`
- Source commit: `b3d43520e2119296324faedccc2bf4fda4fd587f`
- Source tree SHA-256: `6c264d8fb9d3ef1a9ce61e6aa5b80cf0ef806988dd7389713f5eea91e55081d4`
- JAR SHA-256: `51ec890b6f079994c1fcc1a348a99a6ab359993e5bc83fe1d71ed8986da37f2b`
- JAR SHA-512: `f9bf2f432098babe88e13b5bea3ba631d433500f8d10f7b146d800f60cc2b46c6b4acc5dcce07f00561205880a75d27a2639d25fc35ae3a5f32aa0b5cd6cc892`
- Size: 39,392 bytes
- Branch CI run: `31292438314`, green
- Tag CI run: `31292577529`, green
- Controller verification: two clean release builds were byte-for-byte identical, and a fresh GitHub release download matched both hashes, size, tag target, and API digest.

## Fresh Local Gates

All commands ran from `/Users/shaneliszewski/MinecraftTest` on `dev`, with Java 21 and Packwiz paths loaded from `tools/versions.env` where applicable.

### Unit Tests

Command:

```bash
python3 -m unittest discover -s tools/tests -p 'test_*.py'
```

Result: 200 tests passed. Seventy-six live-install tests skipped intentionally in the clean-checkout mode. The same 200 tests passed with zero skips inside the fresh server installation.

### Quest Validation

Both static and runtime modes passed:

```text
VALIDATE QUESTS: OK (41 chapters, 283 quests, 307 tasks, 393 rewards)
```

### Pack Verification

Command:

```bash
./tools/verify-pack.sh
```

Result:

```text
VERIFY: ALL GREEN
```

Packwiz refresh was idempotent before the final commit. No Packwiz refresh ran after the commit.

### Dedicated Server

Command:

```bash
BOOT_TIMEOUT=600 ./tools/server-test.sh
```

Result:

```text
SERVER BOOT: OK
```

The final server run used Java 21.0.12, bound the test server to port 25599, reached `Done (31.558s)!`, passed all 200 installed live tests with zero skips, and exited cleanly.

### Authenticated State

- `pack.toml` SHA-256: `6bf8c2aff8cbebafca966a2b72022aeac44be7d8af775532ba6b89845b4b5ce8`
- `index.toml` SHA-256: `668bf754d9e88abc80023ae4c1d2b84c2e297fc18a9c3b8fecc60dbfc603ccbb`
- Installed artifact inventory: 157 entries, digest prefix `3fab3746`
- Mixin corpus: 305 archives, 261 configs, 2,286 common entries, 5 server entries, and 2,857 records
- Authenticated common-list client targets: 31, digest `cbb81775f677097560dff565346df0d9cb6a6b68af1f38a52ce9e43184ed6f59`
- Boot oracle result: 14 error records, 478 warning records, and 39 named residuals
- Fatal records: 0
- Generic IDAS `Item must not be minecraft:air` errors: 0

## Independent Review

The first final hardening review found no Critical issues and four Important false-green paths: incomplete GUI client-target classification, bare severe class names not entering all log projections, URI-encoded checkout paths remaining digest-dependent, and an `evidence` symlink escaping before the first write. It also found one Minor process-group test gap.

Fix commit `b7d30074ed97756bd2f4960f6ba797626b70cded` added focused failing regressions for all five findings, applied narrow fail-closed fixes, and reran every local gate listed above.

The scoped re-review marked all five findings addressed, found no new Critical or Important breakage, and returned `READY`. `git diff --check` and `bash -n tools/server-test.sh` also passed in that review.

## Manual Release Gates

These checks require a real client, accounts, multiple players, or live-host access. This report does not claim them:

- Clean Prism import and NeoForge client launch.
- Sub-three-minute title screen on the release client.
- Lithostitched physical-client compatibility.
- Quest book layout, theme, text wrapping, and icon rendering.
- Advancement, structure, dimension, energy, and fluid task completion in gameplay.
- Team progression, choice claiming, and manual item submission behavior.
- Released-client dedicated-server join and reconnect.
- Two-user voice chat, whitelist, firewall, update, rollback, and encrypted offsite recovery drills.

Plan 07 carries these items into the release-candidate acceptance matrix. Version `1.0.0` remains blocked until Shane records that matrix as passed against the exact release-candidate lineage.
