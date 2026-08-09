# AFTERLIGHT Plan 06 Verification

Date: 2026-08-09

Accepted Task 3 base: `1afce74c5a095695706adcc15d59d72657292d2a`

Status: Task 4 implementation and local precommit verification are complete. Independent review, detached postcommit boots, exact-SHA CI, the `main` fast-forward, and Pages parity are controller-owned gates and are not claimed here.

## Delivered Scope

- Story Chapters 17 through 20 complete Act IV without changing any accepted Task 1 through Task 3 ID or dependency.
- `Beyond Afterlight` adds the six specified postgame quests, fourteen item tasks, and nine rewards.
- The three introductory postgame quests preserve every checked item. Only Kinetic Blessing, Lattice Blessing, and Industrial Blessing repeat, each with a 3,600-second cooldown and consuming submission tasks.
- Every Act IV and postgame quest uses explicit linear progression. The three Chapter 20 response quests remain optional and nonexclusive, and `Choice Is Not a Lock` still converges through `one_completed`.
- The final corpus is 46 chapters, 313 quests, 334 tasks, 436 rewards, and 6 reward tables.
- The existing authenticated Gate listener and marker now prove every occupied mechanical slot, wrong schematic or special item, mirror, rotation, producer cardinality, Draconic Seal position, exact output, exact remainder, and Seal stack contract.
- Repository and installed-file scans allow exactly the reviewed Seal references. Chapter 20 remains the only Seal reward source. New recipe, loot, trade, grant, quest-reward, or generated-data occurrences fail the server gate.

## Test-First Evidence

The mandated focused command first ran before Task 4 production changes:

```bash
python3 -m unittest tools.tests.test_afterlight_quests.Plan06PostgameContractTests tools.tests.test_rc_hygiene_reliability.GateRecipeAdversarialTests -v
```

Result: exit 1, 8 tests run, 18 expected failures. The failures identified the missing postgame chapter, generated graph, verification record, adversarial assertions, final FTB load line, and Seal verifier.

Controller review then identified a potential label-only false green in the adversarial test. The revised tests own executable structural clauses, remove and no-op every clause under mutation, own the exact Seal occurrence inventory, and inject unauthorized sources into both repository and installed corpora across all six source classes.

## Automated Gate

The final local precommit gate completed on 2026-08-09 with these exact outcomes:

```text
Loaded 6 chapter groups, 46 chapters, 313 quests, 6 reward tables
VALIDATE QUESTS: OK (46 chapters, 313 quests, 334 tasks, 436 rewards)
VERIFY: ALL GREEN
Ran 265 tests in 111.185s
OK
SERVER BOOT: OK
```

The authenticated boot used nonce `1786285486-97067-12779`. Its Gate marker reported source SHA-256 `e7308ad2cbeb93494fc10ebe91ad5bf07429389243ed8e50fc4b522678a39c59`, exact recipe count 11, and the same nonce. The quest-item marker reported digest `be3d18091a1e0cc0e81f2ace182b104da15e70170c7bd4e7a4354156ba13f7b2`, 237 validated item IDs, and the same nonce. `server-test/logs/kubejs/server.log` contained zero `ERROR` or `FATAL` records.

The Gate marker remains single, source-authenticated, nonce-authenticated, and inside the post-`Done`, pre-FTB window. This document does not claim controller-owned postcommit or remote integration evidence.

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
