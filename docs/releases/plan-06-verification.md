# AFTERLIGHT Plan 06 Verification

Date: 2026-08-09

Accepted Task 3 base: `1afce74c5a095695706adcc15d59d72657292d2a`

Status: the current Task 4 candidate and its complete local post-fix gate are complete. Commit `0ba8e8c5cee0ca3bff92883fc1bf654ac83ae75b` is superseded by the signed-safe ID, compressed-archive, runtime task-type, and post-save identity fixes recorded here. Exact-commit re-reviews, detached boots, exact-SHA CI, the `main` fast-forward, and Pages parity are not yet claimed here.

## Delivered Scope

- Story Chapters 17 through 20 complete Act IV without changing any accepted Task 1 through Task 3 ID or dependency.
- `Beyond Afterlight` adds the six specified postgame quests, fourteen item tasks, and nine rewards.
- The three introductory postgame quests preserve every checked item. Only Kinetic Blessing, Lattice Blessing, and Industrial Blessing repeat, each with a 3,600-second cooldown and consuming submission tasks.
- Every Act IV and postgame quest uses explicit linear progression. The three Chapter 20 response quests remain optional and nonexclusive, and `Choice Is Not a Lock` still converges through `one_completed`.
- The final corpus is 46 chapters, 313 quests, 334 tasks, 436 rewards, and 6 reward tables.
- The existing authenticated Gate listener and marker now prove every empty and occupied mechanical slot, wrong schematic or special item, mirror, rotation, producer cardinality, Draconic Seal position, exact output, exact remainder, and Seal stack contract.
- Runtime helper self-tests and exact assertion cardinality bind the executable control flow to 14 positive checks, 368 negative checks, 54 remainder-slot checks, and 6 Seal-slot checks before marker emission.
- Repository and installed-file scans allow exactly the reviewed Seal references. Chapter 20 remains the only Seal reward source. New recipe, loot, trade, grant, quest-reward, or generated-data occurrences fail the server gate.
- Installed mod JARs and nested ZIP payloads are inspected recursively regardless of nested filename suffix. JSON and SNBT references are interpreted semantically, binary constants are scanned raw, reviewed duplicate ZIP aliases are authenticated, and archive expansion is bounded by per-member, per-archive, aggregate, depth, and compression-ratio limits.
- The exact nine-file KubeJS code corpus is authenticated by path and SHA-256 inventory. This closes arbitrary computed-ID, Unicode-escape, concatenation, and alias constructions that lexical matching cannot soundly evaluate. The two nonce-rendered installed audit files are accepted only when both are exact authenticated renders using the same nonce.
- Every FTB object ID is a signed-safe 16-character uppercase hexadecimal string beginning with `0` through `7`. The compiler migrates high-bit IDs and their serialized negative reward-table references, rejects collisions, and validates the complete corpus before generation. This prevents FTB Quests 2101.1.30 from silently replacing IDs during save.
- The post-shutdown quest-identity oracle compares 1,525 semantic records across repository and installed corpora. It binds groups, chapter files, quests, dependencies, tasks, rewards, reward tables, target items, table references, stages, and both authored EnderIO conduit components while ignoring formatting and injected default item components.
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

## Automated Gate

All earlier runtime evidence is superseded because the Gate source, Packwiz index, and Seal verifier changed after those runs. The final local post-fix gate completed on 2026-08-09 with these exact outcomes:

```text
BUILD QUESTS: OK (37 compiler-managed chapters written)
PACK SHA-256: 3578c0879f3c8b54ea90d1ee0475bb1e6f5eb29fa14868c3ed862458538ab8f1
INDEX SHA-256: 07ce0081692e373baf42e78a3b26d347120632ee9ebf26510fa9f605a911009f
Ran 277 offline tests in 27.801s
OK (skipped=77)
VALIDATE QUESTS: OK (46 chapters, 313 quests, 334 tasks, 436 rewards)
VERIFY: ALL GREEN
PROVENANCE: OK server-artifacts=157 sha256=3fab3746f050ff8fe52b09ab565df5afca72136d778c5dd9321c4eb7bd84bf67
SEAL SOURCES: OK occurrences=19 sha256=c3be08148ed996416c63983626ef942f65baba4f98c59805606208be0e8d9c67 code-corpus-sha256=7ce66ae56eeb28aebdf1494d2541aa1e05edd05b300ec4b92537a296b61cc258
QUEST IDENTITY: OK records=1525 sha256=ebd3ece8d499fe8e50e8b1881f320c7ecf9fa40de947717c542d83c0fa6e4371
BOOT ORACLE: OK errors=14 warnings=477 named-residuals=39
Ran 277 live tests in 142.083s
OK
SERVER BOOT: OK
VALIDATE QUESTS: OK (46 chapters, 313 quests, 334 tasks, 436 rewards)
```

The authenticated boot was run `local-20260809T174756Z-20412-21427` with nonce `1786297677-20412-8297`. Its Gate marker reported source SHA-256 `9d05c0640f055f769c0c1ab640e75f316f768293728cfe4c3e7505d5becae725`, exact recipe count 11, and the same nonce. The rendered installed Gate audit matched SHA-256 `81824ad37dff50d804a145f2c39b7c76680f4d8528a237ee2353b0647b4b15bb`. The rendered quest audit bytes matched SHA-256 `8dfc0b717001a15658387830d06b8ab519690d72601f0ac6d94d28bb618b80ea`; its marker reported digest `a52a2bd35abdf4241efe6be43a83e56e16dc8d0030f116be3674e67dd44242c2`, 237 validated item IDs, and the same nonce. The exact FTB line was `Loaded 6 chapter groups, 46 chapters, 313 quests, 6 reward tables`. `server-test/logs/kubejs/server.log` contained zero `ERROR` or `FATAL` records.

The server reached `Done (26.440s)!`, then saved and shut down cleanly before the semantic identity comparison. Runtime quest validation ran inside the authenticated 277-test live suite, closing the stale-evidence review finding. The Gate marker remains single, source-authenticated, nonce-authenticated, and inside the post-`Done`, pre-FTB window. This document does not claim controller-owned exact-commit re-review, detached boot, remote integration, or Pages evidence.

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
