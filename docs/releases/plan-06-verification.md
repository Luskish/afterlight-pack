# AFTERLIGHT Plan 06 Verification

Date: 2026-08-09

Accepted Task 3 base: `1afce74c5a095695706adcc15d59d72657292d2a`

Status: review round 3 is based exactly on `3dba759f088410d44e92ddab01a767a61d5f6510` and has the fresh offline gate recorded below. A live boot on the exact round 3 final commit, exact-head independent review, two detached boots, exact-SHA CI, integration, `main` CI, and Pages parity remain open.

## Delivered Scope

- Story Chapters 17 through 20 preserve accepted Task 1 through Task 3 identities and dependencies, with one explicit exception: the repository-wide signed-safe migration changes every high-bit FTB identity plus its schema-owned references so FTB Quests can save them without replacement.
- `Beyond Afterlight` adds the six specified postgame quests, fourteen item tasks, and nine rewards.
- The three introductory postgame quests preserve every checked item. Only Kinetic Blessing, Lattice Blessing, and Industrial Blessing repeat, each with a 3,600-second cooldown and consuming submission tasks.
- Every Act IV and postgame quest uses explicit linear progression. The three Chapter 20 response quests remain optional and nonexclusive, and `Choice Is Not a Lock` still converges through `one_completed`.
- The final corpus is 46 chapters, 313 quests, 334 tasks, 436 rewards, and 6 reward tables.
- The existing authenticated Gate listener and marker now prove every empty and occupied mechanical slot, wrong schematic or special item, mirror, rotation, producer cardinality, Draconic Seal position, exact output, exact remainder, and Seal stack contract.
- Runtime helper self-tests and exact assertion cardinality bind the executable control flow to 14 positive checks, 368 negative checks, 54 remainder-slot checks, and 6 Seal-slot checks before marker emission.
- Repository and installed-file scans allow exactly the reviewed Seal references. Chapter 20 remains the only Seal reward source. New recipe, loot, trade, grant, quest-reward, or generated-data occurrences fail the server gate.
- Installed mod JARs and nested ZIP payloads are inspected recursively regardless of nested filename suffix. JSON and SNBT references are interpreted semantically, binary constants are scanned raw, reviewed duplicate ZIP aliases are authenticated, and archive expansion is bounded by per-member, per-archive, aggregate, depth, and compression-ratio limits. ZIP and ZIP64 member counts plus central-directory sizes are preflighted before `ZipFile` construction. Every scanned outer file uses one stable descriptor with link rejection, bounded reads, initial and final hashes, and device, inode, size, mtime, and ctime checks. Packwiz metadata labels are derived only from authenticated descriptor bytes, with a 1 MiB file limit and final path-identity verification.
- The exact nine-file KubeJS code corpus is authenticated by path and SHA-256 inventory. This closes arbitrary computed-ID, Unicode-escape, concatenation, and alias constructions that lexical matching cannot soundly evaluate. JavaScript and TypeScript reads are limited to 4 MiB per file and 8 MiB in aggregate, with at most 4,096 code files and 1 MiB of aggregate relative-path bytes. The complete Seal occurrence inventory is capped at 100,000 records, and repeated or oversized JSON and SNBT scalar matches share bounded digest descriptors instead of copying whole scalars per match. The two nonce-rendered installed audit files are accepted only when both are exact authenticated renders using the same nonce.
- Every FTB object ID is a signed-safe 16-character uppercase hexadecimal string beginning with `0` through `7`. The compiler covers chapter image IDs, image dependencies, image `open_quest` targets, quest-local dependency control-point keys, quest links, linked quests, autofocus, managed state, table references, and localization keys while preserving unrelated ID-shaped authored values and image prose. An independent validator checks those known identity containers without using the rewrite classifier. Migration preflights every journal operation and authenticated payload before repository mutation, persists duplicated checksummed journals and payloads under a root-independent state directory, writes through rehashed target-local temporary files, fsyncs state and target directories, and resumes interrupted writes, moves, missing targets, process death, and checkout relocation.
- The post-shutdown quest-identity oracle compares 3,135 canonical semantic records across repository and installed corpora. It binds `data.snbt`, every localization file path, key, scalar value, array position, and array text, plus chapter-group order, quest and dependency order, progression and repeat flags, cooldowns, complete ordered tasks and rewards, quantities, item consumption, Forge Energy limits, and complete ordered reward-table entries. Save normalization is directional and limited to the exact characterized item-task counts, item-reward counts, reward-table item types and weights, Iron's Spells component, glow encoding, three chapter order pairs, three reward-table order pairs, exact reward-table filename and title omissions, the three exact installed `data.snbt` defaults, and SNBT formatting. The fresh repository inventory SHA-256 is `6982a92d14bee2ab94613e3b41070c8bfe26a3ca2e0ebc2bfa6d6feda29eeede`.
- The legacy Foothold power task uses `forge_energy`, the exact type registered by the installed NeoForge FTB Quests artifact. The invalid `energy` alias previously loaded as an inert custom task and is now forbidden by regression.

## Test-First Evidence

The mandated focused command first ran before Task 4 production changes:

```bash
python3 -m unittest tools.tests.test_afterlight_quests.Plan06PostgameContractTests tools.tests.test_rc_hygiene_reliability.GateRecipeAdversarialTests -v
```

Result: exit 1, 8 tests run, 18 expected failures. The failures identified the missing postgame chapter, generated graph, verification record, adversarial assertions, final FTB load line, and Seal verifier.

Controller review then identified a potential label-only false green in the adversarial test. The revised tests own executable structural clauses, remove and no-op every clause under mutation, own the exact Seal occurrence inventory, and inject unauthorized sources into both repository and installed corpora across all six source classes.

Independent review then found four additional gaps: the final generated audit was newer than the accepted boot logs, installed `mods/` was outside the Seal scan, empty mechanical cells were skipped, and helper or loop control-flow mutations could evade the structural contract. A second RED cycle added six focused regressions. All six failed before the production fixes, then all six passed after the fixes. The widened Gate, finale, and postgame selection now passes all 47 tests. Two additional fail-closed regressions prove that encoded Seal JSON with invalid UTF-8 and unsafe archive directory paths are rejected. The real installed archive scan reports exactly 19 reviewed occurrences with SHA-256 `a192a2a64b08e23e60bfb154cd5cf52c7782859b1f664b69cfa6c70533b14126` in 9.07 seconds.

A second exact-commit review reproduced three computed KubeJS grant forms that the lexical scanner could not see, a deflated nested JAR stored as `payload.bin`, and a count-two remainder loop that could execute zero iterations. A third RED cycle binds all three computed-script forms to a full code-corpus digest, requires extensionless ZIP recursion, requires exactly nine count-two remainder slots, proves slot 7 was visited, and rejects no-op, early-return, and zero-iteration remainder mutations. All 47 widened Gate, finale, and postgame tests pass after these fixes. The changed Gate source, Packwiz index, and verifier subsequently completed the fresh full gate recorded below.

The next review found two further scanner bypasses: a ZIP with arbitrary prefixed bytes and compressed GZip NBT. Regressions now cover prefixed archives, GZip and zlib payloads, concatenated streams, trailing payloads, malformed compression, nested depth, member counts, expanded-byte budgets, and compression ratios. The real installed Twilight Forest corpus also proved that valid GZip NBT can contain benign trailing bytes, so the scanner recursively inspects trailing content instead of rejecting or ignoring it.

The first post-fix boot then exposed runtime data corruption rather than a test-only issue. FTB Quests rewrote every high-bit ID because its installed bytecode uses signed `Long.parseLong(..., 16)`, and it replaced the affected Seal reward with a default apple. Three signed-safe RED tests drove the compiler migration, then the complete 586-occurrence corpus was regenerated. The next boot exposed the retired Act I `energy` alias becoming `custom`; installed bytecode proved `forge_energy` is the registered NeoForge type. Both defects are now covered by static and post-shutdown semantic regressions.

Independent review then found that the semantic oracle compared identity subsets, signed-ID migration could not recover from mixed interrupted state, migration rewrote arbitrary ID-shaped authored strings, and oversized raw Seal files were allocated before the limit check. Focused RED tests reproduced every issue, and the resulting candidate completed the historical live gate recorded below. Review round 2 supersedes that oracle and transaction implementation.

Review round 2 reproduced 30 focused failures across 16 tests before production changes. The RED set covered unbound data and localization semantics, broad or symmetric normalization, incomplete FTB identity schema, reused validation logic, non-durable and partially preflighted migration state, blocked recovery paths, unbounded code and occurrence scans, ZIP metadata accepted before preflight, and stable-descriptor race gaps. One additional occurrence-bound regression failed before its focused production fix.

Review round 3 reproduced 12 focused failures across eight test methods before production changes. The RED set proved that migration and independent validation omitted quest-local dependency control points plus image dependency and `open_quest` identities, semantic descriptors retained 67,324,928 bytes for two 32 KiB repeated scalars, metadata labels followed symlinks and accepted oversize and path replacement, and the code corpus accepted excessive file counts and aggregate path bytes. The bytecode-shaped FTB fixtures preserve arbitrary image data and prose while exercising each real schema location.

## Review Round 2 Offline Gate

The following fresh commands ran in the isolated review worktree based exactly on `a1f0b39fddb5a96bf99242d0dfc828c14501b918`:

```text
Ran 89 focused tests in 16.895s
OK (skipped=2)
BUILD QUESTS: OK (37 compiler-managed chapters written)
GENERATED STATE: CLEAN
VALIDATE QUESTS: OK (46 chapters, 313 quests, 334 tasks, 436 rewards)
Ran 302 offline tests in 36.998s
OK (skipped=77)
QUEST IDENTITY INVENTORY: records=3135 sha256=6982a92d14bee2ab94613e3b41070c8bfe26a3ca2e0ebc2bfa6d6feda29eeede
```

No quest content, manifest, Packwiz metadata, mod, KubeJS gameplay logic, or release version changed in review round 2. Any live evidence from that parent commit does not validate the review round 3 child.

## Review Round 3 Offline Gate

The following fresh commands ran in the isolated review worktree based exactly on `3dba759f088410d44e92ddab01a767a61d5f6510`:

```text
Ran 95 focused tests in 18.283s
OK (skipped=2)
BUILD QUESTS: OK (37 compiler-managed chapters written)
GENERATED STATE: CLEAN
Ran 308 offline tests in 38.384s
OK (skipped=77)
VALIDATE QUESTS: OK (46 chapters, 313 quests, 334 tasks, 436 rewards)
```

No quest content, manifest, Packwiz metadata, mod, KubeJS gameplay logic, or release version changed. No live boot has run on the exact review round 3 final commit. The parent commit's live run is not evidence for this child. A fresh exact-final-commit live boot remains pending.

## Prior Automated Gate

The following local gate completed on 2026-08-09 at candidate commit `05041ecd72c65b3aa0fe4552f90a2223e0c353df`:

```text
BUILD QUESTS: OK (37 compiler-managed chapters written)
PACK SHA-256: 3578c0879f3c8b54ea90d1ee0475bb1e6f5eb29fa14868c3ed862458538ab8f1
INDEX SHA-256: 07ce0081692e373baf42e78a3b26d347120632ee9ebf26510fa9f605a911009f
Ran 283 offline tests in 31.275s
OK (skipped=77)
VALIDATE QUESTS: OK (46 chapters, 313 quests, 334 tasks, 436 rewards)
VERIFY: ALL GREEN
PROVENANCE: OK server-artifacts=157 sha256=3fab3746f050ff8fe52b09ab565df5afca72136d778c5dd9321c4eb7bd84bf67
SEAL SOURCES: OK occurrences=19 sha256=c3be08148ed996416c63983626ef942f65baba4f98c59805606208be0e8d9c67 code-corpus-sha256=7ce66ae56eeb28aebdf1494d2541aa1e05edd05b300ec4b92537a296b61cc258
QUEST AUDIT BYTES: OK sha256=7fb88229d850fb55934cf66144557d7b6ebb23151ee635fd9d18d2b0ef1e2a4a
GATE AUDIT RENDER: OK sha256=20e2e83a4f7bd14b0f5aca42dff1ae257444356a42f67164d9ca4221a4354983
GATE AUDIT BYTES: OK sha256=20e2e83a4f7bd14b0f5aca42dff1ae257444356a42f67164d9ca4221a4354983
BOOT ORACLE: OK errors=14 warnings=477 named-residuals=39
Ran 283 live tests in 148.039s
OK
SERVER BOOT: OK
VALIDATE QUESTS: OK (46 chapters, 313 quests, 334 tasks, 436 rewards)
```

The authenticated boot was run `local-20260809T185258Z-69291-30378` with nonce `1786301579-69291-12094`. Its Gate marker reported source SHA-256 `9d05c0640f055f769c0c1ab640e75f316f768293728cfe4c3e7505d5becae725`, exact recipe count 11, and the same nonce. The rendered installed Gate audit matched SHA-256 `20e2e83a4f7bd14b0f5aca42dff1ae257444356a42f67164d9ca4221a4354983`. The rendered quest audit bytes matched SHA-256 `7fb88229d850fb55934cf66144557d7b6ebb23151ee635fd9d18d2b0ef1e2a4a`; its marker reported digest `a52a2bd35abdf4241efe6be43a83e56e16dc8d0030f116be3674e67dd44242c2`, 237 validated item IDs, and the same nonce. The exact FTB line was `Loaded 6 chapter groups, 46 chapters, 313 quests, 6 reward tables`. All three files under `server-test/logs/kubejs/` contained zero `ERROR` or `FATAL` records.

The server reached `Done (29.321s)!`, then saved and shut down cleanly before the semantic identity comparison. Runtime quest validation ran inside the authenticated 283-test live suite, closing the stale-evidence review finding. The Gate marker remains single, source-authenticated, nonce-authenticated, and inside the post-`Done`, pre-FTB window. This document does not claim controller-owned exact-head independent review, detached boots, remote integration, CI, or Pages evidence.

## Team-Safety Proof

Static contracts require all of the following:

- `default_reward_team=false`.
- No `team_reward` or `team_stage` field in Act IV or postgame.
- No Act IV or postgame `gamestage` task.
- Explicit linear progression on every endgame quest.
- Exactly three optional Chapter 20 responses with no exclusivity field.
- Exact `one_completed` convergence into `Choice Is Not a Lock`.
- Exactly one count-one Seal reward, owned by Chapter 20 finale `7E6A0AC031F7F484`.
- No postgame quest is a dependency of Chapter 20 or any earlier Story quest.

These static facts do not prove FTB Teams behavior with real clients.

## Plan 07 Manual Acceptance

| Scenario | Required manual procedure | Status |
|---|---|---|
| Two-player claim | Complete the finale as a two-player team, then verify player-local reward claiming and exact Seal counts. | NOT RUN, Plan 07 manual acceptance |
| Late join | Add a second player after team story completion, then verify visible progress and reward eligibility. | NOT RUN, Plan 07 manual acceptance |
| Replay | Exercise repeat and reset behavior without duplicating the one-time Seal reward. | NOT RUN, Plan 07 manual acceptance |
| Team change | Leave, join, and reform teams around completed finale state, then inspect progress and reward ownership. | NOT RUN, Plan 07 manual acceptance |
| Seal transfer | Transfer one Seal between players and verify all three authenticated Draconic recipes for the recipient. | NOT RUN, Plan 07 manual acceptance |

No manual client, multiplayer, voice, gameplay, update, rollback, or VPS behavior is accepted by this record.

## Known Boundary

The Seal has maximum stack size one in supported gameplay. The live audit separately characterizes KubeJS `KeepAction` behavior for an invalid operator-created count-two stack. That invalid state is not a supported crafting path.
