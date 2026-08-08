// AFTERLIGHT custom items. Registry work lives in startup scripts and
// requires a full restart to apply (see kubejs-modding skill).
StartupEvents.registry('item', event => {
  // Quest currency dispensed by ECHO, spent at the Requisition Depot.
  event.create('requisition_chit')
    .displayName('Requisition Chit')
    .rarity('uncommon')
    .maxStackSize(64)

  // Granted by the finale quest chain. The only key that unlocks
  // Draconic Evolution's entry recipes (spec hard gate 4).
  event.create('ascendancy_seal')
    .displayName('Ascendancy Seal')
    .rarity('epic')
    .maxStackSize(16)
    .glow(true)

  event.create('deep_vault_key')
    .displayName('Deep Vault Key')
    .rarity('rare')
    .maxStackSize(1)
    .glow(true)

  event.create('schematic_kinetic_frame')
    .displayName('Kinetic Frame Schematic')
    .rarity('epic')
    .maxStackSize(1)
    .glow(true)

  event.create('schematic_industrial_anchor')
    .displayName('Industrial Anchor Schematic')
    .rarity('epic')
    .maxStackSize(1)
    .glow(true)

  event.create('schematic_isotopic_core')
    .displayName('Isotopic Core Schematic')
    .rarity('epic')
    .maxStackSize(1)
    .glow(true)

  event.create('schematic_lattice_matrix')
    .displayName('Lattice Matrix Schematic')
    .rarity('epic')
    .maxStackSize(1)
    .glow(true)

  event.create('gate_blueprint')
    .displayName('Gate Blueprint')
    .rarity('epic')
    .maxStackSize(1)
    .glow(true)

  event.create('undercurrent_stabilizer_precursor')
    .displayName('Undercurrent Stabilizer Precursor')
    .rarity('rare')
    .maxStackSize(16)
    .glow(false)
})
