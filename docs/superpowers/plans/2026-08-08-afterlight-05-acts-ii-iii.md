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

### Task 2: Plan 05 Progression Items

**Files:**
- Modify: `kubejs/startup_scripts/afterlight/registry.js`
- Modify: `kubejs/assets/kubejs/lang/en_us.json`
- Create: `kubejs/assets/kubejs/textures/item/*.png`
- Modify: `docs/HANDOFF.md`

- [ ] Register `kubejs:deep_vault_key`, `kubejs:schematic_kinetic_frame`, `kubejs:schematic_industrial_anchor`, `kubejs:schematic_isotopic_core`, `kubejs:schematic_lattice_matrix`, `kubejs:gate_blueprint`, and `kubejs:undercurrent_stabilizer_precursor`.
- [ ] Give every item a distinct texture, localized display name, deliberate rarity, stack size, and glow state.
- [ ] Boot after the startup-script change, verify all seven registry IDs in the runtime item registry, and commit.

### Task 3: Act II Story Chapters 6-11

**Files:**
- Modify: `tools/afterlight_quests/catalog.py`
- Generate: `config/ftbquests/quests/chapters/*.snbt`
- Modify: `config/ftbquests/quests/lang/en_us.snbt`
- Modify: `docs/HANDOFF.md`

**Interfaces:**
- Adds six story chapters in Story group `4525BB3160467FCB`.
- Adds exactly 57 named quests, bringing the full corpus to 15 chapters and 113 quests.
- Chapter 6 depends on the final quest in Chapter 5. Each later chapter starts from the previous chapter finale.

- [ ] Add Chapter 6, `The Lattice` (10 quests): Certus Resonance, Charged Matter, Fluix, Lost Presses, Processor Line, Controller, Cell Bank, Crafting Terminal, External Storage, First Autocraft. ECHO rediscovers distributed memory and remembers records being deleted before evacuation.
- [ ] Add Chapter 7, `Lines of Motion` (9 quests): Brass Standard, Precision Mechanism, Deployer, Filtered Belts, Mechanical Arm, Portable Interface, Rail Stock, Station and Schedule, 256-Track Capstone. The evacuation railway moved machinery outward, not civilians.
- [ ] Add Chapter 8, `Pressure Language` (9 quests): Air Compressor, Pressure Chamber, Compressed Iron, Plastic, Etching Acid, Printed Circuit, Programmer, Logistics Drone, 64-Circuit Capstone. Maintenance drones still follow orders from absent operators.
- [ ] Add Chapter 9, `The Grid` (9 quests): Energizing Orb, Reliable Generation, Reactor Core, Energy Cell, Capacitor Bank, Conduit Backbone, Flux Plug, Flux Point and Controller, 10M FE Reserve. Restored facilities reconnect, including one that should be dead.
- [ ] Add Chapter 10, `Thresholds` (10 quests): Purification, Crushing, Oxygen Separation, Chemical Injection, Factory Upgrade, Digital Miner, Sulfur Chain, Fissile Fuel, 1,024-Ingot Quota, Reactor Warning. ECHO recognizes Cascade support infrastructure.
- [ ] Add Chapter 11, `Convergence` (10 quests): AE Stockkeeping, Create Feed Line, Drone Delivery, IE Assembly, Conduit Routing, Laser Extraction, Automated Processor Batch, Automated Steel Batch, Stable Power Proof, Signal Triangulated. Four encrypted schematic locations appear, but no schematic is awarded in Act II. The finale awards `kubejs:deep_vault_key`.
- [ ] Give each chapter finale Memory Fragment 05-10, an Ascendancy Cache, Chits, XP, and the dependency used by the next chapter.
- [ ] Build, validate, boot, inspect FTB Quests load counts, and commit.

### Task 4: Act III Story Chapters 12-16

**Files:**
- Modify: `tools/afterlight_quests/catalog.py`
- Generate: `config/ftbquests/quests/chapters/*.snbt`
- Modify: `config/ftbquests/quests/lang/en_us.snbt`
- Modify: `docs/HANDOFF.md`

- [ ] Add Chapter 12, `Frontier Machines` (10 quests): Machine Core, Pulverization, Centrifuge, Assembly, Foundry, Laser Processing, Jetpack, Reactor Frontier, Prometheum, Kinetic Schematic. Award `kubejs:schematic_kinetic_frame` and stage `afterlight:gate_create`.
- [ ] Add Chapter 13, `The War Below` (10 quests): Ancient Factory, Harbinger, Ruined Citadel, Ender Guardian, Burning Arena, Ignis, Sunken City, Leviathan, War Salvage, Industry Schematic. Award `kubejs:schematic_industrial_anchor` and stage `afterlight:gate_ie`.
- [ ] Add Chapter 14, `Quantum Weather` (9 quests): Fission Assembly, Fissile Fuel, Turbine, Polonium, Plutonium, SPS, Antimatter, 100M FE Proof, Isotope Schematic. Award `kubejs:schematic_isotopic_core` and stage `afterlight:gate_mekanism`.
- [ ] Add Chapter 15, `The Long Sky` (10 quests): Flight Harness, Aeronautics Trial, Propulsion, Mobile Storage, High-Altitude Trial, Starlight, Golem Forge, Gatekeeper Signal, Relay Core, Lattice Schematic. Award `kubejs:schematic_lattice_matrix` and stage `afterlight:gate_ae2`; use Oritech flight tasks if Aeronautics item IDs are not runtime-verifiable.
- [ ] Add Chapter 16, `Architect` (8 quests): Four Keys stage proof, Mega Storage, 256K Crafting CPU, Assembler Matrix, Fusion Controller, Certified Bulk Quotas, Ancient Remnant, Gate Blueprint. Award `kubejs:gate_blueprint` and `afterlight_act3_complete`.
- [ ] Give each finale Memory Fragment 11-15 and the four schematic items/stages only at their specified recoveries.
- [ ] Build, validate, boot, inspect FTB Quests load counts, and commit.

### Task 5: Automation Certifications and Depot

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
- [ ] Award stable stages `afterlight_cert_kinetics_i`, `afterlight_cert_logistics_i`, `afterlight_cert_ore_loop_i`, `afterlight_cert_autocrafting_i`, `afterlight_cert_cross_mod_i`, `afterlight_cert_power_i`, and `afterlight_cert_infrastructure_ii` from certification finales.
- [ ] Add Requisition Depot chapters with choice rewards that exchange Chits for early, mid, and late-game supplies.
- [ ] Build, validate, boot, and commit.

### Task 6: Side Group Completion

**Files:**
- Modify: `tools/afterlight_quests/catalog.py`
- Generate: `config/ftbquests/quests/chapters/*.snbt`
- Modify: `config/ftbquests/quests/lang/en_us.snbt`

- [ ] Gate the existing Deep Vault opener behind possession of the key and award stage `afterlight_deep_vault` without changing its existing IDs.
- [ ] Add Undercurrent chapters `Names in the Circuit` (Occultism), `Spells Under Load` (Iron's Spells), `The Soul Ledger` (Malum), and `Resonance Proof` (cross-magic stabilizer precursor). Require Ars plus one of the other three branches, not all magic mods. Award `afterlight_stabilizer_ready`.
- [ ] Add Deep Vault chapters `Current Below` (MI electric age), `Black Distillate` (oil/chemistry), `Hot Cell` (nuclear age), and `Quantum Burden` (quantum industry).
- [ ] Add Atlas chapters `Courts Above and Beyond`, `Root and Echo`, `Edges of the Map`, and `Corrupted Guardians`, covering Twilight/Aether, Undergarden/Otherside, Starlight, Mowzie's, BoMD, and Cataclysm.
- [ ] Add rare and epic Ascendancy Cache reward tables with progression-safe contents.
- [ ] Build, validate, boot, inspect logs, and commit.

### Task 7: Plan 05 Verification and Merge

**Files:**
- Modify: `docs/HANDOFF.md`
- Create: `docs/releases/plan-05-verification.md`

- [ ] Run `python3 tools/validate-quests.py`.
- [ ] Run `./tools/verify-pack.sh` and require `VERIFY: ALL GREEN`.
- [ ] Run `BOOT_TIMEOUT=1200 ./tools/server-test.sh` and require `SERVER BOOT: OK`.
- [ ] Require zero KubeJS script errors and a clean FTB Quests load summary.
- [ ] Push `dev`, wait for green CI, update handoff, and merge to `main`.
