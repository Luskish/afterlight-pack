from __future__ import annotations

from dataclasses import dataclass

from .builder import ChapterSpec, GroupSpec, QuestSpec, RewardSpec, SnbtLong, TaskSpec
from .story_cohesion import apply_manual_return_links


FIELD_MANUALS = GroupSpec(
    "certifications",
    "Field Manuals & Certifications",
    "4A20F33642175B95",
)


@dataclass(frozen=True)
class FieldManualAcquisition:
    quest_slug: str
    method: str


@dataclass(frozen=True)
class _Task:
    slug: str
    task_type: str
    target: str = ""
    title: str = ""
    components: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class _Node:
    slug: str
    title: str
    subtitle: str
    description: str
    tasks: tuple[_Task, ...]
    acquisition: str


@dataclass(frozen=True)
class _Manual:
    slug: str
    title: str
    icon: str
    chapter_id: str
    root_id: str
    nodes: tuple[_Node, ...]


def _item(
    slug: str,
    item_id: str,
    *,
    components: tuple[tuple[str, str], ...] = (),
) -> _Task:
    return _Task(slug, "item", item_id, components=components)


def _advancement(slug: str, advancement_id: str) -> _Task:
    return _Task(slug, "advancement", advancement_id)


def _checkmark(slug: str, title: str) -> _Task:
    return _Task(slug, "checkmark", title=title)


_MANUALS = (
    _Manual(
        "manuals/immersive-engineering",
        "Field Manual: Heavy Industry",
        "immersiveengineering:manual",
        "150C6F996983394C",
        "3E77A16CB0C0AD11",
        (
            _Node(
                "manuals/immersive-engineering/recover-field-manual",
                "Recover the Heavy Industry Manual",
                "Archive shard: soot, copper, patience.",
                "ECHO recovered a field copy, incomplete but internally consistent. Open the Engineer's Manual before JEI; use the Hammer only where the Manual shows a formed structure.",
                (
                    _item("manuals/immersive-engineering/recover-field-manual/task/manual", "immersiveengineering:manual"),
                    _item("manuals/immersive-engineering/recover-field-manual/task/hammer", "immersiveengineering:hammer"),
                ),
                "recipe",
            ),
            _Node(
                "manuals/immersive-engineering/coke-oven",
                "Form the Coke Oven",
                "Heat first. Hurry later.",
                "The blueprint is older than the walls around it. Form the complete oven with the Engineer's Hammer; ECHO accepts the multiblock record, not a pile of bricks.",
                (_advancement("manuals/immersive-engineering/coke-oven/task/advancement", "immersiveengineering:main/mb_cokeoven"),),
                "advancement",
            ),
            _Node(
                "manuals/immersive-engineering/creosote-and-treated-wood",
                "Capture Creosote",
                "Byproducts require custody.",
                "Coke yields heat and creosote. Contain the fluid, then bind it into treated wood for durable low-voltage work.",
                (
                    _item("manuals/immersive-engineering/creosote-and-treated-wood/task/creosote-bucket", "immersiveengineering:creosote_bucket"),
                    _item("manuals/immersive-engineering/creosote-and-treated-wood/task/treated-wood", "immersiveengineering:treated_wood_horizontal"),
                ),
                "process",
            ),
            _Node(
                "manuals/immersive-engineering/lv-capacitor",
                "Buffer Low Voltage",
                "Current without reserve becomes interruption.",
                "Install an LV Capacitor before the first long run. Stored energy keeps brief demand spikes from resembling machine failure.",
                (_item("manuals/immersive-engineering/lv-capacitor/task/item", "immersiveengineering:capacitor_lv"),),
                "recipe",
            ),
            _Node(
                "manuals/immersive-engineering/copper-wire-and-connectors",
                "Lay Copper Connections",
                "The line is a system, not loose wire.",
                "Prepare copper wire coils and LV Connectors. Keep endpoints deliberate and leave no exposed connection where a player can cross it.",
                (
                    _item("manuals/immersive-engineering/copper-wire-and-connectors/task/wire-coil", "immersiveengineering:wirecoil_copper"),
                    _item("manuals/immersive-engineering/copper-wire-and-connectors/task/connector", "immersiveengineering:connector_lv"),
                ),
                "recipe",
            ),
            _Node(
                "manuals/immersive-engineering/engineers-workbench",
                "Recover the Workbench",
                "Blueprints need a controlled surface.",
                "The Engineer's Workbench restores specialized assembly. Consult its Manual page before committing scarce components.",
                (_item("manuals/immersive-engineering/engineers-workbench/task/item", "immersiveengineering:workbench"),),
                "recipe",
            ),
            _Node(
                "manuals/immersive-engineering/blast-furnace",
                "Form the Blast Furnace",
                "Steel begins with containment.",
                "Form the complete Blast Furnace with the Engineer's Hammer. ECHO accepts the multiblock record, not loose blast bricks.",
                (_advancement("manuals/immersive-engineering/blast-furnace/task/advancement", "immersiveengineering:main/mb_blastfurnace"),),
                "advancement",
            ),
            _Node(
                "manuals/immersive-engineering/field-test",
                "Field Test: Insulated Current",
                "One source. One buffer. One load.",
                "Assemble a low-voltage run and inspect every endpoint. The test is safe only when the load receives power and no live end remains exposed.",
                (_checkmark("manuals/immersive-engineering/field-test/task/checkmark", "Verify one LV source, buffer, connector pair, and load operate with no exposed live ends."),),
                "manual_check",
            ),
        ),
    ),
    _Manual(
        "manuals/mekanism",
        "Field Manual: Matter Systems",
        "mekanism:configurator",
        "4DE10FFCDEEF9892",
        "6B09A1A11CD08E68",
        (
            _Node(
                "manuals/mekanism/configure-the-first-machine",
                "Configure the First Machine",
                "Archive note: every face has a job.",
                "ECHO recovered sided-machine telemetry. Open JEI for each recipe, then use the Configurator to inspect input, output, energy, and eject settings before connecting a line.",
                (_item("manuals/mekanism/configure-the-first-machine/task/item", "mekanism:configurator"),),
                "recipe",
            ),
            _Node(
                "manuals/mekanism/heat-generator",
                "Establish Heat Generation",
                "A small source is enough to learn from.",
                "Acquire a Heat Generator. Possession confirms the component only; the field test will verify that the connected line actually receives power.",
                (_item("manuals/mekanism/heat-generator/task/item", "mekanismgenerators:heat_generator"),),
                "recipe",
            ),
            _Node(
                "manuals/mekanism/steel-casing",
                "Build the Steel Frame",
                "Precision starts at the casing.",
                "A Steel Casing is the common frame beneath the first machine family. Confirm its recipe in JEI before expanding.",
                (_item("manuals/mekanism/steel-casing/task/item", "mekanism:steel_casing"),),
                "recipe",
            ),
            _Node(
                "manuals/mekanism/metallurgic-infuser",
                "Prepare the Infuser",
                "Matter changes when the side channels agree.",
                "Acquire a Metallurgic Infuser. Inventory proves the machine exists; configured infusion and output remain part of the field test.",
                (_item("manuals/mekanism/metallurgic-infuser/task/item", "mekanism:metallurgic_infuser"),),
                "recipe",
            ),
            _Node(
                "manuals/mekanism/enrichment-chamber",
                "Add Enrichment",
                "One ore becomes a measured process.",
                "The Enrichment Chamber is the first clean step toward ore doubling. Reserve distinct faces for input, output, and power.",
                (_item("manuals/mekanism/enrichment-chamber/task/item", "mekanism:enrichment_chamber"),),
                "recipe",
            ),
            _Node(
                "manuals/mekanism/basic-universal-cable",
                "Carry Universal Power",
                "Cables remove distance, not ambiguity.",
                "Use Basic Universal Cable for the first FE run. Read connection states before assuming a machine is starved.",
                (_item("manuals/mekanism/basic-universal-cable/task/item", "mekanism:basic_universal_cable"),),
                "recipe",
            ),
            _Node(
                "manuals/mekanism/basic-energy-cube",
                "Buffer the Line",
                "A cube separates supply from demand.",
                "Acquire a Basic Energy Cube. Possession is not a charge test; the final line must show power entering and leaving the buffer.",
                (_item("manuals/mekanism/basic-energy-cube/task/item", "mekanism:basic_energy_cube"),),
                "recipe",
            ),
            _Node(
                "manuals/mekanism/energized-smelter",
                "Close the Smelting Loop",
                "Dust should return as usable metal.",
                "Add an Energized Smelter after enrichment. The next problem is no longer processing, but reliable side configuration.",
                (_item("manuals/mekanism/energized-smelter/task/item", "mekanism:energized_smelter"),),
                "recipe",
            ),
            _Node(
                "manuals/mekanism/field-test",
                "Field Test: Configured Doubling",
                "Inputs enter once. Outputs leave once.",
                "Connect the first ore-doubling line. ECHO requires visible input, output, and eject settings, plus power moving through the buffer.",
                (_checkmark("manuals/mekanism/field-test/task/checkmark", "Verify configured input, output, and auto-eject sides on a powered ore-doubling line with an Energy Cube buffer."),),
                "manual_check",
            ),
        ),
    ),
    _Manual(
        "manuals/applied-energistics-2",
        "Field Manual: Storage Lattice",
        "ae2:guide",
        "01749E1554DFF98B",
        "70380821D8D0339D",
        (
            _Node(
                "manuals/applied-energistics-2/read-the-lattice",
                "Read the Lattice",
                "Archive shard: names before networks.",
                "ECHO recovered a GuideME index with damaged annotations. Open the AE2 Guide first, then use JEI to trace the Guide and Meteorite Compass acquisition paths.",
                (
                    _item("manuals/applied-energistics-2/read-the-lattice/task/guide", "ae2:guide"),
                    _item("manuals/applied-energistics-2/read-the-lattice/task/compass", "ae2:meteorite_compass"),
                ),
                "process",
            ),
            _Node(
                "manuals/applied-energistics-2/charger",
                "Charge Before Addressing",
                "Certus changes under power.",
                "Acquire the Charger. The task confirms the block only; the field test will prove a powered network.",
                (_item("manuals/applied-energistics-2/charger/task/item", "ae2:charger"),),
                "recipe",
            ),
            _Node(
                "manuals/applied-energistics-2/fluix",
                "Make Fluix",
                "The network needs a conductive language.",
                "Follow the Guide's transformation entry and obtain a Fluix Crystal. Treat the process as evidence, not a recipe guess.",
                (_item("manuals/applied-energistics-2/fluix/task/item", "ae2:fluix_crystal"),),
                "process",
            ),
            _Node(
                "manuals/applied-energistics-2/meteorite-presses",
                "Recover the Four Presses",
                "Meteorites kept the processor alphabet.",
                "The Compass points toward native meteorite sites. Recover all four presses; a single press leaves the archive grammar incomplete.",
                (
                    _item("manuals/applied-energistics-2/meteorite-presses/task/calculation", "ae2:calculation_processor_press"),
                    _item("manuals/applied-energistics-2/meteorite-presses/task/engineering", "ae2:engineering_processor_press"),
                    _item("manuals/applied-energistics-2/meteorite-presses/task/logic", "ae2:logic_processor_press"),
                    _item("manuals/applied-energistics-2/meteorite-presses/task/silicon", "ae2:silicon_press"),
                ),
                "worldgen",
            ),
            _Node(
                "manuals/applied-energistics-2/inscriber",
                "Imprint Processors",
                "The presses need a controlled stroke.",
                "Acquire an Inscriber and review each processor chain in the Guide. Processor production comes before storage scale.",
                (_item("manuals/applied-energistics-2/inscriber/task/item", "ae2:inscriber"),),
                "recipe",
            ),
            _Node(
                "manuals/applied-energistics-2/energy-acceptor-and-cable",
                "Power the First Channel",
                "A network begins where power becomes addressable.",
                "Prepare an Energy Acceptor and Fluix Glass Cable. Possession proves parts, not a powered channel; the terminal test closes that gap.",
                (
                    _item("manuals/applied-energistics-2/energy-acceptor-and-cable/task/energy-acceptor", "ae2:energy_acceptor"),
                    _item("manuals/applied-energistics-2/energy-acceptor-and-cable/task/fluix-glass-cable", "ae2:fluix_glass_cable"),
                ),
                "recipe",
            ),
            _Node(
                "manuals/applied-energistics-2/drive-and-cell",
                "Give the Lattice Memory",
                "Addressable space still needs a vessel.",
                "Pair a Drive with a 1K Item Storage Cell. Begin small enough that every channel and stored item remains visible.",
                (
                    _item("manuals/applied-energistics-2/drive-and-cell/task/drive", "ae2:drive"),
                    _item("manuals/applied-energistics-2/drive-and-cell/task/storage-cell", "ae2:item_storage_cell_1k"),
                ),
                "recipe",
            ),
            _Node(
                "manuals/applied-energistics-2/crafting-terminal",
                "Open the Crafting Terminal",
                "Storage becomes an interface.",
                "Acquire a Crafting Terminal. The item task does not claim successful use; insertion and retrieval belong to the field test.",
                (_item("manuals/applied-energistics-2/crafting-terminal/task/item", "ae2:crafting_terminal"),),
                "recipe",
            ),
            _Node(
                "manuals/applied-energistics-2/first-pattern",
                "Encode the First Pattern",
                "Storage remembers. Patterns intend.",
                "Acquire a blank Crafting Pattern and Pattern Encoding Terminal. The final test will prove that one encoded request reaches a provider.",
                (
                    _item("manuals/applied-energistics-2/first-pattern/task/crafting-pattern", "ae2:blank_pattern"),
                    _item("manuals/applied-energistics-2/first-pattern/task/pattern-terminal", "ae2:pattern_encoding_terminal"),
                ),
                "recipe",
            ),
            _Node(
                "manuals/applied-energistics-2/field-test",
                "Field Test: Addressed Storage",
                "Insert. Retrieve. Request.",
                "Power the terminal, move one item into and out of storage, then send one encoded pattern to a provider. ECHO accepts observable delivery, not inventory alone.",
                (_checkmark("manuals/applied-energistics-2/field-test/task/checkmark", "Verify a powered terminal inserts and retrieves one item, then sends one encoded pattern to a provider."),),
                "manual_check",
            ),
        ),
    ),
    _Manual(
        "manuals/create",
        "Field Manual: Kinetics",
        "create:wrench",
        "4690C88367D47FF3",
        "686943DC0749D6E0",
        (
            _Node(
                "manuals/create/ponder-kinetics",
                "Wrench, Goggles, and Ponder",
                "Motion is visible. Read it before touching it.",
                "ECHO recovered a visual training reel, not a command. Open Ponder on a Shaft and inspect rotation relay, then use JEI for the Wrench and Goggles before building.",
                (_checkmark("manuals/create/ponder-kinetics/task/checkmark", "Open Ponder on a Shaft and inspect the rotation relay scene before building."),),
                "manual_check",
            ),
            _Node(
                "manuals/create/water-wheel",
                "Establish Rotation",
                "Flow becomes rotational evidence.",
                "Form a Water Wheel installation and let Create's milestone record it. The final test will prove useful output under load.",
                (_advancement("manuals/create/water-wheel/task/advancement", "create:water_wheel"),),
                "advancement",
            ),
            _Node(
                "manuals/create/shafts-and-cogs",
                "Relay Motion",
                "Direction and speed travel through geometry.",
                "Acquire Shafts and Cogwheels, then review their Ponder scenes. ECHO needs a readable transmission before adding work.",
                (
                    _item("manuals/create/shafts-and-cogs/task/shaft", "create:shaft"),
                    _item("manuals/create/shafts-and-cogs/task/cogwheel", "create:cogwheel"),
                ),
                "recipe",
            ),
            _Node(
                "manuals/create/millstone",
                "Add the Millstone",
                "Rotation becomes processing.",
                "Acquire a Millstone and inspect its Ponder scene. Place the first process where its input and output remain visible.",
                (_item("manuals/create/millstone/task/item", "create:millstone"),),
                "recipe",
            ),
            _Node(
                "manuals/create/mechanical-press",
                "Apply Mechanical Force",
                "A repeated stroke should remain controlled.",
                "Build the Mechanical Press and complete its native milestone. Keep the working face clear while observing the first cycle.",
                (_advancement("manuals/create/mechanical-press/task/advancement", "create:mechanical_press"),),
                "advancement",
            ),
            _Node(
                "manuals/create/basin-and-mixer",
                "Mix in a Basin",
                "Some recipes require a chamber and a speed.",
                "Add a Basin and Mechanical Mixer, then complete the native mixer milestone. Confirm available speed before diagnosing the recipe.",
                (_advancement("manuals/create/basin-and-mixer/task/advancement", "create:mechanical_mixer"),),
                "advancement",
            ),
            _Node(
                "manuals/create/belts-and-funnels",
                "Route the Output",
                "Processing without transport becomes a queue.",
                "Acquire Belt Connectors and an Andesite Funnel. Use Ponder to inspect direction, filtering, and insertion before joining machines.",
                (
                    _item("manuals/create/belts-and-funnels/task/belt-connector", "create:belt_connector"),
                    _item("manuals/create/belts-and-funnels/task/andesite-funnel", "create:andesite_funnel"),
                ),
                "recipe",
            ),
            _Node(
                "manuals/create/blaze-and-brass",
                "Prepare Heated Mixing",
                "Heat changes the permitted process.",
                "Acquire a Blaze Burner and Brass Ingot after reviewing Ponder heating. These items prove readiness, not a completed heating cycle.",
                (
                    _item("manuals/create/blaze-and-brass/task/blaze-burner", "create:blaze_burner"),
                    _item("manuals/create/blaze-and-brass/task/brass-ingot", "create:brass_ingot"),
                ),
                "process",
            ),
            _Node(
                "manuals/create/precision-mechanism",
                "Recover Sequenced Assembly",
                "One component, several controlled passes.",
                "Acquire a Precision Mechanism and inspect its JEI sequence. Possession proves the component; the field test proves an assembled cycle.",
                (_item("manuals/create/precision-mechanism/task/item", "create:precision_mechanism"),),
                "process",
            ),
            _Node(
                "manuals/create/field-test",
                "Field Test: Controlled Motion",
                "Power, process, route, measure.",
                "Run one powered line below its stress limit, route one processed item to its destination, and complete one visible sequenced-assembly cycle.",
                (_checkmark("manuals/create/field-test/task/checkmark", "Verify one powered line processes and routes an item below stress, then completes one sequenced-assembly cycle."),),
                "manual_check",
            ),
        ),
    ),
    _Manual(
        "manuals/pneumaticcraft",
        "Field Manual: Pressure",
        "pneumaticcraft:manual",
        "0A510C4BD2A3818B",
        "084209B68927F9FC",
        (
            _Node(
                "manuals/pneumaticcraft/read-pressure-safely",
                "Read Pressure Safely",
                "Archive warning: pressure stores consequences.",
                "ECHO recovered a PneumaticCraft field copy with the failure margins intact. Open the PNC Manual before JEI, and read every pressure and heat limit before assembly.",
                (_item("manuals/pneumaticcraft/read-pressure-safely/task/item", "patchouli:guide_book", components=(("patchouli:book", "pneumaticcraft:book"),)),),
                "recipe",
            ),
            _Node(
                "manuals/pneumaticcraft/compressed-iron",
                "Prepare Compressed Iron",
                "The pressure system begins in its alloy.",
                "Obtain Compressed Iron through the current native process. Use the exact registry item; older archive names are not valid evidence.",
                (_item("manuals/pneumaticcraft/compressed-iron/task/item", "pneumaticcraft:ingot_iron_compressed"),),
                "process",
            ),
            _Node(
                "manuals/pneumaticcraft/air-compressor",
                "Establish Compression",
                "Pressure begins low and observed.",
                "Acquire an Air Compressor. Inventory proves the machine, not safe operation; the field test will verify pressure and cooling clearance.",
                (_item("manuals/pneumaticcraft/air-compressor/task/item", "pneumaticcraft:air_compressor"),),
                "recipe",
            ),
            _Node(
                "manuals/pneumaticcraft/pressure-tube-and-gauge",
                "Measure the First Line",
                "A tube without a gauge is an assumption.",
                "Acquire a Pressure Tube and Pressure Gauge. Place measurement where it can be read before expanding the network.",
                (
                    _item("manuals/pneumaticcraft/pressure-tube-and-gauge/task/pressure-tube", "pneumaticcraft:pressure_tube"),
                    _item("manuals/pneumaticcraft/pressure-tube-and-gauge/task/pressure-gauge", "pneumaticcraft:pressure_gauge"),
                ),
                "recipe",
            ),
            _Node(
                "manuals/pneumaticcraft/safety-upgrade",
                "Install a Safety Module",
                "Limits should act before alarms become debris.",
                "Acquire the exact Safety Tube Module and review its Manual entry. Keep the first pressure network below every component limit.",
                (_item("manuals/pneumaticcraft/safety-upgrade/task/item", "pneumaticcraft:safety_tube_module"),),
                "recipe",
            ),
            _Node(
                "manuals/pneumaticcraft/pressure-chamber",
                "Seal the Pressure Chamber",
                "A chamber is formed only when its interface agrees.",
                "Build the native multiblock until the chamber interface opens. Loose walls are not a chamber, and ECHO will not describe them as one.",
                (_advancement("manuals/pneumaticcraft/pressure-chamber/task/advancement", "pneumaticcraft:pressure_chamber"),),
                "advancement",
            ),
            _Node(
                "manuals/pneumaticcraft/plastic",
                "Recover Plastic",
                "The chamber now has a useful output.",
                "Obtain PneumaticCraft Plastic through its current process. Possession proves the material, not chamber pressure discipline.",
                (_item("manuals/pneumaticcraft/plastic/task/item", "pneumaticcraft:plastic"),),
                "process",
            ),
            _Node(
                "manuals/pneumaticcraft/etching-acid",
                "Contain Etching Acid",
                "Circuit work begins with controlled corrosion.",
                "Acquire one sealed Etching Acid bucket. Keep the fluid inside its intended vessel and follow the Manual's handling sequence.",
                (_item("manuals/pneumaticcraft/etching-acid/task/item", "pneumaticcraft:etching_acid_bucket"),),
                "process",
            ),
            _Node(
                "manuals/pneumaticcraft/printed-circuit-board",
                "Complete the Circuit Board",
                "Pressure becomes programmable through careful layers.",
                "Obtain a Printed Circuit Board through the native sequence. Inventory confirms the board only; automation comes later.",
                (_item("manuals/pneumaticcraft/printed-circuit-board/task/item", "pneumaticcraft:printed_circuit_board"),),
                "process",
            ),
            _Node(
                "manuals/pneumaticcraft/programmer",
                "Prepare the Programmer",
                "A route should exist before a drone does.",
                "Acquire the Programmer and read the Manual's area and logistics entries. Define endpoints before deployment.",
                (_item("manuals/pneumaticcraft/programmer/task/item", "pneumaticcraft:programmer"),),
                "recipe",
            ),
            _Node(
                "manuals/pneumaticcraft/bounded-drone",
                "Deploy a Bounded Drone",
                "Mobility requires borders.",
                "Deploy one logistics drone only after its route has named endpoints. The native milestone records deployment; the field test confirms the route remains bounded.",
                (_advancement("manuals/pneumaticcraft/bounded-drone/task/advancement", "pneumaticcraft:logistics_drone"),),
                "advancement",
            ),
            _Node(
                "manuals/pneumaticcraft/field-test",
                "Field Test: Bounded Pressure",
                "Measure, cool, limit, observe.",
                "Hold the network inside its safe pressure range, preserve compressor cooling clearance, and watch one drone complete only its stated route.",
                (_checkmark("manuals/pneumaticcraft/field-test/task/checkmark", "Verify safe operating pressure, compressor cooling clearance, and one drone route limited to its stated endpoints."),),
                "manual_check",
            ),
        ),
    ),
    _Manual(
        "manuals/power-networks",
        "Field Manual: Power Networks",
        "powah:book",
        "67F13F819570ED52",
        "5334545A948815F6",
        (
            _Node(
                "manuals/power-networks/define-the-grid",
                "Define the Grid",
                "Archive rule: unnamed power becomes shared failure.",
                "ECHO recovered a grid ledger with ownership fields still readable. Open the Powah book first, then use JEI for Ender IO and Flux Networks before joining local and remote loads.",
                (_item("manuals/power-networks/define-the-grid/task/item", "powah:book"),),
                "recipe",
            ),
            _Node(
                "manuals/power-networks/starter-generation",
                "Start Local Generation",
                "A first source should be legible, not large.",
                "Acquire a Starter Thermo Generator and review its heat-source rules in the Powah book. Begin with a source you can inspect directly.",
                (_item("manuals/power-networks/starter-generation/task/item", "powah:thermo_generator_starter"),),
                "recipe",
            ),
            _Node(
                "manuals/power-networks/energy-cable",
                "Carry the First Current",
                "Transport comes before scale.",
                "Acquire Basic Energy Cable and keep the first run short. ECHO needs visible source and load behavior before distance is introduced.",
                (_item("manuals/power-networks/energy-cable/task/item", "powah:energy_cable_basic"),),
                "recipe",
            ),
            _Node(
                "manuals/power-networks/energy-cell",
                "Add an Energy Cell",
                "Reserve makes interruptions visible.",
                "Acquire a Basic Energy Cell and place it between generation and load. Buffer direction matters as much as capacity.",
                (_item("manuals/power-networks/energy-cell/task/item", "powah:energy_cell_basic"),),
                "recipe",
            ),
            _Node(
                "manuals/power-networks/energizing-orb",
                "Prepare the Energizing Orb",
                "The grid can now manufacture its next tier.",
                "Acquire an Energizing Orb and read its binding and power requirements. Keep the first recipe local to the buffer.",
                (_item("manuals/power-networks/energizing-orb/task/item", "powah:energizing_orb"),),
                "recipe",
            ),
            _Node(
                "manuals/power-networks/thermo-generator",
                "Upgrade Thermo Generation",
                "Scale one known source before adding another kind.",
                "Acquire a Basic Thermo Generator. Compare its book entry to the Starter tier before assigning it a critical load.",
                (_item("manuals/power-networks/thermo-generator/task/item", "powah:thermo_generator_basic"),),
                "recipe",
            ),
            _Node(
                "manuals/power-networks/basic-reactor",
                "Review the Basic Reactor",
                "Dense generation requires a written operating state.",
                "Acquire the Basic Reactor, then read its fuel and cooling pages before connection. Possession does not authorize operation.",
                (_item("manuals/power-networks/basic-reactor/task/item", "powah:reactor_basic"),),
                "recipe",
            ),
            _Node(
                "manuals/power-networks/enderio-buffer-and-conduit",
                "Add a Local Conduit Buffer",
                "Different networks need a deliberate boundary.",
                "Acquire a Basic Capacitor Bank and the component-bearing Energy Conduit. The generic conduit item without its energy component is not equivalent.",
                (
                    _item("manuals/power-networks/enderio-buffer-and-conduit/task/capacitor-bank", "enderio:basic_capacitor_bank"),
                    _item("manuals/power-networks/enderio-buffer-and-conduit/task/energy-conduit", "enderio:conduit", components=(("enderio:conduit", "enderio:energy"),)),
                ),
                "recipe",
            ),
            _Node(
                "manuals/power-networks/flux-plug",
                "Publish the Source",
                "Wireless transfer begins at a named input.",
                "Acquire a Flux Plug and attach it only after the source grid has a buffer. Record the network name before adding outputs.",
                (_item("manuals/power-networks/flux-plug/task/item", "fluxnetworks:flux_plug"),),
                "recipe",
            ),
            _Node(
                "manuals/power-networks/flux-point",
                "Receive at a Remote Load",
                "Distance should not erase ownership.",
                "Acquire a Flux Point and bind one remote load to the named network. Keep one local load connected for comparison.",
                (_item("manuals/power-networks/flux-point/task/item", "fluxnetworks:flux_point"),),
                "recipe",
            ),
            _Node(
                "manuals/power-networks/flux-controller",
                "Control the Wireless Grid",
                "Access is part of the circuit.",
                "Acquire a Flux Controller and review ownership before increasing transfer limits. A network without a named owner is unfinished.",
                (_item("manuals/power-networks/flux-controller/task/item", "fluxnetworks:flux_controller"),),
                "recipe",
            ),
            _Node(
                "manuals/power-networks/reserve-field-test",
                "Field Test: Named Reserve",
                "Source, buffer, local load, remote load, owner.",
                "Name the grid, verify stored reserve, and observe one local and one remote load. The test is complete only when ownership is visible.",
                (_checkmark("manuals/power-networks/reserve-field-test/task/checkmark", "Name the grid, then verify generation, a buffer, one local load, one remote load, and visible network ownership."),),
                "manual_check",
            ),
        ),
    ),
    _Manual(
        "manuals/oritech",
        "Field Manual: Frontier Machines",
        "oritech:wrench",
        "67C126F7B1338CB1",
        "6CC0CCE16F9FB5BE",
        (
            _Node(
                "manuals/oritech/frontier-orientation",
                "Frontier Orientation",
                "Archive shard: unfamiliar tolerances, familiar caution.",
                "ECHO recovered machine labels without their workshop. Open JEI from the Oritech Wrench and trace each recipe from tier one before placing a line.",
                (_item("manuals/oritech/frontier-orientation/task/item", "oritech:wrench"),),
                "recipe",
            ),
            _Node(
                "manuals/oritech/basic-generator",
                "Establish Basic Generation",
                "The first machine needs a known source.",
                "Acquire the Basic Generator and keep its first load local. Power entry must be observable before processing expands.",
                (_item("manuals/oritech/basic-generator/task/item", "oritech:basic_generator_block"),),
                "recipe",
            ),
            _Node(
                "manuals/oritech/machine-core",
                "Recover the Tier-One Core",
                "Every frontier machine begins at its common center.",
                "Acquire the Tier-One Machine Core. Use JEI to read which machines inherit this frame before spending it.",
                (_item("manuals/oritech/machine-core/task/item", "oritech:machine_core_1"),),
                "recipe",
            ),
            _Node(
                "manuals/oritech/pulverizer",
                "Begin with Pulverizing",
                "Reduce the input before separating it.",
                "Acquire a Pulverizer and place it first in the processing order. Keep the initial input and output visible.",
                (_item("manuals/oritech/pulverizer/task/item", "oritech:pulverizer_block"),),
                "recipe",
            ),
            _Node(
                "manuals/oritech/centrifuge",
                "Separate the Fraction",
                "The second machine answers the first output.",
                "Acquire a Centrifuge and review which pulverized products it accepts. Order matters; guessing consumes time, not evidence.",
                (_item("manuals/oritech/centrifuge/task/item", "oritech:centrifuge_block"),),
                "recipe",
            ),
            _Node(
                "manuals/oritech/assembler",
                "Automate Assembly",
                "Processed parts need a repeatable join.",
                "Acquire an Assembler and inspect one complete JEI input set. Feed it only after the upstream outputs are stable.",
                (_item("manuals/oritech/assembler/task/item", "oritech:assembler_block"),),
                "recipe",
            ),
            _Node(
                "manuals/oritech/foundry",
                "Add the Foundry",
                "Heat belongs after preparation, not before it.",
                "Acquire a Foundry and review its accepted inputs in JEI. Keep the heat stage isolated from the first material test.",
                (_item("manuals/oritech/foundry/task/item", "oritech:foundry_block"),),
                "recipe",
            ),
            _Node(
                "manuals/oritech/laser-arm",
                "Position the Laser Arm",
                "Remote work still needs a bounded target.",
                "Acquire a Laser Arm and inspect its valid targets before power is applied. Orientation is part of the machine contract.",
                (_item("manuals/oritech/laser-arm/task/item", "oritech:laser_arm_block"),),
                "recipe",
            ),
            _Node(
                "manuals/oritech/reactor-orientation",
                "Review Reactor Orientation",
                "Recognition precedes operation.",
                "Acquire the Reactor Controller and inspect its JEI relationships. Leave the reactor unassembled and unlit; this node certifies orientation only.",
                (_item("manuals/oritech/reactor-orientation/task/item", "oritech:reactor_controller"),),
                "recipe",
            ),
            _Node(
                "manuals/oritech/field-test",
                "Field Test: Ordered Processing",
                "One input. Ordered machines. One collected output.",
                "Run one safe input through the planned processing order and collect the final output. Reactor ignition is neither required nor accepted.",
                (_checkmark("manuals/oritech/field-test/task/checkmark", "Run one safe input through the ordered Oritech processing line and collect its final output without reactor ignition."),),
                "manual_check",
            ),
        ),
    ),
    _Manual(
        "manuals/nuclear-systems",
        "Field Manual: Nuclear Safety",
        "mekanism:geiger_counter",
        "0B7C7859EBD6EFF3",
        "4EEAB6F41DB426E7",
        (
            _Node(
                "manuals/nuclear-systems/safety-before-output",
                "Safety Before Output",
                "Archive priority: survive the system you build.",
                "ECHO recovered the safety ledger before the production ledger. Open JEI from each Hazmat piece, assemble the complete set, and do not approach live radiation without measurement and containment.",
                (
                    _item("manuals/nuclear-systems/safety-before-output/task/mask", "mekanism:hazmat_mask"),
                    _item("manuals/nuclear-systems/safety-before-output/task/gown", "mekanism:hazmat_gown"),
                    _item("manuals/nuclear-systems/safety-before-output/task/pants", "mekanism:hazmat_pants"),
                    _item("manuals/nuclear-systems/safety-before-output/task/boots", "mekanism:hazmat_boots"),
                ),
                "advancement",
            ),
            _Node(
                "manuals/nuclear-systems/dosimeter-and-geiger-counter",
                "Measure Dose and Field",
                "Two instruments answer different questions.",
                "Acquire a Dosimeter and Geiger Counter. Read personal exposure and environmental radiation separately before planning any boundary.",
                (
                    _item("manuals/nuclear-systems/dosimeter-and-geiger-counter/task/dosimeter", "mekanism:dosimeter"),
                    _item("manuals/nuclear-systems/dosimeter-and-geiger-counter/task/geiger-counter", "mekanism:geiger_counter"),
                ),
                "recipe",
            ),
            _Node(
                "manuals/nuclear-systems/electrolytic-separator",
                "Separate the First Gas",
                "Chemistry starts upstream of the reactor.",
                "Acquire an Electrolytic Separator and inspect its gas outputs in JEI. Keep the first review disconnected from any fuel chain.",
                (_item("manuals/nuclear-systems/electrolytic-separator/task/item", "mekanism:electrolytic_separator"),),
                "recipe",
            ),
            _Node(
                "manuals/nuclear-systems/chemical-chain-orientation",
                "Trace the Chemical Chain",
                "Read the sequence before producing any part of it.",
                "Use JEI to trace water separation, uranium processing, fissile fuel, waste, steam, and recovered coolant. This is orientation only; produce nothing radioactive for the check.",
                (_checkmark("manuals/nuclear-systems/chemical-chain-orientation/task/checkmark", "In JEI, trace water to gases, uranium processing, fissile fuel, waste, steam, and recovered coolant without producing radioactive material."),),
                "manual_check",
            ),
            _Node(
                "manuals/nuclear-systems/isotopic-centrifuge",
                "Prepare Isotope Separation",
                "Precision belongs before fuel.",
                "Acquire an Isotopic Centrifuge and inspect its JEI inputs and outputs. Do not connect it to a live fuel line for this manual.",
                (_item("manuals/nuclear-systems/isotopic-centrifuge/task/item", "mekanism:isotopic_centrifuge"),),
                "recipe",
            ),
            _Node(
                "manuals/nuclear-systems/fission-fuel-assemblies",
                "Inspect Fuel Assemblies",
                "Hardware can be verified without fuel.",
                "Acquire one Fission Fuel Assembly as dry hardware. Do not load fuel, form an active core, or ignite a reactor for this node.",
                (_item("manuals/nuclear-systems/fission-fuel-assemblies/task/item", "mekanismgenerators:fission_fuel_assembly"),),
                "recipe",
            ),
            _Node(
                "manuals/nuclear-systems/reactor-logic-adapter",
                "Prepare Automatic Shutdown",
                "A reactor needs an independent stop condition.",
                "Acquire a Fission Reactor Logic Adapter and review shutdown behavior in JEI and native tooltips. Keep the reactor unlit while configuring the safety path.",
                (_item("manuals/nuclear-systems/reactor-logic-adapter/task/item", "mekanismgenerators:fission_reactor_logic_adapter"),),
                "recipe",
            ),
            _Node(
                "manuals/nuclear-systems/waste-barrels",
                "Reserve Waste Capacity",
                "Containment is sized before production.",
                "Acquire a Radioactive Waste Barrel as containment hardware. The barrel is never a reward, and this node requires no radioactive contents.",
                (_item("manuals/nuclear-systems/waste-barrels/task/item", "mekanism:radioactive_waste_barrel"),),
                "recipe",
            ),
            _Node(
                "manuals/nuclear-systems/steam-and-coolant-recovery",
                "Recover Steam and Coolant",
                "Heat removal needs an exit and a return.",
                "Acquire a Turbine Vent and Saturating Condenser. The pair represents steam exhaust and coolant recovery; no reactor ignition is required to inspect the recovery path.",
                (
                    _item("manuals/nuclear-systems/steam-and-coolant-recovery/task/turbine-vent", "mekanismgenerators:turbine_vent"),
                    _item("manuals/nuclear-systems/steam-and-coolant-recovery/task/saturating-condenser", "mekanismgenerators:saturating_condenser"),
                ),
                "recipe",
            ),
            _Node(
                "manuals/nuclear-systems/contained-field-test",
                "Field Test: Containment Before Output",
                "Protection, shutdown, capacity, recovery, exit.",
                "With Hazmat equipped and the reactor unlit, inspect shutdown logic, spare waste capacity, the steam-to-coolant recovery path, and a clear evacuation route.",
                (_checkmark("manuals/nuclear-systems/contained-field-test/task/checkmark", "With Hazmat equipped and the reactor unlit, verify shutdown logic, spare waste capacity, steam recovery, coolant return, and a clear evacuation route."),),
                "manual_check",
            ),
        ),
    ),
)


FIELD_MANUAL_ACQUISITIONS = tuple(
    FieldManualAcquisition(node.slug, node.acquisition)
    for manual in _MANUALS
    for node in manual.nodes
)


def _build_task(task: _Task) -> TaskSpec:
    if task.task_type == "item":
        stack: dict[str, object] = {"count": 1, "id": task.target}
        data: dict[str, object] = {
            "item": stack,
            "count": SnbtLong(1),
            "consume_items": False,
        }
        if task.components:
            stack["components"] = dict(task.components)
            data["match_components"] = "fuzzy"
        return TaskSpec(task.slug, "item", data)
    if task.task_type == "advancement":
        return TaskSpec(
            task.slug,
            "advancement",
            {"advancement": task.target, "criterion": ""},
        )
    return TaskSpec(task.slug, "checkmark", title=task.title)


def _rewards(quest_slug: str, finale: bool) -> tuple[RewardSpec, ...]:
    chit_count = 3 if finale else 1
    rewards = [
        RewardSpec(
            f"{quest_slug}/reward/chits",
            "item",
            {
                "item": {"count": chit_count, "id": "kubejs:requisition_chit"},
                "count": chit_count,
            },
        )
    ]
    if finale:
        rewards.append(
            RewardSpec(f"{quest_slug}/reward/xp", "xp", {"xp": 100})
        )
    return tuple(rewards)


def _build_manual(manual: _Manual, order_index: int) -> ChapterSpec:
    quests = []
    for node_index, node in enumerate(manual.nodes):
        finale = node_index == len(manual.nodes) - 1
        quests.append(
            QuestSpec(
                slug=node.slug,
                title=node.title,
                subtitle=node.subtitle,
                description=(node.description,),
                x=float(node_index * 2),
                y=0.0,
                dependencies=(manual.nodes[node_index - 1].slug,) if node_index else (),
                tasks=tuple(_build_task(task) for task in node.tasks),
                rewards=_rewards(node.slug, finale),
                optional=True,
                explicit_id=manual.root_id if node_index == 0 else None,
                size=1.5 if node_index == 0 else None,
            )
        )
    return ChapterSpec(
        slug=manual.slug,
        title=manual.title,
        group=FIELD_MANUALS,
        icon=manual.icon,
        order_index=order_index,
        explicit_id=manual.chapter_id,
        quest_links=(),
        quests=tuple(quests),
    )


def build_field_manuals() -> tuple[ChapterSpec, ...]:
    return apply_manual_return_links(
        tuple(
            _build_manual(manual, order_index)
            for order_index, manual in enumerate(_MANUALS)
        )
    )
