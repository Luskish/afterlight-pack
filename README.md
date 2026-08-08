# AFTERLIGHT

A story-driven kitchen-sink modpack for Minecraft NeoForge 1.21.1.
You aren't discovering technology — you're remembering it.

- **Design spec:** docs/superpowers/specs/2026-08-07-afterlight-modpack-design.md
- **Pack source:** this repo is a [packwiz](https://packwiz.infra.link/) pack; mods are TOML metadata under `mods/`, no jars in git.
- **Players:** see docs/INSTALL.md (created in Plan 01 Task 7) for the auto-updating Prism instance.
- **Dev loop:** `packwiz serve` + a Prism dev instance; `tools/server-test.sh` for headless server verification.

## Layout
- `pack.toml` / `index.toml` — packwiz manifest
- `mods/` — one `.pw.toml` per mod
- `config/`, `defaultconfigs/` — shipped configuration
- `kubejs/` — startup/server/client scripts (integration layer)
- `config/ftbquests/` — quest book source (from Plan 04)
- `tools/` — dev/test scripts (not shipped)
- `docs/` — specs, plans, player docs (not shipped)
