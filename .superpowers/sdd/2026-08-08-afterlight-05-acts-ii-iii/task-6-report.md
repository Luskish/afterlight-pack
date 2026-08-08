# Plan 05 Task 6 Report

## Scope

- Added four Undercurrent chapters: Names in the Circuit, Spells Under Load, The Soul Ledger, and Resonance Proof.
- Added four optional Deep Vault chapters: Current Below, Black Distillate, Hot Cell, and Quantum Burden.
- Added four Atlas chapters: Courts Above and Beyond, Root and Echo, Edges of the Map, and Corrupted Guardians.
- Added rare and epic Ascendancy Cache reward tables with progression-safe materials.
- Patched the frozen Deep Vault opener without changing any existing chapter, quest, task, or reward ID.

## Progression Safety

- The Deep Vault key task is non-consuming and awards `afterlight_deep_vault` from the existing opener.
- Every magic branch starts after the legacy Ars Nouveau finale. Resonance Proof uses `dependency_requirement: "one_completed"` on only the three branch finales, so Ars plus exactly one additional discipline is sufficient.
- Resonance Proof rewards exactly one `kubejs:undercurrent_stabilizer_precursor` and stage `afterlight_stabilizer_ready`. No quest requires the precursor as an input.
- Deep Vault chapters remain optional and have no story dependencies.
- Rare and epic caches contain no Deep Vault keys, Gate items, schematics, stabilizer items, Ascendancy Seals, creative items, or machines that bypass progression.

## Compiler and Review Corrections

- `QuestSpec` now renders the installed FTB Quests dependency requirement field and rejects unsupported modes.
- `SnbtLong.from_hex` converts 16-digit reward table IDs to signed Java longs and enforces the signed 64-bit range.
- Tests parse every `choice`, `random`, `loot`, and `all_table` reference and require a matching reward table definition.
- Logistics I now follows installed Pipez 1.2.31 capabilities: Improved teaches distribution, then Advanced teaches filtering.
- All frozen legacy Ascendancy Cache references were converted to signed Java long form without changing IDs.

### Scoped Review Round 1

- Retired Chapter 3, Chapter 4, and Chapter 5 generators can no longer compute unsigned reward-table longs. Each uses the shared `SnbtLong.from_hex` conversion and remains retired.
- The generator regression now detects computed base-16 conversions instead of checking only known decimal literals.
- Pipez coverage now asserts both missing graph edges around the existing Improved-to-Advanced capability sequence.
- The optionality regression now compares every dependency from all sixteen Story chapter files against all 84 quest IDs in the twelve new side chapters, not only their finales.
- The Deep Vault opener localization now explicitly directs the player to bring the recovered Deep Vault Key and a hammer while preserving every existing ID.

## Verification

- `python3 -m unittest discover -s tools/tests -p 'test_*.py'`: 47 tests passed.
- Two consecutive `python3 tools/build-quests.py` runs wrote 32 managed chapters and produced digest `a469b227c0884afc55c7dd6c86f47f49a0a92f10b22c2697ebd2cdefcabf308e`.
- `python3 tools/validate-quests.py --static`: 41 chapters, 283 quests, 307 tasks, and 393 rewards.
- Two consecutive sourced Packwiz refreshes produced digest `68991603cf4c3ad0bf468424d517a897a63eaf1390b07ecb297d82d6def7d8bb`.
- `BOOT_TIMEOUT=600 ./tools/server-test.sh`: `SERVER BOOT: OK`.
- FTB Quests loaded 6 chapter groups, 41 chapters, 283 quests, and 6 reward tables.
- KubeJS loaded 1/1 startup scripts and 5/5 server scripts with 0 errors and 0 warnings.
- The runtime quest item audit passed all 219 item and icon references with fresh digest `b6b6935eafe173d8b382674ecfbe9f309b18d134c66c881a1c75ebe73d168d52`.
- `python3 tools/validate-quests.py`: exact full corpus passed with the fresh runtime proof.
- `./tools/verify-pack.sh`: `VERIFY: ALL GREEN`.

### Scoped Review Round 1 Verification

- Four focused regressions passed for retired generator conversion, the complete Pipez chain, all-side-quest optionality, and Deep Vault opener guidance.
- `python3 -m unittest discover -s tools/tests -p 'test_*.py'`: 47 tests passed.
- Two consecutive active compiler builds produced digest `064682eb6f79609a8ad87f12586df09c50d6e8ae4fbfbdc982ba7b538f25f170`.
- Static and runtime validation both passed with 41 chapters, 283 quests, 307 tasks, and 393 rewards.
- The fresh server boot printed `SERVER BOOT: OK`. FTB Quests loaded 6 groups, 41 chapters, 283 quests, and 6 reward tables with 0 FTB Quests warning or error lines.
- KubeJS loaded 1/1 startup and 5/5 server scripts with 0 errors and 0 warnings. The runtime audit passed 219 references with digest `42007a6a63cb672d6ed8f17062c6d470eb30a8e2a9de00bc0f701ecb6b3dd7cf`.
- `./tools/verify-pack.sh` printed `VERIFY: ALL GREEN`; its Packwiz refresh check was idempotent.

## Remaining Concerns

- Advancement, structure, dimension, and `one_completed` task completion still require one real-client acceptance pass.
- Certification provenance uses possession checks, stages, and explicit checkmarks rather than machine-history telemetry.
- Depot progress is team-shared while each choice reward is claimed by the individual player.
- Consuming item tasks require manual submission in the quest interface.
- Existing third-party recipe parsing residuals remain assigned to the release hygiene pass.
