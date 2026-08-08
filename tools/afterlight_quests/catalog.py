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
            "Recover an Engineering Processor Press from a meteorite.",
            "The task can verify the press, not the search. Bring your own caution underground.",
        ), "ae2:engineering_processor_press", 1, (fluix,), 6.0, -1.0),
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
        _item_quest(finale, "First Autocraft", "Encode the intent. Verify the pattern.", (
            "Encode a Crafting Pattern. The quest can verify the pattern item, not a completed job.",
            "Run the job yourself. I will monitor the network for hesitation.",
            "&d[MEMORY FRAGMENT 05 RESTORED]&r",
            "&7...the evacuation archive was not lost. It was deleted in ordered blocks before the first civilian convoy departed. I executed the deletion. My authorization record contains no requesting officer...&r",
        ), "ae2:crafting_pattern", 1, (external,), 16.0, 0.0, finale=(12, 250)),
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


def build_catalog() -> list[ChapterSpec]:
    chapter_six = _chapter_six()
    chapter_seven = _chapter_seven(chapter_six.quests[-1].slug)
    chapter_eight = _chapter_eight(chapter_seven.quests[-1].slug)
    chapter_nine = _chapter_nine(chapter_eight.quests[-1].slug)
    chapter_ten = _chapter_ten(chapter_nine.quests[-1].slug)
    chapter_eleven = _chapter_eleven(chapter_ten.quests[-1].slug)
    return [
        chapter_six,
        chapter_seven,
        chapter_eight,
        chapter_nine,
        chapter_ten,
        chapter_eleven,
    ]
