# AFTERLIGHT Handoff Guide

For continuing this project in Codex, a fresh Claude session, or any capable agent. Last updated: 2026-08-08, after Plan 02 waves 0-14 (167 mods on dev). Only Task 15 (configs + approved merge) remains in Plan 02.

## Current state (verified, not aspirational)

- Repo: https://github.com/Luskish/afterlight-pack (public). `main` = stable, `dev` = working branch, both pushed and identical at Plan 01 completion.
- Auto-update URL live and byte-exact: https://luskish.github.io/afterlight-pack/pack.toml (GitHub Pages from main root).
- CI (`pack-ci`) green on main and dev: manifest integrity, both exports build (no artifacts uploaded: friends-only policy), full headless NeoForge server boot on ubuntu.
- Pack: see the live progress table below for current mod count and wave state. Baseline platform: NeoForge 21.1.248, MC 1.21.1. Modrinth-sourced mods are live-API verified by `tools/verify-pack.sh`; CurseForge-sourced mods show SKIP there and are validated by the server boot + CI instead.
- Friend-facing artifact `dist/AFTERLIGHT-prism-instance.zip` is built but NOT yet distribution-approved: Shane must first do one manual Prism import + launch (client-side boot has never been exercised; needs a Microsoft account).
- The design spec, the completed Plan 01 (with the Plan 02-07 roadmap table), and six committed project skills in `.agents/skills/` are all in this repo.

## Plan 02 status: IN EXECUTION

The full plan is written: `docs/superpowers/plans/2026-08-08-afterlight-02-roster.md` (Task 0 hardening + Waves 1-13 + verification sweep + configs). Resume at the first wave below not marked complete, following the plan's Wave Pattern exactly.

### Plan 02 live progress (update after every wave)

| Task | Status | Notes |
|---|---|---|
| Task 0 hardening (3 commits) | COMPLETE | .nojekyll live, Pages verified 200 post-deploy, CI hardened + packwiz pinned (dfd8b68) |
| W1 Tech spine A | COMPLETE | 37 mods total. CF-sourced (Modrinth-absent): Applied Flux, ExtendedAE (file ex-pattern-provider.pw.toml), Glodium dep. LESSONS: pipe `printf 'Y\n'` into every `packwiz mr add` (dep prompts EOF-abort otherwise); slug extendedae on Modrinth is the WRONG mod (Plus addon). POLICY: CI no longer uploads pack artifacts (CF-sourced mods embed jars in mrpack overrides; friends-only). verify-pack check 1 now tests true refresh idempotence, works mid-wave. |
| W2 Tech spine B (MILESTONE) | COMPLETE | 63 mods total. Local server boot OK with full tech spine. Modrinth slug is `enderio` not ender-io. CF-sourced: LaserIO, RFTools Base/Utility/Power, Compact Machines (slug compact-machines), Flux Networks, Just Dire Things (slug just-dire-things). CF name-search trap: "Compact Machines" query offers Preview Fixer first, use exact slugs. Modrinth-absent on 1.21.1: Compact Machines, Flux Networks, Just Dire Things. |
| W3 Create set | COMPLETE | 73 mods. All 7 requested + 3 legit required deps (Sable via Aeronautics, Create: Dragons Plus via Enchantment Industry, Kotlin for Forge via Slice and Dice). All Modrinth-native. |
| W4 Deep Vault (MILESTONE) | COMPLETE | 74 mods. ENGINE SWAP (Shane-approved, spec amended): Modern Industrialization replaces GTCEu. GTCEu 7.0.x crashes dedicated servers (client class on server dist); GTCEu 1.4.6 incompatible with Create 6 (IStressValueProvider removed). Both proven by boot tests. MI 2.5.6 boots green. Revisit GTCEu at 26.x migration. |
| W5 Undercurrent magic | COMPLETE | 81 mods. 4 requested + legit deps: curios (W9 want), modonomicon (W12 want), smartbrainlib. All Modrinth-native. |
| W6 Dangerous world (MILESTONE) | COMPLETE | 101 mods, boot OK. Slugs: l_enders-cataclysm (underscore), bosses-of-mass-destruction-forge. CF: alexs-mobs-1-21-1-port (+Citadel port dep). LESSON: Modrinth dep metadata MISSES some required libs; boot revealed irons_lib + lodestonelib missing (wave 5 gap, fixed here). Slug lodestone = a datapack, the lib is lodestonelib. Non-milestone waves rely on CI boot for this class of catch. |
| W7 Worldgen/structures | COMPLETE | 124 mods. IDAS slug is idas; it pulled Quark (W9 want, early), Supplementaries, Integrated API as required deps. All Modrinth-native. |
| W8 Dimensions (MILESTONE) | COMPLETE | 134 mods, boot OK. Slugs: deeperdarker; Twilight Forest is CF-only (the-twilight-forest). LESSON: Stardust multi-version projects can resolve 26.x jars that PASS the API check but fail to load (filename says 26.2): Structory + Towers repinned to 1.21.x version URLs (MXU49bpN, lefqbuOP). Also fixed undeclared libs moonlight (Supplementaries) + zeta (Quark). Verify-pack improvement candidate: flag filenames with a different MC line than 1.21. |
| W9 Storage/QoL 2 | COMPLETE | 142 mods. quark+curios arrived early via deps in W5/W7. Inventory Sorter is CF-only (slug inventory-sorter); Modrinth veinminer-client is correctly side=client. |
| W10 Food | COMPLETE | Farmers Delight + My Nethers Delight + Kaleidoscope Cookery. |
| W11 Multiplayer | COMPLETE | 151 mods. FTB suite is CF-only: slugs ftb-teams-forge/ftb-chunks-forge/ftb-ranks-forge (+ftb-library-forge dep) but plain ftb-essentials. SVC + LuckPerms Modrinth-native. W10 note: mynethersdelight not on Modrinth 1.21.1, skipped per plan.
| W12 Story/scripting (MILESTONE) | COMPLETE | 161 mods, boot OK. Slugs: almostunified (no hyphen), CF ftb-quests-forge + ftb-xmod-compat + immersive-messages-api; Global Packs CF slug is global-datapacks. Modonomicon was already in via W5. |
| W13 Endgame + perf 2 | COMPLETE | 167 mods. Draconic Evolution via CF (beta, post-story gating comes in Plan 03). Perf adds correctly side=client. gpumemleakfix not found on CF under any slug: SKIPPED (minor, revisit). |
| Task 14 verification sweep | COMPLETE | 167 mods: boot OK, verify-pack ALL GREEN, exports build (mrpack 90M with CF-sourced mods embedded in overrides, CF zip 662M: BOTH friends-only now), client-side audit clean (10 render/UI mods), 156 server jars. |
| Task 15 configs + main merge | pending | needs Shane's explicit approval to merge |

## Plan 02 original scope notes

Scope per the roadmap: grow from 22 to roughly 320 mods in category waves following spec section 5, then config normalization and AlmostUnified recipe unification. Mandated first three commits (from the final Plan 01 review):
1. Add an empty `.nojekyll` at repo root, then confirm https://luskish.github.io/afterlight-pack/pack.toml still serves after the next main deploy.
2. Harden `.github/workflows/pack-ci.yml`: `permissions: {contents: read}`, `concurrency` group with cancel-in-progress, `timeout-minutes: 30`, `workflow_dispatch:` trigger.
3. Pin the packwiz version in CI (replace `@latest` in the `go install` line with a known-good commit hash).

Wave pattern for mod additions (repeat per category from spec section 5): add mods with correct sides, `packwiz refresh`, commit (pack.toml + index.toml + mods/ together), run `./tools/verify-pack.sh` (must be ALL GREEN), push dev, confirm CI green. Run `BOOT_TIMEOUT=600 ./tools/server-test.sh` before any merge to main. Expect some mods to need dependency additions; accept packwiz's dependency prompts and verify them.

## Step-by-step: handing off to Codex

1. In Codex, connect the GitHub account (Luskish) and point it at `Luskish/afterlight-pack`, branch `dev`. The repo is public and self-contained: skills, tools, docs all travel with the clone. No secrets exist or are needed.
2. Local-machine note: if running on Shane's Mac instead of Codex cloud, the toolchain already exists (JDK in `~/.jdks`, packwiz in `~/go/bin`). On a fresh cloud machine, `tools/server-test.sh` bootstraps its own NeoForge; packwiz installs via `go install github.com/packwiz/packwiz@latest`; Java 21 via the environment (see `tools/versions.env`, environment wins).
3. Paste the Kickoff Prompt below as the first message.
4. Review the Plan 02 document the agent produces BEFORE letting it execute (this is the one human gate that catches scope drift cheapest).
5. Per session afterwards, paste the Continuation Prompt.

## Kickoff Prompt (paste into Codex, first session)

```
You are taking over the AFTERLIGHT Minecraft modpack project mid-stream. It is a story-driven kitchen-sink pack (NeoForge 1.21.1) with completed foundation infrastructure. Work on branch dev.

Before any action:
1. Read AGENTS.md at the repo root. Every guardrail in it is binding (no em dashes anywhere, skills-first workflow, verification before claims, packwiz discipline, branch model).
2. Read docs/HANDOFF.md (current state), docs/superpowers/specs/2026-08-07-afterlight-modpack-design.md (the approved design), and the roadmap table in docs/superpowers/plans/2026-08-07-afterlight-01-foundation.md.
3. Read the SKILL.md of each skill in .agents/skills/. Before each piece of work, re-read the relevant skill and follow it (packwiz work: minecraft-modpack-authoring; mod lookups: modrinth-api; later phases: ftb-quests, kubejs-modding).

Then: docs/superpowers/plans/2026-08-08-afterlight-02-roster.md already exists and is partially executed. Find the first wave in docs/HANDOFF.md's live progress table that is not COMPLETE and execute it per the plan's Wave Pattern (including the lessons recorded in completed waves' notes: printf 'Y\n' piped into every packwiz add, exact-slug discipline, side checks). Update the live progress table after every wave. If instead all Plan 02 tasks are complete, write the next plan per the roadmap table in the Plan 01 document and present it for approval before executing.

Respect the spec's taste calibration: Create moderate, magic compact, GregTech as optional Deep Vault, generous on wow-factor. Every wave ends with tools/verify-pack.sh ALL GREEN and a commit; server-test green at MILESTONE waves and before any merge to main. When you hit a genuine ambiguity, ask me one question at a time with a recommended option.
```

## Continuation Prompt (paste to resume in later sessions)

```
Continuing the AFTERLIGHT modpack project on branch dev. Re-read AGENTS.md and docs/HANDOFF.md, check git log and the current plan document in docs/superpowers/plans/ to find the first unfinished task, then continue executing it. Follow every guardrail (no em dashes, skills-first, verify before claiming, packwiz discipline). Run ./tools/verify-pack.sh before telling me anything is done. Ask me one question at a time when genuinely blocked.
```

## Review Prompt (optional, run periodically or before merging dev to main)

```
Act as a skeptical reviewer of the AFTERLIGHT repo on branch dev. Read AGENTS.md for the binding guardrails, then audit the most recent work: verify tools/verify-pack.sh is ALL GREEN, confirm every mod added since the last merge has a deliberate side value and matches a spec section 5 category, check no root file entered the packwiz index unintentionally (grep index.toml), confirm CI is green, and list any guardrail violations with file references. Report findings ranked by severity. Do not fix anything without my approval.
```

## Hard rules the prompts assume (also in AGENTS.md)

- No em dashes in any text, anywhere.
- Skills in `.agents/skills/` are read before the work they cover, every time.
- Nothing is "done" without its verification command having just run green.
- `dev` for work, `main` only via green CI, never force-push, never delete dev.
- No jars/secrets in git; CF zip stays friends-only; new root files go into `.packwizignore`.
- One question at a time when blocked, with a recommendation.

## If returning to Claude instead of Codex

Same prompts work. Claude Code additionally auto-loads `CLAUDE.md` (which points at AGENTS.md) and has project memory covering state and Shane's preferences (opus/fable-only subagents, personal verification passes). The superpowers plugin skills (brainstorming, writing-plans, subagent-driven-development) apply on top for plan authoring and execution.
