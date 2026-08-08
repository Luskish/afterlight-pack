# AFTERLIGHT — Modpack Design Spec

**Date:** 2026-08-07
**Status:** Approved design, pending user spec review
**Owner:** Shane + friend group (private server)

---

## 1. Overview

AFTERLIGHT is a custom Minecraft modpack: kitchen-sink breadth (ATM-class mod variety) fused with a real authored storyline delivered through a quest book — a combination no current-generation pack occupies (ATM10/Craftoria/FTB Evolution all ship utilitarian quest books; the narrative gold standards — Blightfall, MC Eternal, MeatballCraft — are all on legacy versions). Tech-focused, exploration-rich, automation-forward, for a private friend group on a self-managed VPS.

**One-line pitch:** You aren't discovering technology — you're remembering it.

## 2. Requirements (from user interview, 2026-08-07)

| Dimension | Decision |
|---|---|
| Progression style | **Guided kitchen sink** — mods (mostly) untouched, story+quests guide; soft gates; sandbox always viable |
| Story | **Sci-fi rediscovery blended with post-apocalyptic** |
| World difficulty | **Dangerous world, fair rules** — danger from places/bosses, not survival micromanagement |
| Length | **100–200+ hours** full story arc |
| Mod center of gravity | Classic big tech (Mekanism/AE2/IE) core; Create present but moderate; GregTech as an optional taste; magic compact/side-path (least favorite); **automation guided by quests, made easy to enter** |
| Inclusion philosophy | "Anything that is cool, include it" — generous wow-factor curation within taste calibration |
| Players/hardware | Small friend group; modern specs everywhere; strong VPS (user-paid, user-managed) |
| Distribution | **Auto-updating primary** (friends set up once, always current) **+ old-school zip exports** for those who prefer manual |
| Audience | **Private, built publish-grade** (clean licensing/repo so going public later is a decision, not a rebuild) |

## 3. Platform decision

**NeoForge on Minecraft 1.21.1, Java 21.**

Rationale (verified via research 2026-08-07):

- 1.21.1 NeoForge is the modded hub: 16k+ mods, all target tech mods present and active (Mekanism 10.7.x, Create 6.0.x, AE2, IE, GTCEu Modern, EnderIO rewrite, Oritech).
- Minecraft moved to calendar versioning (26.1 "Tiny Takeover" in Mar 2026, 26.2 current). Modded has NOT migrated: ATM11 on 26.1.2 is "super early alpha" (~243/500 mods, placeholder quests). Targeting 26.x today means a fraction of the library.
- FTB Quests 2101.x (SNBT format + lang files) is mature on 1.21.1; the 26.x line switches to Json5 — a documented migration we defer.
- Migration path insurance: ATM-11's public repo is the live template for an eventual 1.21.1 → 26.x move (KubeJS 8, FTB Quests Json5). Quests/scripts will be organized for portability.

## 4. Identity & story

**Name:** AFTERLIGHT — the glow after the light went out, and the light you bring back.

### Premise

Generations ago this world belonged to the **Ascendancy**, a civilization preparing to leave for the stars. Their final project — the **Cascade Engine** — tapped the **Undercurrent**, an energy source beneath physics. The night it came online, the Undercurrent poured through and broke the world: machines twisted into monsters, guardians corrupted, regions scarred. The Ascendancy fled through a barely-finished gate and sealed it. The players wake from a failed cryo-vault: the last engineers, in a wasteland built on the bones of genius.

### Narrator — ECHO

The quest book is diegetic: **ECHO**, a fragmentary facility AI rebooted in chapter 1. All quest text is ECHO's voice — guiding, deadpan, slowly recovering corrupted memory. Each completed chapter restores a **memory fragment** revealing what happened the night of the Cascade. ECHO's arc (fragmentary → whole → conflicted about what it remembers) is the emotional spine. The mystery unspools in lockstep with the tech tree.

### Fiction ↔ mechanics mapping

- **Tech mods** = recovered Ascendancy engineering, tiered by how deep the knowledge was buried
- **Magic mods** = the Undercurrent — the anomaly science can't explain; side-path, eerie, never mandatory except the finale stabilizer
- **GTCEu Modern** = the **Deep Vault** — optional buried archive of heaviest industry; exclusive rewards, zero story-gating
- **Bosses/dungeons** = corrupted guardians and war-remnants squatting in ruins (danger lives in places, not meters)
- **Automation** = ECHO is an infrastructure AI; it wants throughput, not trinkets

### Endgame

**The Gate of Return** — an ATM-Star-class megaproject rebuilding the Ascendancy's gate to reopen contact with the survivors among the stars. Four Gate components, each a certified automation chain from a different tech constellation (Mekanism isotopes, AE2 autocrafting lattice, Create kinetics, IE industry) **plus one Undercurrent stabilizer** — the single moment magic is required (the lesson of the Cascade: you can't engineer around what you refuse to understand). Post-finale: creative-tier rewards, sandbox blessings for the server afterlife. Draconic Evolution (beta) is gated post-story as the "beyond the finale" power sink.

### Working nomenclature (refinable during quest writing)

Ascendancy (fallen civilization) · Cascade (the catastrophe) · Undercurrent (the anomaly/magic) · ECHO (narrator AI) · Gate of Return (endgame artifact) · Deep Vault (GTCEu archive) · Requisition Depot / Chits (quest economy) · Ascendancy Caches (loot crates) · Memory Archive (Modonomicon lore book).

## 5. Mod list architecture

**Target ~300–340 mods** including ~70 libraries. Full pinned manifest is produced in the implementation plan; the spec fixes roles and judgment calls. All named mods verified available/active on NeoForge 1.21.1 (research 2026-08-07).

| Layer | Mods (representative, not exhaustive) |
|---|---|
| **Tech spine** | Mekanism family, AE2 + ExtendedAE + MEGA Cells + Applied Mekanistics, Immersive Engineering, EnderIO, Industrial Foregoing, PneumaticCraft, Powah, Oritech, RFTools suite, Extreme Reactors, Mystical Agriculture, Compact Machines, Modular Machinery Reborn, Pipez, LaserIO, Flux Networks, Just Dire Things, Hostile Neural Networks |
| **Create (moderate)** | Create 6 core, Crafts & Additions, Connected, Copycats+, Slice & Dice, Enchantment Industry, **Create: Aeronautics** (user-approved; airships) |
| **Deep Vault** | GregTech CEu Modern (self-contained optional chapter group) |
| **Undercurrent (magic, compact)** | Ars Nouveau, Occultism, Iron's Spells 'n Spellbooks, Malum |
| **Dangerous world** | L_Ender's Cataclysm, Bosses of Mass Destruction, Mowzie's Mobs, Apotheosis/Apothic family, Better Combat, **Alex's Mobs (unofficial 1.21.1 port)**, **Ice and Fire: Community Edition** (both user-approved) |
| **Worldgen/exploration** | Terralith, Tectonic, Nullscape, Incendium, YUNG's suite, When Dungeons Arise, IDAS, Structory (+Towers), Dungeons and Taverns, custom Ascendancy ruins (own datapack); dimensions: Twilight Forest, Undergarden, Eternal Starlight, Deeper & Darker, Aether (+Deep Aether) |
| **Endgame+** | Draconic Evolution 1.21.1 beta (post-story gated) |
| **Storage/QoL** | Sophisticated Backpacks/Storage, Functional Storage, Tom's Simple Storage, JEI, Jade, JourneyMap, Quark, Waystones, Corpse, VeinMiner Hotkey, Curios, AppleSkin, Mouse Tweaks, Inventory Sorter, Nature's Compass, Advanced Loot Info |
| **Food** | Farmer's Delight + curated addons, Kaleidoscope Cookery |
| **Multiplayer/server** | FTB Teams/Chunks/Essentials/Ranks, Simple Voice Chat, LuckPerms, ServerCore, PacketFixer, spark, Chunky |
| **Story delivery** | FTB Quests + FTB XMod Compat, Immersive Messages API, Modonomicon, Music Triggers (candidate — only with properly licensed audio) |
| **Scripting/integration** | KubeJS 7 (NeoForge), LootJS, KubeJS Create / Mekanism-family addons, AlmostUnified, ProbeJS (dev), Global Packs (datapack loading) |
| **Performance** | Sodium (official NeoForge) + Iris, Lithium (official NeoForge), ModernFix, FerriteCore, EntityCulling, Clumps, GPU Memory Leak Fix, Ixeris, AsyncParticles, Better Block Entities, Crash Assistant |

**Explicit cuts:** Refined Storage (AE2 chosen; two storage systems double unification work), Epic Fight (group-divisive), Thermal (dead), Ad Astra (dead; story carries the space theme), Botania/Blood Magic/Hex (unavailable on 1.21.1; consistent with compact-magic preference), DawnCraft-style RPG bloat.

**Recipe-viewer note:** JEI primary; EMI may be added alongside via TMRV bridge if the group wants it — decision deferred to beta feedback.

## 6. Quest book & progression architecture

**Shape:** 4 acts, ~20 story chapters + 4 side chapter-groups; ~700–900 quests total.

- **Act I — Scavenger (ch 1–4):** vault awakening, survival, ECHO reboot, rustic tech (IE + Create basics)
- **Act II — Engineer (ch 5–11):** the automation heart — Mekanism tiers, power, AE2 lattice, logistics; first Undercurrent contact; dimension expeditions (Twilight, Undergarden, Aether)
- **Act III — Architect (ch 12–16):** fusion/quantum/flight, Oritech frontier, boss gauntlet (Cataclysm), recovering four Gate schematics
- **Act IV — Ascendant (ch 17–20):** Gate of Return megaproject, finale, postgame blessings

**Side chapter-groups:** Deep Vault (GTCEu) · The Undercurrent (magic) · Atlas of the Broken World (exploration/bosses/dimensions) · Certifications (automation curriculum).

### Automation on-ramp (three mechanisms)

1. **Bulk capstones** (Create: Above & Beyond pattern): chapter finales demand quantities miserable by hand, trivial automated; framed as ECHO's infrastructure quotas
2. **Certifications:** step-by-step quest-lines each teaching one automation pattern (Create press line → Mekanism ore loop → AE2 autocraft → cross-mod chains), paying permanent perks
3. **Native throughput detection:** FTB Quests energy/fluid/stat tasks verify production, not pockets

### Reward economy

**Requisition Chits** (quest currency) spent at ECHO's **Requisition Depot** (unlocking quest-shop, MC Eternal pattern); milestone **Ascendancy Caches** (loot-crate tables). Memory fragments per chapter: Modonomicon entry + ECHO monologue via Immersive Messages.

### Gating model

Soft-gated by default (visible early, no locked recipes). **Exactly four hard gates:** (1) Gate component recipes — stage-unlocked by quest completion; (2) Deep Vault entry — found key item; (3) the finale; (4) Draconic Evolution — stage-gated behind story completion (doubles as beta-stability insulation). Implemented via FTB Quests stages + XMod Compat + KubeJS stages.

## 7. Integration layer (KubeJS) — scope

Every script serves story, unification, the automation on-ramp, or a documented balance need (explicit anti-scope-creep rule):

1. **Unification:** AlmostUnified + tag surgery — one item family for ores/ingots/dusts across Mekanism/IE/Create/GTCEu
2. **Bridge recipes:** each major mod's machines can process into neighbors' ecosystems where sensible (Create crushing → Mekanism dirty dust path; IE diesel → Powah/Mekanism fuel chains; etc.)
3. **Loot injection (LootJS):** Ascendancy Caches, memory-lore items, and Gate schematic fragments into dungeon/boss loot
4. **Story tech:** Gate-stage multiblocks via Modular Machinery Reborn + KubeJS recipes consuming certified automation outputs; Requisition Chit items; stage wiring; ECHO screen-lines on quest events
5. **Balance passes:** only where a mod trivializes another's role (documented per-change)

## 8. Repo, toolchain, distribution, server

- **Repo:** packwiz pack-as-code git repo — `pack.toml` + per-mod `.pw.toml`, `config/`, `defaultconfigs/`, `kubejs/`, `config/ftbquests/quests/**.snbt` (quest text in `quests/lang/en_us.snbt`), custom datapacks. No jars in git.
- **Dev loop:** `packwiz serve` → dev Prism instance; ProbeJS typings; in-game FTB Quests editor writes SNBT directly into repo; KubeJS server scripts hot-reload via `/reload`
- **CI (GitHub Actions):** packwiz refresh check → `.mrpack` + CurseForge zip artifacts → headless server-boot smoke test (itzg image health check)
- **Distribution:** (a) **primary:** Prism instance zip with packwiz-installer-bootstrap pointed at GitHub Pages — auto-sync every launch; (b) **zip lane:** versioned `.mrpack`/CF zip releases; (c) **dragnet:** AutoModpack on the server for one-jar friends
- **VPS:** itzg/docker-minecraft-server, `PACKWIZ_URL` at the same GitHub Pages source; `git push` + restart = server updated in lockstep. 10–12GB heap, Java 21, Chunky pregen playbook, automated backups, `docker compose` one-command setup doc
- **Licensing hygiene (publish-grade):** every mod fetched via packwiz from CurseForge/Modrinth (no rehosting); track per-mod licenses; custom content (quests, scripts, datapacks, art) original or properly licensed; no copyrighted audio unless licensed (Music Triggers ships only with cleared tracks)

## 9. Performance & defaults

- Client defaults: shader-ready (Iris installed, off by default), pretty leaves, sane render distance, JourneyMap tuned, Quark tuned, keepInventory **off** (Corpse mod makes death fair)
- Server: ServerCore + spark baseline, pregen via Chunky, view-distance tuned for group size
- Budget targets: client ~8–10GB alloc on 16GB+ machines; server 10–12GB heap

## 10. Testing & launch criteria

- Clean client boot < 3 min on target hardware; zero startup errors that matter (triaged log)
- Headless server boot green in CI on every push
- All three hard gates verified openable; every Certification line hand-tested
- Chapters 1–8 quest flow played through on dev instance before friends join
- **Launch model:** go live when ch 1–8 (~60–80 hrs of content) are polished; later chapters ship via auto-update mid-season (quest SNBT syncs without world resets)

## 11. Out of scope (this cycle)

- Public publishing (Modrinth/CurseForge listing + permission declarations) — enabled-by-design, not executed
- 26.x migration — deferred until ecosystem matures (~ATM11 1.0); ATM-11 repo is the template
- Custom Java companion mod — only if a required story mechanic proves impossible in KubeJS + existing mods (decision point in implementation plan)
- Voice acting / licensed soundtrack

## 12. Key references (research 2026-08-07)

- Study repos: [ATM-10](https://github.com/AllTheMods/ATM-10) (KubeJS layout, ATM Star chain), [Enigmatica 10](https://github.com/EnigmaticaModpacks/Enigmatica10) (engineering culture, config normalization), [Craftoria](https://github.com/TeamAOF/Craftoria) (2000+ quests, addon usage), [ATM-11](https://github.com/AllTheMods/ATM-11) (26.x migration template), [packwiz-example-pack](https://github.com/packwiz/packwiz-example-pack)
- Tooling: [packwiz](https://github.com/packwiz/packwiz) · [packwiz-installer](https://packwiz.infra.link/tutorials/installing/packwiz-installer/) · [itzg docker packwiz support](https://docker-minecraft-server.readthedocs.io/en/latest/mods-and-plugins/packwiz/) · [AutoModpack](https://modrinth.com/mod/automodpack) · [Prism Launcher](https://prismlauncher.org)
- Narrative gold standards analyzed: Blightfall (diegetic book), MC Eternal (Questmaster framing + quest shop), MeatballCraft (lore density), GTNH (guidance quality), Create: A&B (bulk-capstone automation quests), Fear Nightfall (prose-only narrative), SevTech (mystery-preserving gating)
- Installed agent skills used: `minecraft-modpack-authoring`, `kubejs-modding`, `ftb-quests`, `neoforge-modding`, `modrinth-api`, `minecraft-modding`
