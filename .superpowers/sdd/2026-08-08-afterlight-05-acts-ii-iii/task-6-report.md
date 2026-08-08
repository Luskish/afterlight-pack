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

## Remaining Concerns

- Advancement, structure, dimension, and `one_completed` task completion still require one real-client acceptance pass.
- Certification provenance uses possession checks, stages, and explicit checkmarks rather than machine-history telemetry.
- Depot progress is team-shared while each choice reward is claimed by the individual player.
- Consuming item tasks require manual submission in the quest interface.
- Existing third-party recipe parsing residuals remain assigned to the release hygiene pass.
