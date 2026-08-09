ServerEvents.recipes(event => {
  event.recipes.create.mechanical_crafting(AFTERLIGHT.GATE_KINETIC, ['ABCDF', 'EFABC', 'DASBE', 'CDEFA', 'FBCDE'], {
    A: 'create:precision_mechanism',
    B: 'create:sturdy_sheet',
    C: 'create:brass_sheet',
    D: 'create:electron_tube',
    E: 'create:railway_casing',
    F: 'create:mechanical_crafter',
    S: 'kubejs:schematic_kinetic_frame'
  }).acceptMirrored(false).id('kubejs:gate/component/kinetic_frame')

  event.recipes.create.mechanical_crafting(AFTERLIGHT.GATE_INDUSTRIAL, ['ABCDF', 'EFABC', 'DASBE', 'CDEFA', 'FBCDE'], {
    A: 'immersiveengineering:heavy_engineering',
    B: 'immersiveengineering:component_electronic_adv',
    C: 'immersiveengineering:component_steel',
    D: 'immersiveengineering:capacitor_hv',
    E: 'immersiveengineering:radiator',
    F: 'immersiveengineering:wirecoil_electrum',
    S: 'kubejs:schematic_industrial_anchor'
  }).acceptMirrored(false).id('kubejs:gate/component/industrial_anchor')

  event.recipes.create.mechanical_crafting(AFTERLIGHT.GATE_ISOTOPIC, ['ABCDF', 'EFABC', 'DASBE', 'CDEFA', 'FBCDE'], {
    A: 'mekanism:alloy_atomic',
    B: 'mekanism:ultimate_control_circuit',
    C: 'mekanism:hdpe_sheet',
    D: 'mekanism:pellet_polonium',
    E: 'mekanism:pellet_plutonium',
    F: 'mekanism:pellet_antimatter',
    S: 'kubejs:schematic_isotopic_core'
  }).acceptMirrored(false).id('kubejs:gate/component/isotopic_core')

  event.recipes.create.mechanical_crafting(AFTERLIGHT.GATE_LATTICE, ['ABCDF', 'EFABC', 'DASBE', 'CDEFA', 'FBCDE'], {
    A: 'ae2:logic_processor',
    B: 'ae2:calculation_processor',
    C: 'ae2:engineering_processor',
    D: 'ae2:cell_component_256k',
    E: 'ae2:dense_energy_cell',
    F: 'ae2:quantum_entangled_singularity',
    S: 'kubejs:schematic_lattice_matrix'
  }).acceptMirrored(false).id('kubejs:gate/component/lattice_matrix')
})
