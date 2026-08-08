// Requisition Chits surface in the world's ruins (spec: reward economy),
// seeding the Depot loop before quests grant them in volume.
// Modest chance, structure chests only.
LootJS.modifiers(event => {
  event.addTableModifier([
    'minecraft:chests/simple_dungeon',
    'minecraft:chests/abandoned_mineshaft',
    'minecraft:chests/stronghold_corridor',
    'minecraft:chests/ancient_city',
    'minecraft:chests/end_city_treasure'
  ])
    .randomChance(0.4)
    .addLoot(LootEntry.of(AFTERLIGHT.CHIT).setCount([1, 3]))
})
