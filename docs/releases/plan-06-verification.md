# AFTERLIGHT Plan 06 Verification

Date: 2026-08-09

Accepted Task 3 base: `1afce74c5a095695706adcc15d59d72657292d2a`

Status: Task 4 second-review fix commit `0ba8e8c5cee0ca3bff92883fc1bf654ac83ae75b` and the complete local post-fix gate are complete. Exact-commit re-reviews, detached boots, exact-SHA CI, the `main` fast-forward, and Pages parity are not yet claimed here.

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

## Test-First Evidence

The mandated focused command first ran before Task 4 production changes:

```bash
python3 -m unittest tools.tests.test_afterlight_quests.Plan06PostgameContractTests tools.tests.test_rc_hygiene_reliability.GateRecipeAdversarialTests -v
```

Result: exit 1, 8 tests run, 18 expected failures. The failures identified the missing postgame chapter, generated graph, verification record, adversarial assertions, final FTB load line, and Seal verifier.

Controller review then identified a potential label-only false green in the adversarial test. The revised tests own executable structural clauses, remove and no-op every clause under mutation, own the exact Seal occurrence inventory, and inject unauthorized sources into both repository and installed corpora across all six source classes.

Independent review then found four additional gaps: the final generated audit was newer than the accepted boot logs, installed `mods/` was outside the Seal scan, empty mechanical cells were skipped, and helper or loop control-flow mutations could evade the structural contract. A second RED cycle added six focused regressions. All six failed before the production fixes, then all six passed after the fixes. The widened Gate, finale, and postgame selection now passes all 47 tests. Two additional fail-closed regressions prove that encoded Seal JSON with invalid UTF-8 and unsafe archive directory paths are rejected. The real installed archive scan reports exactly 19 reviewed occurrences with SHA-256 `a192a2a64b08e23e60bfb154cd5cf52c7782859b1f664b69cfa6c70533b14126` in 9.07 seconds.

A second exact-commit review reproduced three computed KubeJS grant forms that the lexical scanner could not see, a deflated nested JAR stored as `payload.bin`, and a count-two remainder loop that could execute zero iterations. A third RED cycle binds all three computed-script forms to a full code-corpus digest, requires extensionless ZIP recursion, requires exactly nine count-two remainder slots, proves slot 7 was visited, and rejects no-op, early-return, and zero-iteration remainder mutations. All 47 widened Gate, finale, and postgame tests pass after these fixes. Final runtime evidence is intentionally withheld until the changed Gate source, Packwiz index, and verifier complete a fresh full gate.

## Automated Gate

All earlier runtime evidence is superseded because the Gate source, Packwiz index, and Seal verifier changed after those runs. The final local post-fix gate completed on 2026-08-09 with these exact outcomes:

```text
BUILD QUESTS: OK (37 compiler-managed chapters written)
PACKWIZ STATE: ef3c607f4956e55683a8ca4f6242b53bc07e69cf6b47a00ea69daafddaa3299e
Ran 267 offline tests in 24.767s
OK (skipped=77)
VALIDATE QUESTS: OK (46 chapters, 313 quests, 334 tasks, 436 rewards)
VERIFY: ALL GREEN
PROVENANCE: OK server-artifacts=157 sha256=3fab3746f050ff8fe52b09ab565df5afca72136d778c5dd9321c4eb7bd84bf67
SEAL SOURCES: OK occurrences=19 sha256=a192a2a64b08e23e60bfb154cd5cf52c7782859b1f664b69cfa6c70533b14126 code-corpus-sha256=381c9b2bedf2ff5915e7b255bb16ec77e2e3b60c53e998d59711baa19555a0d7
BOOT ORACLE: OK errors=14 warnings=477 named-residuals=39
Ran 267 live tests in 118.931s
OK
SERVER BOOT: OK
VALIDATE QUESTS: OK (46 chapters, 313 quests, 334 tasks, 436 rewards)
```

The authenticated boot used nonce `1786291573-59071-31827`. Its Gate marker reported source SHA-256 `9d05c0640f055f769c0c1ab640e75f316f768293728cfe4c3e7505d5becae725`, exact recipe count 11, and the same nonce. The rendered installed Gate audit matched SHA-256 `f38a76472792c908e97c3e0cd32b4db29a98d49f31d5fc2449d8421b26c7a945`. The rendered quest audit bytes matched SHA-256 `b6be89a35c7c5ea2f960fccd48f58fd813b5c86e2caf792fc3d06a196486a6e7`; its marker reported digest `be3d18091a1e0cc0e81f2ace182b104da15e70170c7bd4e7a4354156ba13f7b2`, 237 validated item IDs, and the same nonce. The exact FTB line was `Loaded 6 chapter groups, 46 chapters, 313 quests, 6 reward tables`. `server-test/logs/kubejs/server.log` contained zero `ERROR` or `FATAL` records.

The generated quest audit mtime was `1786290866`; both authoritative logs were newer at `1786291668`. Runtime quest validation ran immediately after `SERVER BOOT: OK`, closing the stale-evidence review finding. The Gate marker remains single, source-authenticated, nonce-authenticated, and inside the post-`Done`, pre-FTB window. This document does not claim controller-owned exact-commit re-review, detached boot, remote integration, or Pages evidence.

## Team-Safety Proof

Static contracts require all of the following:

- `default_reward_team=false`.
- No `team_reward` or `team_stage` field in Act IV or postgame.
- No Act IV or postgame `gamestage` task.
- Explicit linear progression on every endgame quest.
- Exactly three optional Chapter 20 responses with no exclusivity field.
- Exact `one_completed` convergence into `Choice Is Not a Lock`.
- Exactly one count-one Seal reward, owned by Chapter 20 finale `FE6A0AC031F7F484`.
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
