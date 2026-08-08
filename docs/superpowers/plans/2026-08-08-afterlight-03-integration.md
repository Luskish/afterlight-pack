# AFTERLIGHT Plan 03: KubeJS Integration Layer

> **For agentic workers:** AGENTS.md guardrails binding. Read `.agents/skills/kubejs-modding/SKILL.md` before touching any script. Verification for every task: `BOOT_TIMEOUT=1200 ./tools/server-test.sh` prints SERVER BOOT: OK AND `grep -iE "error|exception" server-test/logs/kubejs/server.log` (plus startup.log) shows no script errors. Track progress in docs/HANDOFF.md's Plan 03 table.

**Goal:** The scripting foundation every later plan builds on: custom items, the post-story Draconic gate, cross-mod bridge recipe patterns, and loot injection. Spec section 7 scope rule applies: every script serves story, unification, the automation on-ramp, or a documented balance need.

**File map (all new):**
- `kubejs/startup_scripts/afterlight/registry.js` (items: requisition_chit, ascendancy_seal)
- `kubejs/server_scripts/afterlight/_constants.js` (shared IDs/tags; underscore loads first)
- `kubejs/server_scripts/afterlight/gate_draconic.js` (entry recipes require ascendancy_seal)
- `kubejs/server_scripts/afterlight/bridges.js` (cross-mod ore processing exemplars)
- `kubejs/server_scripts/afterlight/loot_chits.js` (chit injection into dungeon chest tables)
- `kubejs/assets/kubejs/textures/item/*.png` + lang (custom item visuals)

## Tasks

- [x] Task 1: Plan doc + file skeleton
- [x] Task 2: Item registrations + textures + lang (restart-class change, boot verify)
- [x] Task 3: Draconic post-story gate via seal-ingredient recipe replacement (spec section 6 hard gate 4)
- [x] Task 4: Bridge exemplars: Create crushing + IE crusher accept Mekanism raw ores (osmium, uranium, fluorite) with conservative yields (pattern for Plan 05+ expansion)
- [x] Task 5: LootJS chit injection (structure chests, modest chance) 
- [x] Task 6: Boot + kubejs log verification, ship, HANDOFF update

## Later-plan consumers
Plan 04 quests grant chits and reference the seal in the finale chain; Plan 05/06 expand bridges and add Gate multiblocks (Modular Machinery Reborn) consuming certified outputs. Keep IDs stable: `kubejs:requisition_chit`, `kubejs:ascendancy_seal`.
