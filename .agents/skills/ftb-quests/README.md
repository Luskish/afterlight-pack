# ftb-quests

An agent skill for creating, designing, writing, and modifying [FTB Quests](https://www.curseforge.com/minecraft/mc-mods/ftb-quests) configurations in Minecraft modpacks.

## What This Skill Does

Guides AI coding agents through FTB Quests development with accurate, version-specific knowledge (1.21+):

- **SNBT file authoring**: correct syntax, ID format, item objects, localization
- **Chapter & quest creation**: file structure, dependency chains, visibility settings
- **All 12 task types**: item, checkmark, kill, location, advancement, dimension, stat, biome, structure, stage, fluid, energy
- **All 12 reward types**: item, XP, command, choice, random, loot, all table, advancement, toast, stage, custom
- **KubeJS integration**: custom rewards via `FTBQuestsEvents.customReward()`
- **Reward tables & loot crates**: configuration, nesting, datapack integration, preset rarities
- **Theme styling**: `ftb_quests_theme.txt` properties, tag-based filtering, custom shapes

## Install

```bash
npx skills add ParticleG/ftb-quests -g -y
```

Or with bun:

```bash
bunx skills add ParticleG/ftb-quests -g -y
```

## Structure

```
├── SKILL.md                  # Main skill instructions
└── references/
    ├── snbt-format.md        # SNBT syntax, ID format, item objects, localization
    ├── tasks-and-rewards.md  # All task & reward types with SNBT templates
    └── styling.md            # Theme properties, tag filtering, custom shapes
```

## Example Prompts

- "Create a new FTB Quests chapter with 5 quests forming a dependency tree"
- "Write a KubeJS custom reward that gives items based on player level"
- "Design a quest book theme with custom colors and boss quest styling"
- "Add a repeatable item exchange quest that consumes the submitted items"
- "Configure loot crates with tiered rarities that drop from mobs"

## Compatibility

- FTB Quests for Minecraft 1.21+ (SNBT format, component-based items)
- KubeJS + FTB XMod Compat (for custom rewards)
- Works with any agent that supports the [Skills](https://skills.sh/) ecosystem

## License

MIT
