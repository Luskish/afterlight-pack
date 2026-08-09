ServerEvents.recipes(event => {
  event.remove({ id: 'draconicevolution:components/draconium_core' })
  event.shaped('draconicevolution:draconium_core', ['ABA', 'BCB', 'AZA'], {
    A: '#c:ingots/draconium',
    B: '#c:ingots/gold',
    C: '#c:gems/diamond',
    Z: AFTERLIGHT.SEAL
  }).keepIngredient({ item: AFTERLIGHT.SEAL, index: 7 })
    .id('kubejs:gated/draconium_core')

  event.remove({ id: 'draconicevolution:tools/dislocator' })
  event.shaped('draconicevolution:dislocator', ['ABA', 'BCB', 'AZA'], {
    A: 'minecraft:blaze_powder',
    B: '#c:dusts/draconium',
    C: 'minecraft:ender_eye',
    Z: AFTERLIGHT.SEAL
  }).keepIngredient({ item: AFTERLIGHT.SEAL, index: 7 })
    .id('kubejs:gated/dislocator')

  event.remove({ id: 'draconicevolution:modules/module_core' })
  event.shaped('draconicevolution:module_core', ['IRI', 'GDG', 'IZI'], {
    D: '#c:ingots/draconium',
    G: '#c:ingots/gold',
    I: '#c:ingots/iron',
    R: '#c:dusts/redstone',
    Z: AFTERLIGHT.SEAL
  }).keepIngredient({ item: AFTERLIGHT.SEAL, index: 7 })
    .id('kubejs:gated/module_core')
})
