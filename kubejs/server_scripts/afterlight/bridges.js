// Cross-mod bridge exemplars (spec section 7 item 2): every major
// processing line should accept its neighbors' ores. These establish the
// pattern; Plan 05 expands coverage.
// Balance note: yields sit BELOW each mod's native best path (Mekanism
// enrichment stays the efficient route for its own ores) so bridges add
// convenience, not power creep.
// 1.21 chance syntax: CreateItem.of(item, chance) per KubeJS Create; IE
// recipes are emitted as native JSON (schema extracted from the IE jar).
ServerEvents.recipes(event => {
  AFTERLIGHT.MEK_ORES.forEach(ore => {
    // Create crushing wheels accept Mekanism raw ores.
    event.recipes.create.crushing(
      [ore.dust, CreateItem.of(ore.dust, 0.3), CreateItem.of('create:experience_nugget', 0.75)],
      ore.raw
    ).id('kubejs:bridge/crushing/' + ore.raw.replace(':', '_'))

    // Immersive Engineering's crusher accepts them too (native schema).
    event.custom({
      type: 'immersiveengineering:crusher',
      energy: 6000,
      input: { item: ore.raw },
      result: { id: ore.dust },
      secondaries: [{ chance: 0.25, output: { item: ore.dust } }]
    }).id('kubejs:bridge/ie_crusher/' + ore.raw.replace(':', '_'))
  })
})
