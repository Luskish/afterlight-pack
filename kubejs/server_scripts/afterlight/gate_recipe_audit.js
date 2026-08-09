const MechanicalCraftingInput = Java.loadClass('com.simibubi.create.content.kinetics.crafter.MechanicalCraftingInput')
const GroupedItems = Java.loadClass('com.simibubi.create.content.kinetics.crafter.RecipeGridHandler$GroupedItems')
const CraftingInput = Java.loadClass('net.minecraft.world.item.crafting.CraftingInput')
const ItemStack = Java.loadClass('net.minecraft.world.item.ItemStack')
const ArrayList = Java.loadClass('java.util.ArrayList')
const CompoundTag = Java.loadClass('net.minecraft.nbt.CompoundTag')
const ListTag = Java.loadClass('net.minecraft.nbt.ListTag')
const ResourceLocation = Java.loadClass('net.minecraft.resources.ResourceLocation')

ServerEvents.loaded(event => {
  const server = event.server
  const level = server.overworld()
  const registries = server.registryAccess()

  function afterlightRecipe(id) {
    const optional = server.getRecipeManager().byKey(ResourceLocation.parse(id))
    if (optional.isEmpty()) throw new Error(`missing ${id}`)
    return optional.get().value()
  }

  function afterlightMechanicalInput(pattern, keys) {
    const root = new CompoundTag()
    const grid = new ListTag()
    for (let row = 0; row < pattern.length; row++) {
      for (let column = 0; column < pattern[row].length; column++) {
        let character = pattern[row][column]
        if (character === ' ') continue
        let entry = new CompoundTag()
        entry.putInt('x', column)
        entry.putInt('y', pattern.length - 1 - row)
        let stack = Item.of(keys[character]).copy()
        entry.put('item', stack.saveOptional(registries))
        grid.add(entry)
      }
    }
    root.put('Grid', grid)
    const grouped = GroupedItems.read(root, registries)
    grouped.calcStats()
    return MechanicalCraftingInput.of(grouped)
  }

  function afterlightCraftingInput(pattern, keys) {
    const items = new ArrayList()
    for (let row = 0; row < pattern.length; row++) {
      for (let column = 0; column < pattern[row].length; column++) {
        let character = pattern[row][column]
        items.add(character === ' ' ? ItemStack.EMPTY : Item.of(keys[character]).copy())
      }
    }
    return CraftingInput.of(pattern[0].length, pattern.length, items)
  }

  function afterlightAssertMatch(recipe, input, label) {
    if (!recipe.matches(input, level)) throw new Error(`${label} did not match`)
  }

  function afterlightAssertNoMatch(recipe, input, label) {
    if (recipe.matches(input, level)) throw new Error(`${label} matched unexpectedly`)
  }

  function afterlightAssertOnlySealRemainder(recipe, input, label) {
    const remainder = recipe.getRemainingItems(input)
    if (remainder.size() !== 9) throw new Error(`${label} returned ${remainder.size()} remainder slots`)
    for (let index = 0; index < remainder.size(); index++) {
      let stack = remainder.get(index)
      if (index === 7) {
        if (!ItemStack.isSameItemSameComponents(stack, Item.of(AFTERLIGHT.SEAL)) || stack.getCount() !== 1) {
          throw new Error(`${label} did not return one Seal in slot 7`)
        }
      } else if (!stack.isEmpty()) {
        throw new Error(`${label} returned an extra remainder in slot ${index}`)
      }
    }
  }

  const requiredItems = [
    ['create:precision_mechanism', Item.exists('create:precision_mechanism')],
    ['create:sturdy_sheet', Item.exists('create:sturdy_sheet')],
    ['create:brass_sheet', Item.exists('create:brass_sheet')],
    ['create:electron_tube', Item.exists('create:electron_tube')],
    ['create:railway_casing', Item.exists('create:railway_casing')],
    ['create:mechanical_crafter', Item.exists('create:mechanical_crafter')],
    ['immersiveengineering:heavy_engineering', Item.exists('immersiveengineering:heavy_engineering')],
    ['immersiveengineering:component_electronic_adv', Item.exists('immersiveengineering:component_electronic_adv')],
    ['immersiveengineering:component_steel', Item.exists('immersiveengineering:component_steel')],
    ['immersiveengineering:capacitor_hv', Item.exists('immersiveengineering:capacitor_hv')],
    ['immersiveengineering:radiator', Item.exists('immersiveengineering:radiator')],
    ['immersiveengineering:wirecoil_electrum', Item.exists('immersiveengineering:wirecoil_electrum')],
    ['mekanism:alloy_atomic', Item.exists('mekanism:alloy_atomic')],
    ['mekanism:ultimate_control_circuit', Item.exists('mekanism:ultimate_control_circuit')],
    ['mekanism:hdpe_sheet', Item.exists('mekanism:hdpe_sheet')],
    ['mekanism:pellet_polonium', Item.exists('mekanism:pellet_polonium')],
    ['mekanism:pellet_plutonium', Item.exists('mekanism:pellet_plutonium')],
    ['mekanism:pellet_antimatter', Item.exists('mekanism:pellet_antimatter')],
    ['ae2:logic_processor', Item.exists('ae2:logic_processor')],
    ['ae2:calculation_processor', Item.exists('ae2:calculation_processor')],
    ['ae2:engineering_processor', Item.exists('ae2:engineering_processor')],
    ['ae2:cell_component_256k', Item.exists('ae2:cell_component_256k')],
    ['ae2:dense_energy_cell', Item.exists('ae2:dense_energy_cell')],
    ['ae2:quantum_entangled_singularity', Item.exists('ae2:quantum_entangled_singularity')],
    ['create:iron_sheet', Item.exists('create:iron_sheet')],
    ['pneumaticcraft:printed_circuit_board', Item.exists('pneumaticcraft:printed_circuit_board')],
    ['immersiveengineering:ingot_steel', Item.exists('immersiveengineering:ingot_steel')],
    ['occultism:spirit_attuned_gem', Item.exists('occultism:spirit_attuned_gem')],
    ['irons_spellbooks:magic_cloth', Item.exists('irons_spellbooks:magic_cloth')],
    ['malum:soul_stained_steel_ingot', Item.exists('malum:soul_stained_steel_ingot')]
  ]
  requiredItems.forEach(entry => {
    if (!entry[1]) throw new Error(`missing Gate ingredient ${entry[0]}`)
  })

  const componentPattern = ['ABCDF', 'EFABC', 'DASBE', 'CDEFA', 'FBCDE']
  const mechanicalRecipes = [
    {
      id: 'kubejs:gate/component/kinetic_frame',
      recipe: afterlightRecipe('kubejs:gate/component/kinetic_frame'),
      output: AFTERLIGHT.GATE_KINETIC,
      pattern: componentPattern,
      keys: {
        A: 'create:precision_mechanism', B: 'create:sturdy_sheet', C: 'create:brass_sheet',
        D: 'create:electron_tube', E: 'create:railway_casing', F: 'create:mechanical_crafter',
        S: 'kubejs:schematic_kinetic_frame'
      }
    },
    {
      id: 'kubejs:gate/component/industrial_anchor',
      recipe: afterlightRecipe('kubejs:gate/component/industrial_anchor'),
      output: AFTERLIGHT.GATE_INDUSTRIAL,
      pattern: componentPattern,
      keys: {
        A: 'immersiveengineering:heavy_engineering', B: 'immersiveengineering:component_electronic_adv',
        C: 'immersiveengineering:component_steel', D: 'immersiveengineering:capacitor_hv',
        E: 'immersiveengineering:radiator', F: 'immersiveengineering:wirecoil_electrum',
        S: 'kubejs:schematic_industrial_anchor'
      }
    },
    {
      id: 'kubejs:gate/component/isotopic_core',
      recipe: afterlightRecipe('kubejs:gate/component/isotopic_core'),
      output: AFTERLIGHT.GATE_ISOTOPIC,
      pattern: componentPattern,
      keys: {
        A: 'mekanism:alloy_atomic', B: 'mekanism:ultimate_control_circuit', C: 'mekanism:hdpe_sheet',
        D: 'mekanism:pellet_polonium', E: 'mekanism:pellet_plutonium', F: 'mekanism:pellet_antimatter',
        S: 'kubejs:schematic_isotopic_core'
      }
    },
    {
      id: 'kubejs:gate/component/lattice_matrix',
      recipe: afterlightRecipe('kubejs:gate/component/lattice_matrix'),
      output: AFTERLIGHT.GATE_LATTICE,
      pattern: componentPattern,
      keys: {
        A: 'ae2:logic_processor', B: 'ae2:calculation_processor', C: 'ae2:engineering_processor',
        D: 'ae2:cell_component_256k', E: 'ae2:dense_energy_cell', F: 'ae2:quantum_entangled_singularity',
        S: 'kubejs:schematic_lattice_matrix'
      }
    },
    {
      id: 'Gate of Return core',
      recipe: afterlightRecipe('kubejs:gate/gate_of_return_core'),
      output: AFTERLIGHT.GATE_CORE,
      pattern: ['CCAAPPS', 'CC B AA', 'A PKS S', 'P IUO S', 'A SLP P', 'CA   CS', 'SSPPACC'],
      keys: {
        B: 'kubejs:gate_blueprint', K: AFTERLIGHT.GATE_KINETIC, I: AFTERLIGHT.GATE_INDUSTRIAL,
        O: AFTERLIGHT.GATE_ISOTOPIC, L: AFTERLIGHT.GATE_LATTICE, U: AFTERLIGHT.STABILIZER,
        C: 'create:iron_sheet', A: 'ae2:logic_processor', P: 'pneumaticcraft:printed_circuit_board',
        S: 'immersiveengineering:ingot_steel'
      }
    }
  ]

  mechanicalRecipes.forEach(spec => {
    const recipe = spec.recipe
    if (!String(recipe).startsWith('com.simibubi.create.content.kinetics.crafter.MechanicalCraftingRecipe@')) {
      throw new Error(`${spec.id} has the wrong recipe type`)
    }
    if (recipe.acceptsMirrored()) throw new Error(`${spec.id} accepts mirroring`)
    const input = afterlightMechanicalInput(spec.pattern, spec.keys)
    const expectedWidth = spec.pattern[0].length
    const expectedHeight = spec.pattern.length
    if (input.width() !== expectedWidth || input.height() !== expectedHeight) {
      throw new Error(`${spec.id} dimensions changed to ${input.width()} by ${input.height()}`)
    }
    if (!recipe.canCraftInDimensions(expectedWidth, expectedHeight)
      || recipe.canCraftInDimensions(expectedWidth - 1, expectedHeight)
      || recipe.canCraftInDimensions(expectedWidth, expectedHeight - 1)) {
      throw new Error(`${spec.id} crafting dimensions are not exact`)
    }
    const declaredOutput = recipe.getResultItem(registries)
    const expectedOutput = Item.of(spec.output)
    if (!ItemStack.isSameItemSameComponents(declaredOutput, expectedOutput) || declaredOutput.getCount() !== 1) {
      throw new Error(`${spec.id} declared output changed`)
    }
    afterlightAssertMatch(recipe, input, `${spec.id} canonical input`)
    const assembled = recipe.assemble(input, registries)
    if (!ItemStack.isSameItemSameComponents(assembled, expectedOutput) || assembled.getCount() !== 1) {
      throw new Error(`${spec.id} assembled output changed`)
    }

    const mirrored = spec.pattern.map(row => row.split('').reverse().join(''))
    afterlightAssertNoMatch(recipe, afterlightMechanicalInput(mirrored, spec.keys), `${spec.id} mirrored input`)

    for (let row = 0; row < spec.pattern.length; row++) {
      for (let column = 0; column < spec.pattern[row].length; column++) {
        let changedPattern = spec.pattern.slice()
        let character = spec.pattern[row][column]
        changedPattern[row] = changedPattern[row].substring(0, column)
          + (character === ' ' ? 'X' : ' ')
          + changedPattern[row].substring(column + 1)
        let changedKeys = {}
        Object.keys(spec.keys).forEach(key => { changedKeys[key] = spec.keys[key] })
        changedKeys.X = 'minecraft:barrier'
        afterlightAssertNoMatch(
          recipe,
          afterlightMechanicalInput(changedPattern, changedKeys),
          `${spec.id} pattern position ${row},${column}`
        )
      }
    }

    Object.keys(spec.keys).forEach(key => {
      const changedKeys = {}
      Object.keys(spec.keys).forEach(copyKey => { changedKeys[copyKey] = spec.keys[copyKey] })
      changedKeys[key] = 'minecraft:barrier'
      afterlightAssertNoMatch(
        recipe,
        afterlightMechanicalInput(spec.pattern, changedKeys),
        `${spec.id} key ${key}`
      )
    })
  })

  const stabilizerRecipes = [
    {
      id: 'kubejs:gate/stabilizer/occultism',
      recipe: afterlightRecipe('kubejs:gate/stabilizer/occultism'),
      branch: 'occultism:spirit_attuned_gem'
    },
    {
      id: 'kubejs:gate/stabilizer/irons_spellbooks',
      recipe: afterlightRecipe('kubejs:gate/stabilizer/irons_spellbooks'),
      branch: 'irons_spellbooks:magic_cloth'
    },
    {
      id: 'kubejs:gate/stabilizer/malum',
      recipe: afterlightRecipe('kubejs:gate/stabilizer/malum'),
      branch: 'malum:soul_stained_steel_ingot'
    }
  ]
  stabilizerRecipes.forEach(spec => {
    const recipe = spec.recipe
    const ingredients = recipe.getIngredients()
    if (ingredients.size() !== 2
      || !ingredients.get(0).test(Item.of('kubejs:undercurrent_stabilizer_precursor'))
      || !ingredients.get(1).test(Item.of(spec.branch))) {
      throw new Error(`${spec.id} ingredients changed`)
    }
    const keys = { A: 'kubejs:undercurrent_stabilizer_precursor', B: spec.branch }
    const input = afterlightCraftingInput(['AB'], keys)
    afterlightAssertMatch(recipe, input, `${spec.id} canonical input`)
    afterlightAssertNoMatch(recipe, afterlightCraftingInput(['A '], keys), `${spec.id} missing branch`)
    afterlightAssertNoMatch(recipe, afterlightCraftingInput([' B'], keys), `${spec.id} missing precursor`)
    const declaredOutput = recipe.getResultItem(registries)
    const assembled = recipe.assemble(input, registries)
    const expectedOutput = Item.of(AFTERLIGHT.STABILIZER)
    if (!ItemStack.isSameItemSameComponents(declaredOutput, expectedOutput)
      || declaredOutput.getCount() !== 1
      || !ItemStack.isSameItemSameComponents(assembled, expectedOutput)
      || assembled.getCount() !== 1) {
      throw new Error(`${spec.id} output changed`)
    }
  })

  const draconicRecipes = [
    {
      original: 'draconicevolution:components/draconium_core',
      id: 'kubejs:gated/draconium_core',
      recipe: afterlightRecipe('kubejs:gated/draconium_core'),
      output: 'draconicevolution:draconium_core',
      pattern: ['ABA', 'BCB', 'AZA'],
      keys: {
        A: 'draconicevolution:draconium_ingot', B: 'minecraft:gold_ingot',
        C: 'minecraft:diamond', Z: AFTERLIGHT.SEAL
      },
      nonSealKeys: ['A', 'B', 'C']
    },
    {
      original: 'draconicevolution:tools/dislocator',
      id: 'kubejs:gated/dislocator',
      recipe: afterlightRecipe('kubejs:gated/dislocator'),
      output: 'draconicevolution:dislocator',
      pattern: ['ABA', 'BCB', 'AZA'],
      keys: {
        A: 'minecraft:blaze_powder', B: 'draconicevolution:draconium_dust',
        C: 'minecraft:ender_eye', Z: AFTERLIGHT.SEAL
      },
      nonSealKeys: ['A', 'B', 'C']
    },
    {
      original: 'draconicevolution:modules/module_core',
      id: 'kubejs:gated/module_core',
      recipe: afterlightRecipe('kubejs:gated/module_core'),
      output: 'draconicevolution:module_core',
      pattern: ['IRI', 'GDG', 'IZI'],
      keys: {
        D: 'draconicevolution:draconium_ingot', G: 'minecraft:gold_ingot',
        I: 'minecraft:iron_ingot', R: 'minecraft:redstone', Z: AFTERLIGHT.SEAL
      },
      nonSealKeys: ['D', 'G', 'I', 'R']
    }
  ]
  draconicRecipes.forEach(spec => {
    if (server.getRecipeManager().byKey(ResourceLocation.parse(spec.original)).isPresent()) {
      throw new Error(`${spec.original} was not removed`)
    }
    const recipe = spec.recipe
    if (!String(recipe.getSerializer()).startsWith('dev.latvian.mods.kubejs.recipe.special.ShapedKubeJSRecipe$SerializerKJS@')) {
      throw new Error(`${spec.id} is not using the kubejs:shaped serializer`)
    }
    const validInput = afterlightCraftingInput(spec.pattern, spec.keys)
    afterlightAssertMatch(recipe, validInput, `${spec.id} canonical input`)
    const noSealPattern = spec.pattern.slice()
    noSealPattern[2] = noSealPattern[2].substring(0, 1) + ' ' + noSealPattern[2].substring(2)
    afterlightAssertNoMatch(recipe, afterlightCraftingInput(noSealPattern, spec.keys), `${spec.id} without Seal`)
    spec.nonSealKeys.forEach(key => {
      const changedKeys = {}
      Object.keys(spec.keys).forEach(copyKey => { changedKeys[copyKey] = spec.keys[copyKey] })
      changedKeys[key] = 'minecraft:barrier'
      afterlightAssertNoMatch(
        recipe,
        afterlightCraftingInput(spec.pattern, changedKeys),
        `${spec.id} wrong key ${key}`
      )
    })
    const declaredOutput = recipe.getResultItem(registries)
    const assembled = recipe.assemble(validInput, registries)
    const expectedOutput = Item.of(spec.output)
    if (!ItemStack.isSameItemSameComponents(declaredOutput, expectedOutput)
      || declaredOutput.getCount() !== 1
      || !ItemStack.isSameItemSameComponents(assembled, expectedOutput)
      || assembled.getCount() !== 1) {
      throw new Error(`${spec.id} output changed`)
    }
    afterlightAssertOnlySealRemainder(recipe, validInput, spec.id)

    const countTwoKeys = {}
    Object.keys(spec.keys).forEach(key => { countTwoKeys[key] = spec.keys[key] })
    countTwoKeys.Z = Item.of(AFTERLIGHT.SEAL, 2)
    const countTwoInput = afterlightCraftingInput(spec.pattern, countTwoKeys)
    afterlightAssertMatch(recipe, countTwoInput, `${spec.id} count-two Seal hazard input`)
    const countTwoRemainder = recipe.getRemainingItems(countTwoInput)
    for (let index = 0; index < countTwoRemainder.size(); index++) {
      let stack = countTwoRemainder.get(index)
      if (index === 7) {
        if (!ItemStack.isSameItemSameComponents(stack, Item.of(AFTERLIGHT.SEAL)) || stack.getCount() !== 2) {
          throw new Error(`${spec.id} count-two Seal hazard remainder changed`)
        }
        let mergedCount = countTwoInput.getItem(index).getCount() - 1 + stack.getCount()
        if (mergedCount !== 3) throw new Error(`${spec.id} count-two Seal hazard merge changed to ${mergedCount}`)
      } else if (!stack.isEmpty()) {
        throw new Error(`${spec.id} count-two Seal hazard returned an extra remainder`)
      }
    }
  })

  const expectedProducerCount = {
    'kubejs:gate_kinetic_frame': 1,
    'kubejs:gate_industrial_anchor': 1,
    'kubejs:gate_isotopic_core': 1,
    'kubejs:gate_lattice_matrix': 1,
    'kubejs:undercurrent_stabilizer': 3,
    'kubejs:gate_of_return_core': 1,
    'draconicevolution:draconium_core': 1,
    'draconicevolution:dislocator': 1,
    'draconicevolution:module_core': 1
  }
  const producerIds = {}
  Object.keys(expectedProducerCount).forEach(output => { producerIds[output] = [] })
  server.getRecipeManager().getRecipes().forEach(holder => {
    const output = holder.value()['getResultItem(net.minecraft.core.HolderLookup$Provider)'](registries)
    if (output.isEmpty()) return
    const outputId = String(output.id)
    if (Object.prototype.hasOwnProperty.call(producerIds, outputId)) {
      producerIds[outputId].push(String(holder.id()))
    }
  })
  Object.keys(expectedProducerCount).forEach(output => {
    if (producerIds[output].length !== expectedProducerCount[output]) {
      throw new Error(`${output} producer count changed: ${producerIds[output].join(', ')}`)
    }
  })
  const approvedStabilizers = [
    'kubejs:gate/stabilizer/irons_spellbooks',
    'kubejs:gate/stabilizer/malum',
    'kubejs:gate/stabilizer/occultism'
  ]
  producerIds[AFTERLIGHT.STABILIZER].sort()
  if (producerIds[AFTERLIGHT.STABILIZER].join('|') !== approvedStabilizers.join('|')) {
    throw new Error(`stabilizer producer set changed: ${producerIds[AFTERLIGHT.STABILIZER].join(', ')}`)
  }

  const auditSha256 = '__AFTERLIGHT_GATE_AUDIT_SHA256__'
  const bootNonce = '__AFTERLIGHT_GATE_BOOT_NONCE__'
  console.info(`[AFTERLIGHT GATE RECIPE AUDIT] OK ${auditSha256} 11 ${bootNonce}`)
})
