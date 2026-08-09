ServerEvents.recipes(event => {
  event.shapeless(AFTERLIGHT.STABILIZER, [
    'kubejs:undercurrent_stabilizer_precursor',
    'occultism:spirit_attuned_gem'
  ]).id('kubejs:gate/stabilizer/occultism')

  event.shapeless(AFTERLIGHT.STABILIZER, [
    'kubejs:undercurrent_stabilizer_precursor',
    'irons_spellbooks:magic_cloth'
  ]).id('kubejs:gate/stabilizer/irons_spellbooks')

  event.shapeless(AFTERLIGHT.STABILIZER, [
    'kubejs:undercurrent_stabilizer_precursor',
    'malum:soul_stained_steel_ingot'
  ]).id('kubejs:gate/stabilizer/malum')

  event.recipes.create.mechanical_crafting(
    AFTERLIGHT.GATE_CORE,
    ['CCAAPPS', 'CC B AA', 'A PKS S', 'P IUO S', 'A SLP P', 'CA   CS', 'SSPPACC'],
    {
      B: 'kubejs:gate_blueprint',
      K: AFTERLIGHT.GATE_KINETIC,
      I: AFTERLIGHT.GATE_INDUSTRIAL,
      O: AFTERLIGHT.GATE_ISOTOPIC,
      L: AFTERLIGHT.GATE_LATTICE,
      U: AFTERLIGHT.STABILIZER,
      C: 'create:iron_sheet',
      A: 'ae2:logic_processor',
      P: 'pneumaticcraft:printed_circuit_board',
      S: 'immersiveengineering:ingot_steel'
    }
  ).acceptMirrored(false).id('kubejs:gate/gate_of_return_core')
})
