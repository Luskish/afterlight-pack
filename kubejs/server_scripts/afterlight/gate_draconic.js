// Spec section 6, hard gate 4: Draconic Evolution sits behind story
// completion. Mechanism: the two entry recipes every Draconic chain runs
// through (draconium_core, dislocator) are replaced with exact copies that
// additionally require an Ascendancy Seal, which only the finale quest
// chain grants. Replacements mirror the mod's own 1.21.1 recipe JSONs
// (extracted from the jar) with the center key swapped to a seal-holding
// pattern slot. This also insulates the group from Draconic's beta bugs
// until postgame.
ServerEvents.recipes(event => {
  event.remove({ id: 'draconicevolution:components/draconium_core' })
  event.custom({
    type: 'minecraft:crafting_shaped',
    category: 'misc',
    key: {
      A: { tag: 'c:ingots/draconium' },
      B: { tag: 'c:ingots/gold' },
      C: { tag: 'c:gems/diamond' },
      Z: { item: AFTERLIGHT.SEAL }
    },
    pattern: ['ABA', 'BCB', 'AZA'],
    result: { count: 1, id: 'draconicevolution:draconium_core' }
  }).id('kubejs:gated/draconium_core')

  event.remove({ id: 'draconicevolution:tools/dislocator' })
  event.custom({
    type: 'minecraft:crafting_shaped',
    category: 'misc',
    key: {
      A: { item: 'minecraft:blaze_powder' },
      B: { tag: 'c:dusts/draconium' },
      C: { item: 'minecraft:ender_eye' },
      Z: { item: AFTERLIGHT.SEAL }
    },
    pattern: ['ABA', 'BCB', 'AZA'],
    result: { count: 1, id: 'draconicevolution:dislocator' }
  }).id('kubejs:gated/dislocator')
})
