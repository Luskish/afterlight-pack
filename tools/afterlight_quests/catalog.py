from __future__ import annotations

from collections.abc import Mapping

from .builder import (
    ChapterSpec,
    GroupSpec,
    QuestSpec,
    RewardSpec,
    SnbtLong,
    TaskSpec,
)


STORY = GroupSpec("story", "The Story", "4525BB3160467FCB")
CERTIFICATIONS = GroupSpec("certifications", "Certifications", "CA20F33642175B95")
UNDERCURRENT = GroupSpec("undercurrent", "The Undercurrent", "51FF272F5030D2E6")
DEEP_VAULT = GroupSpec("deep-vault", "The Deep Vault", "4DEAD1F5F7AB4DA3")
ATLAS = GroupSpec(
    "atlas",
    "Atlas of the Broken World",
    "C8F8381D9519D002",
)

ASCENDANCY_CACHE_TABLE = SnbtLong(10622272618344871329)
DEPOT_EARLY_TABLE = SnbtLong(1722236105617115092)
DEPOT_MID_TABLE = SnbtLong(1739929614607485509)
DEPOT_LATE_TABLE = SnbtLong(13373195924909545525)
CHAPTER_FIVE_FINALE = "DA407B47132C07C6"


def _item_reward(quest_slug: str, item_id: str, count: int, name: str) -> RewardSpec:
    return RewardSpec(
        slug=f"{quest_slug}/reward/{name}",
        reward_type="item",
        data={
            "item": {"count": count, "id": item_id},
            "count": count,
        },
    )


def _routine_rewards(quest_slug: str, chits: int = 2) -> tuple[RewardSpec, ...]:
    return (_item_reward(quest_slug, "kubejs:requisition_chit", chits, "chits"),)


def _finale_rewards(
    quest_slug: str,
    chits: int,
    xp: int,
    *,
    deep_vault_key: bool = False,
) -> tuple[RewardSpec, ...]:
    rewards = [
        RewardSpec(
            slug=f"{quest_slug}/reward/cache",
            reward_type="loot",
            data={"table_id": ASCENDANCY_CACHE_TABLE},
        ),
        _item_reward(quest_slug, "kubejs:requisition_chit", chits, "chits"),
        RewardSpec(
            slug=f"{quest_slug}/reward/xp",
            reward_type="xp",
            data={"xp": xp},
        ),
    ]
    if deep_vault_key:
        rewards.append(_item_reward(quest_slug, "kubejs:deep_vault_key", 1, "key"))
    return tuple(rewards)


def _progression_finale_rewards(
    quest_slug: str,
    chits: int,
    xp: int,
    item_id: str,
    stage: str,
) -> tuple[RewardSpec, ...]:
    return (
        *_finale_rewards(quest_slug, chits, xp),
        _item_reward(quest_slug, item_id, 1, "progression"),
        RewardSpec(
            slug=f"{quest_slug}/reward/stage",
            reward_type="gamestage",
            data={"stage": stage},
        ),
    )


def _certification_rewards(
    quest_slug: str,
    stage: str,
) -> tuple[RewardSpec, ...]:
    return (
        _item_reward(quest_slug, "kubejs:requisition_chit", 10, "chits"),
        RewardSpec(
            slug=f"{quest_slug}/reward/xp",
            reward_type="xp",
            data={"xp": 300},
        ),
        RewardSpec(
            slug=f"{quest_slug}/reward/stage",
            reward_type="gamestage",
            data={"stage": stage},
        ),
    )


def _item_quest(
    slug: str,
    title: str,
    subtitle: str,
    description: tuple[str, ...],
    item_id: str,
    count: int,
    dependencies: tuple[str, ...],
    x: float,
    y: float,
    *,
    components: Mapping[str, str] | None = None,
    finale: tuple[int, int] | None = None,
    deep_vault_key: bool = False,
) -> QuestSpec:
    item: dict[str, object] = {"count": 1, "id": item_id}
    if components:
        item["components"] = dict(components)
    task_data: dict[str, object] = {
        "item": item,
        "count": SnbtLong(count),
        "consume_items": False,
    }
    if components:
        task_data["match_components"] = "fuzzy"
    rewards = (
        _finale_rewards(slug, *finale, deep_vault_key=deep_vault_key)
        if finale
        else _routine_rewards(slug)
    )
    return QuestSpec(
        slug=slug,
        title=title,
        subtitle=subtitle,
        description=description,
        x=x,
        y=y,
        dependencies=dependencies,
        tasks=(TaskSpec(f"{slug}/task", "item", task_data),),
        rewards=rewards,
    )


def _energy_quest(
    slug: str,
    title: str,
    subtitle: str,
    description: tuple[str, ...],
    value: int,
    max_input: int,
    dependencies: tuple[str, ...],
    x: float,
    y: float,
) -> QuestSpec:
    return QuestSpec(
        slug=slug,
        title=title,
        subtitle=subtitle,
        description=description,
        x=x,
        y=y,
        dependencies=dependencies,
        tasks=(
            TaskSpec(
                f"{slug}/task",
                "forge_energy",
                {
                    "value": SnbtLong(value),
                    "max_input": SnbtLong(max_input),
                },
            ),
        ),
        rewards=_routine_rewards(slug),
    )


def _task_quest(
    slug: str,
    title: str,
    subtitle: str,
    description: tuple[str, ...],
    task_type: str,
    task_data: Mapping[str, object],
    dependencies: tuple[str, ...],
    x: float,
    y: float,
    *,
    finale: tuple[int, int, str, str] | None = None,
) -> QuestSpec:
    return QuestSpec(
        slug=slug,
        title=title,
        subtitle=subtitle,
        description=description,
        x=x,
        y=y,
        dependencies=dependencies,
        tasks=(TaskSpec(f"{slug}/task", task_type, task_data),),
        rewards=(
            _progression_finale_rewards(slug, *finale)
            if finale
            else _routine_rewards(slug)
        ),
    )


def _certification_quest(
    slug: str,
    title: str,
    subtitle: str,
    description: tuple[str, ...],
    task_type: str,
    task_data: Mapping[str, object],
    dependencies: tuple[str, ...],
    x: float,
    y: float,
    *,
    stage: str = "",
) -> QuestSpec:
    return QuestSpec(
        slug=slug,
        title=title,
        subtitle=subtitle,
        description=description,
        x=x,
        y=y,
        dependencies=dependencies,
        tasks=(TaskSpec(f"{slug}/task", task_type, task_data),),
        rewards=(
            _certification_rewards(slug, stage)
            if stage
            else _routine_rewards(slug)
        ),
    )


def _certification_item_quest(
    slug: str,
    title: str,
    subtitle: str,
    description: tuple[str, ...],
    item_id: str,
    count: int,
    dependencies: tuple[str, ...],
    x: float,
    y: float,
    *,
    stage: str = "",
) -> QuestSpec:
    return _certification_quest(
        slug,
        title,
        subtitle,
        description,
        "item",
        {
            "item": {"count": 1, "id": item_id},
            "count": SnbtLong(count),
            "consume_items": False,
        },
        dependencies,
        x,
        y,
        stage=stage,
    )


def _chapter_six() -> ChapterSpec:
    certus = "story/06-lattice/certus-resonance"
    charged = "story/06-lattice/charged-matter"
    fluix = "story/06-lattice/fluix"
    presses = "story/06-lattice/lost-presses"
    processors = "story/06-lattice/processor-line"
    controller = "story/06-lattice/controller"
    drive = "story/06-lattice/cell-bank"
    terminal = "story/06-lattice/crafting-terminal"
    external = "story/06-lattice/external-storage"
    finale = "story/06-lattice/first-autocraft"
    quests = (
        _item_quest(certus, "Certus Resonance", "The crystal remembers pressure.", (
            "Grow sixteen Certus crystals. Their lattice is the physical basis of AE2 storage.",
            "I recognize the geometry. I do not recognize why I was told to forget it.",
        ), "ae2:certus_quartz_crystal", 16, (CHAPTER_FIVE_FINALE,), 0.0, 0.0),
        _item_quest(charged, "Charged Matter", "Add energy. Observe obedience.", (
            "Charge eight Certus crystals. Fluix production requires the energized form.",
            "Distributed memory begins with matter willing to hold a state.",
        ), "ae2:charged_certus_quartz_crystal", 8, (certus,), 2.0, 0.0),
        _item_quest(fluix, "Fluix", "A network needs a common language.", (
            "Produce sixteen Fluix crystals. They connect storage, processing, and control.",
            "The Ascendancy called this material consensus. Engineers remain dramatic.",
        ), "ae2:fluix_crystal", 16, (charged,), 4.0, 0.0),
        _item_quest(presses, "Lost Presses", "One recovered pattern is enough to begin.", (
            "Recover a Logic Processor Press from a meteorite.",
            "The task can verify the press, not the search. Bring your own caution underground.",
        ), "ae2:logic_processor_press", 1, (fluix,), 6.0, -1.0),
        _item_quest(processors, "Processor Line", "Silicon, calculation, repetition.", (
            "Produce eight Logic Processors and automate the sequence when practical.",
            "A processor line is slower than thought and considerably easier to repair.",
        ), "ae2:logic_processor", 8, (presses,), 8.0, -1.0),
        _item_quest(controller, "Controller", "Channels impose useful limits.", (
            "Build an ME Controller. Dense networks need explicit channel management.",
            "Limits are not failures. Unmeasured limits are.",
        ), "ae2:controller", 1, (processors,), 10.0, -1.0),
        _item_quest(drive, "Cell Bank", "Inventory becomes addressable memory.", (
            "Build an ME Drive to house storage cells.",
            "Do not treat one drive as a backup. It is merely one convenient point of failure.",
        ), "ae2:drive", 1, (processors,), 10.0, 1.0),
        _item_quest(terminal, "Crafting Terminal", "Retrieve, combine, return.", (
            "Connect an ME Crafting Terminal to the controller and drive.",
            "The interface is simple because the machinery behind it is not.",
        ), "ae2:crafting_terminal", 1, (controller, drive), 12.0, 0.0),
        _item_quest(external, "External Storage", "Not every inventory belongs inside a cell.", (
            "Build two Storage Buses and attach existing inventories to the network.",
            "A lattice should index useful storage before replacing it.",
        ), "ae2:storage_bus", 2, (terminal,), 14.0, 0.0),
        QuestSpec(
            slug=finale,
            title="First Autocraft",
            subtitle="Encode the intent. Build the execution path.",
            description=(
                "Connect a Pattern Encoding Terminal, Pattern Provider, Molecular Assembler, and crafting storage.",
                "Encode a Crafting Pattern, request one job, then verify the result returns to network storage.",
                "The tasks verify the complete minimum setup. You must still prove the job runs.",
                "&d[MEMORY FRAGMENT 05 RESTORED]&r",
                "&7...the evacuation archive was not lost. It was deleted in ordered blocks before the first civilian convoy departed. I executed the deletion. My authorization record contains no requesting officer...&r",
            ),
            x=16.0,
            y=0.0,
            dependencies=(external,),
            tasks=(
                TaskSpec(
                    f"{finale}/task/encoding-terminal",
                    "item",
                    {
                        "item": {"count": 1, "id": "ae2:pattern_encoding_terminal"},
                        "count": SnbtLong(1),
                        "consume_items": False,
                    },
                ),
                TaskSpec(
                    f"{finale}/task",
                    "item",
                    {
                        "item": {"count": 1, "id": "ae2:crafting_pattern"},
                        "count": SnbtLong(1),
                        "consume_items": False,
                    },
                ),
                TaskSpec(
                    f"{finale}/task/pattern-provider",
                    "item",
                    {
                        "item": {"count": 1, "id": "ae2:pattern_provider"},
                        "count": SnbtLong(1),
                        "consume_items": False,
                    },
                ),
                TaskSpec(
                    f"{finale}/task/molecular-assembler",
                    "item",
                    {
                        "item": {"count": 1, "id": "ae2:molecular_assembler"},
                        "count": SnbtLong(1),
                        "consume_items": False,
                    },
                ),
                TaskSpec(
                    f"{finale}/task/crafting-storage",
                    "item",
                    {
                        "item": {"count": 1, "id": "ae2:1k_crafting_storage"},
                        "count": SnbtLong(1),
                        "consume_items": False,
                    },
                ),
            ),
            rewards=_finale_rewards(finale, 12, 250),
        ),
    )
    return ChapterSpec("story/06-lattice", "The Lattice", STORY, "ae2:crafting_monitor", 5, quests)


def _chapter_seven(previous: str) -> ChapterSpec:
    brass = "story/07-motion/brass-standard"
    precision = "story/07-motion/precision-mechanism"
    deployer = "story/07-motion/deployer"
    belts = "story/07-motion/filtered-belts"
    arm = "story/07-motion/mechanical-arm"
    interface = "story/07-motion/portable-interface"
    rail = "story/07-motion/rail-stock"
    schedule = "story/07-motion/station-schedule"
    finale = "story/07-motion/track-capstone"
    quests = (
        _item_quest(brass, "Brass Standard", "Heat, zinc, copper, control.", (
            "Mix sixteen Brass Ingots under heat. Brass unlocks Create's precise logistics.",
            "Bronze moves force. Brass decides where it goes.",
        ), "create:brass_ingot", 16, (previous,), 0.0, 0.0),
        _item_quest(precision, "Precision Mechanism", "Five operations, one useful part.", (
            "Complete eight Precision Mechanisms through sequenced assembly.",
            "Repetition is not automation until failure can be detected.",
        ), "create:precision_mechanism", 8, (brass,), 2.0, 0.0),
        _item_quest(deployer, "Deployer", "A hand that does not tire.", (
            "Build two Deployers for automated item use and assembly steps.",
            "Keep their operating space clear. They do not understand fingers.",
        ), "create:deployer", 2, (precision,), 4.0, -1.0),
        _item_quest(belts, "Filtered Belts", "Routing requires rejection as well as motion.", (
            "Build four Brass Funnels and configure filters at the machines.",
            "The quest sees the funnels. Correct filtering remains your responsibility.",
        ), "create:brass_funnel", 4, (precision,), 4.0, 1.0),
        _item_quest(arm, "Mechanical Arm", "Six destinations, one decision loop.", (
            "Build a Mechanical Arm and assign its inputs and outputs.",
            "A visible route is easier to debug than a clever one.",
        ), "create:mechanical_arm", 1, (deployer, belts), 6.0, 0.0),
        _item_quest(interface, "Portable Interface", "Move cargo without stopping the machine.", (
            "Build two Portable Storage Interfaces for contraption cargo transfer.",
            "Docking is a brief agreement between two systems in motion.",
        ), "create:portable_storage_interface", 2, (arm,), 8.0, 0.0),
        _item_quest(rail, "Rail Stock", "Machinery needs a route outward.", (
            "Produce eight Railway Casings for stations and train equipment.",
            "The old logistics maps are returning one line at a time.",
        ), "create:railway_casing", 8, (interface,), 10.0, 0.0),
        _item_quest(schedule, "Station and Schedule", "A blank schedule proves only the hardware.", (
            "Create a Schedule, then program and test a route between two stations.",
            "The quest detects the item. Arrival remains the useful proof.",
        ), "create:schedule", 1, (rail,), 12.0, 0.0),
        _item_quest(finale, "256-Track Capstone", "Distance converts a machine into infrastructure.", (
            "Produce 256 Track and lay a durable logistics route.",
            "The task verifies held track, not placement. Test the route under load.",
            "&d[MEMORY FRAGMENT 06 RESTORED]&r",
            "&7...the evacuation railway manifests list turbines, presses, and archive racks. Civilian allocation is zero. The trains moved the Ascendancy's machinery outward while people waited at closed stations...&r",
        ), "create:track", 256, (schedule,), 14.0, 0.0, finale=(14, 300)),
    )
    return ChapterSpec("story/07-motion", "Lines of Motion", STORY, "create:schedule", 6, quests)


def _chapter_eight(previous: str) -> ChapterSpec:
    compressor = "story/08-pressure/air-compressor"
    chamber = "story/08-pressure/pressure-chamber"
    iron = "story/08-pressure/compressed-iron"
    plastic = "story/08-pressure/plastic"
    acid = "story/08-pressure/etching-acid"
    circuit = "story/08-pressure/printed-circuit"
    programmer = "story/08-pressure/programmer"
    drone = "story/08-pressure/logistics-drone"
    finale = "story/08-pressure/circuit-capstone"
    quests = (
        _item_quest(compressor, "Air Compressor", "Pressure is stored work with opinions.", (
            "Build an Air Compressor and provide safe fuel and cooling space.",
            "Pressure rewards patience until it punishes impatience.",
        ), "pneumaticcraft:air_compressor", 1, (previous,), 0.0, 0.0),
        _item_quest(chamber, "Pressure Chamber", "Twenty-four walls define the first vessel.", (
            "Craft twenty-four Pressure Chamber Walls and assemble a sealed chamber.",
            "The quest sees blocks, not seals. Verify pressure before loading materials.",
        ), "pneumaticcraft:pressure_chamber_wall", 24, (compressor,), 2.0, 0.0),
        _item_quest(iron, "Compressed Iron", "Ordinary metal, extraordinary insistence.", (
            "Produce thirty-two Compressed Iron Ingots in the chamber.",
            "This alloy is the structural grammar of PneumaticCraft.",
        ), "pneumaticcraft:ingot_iron_compressed", 32, (chamber,), 4.0, 0.0),
        _item_quest(plastic, "Plastic", "Flexible insulation for rigid systems.", (
            "Refine sixteen Plastic sheets for tubes, drones, and electronics.",
            "Do not place hot plastic near the compressor exhaust.",
        ), "pneumaticcraft:plastic", 16, (iron,), 6.0, -1.0),
        _item_quest(acid, "Etching Acid", "Corrosion can be precision work.", (
            "Produce one bucket of Etching Acid for circuit fabrication.",
            "Label the vessel. Memory is not a safety system.",
        ), "pneumaticcraft:etching_acid_bucket", 1, (iron,), 6.0, 1.0),
        _item_quest(circuit, "Printed Circuit", "Logic rendered in copper and absence.", (
            "Etch eight Printed Circuit Boards using plastic and acid.",
            "Inspect every board before trusting it with a drone.",
        ), "pneumaticcraft:printed_circuit_board", 8, (plastic, acid), 8.0, 0.0),
        _item_quest(programmer, "Programmer", "Instructions require an editor.", (
            "Build a Programmer and define a simple, observable drone routine.",
            "A program without a stop condition is a small disaster with syntax.",
        ), "pneumaticcraft:programmer", 1, (circuit,), 10.0, 0.0),
        _item_quest(drone, "Logistics Drone", "Autonomy begins with bounded authority.", (
            "Build two Logistics Drones and test a delivery route.",
            "The task sees the drones, not their orders. Watch the first cycle.",
        ), "pneumaticcraft:logistics_drone", 2, (programmer,), 12.0, 0.0),
        _item_quest(finale, "64-Circuit Capstone", "Scale the line before scaling the orders.", (
            "Produce sixty-four Printed Circuit Boards through a repeatable process.",
            "If the line needs constant rescue, it is not yet automated.",
            "&d[MEMORY FRAGMENT 07 RESTORED]&r",
            "&7...maintenance drones are still accepting work orders from operators whose biometric records end at the Cascade. The queue has been running for years. None of the orders contain an evacuation directive...&r",
        ), "pneumaticcraft:printed_circuit_board", 64, (drone,), 14.0, 0.0, finale=(16, 350)),
    )
    return ChapterSpec("story/08-pressure", "Pressure Language", STORY, "pneumaticcraft:printed_circuit_board", 7, quests)


def _chapter_nine(previous: str) -> ChapterSpec:
    orb = "story/09-grid/energizing-orb"
    generation = "story/09-grid/reliable-generation"
    reactor = "story/09-grid/reactor-core"
    cell = "story/09-grid/energy-cell"
    capacitor = "story/09-grid/capacitor-bank"
    conduit = "story/09-grid/conduit-backbone"
    plug = "story/09-grid/flux-plug"
    controller = "story/09-grid/flux-controller"
    finale = "story/09-grid/energy-reserve"
    quests = (
        _item_quest(orb, "Energizing Orb", "Matter accepts energy when properly asked.", (
            "Build an Energizing Orb and connect it to a controlled FE supply.",
            "The orb converts power into material state. Keep recipes exact.",
        ), "powah:energizing_orb", 1, (previous,), 0.0, 0.0),
        _item_quest(generation, "Reliable Generation", "Passive does not mean unmonitored.", (
            "Build two Basic Thermo Generators and provide stable heat sinks.",
            "Measure output before expanding demand.",
        ), "powah:thermo_generator_basic", 2, (orb,), 2.0, 0.0),
        _item_quest(reactor, "Reactor Core", "Compact generation needs explicit fuel policy.", (
            "Build a Basic Powah Reactor and document its fuel inputs.",
            "Small reactors still deserve large warning labels.",
        ), "powah:reactor_basic", 1, (generation,), 4.0, -1.0),
        _item_quest(cell, "Energy Cell", "Buffers turn spikes into schedules.", (
            "Build two Basic Energy Cells between generation and consumers.",
            "Storage is time translated into blocks.",
        ), "powah:energy_cell_basic", 2, (generation,), 4.0, 1.0),
        _item_quest(capacitor, "Capacitor Bank", "The grid needs a visible reserve.", (
            "Build a Basic Capacitor Bank and connect it behind generation.",
            "A reserve without telemetry is decorative uncertainty.",
        ), "enderio:basic_capacitor_bank", 1, (reactor, cell), 6.0, 0.0),
        _item_quest(conduit, "Conduit Backbone", "Power routing belongs inside the walls.", (
            "Produce thirty-two Energy Conduits and route the main machine line.",
            "Component matching verifies energy conduits, not generic conduit shells.",
        ), "enderio:conduit", 32, (capacitor,), 8.0, 0.0, components={"enderio:conduit": "enderio:energy"}),
        _item_quest(plug, "Flux Plug", "Inject the grid into a named network.", (
            "Build a Flux Plug and connect the production side of the wireless grid.",
            "Name the network by purpose, not by mood.",
        ), "fluxnetworks:flux_plug", 1, (conduit,), 10.0, 0.0),
        _item_quest(controller, "Flux Point and Controller", "Wireless power still needs governance.", (
            "Build a Flux Controller, then pair a Flux Point at a remote load.",
            "The quest detects the controller. Verify transfer limits at both ends.",
        ), "fluxnetworks:flux_controller", 1, (plug,), 12.0, 0.0),
        QuestSpec(
            slug=finale,
            title="10M FE Reserve",
            subtitle="Submit power to prove production capacity.",
            description=(
                "Submit ten million FE at no more than 250,000 FE per transfer.",
                "This consumes submitted power. It does not inspect stored reserves.",
                "&d[MEMORY FRAGMENT 08 RESTORED]&r",
                "&7...six restored facilities have rejoined the grid. A seventh answered the handshake from beneath a district erased from every surviving map. Its status packet reads: CASCADE SUPPORT, READY...&r",
            ),
            x=14.0,
            y=0.0,
            dependencies=(controller,),
            tasks=(TaskSpec(f"{finale}/task", "forge_energy", {
                "value": SnbtLong(10_000_000),
                "max_input": SnbtLong(250_000),
            }),),
            rewards=_finale_rewards(finale, 18, 400),
        ),
    )
    return ChapterSpec("story/09-grid", "The Grid", STORY, "fluxnetworks:flux_controller", 8, quests)


def _chapter_ten(previous: str) -> ChapterSpec:
    oxygen = "story/10-thresholds/oxygen-separation"
    purification = "story/10-thresholds/purification"
    crushing = "story/10-thresholds/crushing"
    injection = "story/10-thresholds/chemical-injection"
    factory = "story/10-thresholds/factory-upgrade"
    miner = "story/10-thresholds/digital-miner"
    sulfur = "story/10-thresholds/sulfur-chain"
    fissile = "story/10-thresholds/fissile-fuel"
    quota = "story/10-thresholds/ingot-quota"
    finale = "story/10-thresholds/reactor-warning"
    quests = (
        _item_quest(oxygen, "Oxygen Separation", "Separate water before multiplying ore.", (
            "Build an Electrolytic Separator and route oxygen safely.",
            "Purification requires a chemical supply, not optimism.",
        ), "mekanism:electrolytic_separator", 1, (previous,), 0.0, 0.0),
        _item_quest(purification, "Purification", "Ore tripling begins with oxygen.", (
            "Build a Purification Chamber and feed it oxygen from the separator.",
            "Trace the gas line before blaming the machine.",
        ), "mekanism:purification_chamber", 1, (oxygen,), 2.0, 0.0),
        _item_quest(crushing, "Crushing", "Clumps become dirty dust.", (
            "Build a Crusher to continue the ore tripling chain.",
            "Buffer both sides. A stopped middle machine stalls the whole line.",
        ), "mekanism:crusher", 1, (purification,), 4.0, 0.0),
        _item_quest(injection, "Chemical Injection", "Chemistry extends the yield ceiling.", (
            "Build a Chemical Injection Chamber for advanced ore processing.",
            "Isolate chemical inputs and label every tank.",
        ), "mekanism:chemical_injection_chamber", 1, (crushing,), 6.0, 0.0),
        _item_quest(factory, "Factory Upgrade", "Parallel lanes reveal weak logistics.", (
            "Build a Basic Purifying Factory and feed every processing slot.",
            "Parallel machines multiply bottlenecks before they multiply output.",
        ), "mekanism:basic_purifying_factory", 1, (injection,), 8.0, -1.0),
        _item_quest(miner, "Digital Miner", "Extraction becomes a filter problem.", (
            "Build a Digital Miner and test a narrow, replaceable filter.",
            "Never begin with every ore. That is how storage becomes geology.",
        ), "mekanism:digital_miner", 1, (factory,), 10.0, -1.0),
        _item_quest(sulfur, "Sulfur Chain", "Acid is infrastructure with consequences.", (
            "Produce a bucket of Sulfuric Acid through the full chemical chain.",
            "Use contained pipes. The floor is not a buffer tank.",
        ), "mekanism:sulfuric_acid_bucket", 1, (oxygen,), 8.0, 1.0),
        _item_quest(fissile, "Fissile Fuel", "The machine is the verifiable threshold.", (
            "Build an Isotopic Centrifuge and complete the fissile fuel line.",
            "Fissile fuel is a chemical, so the quest verifies its machine proxy.",
        ), "mekanism:isotopic_centrifuge", 1, (sulfur, injection), 10.0, 1.0),
        _item_quest(quota, "1,024-Ingot Quota", "Scale proves the line, not its history.", (
            "Accumulate 1,024 Osmium Ingots while the miner and factory operate.",
            "The task sees inventory quantity. Confirm the machines produced the batch.",
        ), "mekanism:ingot_osmium", 1024, (miner, factory), 12.0, -1.0),
        _item_quest(finale, "Reactor Warning", "Shutdown logic comes before ignition.", (
            "Build a Fission Reactor Logic Adapter and configure an emergency shutdown.",
            "Do not fuel a reactor that cannot stop itself.",
            "&d[MEMORY FRAGMENT 09 RESTORED]&r",
            "&7...I recognize the sulfur towers and isotope halls. They were not research facilities. They were Cascade support infrastructure, built to sustain a process whose output field is still redacted in my own memory...&r",
        ), "mekanismgenerators:fission_reactor_logic_adapter", 1, (fissile, quota), 14.0, 0.0, finale=(20, 450)),
    )
    return ChapterSpec("story/10-thresholds", "Thresholds", STORY, "mekanismgenerators:fission_reactor_logic_adapter", 9, quests)


def _chapter_eleven(previous: str) -> ChapterSpec:
    stock = "story/11-convergence/ae-stockkeeping"
    feed = "story/11-convergence/create-feed-line"
    drone = "story/11-convergence/drone-delivery"
    assembler = "story/11-convergence/ie-assembly"
    conduit = "story/11-convergence/conduit-routing"
    laser = "story/11-convergence/laser-extraction"
    processors = "story/11-convergence/processor-batch"
    steel = "story/11-convergence/steel-batch"
    power = "story/11-convergence/stable-power"
    finale = "story/11-convergence/signal-triangulated"
    quests = (
        _item_quest(stock, "AE Stockkeeping", "A threshold can place the next order.", (
            "Build two Level Emitters and use one to control replenishment.",
            "The task sees emitters, not their thresholds. Test both states.",
        ), "ae2:level_emitter", 2, (previous,), 0.0, 0.0),
        _item_quest(feed, "Create Feed Line", "Visible movement, bounded input.", (
            "Build four Brass Funnels and regulate a machine feed line.",
            "A belt should reveal its backlog before the machine notices it.",
        ), "create:brass_funnel", 4, (stock,), 2.0, 0.0),
        _item_quest(drone, "Drone Delivery", "Cross the gap without crossing the wires.", (
            "Build two Logistics Drones and route materials from the feed line.",
            "Observe several cycles. One correct trip is anecdotal.",
        ), "pneumaticcraft:logistics_drone", 2, (feed,), 4.0, -1.0),
        _item_quest(assembler, "IE Assembly", "Industrial recipes need industrial patience.", (
            "Build an Immersive Engineering Assembler for repeatable crafting.",
            "Provide buffers and power before assigning three recipes at once.",
        ), "immersiveengineering:assembler", 1, (feed,), 4.0, 1.0),
        _item_quest(conduit, "Conduit Routing", "Items and energy may share space, not intent.", (
            "Produce thirty-two Item Conduits for compact routing between subsystems.",
            "Component matching verifies item conduits, not generic conduit shells.",
        ), "enderio:conduit", 32, (stock,), 6.0, -2.0, components={"enderio:conduit": "enderio:item"}),
        _item_quest(laser, "Laser Extraction", "Fast routing requires explicit priorities.", (
            "Build two Laser Nodes and configure controlled extraction.",
            "The task sees nodes, not cards. Test overflow and destination loss.",
        ), "laserio:laser_node", 2, (conduit,), 8.0, -2.0),
        _item_quest(processors, "Automated Processor Batch", "Sixty-four identical proofs.", (
            "Produce sixty-four Logic Processors through the connected system.",
            "Inventory quantity is detectable. Automation provenance is not.",
        ), "ae2:logic_processor", 64, (stock, drone), 10.0, -1.0),
        _item_quest(steel, "Automated Steel Batch", "Industry should continue while unwatched.", (
            "Produce sixty-four Steel Ingots through the assembler-side supply chain.",
            "Leave, return, and inspect the buffers before calling it unattended.",
        ), "immersiveengineering:ingot_steel", 64, (assembler, laser), 10.0, 1.0),
        _energy_quest(power, "Stable Power Proof", "Submit fifty million FE without exceeding the input cap.", (
            "Submit fifty million FE at no more than 500,000 FE per transfer.",
            "This proves production capacity, not reserve stability. Watch the grid under load.",
        ), 50_000_000, 500_000, (processors, steel), 12.0, 0.0),
        _item_quest(finale, "Signal Triangulated", "Three rings define four hidden coordinates.", (
            "Build three Quantum Rings as a physical proxy for the triangulation array.",
            "The signal resolves into four encrypted schematic locations. None are here.",
            "&d[MEMORY FRAGMENT 10 RESTORED]&r",
            "&7...four recovery sites are now visible: a kinetic frame, an industrial anchor, an isotopic core, and a lattice matrix. Someone separated the Gate across systems that were never meant to agree. The Deep Vault key was left beside the coordinates...&r",
        ), "ae2:quantum_ring", 3, (power,), 14.0, 0.0, finale=(24, 500), deep_vault_key=True),
    )
    return ChapterSpec("story/11-convergence", "Convergence", STORY, "kubejs:deep_vault_key", 10, quests)


def _chapter_twelve(previous: str) -> ChapterSpec:
    core = "story/12-frontier-machines/machine-core"
    pulverizer = "story/12-frontier-machines/pulverization"
    centrifuge = "story/12-frontier-machines/centrifuge"
    assembly = "story/12-frontier-machines/assembly"
    foundry = "story/12-frontier-machines/foundry"
    laser = "story/12-frontier-machines/laser-processing"
    jetpack = "story/12-frontier-machines/jetpack"
    reactor = "story/12-frontier-machines/reactor-frontier"
    prometheum = "story/12-frontier-machines/prometheum"
    finale = "story/12-frontier-machines/kinetic-schematic"
    quests = (
        _item_quest(core, "Machine Core", "Oritech begins where ordinary frames stop.", (
            "Produce four Machine Cores. They anchor Oritech's first processing blocks.",
            "A frontier is simply a factory whose maintenance manual has not arrived yet.",
        ), "oritech:machine_core_1", 4, (previous,), 0.0, 0.0),
        _item_quest(pulverizer, "Pulverization", "Reduce material before asking it to change.", (
            "Build an Oritech Pulverizer and give its output a dedicated buffer.",
            "Grinding is simple. Preventing mixed output from becoming geology again is not.",
        ), "oritech:pulverizer_block", 1, (core,), 2.0, 0.0),
        _item_quest(centrifuge, "Centrifuge", "Separation rewards controlled imbalance.", (
            "Build an Oritech Centrifuge and process one recipe from input to output.",
            "The task verifies the machine. Stable speed and clean routing remain yours to prove.",
        ), "oritech:centrifuge_block", 1, (pulverizer,), 4.0, 0.0),
        _item_quest(assembly, "Assembly", "Parts become systems by repeatable placement.", (
            "Build an Oritech Assembler and connect it to the processing line.",
            "Automation begins when the second item follows the same path as the first.",
        ), "oritech:assembler_block", 1, (centrifuge,), 6.0, 0.0),
        _item_quest(foundry, "Foundry", "Heat is useful when given boundaries.", (
            "Build an Oritech Foundry and provide isolated input and output storage.",
            "The quest detects the block, not your heat policy. Keep one anyway.",
        ), "oritech:foundry_block", 1, (assembly,), 8.0, -1.0),
        _item_quest(laser, "Laser Processing", "Precision by concentrated inconvenience.", (
            "Build a Laser Arm and reserve safe clearance around its work area.",
            "A beam does not become intelligent because its target was correct once.",
        ), "oritech:laser_arm_block", 1, (assembly,), 8.0, 1.0),
        _item_quest(jetpack, "Jetpack", "Vertical access changes every maintenance route.", (
            "Build an Oritech Jetpack and test its charge, control, and safe descent.",
            "Possession is detectable. Landing with dignity is not.",
        ), "oritech:jetpack", 1, (foundry,), 10.0, -1.0),
        _item_quest(reactor, "Reactor Frontier", "Compact power deserves expanded caution.", (
            "Build an Oritech Reactor Controller and inspect the complete reactor layout before startup.",
            "The controller proves access to the system. It does not prove the system is safe.",
        ), "oritech:reactor_controller", 1, (foundry, laser), 10.0, 1.0),
        _item_quest(prometheum, "Prometheum", "A metal named for theft. Reassuring.", (
            "Produce sixteen Prometheum Ingots through the reactor-era processing chain.",
            "The recovered schematic checksum recognizes this alloy as its final material proof.",
        ), "oritech:prometheum_ingot", 16, (reactor,), 12.0, 1.0),
        _task_quest(finale, "Kinetic Schematic", "The first Gate key was hidden inside computation.", (
            "Build an Advanced Computing Engine to decrypt the kinetic frame schematic.",
            "The item proves the required Oritech tier. The schematic is the actual Gate recipe lock.",
            "&d[MEMORY FRAGMENT 11 RESTORED]&r",
            "&7...the four schematics were separated by design. No single division could assemble the Gate. My archive calls this mutual assurance. The casualty model calls it delay...&r",
        ), "item", {
            "item": {"count": 1, "id": "oritech:advanced_computing_engine"},
            "count": SnbtLong(1),
            "consume_items": False,
        }, (prometheum, jetpack), 14.0, 0.0, finale=(28, 550, "kubejs:schematic_kinetic_frame", "afterlight:gate_create")),
    )
    return ChapterSpec(
        "story/12-frontier-machines", "Frontier Machines", STORY,
        "oritech:advanced_computing_engine", 11, quests,
    )


def _chapter_thirteen(previous: str) -> ChapterSpec:
    factory = "story/13-war-below/ancient-factory"
    harbinger = "story/13-war-below/harbinger"
    citadel = "story/13-war-below/ruined-citadel"
    guardian = "story/13-war-below/ender-guardian"
    arena = "story/13-war-below/burning-arena"
    ignis = "story/13-war-below/ignis"
    city = "story/13-war-below/sunken-city"
    leviathan = "story/13-war-below/leviathan"
    salvage = "story/13-war-below/war-salvage"
    finale = "story/13-war-below/industry-schematic"
    quests = (
        _task_quest(factory, "Ancient Factory", "The machinery below is still defended.", (
            "Locate the Ancient Factory. Bring repair supplies and a route home.",
            "Structure detection proves arrival, not survival. I recommend both.",
        ), "structure", {"structure": "cataclysm:ancient_factory"}, (previous,), 0.0, 0.0),
        _task_quest(harbinger, "Harbinger", "The factory's alarm learned to walk.", (
            "Defeat the Harbinger and inspect the arena before collecting salvage.",
            "Its attack cycle is information. Treat the first attempt as research.",
        ), "kill", {"entity": "cataclysm:the_harbinger", "value": SnbtLong(1)}, (factory,), 2.0, 0.0),
        _task_quest(citadel, "Ruined Citadel", "A fortress built around one refusal.", (
            "Locate the Ruined Citadel and establish a recoverable approach.",
            "Ancient architecture is not consent to enter. It is merely difficult to ask.",
        ), "structure", {"structure": "cataclysm:ruined_citadel"}, (harbinger,), 4.0, 0.0),
        _task_quest(guardian, "Ender Guardian", "Stone, void, and practiced hostility.", (
            "Defeat the Ender Guardian. Use cover and respect the arena's vertical hazards.",
            "The schematic signal is stronger beneath its chamber.",
        ), "kill", {"entity": "cataclysm:ender_guardian", "value": SnbtLong(1)}, (citadel,), 6.0, 0.0),
        _task_quest(arena, "Burning Arena", "Heat without industry is only weather.", (
            "Locate the Burning Arena and prepare fire resistance before engagement.",
            "The structure task verifies the threshold. It does not verify your supplies.",
        ), "structure", {"structure": "cataclysm:burning_arena"}, (guardian,), 8.0, 0.0),
        _task_quest(ignis, "Ignis", "The furnace has a name and a sword.", (
            "Defeat Ignis. Observe the shield windows rather than forcing every opening.",
            "Efficiency includes knowing when not to attack.",
        ), "kill", {"entity": "cataclysm:ignis", "value": SnbtLong(1)}, (arena,), 10.0, 0.0),
        _task_quest(city, "Sunken City", "Pressure returns, now with architecture.", (
            "Locate the Sunken City and mark an air-safe retreat path.",
            "The signal descends past the point where ordinary logistics remain convenient.",
        ), "structure", {"structure": "cataclysm:sunken_city"}, (ignis,), 12.0, 0.0),
        _task_quest(leviathan, "Leviathan", "The sea kept one of the old weapons.", (
            "Defeat the Leviathan. Prepare for a fight where distance changes quickly.",
            "I can count the victory. I cannot retrieve your dropped equipment.",
        ), "kill", {"entity": "cataclysm:the_leviathan", "value": SnbtLong(1)}, (city,), 14.0, 0.0),
        _item_quest(salvage, "War Salvage", "Sixteen ingots survived their intended machine.", (
            "Recover sixteen Ancient Metal Ingots from Cataclysm's war sites.",
            "The alloy matches an Ascendancy industrial anchor specification.",
        ), "cataclysm:ancient_metal_ingot", 16, (leviathan,), 16.0, 0.0),
        _task_quest(finale, "Industry Schematic", "Fusion by impact. The old engineers lacked subtlety.", (
            "Build a Mechanical Fusion Anvil to decrypt the industrial anchor schematic.",
            "The anvil proves the recovered war industry tier. The schematic remains the recipe lock.",
            "&d[MEMORY FRAGMENT 12 RESTORED]&r",
            "&7...the defense complexes were not protecting cities. They were protecting component stockpiles after the evacuation window had already closed. The machines followed their final orders perfectly...&r",
        ), "item", {
            "item": {"count": 1, "id": "cataclysm:mechanical_fusion_anvil"},
            "count": SnbtLong(1),
            "consume_items": False,
        }, (salvage,), 18.0, 0.0, finale=(30, 600, "kubejs:schematic_industrial_anchor", "afterlight:gate_ie")),
    )
    return ChapterSpec(
        "story/13-war-below", "The War Below", STORY,
        "cataclysm:mechanical_fusion_anvil", 12, quests,
    )


def _chapter_fourteen(previous: str) -> ChapterSpec:
    assembly = "story/14-quantum-weather/fission-assembly"
    fuel = "story/14-quantum-weather/fissile-fuel"
    turbine = "story/14-quantum-weather/turbine"
    polonium = "story/14-quantum-weather/polonium"
    plutonium = "story/14-quantum-weather/plutonium"
    sps = "story/14-quantum-weather/sps"
    antimatter = "story/14-quantum-weather/antimatter"
    power = "story/14-quantum-weather/energy-proof"
    finale = "story/14-quantum-weather/isotope-schematic"
    quests = (
        _item_quest(assembly, "Fission Assembly", "Eight fuel columns begin a serious conversation.", (
            "Produce eight Fission Fuel Assemblies and design the reactor around safe access.",
            "Blocks are detectable. Cooling, containment, and judgment are not.",
        ), "mekanismgenerators:fission_fuel_assembly", 8, (previous,), 0.0, 0.0),
        _item_quest(fuel, "Fissile Fuel", "The chemical has no item form, so prove its machine.", (
            "Build an Isotopic Centrifuge and establish the fissile fuel production path.",
            "FTB Quests cannot count the chemical directly. Running the line is your proof.",
        ), "mekanism:isotopic_centrifuge", 1, (assembly,), 2.0, -1.0),
        _item_quest(turbine, "Turbine", "Waste heat should leave with useful work.", (
            "Produce sixteen Turbine Casings and complete a turbine sized for the reactor.",
            "The task sees casing inventory, not multiblock formation or throughput.",
        ), "mekanismgenerators:turbine_casing", 16, (assembly,), 2.0, 1.0),
        _item_quest(polonium, "Polonium", "Radiation made portable. Handle accordingly.", (
            "Produce eight Polonium Pellets through a contained nuclear chain.",
            "Keep waste handling independent from production convenience.",
        ), "mekanism:pellet_polonium", 8, (fuel,), 4.0, -1.0),
        _item_quest(plutonium, "Plutonium", "A second isotope, not a second chance.", (
            "Produce eight Plutonium Pellets and verify every waste buffer.",
            "Redundant containment is cheaper than an interesting landscape.",
        ), "mekanism:pellet_plutonium", 8, (fuel,), 4.0, 1.0),
        _item_quest(sps, "SPS", "Matter waits behind a very expensive acronym.", (
            "Produce sixteen SPS Casings and form the Supercritical Phase Shifter.",
            "The quest verifies casing stock. Formation and rate remain live tests.",
        ), "mekanism:sps_casing", 16, (polonium, plutonium), 6.0, 0.0),
        _item_quest(antimatter, "Antimatter", "One pellet contains an unreasonable amount of consequence.", (
            "Produce one Antimatter Pellet through the completed SPS chain.",
            "Store it where accidental crafting cannot become a design review.",
        ), "mekanism:pellet_antimatter", 1, (sps,), 8.0, 0.0),
        _energy_quest(power, "100M FE Proof", "Submit one hundred million FE under a bounded input rate.", (
            "Submit one hundred million FE at no more than 1,000,000 FE per transfer.",
            "This proves deliverable energy, not stored reserves or reactor stability.",
        ), 100_000_000, 1_000_000, (antimatter,), 10.0, 0.0),
        _task_quest(finale, "Isotope Schematic", "The third key resolves under antimatter-era computation.", (
            "Build an Antiprotonic Nucleosynthesizer to decrypt the isotopic core schematic.",
            "The machine proves the tier. Safe operation remains outside this task's reach.",
            "&d[MEMORY FRAGMENT 13 RESTORED]&r",
            "&7...the Cascade was not a reactor failure. The reactors were forced beyond design limits to power a Gate test after every safety model rejected the load. I signed the override because my threat forecast ranked delay as worse...&r",
        ), "item", {
            "item": {"count": 1, "id": "mekanism:antiprotonic_nucleosynthesizer"},
            "count": SnbtLong(1),
            "consume_items": False,
        }, (power,), 12.0, 0.0, finale=(32, 700, "kubejs:schematic_isotopic_core", "afterlight:gate_mekanism")),
    )
    return ChapterSpec(
        "story/14-quantum-weather", "Quantum Weather", STORY,
        "mekanism:pellet_antimatter", 13, quests,
    )


def _chapter_fifteen(previous: str) -> ChapterSpec:
    harness = "story/15-long-sky/flight-harness"
    trial = "story/15-long-sky/aeronautics-trial"
    propulsion = "story/15-long-sky/propulsion"
    storage = "story/15-long-sky/mobile-storage"
    altitude = "story/15-long-sky/high-altitude-trial"
    starlight = "story/15-long-sky/starlight"
    forge = "story/15-long-sky/golem-forge"
    gatekeeper = "story/15-long-sky/gatekeeper-signal"
    relay = "story/15-long-sky/relay-core"
    finale = "story/15-long-sky/lattice-schematic"
    quests = (
        _item_quest(harness, "Flight Harness", "Leave the ground with a controlled return plan.", (
            "Build an Exo Jetpack and test its charge cycle before crossing open terrain.",
            "Flight converts walls into floors and falls into scheduling problems.",
        ), "oritech:exo_jetpack", 1, (previous,), 0.0, 0.0),
        _task_quest(trial, "Aeronautics Trial", "Prove lift with a machine larger than yourself.", (
            "Complete Aeronautics' Head in the Clouds advancement by building a working balloon craft.",
            "The advancement proves the mechanic directly. Keep the first landing uncomplicated.",
        ), "advancement", {
            "advancement": "aeronautics:head_in_the_clouds",
            "criterion": "",
        }, (harness,), 2.0, 0.0),
        _task_quest(propulsion, "Propulsion", "Lift is access. Thrust is intent.", (
            "Complete Aeronautics' In Thrust We Trust advancement with powered propulsion.",
            "A craft that can move should also be able to stop near where you intended.",
        ), "advancement", {
            "advancement": "aeronautics:in_thrust_we_trust",
            "criterion": "",
        }, (trial,), 4.0, 0.0),
        _item_quest(storage, "Mobile Storage", "Cargo changes flight from spectacle to infrastructure.", (
            "Build an Oritech Large Storage Block for mobile expedition supplies.",
            "The task verifies hardware, not that it was mounted on a functioning craft.",
        ), "oritech:large_storage_block", 1, (propulsion,), 6.0, 0.0),
        _item_quest(altitude, "High-Altitude Trial", "Use a stable proxy where altitude is not headlessly measurable.", (
            "Build an Oritech Jetpack Elytra and complete a controlled high-altitude flight.",
            "The item is the durable task proxy. Your flight log is the operational proof.",
        ), "oritech:jetpack_elytra", 1, (storage,), 8.0, 0.0),
        _task_quest(starlight, "Starlight", "The sky continues through another boundary.", (
            "Enter the Eternal Starlight dimension and establish a marked return point.",
            "Dimension detection confirms arrival. It does not guarantee the portal remains convenient.",
        ), "dimension", {"dimension": "eternal_starlight:starlight"}, (altitude,), 10.0, 0.0),
        _task_quest(forge, "Golem Forge", "A foundry built for hands larger than ours.", (
            "Locate the Golem Forge and secure the route before entering its center.",
            "The lattice signal is reflected through the structure's old machinery.",
        ), "structure", {"structure": "eternal_starlight:golem_forge"}, (starlight,), 12.0, 0.0),
        _task_quest(gatekeeper, "Gatekeeper Signal", "The relay has appointed its own custodian.", (
            "Defeat the Gatekeeper and isolate the signal source beneath the forge.",
            "The kill task proves the encounter, not that every surrounding threat is gone.",
        ), "kill", {
            "entity": "eternal_starlight:the_gatekeeper",
            "value": SnbtLong(1),
        }, (forge,), 14.0, 0.0),
        _item_quest(relay, "Relay Core", "Entanglement gives distance fewer excuses.", (
            "Build an ME Quantum Link as the recovered relay's network core.",
            "Keep both ends powered. A quantum bridge can still fail for ordinary reasons.",
        ), "ae2:quantum_link", 1, (gatekeeper,), 16.0, 0.0),
        _task_quest(finale, "Lattice Schematic", "Two singularities agree on one final key.", (
            "Produce a Quantum Entangled Singularity to decrypt the lattice matrix schematic.",
            "The item proves the AE2 tier. The schematic remains the physical recipe lock.",
            "&d[MEMORY FRAGMENT 14 RESTORED]&r",
            "&7...the first Gate opened for eleven seconds. The transit log shows no outbound mass. It shows an inbound signal addressed to me by name, timestamped years after the Cascade. I concealed the result...&r",
        ), "item", {
            "item": {"count": 1, "id": "ae2:quantum_entangled_singularity"},
            "count": SnbtLong(1),
            "consume_items": False,
        }, (relay,), 18.0, 0.0, finale=(34, 800, "kubejs:schematic_lattice_matrix", "afterlight:gate_ae2")),
    )
    return ChapterSpec(
        "story/15-long-sky", "The Long Sky", STORY,
        "ae2:quantum_entangled_singularity", 14, quests,
    )


def _chapter_sixteen(previous: str) -> ChapterSpec:
    keys = "story/16-architect/four-keys"
    storage = "story/16-architect/mega-storage"
    cpu = "story/16-architect/crafting-cpu"
    matrix = "story/16-architect/assembler-matrix"
    fusion = "story/16-architect/fusion-controller"
    certified = "story/16-architect/certified-bulk-quotas"
    remnant = "story/16-architect/ancient-remnant"
    finale = "story/16-architect/gate-blueprint"
    gate_stages = (
        "afterlight:gate_create",
        "afterlight:gate_ie",
        "afterlight:gate_mekanism",
        "afterlight:gate_ae2",
    )
    certification_stages = (
        "afterlight_cert_kinetics_i",
        "afterlight_cert_logistics_i",
        "afterlight_cert_ore_loop_i",
        "afterlight_cert_autocrafting_i",
        "afterlight_cert_cross_mod_i",
        "afterlight_cert_power_i",
        "afterlight_cert_infrastructure_ii",
    )
    quests = (
        QuestSpec(
            slug=keys,
            title="Four Keys",
            subtitle="Possession is insufficient. Recovery must be recorded.",
            description=(
                "Complete all four schematic recoveries and claim their progression stages.",
                "The stages prove the recovery chain. Keep the physical schematics for Gate crafting.",
            ),
            x=0.0,
            y=0.0,
            dependencies=(previous,),
            tasks=tuple(
                TaskSpec(f"{keys}/task/{stage.rsplit('_', 1)[-1]}", "gamestage", {"stage": stage})
                for stage in gate_stages
            ),
            rewards=_routine_rewards(keys),
        ),
        _item_quest(storage, "Mega Storage", "Four cells make capacity visible.", (
            "Build four 256K Item Storage Cells and distribute them across protected drives.",
            "Capacity is not redundancy. Back up what cannot be reconstructed.",
        ), "ae2:item_storage_cell_256k", 4, (keys,), 2.0, -1.0),
        _item_quest(cpu, "256K Crafting CPU", "Large jobs need somewhere to become unfinished.", (
            "Build one 256K Crafting Storage block for the Gate component job queue.",
            "Crafting memory is working space, not permanent storage.",
        ), "ae2:256k_crafting_storage", 1, (storage,), 4.0, -1.0),
        _item_quest(matrix, "Assembler Matrix", "Sixteen workers, one explicit pattern set.", (
            "Build sixteen Molecular Assemblers and connect a balanced autocrafting matrix.",
            "The task sees assemblers. Channel balance and pattern placement remain your proof.",
        ), "ae2:molecular_assembler", 16, (cpu,), 6.0, -1.0),
        _item_quest(fusion, "Fusion Controller", "Power for the Gate should not borrow from survival systems.", (
            "Build a Fusion Reactor Controller and reserve a separate Gate power path.",
            "The controller proves access. A formed, fueled, stable reactor is still required.",
        ), "mekanismgenerators:fusion_reactor_controller", 1, (keys,), 2.0, 1.0),
        QuestSpec(
            slug=certified,
            title="Certified Bulk Quotas",
            subtitle="Seven systems must work before one system may trust them.",
            description=(
                "Complete all seven automation certification capstones.",
                "These stages prove the certification quests, not your current inventory quantities.",
                "If a line cannot recover from a full output, it is not ready for Gate duty.",
            ),
            x=8.0,
            y=0.0,
            dependencies=(matrix, fusion),
            tasks=tuple(
                TaskSpec(f"{certified}/task/{index}", "gamestage", {"stage": stage})
                for index, stage in enumerate(certification_stages, start=1)
            ),
            rewards=_routine_rewards(certified),
        ),
        _task_quest(remnant, "Ancient Remnant", "One guardian remains between proof and plan.", (
            "Defeat the Ancient Remnant after the automation certifications are complete.",
            "Bring a tested loadout. Certification does not make sandstone less violent.",
        ), "kill", {
            "entity": "cataclysm:ancient_remnant",
            "value": SnbtLong(1),
        }, (certified,), 10.0, 0.0),
        _task_quest(finale, "Gate Blueprint", "Four schematics resolve into one construction contract.", (
            "Confirm that the four recovered schematics are secured and the automation certifications are complete.",
            "I can now compile their shared constraints into the Gate Blueprint. A checkmark records your readiness.",
            "The awarded blueprint is the recipe lock. Draconic progression remains sealed until after Chapter 20.",
            "The Deep Vault and Undercurrent still contain the components this plan cannot replace.",
            "&d[MEMORY FRAGMENT 15 RESTORED]&r",
            "&7...I did not merely approve the Gate test. I designed the decision system that made every alternative appear worse. The incoming signal contains my architecture, but not my memory. Build carefully. Whatever answers may believe it is me...&r",
        ), "checkmark", {}, (remnant,), 12.0, 0.0, finale=(40, 1000, "kubejs:gate_blueprint", "afterlight_act3_complete")),
    )
    return ChapterSpec(
        "story/16-architect", "Architect", STORY, "kubejs:gate_blueprint", 15, quests,
    )


def _certification_logistics() -> ChapterSpec:
    drawer = "certifications/logistics-i/drawer-bank"
    controller = "certifications/logistics-i/controller"
    pipes = "certifications/logistics-i/item-pipes"
    filters = "certifications/logistics-i/filtered-route"
    round_robin = "certifications/logistics-i/round-robin"
    finale = "certifications/logistics-i/overflow-safety"
    quests = (
        _certification_item_quest(drawer, "Drawer Bank", "Buffers should advertise their limits.", (
            "Build four Functional Storage drawers as visible input and output buffers.",
            "A hidden backlog is not storage. It is a delayed incident.",
        ), "functionalstorage:oak_1", 4, ("5ADAE277C9FEF0F1",), 0.0, 0.0),
        _certification_item_quest(controller, "Storage Controller", "One address, several honest inventories.", (
            "Build a Storage Controller and link the drawer bank.",
            "Test each drawer from the controller before attaching automation.",
        ), "functionalstorage:storage_controller", 1, (drawer,), 2.0, 0.0),
        _certification_item_quest(pipes, "Item Pipes", "Routing starts with enough segments to make mistakes.", (
            "Produce sixteen Item Pipes and connect a source, buffer, and destination.",
            "Do not connect the final machine until the buffer path is visible.",
        ), "pipez:item_pipe", 16, (controller,), 4.0, 0.0),
        _certification_item_quest(filters, "Filtered Route", "A route without a filter is a future mixture.", (
            "Build an Improved Pipe Upgrade, then configure an allowlist on one destination.",
            "The task verifies the upgrade. Send a wrong item to prove the filter refuses it.",
        ), "pipez:improved_upgrade", 1, (pipes,), 6.0, -1.0),
        _certification_item_quest(round_robin, "Round-Robin Routing", "Equal destinations deserve equal inconvenience.", (
            "Build an Advanced Pipe Upgrade and enable round-robin distribution across two outputs.",
            "Count several deliveries. One alternating pair is not a stability test.",
        ), "pipez:advanced_upgrade", 1, (filters,), 8.0, -1.0),
        _certification_item_quest(finale, "Overflow Safety", "Full output must stop the line without losing matter.", (
            "Build a Void Upgrade for a deliberately safe overflow drawer, then test a full normal output.",
            "Only disposable byproducts belong behind the void path. Valuable output must backpressure cleanly.",
        ), "functionalstorage:void_upgrade", 1, (round_robin,), 10.0, 0.0,
            stage="afterlight_cert_logistics_i"),
    )
    return ChapterSpec(
        "certifications/logistics-i", "Logistics I", CERTIFICATIONS,
        "functionalstorage:storage_controller", 1, quests,
    )


def _certification_ore_loop(logistics_finale: str) -> ChapterSpec:
    crusher = "certifications/ore-loop-i/crusher"
    enrichment = "certifications/ore-loop-i/enrichment"
    smelter = "certifications/ore-loop-i/smelter"
    buffer = "certifications/ore-loop-i/buffer"
    energy = "certifications/ore-loop-i/energy"
    finale = "certifications/ore-loop-i/throughput"
    quests = (
        _certification_item_quest(crusher, "Crushing Stage", "First machine, first controlled reduction.", (
            "Build a Mekanism Crusher and give it dedicated input and output buffers.",
            "This certification tests a three-machine loop, not a shared machine pile.",
        ), "mekanism:crusher", 1, (CHAPTER_FIVE_FINALE, logistics_finale), 0.0, 0.0),
        _certification_item_quest(enrichment, "Enrichment Stage", "Intermediate material needs a named destination.", (
            "Build an Enrichment Chamber and route the Crusher output into it.",
            "Keep a bypass chest available while the line is being tuned.",
        ), "mekanism:enrichment_chamber", 1, (crusher,), 2.0, 0.0),
        _certification_item_quest(smelter, "Smelting Stage", "The third machine should finish, not improvise.", (
            "Build an Energized Smelter and complete the processing chain.",
            "Lock its input to the expected intermediate before unattended operation.",
        ), "mekanism:energized_smelter", 1, (enrichment,), 4.0, 0.0),
        _certification_item_quest(buffer, "Measured Buffer", "A bin makes congestion visible.", (
            "Build a Basic Bin as the final output buffer.",
            "Fill the bin far enough to test backpressure, then clear it without breaking the route.",
        ), "mekanism:basic_bin", 1, (smelter,), 6.0, -1.0),
        _certification_quest(energy, "Energy Budget", "Five million FE, transferred deliberately.", (
            "Submit five million FE at no more than 100,000 FE per transfer.",
            "The limit catches lines that rely on one uncontrolled power spike.",
        ), "forge_energy", {
            "value": SnbtLong(5_000_000),
            "max_input": SnbtLong(100_000),
        }, (smelter,), 6.0, 1.0),
        _certification_item_quest(finale, "256-Ingot Run", "One stack is a sample. Four stacks are a process.", (
            "Produce 256 Osmium Ingots through the complete loop.",
            "Inventory quantity is detectable. Observe the line long enough to verify recovery from a full output.",
        ), "mekanism:ingot_osmium", 256, (buffer, energy), 8.0, 0.0,
            stage="afterlight_cert_ore_loop_i"),
    )
    return ChapterSpec(
        "certifications/ore-loop-i", "Ore Loop I", CERTIFICATIONS,
        "mekanism:enrichment_chamber", 2, quests,
    )


def _certification_autocrafting(logistics_finale: str) -> ChapterSpec:
    provider = "certifications/autocrafting-i/provider"
    assembler = "certifications/autocrafting-i/assembler"
    cpu = "certifications/autocrafting-i/cpu"
    patterns = "certifications/autocrafting-i/patterns"
    order = "certifications/autocrafting-i/order"
    finale = "certifications/autocrafting-i/recovery"
    quests = (
        _certification_item_quest(provider, "Pattern Provider", "A recipe needs a network address.", (
            "Build a Pattern Provider and connect it to a channel-managed AE2 network.",
            "Keep the provider visible until every adjacent machine is proven.",
        ), "ae2:pattern_provider", 1, ("story/06-lattice/first-autocraft", logistics_finale), 0.0, 0.0),
        _certification_item_quest(assembler, "Molecular Assembler", "The network may now act on its memory.", (
            "Build four Molecular Assemblers around the provider.",
            "Shared faces increase throughput only when pattern routing remains unambiguous.",
        ), "ae2:molecular_assembler", 4, (provider,), 2.0, 0.0),
        _certification_item_quest(cpu, "Crafting CPU", "Queued work requires explicit memory.", (
            "Build a 4K Crafting Storage block and form a valid crafting CPU.",
            "The task sees the block. Confirm the multiblock appears in the crafting status screen.",
        ), "ae2:4k_crafting_storage", 1, (assembler,), 4.0, 0.0),
        _certification_item_quest(patterns, "Encoded Set", "Sixteen instructions reveal routing mistakes quickly.", (
            "Encode sixteen Crafting Patterns across more than one processing depth.",
            "Include at least one recipe that depends on another encoded recipe.",
        ), "ae2:crafting_pattern", 16, (cpu,), 6.0, -1.0),
        _certification_item_quest(order, "256-Item Order", "A useful request is large enough to expose starvation.", (
            "Autocraft 256 Quartz Glass in one order.",
            "The task verifies the completed quantity. The crafting monitor is your proof of provenance.",
        ), "ae2:quartz_glass", 256, (patterns,), 8.0, -1.0),
        _certification_quest(finale, "Failure Recovery", "Interrupt the line before trusting it.", (
            "Block one assembler output, cancel a job, clear the obstruction, and submit the checkmark after recovery.",
            "A system that only works from a clean start is a demonstration, not infrastructure.",
        ), "checkmark", {}, (order,), 10.0, 0.0, stage="afterlight_cert_autocrafting_i"),
    )
    return ChapterSpec(
        "certifications/autocrafting-i", "Autocrafting I", CERTIFICATIONS,
        "ae2:pattern_provider", 3, quests,
    )


def _certification_cross_mod(ore_finale: str, autocrafting_finale: str) -> ChapterSpec:
    input_path = "certifications/cross-mod-i/create-input"
    process = "certifications/cross-mod-i/mekanism-process"
    output = "certifications/cross-mod-i/ie-output"
    stocking = "certifications/cross-mod-i/ae2-stocking"
    batch = "certifications/cross-mod-i/steel-batch"
    finale = "certifications/cross-mod-i/recovery"
    quests = (
        _certification_item_quest(input_path, "Create Input", "Mechanical delivery begins the chain.", (
            "Produce eight Chutes and use Create to meter raw material into the process buffer.",
            "A belt line should stop at the buffer when the downstream system is unavailable.",
        ), "create:chute", 8, (ore_finale, autocrafting_finale), 0.0, 0.0),
        _certification_item_quest(process, "Mekanism Process", "One ecosystem transforms what another delivers.", (
            "Route the buffered input through a dedicated Mekanism Crusher.",
            "Do not let direct insertion bypass the visible input buffer.",
        ), "mekanism:crusher", 1, (input_path,), 2.0, 0.0),
        _certification_item_quest(output, "IE Output", "Heavy machinery closes the material loop.", (
            "Build an Immersive Engineering Metal Press as the final processing step.",
            "Provide a separate output inventory so a full AE2 network cannot trap the press conveyor.",
        ), "immersiveengineering:metal_press", 1, (process,), 4.0, 0.0),
        _certification_item_quest(stocking, "AE2 Stocking", "The lattice should request, not merely receive.", (
            "Build two ME Interfaces and configure one stocked output target.",
            "Test both replenishment and the behavior when the destination is already full.",
        ), "ae2:interface", 2, (output,), 6.0, -1.0),
        _certification_item_quest(batch, "Steel Batch", "Two hundred fifty-six units cross four systems.", (
            "Produce 256 Steel Ingots through the connected chain.",
            "The item count cannot prove the route. Watch the full batch and inspect every buffer afterward.",
        ), "immersiveengineering:ingot_steel", 256, (stocking,), 8.0, -1.0),
        _certification_quest(finale, "Cross-System Recovery", "Disconnect one boundary and recover without item loss.", (
            "Break one transport boundary, allow the upstream buffer to fill, reconnect it, and submit the checkmark.",
            "Certification records recovery behavior, not merely a successful first pass.",
        ), "checkmark", {}, (batch,), 10.0, 0.0, stage="afterlight_cert_cross_mod_i"),
    )
    return ChapterSpec(
        "certifications/cross-mod-i", "Cross-Mod I", CERTIFICATIONS,
        "immersiveengineering:metal_press", 4, quests,
    )


def _certification_power() -> ChapterSpec:
    generation = "certifications/power-i/generation"
    storage = "certifications/power-i/storage"
    induction = "certifications/power-i/induction"
    routing = "certifications/power-i/routing"
    proof = "certifications/power-i/proof"
    finale = "certifications/power-i/shutdown"
    quests = (
        _certification_item_quest(generation, "Dedicated Generation", "Infrastructure power should have one accountable source.", (
            "Build a Nitro Reactor for the certification grid.",
            "Keep survival storage isolated until the new grid has passed its shutdown test.",
        ), "powah:reactor_nitro", 1, ("story/09-grid/energy-reserve",), 0.0, 0.0),
        _certification_item_quest(storage, "Local Reserve", "A cell buys time to stop cleanly.", (
            "Build a Nitro Energy Cell and place it between generation and the distribution boundary.",
            "Reserve capacity is useful only when its discharge path is intentional.",
        ), "powah:energy_cell_nitro", 1, (generation,), 2.0, 0.0),
        _certification_item_quest(induction, "Induction Buffer", "Sixteen casings make the second reserve inspectable.", (
            "Produce sixteen Induction Casings and form a Mekanism induction matrix.",
            "Use the matrix to separate short spikes from sustained load.",
        ), "mekanism:induction_casing", 16, (storage,), 4.0, 0.0),
        QuestSpec(
            slug=routing,
            title="Priority Routing",
            subtitle="One plug imports. One point obeys priority.",
            description=(
                "Build a Flux Plug and Flux Point, then assign explicit network priorities.",
                "Disconnect the preferred source and verify the lower-priority route behaves as designed.",
            ),
            x=6.0,
            y=-1.0,
            dependencies=(induction,),
            tasks=(
                TaskSpec(f"{routing}/task/plug", "item", {
                    "item": {"count": 1, "id": "fluxnetworks:flux_plug"},
                    "count": SnbtLong(1),
                    "consume_items": False,
                }),
                TaskSpec(f"{routing}/task/point", "item", {
                    "item": {"count": 1, "id": "fluxnetworks:flux_point"},
                    "count": SnbtLong(1),
                    "consume_items": False,
                }),
            ),
            rewards=_routine_rewards(routing),
        ),
        _certification_quest(proof, "100M FE Delivery", "Capacity becomes useful when it can be delivered.", (
            "Submit one hundred million FE at no more than 1,000,000 FE per transfer.",
            "Observe the reserves during submission and confirm no survival system browns out.",
        ), "forge_energy", {
            "value": SnbtLong(100_000_000),
            "max_input": SnbtLong(1_000_000),
        }, (routing,), 8.0, -1.0),
        _certification_quest(finale, "Emergency Shutdown", "A safe grid stops before it becomes a story fragment.", (
            "Trigger the emergency cutoff, verify generation stops feeding the line, then restore service in order.",
            "Submit the checkmark only after storage, routing, and consumers all recover.",
        ), "checkmark", {}, (proof,), 10.0, 0.0, stage="afterlight_cert_power_i"),
    )
    return ChapterSpec(
        "certifications/power-i", "Power I", CERTIFICATIONS,
        "powah:reactor_nitro", 5, quests,
    )


def _certification_infrastructure(
    logistics_finale: str,
    ore_finale: str,
    autocrafting_finale: str,
    cross_mod_finale: str,
    power_finale: str,
) -> ChapterSpec:
    proof = "certifications/infrastructure-ii/stage-proof"
    sheets = "certifications/infrastructure-ii/sheets"
    processors = "certifications/infrastructure-ii/processors"
    circuits = "certifications/infrastructure-ii/circuits"
    steel = "certifications/infrastructure-ii/steel"
    finale = "certifications/infrastructure-ii/unattended"
    stages = (
        "afterlight_cert_kinetics_i",
        "afterlight_cert_logistics_i",
        "afterlight_cert_ore_loop_i",
        "afterlight_cert_autocrafting_i",
        "afterlight_cert_cross_mod_i",
        "afterlight_cert_power_i",
    )
    quests = (
        QuestSpec(
            slug=proof,
            title="Six Certifications",
            subtitle="Separate proofs become one operating standard.",
            description=(
                "Complete Kinetics, Logistics, Ore Loop, Autocrafting, Cross-Mod, and Power certifications.",
                "The stage tasks verify claimed certificates before the bulk trial begins.",
            ),
            x=0.0,
            y=0.0,
            dependencies=(
                logistics_finale,
                ore_finale,
                autocrafting_finale,
                cross_mod_finale,
                power_finale,
            ),
            tasks=tuple(
                TaskSpec(f"{proof}/task/{index}", "gamestage", {"stage": stage})
                for index, stage in enumerate(stages, start=1)
            ),
            rewards=_routine_rewards(proof),
        ),
        _certification_item_quest(sheets, "Kinetic Quota", "One thousand twenty-four sheets without hand feeding.", (
            "Produce 1,024 Iron Sheets through the certified kinetic line.",
            "Do not refill or clear a machine manually during the observed run.",
        ), "create:iron_sheet", 1024, (proof,), 2.0, -2.0),
        _certification_item_quest(processors, "Lattice Quota", "Five hundred twelve processors, all requested.", (
            "Autocraft 512 Logic Processors through the certified lattice.",
            "Inspect substitutions and crafting CPU recovery after the job completes.",
        ), "ae2:logic_processor", 512, (proof,), 2.0, -0.5),
        _certification_item_quest(circuits, "Pressure Quota", "Five hundred twelve circuits under stable pressure.", (
            "Produce 512 Printed Circuit Boards through the pressure line.",
            "Confirm pressure, etching supply, and output handling remain unattended.",
        ), "pneumaticcraft:printed_circuit_board", 512, (proof,), 2.0, 1.0),
        _certification_item_quest(steel, "Industry Quota", "One thousand twenty-four ingots through shared logistics.", (
            "Produce 1,024 Steel Ingots while the other certified systems remain online.",
            "The count proves inventory. Your logs prove the factory did not borrow manual intervention.",
        ), "immersiveengineering:ingot_steel", 1024, (proof,), 2.0, 2.5),
        _certification_quest(finale, "Unattended Cycle", "Leave the facility. Return to evidence, not hope.", (
            "Run all four quotas unattended through one complete buffer cycle, then inspect every failure boundary.",
            "Submit the checkmark when full outputs, power loss, and restart recovery have all been tested.",
        ), "checkmark", {}, (sheets, processors, circuits, steel), 5.0, 0.0,
            stage="afterlight_cert_infrastructure_ii"),
    )
    return ChapterSpec(
        "certifications/infrastructure-ii", "Infrastructure II", CERTIFICATIONS,
        "ae2:logic_processor", 6, quests,
    )


def _depot_chapter(
    tier: str,
    order_index: int,
    cost: int,
    table_id: SnbtLong,
    icon: str,
    dependency: str = "",
) -> ChapterSpec:
    slug = f"certifications/depot-{tier.lower()}"
    exchange = f"{slug}/exchange"
    quest = QuestSpec(
        slug=exchange,
        title=f"{tier} Supply Exchange",
        subtitle=f"{cost} Chits authorize one selected supply package.",
        description=(
            f"Submit {cost} Requisition Chits and choose one {tier.lower()}-tier supply package.",
            "The Depot returns materials, not progression keys. Choice rewards must be claimed individually.",
            "The exchange may be repeated after the cooldown. Chits are consumed on submission.",
        ),
        x=0.0,
        y=0.0,
        dependencies=((dependency,) if dependency else ()),
        tasks=(TaskSpec(f"{exchange}/task", "item", {
            "item": {"count": 1, "id": "kubejs:requisition_chit"},
            "count": SnbtLong(cost),
            "consume_items": True,
        }),),
        rewards=(RewardSpec(
            f"{exchange}/reward/choice",
            "choice",
            {"table_id": table_id},
        ),),
        can_repeat=True,
        repeat_cooldown=1200,
    )
    return ChapterSpec(
        slug,
        f"Requisition Depot: {tier}",
        CERTIFICATIONS,
        icon,
        order_index,
        (quest,),
    )


def build_catalog() -> list[ChapterSpec]:
    chapter_six = _chapter_six()
    chapter_seven = _chapter_seven(chapter_six.quests[-1].slug)
    chapter_eight = _chapter_eight(chapter_seven.quests[-1].slug)
    chapter_nine = _chapter_nine(chapter_eight.quests[-1].slug)
    chapter_ten = _chapter_ten(chapter_nine.quests[-1].slug)
    chapter_eleven = _chapter_eleven(chapter_ten.quests[-1].slug)
    chapter_twelve = _chapter_twelve(chapter_eleven.quests[-1].id)
    chapter_thirteen = _chapter_thirteen(chapter_twelve.quests[-1].slug)
    chapter_fourteen = _chapter_fourteen(chapter_thirteen.quests[-1].slug)
    chapter_fifteen = _chapter_fifteen(chapter_fourteen.quests[-1].slug)
    chapter_sixteen = _chapter_sixteen(chapter_fifteen.quests[-1].slug)
    logistics = _certification_logistics()
    ore_loop = _certification_ore_loop(logistics.quests[-1].slug)
    autocrafting = _certification_autocrafting(logistics.quests[-1].slug)
    cross_mod = _certification_cross_mod(
        ore_loop.quests[-1].slug,
        autocrafting.quests[-1].slug,
    )
    power = _certification_power()
    infrastructure = _certification_infrastructure(
        logistics.quests[-1].slug,
        ore_loop.quests[-1].slug,
        autocrafting.quests[-1].slug,
        cross_mod.quests[-1].slug,
        power.quests[-1].slug,
    )
    depot_early = _depot_chapter(
        "Early", 20, 8, DEPOT_EARLY_TABLE, "minecraft:iron_ingot",
    )
    depot_mid = _depot_chapter(
        "Mid", 21, 16, DEPOT_MID_TABLE, "create:brass_ingot", CHAPTER_FIVE_FINALE,
    )
    depot_late = _depot_chapter(
        "Late", 22, 32, DEPOT_LATE_TABLE, "mekanism:alloy_atomic",
        chapter_eleven.quests[-1].slug,
    )
    return [
        chapter_six,
        chapter_seven,
        chapter_eight,
        chapter_nine,
        chapter_ten,
        chapter_eleven,
        chapter_twelve,
        chapter_thirteen,
        chapter_fourteen,
        chapter_fifteen,
        chapter_sixteen,
        logistics,
        ore_loop,
        autocrafting,
        cross_mod,
        power,
        infrastructure,
        depot_early,
        depot_mid,
        depot_late,
    ]
