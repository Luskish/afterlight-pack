# AFTERLIGHT Handoff Guide

For continuing this project in Codex, a fresh Claude session, or any capable agent. Last updated: 2026-08-08, immediately after Plan 01 merged.

## Current state (verified, not aspirational)

- Repo: https://github.com/Luskish/afterlight-pack (public). `main` = stable, `dev` = working branch, both pushed and identical at Plan 01 completion.
- Auto-update URL live and byte-exact: https://luskish.github.io/afterlight-pack/pack.toml (GitHub Pages from main root).
- CI (`pack-ci`) green on main and dev: manifest integrity, mrpack + CF exports, full headless NeoForge server boot on ubuntu.
- Pack: 22 mods (performance/ops/QoL baseline), NeoForge 21.1.248, MC 1.21.1. All 22 verified against the live Modrinth API by `tools/verify-pack.sh`.
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
| W4 Deep Vault (MILESTONE) | pending | |
| W5 Undercurrent magic | pending | |
| W6 Dangerous world (MILESTONE) | pending | |
| W7 Worldgen/structures | pending | |
| W8 Dimensions (MILESTONE) | pending | |
| W9 Storage/QoL 2 | pending | |
| W10 Food | pending | |
| W11 Multiplayer | pending | |
| W12 Story/scripting (MILESTONE) | pending | |
| W13 Endgame + perf 2 | pending | |
| Task 14 verification sweep | pending | |
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

Then produce docs/superpowers/plans/2026-08-08-afterlight-02-roster.md: a Plan 02 implementation plan in the same task/step format as Plan 01, covering (a) the three mandated hardening commits listed in docs/HANDOFF.md, then (b) the full mod roster built in category waves per spec section 5 with the wave pattern from docs/HANDOFF.md, then (c) config normalization and AlmostUnified setup. Respect the spec's taste calibration: Create moderate, magic compact, GregTech as optional Deep Vault, generous on wow-factor. Every wave ends with tools/verify-pack.sh ALL GREEN and a commit; server-test green before any merge to main.

Present the plan to me for approval before executing anything. When you hit a genuine ambiguity, ask me one question at a time with a recommended option.
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
