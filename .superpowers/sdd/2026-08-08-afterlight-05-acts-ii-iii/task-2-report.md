# Plan 05 Task 2 Report

Date: 2026-08-08
Branch: `dev`
Task: Plan 05 Progression Items

## Scope Delivered

- Registered exactly seven new KubeJS progression items in `kubejs/startup_scripts/afterlight/registry.js`.
- Added exact English localization entries in `kubejs/assets/kubejs/lang/en_us.json`.
- Preserved the seven committed 32x32 PNG textures without modification.
- Extended `KUBEJS_ITEM_ALLOWLIST` with all seven exact item IDs.
- Changed runtime audit generation so every allowlisted KubeJS item is audited before any quest references it.
- Changed runtime validation to use the same allowlist-inclusive item set and count as audit generation.
- Regenerated `kubejs/server_scripts/afterlight/generated_quest_item_audit.js`.
- Refreshed `index.toml` and the index hash in `pack.toml`.
- Updated `docs/HANDOFF.md` with the completed Task 2 checkpoint and Task 3 recovery point.
- Did not modify quests or add recipes.

## Registered Items

| Item ID | Display Name | Rarity | Stack | Glow |
|---|---|---:|---:|---:|
| `kubejs:deep_vault_key` | Deep Vault Key | rare | 1 | true |
| `kubejs:schematic_kinetic_frame` | Kinetic Frame Schematic | epic | 1 | true |
| `kubejs:schematic_industrial_anchor` | Industrial Anchor Schematic | epic | 1 | true |
| `kubejs:schematic_isotopic_core` | Isotopic Core Schematic | epic | 1 | true |
| `kubejs:schematic_lattice_matrix` | Lattice Matrix Schematic | epic | 1 | true |
| `kubejs:gate_blueprint` | Gate Blueprint | epic | 1 | true |
| `kubejs:undercurrent_stabilizer_precursor` | Undercurrent Stabilizer Precursor | rare | 16 | false |

## Texture Check

The seven supplied textures were inspected with `file`. Every file is a valid 32x32 PNG. Six report RGBA color data. `deep_vault_key.png` reports an 8-bit colormap. No texture was changed.

## TDD Evidence

### Baseline

Command:

```text
python3 -m unittest tools.tests.test_afterlight_quests -v
```

Result before implementation: 19 tests passed.

### Allowlist Audit Red Phase

Added `test_runtime_item_audit_includes_allowlisted_kubejs_items_without_quests`. The test writes an empty compiler catalog and requires every exact `KUBEJS_ITEM_ALLOWLIST` entry in the generated runtime audit.

The focused test failed before the implementation with:

```text
AssertionError: '  "kubejs:requisition_chit"' not found in ...
const AFTERLIGHT_QUEST_ITEM_IDS = []
```

### Allowlist Audit Green Phase

Changed `_quest_item_ids()` to return the sorted union of quest item references and `KUBEJS_ITEM_ALLOWLIST`. The focused test passed, followed by all 20 tests.

### Runtime Marker Count Red Phase

The first default validator run after the server boot exposed a count mismatch:

```text
ERROR: runtime item audit missing or stale: expected digest 783685a43be5d60ea1f3436695e43e5f3c7751c27c114ad1918b7a95651974d1
VALIDATE QUESTS: FAILED (1 errors)
```

Root cause: generated audit markers used the allowlist-inclusive set of 59 IDs, while `validate_quests()` still expected the old quest-only count of 51. Updated the runtime marker tests to use the allowlist-inclusive count. The focused validator test failed before the production fix.

### Runtime Marker Count Green Phase

Changed runtime validation to call `_quest_item_ids()` so generation, digesting, and marker validation share one item set. The focused test passed, all 20 tests passed, and the default runtime validator passed.

## Generated Audit Coverage

The generated audit contains exactly nine `kubejs:` IDs:

1. `kubejs:ascendancy_seal`
2. `kubejs:deep_vault_key`
3. `kubejs:gate_blueprint`
4. `kubejs:requisition_chit`
5. `kubejs:schematic_industrial_anchor`
6. `kubejs:schematic_isotopic_core`
7. `kubejs:schematic_kinetic_frame`
8. `kubejs:schematic_lattice_matrix`
9. `kubejs:undercurrent_stabilizer_precursor`

The successful runtime marker was:

```text
[AFTERLIGHT QUEST ITEM AUDIT] OK 783685a43be5d60ea1f3436695e43e5f3c7751c27c114ad1918b7a95651974d1 59 1786204251-56476-28904
```

The marker covers 59 total quest and allowlisted registry IDs. Because the generated list contains all nine KubeJS IDs and the marker passed, all nine existed in the runtime item registry.

## Server Log Inspection

KubeJS startup log:

```text
Loaded script startup_scripts:afterlight/registry.js in 0.099 s
Loaded 1/1 KubeJS startup scripts in 0.49 s with 0 errors and 0 warnings
```

KubeJS server log:

```text
Loaded script server_scripts:afterlight/generated_quest_item_audit.js in 0.002 s
Loaded 5/5 KubeJS server scripts in 0.018 s with 0 errors and 0 warnings
Added 10 recipes, removed 2 recipes, modified 2 recipes, with 0 failed recipes taking 968 ms in total
```

The server log also contains recipe parser warnings for Malum, Oritech, Kaleidoscope Cookery, and Incendium content. No KubeJS script error was reported, and the recipe modification summary reports 0 failed recipes.

FTB Quests load summary:

```text
loaded translation tables for 1 language(s)
Loaded 6 chapter groups, 9 chapters, 56 quests, 1 reward tables
```

## Verification Results

```text
python3 tools/build-quests.py
BUILD QUESTS: OK (0 compiler-managed chapters written)

python3 tools/validate-quests.py --static
VALIDATE QUESTS: OK (9 chapters, 56 quests, 56 tasks, 93 rewards)

source tools/versions.env && export PATH="$PATH_EXTRA:$PATH" && packwiz refresh
Index refreshed!

BOOT_TIMEOUT=600 ./tools/server-test.sh
SERVER BOOT: OK

python3 tools/validate-quests.py
VALIDATE QUESTS: OK (9 chapters, 56 quests, 56 tasks, 93 rewards)

python3 -m unittest tools.tests.test_afterlight_quests -v
Ran 20 tests
OK

./tools/verify-pack.sh
VERIFY: ALL GREEN
```

## Files Changed

- `kubejs/startup_scripts/afterlight/registry.js`
- `kubejs/assets/kubejs/lang/en_us.json`
- `kubejs/server_scripts/afterlight/generated_quest_item_audit.js`
- `tools/afterlight_quests/builder.py`
- `tools/tests/test_afterlight_quests.py`
- `docs/HANDOFF.md`
- `.superpowers/sdd/2026-08-08-afterlight-05-acts-ii-iii/task-2-report.md`
- `index.toml`
- `pack.toml`
