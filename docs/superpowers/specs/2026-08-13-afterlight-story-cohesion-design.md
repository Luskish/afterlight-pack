# AFTERLIGHT Story Cohesion and Field Manuals Design

**Date:** 2026-08-13
**Status:** Approved direction, pending written spec review
**Owner:** Shane and the AFTERLIGHT friend group
**Target:** AFTERLIGHT `1.0.0-rc.2` on NeoForge 1.21.1

---

## 1. Purpose

AFTERLIGHT already has a complete ECHO-led story and substantial quest content, but the main path often enters a mod at an intermediate machine without first teaching the mod's basic language. The result is technically valid progression that can feel like a sequence of unrelated mod checklists.

This change makes the story feel intentional without invalidating any live progress:

1. Keep one clear main narrative spine.
2. Add optional, beginner-first field manuals for each major technology used by that spine.
3. Place clickable cross-chapter links exactly where a player first needs each manual.
4. Rewrite story transitions so each technology answers a problem created by the previous chapter.
5. Preserve every existing chapter, quest, task, reward, dependency, and progress identity.

The result should feel like ECHO is restoring a connected infrastructure plan, not sending players through a shuffled mod list.

## 2. Player Promise

- The main story remains mandatory only where it is already mandatory.
- Field manuals are optional. They teach, orient, and reward, but never gate the story.
- Existing completed, active, claimed, and pinned quest state remains valid.
- Players who already know a mod can ignore its manual.
- Players who do not know a mod can enter its manual from the exact story chapter that needs it.
- Native guidebooks, Ponder scenes, JEI, and field manuals complement one another. AFTERLIGHT does not rewrite complete third-party manuals.

## 3. Evidence and Reference Model

### 3.1 Live AFTERLIGHT evidence

A read-only snapshot was taken from the production server before design work. It contains four FTB Quests progress records and the matching FTB Teams state. No live file was modified.

Observed frontier:

- One player has completed Foothold and Slow Fire.
- One player has completed Foothold, Slow Fire, and The Engineer's Bench.
- No player has completed Steel Yourself or any later story quest.
- Earlier chapters contain active and completed state for multiple players.

The committed project must not contain player names, UUIDs, timestamps, team files, or copied live progress. The snapshot is operational evidence only.

### 3.2 Popular-pack research

The design uses structural lessons from official source repositories, not copied quest text, layouts, assets, IDs, or data.

| Pack | Reviewed revision | Useful pattern |
|---|---|---|
| [All The Mods 10](https://github.com/AllTheMods/ATM-10) | `57f8066138c9e5a9aa6378487130c2ced5ce3de5` | A separate main questline plus discoverable category and per-mod guidance lets experienced players roam while newer players find an entry point. Basic power, storage, and logistics are treated as first-class curricula. |
| [Enigmatica 10](https://github.com/EnigmaticaModpacks/Enigmatica10) | `6c13627111057e6d2b2595cdf6775219dfabbb31` | Technology learning chapters generally begin at one obvious root and move through a readable beginner path without cross-chapter prerequisites. |

ATM10's repository is All Rights Reserved. Enigmatica's content also remains its authors' work. AFTERLIGHT copies no prose, graphics, quest coordinates, rewards, or serialized quest objects. Only the general information architecture informs this design.

### 3.3 AFTERLIGHT synthesis

AFTERLIGHT combines the two useful patterns while retaining its own identity:

- ATM-like separation between the narrative spine and optional mod guidance.
- Enigmatica-like beginner roots and linear teaching paths inside each guide.
- Original ECHO narration, Signal Reliquary presentation, progression, rewards, and endgame.
- Existing Certifications remain advanced proof-of-automation content, not beginner tutorials.

## 4. Compatibility Contract

Progress compatibility is a release blocker, not a best-effort goal.

### 4.1 Frozen identities

The implementation records the current quest corpus at commit `7fcbc3a99fedcb8f6a62861ef86a2fd1e05fef25` in a checked-in compatibility fixture. The fixture is a canonical, recursively sorted representation of every existing chapter group, chapter, quest link, quest, task, reward, and localization entry. It retains complete parsed payloads, including:

- IDs, ownership, icons, and chapter settings
- dependencies and progression settings
- task types, targets, counts, components, and every other task field
- reward types, targets, counts, tables, commands, and every other reward field
- optional, repeatable, consumption, visibility, and sequencing flags
- all existing localization values

The fixture omits only the exact fields listed in section 4.2. The compatibility test recursively compares every other baseline value and requires the post-change corpus to be an additive superset. New chapters, quests, tasks, rewards, localization keys, and quest links are allowed. Outside the declared commodity task exception in section 4.2.1, a changed item ID, required count, reward amount, command, flag, owner, dependency, or type is a hard failure.

The fixture is generated from pack content only. It contains no world data, player names, UUIDs, timestamps, progress values, pins, claims, or live paths.

### 4.2 Fields allowed to change

The cohesion pass may change only these fields on existing content:

- localization key `chapter_group.4A20F33642175B95.title`
- `quest_subtitle` and `quest_desc` localization keys for existing Story-group quests
- `order_index` for the ten existing chapters in group `4A20F33642175B95`, solely to place Certifications at 10 through 16 and Depots at 30 through 32
- additive entries in existing chapter-level `quest_links` arrays

Existing quest positions, shapes, sizes, titles, dependencies, tasks, rewards, optional flags, repeatability, progression modes, and every other unlisted field remain byte-equivalent after canonical parsing.

### 4.2.1 Commodity task exception

An existing item task may change from one mod-specific commodity item to a semantically equivalent `ftbfiltersystem:item_tag` filter. The compatibility declaration maps the frozen task ID to the runtime item tag. This is the only additional existing-field exception.

- The task ID, task type, required count, consume behavior, `match_components` behavior, and every surrounding quest value remain fixed.
- The replacement uses `ftbfiltersystem:smart_filter` with an exact `ftbfiltersystem:filter` component value of `ftbfiltersystem:item_tag(<tag>)`.
- The tag must exist in the installed runtime and represent interchangeable outputs of the same commodity.
- No machine, component, schematic, custom progression item, or mod-specific resource qualifies.

### 4.3 New content rules

- New IDs use deterministic `stable_id()` generation and must be signed-safe FTB IDs.
- New manual quests have no dependency relationship to the story.
- Every new manual quest is marked optional.
- New manual rewards are modest Requisition Chits and XP only. They do not grant schematics, Gate parts, seals, keys, or progression stages.
- Manual tasks do not consume items.
- Manual chapters are compiler-managed and deterministic.
- Story links are navigation only. They do not imply completion or unlock state.

### 4.4 Production proof

Before deployment:

1. Acquire the existing host maintenance lock.
2. Confirm zero players through internal RCON.
3. Install and verify a fail-closed `DOCKER-USER` firewall rule that rejects new external TCP `25565` connections without affecting SSH or internal health checks.
4. Reconfirm zero players, flush saves, and stop Minecraft cleanly.
5. Create a timestamped verified backup of `world/ftbquests`, `world/ftbteams`, `usercache.json`, and `whitelist.json`.
6. Parse and canonically hash every complete FTB Quests and FTB Teams SNBT document. This includes `task_progress`, `started`, `completed`, `repeatable`, `completion_count`, `claimed_rewards`, `player_data`, pins when present, scalar flags, team properties, and every stored value.
7. Deploy and start the exact CI-approved commit while the connection gate remains closed.
8. Pass health checks, stop cleanly again, and require canonical equality for every pre-deploy progress and team document. Because no player can connect, no progress delta is expected or allowed.
9. Start the accepted release once more, pass health checks, then remove the exact maintenance firewall rule and release the lock.
10. Fail closed and roll back if any document, key, value, count, cooldown, repeat state, claim, pin, property, or flag differs.

The comparison stores identity-bearing snapshots only in a mode `0700` temporary VPS directory and the authenticated backup. Console output contains per-file counts and hashes, not names or UUIDs. Nothing from production progress enters git or release artifacts.

## 5. Information Architecture

### 5.1 Group rename

Keep chapter group ID `4A20F33642175B95` and change only its localized title:

`Certifications` becomes `Field Manuals & Certifications`.

Keeping the group ID preserves all references and progress ownership.

### 5.2 Chapter order

The group uses these display ranges:

| Order | Chapter type |
|---:|---|
| 0 to 7 | Beginner field manuals |
| 10 to 16 | Existing Certifications, Kinetics through Infrastructure |
| 30 to 32 | Existing Requisition Depots |

All existing chapter IDs remain unchanged. Only display order changes.

### 5.3 Manual visual grammar

Every manual follows one layout and voice pattern:

- One large root node at the left, framed as an ECHO archive recovery.
- A single readable beginner path moving left to right.
- Small branches only where the player makes a meaningful choice.
- A final checkmark node called a field test, proving the system was assembled and understood.
- Native-guide direction in the root description, such as opening the Engineer's Manual, AE2 Guide, PNC Manual, Powah book, JEI, or Create Ponder.
- A return link to the first relevant story milestone.

The root node teaches how to learn the mod. The remaining nodes teach the minimum path needed to understand the story's first use of it.

## 6. Field Manual Chapters

All titles and descriptions use ECHO's recovered-terminal voice. Exact item availability is validated against the installed 1.21.1 jars before generation.

### 6.1 Field Manual: Heavy Industry

- **Mod:** Immersive Engineering
- **Chapter slug and ID:** `manuals/immersive-engineering`, `150C6F996983394C`
- **Root slug and ID:** `manuals/immersive-engineering/recover-field-manual`, `3E77A16CB0C0AD11`
- **Story entry:** Foothold
- **Path:** Engineer's Manual and Hammer, Coke Oven, Creosote and Treated Wood, LV Capacitor, Copper Wire and Connectors, Engineer's Workbench, Blast Furnace, field test.
- **Teaching goal:** Multiblock formation, patient processing, low-voltage wiring, and blueprint crafting.

### 6.2 Field Manual: Matter Systems

- **Mod:** Mekanism
- **Chapter slug and ID:** `manuals/mekanism`, `4DE10FFCDEEF9892`
- **Root slug and ID:** `manuals/mekanism/configure-the-first-machine`, `6B09A1A11CD08E68`
- **Story entries:** Foothold, The Engine Room, Thresholds
- **Path:** Configurator, Heat Generator, Steel Casing, Metallurgic Infuser, Enrichment Chamber, Basic Universal Cable, Basic Energy Cube, Energized Smelter, field test.
- **Teaching goal:** Sided machines, alloy infusion, ore doubling, FE transport, and buffers before chemical processing.

### 6.3 Field Manual: Storage Lattice

- **Mod:** Applied Energistics 2
- **Chapter slug and ID:** `manuals/applied-energistics-2`, `01749E1554DFF98B`
- **Root slug and ID:** `manuals/applied-energistics-2/read-the-lattice`, `70380821D8D0339D`
- **Story entries:** The Lattice, Convergence, Architect
- **Path:** AE2 Guide and Meteorite Compass, Charger, Fluix, meteorite presses, Inscriber, Energy Acceptor and cable, Drive and storage cell, Crafting Terminal, first pattern, field test.
- **Teaching goal:** Power, channels, storage cells, processor production, and the conceptual jump from storage to autocrafting.

### 6.4 Field Manual: Kinetics

- **Mod:** Create
- **Chapter slug and ID:** `manuals/create`, `4690C88367D47FF3`
- **Root slug and ID:** `manuals/create/ponder-kinetics`, `686943DC0749D6E0`
- **Story entries:** Scavenger's Creed, Lines of Motion, Gate of Return
- **Path:** Wrench, Goggles, and Ponder; Water Wheel; shafts and cogs; Millstone; Mechanical Press; Basin and Mixer; belts and funnels; Blaze Burner and Brass; Precision Mechanism; field test.
- **Teaching goal:** Rotation, stress, processing, transport, heating, and sequenced assembly before the story asks for brass logistics.

### 6.5 Field Manual: Pressure

- **Mod:** PneumaticCraft: Repressurized
- **Chapter slug and ID:** `manuals/pneumaticcraft`, `0A510C4BD2A3818B`
- **Root slug and ID:** `manuals/pneumaticcraft/read-pressure-safely`, `084209B68927F9FC`
- **Story entries:** Pressure Language, Convergence
- **Path:** PNC Manual, Compressed Iron, Air Compressor, Pressure Tube and Gauge, safety upgrade, Pressure Chamber, Plastic, Etching Acid, Printed Circuit Board, Programmer and bounded drone test.
- **Teaching goal:** Pressure range, heat, explosion risk, chamber interfaces, and safe automation before logistics drones.

### 6.6 Field Manual: Power Networks

- **Mods:** Powah, Ender IO, Flux Networks
- **Chapter slug and ID:** `manuals/power-networks`, `67F13F819570ED52`
- **Root slug and ID:** `manuals/power-networks/define-the-grid`, `5334545A948815F6`
- **Story entries:** The Grid, Convergence, Architect
- **Path:** Powah book, starter generation, Energy Cable, Energy Cell, Energizing Orb, Basic Thermo Generator, Basic Reactor, Ender IO capacitor and conduits, Flux Plug and Point, Controller, reserve field test.
- **Teaching goal:** Generation, transport, buffering, wireless distribution, network ownership, and isolation of critical loads.

### 6.7 Field Manual: Frontier Machines

- **Mod:** Oritech
- **Chapter slug and ID:** `manuals/oritech`, `67C126F7B1338CB1`
- **Root slug and ID:** `manuals/oritech/frontier-orientation`, `6CC0CCE16F9FB5BE`
- **Story entries:** Frontier Machines, The Long Sky
- **Path:** Oritech Wrench, Basic Generator, Machine Core, Pulverizer, Centrifuge, Assembler, Foundry, Laser Arm, reactor orientation, field test.
- **Teaching goal:** Oritech's machine tiers, power entry, processing order, and safe approach to the reactor-era materials used by the story.

### 6.8 Field Manual: Nuclear Safety

- **Mods:** Mekanism Generators and Mekanism radiation systems
- **Chapter slug and ID:** `manuals/nuclear-systems`, `0B7C7859EBD6EFF3`
- **Root slug and ID:** `manuals/nuclear-systems/safety-before-output`, `4EEAB6F41DB426E7`
- **Story entries:** Thresholds, Quantum Weather
- **Path:** Hazmat set, Dosimeter and Geiger Counter, Electrolytic Separator, chemical chain orientation, Isotopic Centrifuge, reactor fuel assemblies, Reactor Logic Adapter, waste barrels, turbine heat sink, contained field test.
- **Teaching goal:** Radiation measurement, waste handling, automatic shutdown, and heat management before any output quota.
- **Safety rule:** The manual never rewards radioactive material and never tells a player to ignite a reactor merely to complete a checkmark.

### 6.9 Detection and completion contract

Every manual node declares one detection method. A task may not infer a formed multiblock from a component item, and a recipe-unlock advancement may not stand in for crafting or operating a machine.

| Manual | Automatic task contract | Manual confirmation contract |
|---|---|---|
| Heavy Industry | Item tasks for the Engineer's Manual, Hammer, Treated Wood, LV components, wire, connectors, and Workbench. Use `immersiveengineering:main/mb_cokeoven` and `immersiveengineering:main/mb_blastfurnace` for the two formed multiblocks. | The field test confirms that one LV source, buffer, connector pair, and load are wired without exposed live ends. |
| Matter Systems | Use `mekanismgenerators:heat_generator`, `mekanism:metallurgic_infuser`, and `mekanism:energy_cube` advancements where their criteria prove the intended machine. Use item tasks for Steel Casing, Enrichment Chamber, Basic Universal Cable, Configurator, and Energized Smelter. | The field test confirms configured input, output, and eject sides on a connected ore-doubling line. |
| Storage Lattice | Use `ae2:main/charger`, `ae2:main/presses`, `ae2:main/glass_cable`, `ae2:main/crafting_terminal`, and `ae2:main/pattern_encoding_terminal` where their criteria match the node. Use item tasks for the Guide, Meteorite Compass, Inscriber, Drive, storage cell, and first pattern components. | The field test confirms a powered terminal can insert and retrieve an item and that one encoded pattern reaches a provider. |
| Kinetics | The orientation node is a checkmark that explicitly asks the player to open Ponder. Use `create:water_wheel`, `create:mechanical_press`, `create:mechanical_mixer`, `create:brass`, and `create:precision_mechanism` for their proven milestones. Use item tasks for shafts, cogs, Millstone, belts, and funnels. | The field test confirms one powered line processes and routes an item while remaining below its stress limit. |
| Pressure | Use `pneumaticcraft:air_compressor`, `pneumaticcraft:pressure_tube`, `pneumaticcraft:pressure_chamber`, `pneumaticcraft:plastic`, `pneumaticcraft:etchacid_bucket`, `pneumaticcraft:printed_circuit_board`, `pneumaticcraft:programmer`, and `pneumaticcraft:logistics_drone`. | The field test confirms safe operating pressure, cooling clearance, and one bounded logistics route. |
| Power Networks | Use non-consuming item tasks for the Powah book, generators, cables, cells, Energizing Orb, reactor, capacitor bank, conduits, Flux Plug, Flux Point, and Flux Controller. Recipe-unlock advancements are not accepted as operation proof. | The field test confirms generation, a buffer, a local load, a remote load, and network ownership under a named grid. |
| Frontier Machines | Use non-consuming item tasks for the Oritech Wrench, Basic Generator, Machine Core, Pulverizer, Centrifuge, Assembler, Foundry, Laser Arm, and Reactor Controller. | The field test confirms the ordered processing line runs once. Reactor ignition is not required. |
| Nuclear Safety | Use `mekanism:radiation_prevention` for the complete protective set. Use non-consuming item tasks for the Dosimeter, Geiger Counter, Electrolytic Separator, Isotopic Centrifuge, Fission Fuel Assemblies, Reactor Logic Adapter, Radioactive Waste Barrels, and turbine components. | The final check confirms shutdown logic, waste capacity, heat removal, and a clear evacuation route. Reactor ignition is forbidden as quest proof. |

Each node also has a checked-in acquisition declaration: `recipe`, `process`, `worldgen`, `advancement`, or `manual_check`. A runtime server audit verifies every declared advancement and every effective recipe or process output after KubeJS changes. Worldgen declarations are restricted to established native acquisition such as AE2 meteorite presses. Manual checks must state an observable action and cannot conceal a missing detector.

## 7. Story-to-Manual Link Map

`quest_links` are visual navigation nodes. They never become dependencies.

| Source quest | Source ID | Target guidance quest | Target ID |
|---|---|---|---|
| The Alloy of Beginnings | `0576C37E9FA4116C` | Field Manual: Kinetics root | `686943DC0749D6E0` |
| The Scarlands | `718424A08FE06E9A` | Expedition Log root | `5DBA48B322065E95` |
| Through the Scarred Door | `5413406A90BD2714` | Anomalous Readings root | `6546BA910285D6EB` |
| The Engineer's Bench | `20169EC099FABBA0` | Field Manual: Heavy Industry root | `3E77A16CB0C0AD11` |
| First Current | `1AC07872BABAC949` | Field Manual: Matter Systems root | `6B09A1A11CD08E68` |
| The Engine Room | `43860D6CFEF31BB9` | Field Manual: Matter Systems root | `6B09A1A11CD08E68` |
| The Room Hums | `5A407B47132C07C6` | The Deep Vault root | `16783315E0833B1D` |
| Certus Resonance | `0CEB581902A9D016` | Field Manual: Storage Lattice root | `70380821D8D0339D` |
| Brass Standard | `4B0048F311BDF3D9` | Field Manual: Kinetics root | `686943DC0749D6E0` |
| 256-Track Capstone | `7199A16DB5D83154` | Certification: Kinetics I root | `1641CC316D20D678` |
| Air Compressor | `4D41BE537DD35854` | Field Manual: Pressure root | `084209B68927F9FC` |
| Logistics Drone | `53C65BE4DB17F1B9` | Logistics I root | `25E5B276B9FA47ED` |
| Energizing Orb | `0D1D4842B326D878` | Field Manual: Power Networks root | `5334545A948815F6` |
| 10M FE Reserve | `6B876A865DE7A77A` | Power I root | `64659C3AE503FE5D` |
| Oxygen Separation | `3F12A84AF92F28B8` | Field Manual: Matter Systems root | `6B09A1A11CD08E68` |
| Reactor Warning | `45A86A6AA4AD7824` | Field Manual: Nuclear Safety root | `4EEAB6F41DB426E7` |
| 1,024-Ingot Quota | `3C72E0ADC8E785D0` | Ore Loop I root | `1AE92DE8CA81283E` |
| Drone Delivery | `4F8F8B4545572260` | Logistics I root | `25E5B276B9FA47ED` |
| AE Stockkeeping | `27AEE834BFD148F2` | Autocrafting I root | `3011977E372A3BC6` |
| Create Feed Line | `742BEB99DFA479FD` | Cross-Mod I root | `02BA27AF63721ACA` |
| Machine Core | `6A0FBE1789BEFD37` | Field Manual: Frontier Machines root | `6CC0CCE16F9FB5BE` |
| Ancient Factory | `10EEBFB30F143EC4` | Expedition Log root | `5DBA48B322065E95` |
| Fission Assembly | `19D5F09EADF78A32` | Field Manual: Nuclear Safety root | `4EEAB6F41DB426E7` |
| Flight Harness | `557DC7BACD462EFE` | Field Manual: Frontier Machines root | `6CC0CCE16F9FB5BE` |
| Starlight | `23C08FB037E35BDE` | Expedition Log root | `5DBA48B322065E95` |
| Certified Bulk Quotas | `2D6ACF1CCBC7B4F2` | Certification: Kinetics I root | `1641CC316D20D678` |
| Certified Bulk Quotas | `2D6ACF1CCBC7B4F2` | Logistics I root | `25E5B276B9FA47ED` |
| Certified Bulk Quotas | `2D6ACF1CCBC7B4F2` | Ore Loop I root | `1AE92DE8CA81283E` |
| Certified Bulk Quotas | `2D6ACF1CCBC7B4F2` | Autocrafting I root | `3011977E372A3BC6` |
| Certified Bulk Quotas | `2D6ACF1CCBC7B4F2` | Cross-Mod I root | `02BA27AF63721ACA` |
| Certified Bulk Quotas | `2D6ACF1CCBC7B4F2` | Power I root | `64659C3AE503FE5D` |
| Certified Bulk Quotas | `2D6ACF1CCBC7B4F2` | Infrastructure II root | `7CB2D7D361BEA4C4` |
| Kinetic Frame | `0055C66103106D86` | Field Manual: Kinetics root | `686943DC0749D6E0` |
| Industrial Anchor | `52FE1624DCCE878F` | Field Manual: Heavy Industry root | `3E77A16CB0C0AD11` |
| Isotopic Core | `50775CE87FAA4EB7` | Field Manual: Nuclear Safety root | `4EEAB6F41DB426E7` |
| Lattice Matrix | `7F064705A3CAB2E6` | Field Manual: Storage Lattice root | `70380821D8D0339D` |
| Undercurrent Stabilizer | `39C1F24EABBB34A3` | Resonance Proof root | `6363BCE8A71FA766` |
| Monument Footprint | `36D0902A2921C44E` | Field Manual: Kinetics root | `686943DC0749D6E0` |
| Separate Grid | `66AD5C821947DF8E` | Field Manual: Power Networks root | `5334545A948815F6` |

Every new manual root has no dependencies and is `optional: true`, so its outbound story link is visible whenever the containing story chapter is visible. Each new manual mirrors every outbound manual link with a return link to the exact source quest in this table. A return link appears only when its story target is visible, which prevents spoilers. Existing Atlas, Undercurrent, Deep Vault, and Certification chapters receive outbound links only because their established group navigation already provides a return path.

Links use deterministic IDs and stable coordinates near their source quest. No link changes visibility, completion, or dependency state.

## 8. Narrative Transition Rewrite

Existing quest titles remain stable. The audit changes prose only where context is missing or a chapter transition currently reads like a mod switch.

| Transition | Required connective meaning |
|---|---|
| Cold Boot to Scavenger's Creed | Survival becomes repeatable supply, not a second tutorial reset. |
| Scavenger's Creed to The Scarlands | Material hunger forces survey work; the Nether door is evidence, not a random dimension requirement. |
| The Scarlands to Foothold | The Nether proves movement is possible; Foothold proves return is possible. |
| Foothold to The Engine Room | Steel and first current are the prerequisites for machines that multiply labor. |
| The Engine Room to The Lattice | Ore multiplication creates more inventory than human sorting can govern. |
| The Lattice to Lines of Motion | Addressable storage solves memory, not physical transport. |
| Lines of Motion to Pressure Language | Fixed logistics routes reveal the need for mobile, programmable delivery. |
| Pressure Language to The Grid | Autonomous systems turn inconsistent power from inconvenience into failure. |
| The Grid to Thresholds | A stable reserve unlocks chemical depth and demands a nuclear safety contract. |
| Thresholds to Convergence | High-tier machines remain prototypes until supply, routing, crafting, and recovery work together. |
| Convergence to Frontier Machines | The recovered signal contains manufacturing tolerances outside the known systems. |
| Frontier Machines to The War Below | The first decrypted key resolves to coordinates defended by corrupted war machines. |
| The War Below to Quantum Weather | Ancient metal carries a reactor-era encoding that can only be read through isotope systems. |
| Quantum Weather to The Long Sky | The third key identifies a fourth relay beyond ordinary terrain and ordinary sky. |
| The Long Sky to Architect | Four keys become a construction contract; knowledge must now become certified throughput. |
| Architect to Five Impossible Parts | The blueprint names five parts, each representing a lesson the Ascendancy kept separate. |
| Five Impossible Parts to The Cascade Truth | Physical readiness restores the final memory ECHO had prevented itself from reading. |
| The Cascade Truth to Gate of Return | The same design is rebuilt under explicit containment and human authority. |
| Gate of Return to Afterlight | Contact is evidence, not an order; the ending is a choice about responsibility. |
| Afterlight to Beyond Afterlight | The Seal opens postgame systems without rewriting the completed ending. |

Each affected root or finale description uses two layers:

1. ECHO explains why this system follows the previous one.
2. ECHO names the optional field manual when the chapter assumes prior mod knowledge.

Technical middle quests remain concise when their current action and voice are already correct. The audit records every story quest as retained, revised, or linked so the pass is complete and reviewable.

## 9. Quest-Link Compiler Design

### 9.1 New data type

Add a focused `QuestLinkSpec` dataclass to `tools/afterlight_quests/builder.py`:

```python
@dataclass(frozen=True)
class QuestLinkSpec:
    slug: str
    linked_quest: str
    x: float
    y: float
    explicit_id: str | None = None
```

It exposes:

- `id`, using `explicit_id` or `stable_id("quest_link", slug)`
- `linked_quest_id`, accepting either a signed-safe explicit ID or a quest slug

`ChapterSpec` gains `quest_links: tuple[QuestLinkSpec, ...] = ()`.

### 9.2 Rendering

The implementation targets the installed FTB Quests build `2101.1.30`. Its `QuestLink` resolves `linked_quest` as a navigation target, reports zero relative progress, and mirrors the target quest's visibility. It is not a dependency edge and contributes no completion state.

The renderer emits:

```snbt
quest_links: [
	{ id: "...", linked_quest: "...", x: 8.0d, y: -2.0d }
]
```

The renderer remains deterministic. Empty chapters continue to emit `quest_links: [ ]`.

### 9.3 Validation

The builder and corpus validator reject:

- malformed or high-bit link IDs
- link ID collisions with any chapter, quest, task, reward, or other link
- unresolved `linked_quest` targets
- duplicate link IDs
- duplicate target and coordinate triples in one chapter
- non-finite coordinates

Quest links participate in ID normalization and migration validation as first-class FTB identities.

### 9.4 Unmanaged quest overlays

Scavenger's Creed `4C01977EF77930A6`, The Scarlands `770DAD173D9C234B`, Foothold `45491A24F6B8C192`, The Engine Room `52EF477C2D995F40`, and Certification: Kinetics I `23643435F7BE74AC` predate the Python catalog and are intentionally not migrated wholesale during this release.

Add `tools/afterlight_quests/legacy_quest_overlays.py` with three explicit manifests:

- chapter ID to `QuestLinkSpec` entries
- whitelisted legacy Story localization key to replacement subtitle or description
- chapter ID to permitted replacement `order_index`, containing only Kinetics I from 0 to 10

`write_legacy_quest_overlays()` uses the existing structural SNBT scanner to replace only the top-level `quest_links` value in the four early Story files and `order_index` in Kinetics I. It merges only declared localization keys. It records and verifies a digest of all bytes outside the permitted spans, so a build fails if unrelated legacy content changes. Running it twice is byte-idempotent.

`tools/build-quests.py` writes the managed catalog first, applies legacy overlays second, then validates the complete corpus. Tests prove that deleting the permitted link and localization spans from output reproduces the frozen baseline exactly. This provides deterministic early links without risking a serialization rewrite of chapters where players already have active progress.

## 10. Testing Strategy

Implementation follows test-driven development.

### 10.1 Builder tests

- Rendering one link produces canonical SNBT.
- Empty links preserve the current output.
- Slug targets resolve to stable quest IDs.
- Explicit targets remain unchanged.
- Malformed, high-bit, duplicate, colliding, unresolved, and non-finite links fail with precise errors.
- Two consecutive builds are byte-identical.

### 10.2 Progress compatibility tests

- Generate the frozen compatibility fixture from the `7fcbc3a` corpus once.
- Recursively compare every baseline group, chapter, quest link, quest, task, reward, and localization value except the exact fields permitted by section 4.2.
- Assert permitted localization and order changes are limited to the exact IDs and keys declared by the design.
- Assert existing link arrays remain a prefix of the new arrays and all appended link IDs are new.
- Allow an existing item target change only when its frozen task ID declares an exact runtime-backed commodity tag replacement under section 4.2.1.
- Assert every declared commodity replacement freezes task type, count, consumption, component matching, and all surrounding quest data.
- Assert the fixture contains no player names, UUIDs, timestamps, progress values, or live paths.
- Assert all new manuals, quests, tasks, rewards, localization keys, and links are additive.
- Mutate one frozen task count, reward payload, quest flag, owner, dependency, title, and icon in isolated fixtures and prove each mutation fails.

### 10.3 Content tests

- Eight manual chapters exist under group `4A20F33642175B95`.
- Every manual has one root, one reachable finale, and no dependency cycle.
- Every manual quest has `optional: true`, and no story quest depends directly or transitively on a manual quest.
- Every source and target ID in section 7 resolves exactly, and every new manual contains one return link for each matching outbound story link.
- Every manual root has no dependencies, making outbound links immediately visible. Return-link visibility is asserted to mirror its exact story target.
- Legacy overlays are byte-idempotent and preserve every byte outside their declared link and localization spans.
- Existing Certification finale IDs remain the Architect dependencies.
- No manual grants a hard-gate item or stage.
- Every referenced item, advancement, entity, structure, biome, and dimension exists in the installed corpus.
- Every manual node has exactly one acquisition declaration and one task type from section 6.9.
- The runtime acquisition audit verifies each declared advancement, recipe, process output, and documented worldgen source after KubeJS recipe changes.
- All new prose passes the no-em-dash rule and uses ECHO's voice.

### 10.4 Release gates

The completed change must pass, in order:

1. Focused quest unit tests.
2. `python3 tools/build-quests.py` twice with no second-pass diff.
3. `python3 tools/validate-quests.py`.
4. `./tools/verify-pack.sh`, ending with `VERIFY: ALL GREEN`.
5. `BOOT_TIMEOUT=600 ./tools/server-test.sh`, ending with `SERVER BOOT: OK`.
6. Pushed `pack-ci` for the exact commit.
7. Release gauntlet and artifact inspection for the exact commit.
8. Pre-deploy and post-start live progress comparison.

## 11. Rollout and Recovery

### 11.1 Rollout

- Release through the existing `dev` to `main` promotion path.
- Do not restart or update the VPS while any player is online.
- Keep the maintenance lock and external connection gate closed through both verification starts and the canonical progress comparison.
- Preserve the current world, whitelist, FTB Teams state, memory settings, and no-pregen policy.
- Update Prism and CurseForge downloads together so clients and server receive identical quest data.

### 11.2 Recovery triggers

Roll back immediately if:

- any baseline content value outside the section 4.2 allowlist changes
- any canonical FTB Quests or FTB Teams progress document differs after the no-player load-save cycle
- the server fails the boot oracle
- a client cannot parse the new quest corpus
- any story quest becomes newly blocked by a manual

### 11.3 Recovery action

1. Keep the external connection gate closed and stop the candidate server.
2. Restore the previous exact server release.
3. Restore the pre-deploy `world/ftbquests` and `world/ftbteams` backup when the canonical comparison proves those files changed.
4. Start the previous release behind the gate, stop it cleanly, and require canonical equality with the pre-deploy snapshot.
5. Start the previous release, pass health checks, then remove the connection gate and release the maintenance lock.
6. Record the candidate as rejected and fix forward through a new commit and release. Never force-push `dev` or `main`, and never move an immutable tag.

## 12. Non-Goals

- No recipe gating changes.
- No removal or replacement of current quests.
- No world reset, dimension reset, or pre-generation.
- No new major mods.
- No copied quest content from ATM, Enigmatica, or another pack.
- No requirement to complete beginner manuals if a player already knows the mod.
- No expansion of the custom Signal dimension or Gate mechanics in this change.
- No attempt to duplicate every native guidebook page inside FTB Quests.

## 13. Acceptance Criteria

The feature is complete when:

- Every current progress identity passes the compatibility contract.
- Eight optional manuals teach the actual entry path for the story's major technologies.
- Story chapters contain clickable guidance at every currently abrupt mod transition.
- Root and finale prose makes the complete story read as one recovery plan.
- Existing Certifications and Gate dependencies remain unchanged.
- A fresh player can answer both "why am I doing this now?" and "where do I learn this mod from the beginning?" at every story transition.
- All local, CI, release, artifact, and live progress gates are green.
