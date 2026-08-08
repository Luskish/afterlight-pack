# Plan 05 Task 5 Report

## Scope

Implemented six automation certification chapters and three Requisition Depot chapters:

- Logistics I
- Ore Loop I
- Autocrafting I
- Cross-Mod I
- Power I
- Infrastructure II
- Requisition Depot: Early
- Requisition Depot: Mid
- Requisition Depot: Late

## Progression

- The legacy Kinetics I finale retains every existing ID and now awards `afterlight_cert_kinetics_i`.
- Each new certification finale awards its exact stable stage.
- Infrastructure II checks all six prerequisite certification stages before four bulk quotas and an unattended recovery trial.
- Chapter 16 can now receive all seven certification stages without a dependency cycle.

## Mechanical Coherence Correction

- Ore Loop I now follows installed Mekanism recipes exactly: the Enrichment Chamber turns raw osmium into dust, the Energized Smelter turns dust into ingots, and the Formulaic Assemblicator compacts ingots into blocks.
- The Ore Loop I finale requires 32 `mekanism:block_osmium`, proving output from all three machine stages.
- Cross-Mod I now follows one connected material path: Create Crushing Wheels process `mekanism:raw_osmium` through the existing KubeJS bridge, a Mekanism Energized Smelter produces ingots, eight `immersiveengineering:conveyor_basic` units carry output, and two AE2 interfaces stock it.
- The Cross-Mod I batch remains 256 `mekanism:ingot_osmium`.
- Installed recipe JSON and item models verified `mekanism:formulaic_assemblicator`, `mekanism:block_osmium`, `create:crushing_wheel`, and `immersiveengineering:conveyor_basic` before catalog changes.

## Independent Review Corrections

- Every FTB Quests reward-table reference now uses the signed Java long representation of its 16-digit table ID. `SnbtLong.from_hex` performs the two's complement conversion and rejects values outside the signed 64-bit range.
- The legacy Ascendancy Cache references now emit `-7824471455364680287L`, and the late Depot reference now emits `-5073548148800006091L`. Tests parse every `choice`, `random`, `loot`, and `all_table` reference and require an existing reward table with the same signed value.
- Logistics I now follows Pipez 1.2.31 capabilities verified from the installed `Upgrade` bytecode. The Improved Upgrade teaches round-robin distribution first. The Advanced Upgrade follows and teaches filtering while retaining distribution controls.
- Frozen quest IDs and reward table IDs remain unchanged. Retired quest generators were scanned for stale unsigned literals and were not rerun.

### Scoped Review Round 1

- The first regression only searched three known unsigned decimal literals. It did not detect computed base-16 conversions in retired generators.
- `tools/gen-quests-ch3.py`, `tools/gen-quests-ch4.py`, and `tools/gen-quests-ch5.py` now route reward-table IDs through `SnbtLong.from_hex`. None of the retired generators were executed.
- The strengthened AST regression rejects positional or keyword base-16 `int` conversions, oversized integer constants, and any reward-table generator that omits the shared signed conversion.
- The Pipez regression now proves the full chain: Round-Robin Routing depends on Item Pipes, Filtered Route depends on Round-Robin Routing, and Overflow Safety depends on Filtered Route.
- The integrated side-group regression compares every dependency in all sixteen Story chapter files against every quest ID in the twelve new side chapters.
- The frozen Deep Vault opener now tells players to bring both the recovered Deep Vault Key and a hammer, matching its actual tasks.

## Depot

- Early, mid, and late exchanges consume 8, 16, and 32 Requisition Chits.
- Exchanges are repeatable with `repeat_cooldown: 5`. FTB Quests 2101.1.30 interprets the field as seconds.
- Each exchange grants one `choice` reward from its exact numeric `table_id`.
- Depot tables exclude every progression key, Gate schematic, blueprint, stabilizer precursor, and Ascendancy Seal.

## TDD Evidence

Focused tests failed before implementation for missing repeatable quest rendering, missing Task 5 chapters, missing stage rewards, missing Depot constants and tables, and the absent Kinetics I stage. Static validation later exposed an incorrect Chapter 9 dependency slug. A focused regression reproduced the resulting deterministic ID mismatch before the source slug was corrected.

## Verification

- `python3 -m unittest discover -s tools/tests -p 'test_*.py'`: 36 tests passed.
- Focused regression tests assert both exact recipe-valid machine paths and the five-second Depot cooldown.
- `python3 tools/build-quests.py`: 20 compiler-managed chapters written.
- Two consecutive builds produced digest `f0f6684d0f0ac5abd56ec3ed71ac0f11884798aa720cc5dd48b415bd720f55d6`.
- `python3 tools/validate-quests.py --static`: 29 chapters, 199 quests, 218 tasks, 282 rewards.
- Two consecutive sourced Packwiz refreshes produced digest `090d1ac40b1d5578724f903af8ea2067898778a3803302e97803c3af7b8438ec`.
- `BOOT_TIMEOUT=600 ./tools/server-test.sh`: `SERVER BOOT: OK`.
- FTB Quests loaded 6 chapter groups, 29 chapters, 199 quests, and 4 reward tables.
- KubeJS loaded 1/1 startup scripts and 5/5 server scripts with 0 script errors and 0 script warnings.
- Runtime item audit passed 162 registry IDs with a fresh boot nonce.
- `python3 tools/validate-quests.py`: exact full corpus passed with matching runtime proof.
- `./tools/verify-pack.sh`: `VERIFY: ALL GREEN`.

Scoped-review validation ran with Task 6 integration. All 47 quest tests passed, including the complete Pipez dependency chain, computed unsigned-long rejection, and signed reward-table resolution. Two deterministic active compiler builds produced digest `064682eb6f79609a8ad87f12586df09c50d6e8ae4fbfbdc982ba7b538f25f170`. Static and runtime quest validation passed with 41 chapters, 283 quests, 307 tasks, and 393 rewards. The fresh server boot printed `SERVER BOOT: OK`; FTB Quests loaded 6 groups, 41 chapters, 283 quests, and 6 reward tables; KubeJS loaded 1/1 startup and 5/5 server scripts with 0 errors and 0 warnings; and the runtime item audit passed 219 references with digest `42007a6a63cb672d6ed8f17062c6d470eb30a8e2a9de00bc0f701ecb6b3dd7cf`. `./tools/verify-pack.sh` printed `VERIFY: ALL GREEN`.

## Residuals

KubeJS script loading reports zero script errors and zero script warnings. Its later recipe inspection log contains 31 third-party fallback warnings, primarily Kaleidoscope Cookery carriers plus Oritech and Malum compatibility recipes. Minecraft's recipe manager reports 10 third-party Malum compatibility parse errors. FTB Quests logs zero warning or error lines. The AFTERLIGHT bridge reports 10 recipes added, 2 removed, 2 modified, and 0 failed recipes. These existing third-party recipe issues remain queued for the release hygiene pass and were not introduced by Task 5.

The certification and Depot implementation also retains three known FTB Quests platform limitations. Certification provenance is represented by possession checks, stage rewards, and explicit player checkmarks rather than machine-history telemetry. Depot quest progress is team-shared while each choice reward is claimed by the individual player. Consuming item tasks require manual submission in the quest interface. These limitations are documented behavior and are not release blockers.
