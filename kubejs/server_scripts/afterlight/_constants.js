// AFTERLIGHT shared constants. Underscore prefix loads this file before
// the other server scripts in this folder.
// Scope rule (spec section 7): scripts serve story, unification, the
// automation on-ramp, or a documented balance need. Nothing else.
const AFTERLIGHT = {
  CHIT: 'kubejs:requisition_chit',
  SEAL: 'kubejs:ascendancy_seal',
  GATE_KINETIC: 'kubejs:gate_kinetic_frame',
  GATE_INDUSTRIAL: 'kubejs:gate_industrial_anchor',
  GATE_ISOTOPIC: 'kubejs:gate_isotopic_core',
  GATE_LATTICE: 'kubejs:gate_lattice_matrix',
  STABILIZER: 'kubejs:undercurrent_stabilizer',
  GATE_CORE: 'kubejs:gate_of_return_core',
  // Mekanism ore families bridged into other mods' processing chains.
  // Only families with real raw forms; fluorite is a direct gem drop and
  // has no raw item (learned from a failed-recipe boot log).
  MEK_ORES: [
    { raw: 'mekanism:raw_osmium', dust: 'mekanism:dust_osmium' },
    { raw: 'mekanism:raw_uranium', dust: 'mekanism:dust_uranium' },
    { raw: 'mekanism:raw_lead', dust: 'mekanism:dust_lead' },
    { raw: 'mekanism:raw_tin', dust: 'mekanism:dust_tin' }
  ]
}
