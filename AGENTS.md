# AFTERLIGHT Agent Guardrails

This file is the source of truth for how ANY agent (Codex, Claude, or other) works in this repo. Read it fully before your first action. These guardrails mirror Shane's ranked-betting-app project conventions.

## Project identity

AFTERLIGHT is a story-driven kitchen-sink Minecraft modpack (NeoForge 1.21.1, Java 21) for a private friend group. Quality bar: "as seamless as All The Mods, but better." Full design: `docs/superpowers/specs/2026-08-07-afterlight-modpack-design.md`. Completed Plan 01 + the Plan 02-07 roadmap: `docs/superpowers/plans/2026-08-07-afterlight-01-foundation.md`. Current state and handoff prompts: `docs/HANDOFF.md`.

## Writing style (hard rule)

- NO EM DASHES. Not in docs, quest text, code comments, commit messages, or replies to Shane. Use commas, colons, parentheses, or separate sentences instead.
- Quest and story text is written in ECHO's voice (see spec section 4) once quest work begins.

## Skills-first workflow (hard rule)

- Six project skills live in `.agents/skills/` (committed to this repo). Before ANY task, check whether one applies and follow it:
  - packwiz / pack structure / exports / server validation: `minecraft-modpack-authoring`
  - FTB Quests SNBT work: `ftb-quests`
  - KubeJS scripts: `kubejs-modding`
  - Mod lookups, version checks, downloads: `modrinth-api`
  - NeoForge specifics or Java mod work: `neoforge-modding`, `minecraft-modding`
- If a task has no matching skill, search for one first (`npx skills find <topic>`) before improvising. Vet anything under 100 installs by reading it.
- If you think there is even a small chance a skill applies, read it. This is not optional.

## Verification before claims (hard rule)

Never state that something works without having run the check in the same session:
- Manifest or mod changes: `./tools/verify-pack.sh` must print `VERIFY: ALL GREEN`.
- Anything touching mods, configs, or scripts: `BOOT_TIMEOUT=600 ./tools/server-test.sh` must print `SERVER BOOT: OK` before merge to main.
- CI (`pack-ci`) must be green on the pushed branch before merging to main.
- Report failures verbatim. Never soften, never claim partial success as success.

## Packwiz discipline

- Every shell that runs packwiz starts with: `source tools/versions.env && export PATH="$PATH_EXTRA:$PATH"`.
- Every packwiz-touching commit includes `pack.toml`, `index.toml`, and `mods/` together. Never leave refresh output uncommitted. Never run `packwiz refresh` after your final commit.
- Every mod gets a deliberate `side` value (`client`, `server`, or `both`). Client-only mods must never reach the server install.
- New root-level files must be added to `.packwizignore` unless they are meant to ship inside the pack. The pack index is served publicly; check `index.toml` after refresh.
- No jars, secrets, or tokens in git, ever.

## Branch and release model

- `dev` is the working branch. `main` is the stable channel that friends' launchers auto-update from (GitHub Pages serves it). Merge dev to main only on green CI. Never delete dev. Never force-push either branch.
- Shane explicitly authorized public distribution of the current `.mrpack` and CurseForge ZIP on 2026-08-11. This authorization supersedes every earlier friends-only classification for those launcher archives.
- A public release contains exactly `AFTERLIGHT-prism-instance.zip`, `AFTERLIGHT-curseforge.zip`, `AFTERLIGHT.mrpack`, `SHA256SUMS`, and `release-metadata.json` in one flat inventory. No additional file, directory, or link is allowed.
- Every launcher archive is inspected before release. Reject malformed archives, unsafe paths, links, secrets, private keys, and unclassified files. Checksums and metadata must bind all three launcher archives.
- Published releases and tags are immutable. Fix forward with a new candidate, never replace an asset or move a published tag.

## Scope discipline

- KubeJS scripts exist only for: story mechanics, unification, the automation on-ramp, or a documented balance need (spec section 7). No scripting for its own sake.
- Mod additions follow the spec section 5 category tables. Adding mods outside those categories requires asking Shane first.

## Working with Shane

- When requirements are ambiguous, ask one question at a time, with options and a recommended choice. Shane wants to be grilled on real decisions, not asked for permission on routine ones.
- Destructive actions (deleting worlds, force-pushes, removing mods mid-save, changing distribution architecture) always require an explicit ask.
- End commit messages with an attribution trailer naming the agent that authored the work (e.g. `Co-Authored-By: Codex <noreply@openai.com>` or the Claude equivalent).

## Known machine quirks (Shane's Mac)

- JDK 21 is a user-space tarball in `~/.jdks`; packwiz lives in `~/go/bin`. Both are wired through `tools/versions.env` (`${VAR:-default}` forms, environment wins in CI). There is no system Java.
- The shell is non-interactive: nothing can type an admin password. Prefer user-space installs.
