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
})
