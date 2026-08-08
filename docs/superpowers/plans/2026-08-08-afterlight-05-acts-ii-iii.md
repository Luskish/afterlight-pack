# AFTERLIGHT Plans 05: Acts II-III and Side Groups Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete story chapters 6-16, populate every side group, add automation certifications and the Requisition Depot, and leave the pack with a coherent pre-finale progression graph.

**Architecture:** A deterministic Python quest compiler becomes the source of truth for all new chapters. Existing hand-authored chapters 1-5 remain untouched. The compiler emits stable FTB Quests SNBT and localization from declarative chapter data, while a separate validator checks IDs, dependencies, localization coverage, forbidden punctuation, and referenced item IDs before every boot.

**Tech Stack:** Python 3, FTB Quests SNBT, NeoForge 1.21.1, KubeJS custom items, installed mod jars for item-ID verification.

## Global Constraints

- Read `AGENTS.md` and `.agents/skills/ftb-quests/SKILL.md` before quest work.
- No em dashes in any authored text.
- Every FTB Quests ID is a 16-character uppercase hexadecimal string.
- Existing chapter and quest IDs never change.
- All new generated IDs are deterministic and stable across reruns.
- Quest descriptions use ECHO's dry, precise voice and teach a real mechanic or advance the story.
- Do not add filler solely to chase the original 700-900 quest estimate.
- Every task ends with `python3 tools/validate-quests.py`, `./tools/verify-pack.sh`, and a dedicated-server boot at milestone tasks.

---

### Task 1: Deterministic Quest Compiler and Validator

**Files:**
- Create: `tools/afterlight_quests/__init__.py`
- Create: `tools/afterlight_quests/builder.py`
- Create: `tools/afterlight_quests/catalog.py`
- Create: `tools/build-quests.py`
- Create: `tools/validate-quests.py`
- Modify: `.packwizignore`
- Modify: `docs/HANDOFF.md`

**Interfaces:**
- Produces `stable_id(kind: str, slug: str) -> str` using SHA-256 truncated to 16 uppercase hex characters.
- Produces `build_catalog() -> list[ChapterSpec]` and writes only compiler-managed chapter files.
- Validator exits nonzero for malformed IDs, duplicates, unresolved dependencies, missing localization, em dashes, filename/id mismatch, or impossible item references.

- [ ] Create the package and dataclasses for groups, chapters, quests, tasks, and rewards.
- [ ] Add deterministic ID generation with collision detection.
- [ ] Add SNBT and localization writers with atomic file replacement.
- [ ] Add validator checks for graph closure, language coverage, duplicate IDs, and forbidden punctuation.
- [ ] Add item-ID audit using installed jars in `server-test/mods`, with an explicit allowlist for vanilla and KubeJS items.
- [ ] Run the validator against the current 9 chapters and fix any pre-existing structural defects without changing IDs.
- [ ] Commit compiler, validator, and handoff update.

### Task 2: Act II Story Chapters 6-11

**Files:**
- Modify: `tools/afterlight_quests/catalog.py`
- Generate: `config/ftbquests/quests/chapters/*.snbt`
- Modify: `config/ftbquests/quests/lang/en_us.snbt`
- Modify: `docs/HANDOFF.md`

**Interfaces:**
- Adds six story chapters in Story group `4525BB3160467FCB`.
- Chapter 6 depends on the final quest in Chapter 5. Each later chapter starts from the previous chapter finale.

- [ ] Add Chapter 6, `The Lattice`: AE2 power, terminals, storage cells, channels, and first autocraft.
- [ ] Add Chapter 7, `Lines of Motion`: Create logistics, trains, schedules, and a bulk railway-supply capstone.
- [ ] Add Chapter 8, `Pressure Language`: PneumaticCraft pressure, refinery, drones, and programmable logistics.
- [ ] Add Chapter 9, `The Grid`: Powah, Flux Networks, power storage, and cross-base distribution.
- [ ] Add Chapter 10, `Thresholds`: Mekanism factories, gases, ore multiplication, and fissile-material preparation.
- [ ] Add Chapter 11, `The First Schematic`: cross-mod automated production proof and Gate schematic one.
- [ ] Build, validate, boot, inspect FTB Quests load counts, and commit.

### Task 3: Act III Story Chapters 12-16

**Files:**
- Modify: `tools/afterlight_quests/catalog.py`
- Generate: `config/ftbquests/quests/chapters/*.snbt`
- Modify: `config/ftbquests/quests/lang/en_us.snbt`
- Modify: `docs/HANDOFF.md`

- [ ] Add Chapter 12, `Frontier Machines`: Oritech resource chains, laser processing, and reactor frontier.
- [ ] Add Chapter 13, `The War Below`: Cataclysm bosses and corrupted Ascendancy war constructs.
- [ ] Add Chapter 14, `Quantum Weather`: Mekanism fission, SPS preparation, antimatter, and schematic two.
- [ ] Add Chapter 15, `The Long Sky`: Aeronautics, flight infrastructure, Eternal Starlight expedition, and schematic three.
- [ ] Add Chapter 16, `Architect`: AE2-scale autocrafting, fusion, cross-mod quotas, boss proof, and schematic four.
- [ ] Build, validate, boot, inspect FTB Quests load counts, and commit.

### Task 4: Automation Certifications and Depot

**Files:**
- Modify: `tools/afterlight_quests/catalog.py`
- Create: `config/ftbquests/quests/reward_tables/depot_*.snbt`
- Generate: `config/ftbquests/quests/chapters/*.snbt`
- Modify: `config/ftbquests/quests/lang/en_us.snbt`

- [ ] Add Certification `Logistics I`: drawers, pipes, filters, round-robin routing, and overflow safety.
- [ ] Add Certification `Ore Loop I`: three-machine Mekanism ore loop with energy and throughput checks.
- [ ] Add Certification `Autocrafting I`: AE2 pattern provider, molecular assembler, CPU, and 256-item order.
- [ ] Add Certification `Cross-Mod I`: Create input, Mekanism process, IE or EnderIO output, AE2 stocking.
- [ ] Add Certification `Power I`: generation, storage, priority, and emergency shutdown.
- [ ] Add Certification `Infrastructure II`: bulk capstone proving unattended operation.
- [ ] Add Requisition Depot chapters with choice rewards that exchange Chits for early, mid, and late-game supplies.
- [ ] Build, validate, boot, and commit.

### Task 5: Side Group Completion

**Files:**
- Modify: `tools/afterlight_quests/catalog.py`
- Generate: `config/ftbquests/quests/chapters/*.snbt`
- Modify: `config/ftbquests/quests/lang/en_us.snbt`

- [ ] Add Undercurrent chapters for Occultism, Iron's Spells, Malum, and the stabilizer precursor.
- [ ] Add Deep Vault chapters for MI electric age, oil/chemistry, nuclear age, and quantum industry.
- [ ] Add Atlas chapters for Nether/End ruins, Aether/Twilight bosses, Undergarden/Otherside, Starlight, and the Cataclysm gauntlet.
- [ ] Add rare and epic Ascendancy Cache reward tables with progression-safe contents.
- [ ] Build, validate, boot, inspect logs, and commit.

### Task 6: Plan 05 Verification and Merge

**Files:**
- Modify: `docs/HANDOFF.md`
- Create: `docs/releases/plan-05-verification.md`

- [ ] Run `python3 tools/validate-quests.py`.
- [ ] Run `./tools/verify-pack.sh` and require `VERIFY: ALL GREEN`.
- [ ] Run `BOOT_TIMEOUT=1200 ./tools/server-test.sh` and require `SERVER BOOT: OK`.
- [ ] Require zero KubeJS script errors and a clean FTB Quests load summary.
- [ ] Push `dev`, wait for green CI, update handoff, and merge to `main`.

